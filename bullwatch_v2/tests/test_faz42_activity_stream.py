# -*- coding: utf-8 -*-
"""FAZ 42 — Market Activity Stream / Live Intelligence Feed Tests.

Validates:
  1. File existence (engine, blueprint, template)
  2. Engine module structure (functions, constants, event types)
  3. Database operations (push, query, dedup, views, trending)
  4. Event normalization & compliance
  5. API endpoint responses (REST + JSON)
  6. WebSocket route registration
  7. Frontend template structure
  8. Discover integration widget
  9. Trade page integration (Activity tab)
  10. Copilot integration endpoint
  11. Blueprint registration in monolith
  12. Live HTTP verification (all endpoints)
"""
from __future__ import annotations

import importlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid

import pytest
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:34000"
TIMEOUT = 12

# Ensure project is importable
if BASE not in sys.path:
    sys.path.insert(0, BASE)


# ─── Helpers ────────────────────────────────────────────────────
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
    """Verify all FAZ 42 files exist."""

    def test_engine_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/activity_stream_engine.py"))

    def test_blueprint_init_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/activity/__init__.py"))

    def test_blueprint_routes_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/activity/routes.py"))

    def test_activity_template_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/activity.html"))


# ═══════════════════════════════════════════════════════════════════
# 2) ENGINE MODULE STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestEngineStructure:
    """Validate engine module has required attributes and functions."""

    def test_import_engine(self):
        mod = importlib.import_module("app.core.activity_stream_engine")
        assert mod is not None

    def test_event_types_defined(self):
        from app.core.activity_stream_engine import EVENT_TYPES
        assert isinstance(EVENT_TYPES, dict)
        assert len(EVENT_TYPES) >= 12

    def test_event_types_have_required_fields(self):
        from app.core.activity_stream_engine import EVENT_TYPES
        for key, val in EVENT_TYPES.items():
            assert "icon" in val, f"Missing icon for {key}"
            assert "label" in val, f"Missing label for {key}"
            assert "color" in val, f"Missing color for {key}"

    def test_expected_event_types_present(self):
        from app.core.activity_stream_engine import EVENT_TYPES
        expected = [
            "volume_spike", "volatility_spike", "momentum_shift",
            "sector_rotation", "news_impact", "macro_impact",
            "asset_activity", "mentor_post", "mentor_live_room",
            "strategy_activity", "social_trending", "portfolio_risk_change",
        ]
        for et in expected:
            assert et in EVENT_TYPES, f"Missing event type: {et}"

    def test_severity_levels(self):
        from app.core.activity_stream_engine import SEVERITY_LEVELS
        assert "low" in SEVERITY_LEVELS
        assert "medium" in SEVERITY_LEVELS
        assert "high" in SEVERITY_LEVELS
        assert "critical" in SEVERITY_LEVELS

    def test_public_functions_exist(self):
        from app.core import activity_stream_engine as ase
        assert callable(ase.push_event)
        assert callable(ase.get_events)
        assert callable(ase.get_event)
        assert callable(ase.get_events_for_symbol)
        assert callable(ase.get_events_for_market)
        assert callable(ase.get_trending_symbols)
        assert callable(ase.mark_viewed)
        assert callable(ase.get_unread_count)
        assert callable(ase.collect_all)
        assert callable(ase.get_activity_summary)

    def test_websocket_functions_exist(self):
        from app.core import activity_stream_engine as ase
        assert callable(ase.ws_register)
        assert callable(ase.ws_unregister)

    def test_collect_interval_defined(self):
        from app.core.activity_stream_engine import COLLECT_INTERVAL
        assert isinstance(COLLECT_INTERVAL, int)
        assert COLLECT_INTERVAL > 0

    def test_dedup_window_defined(self):
        from app.core.activity_stream_engine import DEDUP_WINDOW
        assert isinstance(DEDUP_WINDOW, int)
        assert DEDUP_WINDOW > 0

    def test_max_events_defined(self):
        from app.core.activity_stream_engine import MAX_EVENTS
        assert isinstance(MAX_EVENTS, int)
        assert MAX_EVENTS > 0


