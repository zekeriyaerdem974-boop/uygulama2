"""Centralized cache layer for ZKR Analiz.

Supports Redis (optional) with thread-safe in-memory fallback.
Extracted from legacy_monolith.py — single source of truth for
all cache operations in the application.

FAZ 2 — Added:
  * ``cache_get_or_set()`` pattern to eliminate repetitive
    "get → if None → compute → set" boilerplate across the monolith.
  * ``cache_delete()`` for explicit invalidation.
  * ``cache_keys()`` for diagnostics / health-check.
"""
from __future__ import annotations

import logging

_logger = logging.getLogger("zkr_analiz.cache")

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Optional

# --------------- Redis (optional) ---------------
try:
    import redis as _redis_mod  # type: ignore
except Exception:  # pragma: no cover
    _redis_mod = None

_REDIS_URL = os.getenv("REDIS_URL")
_redis_client = None

if _REDIS_URL and _redis_mod is not None:
    try:
        _redis_client = _redis_mod.Redis.from_url(
            _REDIS_URL, decode_responses=True
        )
        _redis_client.ping()
        _logger.info("Redis cache enabled: %s", _REDIS_URL)
    except Exception as exc:
        _redis_client = None
        _logger.warning("Redis cache disabled: %s", exc)

# --------------- In-memory fallback ---------------
_mem: dict = {}
_mem_lock = threading.Lock()


# --------------- Serialization helpers ---------------
def _pack(val) -> str:
    return json.dumps({"ts": time.time(), "val": val}, ensure_ascii=False)


def _unpack(raw: str):
    obj = json.loads(raw)
    return float(obj.get("ts", 0)), obj.get("val")


# --------------- Public API ---------------
def cache_get(key: str, ttl: float = 60):
    """Return cached value if fresh (within *ttl* seconds), else ``None``."""
    if _redis_client is not None:
        raw = _redis_client.get(key)
        if not raw:
            return None
        try:
            ts, val = _unpack(raw)
        except Exception:
            return None
        if time.time() - ts > ttl:
            return None
        return val

    with _mem_lock:
        item = _mem.get(key)
        if not item:
            return None
        ts, val = item
    if time.time() - ts > ttl:
        return None
    return val


def cache_set(key: str, val) -> None:
    """Store *val* under *key* with current timestamp."""
    if _redis_client is not None:
        try:
            _redis_client.set(key, _pack(val))
            return
        except Exception as exc:
            _logger.warning("Redis set failed, fallback to memory: %s", exc)

    with _mem_lock:
        _mem[key] = (time.time(), val)


def cache_get_or_set(key: str, ttl: float, factory: Callable, *args, **kwargs):
    """Return cached value if fresh, otherwise call *factory* to compute,
    store the result, and return it.

    Eliminates the common pattern scattered throughout the monolith::

        val = cache_get(key, ttl=300)
        if val is None:
            val = expensive_function()
            cache_set(key, val)
        return val

    Usage::

        df = cache_get_or_set("btc_1d_df", 300,
                              binance_klines, "BTCUSDT", "1d", 400)
    """
    val = cache_get(key, ttl=ttl)
    if val is not None:
        return val
    val = factory(*args, **kwargs)
    if val is not None:
        cache_set(key, val)
    return val


def cache_delete(key: str) -> None:
    """Explicitly remove *key* from the cache."""
    if _redis_client is not None:
        try:
            _redis_client.delete(key)
        except Exception:
            pass
    with _mem_lock:
        _mem.pop(key, None)


def cache_keys() -> list[str]:
    """Return a snapshot of all known cache keys (diagnostic use)."""
    if _redis_client is not None:
        try:
            return [k for k in _redis_client.keys("*")]
        except Exception:
            pass
    with _mem_lock:
        return list(_mem.keys())


def utcnow() -> datetime:
    """Timezone-aware UTC now — single source of truth."""
    return datetime.now(timezone.utc)
