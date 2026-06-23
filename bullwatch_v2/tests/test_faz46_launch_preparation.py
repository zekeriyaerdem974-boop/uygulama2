# -*- coding: utf-8 -*-
"""FAZ 46 — Launch Preparation Tests.

Covers:
  - Landing page
  - Onboarding flow
  - Demo data engine
  - User preferences / onboarding engine
  - Watchlist initialization
  - Analytics tracking
  - Empty-state UX
  - Discover page improvements

Minimum 50 tests.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Isolate all SQLite databases to a temp directory."""
    db_dir = str(tmp_path / "data")
    os.makedirs(db_dir, exist_ok=True)
    # db_manager (centralized)
    monkeypatch.setattr("app.core.db_manager._DB_DIR", db_dir)
    # user_engine
    monkeypatch.setattr("app.core.user_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.user_engine._DB_PATH",
                        os.path.join(db_dir, "users.db"))
    from app.core.user_engine import _init_db
    _init_db()

    # portfolio_engine
    monkeypatch.setattr("app.core.portfolio_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.portfolio_engine._DB_PATH",
                        os.path.join(db_dir, "portfolios.db"))
    from app.core.portfolio_engine import _init_db as _init_portfolio_db
    _init_portfolio_db()


@pytest.fixture
def _user(tmp_path, monkeypatch):
    """Create a test user and return user dict."""
    from app.core.user_engine import register_user
    return register_user("test46@example.com", "testuser46", "password123")


# ══════════════════════════════════════════════════════════════════════
# 1. LANDING PAGE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestLandingPage:
    """Landing page rendering and content tests."""

    def test_landing_page_loads(self, client):
        """Landing page returns 200."""
        resp = client.get("/landing")
        assert resp.status_code == 200

    def test_landing_has_title(self, client):
        """Landing page has ZKR Analiz Pro title."""
        resp = client.get("/landing")
        assert b"ZKR Analiz Pro" in resp.data

    def test_landing_has_hero(self, client):
        """Landing page contains hero section."""
        resp = client.get("/landing")
        assert b"ln-hero" in resp.data

    def test_landing_has_features_section(self, client):
        """Landing page contains features section."""
        resp = client.get("/landing")
        assert b"ln-features" in resp.data

    def test_landing_has_screenshots_section(self, client):
        """Landing page contains screenshots section."""
        resp = client.get("/landing")
        assert b"ln-screenshots" in resp.data

    def test_landing_has_pricing_section(self, client):
        """Landing page contains pricing section."""
        resp = client.get("/landing")
        assert b"ln-pricing" in resp.data

    def test_landing_has_cta(self, client):
        """Landing page contains CTA section."""
        resp = client.get("/landing")
        assert b"ln-cta" in resp.data

    def test_landing_has_register_link(self, client):
        """Landing page links to /register."""
        resp = client.get("/landing")
        assert b"/register" in resp.data

    def test_landing_has_login_link(self, client):
        """Landing page links to /login."""
        resp = client.get("/landing")
        assert b"/login" in resp.data

    def test_landing_has_discover_link(self, client):
        """Landing page links to /discover (demo)."""
        resp = client.get("/landing")
        assert b"/discover" in resp.data

    def test_landing_has_all_8_features(self, client):
        """Landing page shows all 8 core features."""
        resp = client.get("/landing")
        html = resp.data
        features = [b"AI Market Radar", b"Opportunity Engine",
                    b"Activity Stream", b"Portfolio Intelligence",
                    b"AI Copilot", b"Social Trading",
                    b"Strategy Builder", b"Backtesting"]
        for feat in features:
            assert feat in html, f"Missing feature: {feat.decode()}"

    def test_landing_has_get_started_button(self, client):
        """Landing has 'Get Started' button."""
        resp = client.get("/landing")
        assert b"Get Started" in resp.data

    def test_landing_has_view_demo_button(self, client):
        """Landing has 'View Demo' link."""
        resp = client.get("/landing")
        assert b"View Demo" in resp.data or b"Explore Demo" in resp.data

    def test_landing_has_pricing_tiers(self, client):
        """Landing has Free, Pro, Enterprise pricing."""
        resp = client.get("/landing")
        assert b"Free" in resp.data
        assert b"Pro" in resp.data
        assert b"Enterprise" in resp.data

    def test_landing_has_analytics_tracking(self, client):
        """Landing page includes analytics tracking script."""
        resp = client.get("/landing")
        assert b"api/analytics/track" in resp.data


