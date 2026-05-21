"""
Pipeline Runner (v3) — orchestrates the full multi-agent pipeline.

Phase 1: Review Ingestion Agent
Phase 2: Theme Classification + Sentiment Analysis
Phase 3: Trend Detection + Impact Scoring + Recommendations + Pulse
"""

import logging
from datetime import datetime, timezone
from typing import Set, List

from sqlalchemy.orm import Session

from app.agents.ingestion_agent import ReviewIngestionAgent
from app.agents.theme_agent import ThemeClassificationAgent
from app.agents.sentiment_agent import SentimentEmotionAgent
from app.agents.trend_agent import TrendDetectionAgent
from app.agents.impact_agent import ProductImpactScoringAgent
from app.agents.recommendation_agent import PMCopilotAgent
from app.agents.pulse_agent import WeeklyPulseGeneratorAgent
from app.models.database import (
    Review, PipelineRun, Theme, ReviewTheme, Sentiment,
    TrendRecord, ImpactScoreRecord, RecommendationRecord, PulseRecord,
)
from app.schemas.review import ReviewRecord
from app.schemas.analysis import ThemeCluster, SentimentAnnotation
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class PipelineRunner:
    """
    Orchestrates the end-to-end pipeline (Phases 1–3).

    Pipeline flow:
      Phase 1: Ingestion → Dedup → Persist → Embed
      Phase 2: Theme Classification + Sentiment Analysis
      Phase 3: Trend Detection → Impact Scoring → Recommendations → Pulse
    """

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_agent = ReviewIngestionAgent()
        self.theme_agent = ThemeClassificationAgent()
        self.sentiment_agent = SentimentEmotionAgent()
        self.vector_store = VectorStoreService()

    def run(self, app_id: str = "com.nextbillion.groww", weeks: int = 4) -> dict:
        """Execute the full pipeline."""
        run = PipelineRun(
            status="running",
            config={"app_id": app_id, "weeks": weeks, "phase": "1+2+3"},
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        logger.info("Pipeline run started: %s", run.id)

        try:
            # ── PHASE 1 ─────────────────────────────────────────────
            reviews = self.ingestion_agent.fetch_reviews(app_id=app_id, weeks=weeks)
            total_fetched = len(reviews)

            existing_ids = self._get_existing_review_ids()
            new_reviews = self.ingestion_agent.deduplicate(reviews, existing_ids)
            duplicates_skipped = total_fetched - len(new_reviews)

            self._persist_reviews(new_reviews, run.id)
            embeddings_created = self._upsert_embeddings(new_reviews)
            logger.info("Phase 1 done: %d new, %d dupes", len(new_reviews), duplicates_skipped)

            all_reviews = self._load_all_reviews()

            # ── PHASE 2 ─────────────────────────────────────────────
            logger.info("Phase 2: Theme + Sentiment for %d reviews", len(all_reviews))
            themes = self.theme_agent.classify(all_reviews)
            sentiments = self.sentiment_agent.analyze(all_reviews)

            self._persist_themes(themes, all_reviews, run.id)
            self._persist_sentiments(sentiments, run.id)

            # ── PHASE 3 ─────────────────────────────────────────────
            logger.info("Phase 3: Trends → Impact → Recommendations → Pulse")

            trend_agent = TrendDetectionAgent(self.db)
            trends = trend_agent.detect()
            self._persist_trends(trends, run.id)

            impact_agent = ProductImpactScoringAgent(self.db)
            scores = impact_agent.score(trends)
            self._persist_impact_scores(scores, run.id)

            rec_agent = PMCopilotAgent(self.db)
            recommendations = rec_agent.recommend(scores)
            self._persist_recommendations(recommendations, run.id)

            pulse_agent = WeeklyPulseGeneratorAgent(self.db)
            pulse = pulse_agent.generate(trends, scores, recommendations)
            self._persist_pulse(pulse, run.id)

            # ── Complete ─────────────────────────────────────────────
            run.status = "completed"
            run.completed_at = datetime.now(timezone.utc)
            run.review_count = len(new_reviews)
            self.db.commit()

            summary = {
                "pipeline_run_id": run.id,
                "phase1": {"new_reviews": len(new_reviews), "embeddings": embeddings_created},
                "phase2": {"themes": len(themes), "sentiments": len(sentiments)},
                "phase3": {
                    "trends": len(trends),
                    "impact_scores": len(scores),
                    "recommendations": len(recommendations),
                    "pulse_generated": True,
                },
                "status": "completed",
            }
            logger.info("Pipeline completed: %s", summary)
            return summary

        except Exception as exc:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            run.error_log = str(exc)
            self.db.commit()
            logger.error("Pipeline failed: %s", exc, exc_info=True)
            raise

    # ── Phase 1 helpers ──────────────────────────────────────────────

    def _get_existing_review_ids(self) -> Set[str]:
        return {r[0] for r in self.db.query(Review.source_review_id).all()}

    def _persist_reviews(self, reviews: List[ReviewRecord], run_id: str):
        objs = [
            Review(
                review_text=r.text, rating=r.rating, review_date=r.date,
                app_version=r.version, language=r.language,
                word_count=r.word_count, source_review_id=r.review_id,
                pipeline_run_id=run_id,
            )
            for r in reviews
        ]
        self.db.bulk_save_objects(objs)
        self.db.commit()

    def _upsert_embeddings(self, reviews: List[ReviewRecord]) -> int:
        if not reviews:
            return 0
        return self.vector_store.add_reviews(
            [r.review_id for r in reviews],
            [r.text for r in reviews],
            [{"rating": r.rating, "date": r.date.isoformat(), "version": r.version or ""} for r in reviews],
        )

    def _load_all_reviews(self) -> List[ReviewRecord]:
        return [
            ReviewRecord(
                review_id=r.source_review_id, text=r.review_text,
                rating=r.rating, date=r.review_date,
                version=r.app_version, language=r.language or "en",
                word_count=r.word_count or 0,
            )
            for r in self.db.query(Review).all()
        ]

    # ── Phase 2 helpers ──────────────────────────────────────────────

    def _persist_themes(self, themes, reviews, run_id):
        self.db.query(ReviewTheme).delete()
        self.db.query(Theme).delete()
        self.db.commit()

        source_to_db = {r.source_review_id: r.id for r in self.db.query(Review).all()}

        for cluster in themes:
            theme = Theme(
                pipeline_run_id=run_id, theme_name=cluster.theme_name,
                ai_summary=cluster.ai_summary, review_count=cluster.review_count,
                classification_confidence=cluster.classification_confidence,
            )
            self.db.add(theme)
            self.db.flush()
            for rid in cluster.review_ids:
                db_id = source_to_db.get(rid)
                if db_id:
                    self.db.add(ReviewTheme(review_id=db_id, theme_id=theme.id, confidence=cluster.classification_confidence))
        self.db.commit()

    def _persist_sentiments(self, sentiments, run_id):
        self.db.query(Sentiment).delete()
        self.db.commit()
        source_to_db = {r.source_review_id: r.id for r in self.db.query(Review).all()}
        objs = []
        for s in sentiments:
            db_id = source_to_db.get(s.review_id)
            if db_id:
                objs.append(Sentiment(
                    review_id=db_id, pipeline_run_id=run_id,
                    sentiment=s.sentiment, sentiment_score=s.sentiment_score,
                    emotion=s.emotion, confidence=s.confidence,
                ))
        self.db.bulk_save_objects(objs)
        self.db.commit()

    # ── Phase 3 helpers ──────────────────────────────────────────────

    def _persist_trends(self, trends, run_id):
        self.db.query(TrendRecord).delete()
        self.db.commit()
        for t in trends:
            self.db.add(TrendRecord(
                pipeline_run_id=run_id, theme_name=t.theme_name,
                current_week_volume=t.current_week_volume,
                previous_week_volume=t.previous_week_volume,
                volume_change_pct=t.volume_change_pct,
                current_avg_sentiment=t.current_avg_sentiment,
                previous_avg_sentiment=t.previous_avg_sentiment,
                sentiment_change=t.sentiment_change,
                is_spike=t.is_spike, direction=t.direction,
                release_correlated=t.release_correlated,
            ))
        self.db.commit()

    def _persist_impact_scores(self, scores, run_id):
        self.db.query(ImpactScoreRecord).delete()
        self.db.commit()
        for s in scores:
            self.db.add(ImpactScoreRecord(
                pipeline_run_id=run_id, theme_name=s.theme_name,
                score=s.score, priority=s.priority,
                volume_component=s.volume_component,
                sentiment_component=s.sentiment_component,
                rating_component=s.rating_component,
                trend_component=s.trend_component,
                repeat_component=s.repeat_component,
                keyword_component=s.keyword_component,
            ))
        self.db.commit()

    def _persist_recommendations(self, recs, run_id):
        self.db.query(RecommendationRecord).delete()
        self.db.commit()
        for r in recs:
            self.db.add(RecommendationRecord(
                pipeline_run_id=run_id, theme_name=r.theme_name,
                title=r.title, description=r.description,
                priority=r.priority, evidence_quotes=r.evidence_quotes,
                impact_score=r.impact_score,
            ))
        self.db.commit()

    def _persist_pulse(self, pulse, run_id):
        self.db.query(PulseRecord).delete()
        self.db.commit()
        self.db.add(PulseRecord(
            pipeline_run_id=run_id, pulse_id=pulse.pulse_id,
            week_label=pulse.week_label, total_reviews=pulse.total_reviews,
            overall_sentiment=pulse.overall_sentiment,
            top_themes=pulse.top_themes, key_quotes=pulse.key_quotes,
            trends=pulse.trends, recommendations=pulse.recommendations,
            markdown_content=pulse.markdown_content,
        ))
        self.db.commit()
