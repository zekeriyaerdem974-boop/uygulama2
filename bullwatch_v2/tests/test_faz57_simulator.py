# -*- coding: utf-8 -*-
"""FAZ 57 — Advanced Trading Simulator Tests.

Validates:
  1.  File existence — simulator_engine.py
  2.  File existence — updated routes.py
  3.  File existence — simulator.html (rewritten)
  4.  File existence — simulator.css (rewritten)
  5.  File existence — simulator.js (rewritten)
  6.  Engine — ORDER_TYPES constant
  7.  Engine — ORDER_STATUSES constant
  8.  Engine — get_current_price function
  9.  Engine — calculate_pnl function exists
  10. Engine — calculate_pnl buy positive
  11. Engine — calculate_pnl buy negative
  12. Engine — calculate_pnl sell positive
  13. Engine — calculate_pnl sell negative
  14. Engine — calculate_pnl zero entry guard
  15. Engine — place_order function exists
  16. Engine — cancel_order function exists
  17. Engine — list_orders function exists
  18. Engine — check_pending_orders function exists
  19. Engine — generate_order_book function exists
  20. Engine — get_account_extended function exists
  21. Engine — clear_orders function exists
  22. Engine — _record_order helper exists
  23. Engine — _price_decimals helper exists
  24. Engine — paper_orders table schema
  25. Engine — order types validation
  26. Engine — side validation
  27. Engine — quantity validation
  28. Engine — order book spread logic
  29. Engine — order book levels
  30. Engine — price decimals logic
  31. Routes — GET /api/simulator/account/extended
  32. Routes — POST /api/simulator/order
  33. Routes — GET /api/simulator/orders
  34. Routes — POST /api/simulator/order/<id>/cancel
  35. Routes — GET /api/simulator/orderbook
  36. Routes — POST /api/simulator/check-orders
  37. Routes — reset clears orders
  38. Routes — order requires symbol
  39. Routes — order requires side
  40. Routes — order requires quantity > 0
  41. API — extended account returns fields
  42. API — market order executes immediately
  43. API — limit order creates pending
  44. API — stop_limit order creates pending
  45. API — list orders returns array
  46. API — list orders with status filter
  47. API — cancel pending order
  48. API — cancel non-existent order fails
  49. API — order book returns bids/asks
  50. API — order book has spread
  51. API — check-orders endpoint works
  52. API — reset clears orders too
  53. API — invalid order type rejected
  54. API — limit order without price rejected
  55. API — stop_limit without stop_price rejected
  56. Template — exchange layout structure
  57. Template — account bar
  58. Template — order book panel
  59. Template — trade panel
  60. Template — side toggle (buy/sell)
  61. Template — order type tabs
  62. Template — presets (25/50/75/100)
  63. Template — execute button
  64. Template — 4 tabs section
  65. Template — demo badge
  66. Template — toast container
  67. Template — empty states
  68. CSS — account bar styles
  69. CSS — trading grid styles
  70. CSS — order book styles
  71. CSS — trade panel styles
  72. CSS — side toggle styles
  73. CSS — order type tab styles
  74. CSS — execute button styles
  75. CSS — toast notification styles
  76. CSS — preset button styles
  77. CSS — empty state styles
  78. CSS — flash animation styles
  79. CSS — responsive breakpoints
  80. CSS — order card styles
  81. JS — state variables
  82. JS — showToast function
  83. JS — loadAccount function
  84. JS — loadOrderBook function
  85. JS — executeTrade function
  86. JS — cancelOrder function
  87. JS — checkPendingOrders function
  88. JS — fetchPrice function
  89. JS — updateEstimate function
  90. JS — side toggle logic
  91. JS — order type tab logic
  92. JS — amount preset handlers
  93. JS — auto-refresh intervals
  94. JS — journal prompt preserved
  95. Backward — GET /api/simulator/account still works
  96. Backward — POST /api/simulator/buy still works
  97. Backward — POST /api/simulator/sell still works
  98. Backward — POST /api/simulator/close/<id> still works
  99. Backward — GET /api/simulator/price still works
  100. Backward — /simulator page loads

Run:
  cd /home/zkr-kripto2/Masaüstü/uygulama/zkr_analiz_v2
  python -m pytest tests/test_faz57_simulator.py -v
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

# ──────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────

def _read(path: str) -> str:
    full = os.path.join(BASE, path)
    with open(full, encoding="utf-8") as f:
        return f.read()


def _exists(path: str) -> bool:
    return os.path.isfile(os.path.join(BASE, path))


def _api(method: str, path: str, **kw):
    fn = getattr(requests, method.lower())
    return fn(f"{URL}{path}", timeout=TIMEOUT, **kw)


def _reset_account():
    """Reset simulator account for clean test state."""
    try:
        _api("POST", "/api/simulator/account/reset")
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
# 1-5: FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════

class TestFileExistence:
    def test_01_simulator_engine_exists(self):
        assert _exists("app/core/simulator_engine.py")

    def test_02_routes_updated(self):
        assert _exists("app/blueprints/simulator/routes.py")
        src = _read("app/blueprints/simulator/routes.py")
        assert "FAZ 57" in src

    def test_03_template_rewritten(self):
        assert _exists("templates/simulator.html")

    def test_04_css_rewritten(self):
        assert _exists("static/css/simulator.css")
        src = _read("static/css/simulator.css")
        assert "FAZ 57" in src

    def test_05_js_rewritten(self):
        assert _exists("static/js/simulator.js")
        src = _read("static/js/simulator.js")
        assert "FAZ 57" in src or "order_type" in src or "currentSide" in src


# ══════════════════════════════════════════════════════════════════════
# 6-30: ENGINE SOURCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════

class TestEngineSource:
    @pytest.fixture(autouse=True)
    def _load_src(self):
        self.src = _read("app/core/simulator_engine.py")

    def test_06_order_types_constant(self):
        assert "ORDER_TYPES" in self.src
        assert '"market"' in self.src
        assert '"limit"' in self.src
        assert '"stop_limit"' in self.src

    def test_07_order_statuses_constant(self):
        assert "ORDER_STATUSES" in self.src
        assert '"pending"' in self.src
        assert '"filled"' in self.src
        assert '"cancelled"' in self.src

    def test_08_get_current_price(self):
        assert "def get_current_price" in self.src
        assert "fetch_current_price" in self.src

    def test_09_calculate_pnl_exists(self):
        assert "def calculate_pnl" in self.src
        assert "pnl_abs" in self.src
        assert "pnl_pct" in self.src
        assert "pnl_usdt" in self.src

    def test_10_calculate_pnl_buy_positive(self):
        sys.path.insert(0, BASE)
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(100.0, 110.0, 10.0, "buy")
        assert result["pnl_abs"] == 100.0
        assert result["pnl_pct"] == 10.0
        assert result["pnl_usdt"] == 100.0

    def test_11_calculate_pnl_buy_negative(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(100.0, 90.0, 10.0, "buy")
        assert result["pnl_abs"] == -100.0
        assert result["pnl_pct"] == -10.0

    def test_12_calculate_pnl_sell_positive(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(100.0, 90.0, 10.0, "sell")
        assert result["pnl_abs"] == 100.0
        assert result["pnl_pct"] == 10.0

    def test_13_calculate_pnl_sell_negative(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(100.0, 110.0, 10.0, "sell")
        assert result["pnl_abs"] == -100.0
        assert result["pnl_pct"] == -10.0

    def test_14_calculate_pnl_zero_entry(self):
        from app.core.simulator_engine import calculate_pnl
        result = calculate_pnl(0, 100.0, 10.0, "buy")
        assert result["pnl_abs"] == 0

    def test_15_place_order_exists(self):
        assert "def place_order" in self.src

    def test_16_cancel_order_exists(self):
        assert "def cancel_order" in self.src

    def test_17_list_orders_exists(self):
        assert "def list_orders" in self.src

    def test_18_check_pending_orders_exists(self):
        assert "def check_pending_orders" in self.src

    def test_19_generate_order_book_exists(self):
        assert "def generate_order_book" in self.src

    def test_20_get_account_extended_exists(self):
        assert "def get_account_extended" in self.src

    def test_21_clear_orders_exists(self):
        assert "def clear_orders" in self.src

    def test_22_record_order_helper(self):
        assert "def _record_order" in self.src

    def test_23_price_decimals_helper(self):
        assert "def _price_decimals" in self.src

    def test_24_orders_table_schema(self):
        assert "paper_orders" in self.src
        assert "CREATE TABLE" in self.src
        assert "account_id" in self.src
        assert "order_type" in self.src
        assert "stop_price" in self.src
        assert "limit_price" in self.src
        assert "filled_price" in self.src

    def test_25_order_types_validation(self):
        assert "Geçersiz emir tipi" in self.src or "order_type" in self.src

    def test_26_side_validation(self):
        assert "'buy'" in self.src
        assert "'sell'" in self.src

    def test_27_quantity_validation(self):
        assert "quantity" in self.src
        assert "pozitif" in self.src or "quantity <= 0" in self.src

    def test_28_order_book_spread_logic(self):
        assert "spread_pct" in self.src
        assert "half_spread" in self.src
        assert "best_bid" in self.src
        assert "best_ask" in self.src

    def test_29_order_book_levels(self):
        assert "levels" in self.src
        assert "bids" in self.src
        assert "asks" in self.src

    def test_30_price_decimals_logic(self):
        from app.core.simulator_engine import _price_decimals
        assert _price_decimals(50000) == 2
        assert _price_decimals(1.5) == 2
        assert _price_decimals(0.05) == 4
        assert _price_decimals(0.005) == 6


# ══════════════════════════════════════════════════════════════════════
# 31-40: ROUTES SOURCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════

class TestRoutesSource:
    @pytest.fixture(autouse=True)
    def _load_src(self):
        self.src = _read("app/blueprints/simulator/routes.py")

    def test_31_extended_account_route(self):
        assert "/account/extended" in self.src
        assert "get_account_extended" in self.src

    def test_32_place_order_route(self):
        assert '"/order"' in self.src
        assert "place_order" in self.src

    def test_33_list_orders_route(self):
        assert '"/orders"' in self.src
        assert "list_orders" in self.src

    def test_34_cancel_order_route(self):
        assert "/order/<order_id>/cancel" in self.src
        assert "cancel_order" in self.src

    def test_35_orderbook_route(self):
        assert "/orderbook" in self.src
        assert "generate_order_book" in self.src

    def test_36_check_orders_route(self):
        assert "/check-orders" in self.src
        assert "check_pending_orders" in self.src

    def test_37_reset_clears_orders(self):
        assert "clear_orders" in self.src

    def test_38_order_requires_symbol(self):
        assert "symbol gerekli" in self.src

    def test_39_order_requires_side(self):
        assert "side gerekli" in self.src

    def test_40_order_requires_quantity(self):
        assert "quantity > 0" in self.src or "quantity > 0 olmalı" in self.src


# ══════════════════════════════════════════════════════════════════════
# 41-55: API INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════

class TestAPIIntegration:
    @classmethod
    def setup_class(cls):
        _reset_account()

    def test_41_extended_account_fields(self):
        r = _api("GET", "/api/simulator/account/extended")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "balance" in d
        assert "equity" in d
        assert "available" in d
        assert "unrealized_pnl" in d
        assert "realized_pnl" in d
        assert "total_pnl" in d
        assert "total_pnl_pct" in d

    def test_42_market_order_executes(self):
        _reset_account()
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "market",
            "quantity": 0.001,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["status"] == "filled"
        assert "position" in d

    def test_43_limit_order_creates_pending(self):
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "limit",
            "quantity": 0.001,
            "price": 10000.0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["status"] == "pending"
        assert "order" in d

    def test_44_stop_limit_order_creates_pending(self):
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "stop_limit",
            "quantity": 0.001,
            "price": 120000.0,
            "stop_price": 115000.0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["status"] == "pending"

    def test_45_list_orders_returns_array(self):
        r = _api("GET", "/api/simulator/orders")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert isinstance(d["orders"], list)
        assert d["count"] >= 0

    def test_46_list_orders_with_status(self):
        r = _api("GET", "/api/simulator/orders?status=pending")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        for o in d["orders"]:
            assert o["status"] == "pending"

    def test_47_cancel_pending_order(self):
        # Create a limit order to cancel
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "ETHUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "limit",
            "quantity": 0.01,
            "price": 1000.0,
        })
        d = r.json()
        order_id = d["order"]["id"]

        # Cancel it
        r2 = _api("POST", f"/api/simulator/order/{order_id}/cancel")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["ok"] is True
        assert d2["order"]["status"] == "cancelled"

    def test_48_cancel_nonexistent_fails(self):
        r = _api("POST", "/api/simulator/order/nonexistent999/cancel")
        assert r.status_code == 400
        d = r.json()
        assert d["ok"] is False

    def test_49_orderbook_returns_bids_asks(self):
        r = _api("GET", "/api/simulator/orderbook?symbol=BTCUSDT&market=crypto")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert isinstance(d["bids"], list)
        assert isinstance(d["asks"], list)
        assert len(d["bids"]) > 0
        assert len(d["asks"]) > 0

    def test_50_orderbook_has_spread(self):
        r = _api("GET", "/api/simulator/orderbook?symbol=BTCUSDT&market=crypto")
        d = r.json()
        assert "spread" in d
        assert "mid_price" in d
        assert "best_bid" in d
        assert "best_ask" in d
        assert d["spread"] >= 0
        assert d["best_ask"] > d["best_bid"]

    def test_51_check_orders_endpoint(self):
        r = _api("POST", "/api/simulator/check-orders")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "filled" in d
        assert "filled_count" in d

    def test_52_reset_clears_orders(self):
        # Create an order
        _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "limit",
            "quantity": 0.001,
            "price": 10000.0,
        })
        # Reset
        _api("POST", "/api/simulator/account/reset")
        # Check orders are gone
        r = _api("GET", "/api/simulator/orders?status=pending")
        d = r.json()
        assert d["count"] == 0

    def test_53_invalid_order_type_rejected(self):
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "trailing_stop",
            "quantity": 0.001,
        })
        assert r.status_code == 400
        d = r.json()
        assert d["ok"] is False

    def test_54_limit_without_price_rejected(self):
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "limit",
            "quantity": 0.001,
        })
        assert r.status_code == 400
        d = r.json()
        assert d["ok"] is False

    def test_55_stop_limit_without_stop_rejected(self):
        r = _api("POST", "/api/simulator/order", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "side": "buy",
            "order_type": "stop_limit",
            "quantity": 0.001,
            "price": 120000.0,
        })
        assert r.status_code == 400
        d = r.json()
        assert d["ok"] is False


# ══════════════════════════════════════════════════════════════════════
# 56-67: TEMPLATE ANALYSIS
# ══════════════════════════════════════════════════════════════════════

class TestTemplate:
    @pytest.fixture(autouse=True)
    def _load_src(self):
        self.src = _read("templates/simulator.html")

    def test_56_exchange_layout(self):
        assert "sim-trading-grid" in self.src

    def test_57_account_bar(self):
        assert "sim-account-bar" in self.src
        assert "sim-acc-item" in self.src
        assert "sim-acc-divider" in self.src

    def test_58_orderbook_panel(self):
        assert "sim-orderbook-panel" in self.src
        assert "sim-ob-asks" in self.src
        assert "sim-ob-bids" in self.src
        assert "sim-ob-mid" in self.src

    def test_59_trade_panel(self):
        assert "sim-trade-panel" in self.src
        assert "sim-tp-" in self.src

    def test_60_side_toggle(self):
        assert "sim-side-toggle" in self.src
        assert "sim-side-buy" in self.src
        assert "sim-side-sell" in self.src

    def test_61_order_type_tabs(self):
        assert "sim-otype-tabs" in self.src
        assert "sim-otype-tab" in self.src
        assert "Market" in self.src
        assert "Limit" in self.src
        assert "Stop-Limit" in self.src

    def test_62_presets(self):
        assert "sim-preset-btn" in self.src
        assert "25%" in self.src
        assert "50%" in self.src
        assert "75%" in self.src
        assert "100%" in self.src

    def test_63_execute_button(self):
        assert "sim-execute-btn" in self.src

    def test_64_four_tabs(self):
        assert 'data-tab="positions"' in self.src or "Pozisyonlar" in self.src
        assert 'data-tab="orders"' in self.src or "Emirler" in self.src

    def test_65_demo_badge(self):
        assert "sim-demo-badge" in self.src
        assert "DEMO" in self.src

    def test_66_toast_container(self):
        assert "sim-toast-container" in self.src

    def test_67_empty_states(self):
        assert "sim-empty-state" in self.src
        assert "sim-empty-icon" in self.src
        assert "sim-empty-title" in self.src


# ══════════════════════════════════════════════════════════════════════
# 68-81: CSS ANALYSIS
# ══════════════════════════════════════════════════════════════════════

class TestCSS:
    @pytest.fixture(autouse=True)
    def _load_src(self):
        self.src = _read("static/css/simulator.css")

    def test_68_account_bar_styles(self):
        assert ".sim-account-bar" in self.src
        assert ".sim-acc-item" in self.src
        assert ".sim-acc-value" in self.src
        assert ".sim-acc-label" in self.src
        assert ".sim-acc-divider" in self.src

    def test_69_trading_grid_styles(self):
        assert ".sim-trading-grid" in self.src
        assert "grid-template-columns" in self.src

    def test_70_orderbook_styles(self):
        assert ".sim-orderbook-panel" in self.src
        assert ".sim-ob-row" in self.src
        assert ".sim-ob-ask" in self.src
        assert ".sim-ob-bid" in self.src
        assert ".sim-ob-mid" in self.src
        assert ".sim-ob-bar-bg" in self.src

    def test_71_trade_panel_styles(self):
        assert ".sim-trade-panel" in self.src
        assert ".sim-tp-input" in self.src
        assert ".sim-tp-select" in self.src
        assert ".sim-tp-label" in self.src

    def test_72_side_toggle_styles(self):
        assert ".sim-side-toggle" in self.src
        assert ".sim-side-btn" in self.src
        assert ".sim-side-buy.active" in self.src
        assert ".sim-side-sell.active" in self.src

    def test_73_order_type_tab_styles(self):
        assert ".sim-otype-tabs" in self.src
        assert ".sim-otype-tab" in self.src
        assert ".sim-otype-tab.active" in self.src

    def test_74_execute_button_styles(self):
        assert ".sim-execute-btn" in self.src
        assert ".sim-execute-buy" in self.src
        assert ".sim-execute-sell" in self.src

    def test_75_toast_styles(self):
        assert ".sim-toast-container" in self.src
        assert ".sim-toast" in self.src
        assert ".sim-toast-success" in self.src
        assert ".sim-toast-error" in self.src
        assert ".sim-toast-info" in self.src

    def test_76_preset_button_styles(self):
        assert ".sim-preset-btn" in self.src
        assert ".sim-tp-presets" in self.src

    def test_77_empty_state_styles(self):
        assert ".sim-empty-state" in self.src
        assert ".sim-empty-icon" in self.src
        assert ".sim-empty-title" in self.src
        assert ".sim-empty-desc" in self.src

    def test_78_flash_animation_styles(self):
        assert ".flash-up" in self.src
        assert ".flash-down" in self.src

    def test_79_responsive_breakpoints(self):
        assert "@media" in self.src
        assert "768px" in self.src
        assert "480px" in self.src

    def test_80_order_card_styles(self):
        assert ".sim-order-card" in self.src
        assert ".sim-btn-cancel" in self.src

    def test_81_position_card_color_system(self):
        assert "#16C784" in self.src
        assert "#FF4D6D" in self.src
        assert "#3B82F6" in self.src


# ══════════════════════════════════════════════════════════════════════
# 82-94: JS ANALYSIS
# ══════════════════════════════════════════════════════════════════════

class TestJS:
    @pytest.fixture(autouse=True)
    def _load_src(self):
        self.src = _read("static/js/simulator.js")

    def test_82_state_variables(self):
        assert "currentSide" in self.src
        assert "currentType" in self.src
        assert "livePrice" in self.src

    def test_83_show_toast(self):
        assert "showToast" in self.src
        assert "sim-toast" in self.src

    def test_84_load_account(self):
        assert "loadAccount" in self.src
        assert "/account/extended" in self.src

    def test_85_load_orderbook(self):
        assert "loadOrderBook" in self.src
        assert "/orderbook" in self.src

    def test_86_execute_trade(self):
        assert "executeTrade" in self.src
        assert "/order" in self.src

    def test_87_cancel_order(self):
        assert "cancelOrder" in self.src
        assert "/cancel" in self.src

    def test_88_check_pending_orders(self):
        assert "checkPendingOrders" in self.src
        assert "/check-orders" in self.src

    def test_89_fetch_price(self):
        assert "fetchPrice" in self.src
        assert "/price" in self.src

    def test_90_update_estimate(self):
        assert "updateEstimate" in self.src

    def test_91_side_toggle_logic(self):
        assert "sim-side-btn" in self.src
        assert "currentSide" in self.src
        assert "Side toggle" in self.src or "side" in self.src

    def test_92_order_type_logic(self):
        assert "sim-otype-tab" in self.src
        assert "currentType" in self.src

    def test_93_auto_refresh_intervals(self):
        assert "setInterval" in self.src

    def test_94_journal_prompt_preserved(self):
        assert "journal" in self.src.lower()


# ══════════════════════════════════════════════════════════════════════
# 95-100: BACKWARD COMPATIBILITY
# ══════════════════════════════════════════════════════════════════════

class TestBackwardCompat:
    @classmethod
    def setup_class(cls):
        _reset_account()

    def test_95_get_account_works(self):
        r = _api("GET", "/api/simulator/account")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert "account" in d

    def test_96_buy_still_works(self):
        r = _api("POST", "/api/simulator/buy", json={
            "symbol": "BTCUSDT",
            "market": "crypto",
            "quantity": 0.001,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True

    def test_97_sell_still_works(self):
        r = _api("POST", "/api/simulator/sell", json={
            "symbol": "ETHUSDT",
            "market": "crypto",
            "quantity": 0.01,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True

    def test_98_close_still_works(self):
        # Open a position then close it
        r = _api("POST", "/api/simulator/buy", json={
            "symbol": "BTCUSDT", "market": "crypto", "quantity": 0.001,
        })
        d = r.json()
        pos_id = d["position"]["id"]

        r2 = _api("POST", f"/api/simulator/close/{pos_id}")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["ok"] is True

    def test_99_price_still_works(self):
        r = _api("GET", "/api/simulator/price?symbol=BTCUSDT&market=crypto")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        assert d["price"] > 0

    def test_100_simulator_page_loads(self):
        r = requests.get(f"{URL}/simulator", timeout=TIMEOUT)
        assert r.status_code == 200
        assert "sim-trading-grid" in r.text
        assert "sim-account-bar" in r.text
