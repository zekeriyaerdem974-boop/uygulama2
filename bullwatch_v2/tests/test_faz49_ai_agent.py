# -*- coding: utf-8 -*-
"""FAZ 49 — AI Personal Market Agent + AI-Driven Discover Tests.

Covers:
  1. ai_market_agent.py — engine functions (generate_brief, analyze_portfolio, etc.)
  2. ai_agent blueprint — API routes, auth, edge cases
  3. ai_agent.html — template structure
  4. discover.html — AI hero section
  5. Copilot integration endpoint
  6. LEGAL_SAFE_MODE compliance
  7. Caching behaviour
  8. Performance constraints

70+ tests organized into 10 test classes.
"""
from __future__ import annotations

import json
import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock

import pytest

# ── Paths ─────────────────────────────────────────────────────────
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

# ── Helpers ───────────────────────────────────────────────────────
def _read(rel_path: str) -> str:
    with open(os.path.join(BASE, rel_path), encoding="utf-8") as f:
        return f.read()


def _get_app():
    """Import and return the Flask app for testing."""
    from legacy_monolith import app
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-faz49"
    return app


def _client():
    return _get_app().test_client()


def _auth_client():
    """Client with fake auth session — patches get_current_user."""
    app = _get_app()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["user_id"] = "test_user_faz49"
        sess["username"] = "testuser49"
    return client


_FAKE_USER = {"id": "test_user_faz49", "username": "testuser49", "email": "t@t.com"}


def _patch_auth():
    """Patch get_current_user to return fake user."""
    return patch("app.blueprints.auth.routes.get_current_user",
                 return_value=_FAKE_USER)


# ══════════════════════════════════════════════════════════════════
# CLASS 1: File Existence & Structure
# ══════════════════════════════════════════════════════════════════

class TestFaz49FileStructure(unittest.TestCase):
    """Verify all FAZ 49 files exist and have correct structure."""

    def test_engine_file_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/ai_market_agent.py"))

    def test_blueprint_init_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/ai_agent/__init__.py"))

    def test_blueprint_routes_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/ai_agent/routes.py"))

    def test_template_ai_agent_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/ai_agent.html"))

    def test_template_discover_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/discover.html"))

    def test_engine_has_public_api(self):
        src = _read("app/core/ai_market_agent.py")
        for fn in ["generate_brief", "analyze_portfolio", "analyze_watchlist",
                    "explain_opportunity", "get_market_summary",
                    "get_top_opportunities", "ask_agent"]:
            assert f"def {fn}" in src, f"Missing public function: {fn}"

    def test_routes_has_all_endpoints(self):
        src = _read("app/blueprints/ai_agent/routes.py")
        for route in ["/ai-agent", "/api/ai/brief", "/api/ai/market-summary",
                      "/api/ai/portfolio", "/api/ai/watchlist",
                      "/api/ai/opportunities", "/api/ai/ask",
                      "/api/copilot/agent"]:
            assert route in src, f"Missing route: {route}"

    def test_blueprint_registered_in_monolith(self):
        src = _read("legacy_monolith.py")
        assert "ai_agent_bp" in src
        assert "app.register_blueprint(ai_agent_bp)" in src


# ══════════════════════════════════════════════════════════════════
# CLASS 2: Engine — LEGAL_SAFE_MODE Compliance
# ══════════════════════════════════════════════════════════════════

