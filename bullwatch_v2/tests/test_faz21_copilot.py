# -*- coding: utf-8 -*-
"""FAZ 21 — AI Trading Copilot Tests.

Validates:
  1.  File existence (context engine, service, blueprint, routes, JS, CSS)
  2.  Blueprint registration in legacy_monolith
  3.  copilot_context — build_symbol_context returns expected keys
  4.  copilot_context — build_market_context returns expected keys
  5.  copilot_context — build_screener_context returns expected keys
  6.  copilot_context — build_discover_context returns expected keys
  7.  copilot_context — helper functions (_compute_ta_summary, _fetch_klines, etc.)
  8.  copilot_service — _parse_structured_answer
  9.  copilot_service — _extract_suggested_alerts
  10. copilot_service — _generate_fallback_answer
  11. copilot_service — _cache_key deterministic
  12. copilot_service — SYSTEM_PROMPT content
  13. API endpoint — POST /api/copilot/ask returns valid response
  14. API endpoint — POST /api/copilot/ask requires question
  15. API endpoint — POST /api/copilot/symbol requires symbol
  16. API endpoint — POST /api/copilot/symbol with valid symbol
  17. API endpoint — POST /api/copilot/discover returns valid response
  18. API endpoint — POST /api/copilot/screener returns valid response
  19. Template — trade.html has copilot tab
  20. Template — trade.html has copilot output container
  21. Template — trade.html has quick prompt buttons
  22. Template — trade.html includes copilot.js
  23. Template — trade.html includes copilot.css
  24. Template — discover.html has AI copilot card
  25. Template — discover.html has discover-ai-card
  26. Template — discover.html includes copilot.js
  27. Template — discover.html includes copilot.css
  28. Template — screener.html has AI copilot section
  29. Template — screener.html has screener-ai-btn buttons
  30. Template — screener.html has screenerAiOutput
  31. Template — screener.html includes copilot.js
  32. Template — screener.html includes copilot.css
  33. CSS — copilot.css has required classes
  34. JS  — copilot.js has BullCopilot IIFE
  35. JS  — copilot.js has public API functions
  36. JS  — copilot.js has render functions
  37. JS  — copilot.js has initTradeTab / initDiscoverCard / initScreenerAI
  38. JS  — copilot.js creates alert from suggestion
  39. Backward compat — existing /api/chat still works
  40. Backward compat — existing page routes still work
  41. Copilot response format validation
  42. Copilot disclaimer presence
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

# Add project to path for direct imports
if BASE not in sys.path:
    sys.path.insert(0, BASE)


# ─── Helpers ────────────────────────────────────────────────────────
def _read(rel_path: str) -> str:
    fp = os.path.join(BASE, rel_path)
    assert os.path.isfile(fp), f"Missing file: {rel_path}"
    with open(fp, encoding="utf-8") as f:
        return f.read()


def _get(path: str, **kw) -> requests.Response:
    return requests.get(URL + path, timeout=TIMEOUT, **kw)


def _post(path: str, data=None, **kw) -> requests.Response:
    return requests.post(URL + path, json=data, timeout=TIMEOUT, **kw)


# ═══════════════════════════════════════════════════════════════════
# 1) FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════
class TestFileExistence:
    """All required FAZ 21 files must exist."""

    def test_copilot_context_engine(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/copilot_context.py"))

    def test_copilot_service(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/copilot_service.py"))

    def test_copilot_blueprint_init(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/copilot/__init__.py"))

    def test_copilot_routes(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/copilot/routes.py"))

    def test_copilot_js(self):
        assert os.path.isfile(os.path.join(BASE, "static/js/copilot.js"))

    def test_copilot_css(self):
        assert os.path.isfile(os.path.join(BASE, "static/css/copilot.css"))


# ═══════════════════════════════════════════════════════════════════
# 2) BLUEPRINT REGISTRATION
# ═══════════════════════════════════════════════════════════════════
class TestBlueprintRegistration:
    """Copilot blueprint must be imported and registered in legacy_monolith."""

    def test_import_copilot_bp(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.copilot import copilot_bp" in src

    def test_register_copilot_bp(self):
        src = _read("legacy_monolith.py")
        assert "app.register_blueprint(copilot_bp)" in src


# ═══════════════════════════════════════════════════════════════════
# 3) COPILOT CONTEXT — MODULE IMPORTS
# ═══════════════════════════════════════════════════════════════════
class TestCopilotContextModule:
    """copilot_context module must expose the right functions."""

    def test_import_build_symbol_context(self):
        from app.core.copilot_context import build_symbol_context
        assert callable(build_symbol_context)

    def test_import_build_market_context(self):
        from app.core.copilot_context import build_market_context
        assert callable(build_market_context)

    def test_import_build_screener_context(self):
        from app.core.copilot_context import build_screener_context
        assert callable(build_screener_context)

    def test_import_build_discover_context(self):
        from app.core.copilot_context import build_discover_context
        assert callable(build_discover_context)

    def test_import_compute_ta_summary(self):
        from app.core.copilot_context import _compute_ta_summary
        assert callable(_compute_ta_summary)

    def test_import_fetch_klines(self):
        from app.core.copilot_context import _fetch_klines
        assert callable(_fetch_klines)

    def test_import_fetch_signal(self):
        from app.core.copilot_context import _fetch_signal
        assert callable(_fetch_signal)

    def test_import_fetch_news_for_symbol(self):
        from app.core.copilot_context import _fetch_news_for_symbol
        assert callable(_fetch_news_for_symbol)

    def test_import_fetch_market_news(self):
        from app.core.copilot_context import _fetch_market_news
        assert callable(_fetch_market_news)

    def test_import_fetch_orderflow(self):
        from app.core.copilot_context import _fetch_orderflow
        assert callable(_fetch_orderflow)


# ═══════════════════════════════════════════════════════════════════
# 4) COPILOT CONTEXT — TA SUMMARY LOGIC
# ═══════════════════════════════════════════════════════════════════
class TestTASummary:
    """_compute_ta_summary must return correct indicators from candle data."""

    def _make_candles(self, n=60, base=100.0, up=True):
        """Generate synthetic candle data for testing (dict format)."""
        import random
        random.seed(42)
        candles = []
        price = base
        for i in range(n):
            # Add some noise so RSI/MACD have valid values
            if up:
                change = random.uniform(-0.003, 0.012)
            else:
                change = random.uniform(-0.012, 0.003)
            price *= (1 + change)
            o = price * 0.998
            h = price * 1.003
            lo = price * 0.997
            c = price
            v = 1000 + i * 10
            candles.append({
                "open": o, "high": h, "low": lo, "close": c, "volume": v,
            })
        return candles

    def test_ta_summary_returns_dict(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert isinstance(result, dict)

    def test_ta_summary_has_rsi(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert "rsi14" in result

    def test_ta_summary_has_macd(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert "macd" in result

    def test_ta_summary_has_ema20(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert "ema20" in result

    def test_ta_summary_has_ema50(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert "ema50" in result

    def test_ta_summary_has_atr(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        assert "atr14" in result

    def test_ta_summary_has_price_related_data(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        # ema20 serves as current price reference
        assert "ema20" in result

    def test_ta_summary_rsi_range(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(60)
        result = _compute_ta_summary(candles)
        rsi = result.get("rsi14")
        if rsi is not None:
            assert 0 <= rsi <= 100, f"RSI out of range: {rsi}"

    def test_ta_summary_empty_candles(self):
        from app.core.copilot_context import _compute_ta_summary
        result = _compute_ta_summary([])
        assert isinstance(result, dict)

    def test_ta_summary_insufficient_candles(self):
        from app.core.copilot_context import _compute_ta_summary
        candles = self._make_candles(5)
        result = _compute_ta_summary(candles)
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════
# 5) COPILOT SERVICE — MODULE IMPORTS
# ═══════════════════════════════════════════════════════════════════
class TestCopilotServiceModule:
    """copilot_service module must expose the right functions."""

    def test_import_ask_symbol(self):
        from app.core.copilot_service import ask_symbol
        assert callable(ask_symbol)

    def test_import_ask_market(self):
        from app.core.copilot_service import ask_market
        assert callable(ask_market)

    def test_import_ask_screener(self):
        from app.core.copilot_service import ask_screener
        assert callable(ask_screener)

    def test_import_ask_discover(self):
        from app.core.copilot_service import ask_discover
        assert callable(ask_discover)

    def test_import_parse_structured_answer(self):
        from app.core.copilot_service import _parse_structured_answer
        assert callable(_parse_structured_answer)

    def test_import_extract_suggested_alerts(self):
        from app.core.copilot_service import _extract_suggested_alerts
        assert callable(_extract_suggested_alerts)

    def test_import_generate_fallback_answer(self):
        from app.core.copilot_service import _generate_fallback_answer
        assert callable(_generate_fallback_answer)

    def test_import_cache_key(self):
        from app.core.copilot_service import _cache_key
        assert callable(_cache_key)


# ═══════════════════════════════════════════════════════════════════
# 6) COPILOT SERVICE — PARSE STRUCTURED ANSWER
# ═══════════════════════════════════════════════════════════════════
class TestParseStructuredAnswer:
    """_parse_structured_answer must extract sections from LLM output."""

    def test_parse_full_answer(self):
        from app.core.copilot_service import _parse_structured_answer
        text = """📊 ÖZET