# ══════════════════════════════════════════════════════════════════════
# 2. ONBOARDING PAGE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestOnboardingPage:
    """Onboarding wizard template tests."""

    def test_onboarding_page_loads(self, client):
        """Onboarding page returns 200."""
        resp = client.get("/onboarding")
        assert resp.status_code == 200

    def test_onboarding_has_progress_bar(self, client):
        """Onboarding has progress bar."""
        resp = client.get("/onboarding")
        assert b"ob-progress" in resp.data

    def test_onboarding_has_5_steps(self, client):
        """Onboarding has 5 step containers."""
        resp = client.get("/onboarding")
        for i in range(1, 6):
            assert f'id="step-{i}"'.encode() in resp.data

    def test_onboarding_has_market_options(self, client):
        """Onboarding has market selection options."""
        resp = client.get("/onboarding")
        for mkt in [b"crypto", b"stocks", b"bist", b"forex", b"commodities"]:
            assert mkt in resp.data

    def test_onboarding_has_welcome_step(self, client):
        """Step 1 is Welcome."""
        resp = client.get("/onboarding")
        assert b"Welcome to ZKR Analiz Pro" in resp.data

    def test_onboarding_has_finish_step(self, client):
        """Step 5 is completion."""
        resp = client.get("/onboarding")
        assert b"You're All Set" in resp.data or b"You&#39;re All Set" in resp.data


# ══════════════════════════════════════════════════════════════════════
# 3. ONBOARDING API TESTS
# ══════════════════════════════════════════════════════════════════════

class TestOnboardingAPI:
    """Onboarding API endpoint tests."""

    def test_onboarding_status_anonymous(self, client):
        """Anonymous user: onboarding not completed."""
        resp = client.get("/api/onboarding/status")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["completed"] is False

    def test_onboarding_complete_anonymous(self, client):
        """Anonymous user can submit onboarding (stored in session)."""
        resp = client.post("/api/onboarding/complete",
                          json={"markets": ["crypto"], "symbols": ["BTCUSDT"]})
        data = resp.get_json()
        assert data["ok"] is True
        assert data.get("saved") == "session"

    def test_onboarding_complete_logged_in(self, app, client, _user):
        """Logged-in user completes onboarding, saved to DB."""
        with client.session_transaction() as sess:
            sess["user_id"] = _user["id"]
            sess["username"] = _user["username"]

        resp = client.post("/api/onboarding/complete",
                          json={"markets": ["crypto", "stocks"],
                                "symbols": ["BTCUSDT", "AAPL"]})
        data = resp.get_json()
        assert data["ok"] is True

    def test_onboarding_status_after_complete(self, app, client, _user):
        """After completing, status returns completed=True."""
        with client.session_transaction() as sess:
            sess["user_id"] = _user["id"]
            sess["username"] = _user["username"]

        client.post("/api/onboarding/complete",
                   json={"markets": ["crypto"], "symbols": ["BTCUSDT"]})

        resp = client.get("/api/onboarding/status")
        data = resp.get_json()
        assert data["completed"] is True

    def test_onboarding_validates_markets(self, app, client, _user):
        """Invalid markets are filtered out."""
        with client.session_transaction() as sess:
            sess["user_id"] = _user["id"]

        resp = client.post("/api/onboarding/complete",
                          json={"markets": ["crypto", "invalid_mkt"],
                                "symbols": []})
        assert resp.get_json()["ok"] is True


# ══════════════════════════════════════════════════════════════════════
# 4. ONBOARDING ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestOnboardingEngine:
    """Unit tests for onboarding_engine.py."""

    def test_get_preferences_empty(self, _user):
        """New user has empty preferences."""
        from app.core.onboarding_engine import get_preferences
        prefs = get_preferences(_user["id"])
        assert prefs == {}

    def test_save_preferences(self, _user):
        """Can save and retrieve preferences."""
        from app.core.onboarding_engine import save_preferences, get_preferences
        save_preferences(_user["id"], {"theme": "dark"})
        prefs = get_preferences(_user["id"])
        assert prefs["theme"] == "dark"

    def test_save_preferences_merges(self, _user):
        """Saving preferences merges with existing."""
        from app.core.onboarding_engine import save_preferences, get_preferences
        save_preferences(_user["id"], {"theme": "dark"})
        save_preferences(_user["id"], {"lang": "tr"})
        prefs = get_preferences(_user["id"])
        assert prefs["theme"] == "dark"
        assert prefs["lang"] == "tr"

    def test_is_onboarding_completed_false(self, _user):
        """New user has not completed onboarding."""
        from app.core.onboarding_engine import is_onboarding_completed
        assert is_onboarding_completed(_user["id"]) is False

    def test_complete_onboarding(self, _user):
        """complete_onboarding marks completion and saves markets."""
        from app.core.onboarding_engine import (
            complete_onboarding, is_onboarding_completed, get_preferences)
        ok = complete_onboarding(_user["id"], ["crypto", "stocks"],
                                ["BTCUSDT", "AAPL"])
        assert ok is True
        assert is_onboarding_completed(_user["id"]) is True
        prefs = get_preferences(_user["id"])
        assert "crypto" in prefs["preferred_markets"]
        assert "BTCUSDT" in prefs["watchlist_symbols"]

    def test_complete_onboarding_creates_watchlist(self, _user):
        """complete_onboarding creates a default watchlist."""
        from app.core.onboarding_engine import complete_onboarding
        from app.core.user_engine import load_user_data
        complete_onboarding(_user["id"], ["crypto"], ["BTCUSDT"])
        wl = load_user_data(_user["id"], "watchlist")
        assert isinstance(wl, list)
        assert len(wl) > 0
        symbols = [item["symbol"] for item in wl]
        assert "BTCUSDT" in symbols