class TestFaz49LegalSafeMode(unittest.TestCase):
    """Ensure LEGAL_SAFE_MODE compliance."""

    def test_banned_words_defined(self):
        from app.core.ai_market_agent import BANNED_WORDS
        assert "BUY" in BANNED_WORDS
        assert "SELL" in BANNED_WORDS
        assert "ENTRY" in BANNED_WORDS
        assert "EXIT" in BANNED_WORDS
        assert "TAKE PROFIT" in BANNED_WORDS
        assert "STOP LOSS" in BANNED_WORDS

    def test_safe_labels_defined(self):
        from app.core.ai_market_agent import SAFE_LABELS
        assert "bullish" in SAFE_LABELS
        assert "bearish" in SAFE_LABELS
        assert "momentum_up" in SAFE_LABELS
        assert "volatility_spike" in SAFE_LABELS

    def test_sanitize_removes_banned_words(self):
        from app.core.ai_market_agent import _sanitize
        assert "BUY" not in _sanitize("You should BUY now")
        assert "SELL" not in _sanitize("Time to SELL everything")
        assert "TAKE PROFIT" not in _sanitize("Take Profit at 50k")
        assert "STOP LOSS" not in _sanitize("Set Stop Loss at 40k")
        assert "***" in _sanitize("BUY now")

    def test_sanitize_case_insensitive(self):
        from app.core.ai_market_agent import _sanitize
        assert "buy" not in _sanitize("you should buy now").lower().replace("***", "")
        assert "sell" not in _sanitize("Time to sell").lower().replace("***", "")

    def test_sanitize_preserves_safe_text(self):
        from app.core.ai_market_agent import _sanitize
        safe = "Momentum artıyor, volatilite dikkat çekiyor"
        assert _sanitize(safe) == safe

    def test_engine_source_no_banned_output(self):
        """Engine source code should not produce banned words in output."""
        src = _read("app/core/ai_market_agent.py")
        # Check string literals don't contain banned advice words in Turkish
        for word in ["hemen al", "hemen sat", "giriş yap", "çıkış yap"]:
            assert word.lower() not in src.lower(), f"Found banned term in source: {word}"


# ══════════════════════════════════════════════════════════════════
# CLASS 3: Engine — Data Collectors (unit tests with mocks)
# ══════════════════════════════════════════════════════════════════

class TestFaz49DataCollectors(unittest.TestCase):
    """Test internal data collection functions."""

    @patch("app.core.ai_market_agent.cache_get")
    @patch("app.cache.cache_get")
    def test_collect_market_data_with_tickers(self, mock_cg_cache, mock_cg_agent):
        def side_effect(key, **kw):
            store = {
                "tickers": {
                    "BTCUSDT": {"price": 65000, "change_pct": 2.5},
                    "ETHUSDT": {"price": 3500, "change_pct": -1.2},
                    "SOLUSDT": {"price": 140, "change_pct": 5.0},
                },
                "fng_latest": {"value": 72, "classification": "Greed"},
            }
            return store.get(key)
        mock_cg_cache.side_effect = side_effect
        mock_cg_agent.side_effect = side_effect

        from app.core.ai_market_agent import _collect_market_data
        data = _collect_market_data()
        assert data["btc_price"] == 65000
        assert data["btc_change"] == 2.5
        assert data["eth_price"] == 3500
        assert data["fng_value"] == 72

    @patch("app.core.ai_market_agent.cache_get")
    def test_collect_market_data_no_cache(self, mock_cg):
        mock_cg.return_value = None
        from app.core.ai_market_agent import _collect_market_data
        data = _collect_market_data()
        assert data["btc_price"] is None

    def test_collect_opportunities_handles_error(self):
        with patch("app.core.ai_market_agent.cache_get", return_value=None):
            from app.core.ai_market_agent import _collect_opportunities
            # Should not raise
            result = _collect_opportunities()
            assert isinstance(result, list)

    def test_collect_news_handles_error(self):
        from app.core.ai_market_agent import _collect_news_impacts
        # Engine may fail but should return empty list
        result = _collect_news_impacts()
        assert isinstance(result, list)

    def test_collect_watchlist_handles_error(self):
        from app.core.ai_market_agent import _collect_watchlist
        result = _collect_watchlist("nonexistent_user")
        assert isinstance(result, list)

    def test_collect_trending_handles_error(self):
        from app.core.ai_market_agent import _collect_trending_symbols
        result = _collect_trending_symbols()
        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════════════
# CLASS 4: Engine — Intelligence Generators
# ══════════════════════════════════════════════════════════════════

