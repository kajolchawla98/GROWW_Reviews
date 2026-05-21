"""
Review Ingestion Agent (Agent 1)

Responsibilities:
  1. Fetch public Google Play Store reviews for the GROWW app
  2. Normalize: remove emojis, filter non-English, require ≥6 words
  3. Strip PII (emails, phone numbers, names)
  4. Deduplicate reviews against existing database records
  5. Cap at MAX_REVIEWS (default 1000)
"""

import re
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Set

from google_play_scraper import Sort, reviews as gps_reviews

from app.config import settings
from app.schemas.review import ReviewRecord

logger = logging.getLogger(__name__)

# ── Patterns ─────────────────────────────────────────────────────────
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
NAME_PATTERN = re.compile(
    r"\b(?:Mr|Mrs|Ms|Dr|Shri|Smt)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
)

# Broad emoji pattern covering most Unicode emoji ranges
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"  # enclosed characters
    "\U0001F900-\U0001F9FF"  # supplemental symbols
    "\U0001FA00-\U0001FA6F"  # chess symbols
    "\U0001FA70-\U0001FAFF"  # symbols extended-A
    "\U00002600-\U000026FF"  # misc symbols
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero width joiner
    "\U00002B50"             # star
    "\U00002764"             # heart
    "\U0000203C-\U0000303D"  # misc
    "]+",
    flags=re.UNICODE,
)

# Non-Latin script detector (Hindi, Arabic, Chinese, etc.)
NON_LATIN_PATTERN = re.compile(
    r"[\u0900-\u097F"   # Devanagari (Hindi)
    r"\u0600-\u06FF"    # Arabic
    r"\u4E00-\u9FFF"    # CJK (Chinese)
    r"\u3040-\u309F"    # Hiragana (Japanese)
    r"\u30A0-\u30FF"    # Katakana
    r"\uAC00-\uD7AF"    # Hangul (Korean)
    r"\u0B80-\u0BFF"    # Tamil
    r"\u0C00-\u0C7F"    # Telugu
    r"\u0A80-\u0AFF"    # Gujarati
    r"\u0A00-\u0A7F"    # Gurmukhi (Punjabi)
    r"\u0B00-\u0B7F"    # Oriya
    r"\u0980-\u09FF"    # Bengali
    r"\u0D00-\u0D7F"    # Malayalam
    r"\u0C80-\u0CFF"    # Kannada
    r"]"
)


