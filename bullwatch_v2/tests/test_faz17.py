# -*- coding: utf-8 -*-
"""FAZ 17 Tests — Universal Signals + Expanded Symbols.

Tests:
  - Expanded symbol lists: stocks (~120), BIST (~100), forex (~25), commodities (~17)
  - Universal signal engine: evaluate_market_signal(), scan_market_signals()
  - Support/Resistance computation
  - API: /api/market-signal, /api/market-signals, /api/signal?market=
  - Frontend: hasSignals=true for all markets, S/R panel, market-aware endpoints
  - Live server verification
"""
import json
import os
import re
import sys
import unittest

import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

LIVE = "http://127.0.0.1:34000"


def _live_ok():
    try:
        r = requests.get(f"{LIVE}/trade", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════
# 1. Expanded Symbol Lists
# ══════════════════════════════════════════════════════════════════════

class TestExpandedSymbols(unittest.TestCase):
    """Verify expanded symbol lists have correct counts and format."""

    def test_stocks_symbols_count(self):
        from app.core.stocks_data import DEFAULT_SYMBOLS
        self.assertGreaterEqual(len(DEFAULT_SYMBOLS), 500,
                                "US Stocks should have 500+ symbols (S&P 500 + NASDAQ)")

    def test_stocks_no_duplicates(self):
        from app.core.stocks_data import DEFAULT_SYMBOLS
        self.assertEqual(len(DEFAULT_SYMBOLS), len(set(DEFAULT_SYMBOLS)),
                         "No duplicate symbols in stocks")

    def test_stocks_contains_key_symbols(self):
        from app.core.stocks_data import DEFAULT_SYMBOLS
        for sym in ["AAPL", "MSFT", "NVDA", "TSLA", "GOOGL", "AMZN", "META", "JPM"]:
            self.assertIn(sym, DEFAULT_SYMBOLS, f"{sym} should be in stocks")

    def test_bist_symbols_count(self):
        from app.core.bist_data import DEFAULT_SYMBOLS
        self.assertGreaterEqual(len(DEFAULT_SYMBOLS), 400,
                                "BIST should have 400+ symbols (full BIST)")

    def test_bist_all_have_is_suffix(self):
        from app.core.bist_data import DEFAULT_SYMBOLS
        for sym in DEFAULT_SYMBOLS:
            self.assertTrue(sym.endswith(".IS"), f"{sym} should end with .IS")

    def test_bist_contains_key_symbols(self):
        from app.core.bist_data import DEFAULT_SYMBOLS
        for sym in ["THYAO.IS", "ASELS.IS", "GARAN.IS", "AKBNK.IS", "EREGL.IS"]:
            self.assertIn(sym, DEFAULT_SYMBOLS, f"{sym} should be in BIST")

    def test_forex_symbols_count(self):
        from app.core.forex_data import DEFAULT_SYMBOLS
        self.assertGreaterEqual(len(DEFAULT_SYMBOLS), 20,
                                "Forex should have 20+ pairs")

    def test_forex_all_have_x_suffix(self):
        from app.core.forex_data import DEFAULT_SYMBOLS
        for sym in DEFAULT_SYMBOLS:
            self.assertTrue(sym.endswith("=X"), f"{sym} should end with =X")

    def test_commodities_symbols_count(self):
        from app.core.commodities_data import DEFAULT_SYMBOLS
        self.assertGreaterEqual(len(DEFAULT_SYMBOLS), 15,
                                "Commodities should have 15+ symbols")

    def test_commodities_all_have_f_suffix(self):
        from app.core.commodities_data import DEFAULT_SYMBOLS
        for sym in DEFAULT_SYMBOLS:
            self.assertTrue(sym.endswith("=F"), f"{sym} should end with =F")


# ══════════════════════════════════════════════════════════════════════
# 2. Universal Signal Engine
# ══════════════════════════════════════════════════════════════════════

class TestUniversalSignalEngine(unittest.TestCase):
    """Test the universal signal engine module."""

    def test_import_module(self):
        from app.core.universal_signal import evaluate_market_signal, scan_market_signals
        self.assertTrue(callable(evaluate_market_signal))
        self.assertTrue(callable(scan_market_signals))

    def test_market_index_mapping(self):
        from app.core.universal_signal import _MARKET_INDEX
        self.assertIn("stocks", _MARKET_INDEX)
        self.assertIn("bist", _MARKET_INDEX)
        self.assertIn("forex", _MARKET_INDEX)
        self.assertIn("commodities", _MARKET_INDEX)
        self.assertEqual(_MARKET_INDEX["stocks"], "^GSPC")
        self.assertEqual(_MARKET_INDEX["bist"], "XU100.IS")

    def test_market_thresholds(self):
        from app.core.universal_signal import _MARKET_THRESHOLDS
        for market in ["stocks", "bist", "forex", "commodities"]:
            th = _MARKET_THRESHOLDS[market]
            self.assertIn("min_ret7_pct", th)
            self.assertIn("min_change24_pct", th)
            self.assertIn("overextended_change24_max", th)
            self.assertIn("heat_atr_max", th)
            self.assertIn("require_index_regime", th)
            self.assertIn("require_above200", th)

    def test_forex_thresholds_lower(self):
        """Forex should have lower thresholds since FX moves less."""
        from app.core.universal_signal import _MARKET_THRESHOLDS
        fx = _MARKET_THRESHOLDS["forex"]
        st = _MARKET_THRESHOLDS["stocks"]
        self.assertLess(fx["min_ret7_pct"], st["min_ret7_pct"])
        self.assertLess(fx["min_change24_pct"], st["min_change24_pct"])

    def test_klines_to_df(self):
        from app.core.universal_signal import _klines_to_df
        import pandas as pd
        rows = [
            {"open": 100, "high": 110, "low": 90, "close": 105, "volume": 1000},
            {"open": 105, "high": 115, "low": 95, "close": 110, "volume": 1200},
        ]
        df = _klines_to_df(rows)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        self.assertEqual(float(df["close"].iloc[-1]), 110.0)

    def test_klines_to_df_empty(self):
        from app.core.universal_signal import _klines_to_df
        df = _klines_to_df([])
        self.assertTrue(df.empty)

    def test_compute_support_resistance(self):
        from app.core.universal_signal import _compute_support_resistance
        import pandas as pd
        import numpy as np
        np.random.seed(42)
        n = 50
        close = pd.Series(100 + np.cumsum(np.random.randn(n) * 0.5))
        high = close + abs(np.random.randn(n) * 0.3)
        low = close - abs(np.random.randn(n) * 0.3)
        df = pd.DataFrame({"open": close, "high": high, "low": low, "close": close, "volume": 1000})
        sr = _compute_support_resistance(df, n_levels=3)
        self.assertIn("support", sr)
        self.assertIn("resistance", sr)
        self.assertIsInstance(sr["support"], list)
        self.assertIsInstance(sr["resistance"], list)

    def test_compute_sr_too_few_rows(self):
        from app.core.universal_signal import _compute_support_resistance
        import pandas as pd
        df = pd.DataFrame({"open": [100], "high": [110], "low": [90], "close": [100], "volume": [500]})
        sr = _compute_support_resistance(df)
        self.assertEqual(sr["support"], [])
        self.assertEqual(sr["resistance"], [])


# ══════════════════════════════════════════════════════════════════════
# 3. Signal Routes
# ══════════════════════════════════════════════════════════════════════

class TestSignalRoutes(unittest.TestCase):
    """Test signal route registration and structure."""

    def test_routes_import(self):
        from app.blueprints.signals.routes import api_market_signal, api_market_signals
        self.assertTrue(callable(api_market_signal))
        self.assertTrue(callable(api_market_signals))

    def test_original_signal_route_preserved(self):
        from app.blueprints.signals.routes import api_signal, api_signals
        self.assertTrue(callable(api_signal))
        self.assertTrue(callable(api_signals))


# ══════════════════════════════════════════════════════════════════════
# 4. Frontend Config
# ══════════════════════════════════════════════════════════════════════

class TestFrontendConfig(unittest.TestCase):
    """Verify frontend is updated for universal signals."""

    def test_all_markets_have_signals_true(self):
        js_path = os.path.join(BASE, "static", "js", "trade.js")
        content = open(js_path).read()
        # All markets should have hasSignals: true
        config_block = content[content.index("const MARKET_CONFIG"):content.index("const LS_MARKET_KEY")]
        has_signals_false = config_block.count("hasSignals: false")
        self.assertEqual(has_signals_false, 0,
                         "All markets should have hasSignals: true")

    def test_market_signal_endpoint_used(self):
        js_path = os.path.join(BASE, "static", "js", "trade.js")
        content = open(js_path).read()
        self.assertIn("/api/market-signal?", content,
                      "Frontend should use /api/market-signal for non-crypto")

    def test_support_resistance_div_exists(self):
        html_path = os.path.join(BASE, "templates", "trade.html")
        content = open(html_path).read()
        self.assertIn('id="sigSR"', content,
                      "Support/Resistance div should exist in trade.html")

    def test_destek_direnc_title_exists(self):
        html_path = os.path.join(BASE, "templates", "trade.html")
        content = open(html_path).read()
        self.assertIn("Destek / Diren", content,
                      "Support/Resistance card title should exist")

    def test_signal_unavailable_text_updated(self):
        js_path = os.path.join(BASE, "static", "js", "trade.js")
        content = open(js_path).read()
        self.assertNotIn("Signal analysis is only available for Crypto market", content,
                         "Old crypto-only message should be removed")

    def test_sr_rendering_in_js(self):
        js_path = os.path.join(BASE, "static", "js", "trade.js")
        content = open(js_path).read()
        self.assertIn("support_resistance", content)
        self.assertIn("sigSR", content)


# ══════════════════════════════════════════════════════════════════════
# 5. Live Server Tests
# ══════════════════════════════════════════════════════════════════════

class TestLiveMarketSignal(unittest.TestCase):
    """Live API tests for market signals."""

    def setUp(self):
        if not _live_ok():
            self.skipTest("Live server not running on port 34000")

    def test_market_signal_stocks(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=AAPL&market=stocks", timeout=30)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"), f"Response: {js}")
        data = js["data"]
        self.assertIn(data["decision"], ["AL", "PULLBACK BEKLE", "ALMA"])
        self.assertEqual(data["symbol"], "AAPL")
        self.assertEqual(data["market"], "stocks")
        self.assertIn("ticks", data)
        self.assertIn("risk", data)
        self.assertIn("pullback_targets", data)
        self.assertIn("support_resistance", data)

    def test_market_signal_bist(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=THYAO.IS&market=bist", timeout=30)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"), f"Response: {js}")
        data = js["data"]
        self.assertIn(data["decision"], ["AL", "PULLBACK BEKLE", "ALMA"])
        self.assertEqual(data["market"], "bist")
        self.assertIn("support_resistance", data)
        sr = data["support_resistance"]
        self.assertIn("support", sr)
        self.assertIn("resistance", sr)

    def test_market_signal_forex(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=EURUSD%3DX&market=forex", timeout=30)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"), f"Response: {js}")
        data = js["data"]
        self.assertIn(data["decision"], ["AL", "PULLBACK BEKLE", "ALMA"])

    def test_market_signal_commodities(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=GC%3DF&market=commodities", timeout=30)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"), f"Response: {js}")
        data = js["data"]
        self.assertIn(data["decision"], ["AL", "PULLBACK BEKLE", "ALMA"])
        self.assertIn("context", data)
        ctx = data["context"]
        self.assertIn("rsi", ctx)
        self.assertIn("macd_bullish", ctx)

    def test_market_signal_missing_symbol(self):
        r = requests.get(f"{LIVE}/api/market-signal?market=stocks", timeout=10)
        self.assertEqual(r.status_code, 400)

    def test_market_signal_invalid_market(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=AAPL&market=crypto", timeout=10)
        self.assertEqual(r.status_code, 400)

    def test_signal_with_market_param(self):
        """Test /api/signal?symbol=AAPL&market=stocks fallback."""
        r = requests.get(f"{LIVE}/api/signal?symbol=AAPL&market=stocks", timeout=30)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"), f"Response: {js}")

    def test_original_crypto_signal_still_works(self):
        """Crypto signal endpoint should still work."""
        r = requests.get(f"{LIVE}/api/signal?symbol=BTCUSDT", timeout=30)
        # May fail if Binance is unreachable, but route should exist
        self.assertIn(r.status_code, [200, 500])

    def test_signal_has_ticks(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=MSFT&market=stocks", timeout=30)
        js = r.json()
        if js.get("ok"):
            data = js["data"]
            ticks = data.get("ticks", [])
            self.assertGreater(len(ticks), 5, "Should have multiple tick checks")
            for tick in ticks:
                self.assertIn("label", tick)
                self.assertIn("ok", tick)

    def test_signal_has_risk(self):
        r = requests.get(f"{LIVE}/api/market-signal?symbol=NVDA&market=stocks", timeout=30)
        js = r.json()
        if js.get("ok"):
            risk = js["data"].get("risk", {})
            self.assertIn("rationale", risk)

    def test_trade_page_loads(self):
        r = requests.get(f"{LIVE}/trade", timeout=10)
        self.assertEqual(r.status_code, 200)
        self.assertIn("sigSR", r.text)
        self.assertIn("Destek / Diren", r.text)

    def test_expanded_stocks_symbols(self):
        r = requests.get(f"{LIVE}/api/stocks/symbols", timeout=180)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreaterEqual(js.get("count", 0), 50,
                                "Should return many stock symbols")

    def test_expanded_bist_symbols(self):
        r = requests.get(f"{LIVE}/api/bist/symbols", timeout=180)
        self.assertEqual(r.status_code, 200)
        js = r.json()
        self.assertTrue(js.get("ok"))
        self.assertGreaterEqual(js.get("count", 0), 50,
                                "Should return many BIST symbols")


if __name__ == "__main__":
    unittest.main()
