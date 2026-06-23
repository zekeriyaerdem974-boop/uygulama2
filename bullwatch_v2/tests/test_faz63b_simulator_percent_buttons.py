# -*- coding: utf-8 -*-
"""FAZ 63B — Simulator Percentage Quick Amount Buttons Fix Tests.

45+ tests covering:
- %25/%50/%75/%100 button HTML existence
- Click handler logic in simulator.js
- Active button highlight CSS
- Balance reading from accountData.available
- Effective price selection (market vs limit)
- Smart decimal precision per asset price
- Preview text element & logic
- Clear active on manual input
- Toast on missing price/balance
- Sell mode support
- No NaN/undefined/broken values
"""
import os
import re
import sys
import unittest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

JS_FILE = os.path.join(BASE, "static", "js", "simulator.js")
CSS_FILE = os.path.join(BASE, "static", "css", "simulator.css")
HTML_FILE = os.path.join(BASE, "templates", "simulator.html")


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ══════════════════════════════════════════════════════════════════
# 1) HTML — Percentage Button Elements
# ══════════════════════════════════════════════════════════════════

class TestPresetButtonsHTML(unittest.TestCase):
    """Verify percentage buttons exist in simulator.html."""

    @classmethod
    def setUpClass(cls):
        cls.html = _read(HTML_FILE)

    def test_25pct_button(self):
        self.assertIn('data-pct="25"', self.html)

    def test_50pct_button(self):
        self.assertIn('data-pct="50"', self.html)

    def test_75pct_button(self):
        self.assertIn('data-pct="75"', self.html)

    def test_100pct_button(self):
        self.assertIn('data-pct="100"', self.html)

    def test_preset_btn_class(self):
        self.assertIn("sim-preset-btn", self.html)

    def test_presets_container(self):
        self.assertIn("sim-tp-presets", self.html)

    def test_preview_element(self):
        self.assertIn('id="sim-preset-preview"', self.html)

    def test_preview_class(self):
        self.assertIn("sim-preset-preview", self.html)

    def test_quantity_input(self):
        self.assertIn('id="sim-quantity"', self.html)

    def test_est_cost_display(self):
        self.assertIn('id="sim-est-cost"', self.html)


# ══════════════════════════════════════════════════════════════════
# 2) JS — Click Handler Logic
# ══════════════════════════════════════════════════════════════════

class TestPresetClickHandler(unittest.TestCase):
    """Verify percentage button click handler has correct logic."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_handler_bound(self):
        self.assertIn('.sim-preset-btn', self.js)
        self.assertIn('addEventListener("click"', self.js)

    def test_reads_pct_from_dataset(self):
        self.assertIn("btn.dataset.pct", self.js)

    def test_reads_available_balance(self):
        self.assertIn("accountData.available", self.js)

    def test_fee_buffer(self):
        self.assertIn("0.999", self.js)

    def test_calls_update_estimate(self):
        # After setting quantity, must call updateEstimate
        idx = self.js.index("$quantity.value = qty")
        snippet = self.js[idx:idx + 400]
        self.assertIn("updateEstimate()", snippet)

    def test_no_nan_guard(self):
        self.assertIn("isNaN(qty)", self.js)

    def test_zero_qty_guard(self):
        self.assertIn("qty <= 0", self.js)


# ══════════════════════════════════════════════════════════════════
# 3) JS — Effective Price Selection
# ══════════════════════════════════════════════════════════════════

class TestEffectivePrice(unittest.TestCase):
    """Verify getEffectivePrice uses limit price when in limit mode."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_getEffectivePrice_defined(self):
        self.assertIn("function getEffectivePrice()", self.js)

    def test_uses_limit_price_when_not_market(self):
        idx = self.js.index("function getEffectivePrice()")
        snippet = self.js[idx:idx + 300]
        self.assertIn('currentType !== "market"', snippet)
        self.assertIn("$limitPrice.value", snippet)

    def test_fallback_to_live_price(self):
        idx = self.js.index("function getEffectivePrice()")
        snippet = self.js[idx:idx + 400]
        self.assertIn("livePrice", snippet)
        # FAZ 64B: now returns livePrice with lastGoodPrice fallback
        self.assertIn("lastGoodPrice", snippet)

    def test_preset_click_uses_effective_price(self):
        # The click handler should call getEffectivePrice(), not use livePrice directly
        found = re.search(r'addEventListener.*click.*\{.*getEffectivePrice\(\)', self.js, re.S)
        self.assertIsNotNone(found)

    def test_update_estimate_uses_effective_price(self):
        idx = self.js.index("function updateEstimate()")
        snippet = self.js[idx:idx + 300]
        self.assertIn("getEffectivePrice()", snippet)


# ══════════════════════════════════════════════════════════════════
# 4) JS — Smart Decimal Precision
# ══════════════════════════════════════════════════════════════════

