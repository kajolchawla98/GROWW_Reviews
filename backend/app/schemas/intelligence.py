"""
Pydantic schemas for Phase 3 — Intelligence & Scoring.

Defines typed I/O contracts for:
  - Trend Detection Agent
  - Product Impact Scoring Agent
  - PM Copilot Recommendation Agent
  - Weekly Pulse Generator Agent
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Trend Schemas ────────────────────────────────────────────────────

class TrendSignal(BaseModel):
    """Output of the Trend Detection Agent for a single theme."""

    theme_name: str
    current_week_volume: int = 0
    previous_week_volume: int = 0
    volume_change_pct: float = 0.0
    current_avg_sentiment: float = 0.0
    previous_avg_sentiment: float = 0.0
    sentiment_change: float = 0.0
    is_spike: bool = False
    direction: str = "stable"  # rising | falling | stable | spike
    release_correlated: bool = False


# ── Impact Score Schemas ─────────────────────────────────────────────

class ImpactScore(BaseModel):
    """Output of the Product Impact Scoring Agent for a single theme."""

    theme_name: str
    score: float = Field(0.0, ge=0, le=100)
    priority: str = "P3"  # P0 | P1 | P2 | P3
    volume_component: float = 0.0
    sentiment_component: float = 0.0
    rating_component: float = 0.0
    trend_component: float = 0.0
    repeat_component: float = 0.0
    keyword_component: float = 0.0
    breakdown: dict = Field(default_factory=dict)


# ── Recommendation Schemas ───────────────────────────────────────────

class Recommendation(BaseModel):
    """Output of the PM Copilot Recommendation Agent."""

    theme_name: str
    title: str
    description: str
    priority: str = "P2"
    evidence_quotes: List[str] = Field(default_factory=list)
    impact_score: float = 0.0


# ── Pulse Schemas ────────────────────────────────────────────────────

class PulseReport(BaseModel):
    """Output of the Weekly Pulse Generator Agent."""

    pulse_id: str = ""
    generated_at: Optional[datetime] = None
    week_label: str = ""
    total_reviews: int = 0
    overall_sentiment: float = 0.0
    top_themes: List[dict] = Field(default_factory=list)
    key_quotes: List[str] = Field(default_factory=list)
    trends: List[dict] = Field(default_factory=list)
    recommendations: List[dict] = Field(default_factory=list)
    markdown_content: str = ""