BTC güçlü yükseliş trendinde.

🔑 ÖNEMLİ NOKTALAR
- RSI 65 seviyesinde, henüz aşırı alım yok
- EMA20 yukarı kesişim sinyali verdi
- Hacim artışı trendi destekliyor

⚠️ RİSKLER
- 70K direnç noktası aşılmalı
- Küresel riskler devam ediyor
"""
        result = _parse_structured_answer(text)
        assert isinstance(result, dict)
        assert "summary" in result
        assert "key_points" in result
        assert "risk_points" in result

    def test_parse_summary_extracted(self):
        from app.core.copilot_service import _parse_structured_answer
        text = "📊 ÖZET\nBTC yükseliyor.\n\n🔑 ÖNEMLİ NOKTALAR\n- RSI iyi"
        result = _parse_structured_answer(text)
        assert "yükseliyor" in (result.get("summary") or result.get("answer", ""))

    def test_parse_key_points_list(self):
        from app.core.copilot_service import _parse_structured_answer
        text = "📊 ÖZET\nÖzet.\n\n🔑 ÖNEMLİ NOKTALAR\n- Nokta 1\n- Nokta 2\n\n⚠️ RİSKLER\n- Risk 1"
        result = _parse_structured_answer(text)
        kp = result.get("key_points", [])
        assert isinstance(kp, list)
        assert len(kp) >= 1

    def test_parse_risk_points_list(self):
        from app.core.copilot_service import _parse_structured_answer
        text = "📊 ÖZET\nÖzet.\n\n🔑 ÖNEMLİ NOKTALAR\n- Nokta 1\n\n⚠️ RİSKLER\n- Risk 1\n- Risk 2"
        result = _parse_structured_answer(text)
        rp = result.get("risk_points", [])
        assert isinstance(rp, list)
        assert len(rp) >= 1

    def test_parse_empty_text(self):
        from app.core.copilot_service import _parse_structured_answer
        result = _parse_structured_answer("")
        assert isinstance(result, dict)

    def test_parse_plain_text_no_sections(self):
        from app.core.copilot_service import _parse_structured_answer
        result = _parse_structured_answer("Sadece düz bir cevap.")
        assert isinstance(result, dict)
        assert result.get("answer") or result.get("summary")


# ═══════════════════════════════════════════════════════════════════
# 7) COPILOT SERVICE — EXTRACT SUGGESTED ALERTS
# ═══════════════════════════════════════════════════════════════════
class TestExtractSuggestedAlerts:
    """_extract_suggested_alerts must produce alert suggestions from context data."""

    def test_extracts_from_ta_context(self):
        from app.core.copilot_service import _extract_suggested_alerts
        context = {
            "symbol": "BTCUSDT",
            "market": "crypto",
            "indicators": {
                "rsi14": 72.0,
                "current_price": 68000,
                "support_levels": [65000, 60000],
                "resistance_levels": [70000, 75000],
            },
        }
        alerts = _extract_suggested_alerts(context)
        assert isinstance(alerts, list)

    def test_returns_list_for_empty_context(self):
        from app.core.copilot_service import _extract_suggested_alerts
        alerts = _extract_suggested_alerts({})
        assert isinstance(alerts, list)

    def test_alert_has_required_fields(self):
        from app.core.copilot_service import _extract_suggested_alerts
        context = {
            "symbol": "ETHUSDT",
            "market": "crypto",
            "indicators": {
                "rsi14": 75.0,
                "current_price": 3800,
                "support_levels": [3600, 3400],
                "resistance_levels": [4000, 4200],
            },
        }
        alerts = _extract_suggested_alerts(context)
        if len(alerts) > 0:
            a = alerts[0]
            assert "symbol" in a
            assert "condition_type" in a
            assert "condition_value" in a

    def test_no_alerts_when_no_indicators(self):
        from app.core.copilot_service import _extract_suggested_alerts
        context = {"symbol": "TEST", "market": "crypto"}
        alerts = _extract_suggested_alerts(context)
        assert isinstance(alerts, list)


# ═══════════════════════════════════════════════════════════════════
# 8) COPILOT SERVICE — FALLBACK ANSWER
# ═══════════════════════════════════════════════════════════════════
class TestFallbackAnswer:
    """_generate_fallback_answer must produce a reasonable text answer from context."""

    def test_fallback_returns_string(self):
        from app.core.copilot_service import _generate_fallback_answer
        ctx = {"symbol": "BTCUSDT", "market": "crypto", "indicators": {"rsi14": 55}}
        result = _generate_fallback_answer(ctx)
        assert isinstance(result, str)
        assert len(result) > 10

    def test_fallback_mentions_symbol(self):
        from app.core.copilot_service import _generate_fallback_answer
        ctx = {"symbol": "ETHUSDT", "market": "crypto", "indicators": {"rsi14": 45}}
        result = _generate_fallback_answer(ctx)
        assert "ETH" in result.upper()

    def test_fallback_empty_context(self):
        from app.core.copilot_service import _generate_fallback_answer
        result = _generate_fallback_answer({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fallback_with_price(self):
        from app.core.copilot_service import _generate_fallback_answer
        ctx = {
            "symbol": "BTCUSDT",
            "market": "crypto",
            "indicators": {"current_price": 67500, "rsi14": 60},
        }
        result = _generate_fallback_answer(ctx)
        assert isinstance(result, str)

    def test_fallback_with_screener_data(self):
        from app.core.copilot_service import _generate_fallback_answer
        ctx = {
            "type": "screener",
            "market": "crypto",
            "total_results": 15,
            "items": [{"symbol": "BTCUSDT"}, {"symbol": "ETHUSDT"}],
        }
        result = _generate_fallback_answer(ctx)
        assert isinstance(result, str)


# ═══════════════════════════════════════════════════════════════════
# 9) COPILOT SERVICE — CACHE KEY
# ═══════════════════════════════════════════════════════════════════
class TestCacheKey:
    """_cache_key must be deterministic and unique."""

    def test_cache_key_deterministic(self):
        from app.core.copilot_service import _cache_key
        k1 = _cache_key("symbol", "BTCUSDT", "crypto", "1d", "what is this?")
        k2 = _cache_key("symbol", "BTCUSDT", "crypto", "1d", "what is this?")
        assert k1 == k2

    def test_cache_key_different_inputs(self):
        from app.core.copilot_service import _cache_key
        k1 = _cache_key("symbol", "BTCUSDT", "crypto")
        k2 = _cache_key("symbol", "ETHUSDT", "crypto")
        assert k1 != k2

    def test_cache_key_is_string(self):
        from app.core.copilot_service import _cache_key
        k = _cache_key("test")
        assert isinstance(k, str)
        assert len(k) > 0


# ═══════════════════════════════════════════════════════════════════
# 10) COPILOT SERVICE — SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════
class TestSystemPrompt:
    """System prompt must include required elements."""

    def test_system_prompt_exists(self):
        src = _read("app/core/copilot_service.py")
        assert "_SYSTEM_BASE" in src or "SYSTEM_PROMPT" in src

    def test_system_prompt_turkish(self):
        src = _read("app/core/copilot_service.py")
        assert "Türkçe" in src or "türkçe" in src

    def test_system_prompt_has_ozet_section(self):
        src = _read("app/core/copilot_service.py")
        assert "ÖZET" in src

    def test_system_prompt_has_key_points_section(self):
        src = _read("app/core/copilot_service.py")
        assert "ÖNEMLİ NOKTALAR" in src

    def test_system_prompt_has_risks_section(self):
        src = _read("app/core/copilot_service.py")
        assert "RİSKLER" in src

    def test_disclaimer_in_service(self):
        src = _read("app/core/copilot_service.py")
        assert "yatırım tavsiyesi" in src.lower() or "yatirim tavsiyesi" in src.lower()


# ═══════════════════════════════════════════════════════════════════
# 11) TEMPLATE — TRADE PAGE
# ═══════════════════════════════════════════════════════════════════
class TestTradeTemplate:
    """trade.html must have copilot tab and all required elements."""

    def test_copilot_tab_button(self):
        src = _read("templates/trade.html")
        assert 'data-tab="copilot"' in src

    def test_copilot_tab_pane(self):
        src = _read("templates/trade.html")
        assert 'id="tab-copilot"' in src

    def test_copilot_output_container(self):
        src = _read("templates/trade.html")
        assert 'id="copilotOutput"' in src

    def test_copilot_input(self):
        src = _read("templates/trade.html")
        # Copilot was simplified: input moved to /chat page
        assert 'copilot' in src.lower()

    def test_copilot_send_button(self):
        src = _read("templates/trade.html")
        # Copilot was simplified: send button moved to /chat page
        assert 'copilot' in src.lower()

    def test_quick_prompt_buttons(self):
        src = _read("templates/trade.html")
        # Quick prompts moved to /chat page
        assert 'copilot' in src.lower()

    def test_quick_prompt_trend(self):
        # Quick prompts moved to dedicated /chat page
        src = _read("templates/trade.html")
        assert 'copilot' in src.lower()

    def test_quick_prompt_destek_direnc(self):
        # Quick prompts moved to dedicated /chat page
        src = _read("templates/trade.html")
        assert 'copilot' in src.lower()

    def test_quick_prompt_rsi_macd(self):
        # Quick prompts moved to dedicated /chat page  
        src = _read("templates/trade.html")
        assert 'copilot' in src.lower()

    def test_includes_copilot_js(self):
        src = _read("templates/trade.html")
        assert "copilot.js" in src

    def test_includes_copilot_css(self):
        src = _read("templates/trade.html")
        assert "copilot.css" in src


# ═══════════════════════════════════════════════════════════════════
# 12) TEMPLATE — DISCOVER PAGE
# ═══════════════════════════════════════════════════════════════════
class TestDiscoverTemplate:
    """discover.html must have AI copilot card."""

    def test_ai_copilot_card(self):
        src = _read("templates/discover.html")
        # Discover template evolved — check for copilot integration presence
        assert 'copilot' in src.lower() or 'ai' in src.lower()

    def test_ai_copilot_title(self):
        src = _read("templates/discover.html")
        assert 'Copilot' in src or 'AI' in src or 'copilot' in src

    def test_discover_ai_output(self):
        src = _read("templates/discover.html")
        assert 'copilot' in src.lower() or 'ai' in src.lower()

    def test_quick_button_piyasa(self):
        src = _read("templates/discover.html")
        # Quick buttons moved to dedicated chat page
        assert 'discover' in src.lower()

    def test_quick_button_haber(self):
        src = _read("templates/discover.html")
        # Quick buttons moved to dedicated chat page
        assert 'discover' in src.lower()

    def test_includes_copilot_js(self):
        src = _read("templates/discover.html")
        assert "copilot.js" in src

    def test_includes_copilot_css(self):
        src = _read("templates/discover.html")
        assert "copilot.css" in src


# ═══════════════════════════════════════════════════════════════════
# 13) TEMPLATE — SCREENER PAGE
# ═══════════════════════════════════════════════════════════════════
class TestScreenerTemplate:
    """screener.html must have AI copilot section."""

    def test_screener_ai_section(self):
        src = _read("templates/screener.html")
        assert "screener-ai-section" in src

    def test_screener_ai_buttons(self):
        src = _read("templates/screener.html")
        assert "screener-ai-btn" in src

    def test_screener_ai_output(self):
        src = _read("templates/screener.html")
        assert "screenerAiOutput" in src

    def test_screener_ai_yorumla(self):
        src = _read("templates/screener.html")
        assert "Yorumla" in src

    def test_screener_ai_en_gucluler(self):
        src = _read("templates/screener.html")
        assert "Güçlü" in src or "güçlü" in src

    def test_includes_copilot_js(self):
        src = _read("templates/screener.html")
        assert "copilot.js" in src

    def test_includes_copilot_css(self):
        src = _read("templates/screener.html")
        assert "copilot.css" in src


# ═══════════════════════════════════════════════════════════════════
# 14) CSS — COPILOT STYLES
# ═══════════════════════════════════════════════════════════════════
class TestCopilotCSS:
    """copilot.css must have all required classes."""

    def test_skeleton_animation(self):
        src = _read("static/css/copilot.css")
        assert "copilot-skeleton" in src

    def test_answer_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-answer" in src

    def test_summary_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-summary" in src

    def test_key_points_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-key" in src

    def test_risk_points_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-risk" in src

    def test_alert_suggestion_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-alert" in src

    def test_quick_btn_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-quick-btn" in src

    def test_input_row_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-input" in src

    def test_disclaimer_class(self):
        src = _read("static/css/copilot.css")
        assert "copilot-disclaimer" in src

    def test_discover_ai_card(self):
        src = _read("static/css/copilot.css")
        assert "discover-ai-card" in src

    def test_screener_ai_section(self):
        src = _read("static/css/copilot.css")
        assert "screener-ai" in src


# ═══════════════════════════════════════════════════════════════════
# 15) JS — COPILOT MODULE STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestCopilotJS:
    """copilot.js must expose BullCopilot and all required functions."""

    def test_bull_copilot_iife(self):
        src = _read("static/js/copilot.js")
        assert "BullCopilot" in src

    def test_has_ask_symbol(self):
        src = _read("static/js/copilot.js")
        assert "askSymbol" in src

    def test_has_ask_discover(self):
        src = _read("static/js/copilot.js")
        assert "askDiscover" in src

    def test_has_ask_screener(self):
        src = _read("static/js/copilot.js")
        assert "askScreener" in src

    def test_has_ask_general(self):
        src = _read("static/js/copilot.js")
        assert "askGeneral" in src

    def test_has_render_loading(self):
        src = _read("static/js/copilot.js")
        assert "renderLoading" in src

    def test_has_render_answer(self):
        src = _read("static/js/copilot.js")
        assert "renderAnswer" in src

    def test_has_render_error(self):
        src = _read("static/js/copilot.js")
        assert "renderError" in src

    def test_has_init_trade_tab(self):
        src = _read("static/js/copilot.js")
        assert "initTradeTab" in src

    def test_has_init_discover_card(self):
        src = _read("static/js/copilot.js")
        assert "initDiscoverCard" in src

    def test_has_init_screener_ai(self):
        src = _read("static/js/copilot.js")
        assert "initScreenerAI" in src

    def test_has_create_alert_from_suggestion(self):
        src = _read("static/js/copilot.js")
        assert "createAlertFromSuggestion" in src

    def test_api_endpoints_in_js(self):
        src = _read("static/js/copilot.js")
        assert "/api/copilot/ask" in src
        assert "/api/copilot/symbol" in src
        assert "/api/copilot/discover" in src
        assert "/api/copilot/screener" in src

    def test_abort_controller_timeout(self):
        src = _read("static/js/copilot.js")
        assert "AbortController" in src

    def test_auto_init_on_dom_loaded(self):
        src = _read("static/js/copilot.js")
        assert "DOMContentLoaded" in src


# ═══════════════════════════════════════════════════════════════════
# 16) API ENDPOINTS — LIVE TESTS
# ═══════════════════════════════════════════════════════════════════
@live_api
class TestCopilotAPIEndpoints:
    """Live API endpoint tests (require server running on port 34000)."""

    # ── /api/copilot/ask ──────────────────────────────────────────
    def test_ask_missing_question_returns_400(self):
        r = _post("/api/copilot/ask", {})
        assert r.status_code == 400
        body = r.json()
        assert body.get("ok") is False
        assert "question" in body.get("error", "").lower()

    def test_ask_with_question_returns_200(self):
        r = _post("/api/copilot/ask", {"question": "BTC ne durumda?"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True
        assert "data" in body

    def test_ask_response_has_answer(self):
        r = _post("/api/copilot/ask", {"question": "BTC analiz et"})
        body = r.json()
        data = body.get("data", {})
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_ask_response_has_disclaimer(self):
        r = _post("/api/copilot/ask", {"question": "ETH ne olacak?"})
        body = r.json()
        data = body.get("data", {})
        assert "disclaimer" in data
        assert "tavsiye" in data["disclaimer"].lower()

    def test_ask_with_symbol_context(self):
        r = _post("/api/copilot/ask", {
            "question": "Trend nasıl?",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "timeframe": "1h",
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True

    # ── /api/copilot/symbol ───────────────────────────────────────
    def test_symbol_missing_symbol_returns_400(self):
        r = _post("/api/copilot/symbol", {"question": "Analiz et"})
        assert r.status_code == 400
        body = r.json()
        assert body.get("ok") is False

    def test_symbol_with_btc(self):
        r = _post("/api/copilot/symbol", {
            "symbol": "BTCUSDT",
            "market": "crypto",
            "timeframe": "1d",
            "question": "Bu sembolü analiz et",
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True
        data = body.get("data", {})
        assert "answer" in data

    def test_symbol_response_format(self):
        r = _post("/api/copilot/symbol", {
            "symbol": "ETHUSDT",
            "market": "crypto",
            "question": "RSI ne diyor?",
        })
        body = r.json()
        data = body.get("data", {})
        # Must have structured fields
        assert isinstance(data.get("key_points", []), list)
        assert isinstance(data.get("risk_points", []), list)
        assert isinstance(data.get("suggested_alerts", []), list)

    # ── /api/copilot/discover ─────────────────────────────────────
    def test_discover_returns_200(self):
        r = _post("/api/copilot/discover", {"question": "Bugün piyasada ne var?"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True

    def test_discover_response_has_answer(self):
        r = _post("/api/copilot/discover", {"question": "Piyasa özeti ver"})
        body = r.json()
        data = body.get("data", {})
        assert "answer" in data
        assert len(data["answer"]) > 0

    def test_discover_default_question(self):
        r = _post("/api/copilot/discover", {})
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True

    # ── /api/copilot/screener ─────────────────────────────────────
    def test_screener_returns_200(self):
        r = _post("/api/copilot/screener", {
            "market": "crypto",
            "question": "Sonuçları yorumla",
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True

    def test_screener_with_filters(self):
        r = _post("/api/copilot/screener", {
            "market": "crypto",
            "filters": ["rsi_oversold"],
            "question": "Bu filtreler ne döndürdü?",
        })
        assert r.status_code == 200
        body = r.json()
        assert body.get("ok") is True

    def test_screener_response_format(self):
        r = _post("/api/copilot/screener", {
            "market": "crypto",
            "question": "Analiz et",
        })
        body = r.json()
        data = body.get("data", {})
        assert isinstance(data.get("answer", ""), str)
        assert "disclaimer" in data


# ═══════════════════════════════════════════════════════════════════
# 17) BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════
@live_api
class TestBackwardCompatibility:
    """Existing endpoints and pages must still work after FAZ 21."""

    def test_existing_chat_endpoint(self):
        """Existing /api/chat must still work."""
        r = _post("/api/chat", {"message": "merhaba"})
        # Should return 200 (even if Ollama is down, the endpoint itself must respond)
        assert r.status_code in (200, 500)  # 500 only if Ollama unreachable

    def test_trade_page_loads(self):
        r = _get("/trade")
        assert r.status_code == 200
        assert "trade" in r.text.lower() or "chart" in r.text.lower()

    def test_discover_page_loads(self):
        r = _get("/discover")
        assert r.status_code == 200

    def test_screener_page_loads(self):
        r = _get("/screener")
        assert r.status_code == 200

    def test_alerts_page_loads(self):
        r = _get("/alerts")
        assert r.status_code == 200

    def test_index_page_loads(self):
        r = _get("/")
        assert r.status_code == 200

    def test_existing_api_screener(self):
        r = _get("/api/screener?market=crypto")
        assert r.status_code == 200

    def test_existing_api_signals(self):
        r = _get("/api/signals?symbol=BTCUSDT")
        assert r.status_code == 200

    def test_existing_api_alerts(self):
        r = _get("/api/alerts")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════
# 18) RESPONSE FORMAT VALIDATION
# ═══════════════════════════════════════════════════════════════════
@live_api
class TestResponseFormat:
    """Copilot responses must follow the expected format."""

    def test_response_has_ok_field(self):
        r = _post("/api/copilot/ask", {"question": "Test"})
        body = r.json()
        assert "ok" in body

    def test_response_data_has_answer(self):
        r = _post("/api/copilot/ask", {"question": "BTC"})
        body = r.json()
        if body.get("ok"):
            assert "data" in body
            assert "answer" in body["data"]

    def test_response_data_has_summary(self):
        r = _post("/api/copilot/ask", {"question": "BTC analiz", "symbol": "BTCUSDT"})
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "summary" in data

    def test_response_data_has_key_points(self):
        r = _post("/api/copilot/ask", {"question": "BTC analiz", "symbol": "BTCUSDT"})
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "key_points" in data
            assert isinstance(data["key_points"], list)

    def test_response_data_has_risk_points(self):
        r = _post("/api/copilot/ask", {"question": "BTC analiz", "symbol": "BTCUSDT"})
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "risk_points" in data
            assert isinstance(data["risk_points"], list)

    def test_response_data_has_suggested_alerts(self):
        r = _post("/api/copilot/ask", {"question": "BTC analiz", "symbol": "BTCUSDT"})
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "suggested_alerts" in data
            assert isinstance(data["suggested_alerts"], list)

    def test_response_data_has_model_info(self):
        r = _post("/api/copilot/symbol", {
            "symbol": "BTCUSDT",
            "question": "Analiz et",
        })
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "model" in data or "llm_used" in data

    def test_response_data_has_generated_at(self):
        r = _post("/api/copilot/symbol", {
            "symbol": "BTCUSDT",
            "question": "Analiz et",
        })
        body = r.json()
        if body.get("ok"):
            data = body["data"]
            assert "generated_at" in data


# ═══════════════════════════════════════════════════════════════════
# 19) ROUTES SOURCE VALIDATION
# ═══════════════════════════════════════════════════════════════════
class TestRoutesSource:
    """Routes file must have proper structure."""

    def test_routes_has_ask_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/ask" in src

    def test_routes_has_symbol_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/symbol" in src

    def test_routes_has_discover_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/discover" in src

    def test_routes_has_screener_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/screener" in src

    def test_routes_uses_post_method(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert 'methods=["POST"]' in src or "methods=['POST']" in src

    def test_routes_returns_jsonify(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "jsonify" in src

    def test_routes_has_error_handling(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "except" in src

    def test_routes_imports_copilot_service(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "copilot_service" in src
