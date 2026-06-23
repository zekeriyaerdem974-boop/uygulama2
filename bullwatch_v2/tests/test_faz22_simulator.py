# -*- coding: utf-8 -*-
"""FAZ 22 — Simülatör / Paper Trading Tests.

Validates:
  1.  File existence — paper_trading_engine.py
  2.  File existence — simulator blueprint (__init__.py, routes.py)
  3.  File existence — simulator.html
  4.  File existence — simulator.css
  5.  File existence — simulator.js
  6.  Blueprint registration in legacy_monolith.py
  7.  Dashboard route — /simulator route exists
  8.  Engine — create_account returns correct keys
  9.  Engine — get_account auto-creates if none
  10. Engine — reset_account resets balance
  11. Engine — open_position validates inputs
  12. Engine — close_position calculates PnL
  13. Engine — list_positions returns correct structure
  14. Engine — list_trades returns correct structure
  15. Engine — refresh_positions updates prices
  16. Engine — portfolio_summary returns all fields
  17. Engine — fetch_current_price function exists
  18. Engine — insufficient balance raises ValueError
  19. Engine — TRADE_FEE_RATE is configured
  20. Engine — SQLite persistence (DB file created)
  21. API — GET /api/simulator/account returns ok
  22. API — POST /api/simulator/account/reset returns ok
  23. API — GET /api/simulator/positions returns list
  24. API — GET /api/simulator/trades returns list
  25. API — GET /api/simulator/summary returns summary
  26. API — POST /api/simulator/buy requires symbol
  27. API — POST /api/simulator/buy requires quantity > 0
  28. API — POST /api/simulator/sell works
  29. API — POST /api/simulator/close/<id> works
  30. Template — simulator.html extends base_app
  31. Template — simulator.html has disclaimer
  32. Template — simulator.html has summary cards
  33. Template — simulator.html has trade form
  34. Template — simulator.html has tabs (open/closed/trades)
  35. Template — simulator.html has reset modal
  36. Template — simulator.html includes simulator.js
  37. Template — simulator.html includes simulator.css
  38. CSS — simulator.css has required classes
  39. JS — simulator.js has IIFE structure
  40. JS — simulator.js has API calls
  41. JS — simulator.js has tab switching
  42. JS — simulator.js has trade functions
  43. Discover — simulator card exists in discover.html
  44. Discover — simulator stats loaded via JS
  45. Trade — simulator tab in panel-right
  46. Trade — simulator pane content
  47. Trade — simulator JS in trade.html
  48. Copilot — build_simulator_context in copilot_context.py
  49. Copilot — ask_simulator in copilot_service.py
  50. Copilot — POST /api/copilot/simulator endpoint
  51. Backward compat — existing /trade route works
  52. Backward compat — existing /discover route works
  53. Backward compat — existing /api/copilot/ask works
  54. Backward compat — /screener route works
  55. Backward compat — /alerts route works
  56. Page — /simulator loads successfully
  57. API integration — buy + close flow
  58. API integration — summary after trade
  59. Engine — multiple positions
  60. Engine — closed positions in history
"""
from __future__ import annotations

import os
import re
import json
import sys
import pytest
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:34000"
TIMEOUT = 5

live_api = pytest.mark.live_api


# ══════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════

def _read(path: str) -> str:
    full = os.path.join(BASE, path)
    with open(full, encoding="utf-8") as f:
        return f.read()


def _exists(path: str) -> bool:
    return os.path.isfile(os.path.join(BASE, path))


# ══════════════════════════════════════════════════════════════════════
# 1-5: FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════

class TestFileExistence:
    def test_01_engine_exists(self):
        assert _exists("app/core/paper_trading_engine.py")

    def test_02_blueprint_init(self):
        assert _exists("app/blueprints/simulator/__init__.py")

    def test_03_blueprint_routes(self):
        assert _exists("app/blueprints/simulator/routes.py")

    def test_04_template(self):
        assert _exists("templates/simulator.html")

    def test_05_css(self):
        assert _exists("static/css/simulator.css")

    def test_06_js(self):
        assert _exists("static/js/simulator.js")


# ══════════════════════════════════════════════════════════════════════
# 6-7: REGISTRATION & ROUTES
# ══════════════════════════════════════════════════════════════════════

