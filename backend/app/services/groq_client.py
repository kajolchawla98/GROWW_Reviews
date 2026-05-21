"""
Groq Rate Limiter — ensures API calls stay within Groq free-tier limits.

Groq free tier limits (as of 2026):
  - 30 requests per minute (RPM)
  - 14,400 requests per day (RPD)
  - 6,000 tokens per minute (TPM)

This module provides a thread-safe rate limiter that:
  - Tracks RPM and RPD counters
  - Estimates token usage per request
  - Sleeps when limits would be exceeded
  - Logs rate limit events for debugging
"""

import time
import logging
import threading
from collections import deque

from app.config import settings

logger = logging.getLogger(__name__)


class GroqRateLimiter:
    """
    Thread-safe rate limiter for Groq API calls.

    Usage:
        limiter = GroqRateLimiter()
        limiter.wait_if_needed(estimated_tokens=500)
        # ... make Groq API call ...
        limiter.record_request(actual_tokens=450)
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Track timestamps of requests in the last 60 seconds
        self._minute_requests: deque = deque()
        # Track daily request count
        self._day_requests: deque = deque()
        # Track tokens used in the last 60 seconds
        self._minute_tokens: deque = deque()

        self.rpm_limit = settings.GROQ_RPM
        self.rpd_limit = settings.GROQ_RPD
        self.tpm_limit = settings.GROQ_TPM

    def wait_if_needed(self, estimated_tokens: int = 500) -> None:
        """
        Block until it's safe to make a request without hitting limits.

        Args:
            estimated_tokens: Estimated token count for the upcoming request
        """
        with self._lock:
            now = time.time()
            self._purge_old_entries(now)

            # Check RPM
            while len(self._minute_requests) >= self.rpm_limit:
                oldest = self._minute_requests[0]
                sleep_time = 60.0 - (now - oldest) + 0.5
                if sleep_time > 0:
                    logger.warning(
                        "RPM limit (%d) reached — sleeping %.1fs",
                        self.rpm_limit, sleep_time,
                    )
                    self._lock.release()
                    time.sleep(sleep_time)
                    self._lock.acquire()
                    now = time.time()
                    self._purge_old_entries(now)
                else:
                    break

            # Check TPM
            current_tokens = sum(t for _, t in self._minute_tokens)
            while current_tokens + estimated_tokens > self.tpm_limit:
                if self._minute_tokens:
                    oldest_time = self._minute_tokens[0][0]
                    sleep_time = 60.0 - (now - oldest_time) + 0.5
                else:
                    sleep_time = 5.0

                if sleep_time > 0:
                    logger.warning(
                        "TPM limit (%d) approached (current: %d + est: %d) — sleeping %.1fs",
                        self.tpm_limit, current_tokens, estimated_tokens, sleep_time,
                    )
                    self._lock.release()
                    time.sleep(sleep_time)
                    self._lock.acquire()
                    now = time.time()
                    self._purge_old_entries(now)
                    current_tokens = sum(t for _, t in self._minute_tokens)
                else:
                    break

            # Check RPD
            if len(self._day_requests) >= self.rpd_limit:
                logger.error(
                    "RPD limit (%d) reached! Cannot make more requests today.",
                    self.rpd_limit,
                )
                raise RuntimeError(
                    f"Groq daily request limit ({self.rpd_limit}) exceeded. "
                    "Try again tomorrow or upgrade your plan."
                )

    def record_request(self, actual_tokens: int = 0) -> None:
        """Record that a request was made with the given token count."""
        with self._lock:
            now = time.time()
            self._minute_requests.append(now)
            self._day_requests.append(now)
            if actual_tokens > 0:
                self._minute_tokens.append((now, actual_tokens))

    def _purge_old_entries(self, now: float) -> None:
        """Remove entries older than their window."""
        # Purge minute-window entries (>60s old)
        while self._minute_requests and now - self._minute_requests[0] > 60:
            self._minute_requests.popleft()

        while self._minute_tokens and now - self._minute_tokens[0][0] > 60:
            self._minute_tokens.popleft()

        # Purge day-window entries (>86400s old)
        while self._day_requests and now - self._day_requests[0] > 86400:
            self._day_requests.popleft()

    @property
    def status(self) -> dict:
        """Current rate limiter status for debugging."""
        with self._lock:
            self._purge_old_entries(time.time())
            return {
                "rpm_used": len(self._minute_requests),
                "rpm_limit": self.rpm_limit,
                "rpd_used": len(self._day_requests),
                "rpd_limit": self.rpd_limit,
                "tpm_used": sum(t for _, t in self._minute_tokens),
                "tpm_limit": self.tpm_limit,
            }


# Singleton instance shared across all agents
groq_limiter = GroqRateLimiter()
