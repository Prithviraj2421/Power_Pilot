"""Tests for the in-memory analysis cache (LRU + TTL)."""

from __future__ import annotations

import pytest

from app.datasets.cache import ResultCache


def test_put_then_get_returns_the_same_object() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=4)
    cache.put("a", "analysis-a")

    assert cache.get("a") == "analysis-a"
    assert cache.stats.hits == 1
    assert cache.stats.misses == 0


def test_get_on_unknown_key_is_a_miss() -> None:
    cache: ResultCache[str] = ResultCache()

    assert cache.get("nope") is None
    assert cache.stats.misses == 1


def test_evicts_least_recently_used_beyond_capacity() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=2)
    cache.put("a", "A")
    cache.put("b", "B")

    # Touch "a" so "b" becomes the least recently used entry.
    assert cache.get("a") == "A"
    cache.put("c", "C")

    assert cache.get("a") == "A"
    assert cache.get("c") == "C"
    assert cache.get("b") is None, "expected the least recently used entry to be evicted"
    assert cache.stats.evictions == 1


def test_capacity_is_never_exceeded() -> None:
    cache: ResultCache[int] = ResultCache(max_entries=3)
    for index in range(25):
        cache.put(f"key-{index}", index)

    assert len(cache) == 3
    assert cache.stats.evictions == 22


def test_zero_ttl_means_entries_never_expire() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=2, ttl_seconds=0)
    cache.put("a", "A")

    assert cache.get("a") == "A"
    assert cache.stats.expirations == 0


def test_expired_entry_is_dropped_and_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 1_000.0}
    monkeypatch.setattr("app.datasets.cache.time.monotonic", lambda: clock["now"])

    cache: ResultCache[str] = ResultCache(max_entries=4, ttl_seconds=60)
    cache.put("a", "A")

    clock["now"] += 59
    assert cache.get("a") == "A", "entry should still be live just inside the TTL"

    clock["now"] += 2
    assert cache.get("a") is None, "entry should expire once past the TTL"
    assert cache.stats.expirations == 1
    assert len(cache) == 0


def test_contains_respects_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = {"now": 500.0}
    monkeypatch.setattr("app.datasets.cache.time.monotonic", lambda: clock["now"])

    cache: ResultCache[str] = ResultCache(ttl_seconds=10)
    cache.put("a", "A")
    assert "a" in cache

    clock["now"] += 11
    assert "a" not in cache


def test_invalidate_removes_only_the_named_entry() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=4)
    cache.put("a", "A")
    cache.put("b", "B")

    assert cache.invalidate("a") is True
    assert cache.invalidate("a") is False, "invalidating twice should report nothing removed"
    assert cache.get("a") is None
    assert cache.get("b") == "B"


def test_clear_empties_the_cache() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=4)
    cache.put("a", "A")
    cache.put("b", "B")

    cache.clear()
    assert len(cache) == 0


def test_hit_rate_and_describe_report_accurate_counters() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=4, ttl_seconds=120)
    cache.put("a", "A")
    cache.get("a")
    cache.get("a")
    cache.get("missing")

    described = cache.describe()
    assert described["hits"] == 2
    assert described["misses"] == 1
    assert described["lookups"] == 3
    assert described["hit_rate"] == pytest.approx(2 / 3, abs=1e-4)
    assert described["entries"] == 1
    assert described["max_entries"] == 4
    assert described["ttl_seconds"] == 120


def test_hit_rate_is_zero_before_any_lookup() -> None:
    cache: ResultCache[str] = ResultCache()
    assert cache.describe()["hit_rate"] == 0.0


def test_capacity_below_one_is_clamped() -> None:
    cache: ResultCache[str] = ResultCache(max_entries=0)
    cache.put("a", "A")
    assert cache.get("a") == "A"
