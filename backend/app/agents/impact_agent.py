"""
Product Impact Scoring Agent (Agent 5)

Responsibilities:
  1. Compute weighted composite impact score (0–100) per theme
  2. Assign P0–P3 priority based on score thresholds
  3. Uses configurable weight formula

Formula:
  volume(20%) + neg_sentiment(25%) + rating(15%)
  + trend_accel(20%) + repeat_freq(10%) + biz_keywords(10%)
"""

import logging
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import Review, Sentiment, Theme, ReviewTheme
from app.schemas.intelligence import ImpactScore, TrendSignal

logger = logging.getLogger(__name__)

# Business-critical keywords that amplify severity
BIZ_KEYWORDS = [
    "payment", "upi", "money", "transaction", "kyc", "withdraw",
    "crash", "freeze", "stuck", "error", "fail", "lost", "scam",
    "refund", "deduct", "broken", "bug", "fraud", "unauthorized",
]


class ProductImpactScoringAgent:
    """
    Agent 5 — Scores each theme's product impact from 0 to 100.

    Priority mapping:
      P0: 90–100 (critical)
      P1: 70–89  (high)
      P2: 40–69  (medium)
      P3: 0–39   (low)
    """

    WEIGHTS = {
        "volume": 0.20,
        "neg_sentiment": 0.25,
        "rating": 0.15,
        "trend_accel": 0.20,
        "repeat_freq": 0.10,
        "biz_keywords": 0.10,
    }

    def __init__(self, db: Session):
        self.db = db
        self.total_reviews = self.db.query(Review).count() or 1

    def score(self, trends: List[TrendSignal]) -> List[ImpactScore]:
        """Compute impact scores for all themes using trend data."""
        themes = self.db.query(Theme).all()
        if not themes:
            return []

        trend_map = {t.theme_name: t for t in trends}
        scores = []

        for theme in themes:
            trend = trend_map.get(theme.theme_name)
            impact = self._score_theme(theme, trend)
            scores.append(impact)

        scores.sort(key=lambda s: s.score, reverse=True)
        logger.info("Impact scoring complete: %s", [(s.theme_name, s.score, s.priority) for s in scores])
        return scores

    def _score_theme(self, theme: Theme, trend: TrendSignal = None) -> ImpactScore:
        """Compute impact score for a single theme."""
        review_ids = [
            rt.review_id
            for rt in self.db.query(ReviewTheme).filter(ReviewTheme.theme_id == theme.id).all()
        ]

        # 1. Volume component (what % of total reviews is this theme?)
        vol_ratio = len(review_ids) / self.total_reviews
        volume_score = min(vol_ratio * 500, 100)  # Cap at 100

        # 2. Negative sentiment component
        neg_count = 0
        if review_ids:
            neg_count = (
                self.db.query(Sentiment)
                .filter(Sentiment.review_id.in_(review_ids), Sentiment.sentiment == "negative")
                .count()
            )
        neg_ratio = neg_count / max(len(review_ids), 1)
        neg_score = neg_ratio * 100

        # 3. Rating component (lower avg rating = higher impact)
        avg_rating = 3.0
        if review_ids:
            result = (
                self.db.query(func.avg(Review.rating))
                .filter(Review.id.in_(review_ids))
                .scalar()
            )
            avg_rating = float(result) if result else 3.0
        rating_score = (5 - avg_rating) / 4 * 100  # 1-star → 100, 5-star → 0

        # 4. Trend acceleration component
        trend_score = 0.0
        if trend:
            if trend.is_spike:
                trend_score = 100
            elif trend.volume_change_pct > 0:
                trend_score = min(trend.volume_change_pct, 100)

        # 5. Repeat frequency (reviews with similar text patterns)
        repeat_score = min(len(review_ids) / 10, 100)  # More reviews = more repeats

        # 6. Business keyword score
        keyword_score = 0.0
        if review_ids:
            reviews = self.db.query(Review.review_text).filter(Review.id.in_(review_ids)).all()
            keyword_hits = sum(
                1 for r in reviews
                for kw in BIZ_KEYWORDS
                if kw in r[0].lower()
            )
            keyword_ratio = keyword_hits / max(len(reviews), 1)
            keyword_score = min(keyword_ratio * 50, 100)

        # Weighted composite
        composite = (
            volume_score * self.WEIGHTS["volume"]
            + neg_score * self.WEIGHTS["neg_sentiment"]
            + rating_score * self.WEIGHTS["rating"]
            + trend_score * self.WEIGHTS["trend_accel"]
            + repeat_score * self.WEIGHTS["repeat_freq"]
            + keyword_score * self.WEIGHTS["biz_keywords"]
        )
        composite = round(min(composite, 100), 1)

        # Priority assignment
        if composite >= 90:
            priority = "P0"
        elif composite >= 70:
            priority = "P1"
        elif composite >= 40:
            priority = "P2"
        else:
            priority = "P3"

        return ImpactScore(
            theme_name=theme.theme_name,
            score=composite,
            priority=priority,
            volume_component=round(volume_score, 1),
            sentiment_component=round(neg_score, 1),
            rating_component=round(rating_score, 1),
            trend_component=round(trend_score, 1),
            repeat_component=round(repeat_score, 1),
            keyword_component=round(keyword_score, 1),
            breakdown=self.WEIGHTS,
        )
