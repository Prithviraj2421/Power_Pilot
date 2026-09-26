"""In-memory cache for computed pipeline analyses.

This is a pure performance layer. Every entry is derived data that can be
recomputed from the stored CSV, so eviction and expiry are never data loss --
they only cost one pipeline run on the next request.

Bounded two ways: least-recently-used eviction past ``max_entries``, and a TTL so
a long-running server does not pin stale analyses in memory forever.
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from app.common.logger import get_logger

logger = get_logger("ResultCache")

T = TypeVar("T")


@dataclass(slots=True)
class CacheStats:
    """Observability counters. Exposed by the datasets route for diagnostics."""

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0

    @property
    def lookups(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return (self.hits / self.lookups) if self.lookups else 0.0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "lookups": self.lookups,
            "hit_rate": round(self.hit_rate, 4),
        }


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    stored_at: float


class ResultCache(Generic[T]):
    """Thread-safe LRU + TTL cache keyed by dataset id."""

    def __init__(self, max_entries: int = 32, ttl_seconds: int = 3600) -> None:
        self._max_entries = max(1, max_entries)
        self._ttl_seconds = max(0, ttl_seconds)
        self._entries: OrderedDict[str, _Entry[T]] = OrderedDict()
        self._lock = threading.RLock()
        self.stats = CacheStats()

    def _is_expired(self, entry: _Entry[T], now: float) -> bool:
        if self._ttl_seconds == 0:
            return False
        return (now - entry.stored_at) > self._ttl_seconds

    def get(self, key: str) -> Optional[T]:
        """Return the cached value, or None on miss or expiry."""
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self.stats.misses += 1
                return None

            if self._is_expired(entry, now):
                del self._entries[key]
                self.stats.expirations += 1
                self.stats.misses += 1
                logger.info(f"Cache entry for {key} expired after {self._ttl_seconds}s")
                return None

            self._entries.move_to_end(key)
            self.stats.hits += 1
            return entry.value

    def put(self, key: str, value: T) -> None:
        with self._lock:
            self._entries[key] = _Entry(value=value, stored_at=time.monotonic())
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                evicted_key, _ = self._entries.popitem(last=False)
                self.stats.evictions += 1
                logger.info(f"Evicted cached analysis for {evicted_key} (cache full)")

    def invalidate(self, key: str) -> bool:
        with self._lock:
            return self._entries.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._entries)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            return not self._is_expired(entry, time.monotonic())

    def describe(self) -> dict[str, object]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "max_entries": self._max_entries,
                "ttl_seconds": self._ttl_seconds,
                **self.stats.to_dict(),
            }