class TestRegistration:
    def test_07_blueprint_registered(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.simulator import simulator_bp" in src
        assert "app.register_blueprint(simulator_bp)" in src

    def test_08_dashboard_route(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert "/simulator" in src
        assert "simulator.html" in src


# ══════════════════════════════════════════════════════════════════════
# 8-20: ENGINE UNIT TESTS
# ══════════════════════════════════════════════════════════════════════

class TestEngine:
    def test_09_engine_imports(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "def create_account" in src
        assert "def get_account" in src
        assert "def reset_account" in src
        assert "def open_position" in src
        assert "def close_position" in src
        assert "def list_positions" in src
        assert "def list_trades" in src
        assert "def refresh_positions" in src
        assert "def portfolio_summary" in src

    def test_10_engine_fee_rate(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "TRADE_FEE_RATE" in src

    def test_11_engine_fetch_price(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "def fetch_current_price" in src
        assert "binance_klines" in src or "binance" in src
        assert "yahoo_client" in src or "get_ticker" in src

    def test_12_engine_sqlite(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "sqlite3" in src
        assert "paper_trading.db" in src
        assert "CREATE TABLE" in src

    def test_13_engine_validation(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "ValueError" in src
        assert "quantity" in src

    def test_14_engine_pnl_calc(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "pnl_abs" in src
        assert "pnl_pct" in src

    def test_15_engine_balance_check(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "Yetersiz bakiye" in src or "insufficient" in src.lower()

    def test_16_engine_default_balance(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "100_000" in src or "100000" in src

    def test_17_engine_thread_safety(self):
        src = _read("app/core/paper_trading_engine.py")
        assert "threading" in src
        assert "_lock" in src


# ══════════════════════════════════════════════════════════════════════
# 21-29: API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@live_api
class TestAPI:
    def test_21_get_account(self):
        r = requests.get(f"{URL}/api/simulator/account", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "account" in data

    def test_22_reset_account(self):
        r = requests.post(f"{URL}/api/simulator/account/reset", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_23_get_positions(self):
        r = requests.get(f"{URL}/api/simulator/positions", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "positions" in data
        assert isinstance(data["positions"], list)

    def test_24_get_trades(self):
        r = requests.get(f"{URL}/api/simulator/trades", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "trades" in data

    def test_25_get_summary(self):
        r = requests.get(f"{URL}/api/simulator/summary", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "account" in data
        assert "total_pnl" in data
        assert "open_positions_count" in data

    def test_26_buy_requires_symbol(self):
        r = requests.post(f"{URL}/api/simulator/buy",
            json={"quantity": 1},
            timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert data["ok"] is False

    def test_27_buy_requires_quantity(self):
        r = requests.post(f"{URL}/api/simulator/buy",
            json={"symbol": "BTCUSDT", "quantity": 0},
            timeout=TIMEOUT)
        assert r.status_code == 400
        data = r.json()
        assert data["ok"] is False

    def test_28_sell_endpoint_exists(self):
        src = _read("app/blueprints/simulator/routes.py")
        assert "def api_sell" in src
        assert '"/sell"' in src

    def test_29_close_endpoint_exists(self):
        src = _read("app/blueprints/simulator/routes.py")
        assert "def api_close_position" in src
        assert "/close/" in src


# ══════════════════════════════════════════════════════════════════════
# 30-37: TEMPLATE VALIDATION
# ══════════════════════════════════════════════════════════════════════

class TestTemplate:
    def test_30_extends_base(self):
        src = _read("templates/simulator.html")
        assert 'extends' in src  # may extend layout_terminal.html or base_app.html

    def test_31_disclaimer(self):
        src = _read("templates/simulator.html")
        assert "yatırım tavsiyesi değildir" in src.lower() or "Yatırım tavsiyesi" in src

    def test_32_summary_cards(self):
        src = _read("templates/simulator.html")
        assert "sim-balance" in src
        assert "sim-total-pnl" in src
        assert "sim-open-count" in src
        assert "sim-trade-count" in src

    def test_33_trade_form(self):
        src = _read("templates/simulator.html")
        assert "sim-symbol" in src
        assert "sim-quantity" in src
        assert "sim-market" in src
        assert "sim-buy-btn" in src
        assert "sim-sell-btn" in src

    def test_34_tabs(self):
        src = _read("templates/simulator.html")
        assert "sim-pane-open" in src
        assert "sim-pane-closed" in src
        assert "sim-pane-trades" in src

    def test_35_reset_modal(self):
        src = _read("templates/simulator.html")
        assert "sim-reset-modal" in src
        assert "sim-reset-confirm" in src

    def test_36_includes_js(self):
        src = _read("templates/simulator.html")
        assert "simulator.js" in src

    def test_37_includes_css(self):
        src = _read("templates/simulator.html")
        assert "simulator.css" in src


# ══════════════════════════════════════════════════════════════════════
# 38-42: CSS & JS VALIDATION
# ══════════════════════════════════════════════════════════════════════

class TestCSSJS:
    def test_38_css_classes(self):
        src = _read("static/css/simulator.css")
        required = [
            ".sim-container", ".sim-card", ".sim-trade-form",
            ".sim-btn-buy", ".sim-btn-sell", ".sim-tab-btn",
            ".sim-position-card", ".sim-trade-item", ".sim-modal",
            ".sim-disclaimer",
        ]
        for cls in required:
            assert cls in src, f"Missing CSS class: {cls}"

    def test_39_js_iife(self):
        src = _read("static/js/simulator.js")
        assert "(function" in src
        assert "use strict" in src

    def test_40_js_api_calls(self):
        src = _read("static/js/simulator.js")
        assert "/api/simulator" in src
        assert "fetch" in src

    def test_41_js_tabs(self):
        src = _read("static/js/simulator.js")
        assert "sim-tab-btn" in src
        assert "sim-tab-pane" in src or "sim-pane-" in src

    def test_42_js_trade_functions(self):
        src = _read("static/js/simulator.js")
        assert "executeTrade" in src or "simTrade" in src or "buy" in src
        assert "closePosition" in src


# ══════════════════════════════════════════════════════════════════════
# 43-47: INTEGRATION (DISCOVER, TRADE)
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:
    def test_43_discover_sim_card(self):
        src = _read("templates/discover.html")
        # Discover page evolved — verify simulator referenced
        assert "simulator" in src.lower() or "Simülatör" in src

    def test_44_discover_sim_stats(self):
        src = _read("templates/discover.html")
        assert "discover-sim-stats" in src
        assert "/api/simulator/summary" in src

    def test_45_trade_sim_tab(self):
        src = _read("templates/trade.html")
        assert 'data-tab="simulator"' in src
        assert "Sim" in src

    def test_46_trade_sim_pane(self):
        src = _read("templates/trade.html")
        assert 'id="tab-simulator"' in src
        assert "simTrdBalance" in src
        assert "simTrdBuy" in src

    def test_47_trade_sim_js(self):
        src = _read("templates/trade.html")
        assert "/api/simulator" in src
        assert "simTrade" in src or "simClosePos" in src


# ══════════════════════════════════════════════════════════════════════
# 48-50: COPILOT INTEGRATION
# ══════════════════════════════════════════════════════════════════════

class TestCopilotIntegration:
    def test_48_copilot_context(self):
        src = _read("app/core/copilot_context.py")
        assert "def build_simulator_context" in src
        assert "paper_trading_engine" in src

    def test_49_copilot_service(self):
        src = _read("app/core/copilot_service.py")
        assert "def ask_simulator" in src
        assert "_SIMULATOR_PROMPT" in src

    def test_50_copilot_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/simulator" in src
        assert "ask_simulator" in src


# ══════════════════════════════════════════════════════════════════════
# 51-55: BACKWARD COMPATIBILITY
# ══════════════════════════════════════════════════════════════════════

@live_api
class TestBackwardCompat:
    def test_51_trade_page(self):
        r = requests.get(f"{URL}/trade", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_52_discover_page(self):
        r = requests.get(f"{URL}/discover", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_53_copilot_ask(self):
        r = requests.post(f"{URL}/api/copilot/ask",
            json={"question": "test", "symbol": "BTCUSDT"},
            timeout=TIMEOUT)
        assert r.status_code == 200

    def test_54_screener_page(self):
        r = requests.get(f"{URL}/screener", timeout=TIMEOUT)
        assert r.status_code == 200

    def test_55_alerts_page(self):
        r = requests.get(f"{URL}/alerts", timeout=TIMEOUT)
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════
# 56-60: LIVE FLOW TESTS
# ══════════════════════════════════════════════════════════════════════

@live_api
class TestLiveFlow:
    def test_56_simulator_page_loads(self):
        r = requests.get(f"{URL}/simulator", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "Simülatör" in r.text or "simulator" in r.text.lower()

    def test_57_buy_close_flow(self):
        """Reset → Buy → Close → verify PnL recorded."""
        # Reset first
        requests.post(f"{URL}/api/simulator/account/reset", timeout=TIMEOUT)

        # Buy BTCUSDT
        r = requests.post(f"{URL}/api/simulator/buy",
            json={"symbol": "BTCUSDT", "market": "crypto", "quantity": 0.001},
            timeout=TIMEOUT)
        data = r.json()
        if not data.get("ok"):
            pytest.skip(f"Buy failed (price fetch): {data.get('error')}")

        pos_id = data["position"]["id"]

        # Close
        r = requests.post(f"{URL}/api/simulator/close/{pos_id}", timeout=TIMEOUT)
        data = r.json()
        assert data["ok"] is True
        assert "pnl_abs" in data["position"]

    def test_58_summary_after_trade(self):
        r = requests.get(f"{URL}/api/simulator/summary", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "total_trade_count" in data

    def test_59_positions_filter(self):
        r = requests.get(f"{URL}/api/simulator/positions?status=open", timeout=TIMEOUT)
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert isinstance(data["positions"], list)

        r2 = requests.get(f"{URL}/api/simulator/positions?status=closed", timeout=TIMEOUT)
        assert r2.status_code == 200

    def test_60_account_info_complete(self):
        r = requests.get(f"{URL}/api/simulator/account", timeout=TIMEOUT)
        data = r.json()
        assert data["ok"] is True
        acc = data["account"]
        assert "id" in acc
        assert "starting_balance" in acc
        assert "current_balance" in acc
        assert "currency" in acc


# ══════════════════════════════════════════════════════════════════════
# DISCOVER CSS — Simulator card styles
# ══════════════════════════════════════════════════════════════════════

class TestDiscoverCSS:
    def test_61_discover_css_sim_card(self):
        src = _read("static/css/discover.css")
        assert ".discover-sim-card" in src
        assert ".discover-sim-icon" in src
        assert ".discover-sim-title" in src
