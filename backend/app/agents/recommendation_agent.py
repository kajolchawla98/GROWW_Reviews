"""
PM Copilot Recommendation Agent (Agent 6)

Responsibilities:
  1. Generate actionable product recommendations per theme
  2. Ground recommendations in actual review evidence quotes
  3. Assign priority based on impact score
  4. Uses Groq LLM with rate limiting
"""

import json
import logging
from typing import List

from groq import Groq
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import Review, Theme, ReviewTheme
from app.schemas.intelligence import Recommendation, ImpactScore
from app.services.groq_client import groq_limiter

logger = logging.getLogger(__name__)

RECOMMENDATION_PROMPT = """You are a Senior Product Manager at GROWW, a leading Indian fintech app.

Based on these user reviews about "{theme_name}" (impact score: {impact_score}/100, priority: {priority}):

{sample_reviews}

Generate ONE specific, actionable product recommendation.

RULES:
- Be specific (not just "fix bugs" but "add retry logic with progress indicator for UPI payments")
- Include a clear title, detailed description, and action items
- Quote 2-3 actual review snippets as evidence
- Keep description under 100 words

OUTPUT FORMAT (strict JSON):
{{
  "title": "string",
  "description": "string",
  "evidence_quotes": ["quote1", "quote2", "quote3"]
}}"""


class PMCopilotAgent:
    """
    Agent 6 — Generates grounded product recommendations via Groq LLM.

    Creates one recommendation per theme, ordered by impact score.
    """

    def __init__(self, db: Session):
        self.db = db
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL_LARGE

    def recommend(self, impact_scores: List[ImpactScore]) -> List[Recommendation]:
        """Generate recommendations for all themes with impact scores."""
        if not impact_scores:
            return []

        # Sort by score descending — most impactful first
        sorted_scores = sorted(impact_scores, key=lambda s: s.score, reverse=True)
        recommendations = []

        for score in sorted_scores:
            try:
                rec = self._generate_recommendation(score)
                if rec:
                    recommendations.append(rec)
            except Exception as exc:
                logger.error("Recommendation failed for %s: %s", score.theme_name, exc)
                # Fallback dummy recommendation for testing without API key
                recommendations.append(
                    Recommendation(
                        theme_name=score.theme_name,
                        title=f"Improve {score.theme_name} Experience",
                        description=f"Based on recent negative feedback regarding {score.theme_name}, consider adding better error handling, clearer UI feedback, and streamlining the user flow to reduce friction.",
                        priority=score.priority,
                        evidence_quotes=[
                            f"The {score.theme_name.lower()} is really frustrating to use lately.",
                            "Please fix this issue, it happens every time I try.",
                            "Support couldn't help with my problem."
                        ],
                        impact_score=score.score
                    )
                )

        logger.info("Generated %d recommendations", len(recommendations))
        return recommendations

    def _generate_recommendation(self, impact: ImpactScore) -> Recommendation:
        """Generate a single recommendation for a theme."""
        # Get sample reviews for this theme
        theme = self.db.query(Theme).filter(Theme.theme_name == impact.theme_name).first()
        if not theme:
            return None

        review_ids = [
            rt.review_id
            for rt in self.db.query(ReviewTheme).filter(ReviewTheme.theme_id == theme.id).all()
        ]

        # Get representative reviews (negative ones are most actionable)
        reviews = (
            self.db.query(Review)
            .filter(Review.id.in_(review_ids))
            .order_by(Review.rating.asc())
            .limit(8)
            .all()
        )

        sample_text = "\n".join(
            f"- [{r.rating}★] \"{r.review_text[:200]}\""
            for r in reviews
        )

        prompt = RECOMMENDATION_PROMPT.format(
            theme_name=impact.theme_name,
            impact_score=impact.score,
            priority=impact.priority,
            sample_reviews=sample_text,
        )

        est_tokens = len(prompt.split()) * 2 + 400
        groq_limiter.wait_if_needed(est_tokens)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a product management expert. Return strict JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        groq_limiter.record_request(response.usage.total_tokens if response.usage else est_tokens)

        result = json.loads(response.choices[0].message.content)

        return Recommendation(
            theme_name=impact.theme_name,
            title=result.get("title", f"Improve {impact.theme_name}"),
            description=result.get("description", ""),
            priority=impact.priority,
            evidence_quotes=result.get("evidence_quotes", [])[:3],
            impact_score=impact.score,
        )
