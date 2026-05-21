"""
Trend Detection Agent (Agent 4)

Responsibilities:
  1. Group reviews by week and theme
  2. Calculate week-over-week volume and sentiment changes
  3. Detect spikes (>2σ from rolling mean)
  4. Flag release-correlated regressions
"""

import logging
import statistics
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from typing import List, Dict

from sqlalchemy.orm import Session

from app.models.database import Review, Sentiment, Theme, ReviewTheme
from app.schemas.intelligence import TrendSignal

logger = logging.getLogger(__name__)


class TrendDetectionAgent:
    """
    Agent 4 — Detects week-over-week trends and anomalies per theme.

    Uses statistical spike detection (>2σ) and version-change correlation.
    No LLM calls needed — pure computation.
    """

    def __init__(self, db: Session):
        self.db = db

    def detect(self) -> List[TrendSignal]:
        """Analyze trends for all themes."""
        themes = self.db.query(Theme).all()
        if not themes:
            logger.warning("No themes found — skipping trend detection")
            return []

        logger.info("Detecting trends for %d themes", len(themes))
        signals = []

        for theme in themes:
            signal = self._analyze_theme(theme)
            signals.append(signal)

        logger.info("Trend detection complete: %d signals", len(signals))
        return signals

    def _analyze_theme(self, theme: Theme) -> TrendSignal:
        """Compute trend signal for a single theme."""
        # Get review IDs for this theme
        review_ids = [
            rt.review_id
            for rt in self.db.query(ReviewTheme).filter(ReviewTheme.theme_id == theme.id).all()
        ]

        if not review_ids:
            return TrendSignal(theme_name=theme.theme_name)

        # Get reviews with dates
        reviews = self.db.query(Review).filter(Review.id.in_(review_ids)).all()
        sentiments = {
            s.review_id: s
            for s in self.db.query(Sentiment).filter(Sentiment.review_id.in_(review_ids)).all()
        }

        # Group by week
        now = datetime.now(timezone.utc)
        weekly_data = self._group_by_week(reviews, sentiments, now)

        # Current vs previous week
        current_week = weekly_data.get(0, {"count": 0, "avg_sentiment": 0.0})
        prev_week = weekly_data.get(1, {"count": 0, "avg_sentiment": 0.0})

        cur_vol = current_week["count"]
        prev_vol = prev_week["count"]
        vol_change = ((cur_vol - prev_vol) / max(prev_vol, 1)) * 100

        cur_sent = current_week["avg_sentiment"]
        prev_sent = prev_week["avg_sentiment"]
        sent_change = cur_sent - prev_sent

        # Spike detection using historical weeks
        historical_volumes = [weekly_data.get(w, {"count": 0})["count"] for w in range(1, 5)]
        is_spike = self._is_spike(cur_vol, historical_volumes)

        # Direction
        if is_spike:
            direction = "spike"
        elif vol_change > 15:
            direction = "rising"
        elif vol_change < -15:
            direction = "falling"
        else:
            direction = "stable"

        # Release correlation: check if version changed in current week reviews
        versions = set(r.app_version for r in reviews if r.app_version)
        release_correlated = len(versions) > 1

        return TrendSignal(
            theme_name=theme.theme_name,
            current_week_volume=cur_vol,
            previous_week_volume=prev_vol,
            volume_change_pct=round(vol_change, 1),
            current_avg_sentiment=round(cur_sent, 3),
            previous_avg_sentiment=round(prev_sent, 3),
            sentiment_change=round(sent_change, 3),
            is_spike=is_spike,
            direction=direction,
            release_correlated=release_correlated,
        )

    def _group_by_week(
        self, reviews: list, sentiments: dict, now: datetime
    ) -> Dict[int, dict]:
        """Group reviews by week offset (0 = current week)."""
        weekly: Dict[int, dict] = defaultdict(lambda: {"count": 0, "sentiment_sum": 0.0})

        for r in reviews:
            rd = r.review_date
            if rd.tzinfo is None:
                rd = rd.replace(tzinfo=timezone.utc)
            days_ago = (now - rd).days
            week_offset = days_ago // 7

            weekly[week_offset]["count"] += 1
            s = sentiments.get(r.id)
            if s:
                weekly[week_offset]["sentiment_sum"] += s.sentiment_score

        result = {}
        for week, data in weekly.items():
            result[week] = {
                "count": data["count"],
                "avg_sentiment": data["sentiment_sum"] / max(data["count"], 1),
            }
        return result

    @staticmethod
    def _is_spike(current: int, historical: List[int]) -> bool:
        """Detect if current volume is >2σ above historical mean."""
        if len(historical) < 2:
            return False
        mean = statistics.mean(historical)
        try:
            stdev = statistics.stdev(historical)
        except statistics.StatisticsError:
            return False
        if stdev == 0:
            return current > mean * 1.5
        return current > mean + 2 * stdev
