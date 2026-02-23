"""Rate Limiting + Exponential Backoff for external API calls.

Provides two reusable primitives:
  1. RateLimiter  — token-bucket rate limiter (thread-safe, async-compatible)
  2. retry_with_backoff — sync retry wrapper with exponential backoff
  3. async_retry_with_backoff — async retry wrapper (non-blocking sleep)

Retryable errors: 429, 5xx, timeouts, connection errors.
Non-retryable: 4xx client errors (except 429).
"""

import asyncio
import logging
import threading
import time
from typing import Callable, Optional, Set, TypeVar

from core.structured_logger import EventType, log_event

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------
# HTTP status codes that should trigger a retry
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503, 504}

# Exception types from common libraries that indicate transient failures
RETRYABLE_EXCEPTION_NAMES: Set[str] = {
    "RateLimitError",
    "APIStatusError",
    "APIConnectionError",
    "APITimeoutError",
    "ConnectionError",
    "Timeout",
    "ReadTimeout",
    "ConnectTimeout",
}


def _is_retryable(exc: Exception) -> bool:
    """Determine whether an exception represents a retryable transient error."""
    exc_name = type(exc).__name__

    # Known retryable exception types
    if exc_name in RETRYABLE_EXCEPTION_NAMES:
        return True

    # Check for status_code attribute (Groq, httpx, requests)
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if status is not None:
        try:
            code = int(status)
            if code in RETRYABLE_STATUS_CODES:
                return True
            # Non-429 4xx → not retryable
            if 400 <= code < 500:
                return False
        except (ValueError, TypeError):
            pass

    # Timeout / connection errors from requests library
    if isinstance(exc, (TimeoutError, ConnectionError, OSError)):
        return True

    return False


# ---------------------------------------------------------------------------
# Token-bucket Rate Limiter
# ---------------------------------------------------------------------------
class RateLimiter:
    """Thread-safe token-bucket rate limiter.

    Args:
        max_calls: Maximum number of calls allowed per ``period`` seconds.
        period: Length of the rate-limit window in seconds.
    """

    def __init__(self, max_calls: int = 10, period: float = 60.0) -> None:
        self.max_calls = max_calls
        self.period = period
        self._tokens = float(max_calls)
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self.max_calls,
            self._tokens + elapsed * (self.max_calls / self.period),
        )
        self._last_refill = now

    def acquire(self) -> float:
        """Block until a token is available. Returns wait duration in seconds."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return 0.0
                # Calculate wait time until next token
                wait = (1.0 - self._tokens) * (self.period / self.max_calls)
            time.sleep(wait)

    async def async_acquire(self) -> float:
        """Non-blocking async version of acquire."""
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return 0.0
                wait = (1.0 - self._tokens) * (self.period / self.max_calls)
            await asyncio.sleep(wait)


# ---------------------------------------------------------------------------
# Pre-configured limiters for each external service
# ---------------------------------------------------------------------------
# Groq free tier: ~30 req/min
groq_limiter = RateLimiter(max_calls=25, period=60.0)

# Tavily free tier: ~100 req/min (conservative)
tavily_limiter = RateLimiter(max_calls=20, period=60.0)


# ---------------------------------------------------------------------------
# Sync retry with exponential backoff
# ---------------------------------------------------------------------------
def retry_with_backoff(
    fn: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 16.0,
    multiplier: float = 2.0,
    rate_limiter: Optional[RateLimiter] = None,
    service_name: str = "api",
    **kwargs,
) -> T:
    """Call ``fn`` with exponential backoff on retryable errors.

    Non-retryable errors (4xx except 429) are raised immediately.
    """
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        # Respect rate limiter before each attempt
        if rate_limiter is not None:
            rate_limiter.acquire()

        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc

            if not _is_retryable(exc):
                log_event(logger, logging.WARNING, EventType.RETRY_ATTEMPT,
                          f"Non-retryable error from {service_name}",
                          retry_count=attempt, service=service_name,
                          error=str(exc))
                raise

            if attempt >= max_retries:
                log_event(logger, logging.ERROR, EventType.RETRY_EXHAUSTED,
                          f"Max retries exceeded for {service_name}",
                          retry_count=max_retries + 1, service=service_name,
                          error=str(exc))
                raise

            delay = min(base_delay * (multiplier ** attempt), max_delay)
            log_event(logger, logging.WARNING, EventType.RETRY_ATTEMPT,
                      f"Retrying {service_name} after {delay:.2f}s",
                      retry_count=attempt + 1, service=service_name,
                      delay_s=round(delay, 2), error=str(exc))
            time.sleep(delay)

    # Should never reach here
    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Async retry with exponential backoff (non-blocking)
# ---------------------------------------------------------------------------
async def async_retry_with_backoff(
    fn: Callable[..., T],
    *args,
    max_retries: int = 3,
    base_delay: float = 0.5,
    max_delay: float = 16.0,
    multiplier: float = 2.0,
    rate_limiter: Optional[RateLimiter] = None,
    service_name: str = "api",
    **kwargs,
) -> T:
    """Async version — uses asyncio.sleep for non-blocking backoff."""
    last_exc: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        if rate_limiter is not None:
            await rate_limiter.async_acquire()

        try:
            return await asyncio.to_thread(fn, *args, **kwargs)
        except Exception as exc:
            last_exc = exc

            if not _is_retryable(exc):
                log_event(logger, logging.WARNING, EventType.RETRY_ATTEMPT,
                          f"Non-retryable error from {service_name}",
                          retry_count=attempt, service=service_name,
                          error=str(exc))
                raise

            if attempt >= max_retries:
                log_event(logger, logging.ERROR, EventType.RETRY_EXHAUSTED,
                          f"Max retries exceeded for {service_name}",
                          retry_count=max_retries + 1, service=service_name,
                          error=str(exc))
                raise

            delay = min(base_delay * (multiplier ** attempt), max_delay)
            log_event(logger, logging.WARNING, EventType.RETRY_ATTEMPT,
                      f"Retrying {service_name} after {delay:.2f}s",
                      retry_count=attempt + 1, service=service_name,
                      delay_s=round(delay, 2), error=str(exc))
            await asyncio.sleep(delay)

    raise last_exc  # type: ignore[misc]
