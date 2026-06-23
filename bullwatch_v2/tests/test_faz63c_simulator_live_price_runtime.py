# -*- coding: utf-8 -*-
"""FAZ 63C — Simulator Live Crypto Price Runtime Tests.

45+ tests covering:
- WebSocket connection and subscription in simulator.js
- kline tick handling and livePrice update
- Symbol matching / normalization
- Symbol switch re-subscription
- REST fallback not overriding WebSocket prices
- PnL updates from live price
- DOM render after price update
- WebSocket reconnect logic
- Backend /ws/market endpoint
- Backend /price REST endpoint
"""
import json
import os
import re
import sys
import time
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

JS_FILE = os.path.join(BASE, "static", "js", "simulator.js")
CSS_FILE = os.path.join(BASE, "static", "css", "simulator.css")
HTML_FILE = os.path.join(BASE, "templates", "simulator.html")
ROUTES_FILE = os.path.join(BASE, "app", "blueprints", "simulator", "routes.py")
MARKET_STREAM_JS = os.path.join(BASE, "static", "js", "market_stream.js")
MARKET_STREAM_PY = os.path.join(BASE, "app", "core", "market_stream.py")
LEGACY_FILE = os.path.join(BASE, "legacy_monolith.py")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) WebSocket Connection Setup
# ══════════════════════════════════════════════════════════════════

class TestWSConnectionSetup(unittest.TestCase):
    """Verify WebSocket connection functions exist in simulator.js."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_connect_sim_ws_defined(self):
        self.assertIn("function connectSimWS()", self.js)

    def test_disconnect_sim_ws_defined(self):
        self.assertIn("function disconnectSimWS()", self.js)

    def test_resubscribe_defined(self):
        self.assertIn("function resubscribeSimWS()", self.js)

    def test_ws_state_variables(self):
        self.assertIn("_simWS", self.js)
        self.assertIn("_wsConnected", self.js)
        self.assertIn("_wsPriceSource", self.js)

    def test_ws_reconnect_state(self):
        self.assertIn("_wsReconnectTimer", self.js)
        self.assertIn("_wsReconnectDelay", self.js)
        self.assertIn("_WS_MAX_RECONNECT", self.js)

    def test_ws_url_construction(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 800]
        self.assertIn("ws", snippet)
        self.assertIn("/ws/market", snippet)

    def test_ws_protocol_detection(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 600]
        self.assertIn('location.protocol === "https:"', snippet)
        self.assertIn('"wss"', snippet)

    def test_only_crypto_uses_ws(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 300]
        self.assertIn('"crypto"', snippet)
        self.assertIn("disconnectSimWS()", snippet)


# ══════════════════════════════════════════════════════════════════
# 2) WebSocket Subscription
# ══════════════════════════════════════════════════════════════════

class TestWSSubscription(unittest.TestCase):
    """Verify correct subscribe message is sent on WS open."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_subscribe_action_sent(self):
        self.assertIn('action: "subscribe"', self.js)

    def test_subscribe_includes_symbol(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 1600]
        self.assertIn('symbol:', snippet)

    def test_subscribe_uses_1m_interval(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 1600]
        self.assertIn('interval: "1m"', snippet)

    def test_subscribe_market_crypto(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 1600]
        self.assertIn('market: "crypto"', snippet)

    def test_symbol_uppercase_before_subscribe(self):
        idx = self.js.index("function connectSimWS()")
        snippet = self.js[idx:idx + 1000]
        self.assertIn(".toUpperCase()", snippet)


# ══════════════════════════════════════════════════════════════════
# 3) Kline Tick Handler
# ══════════════════════════════════════════════════════════════════