class ReviewIngestionAgent:
    """
    Agent 1 — Fetches, cleans, normalizes, and deduplicates GROWW reviews.

    Normalization rules:
      - Remove all emojis
      - Reject reviews with non-Latin (non-English) characters
      - Require minimum 6 words after cleaning
      - Cap total reviews at MAX_REVIEWS (1000)
    """

    def __init__(self):
        self.app_id: str = settings.GROWW_APP_ID
        self.language: str = settings.REVIEW_LANGUAGE
        self.country: str = settings.REVIEW_COUNTRY
        self.max_reviews: int = settings.MAX_REVIEWS
        self.min_words: int = settings.MIN_WORD_COUNT

    # ── Public API ───────────────────────────────────────────────────

    def fetch_reviews(
        self,
        app_id: str | None = None,
        weeks: int = 4,
    ) -> List[ReviewRecord]:
        """
        Fetch and normalize reviews from Google Play Store.

        Pipeline:
          1. Scrape raw reviews
          2. Filter by date range
          3. Strip emojis + PII
          4. Reject non-English
          5. Reject < 6 words
          6. Cap at MAX_REVIEWS
        """
        app_id = app_id or self.app_id
        cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)

        logger.info(
            "Fetching reviews for %s (last %d weeks, max %d)",
            app_id, weeks, self.max_reviews,
        )

        raw_reviews = self._scrape_play_store(app_id)
        logger.info("Raw reviews fetched: %d", len(raw_reviews))

        # Filter by date range
        dated = [
            r for r in raw_reviews
            if r.get("at") and self._to_utc(r["at"]) >= cutoff_date
        ]
        logger.info("Reviews in date range: %d", len(dated))

        # Normalize and filter
        records: List[ReviewRecord] = []
        stats = {"emoji_only": 0, "non_english": 0, "too_short": 0, "valid": 0}

        for raw in dated:
            try:
                record = self._to_review_record(raw)

                # Skip if non-English characters detected
                if self._has_non_latin(record.text):
                    stats["non_english"] += 1
                    continue

                # Skip if fewer than min_words after cleaning
                if record.word_count < self.min_words:
                    stats["too_short"] += 1
                    continue

                records.append(record)
                stats["valid"] += 1

                # Cap at max_reviews
                if len(records) >= self.max_reviews:
                    logger.info("Hit MAX_REVIEWS cap (%d)", self.max_reviews)
                    break

            except Exception as exc:
                logger.warning("Skipping malformed review: %s", exc)

        logger.info(
            "Normalization: %d valid, %d non-English, %d too-short (<6 words), %d emoji-only",
            stats["valid"], stats["non_english"], stats["too_short"], stats["emoji_only"],
        )
        return records

    def deduplicate(
        self,
        reviews: List[ReviewRecord],
        existing_ids: Set[str],
    ) -> List[ReviewRecord]:
        """Remove reviews whose source_review_id already exists in the DB."""
        new_reviews = [r for r in reviews if r.review_id not in existing_ids]
        skipped = len(reviews) - len(new_reviews)
        if skipped:
            logger.info("Deduplicated: %d duplicates skipped", skipped)
        return new_reviews

    # ── Cleaning ─────────────────────────────────────────────────────

    @staticmethod
    def strip_emojis(text: str) -> str:
        """Remove all emoji characters from text."""
        return EMOJI_PATTERN.sub("", text)

    @staticmethod
    def strip_pii(text: str) -> str:
        """Remove email addresses, phone numbers, and named references."""
        text = EMAIL_PATTERN.sub("[EMAIL]", text)
        text = PHONE_PATTERN.sub("[PHONE]", text)
        text = NAME_PATTERN.sub("[NAME]", text)
        return text.strip()

    @staticmethod
    def _has_non_latin(text: str) -> bool:
        """Return True if text contains significant non-Latin characters."""
        non_latin_chars = NON_LATIN_PATTERN.findall(text)
        if not text.strip():
            return True
        # If >20% of chars are non-Latin, treat as non-English
        return len(non_latin_chars) / max(len(text.strip()), 1) > 0.2

    @staticmethod
    def clean_text(text: str) -> str:
        """Full cleaning pipeline: emojis → PII → normalize whitespace."""
        text = ReviewIngestionAgent.strip_emojis(text)
        text = ReviewIngestionAgent.strip_pii(text)
        # Collapse multiple whitespace / newlines
        text = re.sub(r"\s+", " ", text).strip()
        return text

    # ── Private helpers ──────────────────────────────────────────────

    def _scrape_play_store(self, app_id: str) -> list:
        """Fetch reviews from Google Play using google-play-scraper."""
        all_reviews: list = []
        continuation_token = None
        batch_size = 200
        # Fetch more than max_reviews to account for filtering losses
        max_raw = self.max_reviews * 3
        max_batches = (max_raw // batch_size) + 1

        for batch_num in range(max_batches):
            try:
                result, continuation_token = gps_reviews(
                    app_id,
                    lang=self.language,
                    country=self.country,
                    sort=Sort.NEWEST,
                    count=batch_size,
                    continuation_token=continuation_token,
                )
                all_reviews.extend(result)
                logger.debug(
                    "Batch %d: fetched %d reviews (total %d)",
                    batch_num + 1, len(result), len(all_reviews),
                )

                if not continuation_token or len(result) < batch_size:
                    break
            except Exception as exc:
                logger.error("Scrape error on batch %d: %s", batch_num + 1, exc)
                break

        return all_reviews

    def _to_review_record(self, raw: dict) -> ReviewRecord:
        """Convert a raw google-play-scraper dict into a ReviewRecord."""
        review_id = raw.get("reviewId") or self._generate_id(raw)
        raw_text = raw.get("content", "") or ""
        clean_text = self.clean_text(raw_text)

        review_date = self._to_utc(raw.get("at"))
        version = raw.get("reviewCreatedVersion")

        return ReviewRecord(
            review_id=review_id,
            text=clean_text,
            rating=int(raw.get("score", 3)),
            date=review_date,
            version=version,
            language=self.language,
            word_count=len(clean_text.split()),
        )

    @staticmethod
    def _generate_id(raw: dict) -> str:
        """Deterministic fallback ID from review content + date."""
        content = (raw.get("content", "") or "") + str(raw.get("at", ""))
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    @staticmethod
    def _to_utc(dt) -> datetime:
        """Ensure a datetime is timezone-aware (UTC)."""
        if dt is None:
            return datetime.now(timezone.utc)
        if isinstance(dt, datetime):
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        return datetime.now(timezone.utc)