class TestFaz49IntelligenceGenerators(unittest.TestCase):
    """Test AI intelligence generation functions."""

    def test_determine_sentiment_neutral(self):
        from app.core.ai_market_agent import _determine_market_sentiment
        s = _determine_market_sentiment({}, [])
        assert s["key"] in ("neutral", "bullish", "bearish", "very_bullish", "very_bearish")
        assert 0 <= s["score"] <= 100
        assert "label" in s
        assert "icon" in s
        assert "color" in s

    def test_determine_sentiment_bullish(self):
        from app.core.ai_market_agent import _determine_market_sentiment
        market = {"btc_change": 8, "fng_value": 80}
        opps = [{"event_type": "momentum_shift"}, {"event_type": "breakout"}]
        s = _determine_market_sentiment(market, opps)
        assert s["score"] > 50

    def test_determine_sentiment_bearish(self):
        from app.core.ai_market_agent import _determine_market_sentiment
        market = {"btc_change": -8, "fng_value": 15}
        opps = [{"event_type": "rsi_extreme"}, {"event_type": "volatility_spike"}]
        s = _determine_market_sentiment(market, opps)
        assert s["score"] < 50

    def test_build_highlights_with_data(self):
        from app.core.ai_market_agent import _build_market_highlights
        market = {
            "btc_price": 65000, "btc_change": 2.5,
            "eth_price": 3500, "eth_change": -1,
            "fng_value": 72, "fng_label": "Greed",
        }
        opps = [{"event_type": "volume_spike"}, {"event_type": "volume_spike"}]
        news = [{"confidence_score": 80}]
        trending = [{"symbol": "BTC"}, {"symbol": "ETH"}]

        highlights = _build_market_highlights(market, opps, news, trending)
        assert isinstance(highlights, list)
        assert len(highlights) >= 3
        assert any("BTC" in h for h in highlights)

    def test_build_highlights_empty(self):
        from app.core.ai_market_agent import _build_market_highlights
        highlights = _build_market_highlights({}, [], [], [])
        assert isinstance(highlights, list)

    def test_build_portfolio_insights_no_data(self):
        from app.core.ai_market_agent import _build_portfolio_insights
        insights = _build_portfolio_insights({"has_portfolio": False})
        assert insights == []

    def test_build_portfolio_insights_with_data(self):
        from app.core.ai_market_agent import _build_portfolio_insights
        portfolio = {
            "has_portfolio": True,
            "summary": {"total_value": 10000, "total_pnl": 500,
                         "total_pnl_pct": 5.0, "total_current_value": 10000},
            "risk": {"risk_score": 45, "risk_label_tr": "Orta",
                     "concentration_risk": 30},
            "assets": [
                {"symbol": "BTC", "current_price": 65000, "entry_price": 60000},
                {"symbol": "ETH", "current_price": 3500, "entry_price": 4000},
            ],
        }
        insights = _build_portfolio_insights(portfolio)
        assert len(insights) >= 2
        assert all("type" in i for i in insights)
        assert all("title" in i for i in insights)

    def test_build_watchlist_insights_empty(self):
        from app.core.ai_market_agent import _build_watchlist_insights
        insights = _build_watchlist_insights([], {}, [])
        assert insights == []

    def test_build_watchlist_insights_quiet(self):
        from app.core.ai_market_agent import _build_watchlist_insights
        with patch("app.core.ai_market_agent.cache_get", return_value=None):
            insights = _build_watchlist_insights(
                [{"symbol": "BTCUSDT"}], {}, []
            )
            assert len(insights) >= 1
            assert any(i.get("type") == "watchlist_quiet" for i in insights)

    @patch("app.core.ai_market_agent.cache_get")
    def test_build_watchlist_insights_with_opps(self, mock_cg):
        mock_cg.return_value = None  # no tickers cache
        from app.core.ai_market_agent import _build_watchlist_insights
        watchlist = [{"symbol": "BTCUSDT"}]
        opps = [{"symbol": "BTCUSDT", "event_type": "volume_spike",
                 "description": "High volume", "confidence": 80}]
        insights = _build_watchlist_insights(watchlist, {}, opps)
        assert any(i.get("type") == "watchlist_opportunity" for i in insights)


# ══════════════════════════════════════════════════════════════════
# CLASS 5: Engine — Opportunity Explanation
# ══════════════════════════════════════════════════════════════════

