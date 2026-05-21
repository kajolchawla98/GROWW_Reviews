"""
API routes for Phase 1 + 2 + 3.

Phase 3 additions:
  GET  /api/v1/trends                — Trend signals per theme
  GET  /api/v1/impact-scores         — Impact scores per theme
  GET  /api/v1/recommendations       — PM recommendations
  GET  /api/v1/pulses                — Weekly pulse reports
  GET  /api/v1/pulses/latest         — Latest pulse report
  GET  /api/v1/dashboard             — Aggregated dashboard data
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy import text, func
from sqlalchemy.orm import Session

from app.models.database import (
    get_db, Review, PipelineRun, Theme, ReviewTheme, Sentiment,
    TrendRecord, ImpactScoreRecord, RecommendationRecord, PulseRecord,
)
from app.schemas.review import (
    PipelineRunRequest, PipelineRunResponse, PipelineStatusResponse, ReviewResponse,
)
from app.services.pipeline_runner import PipelineRunner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


# ── Pipeline ─────────────────────────────────────────────────────────

def _run_pipeline_background(app_id: str, weeks: int, run_id: str):
    from app.models.database import SessionLocal
    db = SessionLocal()
    try:
        runner = PipelineRunner(db)
        runner.run(app_id=app_id, weeks=weeks, run_id=run_id)
    except Exception as exc:
        logger.error("Background pipeline failed: %s", exc)
    finally:
        db.close()


@router.post("/pipeline/run", response_model=PipelineRunResponse, status_code=202,
             summary="Trigger full pipeline", tags=["Pipeline"])
def trigger_pipeline(request: PipelineRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run = PipelineRun(status="queued", config={"app_id": request.app_id, "weeks": request.weeks})
    db.add(run); db.commit(); db.refresh(run)
    background_tasks.add_task(_run_pipeline_background, app_id=request.app_id, weeks=request.weeks, run_id=run.id)
    return PipelineRunResponse(pipeline_run_id=run.id, status="running", message="Pipeline started — poll /pipeline/status/{id}")


@router.get("/pipeline/status/{run_id}", response_model=PipelineStatusResponse,
            summary="Pipeline run status", tags=["Pipeline"])
def get_pipeline_status(run_id: str, db: Session = Depends(get_db)):
    run = db.query(PipelineRun).filter(PipelineRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Pipeline run not found")
    return PipelineStatusResponse(
        pipeline_run_id=run.id, status=run.status, started_at=run.started_at,
        completed_at=run.completed_at, review_count=run.review_count or 0, error_log=run.error_log,
    )


# ── Reviews ──────────────────────────────────────────────────────────

@router.get("/reviews", response_model=list[ReviewResponse], summary="List reviews", tags=["Reviews"])
def list_reviews(skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200),
                 min_rating: Optional[int] = Query(None, ge=1, le=5),
                 max_rating: Optional[int] = Query(None, ge=1, le=5), db: Session = Depends(get_db)):
    q = db.query(Review)
    if min_rating: q = q.filter(Review.rating >= min_rating)
    if max_rating: q = q.filter(Review.rating <= max_rating)
    return q.order_by(Review.review_date.desc()).offset(skip).limit(limit).all()


@router.get("/reviews/count", summary="Review count", tags=["Reviews"])
def review_count(db: Session = Depends(get_db)):
    return {"total_reviews": db.query(Review).count()}


# ── Themes ───────────────────────────────────────────────────────────

@router.get("/themes", summary="List themes with sentiment + impact", tags=["Themes"])
def list_themes(db: Session = Depends(get_db)):
    themes = db.query(Theme).order_by(Theme.review_count.desc()).all()
    result = []
    for theme in themes:
        review_ids = [rt.review_id for rt in db.query(ReviewTheme).filter(ReviewTheme.theme_id == theme.id).all()]
        sent_bk = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
        if review_ids:
            for s_type, s_count in db.query(Sentiment.sentiment, func.count(Sentiment.id)).filter(Sentiment.review_id.in_(review_ids)).group_by(Sentiment.sentiment).all():
                if s_type in sent_bk: sent_bk[s_type] = s_count

        impact = db.query(ImpactScoreRecord).filter(ImpactScoreRecord.theme_name == theme.theme_name).first()
        trend = db.query(TrendRecord).filter(TrendRecord.theme_name == theme.theme_name).first()

        result.append({
            "id": theme.id, "theme_name": theme.theme_name, "ai_summary": theme.ai_summary,
            "review_count": theme.review_count, "classification_confidence": theme.classification_confidence,
            "sentiment_breakdown": sent_bk,
            "impact_score": impact.score if impact else 0, "priority": impact.priority if impact else "P3",
            "trend_direction": trend.direction if trend else "stable",
            "volume_change_pct": trend.volume_change_pct if trend else 0,
        })
    return result


@router.get("/themes/{theme_id}/reviews", summary="Reviews in a theme", tags=["Themes"])
def theme_reviews(theme_id: str, skip: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    theme = db.query(Theme).filter(Theme.id == theme_id).first()
    if not theme: raise HTTPException(status_code=404, detail="Theme not found")
    review_ids = [rt.review_id for rt in db.query(ReviewTheme).filter(ReviewTheme.theme_id == theme_id).all()]
    reviews = db.query(Review).filter(Review.id.in_(review_ids)).order_by(Review.review_date.desc()).offset(skip).limit(limit).all()
    result = []
    for r in reviews:
        s = db.query(Sentiment).filter(Sentiment.review_id == r.id).first()
        result.append({
            "id": r.id, "review_text": r.review_text, "rating": r.rating,
            "review_date": r.review_date.isoformat(), "app_version": r.app_version,
            "word_count": r.word_count,
            "sentiment": s.sentiment if s else None, "sentiment_score": s.sentiment_score if s else None,
            "emotion": s.emotion if s else None,
        })
    return {"theme": theme.theme_name, "total": len(review_ids), "reviews": result}


# ── Sentiments ───────────────────────────────────────────────────────

@router.get("/sentiments/summary", summary="Sentiment summary", tags=["Sentiments"])
def sentiment_summary(db: Session = Depends(get_db)):
    total = db.query(Sentiment).count()
    sent = {s: c for s, c in db.query(Sentiment.sentiment, func.count(Sentiment.id)).group_by(Sentiment.sentiment).all()}
    emot = {e: c for e, c in db.query(Sentiment.emotion, func.count(Sentiment.id)).group_by(Sentiment.emotion).all()}
    avg_s = db.query(func.avg(Sentiment.sentiment_score)).scalar() or 0.0
    return {"total_annotated": total, "average_sentiment_score": round(float(avg_s), 3),
            "sentiment_distribution": sent, "emotion_distribution": emot}


# ── Trends (Phase 3) ────────────────────────────────────────────────

@router.get("/trends", summary="Trend signals", tags=["Intelligence"])
def list_trends(db: Session = Depends(get_db)):
    trends = db.query(TrendRecord).order_by(TrendRecord.volume_change_pct.desc()).all()
    return [
        {
            "theme_name": t.theme_name, "direction": t.direction,
            "current_week_volume": t.current_week_volume,
            "previous_week_volume": t.previous_week_volume,
            "volume_change_pct": t.volume_change_pct,
            "current_avg_sentiment": t.current_avg_sentiment,
            "sentiment_change": t.sentiment_change,
            "is_spike": t.is_spike, "release_correlated": t.release_correlated,
        }
        for t in trends
    ]


# ── Impact Scores (Phase 3) ─────────────────────────────────────────

@router.get("/impact-scores", summary="Impact scores", tags=["Intelligence"])
def list_impact_scores(db: Session = Depends(get_db)):
    scores = db.query(ImpactScoreRecord).order_by(ImpactScoreRecord.score.desc()).all()
    return [
        {
            "theme_name": s.theme_name, "score": s.score, "priority": s.priority,
            "components": {
                "volume": s.volume_component, "sentiment": s.sentiment_component,
                "rating": s.rating_component, "trend": s.trend_component,
                "repeat": s.repeat_component, "keyword": s.keyword_component,
            },
        }
        for s in scores
    ]


# ── Recommendations (Phase 3) ───────────────────────────────────────

@router.get("/recommendations", summary="PM recommendations", tags=["Intelligence"])
def list_recommendations(db: Session = Depends(get_db)):
    recs = db.query(RecommendationRecord).order_by(RecommendationRecord.impact_score.desc()).all()
    return [
        {
            "theme_name": r.theme_name, "title": r.title, "description": r.description,
            "priority": r.priority, "evidence_quotes": r.evidence_quotes or [],
            "impact_score": r.impact_score,
        }
        for r in recs
    ]


# ── Pulses (Phase 3) ────────────────────────────────────────────────
    
@router.post("/pulses/{pulse_id}/publish", summary="Publish pulse via MCP", tags=["Publishing"])
async def publish_pulse(
    pulse_id: str, 
    target: str = Query("both", description="Target platform: google_docs, gmail, or both"),
    db: Session = Depends(get_db)
):
    from app.agents.publishing_agent import PublishingAgent

    # If pulse_id is "latest" or the specific ID isn't found, fall back to latest pulse
    pulse = db.query(PulseRecord).filter(
        (PulseRecord.id == pulse_id) | (PulseRecord.pulse_id == pulse_id)
    ).first()
    if not pulse:
        pulse = db.query(PulseRecord).order_by(PulseRecord.generated_at.desc()).first()
    if not pulse:
        raise HTTPException(status_code=404, detail="No pulse report found — run the pipeline first")

    agent = PublishingAgent(db)
    try:
        result = await agent.publish_pulse(pulse.pulse_id or pulse.id, target=target)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/pulses/latest", summary="Latest pulse report", tags=["Intelligence"])
def latest_pulse(db: Session = Depends(get_db)):
    pulse = db.query(PulseRecord).order_by(PulseRecord.generated_at.desc()).first()
    if not pulse:
        raise HTTPException(status_code=404, detail="No pulse report found — run the pipeline first")
    return {
        "pulse_id": pulse.id, "week_label": pulse.week_label,
        "total_reviews": pulse.total_reviews, "overall_sentiment": pulse.overall_sentiment,
        "top_themes": pulse.top_themes, "key_quotes": pulse.key_quotes,
        "trends": pulse.trends, "recommendations": pulse.recommendations,
        "markdown_content": pulse.markdown_content,
        "generated_at": pulse.generated_at.isoformat() if pulse.generated_at else None,
    }


# ── Dashboard Aggregate (Phase 4 support) ────────────────────────────

@router.get("/dashboard", summary="Aggregated dashboard data", tags=["Dashboard"])
def dashboard_data(db: Session = Depends(get_db)):
    """Single endpoint returning all data needed for the executive dashboard."""
    total_reviews = db.query(Review).count()
    avg_rating = db.query(func.avg(Review.rating)).scalar() or 0.0
    avg_sentiment = db.query(func.avg(Sentiment.sentiment_score)).scalar() or 0.0

    # Rating distribution
    rating_dist = {str(r): c for r, c in db.query(Review.rating, func.count(Review.id)).group_by(Review.rating).all()}

    # Sentiment distribution
    sent_dist = {s: c for s, c in db.query(Sentiment.sentiment, func.count(Sentiment.id)).group_by(Sentiment.sentiment).all()}
    emot_dist = {e: c for e, c in db.query(Sentiment.emotion, func.count(Sentiment.id)).group_by(Sentiment.emotion).all()}

    # Themes with impact + trend
    themes = db.query(Theme).order_by(Theme.review_count.desc()).all()
    theme_data = []
    for t in themes:
        impact = db.query(ImpactScoreRecord).filter(ImpactScoreRecord.theme_name == t.theme_name).first()
        trend = db.query(TrendRecord).filter(TrendRecord.theme_name == t.theme_name).first()
        review_ids = [rt.review_id for rt in db.query(ReviewTheme).filter(ReviewTheme.theme_id == t.id).all()]
        sent_bk = {"positive": 0, "negative": 0, "neutral": 0, "mixed": 0}
        if review_ids:
            for s_type, s_count in db.query(Sentiment.sentiment, func.count(Sentiment.id)).filter(Sentiment.review_id.in_(review_ids)).group_by(Sentiment.sentiment).all():
                if s_type in sent_bk: sent_bk[s_type] = s_count

        theme_data.append({
            "id": t.id, "name": t.theme_name, "summary": t.ai_summary,
            "review_count": t.review_count,
            "impact_score": impact.score if impact else 0,
            "priority": impact.priority if impact else "P3",
            "trend_direction": trend.direction if trend else "stable",
            "volume_change": trend.volume_change_pct if trend else 0,
            "is_spike": trend.is_spike if trend else False,
            "sentiment_breakdown": sent_bk,
        })

    # Critical issues
    critical = db.query(ImpactScoreRecord).filter(ImpactScoreRecord.priority.in_(["P0", "P1"])).count()

    # Recommendations
    recs = db.query(RecommendationRecord).order_by(RecommendationRecord.impact_score.desc()).all()
    rec_data = [{"theme": r.theme_name, "title": r.title, "description": r.description,
                 "priority": r.priority, "evidence": r.evidence_quotes or [], "score": r.impact_score} for r in recs]

    # Latest pulse
    pulse = db.query(PulseRecord).order_by(PulseRecord.generated_at.desc()).first()

    # Recent reviews for replay
    recent_reviews = db.query(Review).order_by(Review.review_date.desc()).limit(20).all()
    review_replay = []
    for r in recent_reviews:
        s = db.query(Sentiment).filter(Sentiment.review_id == r.id).first()
        rt = db.query(ReviewTheme).filter(ReviewTheme.review_id == r.id).first()
        theme_name = None
        if rt:
            th = db.query(Theme).filter(Theme.id == rt.theme_id).first()
            theme_name = th.theme_name if th else None
        review_replay.append({
            "id": r.id, "text": r.review_text, "rating": r.rating,
            "date": r.review_date.isoformat(), "version": r.app_version,
            "sentiment": s.sentiment if s else None, "emotion": s.emotion if s else None,
            "sentiment_score": s.sentiment_score if s else 0,
            "theme": theme_name,
        })

    return {
        "summary": {
            "total_reviews": total_reviews, "average_rating": round(float(avg_rating), 2),
            "average_sentiment": round(float(avg_sentiment), 3), "critical_issues": critical,
            "rating_distribution": rating_dist, "sentiment_distribution": sent_dist,
            "emotion_distribution": emot_dist,
        },
        "themes": theme_data,
        "recommendations": rec_data,
        "review_replay": review_replay,
        "pulse": {
            "pulse_id": pulse.pulse_id if pulse else None,
            "week_label": pulse.week_label if pulse else None,
            "markdown": pulse.markdown_content if pulse else None,
            "generated_at": pulse.generated_at.isoformat() if pulse else None,
        } if pulse else None,
    }


# ── System ───────────────────────────────────────────────────────────

@router.get("/groq/status", summary="Groq rate limiter", tags=["System"])
def groq_status():
    from app.services.groq_client import groq_limiter
    return groq_limiter.status


@router.get("/health", summary="Health check", tags=["System"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1")); db_status = "connected"
    except Exception:
        db_status = "error"

    # Include last pipeline run info so the frontend can show staleness
    last_run = db.query(PipelineRun).order_by(PipelineRun.started_at.desc()).first()
    last_pulse = db.query(PulseRecord).order_by(PulseRecord.generated_at.desc()).first()

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "version": "0.3.0",
        "last_pipeline_run": {
            "id": last_run.id if last_run else None,
            "status": last_run.status if last_run else None,
            "started_at": last_run.started_at.isoformat() if last_run and last_run.started_at else None,
            "completed_at": last_run.completed_at.isoformat() if last_run and last_run.completed_at else None,
            "error_log": last_run.error_log if last_run else None,
        } if last_run else None,
        "last_pulse_generated_at": last_pulse.generated_at.isoformat() if last_pulse and last_pulse.generated_at else None,
    }