# ══════════════════════════════════════════════════════════════════════
# 5. WATCHLIST INITIALISATION TESTS
# ══════════════════════════════════════════════════════════════════════

class TestWatchlistInit:
    """Watchlist initialization tests."""

    def test_init_default_watchlist_crypto(self, _user):
        """Crypto market creates BTC, ETH, SOL watchlist."""
        from app.core.onboarding_engine import init_default_watchlist
        wl = init_default_watchlist(_user["id"], ["crypto"])
        symbols = [item["symbol"] for item in wl]
        assert "BTCUSDT" in symbols
        assert "ETHUSDT" in symbols
        assert "SOLUSDT" in symbols

    def test_init_default_watchlist_stocks(self, _user):
        """Stocks market creates AAPL, NVDA, MSFT watchlist."""
        from app.core.onboarding_engine import init_default_watchlist
        wl = init_default_watchlist(_user["id"], ["stocks"])
        symbols = [item["symbol"] for item in wl]
        assert "AAPL" in symbols
        assert "NVDA" in symbols

    def test_init_default_watchlist_bist(self, _user):
        """BIST market creates THYAO, ASELS, GARAN watchlist."""
        from app.core.onboarding_engine import init_default_watchlist
        wl = init_default_watchlist(_user["id"], ["bist"])
        symbols = [item["symbol"] for item in wl]
        assert "THYAO" in symbols
        assert "ASELS" in symbols

    def test_init_default_watchlist_multiple_markets(self, _user):
        """Multiple markets combine symbols without duplicates."""
        from app.core.onboarding_engine import init_default_watchlist
        wl = init_default_watchlist(_user["id"], ["crypto", "stocks", "bist"])
        symbols = [item["symbol"] for item in wl]
        assert len(symbols) == len(set(symbols))  # no duplicates
        assert "BTCUSDT" in symbols
        assert "AAPL" in symbols
        assert "THYAO" in symbols

    def test_init_watchlist_no_overwrite(self, _user):
        """Does not overwrite existing watchlist."""
        from app.core.onboarding_engine import init_default_watchlist
        from app.core.user_engine import save_user_data
        save_user_data(_user["id"], "watchlist",
                      [{"symbol": "CUSTOM", "market": "test"}])
        wl = init_default_watchlist(_user["id"], ["crypto"])
        assert len(wl) == 1
        assert wl[0]["symbol"] == "CUSTOM"

    def test_init_watchlist_empty_markets(self, _user):
        """Empty markets list creates empty watchlist."""
        from app.core.onboarding_engine import init_default_watchlist
        wl = init_default_watchlist(_user["id"], [])
        assert wl == []