class TestFaz49OpportunityExplanation(unittest.TestCase):
    """Test opportunity explanation generation."""

    def test_explain_single_opportunity(self):
        from app.core.ai_market_agent import _explain_single_opportunity
        opp = {
            "symbol": "BTCUSDT",
            "event_type": "momentum_shift",
            "confidence": 85,
            "description": "Strong upward momentum detected",
            "details": "EMA crossover on 4H chart",
            "price": 65000,
            "change_pct": 3.5,
        }
        result = _explain_single_opportunity(opp)
        assert result["symbol"] == "BTCUSDT"
        assert result["event_type"] == "momentum_shift"
        assert result["confidence"] == 85
        assert "explanation" in result
        assert result["risk_level"] == "low"  # high confidence = low risk
        assert "generated_at" in result

    def test_explain_low_confidence(self):
        from app.core.ai_market_agent import _explain_single_opportunity
        opp = {"symbol": "XYZ", "event_type": "rsi_extreme",
               "confidence": 30, "description": "", "price": 100}
        result = _explain_single_opportunity(opp)
        assert result["risk_level"] == "high"

    def test_explain_medium_confidence(self):
        from app.core.ai_market_agent import _explain_single_opportunity
        opp = {"symbol": "XYZ", "event_type": "breakout",
               "confidence": 65, "description": ""}
        result = _explain_single_opportunity(opp)
        assert result["risk_level"] == "medium"

    def test_explain_all_event_types(self):
        from app.core.ai_market_agent import _explain_single_opportunity
        types = ["volume_spike", "momentum_shift", "volatility_spike",
                 "rsi_extreme", "ema_cross", "breakout", "sector_rotation",
                 "whale_activity", "fng_extreme", "price_anomaly", "unknown_type"]
        for et in types:
            result = _explain_single_opportunity({
                "symbol": "TEST", "event_type": et, "confidence": 50
            })
            assert result["explanation"], f"Empty explanation for {et}"
            # Verify no banned words
            for banned in ["BUY", "SELL", "ENTRY", "EXIT"]:
                assert banned not in result["explanation"]

    def test_explain_sanitizes_details(self):
        from app.core.ai_market_agent import _explain_single_opportunity
        opp = {"symbol": "X", "event_type": "test", "confidence": 50,
               "details": "You should BUY now and SELL later"}
        result = _explain_single_opportunity(opp)
        assert "BUY" not in result["explanation"]
        assert "SELL" not in result["explanation"]


# ══════════════════════════════════════════════════════════════════
# CLASS 6: Engine — Public API Functions
# ══════════════════════════════════════════════════════════════════