class TestDecimalPrecision(unittest.TestCase):
    """Verify qtyDecimals function provides correct precision per asset price."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_qty_decimals_defined(self):
        self.assertIn("function qtyDecimals(price)", self.js)

    def test_btc_level_6_decimals(self):
        idx = self.js.index("function qtyDecimals(price)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("10000", snippet)
        self.assertIn("return 6", snippet)

    def test_eth_level_5_decimals(self):
        idx = self.js.index("function qtyDecimals(price)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("return 5", snippet)

    def test_low_price_level(self):
        idx = self.js.index("function qtyDecimals(price)")
        snippet = self.js[idx:idx + 300]
        self.assertIn("return 4", snippet)

    def test_toFixed_used_with_decimals(self):
        self.assertIn("toFixed(dec)", self.js)


# ══════════════════════════════════════════════════════════════════
# 5) JS — Active Button State
# ══════════════════════════════════════════════════════════════════

class TestActiveButtonState(unittest.TestCase):
    """Verify active button highlighting on click and clear on manual edit."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_active_class_added(self):
        self.assertIn('btn.classList.add("active")', self.js)

    def test_clear_preset_active_defined(self):
        self.assertIn("function clearPresetActive()", self.js)

    def test_clear_removes_active_class(self):
        idx = self.js.index("function clearPresetActive()")
        snippet = self.js[idx:idx + 200]
        self.assertIn('classList.remove("active")', snippet)

    def test_clear_on_manual_input(self):
        # quantity input listener should call clearPresetActive
        idx = self.js.index('$quantity.addEventListener("input"')
        snippet = self.js[idx:idx + 200]
        self.assertIn("clearPresetActive()", snippet)

    def test_active_preset_pct_tracked(self):
        self.assertIn("activePresetPct", self.js)


# ══════════════════════════════════════════════════════════════════
# 6) JS — Preview Text
# ══════════════════════════════════════════════════════════════════

class TestPreviewText(unittest.TestCase):
    """Verify preview text shows used balance and approximate quantity."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_update_preview_defined(self):
        self.assertIn("function updatePresetPreview(", self.js)

    def test_preview_element_referenced(self):
        self.assertIn("sim-preset-preview", self.js)

    def test_preview_shows_balance_text(self):
        self.assertIn("Kullanılacak:", self.js)

    def test_preview_shows_quantity_text(self):
        self.assertIn("Yaklaşık:", self.js)

    def test_preview_visible_class(self):
        self.assertIn('classList.add("visible")', self.js)

    def test_preview_cleared_on_manual_input(self):
        idx = self.js.index('$quantity.addEventListener("input"')
        snippet = self.js[idx:idx + 200]
        self.assertIn("updatePresetPreview(0, 0)", snippet)


# ══════════════════════════════════════════════════════════════════
# 7) JS — Error Toasts
# ══════════════════════════════════════════════════════════════════

class TestErrorToasts(unittest.TestCase):
    """Verify toast messages on missing price/balance."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_toast_on_no_price(self):
        self.assertIn("Fiyat verisi alınamadı", self.js)

    def test_toast_on_no_balance(self):
        self.assertIn("Bakiye bilgisi yüklenemedi", self.js)

    def test_toast_on_insufficient_balance(self):
        self.assertIn("Yetersiz bakiye", self.js)

    def test_toast_on_tiny_quantity(self):
        self.assertIn("Hesaplanan miktar çok küçük", self.js)


# ══════════════════════════════════════════════════════════════════
# 8) CSS — Active Button Styles
# ══════════════════════════════════════════════════════════════════

class TestPresetCSS(unittest.TestCase):
    """Verify CSS styles for preset buttons and active state."""

    @classmethod
    def setUpClass(cls):
        cls.css = _read(CSS_FILE)

    def test_preset_btn_base_style(self):
        self.assertIn(".sim-preset-btn", self.css)

    def test_preset_btn_hover(self):
        self.assertIn(".sim-preset-btn:hover", self.css)

    def test_preset_btn_active_style(self):
        self.assertIn(".sim-preset-btn.active", self.css)

    def test_active_has_green_color(self):
        idx = self.css.index(".sim-preset-btn.active")
        snippet = self.css[idx:idx + 200]
        self.assertIn("#16C784", snippet)

    def test_preview_css_exists(self):
        self.assertIn(".sim-preset-preview", self.css)

    def test_preview_visible_opacity(self):
        self.assertIn(".sim-preset-preview.visible", self.css)


# ══════════════════════════════════════════════════════════════════
# 9) JS — Buy/Sell Mode Support
# ══════════════════════════════════════════════════════════════════

class TestBuySellModes(unittest.TestCase):
    """Verify percentage buttons work in both buy and sell modes."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)

    def test_current_side_state(self):
        self.assertIn('currentSide = "buy"', self.js)

    def test_side_toggle_buttons(self):
        self.assertIn("sim-side-btn", self.js)

    def test_side_stored_on_click(self):
        self.assertIn("currentSide = btn.dataset.side", self.js)

    def test_execute_uses_current_side(self):
        self.assertIn("side: currentSide", self.js)


# ══════════════════════════════════════════════════════════════════
# 10) INTEGRATION — No Broken Features
# ══════════════════════════════════════════════════════════════════

class TestIntegrity(unittest.TestCase):
    """Verify no broken JS/HTML structure."""

    @classmethod
    def setUpClass(cls):
        cls.js = _read(JS_FILE)
        cls.html = _read(HTML_FILE)

    def test_js_iife_structure(self):
        self.assertTrue(self.js.strip().startswith("/*") or self.js.strip().startswith("("))
        self.assertTrue(self.js.strip().endswith("})();"))

    def test_execute_btn_exists(self):
        self.assertIn('id="sim-execute-btn"', self.html)

    def test_trade_msg_exists(self):
        self.assertIn('id="sim-trade-msg"', self.html)

    def test_order_types_supported(self):
        for t in ["market", "limit", "stop_limit"]:
            self.assertIn(f'data-type="{t}"', self.html)

    def test_refresh_all_defined(self):
        self.assertIn("function refreshAll()", self.js)

    def test_load_account_defined(self):
        self.assertIn("async function loadAccount()", self.js)

    def test_load_orders_defined(self):
        self.assertIn("async function loadOrders()", self.js)

    def test_load_order_book_defined(self):
        self.assertIn("async function loadOrderBook()", self.js)


if __name__ == "__main__":
    unittest.main()
