"""
Weekly Pulse Generator Agent (Agent 7)

Responsibilities:
  1. Compile top 3 themes by impact score
  2. Select representative anonymized quotes
  3. Assemble trend changes, scores, recommendations
  4. Generate markdown weekly pulse report
"""

import logging
from datetime import datetime, timezone
from typing import List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import Review, Sentiment
from app.schemas.intelligence import (
    TrendSignal, ImpactScore, Recommendation, PulseReport,
)

logger = logging.getLogger(__name__)


class WeeklyPulseGeneratorAgent:
    """
    Agent 7 — Compiles all intelligence into a one-page weekly pulse.

    Produces both a structured PulseReport and a formatted Markdown string.
    """

    def __init__(self, db: Session):
        self.db = db

    def generate(
        self,
        trends: List[TrendSignal],
        scores: List[ImpactScore],
        recommendations: List[Recommendation],
    ) -> PulseReport:
        """Generate the weekly pulse report."""
        now = datetime.now(timezone.utc)
        week_label = now.strftime("Week of %B %d, %Y")

        total_reviews = self.db.query(Review).count()
        avg_sentiment = self.db.query(func.avg(Sentiment.sentiment_score)).scalar() or 0.0

        # Top 3 themes by impact
        top_scores = sorted(scores, key=lambda s: s.score, reverse=True)[:3]

        # Build top themes data
        top_themes = []
        for s in top_scores:
            trend = next((t for t in trends if t.theme_name == s.theme_name), None)
            rec = next((r for r in recommendations if r.theme_name == s.theme_name), None)
            top_themes.append({
                "theme_name": s.theme_name,
                "impact_score": s.score,
                "priority": s.priority,
                "volume_change": trend.volume_change_pct if trend else 0,
                "direction": trend.direction if trend else "stable",
                "recommendation": rec.title if rec else "No recommendation",
            })

        # Key quotes from high-impact themes
        key_quotes = self._get_representative_quotes(top_scores)

        # Trend summaries
        trend_data = [
            {
                "theme": t.theme_name,
                "direction": t.direction,
                "volume_change": t.volume_change_pct,
                "sentiment_change": t.sentiment_change,
                "is_spike": t.is_spike,
            }
            for t in trends
        ]

        # Recommendation summaries
        rec_data = [
            {
                "theme": r.theme_name,
                "title": r.title,
                "priority": r.priority,
                "impact_score": r.impact_score,
            }
            for r in recommendations
        ]

        # Generate markdown
        markdown = self._render_markdown(
            week_label, total_reviews, avg_sentiment,
            top_themes, key_quotes, trend_data, rec_data,
        )

        pulse = PulseReport(
            pulse_id=f"pulse-{now.strftime('%Y%m%d')}",
            generated_at=now,
            week_label=week_label,
            total_reviews=total_reviews,
            overall_sentiment=round(float(avg_sentiment), 3),
            top_themes=top_themes,
            key_quotes=key_quotes,
            trends=trend_data,
            recommendations=rec_data,
            markdown_content=markdown,
        )

        logger.info("Weekly pulse generated: %s (%d reviews)", week_label, total_reviews)
        return pulse

    def _get_representative_quotes(self, top_scores: List[ImpactScore]) -> List[str]:
        """Get 3 representative review quotes from top themes."""
        quotes = []
        for s in top_scores[:3]:
            review = (
                self.db.query(Review)
                .filter(Review.review_text.isnot(None))
                .order_by(Review.rating.asc())
                .first()
            )
            if review:
                text = review.review_text[:150]
                quotes.append(f"[{review.rating}★] \"{text}\"")
        return quotes

    def _render_markdown(
        self, week_label, total_reviews, avg_sentiment,
        top_themes, key_quotes, trends, recommendations,
    ) -> str:
        """Render the pulse as formatted markdown."""
        sentiment_emoji = "🟢" if avg_sentiment > 0.2 else "🔴" if avg_sentiment < -0.2 else "🟡"

        md = f"""# 📊 GROWW Weekly Product Pulse
## {week_label}

---

### Executive Summary

| Metric | Value |
|--------|-------|
| Total Reviews Analyzed | {total_reviews} |
| Overall Sentiment | {sentiment_emoji} {avg_sentiment:.2f} |
| Critical Issues (P0/P1) | {sum(1 for t in top_themes if t['priority'] in ('P0', 'P1'))} |

---

### 🔥 Top Issues by Impact

"""
        for i, t in enumerate(top_themes, 1):
            arrow = "↑" if t["direction"] == "rising" else "↓" if t["direction"] == "falling" else "→"
            md += f"""**{i}. {t['theme_name']}** — {t['priority']} (Score: {t['impact_score']})
- Trend: {arrow} {t['volume_change']:+.1f}% volume change
- Action: {t['recommendation']}

"""

        md += """---

### 💬 Key User Voices

"""
        for q in key_quotes:
            md += f"> {q}\n\n"

        md += """---

### 📈 Trend Signals

| Theme | Direction | Volume Δ | Sentiment Δ | Spike? |
|-------|-----------|----------|-------------|--------|
"""
        for t in trends:
            spike = "⚠️ YES" if t["is_spike"] else "No"
            md += f"| {t['theme']} | {t['direction']} | {t['volume_change']:+.1f}% | {t['sentiment_change']:+.3f} | {spike} |\n"

        md += """
---

### 🎯 Recommendations

"""
        for r in recommendations:
            md += f"**[{r['priority']}] {r['title']}**\n"
            md += f"- Theme: {r['theme']} | Impact: {r['impact_score']}\n\n"

        md += "\n---\n*Generated automatically by GROWW AI Product Intelligence Copilot*\n"
        return md
