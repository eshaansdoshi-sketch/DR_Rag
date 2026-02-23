"""Deterministic LRU Cache with TTL for external API responses.

Caches search results and LLM responses to reduce redundant API calls.
Does NOT cache: final reports, evaluator scores, insight objects.

Key design:
  - Deterministic cache keys via hashlib (query + params)
  - Thread-safe via threading.Lock
  - Optional TTL (default 24 hours)
  - Bounded LRU eviction (default 256 entries)
  - Explicit invalidation via clear() or remove()
  - Cache hits/misses logged
  - Does not bypass rate limiting — cache sits above retry layer
"""

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Optional

from core.structured_logger import EventType, log_event

logger = logging.getLogger(__name__)


def make_cache_key(*parts: str) -> str:
    """Build a deterministic cache key from ordered string parts.

    Hashes the concatenation so that key length is bounded and
    the key is safe for any backend.
    """
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class DeterministicCache:
    """Thread-safe in-memory LRU cache with optional TTL.

    Args:
        max_size: Maximum number of entries before LRU eviction.
        ttl_seconds: Time-to-live per entry. None = no expiry.
        name: Human-readable name for logging.
    """

    def __init__(
        self,
        max_size: int = 256,
        ttl_seconds: Optional[float] = 86400.0,  # 24 hours
        name: str = "cache",
    ) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.name = name
        self._store: OrderedDict[str, tuple] = OrderedDict()  # key -> (value, timestamp)
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """Retrieve a cached value. Returns None on miss or expiry."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self._misses += 1
                log_event(logger, logging.DEBUG, EventType.CACHE_MISS,
                          f"Cache miss", cache_name=self.name, key=key[:16])
                return None

            value, ts = entry

            # TTL check
            if self.ttl_seconds is not None:
                if (time.monotonic() - ts) > self.ttl_seconds:
                    del self._store[key]
                    self._misses += 1
                    log_event(logger, logging.DEBUG, EventType.CACHE_MISS,
                              f"Cache expired", cache_name=self.name, key=key[:16])
                    return None

            # Move to end (most recently used)
            self._store.move_to_end(key)
            self._hits += 1
            log_event(logger, logging.DEBUG, EventType.CACHE_HIT,
                      f"Cache hit", cache_name=self.name, key=key[:16])
            return value

    def put(self, key: str, value: Any) -> None:
        """Store a value. Evicts LRU entry if at capacity."""
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = (value, time.monotonic())
                return

            if len(self._store) >= self.max_size:
                evicted_key, _ = self._store.popitem(last=False)
                logger.debug(
                    "cache_evict | cache=%s evicted=%s", self.name, evicted_key[:16]
                )

            self._store[key] = (value, time.monotonic())

    def remove(self, key: str) -> bool:
        """Explicitly remove a single entry. Returns True if found."""
        with self._lock:
            if key in self._store:
                del self._store[key]
                return True
            return False

    def clear(self) -> int:
        """Clear all entries. Returns count of removed entries."""
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self._hits = 0
            self._misses = 0
            logger.info("cache_clear | cache=%s cleared=%d", self.name, count)
            return count

    @property
    def stats(self) -> dict:
        """Return cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            return {
                "name": self.name,
                "size": len(self._store),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            }


# ---------------------------------------------------------------------------
# Pre-configured caches
# ---------------------------------------------------------------------------
# Search results: keyed by (query, max_results, depth_mode)
search_cache = DeterministicCache(max_size=512, ttl_seconds=86400.0, name="search")

# LLM responses: keyed by (prompt_hash, model)
llm_cache = DeterministicCache(max_size=256, ttl_seconds=86400.0, name="llm")
