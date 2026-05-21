"""
Pydantic schemas for Phase 2 — Theme Classification & Sentiment Analysis.

These define the typed I/O contracts between agents.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


# ── Theme Schemas ────────────────────────────────────────────────────

class ThemeCluster(BaseModel):
    """Output of the Theme Classification Agent."""

    theme_id: str = Field(default="", description="Auto-generated UUID")
    theme_name: str = Field(..., description="Human-readable theme name")
    ai_summary: str = Field("", description="AI-generated summary of this theme")
    review_ids: List[str] = Field(default_factory=list, description="Review IDs in this theme")
    review_count: int = Field(0, description="Number of reviews in this theme")
    classification_confidence: float = Field(0.8, ge=0.0, le=1.0)


# ── Sentiment Schemas ────────────────────────────────────────────────

class SentimentAnnotation(BaseModel):
    """Output of the Sentiment & Emotion Agent for a single review."""

    review_id: str = Field(..., description="Review this annotation belongs to")
    sentiment: str = Field(..., description="positive | negative | neutral | mixed")
    sentiment_score: float = Field(0.0, ge=-1.0, le=1.0)
    emotion: str = Field("neutral", description="anger | frustration | satisfaction | delight | confusion | neutral")
    confidence: float = Field(0.7, ge=0.0, le=1.0)


# ── API Response Schemas ─────────────────────────────────────────────

class ThemeResponse(BaseModel):
    """API response for a single theme."""

    id: str
    theme_name: str
    ai_summary: str
    review_count: int
    classification_confidence: float
    sentiment_breakdown: Optional[dict] = None

    class Config:
        from_attributes = True


class SentimentResponse(BaseModel):
    """API response for sentiment data."""

    review_id: str
    sentiment: str
    sentiment_score: float
    emotion: str
    confidence: float

    class Config:
        from_attributes = True


class AnalysisSummary(BaseModel):
    """Summary returned after Phase 2 analysis completes."""

    pipeline_run_id: str
    themes_created: int
    reviews_classified: int
    sentiments_analyzed: int
    status: str