# ═══════════════════════════════════════════════════════════════════
# 3) DATABASE OPERATIONS
# ═══════════════════════════════════════════════════════════════════
class TestDatabaseOperations:
    """Test engine database CRUD operations."""

    def test_push_event_returns_id(self):
        from app.core.activity_stream_engine import push_event, _dedup_cache, _dedup_lock
        # Clear dedup so event goes through
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "volume_spike",
            "symbol": "TESTPUSH1",
            "market": "crypto",
            "title": "Test volume spike",
            "summary": "Unit test",
            "confidence": 75,
            "source": "unit_test_push",
        })
        assert eid is not None
        assert isinstance(eid, str)
        assert len(eid) > 0

    def test_push_unknown_event_type_returns_none(self):
        from app.core.activity_stream_engine import push_event
        result = push_event({
            "event_type": "nonexistent_type_xyz",
            "symbol": "BTC",
            "title": "Bad event",
            "source": "unit_test_bad",
        })
        assert result is None

    def test_push_event_dedup(self):
        from app.core.activity_stream_engine import push_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()

        eid1 = push_event({
            "event_type": "momentum_shift",
            "symbol": "DEDUP_A",
            "title": "First push",
            "source": "unit_test_dedup",
        })
        assert eid1 is not None

        eid2 = push_event({
            "event_type": "momentum_shift",
            "symbol": "DEDUP_A",
            "title": "Duplicate push",
            "source": "unit_test_dedup",
        })
        assert eid2 is None  # duplicate should be skipped

    def test_get_events_returns_list(self):
        from app.core.activity_stream_engine import get_events
        result = get_events(hours=24, limit=10)
        assert isinstance(result, list)

    def test_get_events_with_market_filter(self):
        from app.core.activity_stream_engine import get_events, push_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        push_event({
            "event_type": "asset_activity",
            "symbol": "FILTERTEST",
            "market": "stocks",
            "title": "Stock event for filter test",
            "source": "unit_test_filter_market",
        })
        result = get_events(market="stocks", hours=1, limit=50)
        assert isinstance(result, list)

    def test_get_events_with_severity_filter(self):
        from app.core.activity_stream_engine import get_events, push_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        push_event({
            "event_type": "volatility_spike",
            "symbol": "SEVTEST",
            "market": "crypto",
            "title": "Critical event",
            "confidence": 90,
            "source": "unit_test_sev",
        })
        result = get_events(severity="critical", hours=1, limit=50)
        assert isinstance(result, list)

    def test_get_event_by_id(self):
        from app.core.activity_stream_engine import push_event, get_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "sector_rotation",
            "symbol": "GETBYID",
            "market": "crypto",
            "title": "Get by ID test",
            "confidence": 65,
            "source": "unit_test_getbyid",
        })
        assert eid is not None
        event = get_event(eid)
        assert event is not None
        assert event["id"] == eid
        assert event["symbol"] == "GETBYID"
        assert event["event_type"] == "sector_rotation"

    def test_get_event_nonexistent_returns_none(self):
        from app.core.activity_stream_engine import get_event
        result = get_event("nonexistent-id-xyz-123")
        assert result is None

    def test_get_events_for_symbol(self):
        from app.core.activity_stream_engine import get_events_for_symbol, push_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        push_event({
            "event_type": "volume_spike",
            "symbol": "SYMTEST42",
            "market": "crypto",
            "title": "Symbol-specific event",
            "source": "unit_test_forsymbol",
        })
        result = get_events_for_symbol("SYMTEST42", hours=1)
        assert isinstance(result, list)

    def test_get_events_for_market(self):
        from app.core.activity_stream_engine import get_events_for_market
        result = get_events_for_market("crypto", hours=1)
        assert isinstance(result, list)

    def test_get_trending_symbols(self):
        from app.core.activity_stream_engine import get_trending_symbols
        result = get_trending_symbols(hours=24, limit=10)
        assert isinstance(result, list)

    def test_trending_symbols_structure(self):
        from app.core.activity_stream_engine import get_trending_symbols
        result = get_trending_symbols(hours=24, limit=5)
        for item in result:
            assert "symbol" in item
            assert "event_count" in item
            assert "max_confidence" in item
            assert "max_severity" in item

    def test_mark_viewed(self):
        from app.core.activity_stream_engine import push_event, mark_viewed, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "news_impact",
            "symbol": "VIEWTEST",
            "title": "View test event",
            "source": "unit_test_view",
        })
        assert eid is not None
        count = mark_viewed("test_user_42", [eid])
        assert count == 1

    def test_mark_viewed_empty_returns_zero(self):
        from app.core.activity_stream_engine import mark_viewed
        count = mark_viewed("test_user_42", [])
        assert count == 0

    def test_get_unread_count(self):
        from app.core.activity_stream_engine import get_unread_count
        count = get_unread_count("test_user_unread_42", hours=24)
        assert isinstance(count, int)
        assert count >= 0


