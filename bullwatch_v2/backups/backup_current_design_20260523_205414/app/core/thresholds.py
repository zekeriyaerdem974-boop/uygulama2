"""Runtime threshold management for signal evaluation.

Provides ``get_thresholds()`` / ``update_thresholds()`` backed by
the centralized cache layer.  Extracted from ``legacy_monolith.py``
(FAZ 4) so that both the monolith and the dashboard blueprint can
import without circular dependencies.
"""
from __future__ import annotations

from typing import Dict

from app.cache import cache_get, cache_set

# ── Default values ────────────────────────────────────────────────────
DEFAULT_THRESHOLDS: Dict[str, object] = {
    # Günlük aşırı uzama filtresi (change24)
    "overextended_change24_max": 25.0,   # > ise "PULLBACK BEKLE"
    # Minimum momentum filtreleri
    "min_ret7_pct": 5.0,                 # haftalık getiri alt limiti
    "min_change24_pct": 2.0,             # günlük değişim alt limiti (momentum)
    "max_change24_pct": 15.0,            # "ideal" üst sınır
    # Kısa TF sıcaklık (EMA uzaklığı)
    "heat_atr_max": 1.5,                 # (price-EMA20_15m)/ATR14_15m <= 1.5
    # Rejim / Trend zorunlulukları
    "require_btc_regime": True,          # BTC: SMA200 üstü ve 50>200
    "require_above200": True,            # Coin: 1D SMA200 üstünde
}

THRESHOLDS_KEY = "runtime_thresholds_v1"


def get_thresholds() -> dict:
    """Return current runtime thresholds (cached)."""
    th = cache_get(THRESHOLDS_KEY, ttl=10**9)
    if th is None:
        th = DEFAULT_THRESHOLDS.copy()
        cache_set(THRESHOLDS_KEY, th)
    return th


def update_thresholds(partial: Dict) -> dict:
    """Merge *partial* into current thresholds and persist to cache."""
    th = get_thresholds().copy()
    allowed = set(DEFAULT_THRESHOLDS.keys())
    for k, v in (partial or {}).items():
        if k in allowed:
            if k in ("require_btc_regime", "require_above200"):
                th[k] = bool(v)
            else:
                try:
                    th[k] = float(v)
                except Exception:
                    continue
    cache_set(THRESHOLDS_KEY, th)
    return th
