"""
GROWW AI Product Intelligence Copilot — FastAPI Application

Entry point for the backend server.
"""

import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models.database import init_db
from app.api.routes import router

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI App ──────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "AI-native Product Intelligence Copilot that transforms GROWW app "
        "reviews into weekly executive pulses via multi-agent AI workflows."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(router)


# ── Startup Event ────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Initialise database tables on first run, then seed data if empty."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    init_db()
    logger.info("Database initialised")

    # If DB is empty (fresh deploy), auto-run the pipeline in background
    # so the dashboard has data without anyone needing to click a button
    _auto_seed_if_empty()


def _auto_seed_if_empty():
    """Trigger pipeline automatically if no reviews exist yet."""
    try:
        from app.models.database import SessionLocal, Review
        db = SessionLocal()
        count = db.query(Review).count()
        db.close()
        if count == 0:
            logger.info("DB is empty — auto-seeding pipeline on startup")
            thread = threading.Thread(target=_run_seed_pipeline, daemon=True)
            thread.start()
        else:
            logger.info("DB has %d reviews — skipping auto-seed", count)
    except Exception as exc:
        logger.warning("Auto-seed check failed: %s", exc)


def _run_seed_pipeline():
    """Run the full pipeline in a background thread on first startup."""
    try:
        from app.models.database import SessionLocal
        from app.services.pipeline_runner import PipelineRunner
        db = SessionLocal()
        runner = PipelineRunner(db)
        runner.run(app_id=settings.GROWW_APP_ID, weeks=settings.REVIEW_WEEKS)
        logger.info("Auto-seed pipeline completed successfully")
    except Exception as exc:
        logger.error("Auto-seed pipeline failed: %s", exc)
    finally:
        db.close()


# ── Root ─────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


# ── Top-level health alias (for Railway healthcheck) ─────────────────
@app.get("/health", tags=["System"])
def health_alias():
    """Alias so Railway's healthcheck works without the /api/v1 prefix."""
    return {"status": "healthy", "version": settings.APP_VERSION}