class TestFaz49PublicAPI(unittest.TestCase):
    """Test public API functions of ai_market_agent."""

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_market_data")
    @patch("app.core.ai_market_agent._collect_opportunities")
    @patch("app.core.ai_market_agent._collect_news_impacts")
    @patch("app.core.ai_market_agent._collect_activity")
    @patch("app.core.ai_market_agent._collect_trending_symbols")
    @patch("app.core.ai_market_agent._collect_portfolio")
    @patch("app.core.ai_market_agent._collect_watchlist")
    def test_generate_brief_structure(self, mock_wl, mock_pf, mock_ts,
                                       mock_act, mock_news, mock_opps,
                                       mock_md, mock_cs, mock_cg):
        mock_md.return_value = {"btc_price": 65000, "btc_change": 2}
        mock_opps.return_value = []
        mock_news.return_value = []
        mock_act.return_value = []
        mock_ts.return_value = []
        mock_pf.return_value = {"has_portfolio": False}
        mock_wl.return_value = []

        from app.core.ai_market_agent import generate_brief
        brief = generate_brief("user1")

        assert "user_id" in brief
        assert "generated_at" in brief
        assert "sentiment" in brief
        assert "highlights" in brief
        assert "portfolio" in brief
        assert "watchlist" in brief
        assert "opportunities" in brief
        assert "generation_time_ms" in brief
        assert brief["user_id"] == "user1"

    @patch("app.core.ai_market_agent.cache_get")
    def test_generate_brief_uses_cache(self, mock_cg):
        cached = {"user_id": "u1", "cached": True}
        mock_cg.return_value = cached

        from app.core.ai_market_agent import generate_brief
        result = generate_brief("u1")
        assert result["cached"] is True

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_market_data")
    @patch("app.core.ai_market_agent._collect_opportunities")
    @patch("app.core.ai_market_agent._collect_news_impacts")
    @patch("app.core.ai_market_agent._collect_trending_symbols")
    def test_get_market_summary_structure(self, mock_ts, mock_news,
                                          mock_opps, mock_md, mock_cs, mock_cg):
        mock_md.return_value = {"btc_price": 60000, "btc_change": -1}
        mock_opps.return_value = []
        mock_news.return_value = []
        mock_ts.return_value = []

        from app.core.ai_market_agent import get_market_summary
        result = get_market_summary()

        assert "sentiment" in result
        assert "highlights" in result
        assert "market_data" in result
        assert "generated_at" in result

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_portfolio")
    @patch("app.core.ai_market_agent._collect_opportunities")
    @patch("app.core.ai_market_agent._collect_market_data")
    def test_analyze_portfolio_empty(self, mock_md, mock_opps, mock_pf,
                                      mock_cs, mock_cg):
        mock_pf.return_value = {"has_portfolio": False}
        mock_opps.return_value = []
        mock_md.return_value = {}

        from app.core.ai_market_agent import analyze_portfolio
        result = analyze_portfolio("user1")
        assert result["has_data"] is False
        assert "message" in result

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_watchlist")
    @patch("app.core.ai_market_agent._collect_opportunities")
    @patch("app.core.ai_market_agent._collect_market_data")
    def test_analyze_watchlist_empty(self, mock_md, mock_opps, mock_wl,
                                      mock_cs, mock_cg):
        mock_wl.return_value = []
        mock_opps.return_value = []
        mock_md.return_value = {}

        from app.core.ai_market_agent import analyze_watchlist
        result = analyze_watchlist("user1")
        assert result["has_data"] is False
        assert "message" in result

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_opportunities")
    def test_get_top_opportunities(self, mock_opps, mock_cs, mock_cg):
        mock_opps.return_value = [
            {"symbol": "BTC", "event_type": "breakout", "confidence": 90},
            {"symbol": "ETH", "event_type": "volume_spike", "confidence": 70},
        ]
        from app.core.ai_market_agent import get_top_opportunities
        result = get_top_opportunities(limit=5)
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["confidence"] >= result[1]["confidence"]

    def test_ask_agent_empty_question(self):
        from app.core.ai_market_agent import ask_agent
        result = ask_agent("user1", "")
        assert result["ok"] is False
        assert "error" in result

    def test_ask_agent_whitespace_question(self):
        from app.core.ai_market_agent import ask_agent
        result = ask_agent("user1", "   ")
        assert result["ok"] is False

    @patch("app.core.ai_market_agent._collect_market_data")
    @patch("app.core.ai_market_agent._collect_opportunities")
    @patch("app.core.ai_market_agent._collect_news_impacts")
    @patch("app.core.ai_market_agent._collect_trending_symbols")
    @patch("app.core.ai_market_agent._collect_portfolio")
    @patch("app.core.ai_market_agent._collect_watchlist")
    def test_ask_agent_valid_question(self, mock_wl, mock_pf, mock_ts,
                                       mock_news, mock_opps, mock_md):
        mock_md.return_value = {"btc_price": 65000, "btc_change": 2, "fng_value": 60}
        mock_opps.return_value = []
        mock_news.return_value = []
        mock_ts.return_value = []
        mock_pf.return_value = {"has_portfolio": False}
        mock_wl.return_value = []

        # Prevent copilot_service import from triggering network calls
        import sys
        fake_mod = type(sys)("fake_copilot")
        fake_mod.ask_market = lambda *a, **kw: (_ for _ in ()).throw(ImportError("mocked"))
        with patch.dict(sys.modules, {"app.core.copilot_service": fake_mod}):
            from app.core.ai_market_agent import ask_agent
            result = ask_agent("user1", "Piyasa durumu nedir?")
        assert result["ok"] is True
        assert "data" in result

    def test_explain_opportunity_not_found(self):
        from app.core.ai_market_agent import explain_opportunity
        with patch("app.core.ai_market_agent.cache_get", return_value=None):
            result = explain_opportunity("nonexistent_id_xyz")
            assert result.get("found") is False