# ═══════════════════════════════════════════════════════════════════
# 4) EVENT NORMALIZATION & COMPLIANCE
# ═══════════════════════════════════════════════════════════════════
class TestNormalization:
    """Test event sanitization and severity derivation."""

    def test_severity_from_confidence_critical(self):
        from app.core.activity_stream_engine import _severity_from_confidence
        assert _severity_from_confidence(90) == "critical"
        assert _severity_from_confidence(85) == "critical"

    def test_severity_from_confidence_high(self):
        from app.core.activity_stream_engine import _severity_from_confidence
        assert _severity_from_confidence(75) == "high"
        assert _severity_from_confidence(70) == "high"

    def test_severity_from_confidence_medium(self):
        from app.core.activity_stream_engine import _severity_from_confidence
        assert _severity_from_confidence(60) == "medium"
        assert _severity_from_confidence(50) == "medium"

    def test_severity_from_confidence_low(self):
        from app.core.activity_stream_engine import _severity_from_confidence
        assert _severity_from_confidence(40) == "low"
        assert _severity_from_confidence(10) == "low"

    def test_sanitize_removes_banned_words(self):
        from app.core.activity_stream_engine import _sanitize_text
        result = _sanitize_text("You should BUY Bitcoin now")
        assert "BUY" not in result
        assert "***" in result

    def test_sanitize_removes_sell(self):
        from app.core.activity_stream_engine import _sanitize_text
        result = _sanitize_text("Time to SELL all positions")
        assert "SELL" not in result

    def test_sanitize_removes_trade_now(self):
        from app.core.activity_stream_engine import _sanitize_text
        result = _sanitize_text("TRADE NOW for profit")
        assert "TRADE NOW" not in result

    def test_sanitize_removes_stop_loss(self):
        from app.core.activity_stream_engine import _sanitize_text
        result = _sanitize_text("Set your STOP LOSS at 100")
        assert "STOP LOSS" not in result

    def test_sanitize_preserves_clean_text(self):
        from app.core.activity_stream_engine import _sanitize_text
        text = "Bitcoin shows strong momentum indicators"
        result = _sanitize_text(text)
        assert result == text

    def test_sanitize_handles_empty(self):
        from app.core.activity_stream_engine import _sanitize_text
        assert _sanitize_text("") == ""
        assert _sanitize_text(None) is None

    def test_invalid_severity_defaults_to_low(self):
        from app.core.activity_stream_engine import push_event, get_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "volume_spike",
            "symbol": "BADSEV",
            "title": "Bad severity event",
            "severity": "ultra_extreme",
            "source": "unit_test_badsev",
        })
        assert eid is not None
        ev = get_event(eid)
        assert ev["severity"] == "low"

    def test_metadata_stored_as_json(self):
        from app.core.activity_stream_engine import push_event, get_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        meta = {"price": 50000.5, "exchange": "binance", "custom_field": True}
        eid = push_event({
            "event_type": "asset_activity",
            "symbol": "METATEST",
            "title": "Metadata test",
            "source": "unit_test_meta",
            "metadata": meta,
        })
        assert eid is not None
        ev = get_event(eid)
        assert "metadata" in ev
        assert ev["metadata"]["price"] == 50000.5
        assert ev["metadata"]["exchange"] == "binance"


# ═══════════════════════════════════════════════════════════════════
# 5) COLLECT ALL
# ═══════════════════════════════════════════════════════════════════
class TestCollectors:
    """Test the collect_all aggregation function."""

    def test_collect_all_returns_int(self):
        from app.core.activity_stream_engine import collect_all
        result = collect_all()
        assert isinstance(result, int)
        assert result >= 0

    def test_collect_all_no_crash(self):
        """Collectors should handle missing/erroring engines gracefully."""
        from app.core.activity_stream_engine import collect_all
        # Should not raise even if source engines aren't running
        try:
            collect_all()
        except Exception:
            pytest.fail("collect_all() raised an exception")


# ═══════════════════════════════════════════════════════════════════
# 6) ACTIVITY SUMMARY (Copilot)
# ═══════════════════════════════════════════════════════════════════
class TestActivitySummary:
    """Test get_activity_summary output."""

    def test_summary_returns_dict(self):
        from app.core.activity_stream_engine import get_activity_summary
        result = get_activity_summary(hours=6)
        assert isinstance(result, dict)

    def test_summary_has_required_fields(self):
        from app.core.activity_stream_engine import get_activity_summary
        result = get_activity_summary(hours=6)
        assert "total_events" in result
        assert "summary" in result
        assert "trending_symbols" in result

    def test_summary_string_is_not_empty(self):
        from app.core.activity_stream_engine import get_activity_summary
        result = get_activity_summary(hours=24)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0


