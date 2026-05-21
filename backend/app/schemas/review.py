"""
Pydantic schemas for reviews and pipeline operations.

These define the API request/response contracts and the
typed inter-agent communication data structures.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ── Review Schemas ───────────────────────────────────────────────────

class ReviewRecord(BaseModel):
    """Internal representation of a single anonymized review."""

    review_id: str = Field(..., description="Unique review identifier")
    text: str = Field(..., description="Anonymized review text")
    rating: int = Field(..., ge=1, le=5, description="Star rating 1-5")
    date: datetime = Field(..., description="Review date")
    version: Optional[str] = Field(None, description="App version at time of review")
    language: str = Field("en", description="Review language code")
    word_count: int = Field(0, description="Word count of review text")

    class Config:
        from_attributes = True


class ReviewResponse(BaseModel):
    """API response for a single review."""

    id: str
    review_text: str
    rating: int
    review_date: datetime
    app_version: Optional[str] = None
    language: str = "en"
    word_count: int = 0
    ingested_at: datetime

    class Config:
        from_attributes = True


# ── Pipeline Schemas ─────────────────────────────────────────────────

class PipelineRunRequest(BaseModel):
    """Request body for triggering a pipeline run."""

    app_id: str = Field(
        default="com.nextbillion.groww",
        description="Google Play Store app ID",
    )
    weeks: int = Field(
        default=4,
        ge=1,
        le=12,
        description="Number of weeks of reviews to fetch",
    )


class PipelineRunResponse(BaseModel):
    """Immediate response after triggering a pipeline run."""

    pipeline_run_id: str
    status: str = "running"
    message: str = "Pipeline started successfully"


class PipelineStatusResponse(BaseModel):
    """Status of a pipeline run."""

    pipeline_run_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    review_count: int = 0
    error_log: Optional[str] = None

    class Config:
        from_attributes = True


# ── Summary Schemas ──────────────────────────────────────────────────

class IngestionSummary(BaseModel):
    """Summary returned after ingestion completes."""

    pipeline_run_id: str
    total_fetched: int
    new_reviews: int
    duplicates_skipped: int
    embeddings_created: int
    status: str
