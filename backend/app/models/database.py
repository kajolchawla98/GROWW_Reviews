"""
SQLAlchemy database models and session management.

Tables:
  Phase 1: reviews, pipeline_runs
  Phase 2: themes, review_themes, sentiments
  Phase 3: trends, impact_scores, recommendations, pulses
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    JSON,
    ForeignKey,
    create_engine,
    CheckConstraint,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

from app.config import settings

# ── Engine & Session ─────────────────────────────────────────────────
if settings.DATABASE_URL.startswith("sqlite"):
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
    echo=False,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Phase 1 Models ───────────────────────────────────────────────────

class Review(Base):
    """Anonymized app review from Google Play Store."""

    __tablename__ = "reviews"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_text = Column(Text, nullable=False)
    rating = Column(Integer, CheckConstraint("rating BETWEEN 1 AND 5"), nullable=False)
    review_date = Column(DateTime, nullable=False)
    app_version = Column(String(20), nullable=True)
    language = Column(String(10), default="en")
    word_count = Column(Integer, default=0)
    source_review_id = Column(String(128), unique=True, nullable=False)
    pipeline_run_id = Column(String(64), nullable=True)
    ingested_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    sentiments = relationship("Sentiment", back_populates="review", cascade="all, delete-orphan")
    theme_links = relationship("ReviewTheme", back_populates="review", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Review id={self.id} rating={self.rating} words={self.word_count}>"


class PipelineRun(Base):
    """Tracks each execution of the pipeline."""

    __tablename__ = "pipeline_runs"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="running")
    config = Column(JSON, nullable=True)
    review_count = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<PipelineRun id={self.id} status={self.status}>"


# ── Phase 2 Models ───────────────────────────────────────────────────

class Theme(Base):
    """A product theme discovered by the Theme Classification Agent."""

    __tablename__ = "themes"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = Column(String(64), nullable=True)
    theme_name = Column(String(200), nullable=False)
    ai_summary = Column(Text, nullable=True)
    review_count = Column(Integer, default=0)
    classification_confidence = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    review_links = relationship("ReviewTheme", back_populates="theme", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Theme name={self.theme_name} reviews={self.review_count}>"


class ReviewTheme(Base):
    """Many-to-many mapping between reviews and themes."""

    __tablename__ = "review_themes"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String(64), ForeignKey("reviews.id"), nullable=False)
    theme_id = Column(String(64), ForeignKey("themes.id"), nullable=False)
    confidence = Column(Float, default=0.8)

    review = relationship("Review", back_populates="theme_links")
    theme = relationship("Theme", back_populates="review_links")


class Sentiment(Base):
    """Sentiment and emotion annotation for a review."""

    __tablename__ = "sentiments"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id = Column(String(64), ForeignKey("reviews.id"), nullable=False)
    pipeline_run_id = Column(String(64), nullable=True)
    sentiment = Column(String(20), nullable=False)
    sentiment_score = Column(Float, default=0.0)
    emotion = Column(String(30), nullable=True)
    confidence = Column(Float, default=0.7)

    review = relationship("Review", back_populates="sentiments")

    def __repr__(self) -> str:
        return f"<Sentiment review={self.review_id} sentiment={self.sentiment}>"


# ── Phase 3 Models ───────────────────────────────────────────────────

class TrendRecord(Base):
    """Week-over-week trend signal for a theme."""

    __tablename__ = "trends"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = Column(String(64), nullable=True)
    theme_name = Column(String(200), nullable=False)
    current_week_volume = Column(Integer, default=0)
    previous_week_volume = Column(Integer, default=0)
    volume_change_pct = Column(Float, default=0.0)
    current_avg_sentiment = Column(Float, default=0.0)
    previous_avg_sentiment = Column(Float, default=0.0)
    sentiment_change = Column(Float, default=0.0)
    is_spike = Column(Boolean, default=False)
    direction = Column(String(20), default="stable")
    release_correlated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ImpactScoreRecord(Base):
    """Product impact score for a theme."""

    __tablename__ = "impact_scores"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = Column(String(64), nullable=True)
    theme_name = Column(String(200), nullable=False)
    score = Column(Float, default=0.0)
    priority = Column(String(5), default="P3")
    volume_component = Column(Float, default=0.0)
    sentiment_component = Column(Float, default=0.0)
    rating_component = Column(Float, default=0.0)
    trend_component = Column(Float, default=0.0)
    repeat_component = Column(Float, default=0.0)
    keyword_component = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RecommendationRecord(Base):
    """PM recommendation for a theme."""

    __tablename__ = "recommendations"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = Column(String(64), nullable=True)
    theme_name = Column(String(200), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(5), default="P2")
    evidence_quotes = Column(JSON, nullable=True)
    impact_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PulseRecord(Base):
    """Weekly pulse report."""

    __tablename__ = "pulses"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    pipeline_run_id = Column(String(64), nullable=True)
    pulse_id = Column(String(100), nullable=True)
    week_label = Column(String(100), nullable=True)
    total_reviews = Column(Integer, default=0)
    overall_sentiment = Column(Float, default=0.0)
    top_themes = Column(JSON, nullable=True)
    key_quotes = Column(JSON, nullable=True)
    trends = Column(JSON, nullable=True)
    recommendations = Column(JSON, nullable=True)
    markdown_content = Column(Text, nullable=True)
    generated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── DB init helper ───────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables that don't already exist."""
    Base.metadata.create_all(bind=engine)
