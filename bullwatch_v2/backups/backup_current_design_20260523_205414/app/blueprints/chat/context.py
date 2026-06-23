"""Chat context builder — builds the JSON context blob fed to Ollama.

Extracted from ``legacy_monolith.py`` (FAZ 6).
"""
from __future__ import annotations

import logging

_logger = logging.getLogger("zkr_analiz.chat")

import os
import threading

from app.cache import cache_get_or_set, cache_set, utcnow
from app.core.binance_client import pump_candidates
from app.core.binance_client import binance_klines
from app.core.etf_tracker import fetch_dynamic_etf_events
from app.core.ta import compute_btc_indicators_from_df
from app.core.binance_client import fng_latest
from app.core.thresholds import get_thresholds

# chat_context yenileme periyodu
CHAT_REFRESH_SEC = int(os.getenv("CHAT_REFRESH_SEC", "60"))

# chat_context warmup: startup'ta bloklamamak için arkaplanda hazırlanır.
_CHAT_WARM_STARTED = False
_CHAT_WARM_LOCK = threading.Lock()


def build_chat_context() -> dict:
    """Produce the JSON context blob that is injected into every Ollama prompt."""
    # 1) BTC 1D kline
    df = cache_get_or_set("btc_1d_df", 300, binance_klines, "BTCUSDT", "1d", 400)

    # 2) FNG
    fng = fng_latest()

    # 3) Pump adayları
    pumps = cache_get_or_set("pump_candidates_v1", 300, pump_candidates, limit_pairs=40)

    # 4) ETF event'leri
    etf = fetch_dynamic_etf_events()

    # 5) BTC göstergeleri
    btc = compute_btc_indicators_from_df(df, now_iso=utcnow().isoformat())

    # 6) ETF kısa özet
    etf_summary = {}
    for a in ["BTC", "ETH", "SOL", "XRP"]:
        etf_summary[a] = [e for e in etf if e.get("asset") == a and e.get("status") != "none"][:2]

    context = {
        "now": utcnow().isoformat(),
        "btc": btc,
        "fng": fng,
        "pump_candidates": pumps[:5],
        "etf_summary": etf_summary,
        "thresholds": get_thresholds()
    }
    return context


def warm_chat_context_async() -> None:
    """Build chat_context in a background thread if not already running."""
    global _CHAT_WARM_STARTED
    with _CHAT_WARM_LOCK:
        if _CHAT_WARM_STARTED:
            return
        _CHAT_WARM_STARTED = True

    def _job():
        global _CHAT_WARM_STARTED
        try:
            ctx = build_chat_context()
            cache_set("chat_context", ctx)
        except Exception as e:
            _logger.error("Chat context warmup error: %s", e, exc_info=True)
        finally:
            with _CHAT_WARM_LOCK:
                _CHAT_WARM_STARTED = False

    threading.Thread(target=_job, daemon=True).start()