# ══════════════════════════════════════════════════════════════════
# CLASS 7: API Routes — Auth & Response
# ══════════════════════════════════════════════════════════════════

@pytest.fixture
def db_patch():
    """Patch DB paths for test isolation."""
    import tempfile
    tmp = tempfile.mkdtemp()
    patches = []
    try:
        from app.core import db_manager
        p = patch.object(db_manager, "_DB_DIR", tmp)
        p.start()
        patches.append(p)
    except Exception:
        pass
    yield tmp
    for p in patches:
        p.stop()


class TestFaz49APIRoutes(unittest.TestCase):
    """Test API route responses."""

    def test_ai_agent_page_returns_html(self):
        client = _client()
        r = client.get("/ai-agent")
        assert r.status_code == 200
        assert b"AI Market Agent" in r.data

    def test_api_brief_requires_auth(self):
        client = _client()
        r = client.get("/api/ai/brief")
        assert r.status_code == 401

    def test_api_portfolio_requires_auth(self):
        client = _client()
        r = client.get("/api/ai/portfolio")
        assert r.status_code == 401

    def test_api_watchlist_requires_auth(self):
        client = _client()
        r = client.get("/api/ai/watchlist")
        assert r.status_code == 401

    def test_api_ask_requires_auth(self):
        client = _client()
        r = client.post("/api/ai/ask",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json")
        assert r.status_code == 401

    def test_api_copilot_agent_requires_auth(self):
        client = _client()
        r = client.post("/api/copilot/agent",
                        data=json.dumps({"question": "test"}),
                        content_type="application/json")
        assert r.status_code == 401

    def test_api_market_summary_no_auth(self):
        """Market summary should be accessible without auth."""
        client = _client()
        r = client.get("/api/ai/market-summary")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True

    def test_api_opportunities_no_auth(self):
        """Opportunities list should be accessible without auth."""
        client = _client()
        r = client.get("/api/ai/opportunities")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True

    def test_api_opportunities_limit_param(self):
        client = _client()
        r = client.get("/api/ai/opportunities?limit=5")
        assert r.status_code == 200

    def test_api_opportunity_explain_not_found(self):
        client = _client()
        r = client.get("/api/ai/opportunity/nonexistent_xyz")
        assert r.status_code == 404

    @patch("app.core.ai_market_agent.generate_brief")
    def test_api_brief_authenticated(self, mock_brief):
        mock_brief.return_value = {"user_id": "test", "sentiment": {}}
        with _patch_auth():
            client = _auth_client()
            r = client.get("/api/ai/brief")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True

    @patch("app.core.ai_market_agent.analyze_portfolio")
    def test_api_portfolio_authenticated(self, mock_pf):
        mock_pf.return_value = {"has_data": False, "message": "Empty"}
        with _patch_auth():
            client = _auth_client()
            r = client.get("/api/ai/portfolio")
        assert r.status_code == 200
        data = r.get_json()
        assert data["ok"] is True

    @patch("app.core.ai_market_agent.analyze_watchlist")
    def test_api_watchlist_authenticated(self, mock_wl):
        mock_wl.return_value = {"has_data": False}
        with _patch_auth():
            client = _auth_client()
            r = client.get("/api/ai/watchlist")
        assert r.status_code == 200

    def test_api_ask_empty_question(self):
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/ai/ask",
                            data=json.dumps({"question": ""}),
                            content_type="application/json")
        assert r.status_code == 400

    def test_api_ask_too_long_question(self):
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/ai/ask",
                            data=json.dumps({"question": "x" * 501}),
                            content_type="application/json")
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════
# CLASS 8: Copilot Integration
# ══════════════════════════════════════════════════════════════════