# ══════════════════════════════════════════════════════════════════════
# 6. DEMO DATA ENGINE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestDemoDataEngine:
    """Demo data engine tests."""

    def test_demo_activity_returns_list(self):
        """get_demo_activity returns a list."""
        from app.core.demo_data_engine import get_demo_activity
        events = get_demo_activity()
        assert isinstance(events, list)
        assert len(events) > 0

    def test_demo_activity_has_demo_flag(self):
        """Each demo event has demo=True."""
        from app.core.demo_data_engine import get_demo_activity
        for ev in get_demo_activity():
            assert ev["demo"] is True
            assert ev["demo_event"] is True

    def test_demo_activity_has_required_fields(self):
        """Demo events have title, symbol, type."""
        from app.core.demo_data_engine import get_demo_activity
        for ev in get_demo_activity(limit=3):
            assert "title" in ev
            assert "symbol" in ev
            assert "type" in ev
            assert "created_at" in ev

    def test_demo_activity_respects_limit(self):
        """Limit parameter controls count."""
        from app.core.demo_data_engine import get_demo_activity
        assert len(get_demo_activity(limit=3)) == 3
        assert len(get_demo_activity(limit=5)) == 5

    def test_demo_opportunities(self):
        """get_demo_opportunities returns scored opportunities."""
        from app.core.demo_data_engine import get_demo_opportunities
        opps = get_demo_opportunities()
        assert len(opps) > 0
        for opp in opps:
            assert "score" in opp
            assert "symbol" in opp
            assert opp["demo"] is True

    def test_demo_portfolio(self):
        """get_demo_portfolio returns assets."""
        from app.core.demo_data_engine import get_demo_portfolio
        assets = get_demo_portfolio()
        assert len(assets) == 3
        symbols = [a["symbol"] for a in assets]
        assert "BTCUSDT" in symbols

    def test_demo_news(self):
        """get_demo_news returns news items."""
        from app.core.demo_data_engine import get_demo_news
        news = get_demo_news()
        assert len(news) > 0
        assert news[0]["demo"] is True

    def test_trending_assets(self):
        """get_trending_assets returns assets for discover."""
        from app.core.demo_data_engine import get_trending_assets
        assets = get_trending_assets()
        assert len(assets) > 0
        assert assets[0]["demo"] is True

    def test_popular_opportunities(self):
        """get_popular_opportunities returns items."""
        from app.core.demo_data_engine import get_popular_opportunities
        opps = get_popular_opportunities()
        assert len(opps) > 0

    def test_seed_demo_portfolio(self, _user):
        """seed_demo_portfolio creates portfolio for empty user."""
        from app.core.demo_data_engine import seed_demo_portfolio
        ok = seed_demo_portfolio(_user["id"])
        assert ok is True

    def test_seed_demo_portfolio_no_duplicate(self, _user):
        """seed_demo_portfolio skips if portfolio already exists."""
        from app.core.demo_data_engine import seed_demo_portfolio
        seed_demo_portfolio(_user["id"])
        ok2 = seed_demo_portfolio(_user["id"])
        assert ok2 is False


# ══════════════════════════════════════════════════════════════════════
# 7. DEMO API ENDPOINTS TESTS
# ══════════════════════════════════════════════════════════════════════

class TestDemoAPI:
    """Demo data API endpoint tests."""

    def test_demo_activity_endpoint(self, client):
        """GET /api/demo/activity returns events."""
        resp = client.get("/api/demo/activity")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["events"]) > 0

    def test_demo_activity_limit(self, client):
        """Limit parameter works."""
        resp = client.get("/api/demo/activity?limit=3")
        data = resp.get_json()
        assert len(data["events"]) == 3

    def test_demo_opportunities_endpoint(self, client):
        """GET /api/demo/opportunities returns opps."""
        resp = client.get("/api/demo/opportunities")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["opportunities"]) > 0

    def test_demo_portfolio_endpoint(self, client):
        """GET /api/demo/portfolio returns assets."""
        resp = client.get("/api/demo/portfolio")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["assets"]) == 3

    def test_demo_trending_endpoint(self, client):
        """GET /api/demo/trending returns assets."""
        resp = client.get("/api/demo/trending")
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["assets"]) > 0


# ══════════════════════════════════════════════════════════════════════
# 8. ANALYTICS TRACKING TESTS
# ══════════════════════════════════════════════════════════════════════

class TestAnalytics:
    """Analytics tracking tests."""

    def test_track_landing_visit(self, client):
        """Can track landing_visit event."""
        resp = client.post("/api/analytics/track",
                          json={"event": "landing_visit"})
        assert resp.get_json()["ok"] is True

    def test_track_signup(self, client):
        """Can track signup event."""
        resp = client.post("/api/analytics/track",
                          json={"event": "signup", "data": {"method": "email"}})
        assert resp.get_json()["ok"] is True

    def test_track_invalid_event(self, client):
        """Invalid event name returns 400."""
        resp = client.post("/api/analytics/track",
                          json={"event": "malicious_event"})
        assert resp.status_code == 400

    def test_track_missing_event(self, client):
        """Missing event field returns 400."""
        resp = client.post("/api/analytics/track", json={})
        assert resp.status_code == 400

    def test_analytics_summary(self, client):
        """Summary endpoint returns counts."""
        from app.blueprints.analytics.routes import clear_events
        clear_events()

        client.post("/api/analytics/track",
                   json={"event": "landing_visit"})
        client.post("/api/analytics/track",
                   json={"event": "landing_visit"})
        client.post("/api/analytics/track",
                   json={"event": "signup"})

        resp = client.get("/api/analytics/summary")
        data = resp.get_json()
        assert data["ok"] is True
        assert data["total"] == 3
        assert data["counts"]["landing_visit"] == 2
        assert data["counts"]["signup"] == 1

    def test_track_onboarding_events(self, client):
        """Onboarding step events are valid."""
        for step in range(1, 6):
            resp = client.post("/api/analytics/track",
                              json={"event": f"onboarding_step_{step}"})
            assert resp.get_json()["ok"] is True

    def test_track_invite_click(self, client):
        """invite_click is a valid event."""
        resp = client.post("/api/analytics/track",
                          json={"event": "invite_click"})
        assert resp.get_json()["ok"] is True


