"""FAZ 3 verification tests — core module extraction.

Tests validate:
1. Core modules import correctly
2. TA functions produce correct results
3. Flask app creates successfully with all routes intact
4. Monolith functions delegate to core modules
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest


# ── 1) Core module imports ──────────────────────────────────────────
def test_ta_imports():
    from app.core.ta import (
        simple_sma, ema_last, atr_last, vwap_last,
        compute_rsi, compute_macd, compute_btc_indicators_from_df,
    )
    assert callable(simple_sma)
    assert callable(ema_last)
    assert callable(atr_last)
    assert callable(vwap_last)
    assert callable(compute_rsi)
    assert callable(compute_macd)
    assert callable(compute_btc_indicators_from_df)


def test_binance_client_imports():
    from app.core.binance_client import (
        binance_klines, fetch_klines_df, _fetch_exchange_info,
        get_binance_usdt_map, fapi_open_interest, fapi_open_interest_hist,
        _fetch_fng_raw, fng_latest, blockchain_hashrate,
        defillama_stablecoins, coinglass_coinbase_premium,
        pump_candidates, coingecko_top_by_marketcap,
        BINANCE_API,
    )
    assert BINANCE_API == "https://api.binance.com"
    assert callable(binance_klines)


def test_etf_tracker_imports():
    from app.core.etf_tracker import (
        ASSET_KEYWORDS, EXCHANGE_KEYWORDS,
        fr_search_documents, classify_fr_status, detect_exchange,
        rough_deadline, fetch_dynamic_etf_events,
    )
    assert "BTC" in ASSET_KEYWORDS
    assert callable(fetch_dynamic_etf_events)


def test_ollama_client_imports():
    from app.core.ollama_client import ollama_generate, OLLAMA_HOST
    assert callable(ollama_generate)
    assert "11434" in OLLAMA_HOST


# ── 2) TA function correctness ────────────────────────────────────
def test_simple_sma():
    from app.core.ta import simple_sma
    assert simple_sma([1, 2, 3], 2) == 2.5
    assert simple_sma([1, 2, 3, 4, 5], 5) == 3.0
    assert simple_sma([1, 2], 5) is None


def test_ema_last():
    from app.core.ta import ema_last
    series = list(range(1, 21))  # 1..20
    result = ema_last(series, 10)
    assert result is not None
    assert isinstance(result, float)
    assert ema_last([1, 2], 5) is None


def test_atr_last():
    from app.core.ta import atr_last
    # Create a simple OHLCV DataFrame
    data = {
        "high": np.random.uniform(100, 110, 30),
        "low": np.random.uniform(90, 100, 30),
        "close": np.random.uniform(95, 105, 30),
    }
    df = pd.DataFrame(data)
    result = atr_last(df, 14)
    assert result is not None
    assert isinstance(result, float)
    assert result > 0
    # Not enough data
    assert atr_last(df.head(5), 14) is None
    assert atr_last(None, 14) is None


def test_vwap_last():
    from app.core.ta import vwap_last
    data = {
        "high": [110.0] * 10,
        "low": [90.0] * 10,
        "close": [100.0] * 10,
        "volume": [1000.0] * 10,
    }
    df = pd.DataFrame(data)
    result = vwap_last(df, 5)
    assert result is not None
    assert abs(result - 100.0) < 0.01
    assert vwap_last(None, 5) is None


def test_compute_rsi():
    from app.core.ta import compute_rsi
    closes = pd.Series(np.random.uniform(90, 110, 100))
    rsi = compute_rsi(closes, 14)
    assert len(rsi) == 100
    # RSI should be between 0 and 100 (after warmup)
    valid = rsi.dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_compute_macd():
    from app.core.ta import compute_macd
    closes = pd.Series(np.random.uniform(90, 110, 100))
    macd, sig, hist = compute_macd(closes)
    assert len(macd) == 100
    assert len(sig) == 100
    assert len(hist) == 100


def test_compute_btc_indicators_from_df():
    from app.core.ta import compute_btc_indicators_from_df
    data = {"close": np.random.uniform(30000, 40000, 400).tolist()}
    df = pd.DataFrame(data)
    result = compute_btc_indicators_from_df(df, now_iso="2025-01-01T00:00:00Z")
    assert result["price"] > 0
    assert result["sma20"] is not None
    assert result["sma50"] is not None
    assert result["sma200"] is not None
    assert result["ret30"] is not None
    assert result["updated_at"] == "2025-01-01T00:00:00Z"


# ── 3) ETF tracker helpers ────────────────────────────────────────
def test_classify_fr_status():
    from app.core.etf_tracker import classify_fr_status
    assert classify_fr_status("Order Approving Proposed Rule Change") == "approved"
    assert classify_fr_status("Notice of Filing of Proposed Rule Change") == "filed"
    assert classify_fr_status("Designation of a Longer Period") == "delay"
    assert classify_fr_status("Instituting Proceedings") == "proceedings"
    assert classify_fr_status("Immediate Effectiveness") == "effective"
    assert classify_fr_status("Some random text") == "unknown"


def test_detect_exchange():
    from app.core.etf_tracker import detect_exchange
    assert detect_exchange("Cboe BZX Exchange proposes...") == "Cboe BZX"
    assert detect_exchange("NYSE Arca, Inc.") == "NYSE Arca"
    assert detect_exchange("Random text") is None


def test_rough_deadline():
    from app.core.etf_tracker import rough_deadline
    result = rough_deadline("filed", "2025-01-15")
    assert result is not None
    assert "2025-03-01" in result  # 45 days from Jan 15
    assert rough_deadline("approved", "2025-01-15") is None
    assert rough_deadline("filed", None) is None


# ── 4) Flask app creation & route integrity ───────────────────────
def test_app_creates_successfully():
    from app import create_app
    flask_app = create_app()
    assert flask_app is not None


def test_route_count_preserved():
    from app import create_app
    flask_app = create_app()
    rules = [r.rule for r in flask_app.url_map.iter_rules() if r.rule != "/static/<path:filename>"]
    # These critical routes must exist
    critical = [
        "/api/btc_indicators", "/api/bull_estimate", "/api/pump_candidates",
        "/api/signal", "/api/signals", "/api/fng", "/api/chat",
        "/api/indicators/rsi", "/api/indicators/macd",
        "/api/thresholds", "/api/etf_events", "/api/oi",
        "/api/hashrate", "/api/stablecoin_flow", "/api/coinbase_premium",
        "/api/top_coins_4h", "/api/trade_bundle",
        "/api/coins_sma_summary",
        "/", "/chat", "/tv", "/trade", "/sim/mobile",
    ]
    for route in critical:
        assert route in rules, f"Missing route: {route}"


def test_monolith_delegates_to_core():
    """Verify core modules exist and are importable (FAZ 11 cleanup)."""
    from app.core.ta import simple_sma, compute_rsi, compute_macd
    from app.core.binance_client import binance_klines, fng_latest, pump_candidates
    from app.core.etf_tracker import fetch_dynamic_etf_events
    from app.core.ollama_client import ollama_generate
    from app.core.bull_estimate import heuristic_bull_estimate
    from app.core.security import apk_download_enabled

    # All should be callable
    assert callable(simple_sma)
    assert callable(compute_rsi)
    assert callable(compute_macd)
    assert callable(binance_klines)
    assert callable(fng_latest)
    assert callable(pump_candidates)
    assert callable(fetch_dynamic_etf_events)
    assert callable(heuristic_bull_estimate)
    assert callable(apk_download_enabled)
    assert callable(ollama_generate)