# ═══════════════════════════════════════════════════════════════════
# 7) TEMPLATE STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestTemplateStructure:
    """Validate activity.html template."""

    def test_extends_layout_terminal(self):
        html = _read("templates/activity.html")
        assert "layout_terminal.html" in html

    def test_has_activity_event_list(self):
        html = _read("templates/activity.html")
        assert "act-event-list" in html

    def test_has_filter_chips(self):
        html = _read("templates/activity.html")
        assert "act-filter-chip" in html
        assert "data-filter" in html

    def test_has_severity_classes(self):
        html = _read("templates/activity.html")
        assert "severity-critical" in html
        assert "severity-high" in html
        assert "severity-medium" in html
        assert "severity-low" in html

    def test_has_trending_section(self):
        html = _read("templates/activity.html")
        assert "act-trending" in html

    def test_has_ai_summary_section(self):
        html = _read("templates/activity.html")
        assert "act-ai-summary" in html

    def test_has_websocket_code(self):
        html = _read("templates/activity.html")
        assert "ws/activity" in html

    def test_has_load_more_button(self):
        html = _read("templates/activity.html")
        assert "act-load-more" in html

    def test_has_event_meta_js(self):
        html = _read("templates/activity.html")
        assert "EVENT_META" in html
        assert "volume_spike" in html


# ═══════════════════════════════════════════════════════════════════
# 8) DISCOVER INTEGRATION
# ═══════════════════════════════════════════════════════════════════
class TestDiscoverIntegration:
    """Verify discover.html has activity stream widget."""

    def test_discover_has_activity_section(self):
        html = _read("templates/discover.html")
        assert "disc-activity-stream" in html

    def test_discover_has_activity_api_call(self):
        html = _read("templates/discover.html")
        assert "/api/activity" in html

    def test_discover_has_activity_link(self):
        html = _read("templates/discover.html")
        assert 'href="/activity"' in html

    def test_discover_has_faz42_comment(self):
        html = _read("templates/discover.html")
        assert "FAZ 42" in html


# ═══════════════════════════════════════════════════════════════════
# 9) TRADE PAGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════
class TestTradeIntegration:
    """Verify trade.html has Activity tab."""

    def test_trade_has_activity_tab_button(self):
        html = _read("templates/trade.html")
        assert 'data-tab="activity"' in html

    def test_trade_has_activity_tab_pane(self):
        html = _read("templates/trade.html")
        assert 'id="tab-activity"' in html

    def test_trade_has_activity_feed_container(self):
        html = _read("templates/trade.html")
        assert "tradeActivityFeed" in html

    def test_trade_has_activity_api_call(self):
        html = _read("templates/trade.html")
        assert "/api/activity" in html

    def test_trade_has_faz42_comment(self):
        html = _read("templates/trade.html")
        assert "FAZ 42" in html


# ═══════════════════════════════════════════════════════════════════
# 10) SIDEBAR NAV
# ═══════════════════════════════════════════════════════════════════
class TestSidebarNav:
    """Verify activity nav item in sidebar."""

    def test_layout_has_activity_nav(self):
        html = _read("templates/layout_terminal.html")
        assert 'href="/activity"' in html

    def test_layout_activity_nav_text(self):
        html = _read("templates/layout_terminal.html")
        assert "Activity" in html