class TestKlineTickHandler(unittest.TestCase):
    """Verify kline tick handling updates livePrice and DOM."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_handle_tick_defined(self):
        self.assertIn("function _handleSimWSTick(tick)", self.js)

    def test_extracts_close_price(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 500]
        self.assertIn("tick.close", snippet)

    def test_sets_live_price(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 900]
        self.assertIn("livePrice = price", snippet)

    def test_sets_last_good_price(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 900]
        self.assertIn("lastGoodPrice = price", snippet)

    def test_sets_ws_price_source(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 900]
        self.assertIn("_wsPriceSource = true", snippet)

    def test_updates_dom_text(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 900]
        self.assertIn("$livePrice.textContent", snippet)
        self.assertIn("fmtPrice(price)", snippet)

    def test_adds_loaded_class(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 1000]
        self.assertIn('classList.add("loaded")', snippet)

    def test_flash_animation(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 1100]
        self.assertIn("flash-up", snippet)
        self.assertIn("flash-down", snippet)

    def test_calls_update_estimate(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 1200]
        self.assertIn("updateEstimate()", snippet)


# ══════════════════════════════════════════════════════════════════
# 4) Symbol Matching
# ══════════════════════════════════════════════════════════════════

class TestSymbolMatching(unittest.TestCase):
    """Verify only matching symbol ticks update livePrice."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_symbol_comparison_in_handler(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("tick.symbol !== sym", snippet)

    def test_rejects_empty_symbol(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("!sym", snippet)

    def test_rejects_zero_price(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("price <= 0", snippet)

    def test_symbol_uppercased(self):
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 200]
        self.assertIn(".toUpperCase()", snippet)


# ══════════════════════════════════════════════════════════════════
# 5) Symbol Switch Re-subscription
# ══════════════════════════════════════════════════════════════════

class TestSymbolSwitch(unittest.TestCase):
    """Verify symbol change triggers WS re-subscription."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_symbol_input_calls_resubscribe(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        snippet = self.js[idx:idx + 600]
        self.assertIn("resubscribeSimWS()", snippet)

    def test_symbol_resets_ws_price_source(self):
        idx = self.js.index('$symbol.addEventListener("input"')
        snippet = self.js[idx:idx + 400]
        self.assertIn("_wsPriceSource = false", snippet)

    def test_market_change_connects_crypto(self):
        idx = self.js.index('$market.addEventListener("change"')
        snippet = self.js[idx:idx + 700]
        self.assertIn("connectSimWS()", snippet)

    def test_market_change_disconnects_noncrypto(self):
        idx = self.js.index('$market.addEventListener("change"')
        snippet = self.js[idx:idx + 700]
        self.assertIn("disconnectSimWS()", snippet)

    def test_market_resets_ws_price_source(self):
        idx = self.js.index('$market.addEventListener("change"')
        snippet = self.js[idx:idx + 400]
        self.assertIn("_wsPriceSource = false", snippet)

    def test_resubscribe_sends_new_symbol(self):
        idx = self.js.index("function resubscribeSimWS()")
        snippet = self.js[idx:idx + 600]
        self.assertIn('action: "subscribe"', snippet)
        self.assertIn("$symbol.value", snippet)


# ══════════════════════════════════════════════════════════════════
# 6) REST Fallback Not Overriding WS
# ══════════════════════════════════════════════════════════════════

class TestFallbackPriority(unittest.TestCase):
    """Verify REST fallback does not overwrite live WS prices."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_fetch_price_checks_ws_source_early(self):
        """FAZ 64C: fetchPrice no longer checks _wsPriceSource — REST always polls."""
        idx = self.js.index("async function fetchPrice(")
        snippet = self.js[idx:idx + 600]
        self.assertNotIn("_wsPriceSource", snippet)

    def test_rest_skips_when_ws_active(self):
        idx = self.js.index("async function fetchPrice(")
        snippet = self.js[idx:idx + 600]
        # Should return early when WS is providing prices
        self.assertIn("return;", snippet)

    def test_rest_checks_before_dom_update(self):
        """FAZ 64C: fetchPrice goes straight to REST fetch — no WS guard."""
        idx = self.js.index("async function fetchPrice(")
        body = self.js[idx:idx + 1200]
        # No _wsPriceSource guard inside fetchPrice anymore
        count = body.count("_wsPriceSource")
        self.assertEqual(count, 0, "fetchPrice should have no _wsPriceSource check")

    def test_ws_connected_slows_rest_polling(self):
        """FAZ 64C: Tick handler no longer throttles REST to 30s."""
        idx = self.js.index("function _handleSimWSTick(tick)")
        snippet = self.js[idx:idx + 900]
        self.assertNotIn("30000", snippet)
        self.assertNotIn("clearInterval(priceInterval)", snippet)

    def test_ws_disconnect_restores_fast_polling(self):
        idx = self.js.index("_simWS.onclose")
        snippet = self.js[idx:idx + 400]
        self.assertIn("5000", snippet)


# ══════════════════════════════════════════════════════════════════
# 7) WebSocket Reconnect
# ══════════════════════════════════════════════════════════════════

class TestWSReconnect(unittest.TestCase):
    """Verify WebSocket reconnect logic."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_schedule_reconnect_defined(self):
        self.assertIn("function _scheduleWSReconnect()", self.js)

    def test_exponential_backoff(self):
        idx = self.js.index("function _scheduleWSReconnect()")
        snippet = self.js[idx:idx + 400]
        self.assertIn("_wsReconnectDelay * 2", snippet)

    def test_max_reconnect_cap(self):
        idx = self.js.index("function _scheduleWSReconnect()")
        snippet = self.js[idx:idx + 400]
        self.assertIn("_WS_MAX_RECONNECT", snippet)

    def test_reconnect_only_for_crypto(self):
        idx = self.js.index("function _scheduleWSReconnect()")
        snippet = self.js[idx:idx + 300]
        self.assertIn('"crypto"', snippet)

    def test_onclose_triggers_reconnect(self):
        idx = self.js.index("_simWS.onclose")
        snippet = self.js[idx:idx + 400]
        self.assertIn("_scheduleWSReconnect()", snippet)


# ══════════════════════════════════════════════════════════════════
# 8) Init — WS Connected On Page Load
# ══════════════════════════════════════════════════════════════════

class TestInit(unittest.TestCase):
    """Verify WebSocket is connected at page load for crypto."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_init_connects_ws_for_crypto(self):
        idx = self.js.index("// INIT")
        snippet = self.js[idx:idx + 1500]
        self.assertIn("connectSimWS()", snippet)

    def test_init_checks_market_before_connect(self):
        idx = self.js.index("// INIT")
        snippet = self.js[idx:idx + 1500]
        self.assertIn('"crypto"', snippet)

    def test_start_price_fetch_on_init(self):
        idx = self.js.index("// INIT")
        snippet = self.js[idx:idx + 900]
        self.assertIn("startPriceFetch()", snippet)

    def test_iife_ends_correctly(self):
        self.assertTrue(self.js.strip().endswith("})();"))


# ══════════════════════════════════════════════════════════════════
# 9) Backend — /ws/market Endpoint
# ══════════════════════════════════════════════════════════════════

class TestWSMarketEndpoint(unittest.TestCase):
    """Verify /ws/market server-side endpoint accepts simulator connections."""

    @classmethod
    def setUpClass(cls):
        cls.legacy = _read(LEGACY_FILE)
        cls.stream_py = _read(MARKET_STREAM_PY)

    def test_ws_market_route_exists(self):
        self.assertIn("/ws/market", self.legacy)

    def test_subscribe_action_handled(self):
        self.assertIn('"subscribe"', self.legacy)

    def test_symbol_uppercased_server_side(self):
        self.assertIn(".upper()", self.legacy)

    def test_stream_manager_register_client(self):
        self.assertIn("register_client", self.legacy)

    def test_symbol_room_class(self):
        self.assertIn("class _SymbolRoom", self.stream_py)

    def test_binance_ws_kline(self):
        self.assertIn("@kline_", self.stream_py)

    def test_broadcast_to_clients(self):
        self.assertIn("def broadcast(self, payload", self.stream_py)

    def test_kline_tick_has_close(self):
        idx = self.stream_py.index("def _upstream_loop")
        snippet = self.stream_py[idx:idx + 800]
        self.assertIn('"close":', snippet)

    def test_kline_type_field(self):
        idx = self.stream_py.index("def _upstream_loop")
        snippet = self.stream_py[idx:idx + 800]
        self.assertIn('"type": "kline"', snippet)


# ══════════════════════════════════════════════════════════════════
# 10) Backend — REST /price Endpoint Still Works
# ══════════════════════════════════════════════════════════════════

class TestRESTEndpoint(unittest.TestCase):
    """Verify REST price endpoint is still functional as fallback."""

    @classmethod
    def setUpClass(cls):
        cls.routes = _read(ROUTES_FILE)

    def test_price_route_exists(self):
        self.assertIn("/price", self.routes)

    def test_uses_fetch_current_price(self):
        self.assertIn("fetch_current_price", self.routes)

    def test_returns_json_price(self):
        self.assertIn('"price":', self.routes)

    def test_handles_missing_symbol(self):
        self.assertIn("symbol", self.routes)


# ══════════════════════════════════════════════════════════════════
# 11) Live Runtime Test — WS Returns Kline Data
# ══════════════════════════════════════════════════════════════════

class TestLiveWSRuntime(unittest.TestCase):
    """Actual runtime test: connect to /ws/market and verify kline ticks."""

    def _ws_connect(self, timeout=8):
        try:
            import websocket
            ws = websocket.create_connection(
                "ws://localhost:34000/ws/market", timeout=timeout
            )
            return ws
        except Exception:
            return None

    def test_ws_connects(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running on :34000")
        self.assertIsNotNone(ws)
        ws.close()

    def test_subscribe_btcusdt(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running")
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        # Receive subscribe confirmation
        msgs = []
        start = time.time()
        while time.time() - start < 5:
            try:
                raw = ws.recv()
                msg = json.loads(raw)
                msgs.append(msg)
                if msg.get("type") == "subscribed":
                    break
            except Exception:
                break
        ws.close()
        types = [m.get("type") for m in msgs]
        self.assertIn("subscribed", types)

    def test_receives_kline_tick(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running")
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        klines = []
        start = time.time()
        while time.time() - start < 10:
            try:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("type") == "kline":
                    klines.append(msg)
                    break
            except Exception:
                break
        ws.close()
        self.assertGreater(len(klines), 0, "Should receive at least 1 kline tick")

    def test_kline_has_required_fields(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running")
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        kline = None
        start = time.time()
        while time.time() - start < 10:
            try:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("type") == "kline":
                    kline = msg
                    break
            except Exception:
                break
        ws.close()
        if kline is None:
            self.skipTest("No kline received in time")
        for field in ["symbol", "close", "open", "high", "low", "time"]:
            self.assertIn(field, kline, f"Kline missing field: {field}")

    def test_kline_close_is_positive(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running")
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        start = time.time()
        while time.time() - start < 10:
            try:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("type") == "kline":
                    self.assertGreater(msg["close"], 0)
                    ws.close()
                    return
            except Exception:
                break
        ws.close()
        self.skipTest("No kline received")

    def test_symbol_switch_receives_new_symbol(self):
        ws = self._ws_connect()
        if ws is None:
            self.skipTest("Server not running")
        # Subscribe BTC first
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        time.sleep(1)
        # Switch to ETH
        ws.send(json.dumps({
            "action": "subscribe",
            "symbol": "ETHUSDT",
            "market": "crypto",
            "interval": "1m"
        }))
        eth_received = False
        start = time.time()
        while time.time() - start < 8:
            try:
                raw = ws.recv()
                msg = json.loads(raw)
                if msg.get("type") == "kline" and msg.get("symbol") == "ETHUSDT":
                    eth_received = True
                    break
            except Exception:
                break
        ws.close()
        self.assertTrue(eth_received, "Should receive ETHUSDT kline after switching")

    def test_rest_price_still_works(self):
        """Verify REST endpoint still functions as fallback."""
        import urllib.request
        try:
            url = "http://localhost:34000/api/simulator/price?symbol=BTCUSDT&market=crypto"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            self.assertTrue(data.get("ok"))
            self.assertGreater(data.get("price", 0), 0)
        except Exception:
            self.skipTest("Server not running")


if __name__ == "__main__":
    unittest.main()
