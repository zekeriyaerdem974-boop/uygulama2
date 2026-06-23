# -*- coding: utf-8 -*-
"""FAZ 37 — Legal Safe Mode / Compliance Update tests.

Covers:
  01-05  Compliance filter — signal type conversion
  06-10  Compliance filter — text filtering
  11-15  Compliance filter — API response field renaming
  16-20  Compliance filter — nested / edge cases
  21-25  Copilot system prompt compliance
  26-30  Strategy engine terminology (BULLISH/BEARISH)
  31-35  Disclaimer page + includes
  36-40  Footer + UI terminology checks
  41-45  Marketplace / mentor safety
  46-50  API response filtering (strategy / signals routes)
"""
import json
import os
import sys
import unittest

# ── project root on sys.path ──
_PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT not in sys.path:
    sys.path.insert(0, _PROJECT)

from app.core.compliance_filter import (
    COPILOT_COMPLIANCE_RULE,
    _FIELD_RENAME,
    _SIGNAL_TYPE_MAP,
    _TERM_MAP,
    filter_api_response,
    filter_signal_type,
    filter_text,
    get_disclaimer,
    get_disclaimer_tr,
)

# ── Helper — load template file as string ──
def _read_template(name: str) -> str:
    path = os.path.join(_PROJECT, "templates", name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _read_static(name: str) -> str:
    path = os.path.join(_PROJECT, "static", "js", name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def _read_source(rel_path: str) -> str:
    path = os.path.join(_PROJECT, rel_path)
    with open(path, encoding="utf-8") as f:
        return f.read()


# ═════════════════════════════════════════════════════════════════
# 01-05 — Signal type conversion
# ═════════════════════════════════════════════════════════════════
class TestSignalTypeConversion(unittest.TestCase):
    """01-05"""

    def test_01_buy_to_bullish(self):
        self.assertEqual(filter_signal_type("BUY"), "BULLISH")

    def test_02_sell_to_bearish(self):
        self.assertEqual(filter_signal_type("SELL"), "BEARISH")

    def test_03_lowercase_buy(self):
        self.assertEqual(filter_signal_type("buy"), "bullish")

    def test_04_lowercase_sell(self):
        self.assertEqual(filter_signal_type("sell"), "bearish")

    def test_05_neutral_passthrough(self):
        self.assertEqual(filter_signal_type("NEUTRAL"), "NEUTRAL")


# ═════════════════════════════════════════════════════════════════
# 06-10 — Text filtering
# ═════════════════════════════════════════════════════════════════
class TestTextFiltering(unittest.TestCase):
    """06-10"""

    def test_06_buy_signal_replaced(self):
        result = filter_text("BUY SIGNAL detected")
        self.assertNotIn("BUY SIGNAL", result)
        self.assertIn("BULLISH OUTLOOK", result)

    def test_07_sell_signal_replaced(self):
        result = filter_text("SELL SIGNAL active")
        self.assertNotIn("SELL SIGNAL", result)
        self.assertIn("BEARISH OUTLOOK", result)

    def test_08_trading_signal_replaced(self):
        result = filter_text("New Trading Signal available")
        self.assertNotIn("Trading Signal", result)
        self.assertIn("AI Market Insight", result)

    def test_09_none_passthrough(self):
        self.assertIsNone(filter_text(None))

    def test_10_empty_passthrough(self):
        self.assertEqual(filter_text(""), "")


# ═════════════════════════════════════════════════════════════════
# 11-15 — API response field renaming
# ═════════════════════════════════════════════════════════════════
class TestApiFieldRenaming(unittest.TestCase):
    """11-15"""

    def test_11_entry_price_renamed(self):
        result = filter_api_response({"entry_price": 100.0})
        self.assertIn("analysis_price", result)
        self.assertNotIn("entry_price", result)

    def test_12_exit_price_renamed(self):
        result = filter_api_response({"exit_price": 105.0})
        self.assertIn("close_price", result)
        self.assertNotIn("exit_price", result)

    def test_13_stop_loss_renamed(self):
        result = filter_api_response({"stop_loss": 95.0})
        self.assertIn("risk_level", result)
        self.assertNotIn("stop_loss", result)

    def test_14_take_profit_renamed(self):
        result = filter_api_response({"take_profit": 110.0})
        self.assertIn("target_level", result)
        self.assertNotIn("take_profit", result)

    def test_15_tp_sl_fields(self):
        result = filter_api_response({"tp1": 115, "tp2": 120, "suggested_sl": 90})
        self.assertIn("target_1", result)
        self.assertIn("target_2", result)
        self.assertIn("suggested_risk_level", result)


# ═════════════════════════════════════════════════════════════════
# 16-20 — Nested / edge cases
# ═════════════════════════════════════════════════════════════════
class TestNestedEdgeCases(unittest.TestCase):
    """16-20"""

    def test_16_nested_dict_filtering(self):
        data = {"trade": {"entry_price": 50, "exit_price": 55}}
        result = filter_api_response(data)
        self.assertIn("analysis_price", result["trade"])
        self.assertIn("close_price", result["trade"])

    def test_17_list_of_trades(self):
        data = {"trades": [
            {"entry_price": 50, "exit_price": 55},
            {"entry_price": 60, "exit_price": 65},
        ]}
        result = filter_api_response(data)
        for t in result["trades"]:
            self.assertIn("analysis_price", t)
            self.assertNotIn("entry_price", t)

    def test_18_signal_type_in_response(self):
        result = filter_api_response({"signal_type": "BUY"})
        self.assertEqual(result["signal_type"], "BULLISH")

    def test_19_non_dict_passthrough(self):
        self.assertEqual(filter_api_response("string"), "string")

    def test_20_all_field_renames_mapped(self):
        expected = {
            "entry_price", "exit_price", "take_profit",
            "stop_loss", "tp1", "tp2", "suggested_sl",
        }
        self.assertEqual(set(_FIELD_RENAME.keys()), expected)


# ═════════════════════════════════════════════════════════════════
# 21-25 — Copilot system prompt compliance
# ═════════════════════════════════════════════════════════════════
class TestCopilotCompliance(unittest.TestCase):
    """21-25"""

    def test_21_copilot_compliance_rule_exists(self):
        self.assertTrue(len(COPILOT_COMPLIANCE_RULE) > 20)
        self.assertIn("financial advice", COPILOT_COMPLIANCE_RULE)

    def test_22_system_prompt_market_analyst(self):
        src = _read_source("app/core/copilot_service.py")
        self.assertIn("AI Market Analyst", src)
        self.assertNotIn("AI Trading Copilot", src)

    def test_23_system_prompt_no_signal_terminology(self):
        src = _read_source("app/core/copilot_service.py")
        self.assertNotIn("sinyaller hakkında", src)

    def test_24_system_prompt_no_buy_sell_rule(self):
        src = _read_source("app/core/copilot_service.py")
        self.assertIn("alım/satım talimatı", src)

    def test_25_system_prompt_watch_levels(self):
        src = _read_source("app/core/copilot_service.py")
        self.assertIn("İZLENECEK SEVİYELER", src)
        self.assertNotIn("ÖNERİLEN ALARMLAR", src)


# ═════════════════════════════════════════════════════════════════
# 26-30 — Strategy engine terminology
# ═════════════════════════════════════════════════════════════════
class TestStrategyTerminology(unittest.TestCase):
    """26-30"""

    def test_26_live_engine_bullish(self):
        src = _read_source("app/core/strategy_live_engine.py")
        self.assertIn('"BULLISH"', src)

    def test_27_live_engine_bearish(self):
        src = _read_source("app/core/strategy_live_engine.py")
        self.assertIn('"BEARISH"', src)

    def test_28_live_engine_no_buy_signal(self):
        src = _read_source("app/core/strategy_live_engine.py")
        # Should not have signal_type = "BUY" anymore
        self.assertNotIn('signal_type = "BUY"', src)
        self.assertNotIn('signal_type = "SELL"', src)

    def test_29_signals_engine_risk_fields(self):
        src = _read_source("app/blueprints/signals/engine.py")
        self.assertIn("suggested_risk_level", src)
        self.assertIn("target_1", src)
        self.assertIn("target_2", src)

    def test_30_universal_signal_risk_fields(self):
        src = _read_source("app/core/universal_signal.py")
        self.assertIn("suggested_risk_level", src)
        self.assertIn("target_1", src)


# ═════════════════════════════════════════════════════════════════
# 31-35 — Disclaimer page + includes
# ═════════════════════════════════════════════════════════════════
class TestDisclaimers(unittest.TestCase):
    """31-35"""

    def test_31_disclaimer_page_exists(self):
        path = os.path.join(_PROJECT, "templates", "disclaimer_page.html")
        self.assertTrue(os.path.isfile(path))

    def test_32_disclaimer_page_content(self):
        content = _read_template("disclaimer_page.html")
        self.assertIn("yatırım tavsiyesi", content)
        self.assertIn("Risk Warning", content)

    def test_33_legal_disclaimer_include(self):
        path = os.path.join(_PROJECT, "templates", "legal_disclaimer.html")
        self.assertTrue(os.path.isfile(path))
        content = _read_template("legal_disclaimer.html")
        self.assertIn("yatırım tavsiyesi", content)

    def test_34_disclaimer_function(self):
        d = get_disclaimer()
        self.assertIn("financial advice", d)
        self.assertIn("market analysis", d)

    def test_35_disclaimer_tr_function(self):
        d = get_disclaimer_tr()
        self.assertIn("yatırım tavsiyesi", d)
        self.assertIn("piyasa analizi", d)


# ═════════════════════════════════════════════════════════════════
# 36-40 — Footer + UI terminology checks
# ═════════════════════════════════════════════════════════════════
class TestFooterAndUITerminology(unittest.TestCase):
    """36-40"""

    def test_36_base_app_footer(self):
        content = _read_template("base_app.html")
        self.assertIn("AI Market Intelligence Platform", content)
        self.assertIn("/disclaimer", content)

    def test_37_base_footer(self):
        content = _read_template("base.html")
        self.assertIn("AI Market Intelligence Platform", content)

    def test_38_signals_js_bullish_bearish(self):
        js = _read_static("strategy_signals.js")
        self.assertIn("BULLISH", js)
        self.assertIn("Bearish", js)
        self.assertNotIn('"BUY" ? "↑ AL"', js)

    def test_39_strategy_signals_css_classes(self):
        html = _read_template("strategy_signals.html")
        self.assertIn(".ss-signal-type.BULLISH", html)
        self.assertIn(".ss-signal-type.BEARISH", html)
        self.assertNotIn(".ss-signal-type.BUY", html)

    def test_40_simulator_button_labels(self):
        html = _read_template("simulator.html")
        self.assertIn("Bullish (Long)", html)
        self.assertIn("Bearish (Short)", html)
        self.assertNotIn("AL (Long)", html)
        self.assertNotIn("SAT (Short)", html)


# ═════════════════════════════════════════════════════════════════
# 41-45 — Marketplace / mentor safety
# ═════════════════════════════════════════════════════════════════
class TestMarketplaceMentorSafety(unittest.TestCase):
    """41-45"""

    def test_41_marketplace_disclaimer(self):
        html = _read_template("marketplace.html")
        self.assertIn("legal_disclaimer.html", html)

    def test_42_marketplace_analysis_tool_banner(self):
        html = _read_template("marketplace.html")
        self.assertIn("not financial advice", html)

    def test_43_marketplace_detail_safety(self):
        html = _read_template("marketplace_detail.html")
        self.assertIn("not financial advice", html)
        self.assertIn("legal_disclaimer.html", html)

    def test_44_mentors_disclaimer(self):
        html = _read_template("mentors.html")
        self.assertIn("legal_disclaimer.html", html)

    def test_45_mentor_profile_disclaimer(self):
        html = _read_template("mentor_profile.html")
        self.assertIn("legal_disclaimer.html", html)


# ═════════════════════════════════════════════════════════════════
# 46-50 — API response filtering (strategy / signals routes)
# ═════════════════════════════════════════════════════════════════
class TestAPIResponseFiltering(unittest.TestCase):
    """46-50"""

    def test_46_strategy_routes_import_filter(self):
        src = _read_source("app/blueprints/strategy/routes.py")
        self.assertIn("from app.core.compliance_filter import filter_api_response", src)

    def test_47_strategy_routes_apply_filter(self):
        src = _read_source("app/blueprints/strategy/routes.py")
        self.assertIn("filter_api_response(result)", src)

    def test_48_signals_routes_import_filter(self):
        src = _read_source("app/blueprints/signals/routes.py")
        self.assertIn("from app.core.compliance_filter import filter_api_response", src)

    def test_49_signals_routes_apply_filter(self):
        src = _read_source("app/blueprints/signals/routes.py")
        self.assertIn("filter_api_response(res)", src)

    def test_50_full_backtest_response_filtered(self):
        """Simulate a backtest-like API response and verify fields are renamed."""
        mock_response = {
            "ok": True,
            "trades": [
                {
                    "entry_price": 100.0,
                    "exit_price": 105.0,
                    "stop_loss": 95.0,
                    "take_profit": 110.0,
                    "quantity": 1.0,
                    "pnl": 5.0,
                    "signal_type": "BUY",
                },
            ],
            "metrics": {"win_rate": 60.0},
        }
        result = filter_api_response(mock_response)
        trade = result["trades"][0]
        self.assertIn("analysis_price", trade)
        self.assertIn("close_price", trade)
        self.assertIn("risk_level", trade)
        self.assertIn("target_level", trade)
        self.assertEqual(trade["signal_type"], "BULLISH")
        self.assertNotIn("entry_price", trade)
        self.assertNotIn("exit_price", trade)
        self.assertEqual(result["metrics"]["win_rate"], 60.0)


if __name__ == "__main__":
    unittest.main()