class TestFaz49CopilotIntegration(unittest.TestCase):
    """Test copilot agent integration endpoint."""

    def test_copilot_agent_empty_question(self):
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": ""}),
                            content_type="application/json")
        assert r.status_code == 400

    @patch("app.core.ai_market_agent.generate_brief")
    def test_copilot_agent_brief_context(self, mock_brief):
        mock_brief.return_value = {"test": True}
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "test", "context": "brief"}),
                            content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("source") == "ai_agent_brief"

    @patch("app.core.ai_market_agent.analyze_portfolio")
    def test_copilot_agent_portfolio_context(self, mock_pf):
        mock_pf.return_value = {"test": True}
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "test", "context": "portfolio"}),
                            content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("source") == "ai_agent_portfolio"

    @patch("app.core.ai_market_agent.analyze_watchlist")
    def test_copilot_agent_watchlist_context(self, mock_wl):
        mock_wl.return_value = {"test": True}
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "test", "context": "watchlist"}),
                            content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("source") == "ai_agent_watchlist"

    @patch("app.core.ai_market_agent.get_market_summary")
    def test_copilot_agent_market_context(self, mock_ms):
        mock_ms.return_value = {"test": True}
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "test", "context": "market"}),
                            content_type="application/json")
        assert r.status_code == 200
        data = r.get_json()
        assert data.get("source") == "ai_agent_market"

    @patch("app.core.ai_market_agent.ask_agent")
    def test_copilot_agent_freeform(self, mock_ask):
        mock_ask.return_value = {"ok": True, "data": {"answer": "test"}}
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "What is happening?"}),
                            content_type="application/json")
        assert r.status_code == 200

    def test_copilot_agent_too_long(self):
        with _patch_auth():
            client = _auth_client()
            r = client.post("/api/copilot/agent",
                            data=json.dumps({"question": "x" * 501}),
                            content_type="application/json")
        assert r.status_code == 400


# ══════════════════════════════════════════════════════════════════
# CLASS 9: Template Structure
# ══════════════════════════════════════════════════════════════════

class TestFaz49Templates(unittest.TestCase):
    """Test template HTML structure."""

    def test_ai_agent_template_tabs(self):
        html = _read("templates/ai_agent.html")
        assert 'data-tab="brief"' in html
        assert 'data-tab="portfolio"' in html
        assert 'data-tab="watchlist"' in html
        assert 'data-tab="opportunities"' in html
        assert 'data-tab="ask"' in html

    def test_ai_agent_template_sections(self):
        html = _read("templates/ai_agent.html")
        assert 'id="section-brief"' in html
        assert 'id="section-portfolio"' in html
        assert 'id="section-watchlist"' in html
        assert 'id="section-opportunities"' in html
        assert 'id="section-ask"' in html

    def test_ai_agent_template_ask_form(self):
        html = _read("templates/ai_agent.html")
        assert 'id="ai-ask-input"' in html
        assert 'id="ai-ask-btn"' in html
        assert 'id="ai-ask-output"' in html

    def test_ai_agent_template_legal(self):
        html = _read("templates/ai_agent.html")
        assert "legal_disclaimer" in html

    def test_ai_agent_template_extends_layout(self):
        html = _read("templates/ai_agent.html")
        assert 'extends "layout_terminal.html"' in html

    def test_ai_agent_fetch_endpoints(self):
        html = _read("templates/ai_agent.html")
        assert "/api/ai/brief" in html
        assert "/api/ai/portfolio" in html
        assert "/api/ai/watchlist" in html
        assert "/api/ai/opportunities" in html
        assert "/api/ai/ask" in html

    def test_discover_has_ai_hero(self):
        html = _read("templates/discover.html")
        assert "AI Market Brief" in html or "AI Personal Brief" in html
        assert "ai-hero" in html
        assert "/ai-agent" in html

    def test_discover_has_ai_sentiment(self):
        html = _read("templates/discover.html")
        assert "disc-ai-sentiment" in html
        assert "disc-ai-highlights" in html

    def test_discover_loads_market_summary(self):
        html = _read("templates/discover.html")
        assert "/api/ai/market-summary" in html

    def test_discover_still_has_market_snapshot(self):
        html = _read("templates/discover.html")
        assert "Market Snapshot" in html

    def test_discover_still_has_opportunities(self):
        html = _read("templates/discover.html")
        assert "AI Market Opportunities" in html

    def test_discover_still_has_activity(self):
        html = _read("templates/discover.html")
        assert "Live Market Activity" in html


