"""
GROWW AI Product Intelligence Copilot — FastAPI Application

Entry point for the backend server.
"""

import logging

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
    """Initialise database tables on first run."""
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    init_db()
    logger.info("Database initialised")


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