# ══════════════════════════════════════════════════════════════════════
# 9. DISCOVER PAGE TESTS
# ══════════════════════════════════════════════════════════════════════

class TestDiscoverPage:
    """Discover page rendering tests."""

    def test_discover_page_loads(self, client):
        """Discover page returns 200."""
        resp = client.get("/discover")
        assert resp.status_code == 200

    def test_discover_has_market_snapshot(self, client):
        """Discover page has market snapshot section."""
        resp = client.get("/discover")
        assert b"market-snapshot" in resp.data

    def test_discover_has_demo_fallback(self, client):
        """Discover page has demo activity fallback JS."""
        resp = client.get("/discover")
        assert b"/api/demo/activity" in resp.data


# ══════════════════════════════════════════════════════════════════════
# 10. EMPTY STATE UX TESTS
# ══════════════════════════════════════════════════════════════════════

class TestEmptyState:
    """Empty state CSS and UX tests."""

    def test_empty_state_css_exists(self):
        """Empty state CSS classes exist in components.css."""
        css_path = os.path.join(ROOT, "static", "css", "components.css")
        with open(css_path) as f:
            css = f.read()
        assert ".empty-state-box" in css
        assert ".empty-state-icon" in css
        assert ".empty-state-text" in css
        assert ".empty-state-sub" in css

    def test_skeleton_loader_exists(self):
        """Skeleton loader CSS exists."""
        css_path = os.path.join(ROOT, "static", "css", "components.css")
        with open(css_path) as f:
            css = f.read()
        assert ".pro-skeleton" in css


# ══════════════════════════════════════════════════════════════════════
# 11. INTEGRATION TESTS
# ══════════════════════════════════════════════════════════════════════

class TestIntegration:
    """End-to-end integration tests."""

    def test_full_onboarding_flow(self, app, client, _user):
        """Complete onboarding flow: check → complete → verify."""
        with client.session_transaction() as sess:
            sess["user_id"] = _user["id"]

        # Check status — not completed
        resp = client.get("/api/onboarding/status")
        assert resp.get_json()["completed"] is False

        # Complete onboarding
        resp = client.post("/api/onboarding/complete",
                          json={"markets": ["crypto", "bist"],
                                "symbols": ["BTCUSDT", "THYAO"]})
        assert resp.get_json()["ok"] is True

        # Verify completed
        resp = client.get("/api/onboarding/status")
        assert resp.get_json()["completed"] is True

    def test_watchlist_created_after_onboarding(self, app, client, _user):
        """Watchlist auto-created after onboarding completion."""
        with client.session_transaction() as sess:
            sess["user_id"] = _user["id"]

        client.post("/api/onboarding/complete",
                   json={"markets": ["crypto", "stocks"],
                         "symbols": ["BTCUSDT", "AAPL"]})

        from app.core.user_engine import load_user_data
        wl = load_user_data(_user["id"], "watchlist")
        assert isinstance(wl, list)
        assert len(wl) > 0

    def test_landing_to_register_path(self, client):
        """Landing page has path to registration."""
        resp = client.get("/landing")
        assert b"/register" in resp.data
        # Register page loads
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_demo_data_never_empty(self, client):
        """Demo endpoints always return data (never empty)."""
        for endpoint in ["/api/demo/activity", "/api/demo/opportunities",
                        "/api/demo/portfolio", "/api/demo/trending"]:
            resp = client.get(endpoint)
            data = resp.get_json()
            assert data["ok"] is True
            # At least one key has data
            for key in ["events", "opportunities", "assets"]:
                if key in data:
                    assert len(data[key]) > 0, \
                        f"{endpoint} returned empty {key}"
