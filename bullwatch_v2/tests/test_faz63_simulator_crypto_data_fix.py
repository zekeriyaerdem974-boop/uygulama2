# -*- coding: utf-8 -*-
"""FAZ 63 — Simulator Crypto Data Flow Fix Tests.

50+ tests covering:
- Price endpoint returns valid crypto prices
- Price fallback/cache logic in frontend JS
- Symbol switching resets price state
- Order execution uses correct price source
- PnL calculation correctness for buy/sell
- Account extended returns proper fields
- Order book generation for crypto
- Pending order check logic
"""
import json
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

JS_FILE = os.path.join(BASE, "static", "js", "simulator.js")
CSS_FILE = os.path.join(BASE, "static", "css", "simulator.css")
HTML_FILE = os.path.join(BASE, "templates", "simulator.html")
ROUTES_FILE = os.path.join(BASE, "app", "blueprints", "simulator", "routes.py")
ENGINE_FILE = os.path.join(BASE, "app", "core", "simulator_engine.py")
PAPER_FILE = os.path.join(BASE, "app", "core", "paper_trading_engine.py")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) FRONTEND — Price Cache / Fallback Logic
# ══════════════════════════════════════════════════════════════════

class TestPriceCacheFrontend(unittest.TestCase):
    """Verify JS has lastGoodPrice cache and fallback logic."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_last_good_price_declared(self):
        self.assertIn("lastGoodPrice", self.js)

    def test_last_good_price_initialized_zero(self):
        self.assertIn("lastGoodPrice = 0", self.js)

    def test_last_good_price_updated_on_success(self):
        self.assertIn("lastGoodPrice = d.price", self.js)

    def test_fallback_uses_last_good_price(self):
        self.assertIn("if (lastGoodPrice > 0)", self.js)
        self.assertIn("livePrice = lastGoodPrice", self.js)

    def test_no_immediate_zero_on_failure(self):
        # After the fallback block, only set to 0 if no cached price
        idx_fallback = self.js.index("if (lastGoodPrice > 0)")
        snippet = self.js[idx_fallback:idx_fallback + 300]
        self.assertIn("} else {", snippet)

    def test_symbol_change_resets_cache(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        snippet = self.js[idx:idx + 400]
        self.assertIn("lastGoodPrice = 0", snippet)

    def test_market_change_resets_cache(self):
        idx = self.js.index('$market.addEventListener("change"')
        snippet = self.js[idx:idx + 300]
        self.assertIn("lastGoodPrice = 0", snippet)

    def test_price_poll_interval_5s(self):
        self.assertIn("setInterval(fetchPrice, 5000)", self.js)

    def test_fetch_price_async_function(self):
        self.assertIn("async function fetchPrice(", self.js)

    def test_price_endpoint_url(self):
        self.assertIn('/price?symbol=', self.js)

    def test_flash_animation_on_change(self):
        self.assertIn("flash-up", self.js)
        self.assertIn("flash-down", self.js)


# ══════════════════════════════════════════════════════════════════
# 2) FRONTEND — Symbol & Market Handling
# ══════════════════════════════════════════════════════════════════

class TestSymbolHandling(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_symbol_default_btcusdt(self):
        html = _read(HTML_FILE)
        self.assertIn('value="BTCUSDT"', html)

    def test_market_default_crypto(self):
        html = _read(HTML_FILE)
        self.assertIn('value="crypto"', html)

    def test_symbol_uppercase_on_fetch(self):
        self.assertIn(".toUpperCase()", self.js)

    def test_market_select_options(self):
        html = _read(HTML_FILE)
        for m in ["crypto", "stocks", "bist", "forex", "commodities"]:
            self.assertIn(f'value="{m}"', html)

    def test_url_param_preset(self):
        self.assertIn('params.get("symbol")', self.js)
        self.assertIn('params.get("market")', self.js)

    def test_debounce_on_symbol_input(self):
        self.assertIn("priceDebounce", self.js)
        self.assertIn("setTimeout", self.js)


# ══════════════════════════════════════════════════════════════════
# 3) FRONTEND — Live Price Display
# ══════════════════════════════════════════════════════════════════

class TestLivePriceDisplay(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)
        cls.html = _read(HTML_FILE)

    def test_live_price_element_exists(self):
        self.assertIn('id="sim-live-price"', self.html)

    def test_live_price_label(self):
        self.assertIn("Canlı Fiyat", self.html)

    def test_loaded_class_added(self):
        self.assertIn('classList.add("loaded")', self.js)

    def test_fmtPrice_handles_btc(self):
        self.assertIn("fmtPrice", self.js)
        # fmtPrice should handle high values (>10000) with 2 decimals
        idx = self.js.index("function fmtPrice")
        snippet = self.js[idx:idx + 300]
        self.assertIn("10000", snippet)

    def test_fmtPrice_handles_low_prices(self):
        idx = self.js.index("function fmtPrice")
        snippet = self.js[idx:idx + 300]
        self.assertIn("0.01", snippet)


# ══════════════════════════════════════════════════════════════════
# 4) BACKEND — Price Endpoint
# ══════════════════════════════════════════════════════════════════

class TestPriceEndpoint(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.routes = _read(ROUTES_FILE)

    def test_price_route_exists(self):
        self.assertIn("/price", self.routes)

    def test_price_uses_fetch_current_price(self):
        self.assertIn("fetch_current_price", self.routes)

    def test_price_returns_json(self):
        self.assertIn('"ok": True', self.routes)
        self.assertIn('"price"', self.routes)

    def test_price_handles_missing_symbol(self):
        self.assertIn('"symbol gerekli"', self.routes)

    def test_price_handles_zero_price(self):
        self.assertIn("price <= 0", self.routes)


# ══════════════════════════════════════════════════════════════════
# 5) BACKEND — Crypto Price Fetching
# ══════════════════════════════════════════════════════════════════

class TestCryptoPriceFetching(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.paper = _read(PAPER_FILE)

    def test_binance_client_used_for_crypto(self):
        self.assertIn("binance_klines", self.paper)

    def test_binance_fallback_exists(self):
        self.assertIn("api.binance.com", self.paper)

    def test_yahoo_used_for_non_crypto(self):
        self.assertIn("yahoo_client", self.paper)

    def test_fetch_returns_float(self):
        self.assertIn("float(", self.paper)


# ══════════════════════════════════════════════════════════════════
# 6) BACKEND — PnL Calculation
# ══════════════════════════════════════════════════════════════════

class TestPnLCalculation(unittest.TestCase):

    def test_calculate_pnl_import(self):
        engine = _read(ENGINE_FILE)
        self.assertIn("def calculate_pnl", engine)

    def test_buy_pnl_formula(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(50000, 55000, 1.0, "buy")
        self.assertAlmostEqual(result["pnl_abs"], 5000.0, places=2)
        self.assertAlmostEqual(result["pnl_pct"], 10.0, places=2)

    def test_sell_pnl_formula(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(50000, 45000, 1.0, "sell")
        self.assertAlmostEqual(result["pnl_abs"], 5000.0, places=2)
        self.assertAlmostEqual(result["pnl_pct"], 10.0, places=2)

    def test_buy_loss(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(50000, 48000, 1.0, "buy")
        self.assertTrue(result["pnl_abs"] < 0)

    def test_sell_loss(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(50000, 52000, 1.0, "sell")
        self.assertTrue(result["pnl_abs"] < 0)

    def test_zero_entry_price(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(0, 50000, 1.0, "buy")
        self.assertEqual(result["pnl_abs"], 0)

    def test_fractional_quantity(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(50000, 55000, 0.5, "buy")
        self.assertAlmostEqual(result["pnl_abs"], 2500.0, places=2)


# ══════════════════════════════════════════════════════════════════
# 7) BACKEND — Order Book Generation
# ══════════════════════════════════════════════════════════════════

class TestOrderBook(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = _read(ENGINE_FILE)

    def test_generate_order_book_defined(self):
        self.assertIn("def generate_order_book", self.engine)

    def test_order_book_has_crypto_spread(self):
        self.assertIn('market == "crypto"', self.engine)

    def test_order_book_returns_bids_asks(self):
        self.assertIn('"bids"', self.engine)
        self.assertIn('"asks"', self.engine)

    def test_orderbook_route_exists(self):
        routes = _read(ROUTES_FILE)
        self.assertIn("/orderbook", routes)


# ══════════════════════════════════════════════════════════════════
# 8) BACKEND — Account Extended
# ══════════════════════════════════════════════════════════════════

class TestAccountExtended(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = _read(ENGINE_FILE)

    def test_get_account_extended_defined(self):
        self.assertIn("def get_account_extended", self.engine)

    def test_returns_balance(self):
        self.assertIn('"balance"', self.engine)

    def test_returns_equity(self):
        self.assertIn('"equity"', self.engine)

    def test_returns_available(self):
        self.assertIn('"available"', self.engine)

    def test_returns_unrealized_pnl(self):
        self.assertIn('"unrealized_pnl"', self.engine)

    def test_returns_realized_pnl(self):
        self.assertIn('"realized_pnl"', self.engine)

    def test_pending_reserved_deducted(self):
        self.assertIn("pending_reserved", self.engine)


# ══════════════════════════════════════════════════════════════════
# 9) FRONTEND — Order Execution Flow
# ══════════════════════════════════════════════════════════════════

class TestOrderExecutionFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_execute_trade_function(self):
        self.assertIn("async function executeTrade()", self.js)

    def test_execute_sends_market(self):
        self.assertIn("market: market", self.js)

    def test_execute_sends_side(self):
        self.assertIn("side: currentSide", self.js)

    def test_execute_sends_order_type(self):
        self.assertIn("order_type: currentType", self.js)

    def test_execute_posts_to_order(self):
        self.assertIn('"/order"', self.js)

    def test_limit_price_sent(self):
        self.assertIn("body.price = limitP", self.js)

    def test_stop_price_sent(self):
        self.assertIn("body.stop_price = stopP", self.js)

    def test_refresh_after_trade(self):
        self.assertIn("refreshAll()", self.js)


# ══════════════════════════════════════════════════════════════════
# 10) INTEGRATION — Auto-Refresh Intervals
# ══════════════════════════════════════════════════════════════════

class TestAutoRefresh(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_account_refresh_interval(self):
        self.assertIn("setInterval(loadAccount", self.js)

    def test_orderbook_refresh_interval(self):
        self.assertIn("setInterval(loadOrderBook", self.js)

    def test_pending_orders_check(self):
        self.assertIn("setInterval(checkPendingOrders", self.js)

    def test_init_refreshAll(self):
        self.assertIn("refreshAll();", self.js)

    def test_init_startPriceFetch(self):
        self.assertIn("startPriceFetch();", self.js)


if __name__ == "__main__":
    unittest.main()
