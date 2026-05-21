"""
Application configuration.
Loads settings from environment variables / .env file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """Central configuration for the GROWW AI Copilot backend."""

    # ── App ──────────────────────────────────────────────────────────
    APP_NAME: str = "GROWW AI Product Intelligence Copilot"
    APP_VERSION: str = "0.2.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ── Google Play Store ────────────────────────────────────────────
    GROWW_APP_ID: str = os.getenv("GROWW_APP_ID", "com.nextbillion.groww")
    REVIEW_WEEKS: int = int(os.getenv("REVIEW_WEEKS", "4"))
    REVIEW_LANGUAGE: str = os.getenv("REVIEW_LANGUAGE", "en")
    REVIEW_COUNTRY: str = os.getenv("REVIEW_COUNTRY", "in")
    MAX_REVIEWS: int = int(os.getenv("MAX_REVIEWS", "1000"))
    MIN_WORD_COUNT: int = int(os.getenv("MIN_WORD_COUNT", "6"))

    # ── Database ─────────────────────────────────────────────────────
    _raw_db_url = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{Path(__file__).resolve().parent.parent / 'data' / 'groww_copilot.db'}",
    )
    # Handle SQLAlchemy 1.4+ requirement for postgresql:// instead of postgres://
    DATABASE_URL: str = _raw_db_url.replace("postgres://", "postgresql://", 1) if _raw_db_url.startswith("postgres://") else _raw_db_url


    # ── Groq LLM ─────────────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    GROQ_MODEL_LARGE: str = os.getenv("GROQ_MODEL_LARGE", "llama-3.3-70b-versatile")

    # Groq rate limits (free tier: 30 RPM, 14400 RPD, 6000 TPM)
    GROQ_RPM: int = int(os.getenv("GROQ_RPM", "28"))       # requests per minute (keep below 30)
    GROQ_RPD: int = int(os.getenv("GROQ_RPD", "14000"))     # requests per day
    GROQ_TPM: int = int(os.getenv("GROQ_TPM", "5500"))      # tokens per minute (keep below 6000)

    # ── Vector Store (ChromaDB) ──────────────────────────────────────
    CHROMA_PERSIST_DIR: str = os.getenv(
        "CHROMA_PERSIST_DIR",
        str(Path(__file__).resolve().parent.parent / "data" / "chroma"),
    )
    CHROMA_COLLECTION: str = os.getenv("CHROMA_COLLECTION", "groww_reviews")

    # ── Pipeline ─────────────────────────────────────────────────────
    BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "50"))
    LLM_BATCH_SIZE: int = int(os.getenv("LLM_BATCH_SIZE", "25"))

    # ── Phase 5: Publishing ──────────────────────────────────────────
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "https://saksham-mcp-server-production-0909.up.railway.app")
    PUBLISH_DOC_ID: str = os.getenv("PUBLISH_DOC_ID", "")
    PUBLISH_EMAIL_TO: str = os.getenv("PUBLISH_EMAIL_TO", "pm-team@groww.in")


settings = Settings()
