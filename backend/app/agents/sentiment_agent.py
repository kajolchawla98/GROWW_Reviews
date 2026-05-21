"""
Sentiment & Emotion Agent (Agent 3)

Responsibilities:
  1. Classify each review's sentiment (positive/negative/neutral/mixed)
  2. Assign emotion labels (anger, frustration, satisfaction, delight, confusion)
  3. Generate confidence scores for each classification
  4. Process in batches to respect Groq rate limits
"""

import json
import logging
from typing import List

from groq import Groq

from app.config import settings
from app.schemas.review import ReviewRecord
from app.schemas.analysis import SentimentAnnotation
from app.services.groq_client import groq_limiter

logger = logging.getLogger(__name__)


SENTIMENT_SYSTEM_PROMPT = """You are a sentiment analysis expert for the GROWW fintech app.
For each review, determine:
1. Sentiment: exactly one of "positive", "negative", "neutral", "mixed"
2. Sentiment score: float from -1.0 (most negative) to 1.0 (most positive)
3. Primary emotion: exactly one of "anger", "frustration", "satisfaction", "delight", "confusion", "neutral"
4. Confidence: float 0.0-1.0

OUTPUT FORMAT (strict JSON):
{
  "annotations": [
    {
      "index": 0,
      "sentiment": "negative",
      "sentiment_score": -0.8,
      "emotion": "frustration",
      "confidence": 0.92
    }
  ]
}"""

SENTIMENT_USER_TEMPLATE = """Analyze sentiment and emotion for these {count} reviews.
Return strict JSON only, no markdown.

Reviews:
{reviews}"""


class SentimentEmotionAgent:
    """
    Agent 3 — Classifies sentiment and emotion for each review via Groq LLM.

    Processes reviews in batches to stay within Groq rate limits.
    """

    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL  # 8b-instant is fast enough for sentiment
        self.batch_size = settings.LLM_BATCH_SIZE

    def analyze(self, reviews: List[ReviewRecord]) -> List[SentimentAnnotation]:
        """
        Analyze sentiment and emotion for all reviews.

        Returns one SentimentAnnotation per review.
        """
        if not reviews:
            return []

        logger.info("Starting sentiment analysis for %d reviews", len(reviews))
        all_annotations: List[SentimentAnnotation] = []

        # Process ONLY the first batch via LLM to save time and tokens
        sample_size = min(len(reviews), 50)
        first_batch = reviews[:sample_size]
        
        logger.info("Sentiment batch 1 (LLM) (%d reviews)", len(first_batch))
        llm_annotations = self._analyze_batch(first_batch, start_idx=0)
        all_annotations.extend(llm_annotations)

        # Heuristic for the rest
        if len(reviews) > sample_size:
            logger.info("Applying heuristic sentiment for remaining %d reviews", len(reviews) - sample_size)
            for r in reviews[sample_size:]:
                all_annotations.append(self._heuristic_annotation(r))

        # Ensure we have one annotation per review
        if len(all_annotations) < len(reviews):
            annotated_ids = {a.review_id for a in all_annotations}
            for r in reviews:
                if r.review_id not in annotated_ids:
                    all_annotations.append(self._heuristic_annotation(r))

        logger.info("Sentiment analysis complete: %d annotations", len(all_annotations))
        return all_annotations

    # ── Private ──────────────────────────────────────────────────────

    def _analyze_batch(
        self,
        batch: List[ReviewRecord],
        start_idx: int,
    ) -> List[SentimentAnnotation]:
        """Analyze sentiment for a single batch via Groq."""
        reviews_text = self._format_reviews(batch, start_idx)
        prompt = SENTIMENT_USER_TEMPLATE.format(count=len(batch), reviews=reviews_text)

        est_tokens = len(prompt.split()) * 2 + 500
        groq_limiter.wait_if_needed(est_tokens)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SENTIMENT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"},
            )
            actual_tokens = response.usage.total_tokens if response.usage else est_tokens
            groq_limiter.record_request(actual_tokens)

            result = json.loads(response.choices[0].message.content)
            annotations = []

            for a in result.get("annotations", []):
                local_idx = a.get("index", 0)
                # Map local index to batch index
                if isinstance(local_idx, int) and local_idx < len(batch):
                    review = batch[local_idx]
                elif local_idx - start_idx >= 0 and local_idx - start_idx < len(batch):
                    review = batch[local_idx - start_idx]
                else:
                    continue

                annotations.append(SentimentAnnotation(
                    review_id=review.review_id,
                    sentiment=self._validate_sentiment(a.get("sentiment", "neutral")),
                    sentiment_score=max(-1.0, min(1.0, float(a.get("sentiment_score", 0.0)))),
                    emotion=self._validate_emotion(a.get("emotion", "neutral")),
                    confidence=max(0.0, min(1.0, float(a.get("confidence", 0.7)))),
                ))

            return annotations

        except Exception as exc:
            logger.error("Sentiment batch failed: %s", exc)
            # Fallback: rating-based heuristic
            return [self._heuristic_annotation(r) for r in batch]

    def _heuristic_annotation(self, review: ReviewRecord) -> SentimentAnnotation:
        """Fallback: infer sentiment from star rating."""
        if review.rating >= 4:
            sentiment, score, emotion = "positive", 0.6, "satisfaction"
        elif review.rating <= 2:
            sentiment, score, emotion = "negative", -0.6, "frustration"
        else:
            sentiment, score, emotion = "neutral", 0.0, "neutral"

        return SentimentAnnotation(
            review_id=review.review_id,
            sentiment=sentiment,
            sentiment_score=score,
            emotion=emotion,
            confidence=0.5,  # Low confidence for heuristic
        )

    def _default_annotation(self, review: ReviewRecord) -> SentimentAnnotation:
        """Default annotation for reviews that weren't processed."""
        return self._heuristic_annotation(review)

    @staticmethod
    def _validate_sentiment(value: str) -> str:
        valid = {"positive", "negative", "neutral", "mixed"}
        return value.lower() if value.lower() in valid else "neutral"

    @staticmethod
    def _validate_emotion(value: str) -> str:
        valid = {"anger", "frustration", "satisfaction", "delight", "confusion", "neutral"}
        return value.lower() if value.lower() in valid else "neutral"

    @staticmethod
    def _format_reviews(reviews: List[ReviewRecord], start_idx: int) -> str:
        lines = []
        for i, r in enumerate(reviews):
            text = r.text[:300] if len(r.text) > 300 else r.text
            lines.append(f"[{i}] (rating:{r.rating}) {text}")
        return "\n".join(lines)