# ══════════════════════════════════════════════════════════════════
# CLASS 10: Caching Behaviour
# ══════════════════════════════════════════════════════════════════

class TestFaz49Caching(unittest.TestCase):
    """Test caching TTLs and behaviour."""

    def test_cache_ttls_are_15_minutes(self):
        from app.core.ai_market_agent import (
            BRIEF_CACHE_TTL, MARKET_CACHE_TTL,
            PORTFOLIO_CACHE_TTL, WATCHLIST_CACHE_TTL,
            OPP_EXPLAIN_CACHE_TTL,
        )
        assert BRIEF_CACHE_TTL == 900
        assert MARKET_CACHE_TTL == 900
        assert PORTFOLIO_CACHE_TTL == 900
        assert WATCHLIST_CACHE_TTL == 900
        assert OPP_EXPLAIN_CACHE_TTL == 900

    @patch("app.core.ai_market_agent.cache_get")
    def test_generate_brief_returns_cached(self, mock_cg):
        mock_cg.return_value = {"cached": True}
        from app.core.ai_market_agent import generate_brief
        result = generate_brief("user1")
        assert result == {"cached": True}
        mock_cg.assert_called_once()

    @patch("app.core.ai_market_agent.cache_get")
    def test_market_summary_returns_cached(self, mock_cg):
        mock_cg.return_value = {"cached": True}
        from app.core.ai_market_agent import get_market_summary
        result = get_market_summary()
        assert result == {"cached": True}

    @patch("app.core.ai_market_agent.cache_get")
    def test_analyze_portfolio_returns_cached(self, mock_cg):
        mock_cg.return_value = {"cached": True}
        from app.core.ai_market_agent import analyze_portfolio
        result = analyze_portfolio("user1")
        assert result == {"cached": True}

    @patch("app.core.ai_market_agent.cache_get")
    def test_analyze_watchlist_returns_cached(self, mock_cg):
        mock_cg.return_value = {"cached": True}
        from app.core.ai_market_agent import analyze_watchlist
        result = analyze_watchlist("user1")
        assert result == {"cached": True}

    @patch("app.core.ai_market_agent.cache_get", return_value=None)
    @patch("app.core.ai_market_agent.cache_set")
    @patch("app.core.ai_market_agent._collect_market_data", return_value={})
    @patch("app.core.ai_market_agent._collect_opportunities", return_value=[])
    @patch("app.core.ai_market_agent._collect_news_impacts", return_value=[])
    @patch("app.core.ai_market_agent._collect_trending_symbols", return_value=[])
    def test_market_summary_sets_cache(self, *mocks):
        from app.core.ai_market_agent import get_market_summary, cache_set
        result = get_market_summary()
        cache_set.assert_called_once()


# ══════════════════════════════════════════════════════════════════
# CLASS 11: Sentiment Map Completeness
# ══════════════════════════════════════════════════════════════════

class TestFaz49SentimentMap(unittest.TestCase):
    """Test sentiment mapping completeness."""

    def test_sentiment_map_has_all_keys(self):
        from app.core.ai_market_agent import _SENTIMENT_MAP
        for key in ["very_bullish", "bullish", "neutral", "bearish", "very_bearish"]:
            assert key in _SENTIMENT_MAP
            s = _SENTIMENT_MAP[key]
            assert "label" in s
            assert "icon" in s
            assert "color" in s

    def test_sentiment_score_boundaries(self):
        from app.core.ai_market_agent import _determine_market_sentiment
        # Extreme bullish input
        s = _determine_market_sentiment({"btc_change": 100, "fng_value": 100}, [])
        assert s["score"] <= 100
        # Extreme bearish input
        s = _determine_market_sentiment({"btc_change": -100, "fng_value": 0}, [])
        assert s["score"] >= 0


if __name__ == "__main__":
    unittest.main()