# ═══════════════════════════════════════════════════════════════════
# 11) BLUEPRINT REGISTRATION
# ═══════════════════════════════════════════════════════════════════
class TestBlueprintRegistration:
    """Verify monolith registers activity blueprint and routes."""

    def test_monolith_imports_activity_bp(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.activity import activity_bp" in src

    def test_monolith_registers_activity_bp(self):
        src = _read("legacy_monolith.py")
        assert "app.register_blueprint(activity_bp)" in src

    def test_monolith_has_ws_activity_route(self):
        src = _read("legacy_monolith.py")
        assert "ws/activity" in src

    def test_monolith_has_activity_stream_boot(self):
        src = _read("legacy_monolith.py")
        assert "activity_collect_loop" in src or "activity_stream" in src

    def test_copilot_has_activity_endpoint(self):
        src = _read("app/blueprints/copilot/routes.py")
        assert "/api/copilot/activity" in src


# ═══════════════════════════════════════════════════════════════════
# 12) LIVE HTTP VERIFICATION
# ═══════════════════════════════════════════════════════════════════
class TestLiveHTTP:
    """Live HTTP tests against running server."""

    def test_activity_page_200(self):
        r = _get("/activity")
        assert r.status_code == 200

    def test_activity_page_has_content(self):
        r = _get("/activity")
        assert "act-event-list" in r.text
        assert "Activity Stream" in r.text

    def test_api_activity_200(self):
        r = _get("/api/activity")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "data" in data

    def test_api_activity_with_filters(self):
        r = _get("/api/activity?market=crypto&severity=high&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_api_activity_trending_200(self):
        r = _get("/api/activity/trending")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "data" in data

    def test_api_activity_trending_with_params(self):
        r = _get("/api/activity/trending?hours=6&limit=5")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_api_activity_event_not_found(self):
        r = _get("/api/activity/nonexistent-event-id-999")
        assert r.status_code == 404

    def test_api_activity_symbol_200(self):
        r = _get("/api/activity/symbol/BTCUSDT")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["symbol"] == "BTCUSDT"

    def test_api_activity_market_200(self):
        r = _get("/api/activity/market/crypto")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["market"] == "crypto"

    def test_api_activity_mark_viewed_200(self):
        r = _post("/api/activity/mark-viewed", {"event_ids": []})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_api_activity_unread_count_200(self):
        r = _get("/api/activity/unread-count")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "unread" in data

    def test_api_activity_summary_200(self):
        r = _get("/api/activity/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "data" in data

    def test_api_copilot_activity_200(self):
        r = _post("/api/copilot/activity", {"hours": 6})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_discover_page_shows_activity_widget(self):
        r = _get("/discover")
        assert r.status_code == 200
        assert "disc-activity-stream" in r.text

    def test_trade_page_shows_activity_tab(self):
        r = _get("/trade")
        assert r.status_code == 200
        assert "tab-activity" in r.text

    def test_activity_nav_in_sidebar(self):
        r = _get("/activity")
        assert r.status_code == 200
        assert 'href="/activity"' in r.text


# ═══════════════════════════════════════════════════════════════════
# 13) DEDUP CACHE
# ═══════════════════════════════════════════════════════════════════
class TestDedupCache:
    """Test dedup cache mechanism."""

    def test_dedup_key_deterministic(self):
        from app.core.activity_stream_engine import _dedup_key
        k1 = _dedup_key("volume_spike", "BTCUSDT", "opp_engine")
        k2 = _dedup_key("volume_spike", "BTCUSDT", "opp_engine")
        assert k1 == k2

    def test_dedup_key_differs_for_different_input(self):
        from app.core.activity_stream_engine import _dedup_key
        k1 = _dedup_key("volume_spike", "BTCUSDT", "opp_engine")
        k2 = _dedup_key("momentum_shift", "BTCUSDT", "opp_engine")
        assert k1 != k2

    def test_is_duplicate_first_call_is_false(self):
        from app.core.activity_stream_engine import _is_duplicate, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        result = _is_duplicate("volume_spike", "UNIQUESYM42", "test_dup")
        assert result is False

    def test_is_duplicate_second_call_is_true(self):
        from app.core.activity_stream_engine import _is_duplicate, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        _is_duplicate("volume_spike", "DUPSYM42", "test_dup2")
        result = _is_duplicate("volume_spike", "DUPSYM42", "test_dup2")
        assert result is True


# ═══════════════════════════════════════════════════════════════════
# 14) ROW CONVERSION
# ═══════════════════════════════════════════════════════════════════
class TestRowConversion:
    """Test _row_to_dict utility."""

    def test_row_to_dict_metadata_parsing(self):
        from app.core.activity_stream_engine import push_event, get_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "macro_impact",
            "symbol": "ROWTEST",
            "title": "Row conversion test",
            "source": "unit_test_row",
            "metadata": {"key": "value", "num": 42},
        })
        ev = get_event(eid)
        assert "metadata" in ev
        assert "metadata_json" not in ev  # should be converted
        assert ev["metadata"]["key"] == "value"
        assert ev["metadata"]["num"] == 42

    def test_event_has_all_expected_fields(self):
        from app.core.activity_stream_engine import push_event, get_event, _dedup_cache, _dedup_lock
        with _dedup_lock:
            _dedup_cache.clear()
        eid = push_event({
            "event_type": "strategy_activity",
            "symbol": "FIELDTEST",
            "market": "forex",
            "title": "Field check event",
            "summary": "Testing all fields",
            "confidence": 65,
            "source": "unit_test_fields",
        })
        ev = get_event(eid)
        assert ev is not None
        expected_fields = ["id", "event_type", "market", "symbol", "title",
                           "summary", "confidence", "severity", "source",
                           "created_at", "metadata"]
        for f in expected_fields:
            assert f in ev, f"Missing field: {f}"
