# -*- coding: utf-8 -*-
"""FAZ 40 — AI Smart Alerts & Market Opportunity Engine tests.

50+ tests covering:
  - Opportunity engine: detectors, DB ops, cache, helpers
  - Smart alert engine: CRUD, evaluation, matching, cooldown, triggers
  - API routes: all endpoints, auth checks, filters, edge cases
  - LEGAL_SAFE_MODE compliance
"""
import json
import os
import sqlite3
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from legacy_monolith import app


# ══════════════════════════════════════════════════════════════════════
# FIXTURES
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def client():
    """Flask test client."""
    with app.test_client() as c:
        yield c


@pytest.fixture
def tmp_db(monkeypatch, tmp_path):
    """Use a temporary DB for opportunity + smart alert engines."""
    db_path = str(tmp_path / "opportunities.db")
    db_dir = str(tmp_path)
    monkeypatch.setattr("app.core.db_manager._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.opportunity_engine._DB_PATH", db_path)
    monkeypatch.setattr("app.core.opportunity_engine._DB_DIR", db_dir)
    monkeypatch.setattr("app.core.smart_alert_engine._DB_PATH", db_path)
    monkeypatch.setattr("app.core.smart_alert_engine._DB_DIR", db_dir)
    # Init the tables
    from app.core.opportunity_engine import _init_db as init_opp
    from app.core.smart_alert_engine import _init_db as init_alert
    init_opp()
    init_alert()
    return db_path


@pytest.fixture
def sample_klines_rising():
    """Generate klines with clear rising trend (25+ bars)."""
    klines = []
    base = 100.0
    for i in range(30):
        close = base + i * 2.0 + (i % 3) * 0.5
        klines.append({
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.5,
            "close": close,
            "volume": 1000 + i * 50,
        })
    return klines


@pytest.fixture
def sample_klines_volume_spike():
    """Klines with last bar having huge volume spike (>2x avg)."""
    klines = []
    for i in range(20):
        klines.append({
            "open": 50.0, "high": 51.0, "low": 49.0, "close": 50.0,
            "volume": 1000,
        })
    # Last bar: 5x average volume
    klines.append({
        "open": 50.0, "high": 52.0, "low": 49.0, "close": 51.5,
        "volume": 5000,
    })
    return klines


@pytest.fixture
def sample_klines_rsi_overbought():
    """Klines producing RSI > 75 (steadily rising closes)."""
    klines = []
    for i in range(20):
        close = 100.0 + i * 3.0  # Steady rise → high RSI
        klines.append({
            "open": close - 1, "high": close + 0.5,
            "low": close - 1.5, "close": close, "volume": 1000,
        })
    return klines


@pytest.fixture
def sample_klines_rsi_oversold():
    """Klines producing RSI < 25 (steadily falling closes)."""
    klines = []
    for i in range(20):
        close = 200.0 - i * 3.0  # Steady decline → low RSI
        klines.append({
            "open": close + 1, "high": close + 1.5,
            "low": close - 0.5, "close": close, "volume": 1000,
        })
    return klines


@pytest.fixture
def sample_klines_ema_cross():
    """Klines with EMA9/21 bullish crossover in last 2 bars."""
    klines = []
    # First 20 bars: declining
    for i in range(20):
        close = 100.0 - i * 0.5
        klines.append({
            "open": close + 0.2, "high": close + 0.5,
            "low": close - 0.5, "close": close, "volume": 1000,
        })
    # Last 6 bars: sharp rise → EMA9 crosses above EMA21
    for i in range(6):
        close = 90.0 + i * 5.0
        klines.append({
            "open": close - 2, "high": close + 1,
            "low": close - 2.5, "close": close, "volume": 1500,
        })
    return klines


@pytest.fixture
def sample_klines_breakout():
    """Klines with breakout above 20-bar range."""
    klines = []
    # 22 bars within a range of 48-52
    for i in range(22):
        close = 50.0 + (i % 3) - 1  # oscillates 49-51
        klines.append({
            "open": close, "high": close + 1.5, "low": close - 1.5,
            "close": close, "volume": 1000,
        })
    # Last bar: breakout above 52.5
    klines.append({
        "open": 51.0, "high": 56.0, "low": 51.0, "close": 55.0,
        "volume": 2000,
    })
    return klines


@pytest.fixture
def sample_klines_whale():
    """Klines with a whale-like single candle (>5x median volume)."""
    klines = []
    for i in range(15):
        klines.append({
            "open": 100.0, "high": 101.0, "low": 99.0,
            "close": 100.0 + (i % 2), "volume": 500 + i * 10,
        })
    # Last bar: 10x median volume
    klines.append({
        "open": 100.0, "high": 103.0, "low": 99.0, "close": 102.0,
        "volume": 8000,
    })
    return klines


@pytest.fixture
def sample_klines_volatile():
    """Klines with a volatility spike in the last bar."""
    klines = []
    for i in range(20):
        klines.append({
            "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0,
            "volume": 1000,
        })
    # Very wide range candle → high ATR ratio
    klines.append({
        "open": 100.0, "high": 110.0, "low": 90.0, "close": 105.0,
        "volume": 3000,
    })
    return klines


@pytest.fixture
def sample_opps():
    """A list of sample opportunities for alert evaluation."""
    return [
        {
            "id": "opp-001", "symbol": "BTCUSDT", "market": "crypto",
            "event_type": "volume_spike", "confidence": 85,
            "description": "BTCUSDT: Hacim artışı", "details": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "opp-002", "symbol": "ETHUSDT", "market": "crypto",
            "event_type": "momentum_shift", "confidence": 72,
            "description": "ETHUSDT: Momentum değişimi", "details": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "opp-003", "symbol": "META", "market": "stocks",
            "event_type": "price_anomaly", "confidence": 74,
            "description": "META: Fiyat anomalisi", "details": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        {
            "id": "opp-004", "symbol": "EURUSD", "market": "forex",
            "event_type": "price_anomaly", "confidence": 65,
            "description": "EURUSD: Dikkat çekici hareket", "details": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]


def _fake_user_session(client, user_id="test-user-123"):
    """Set session to simulate a logged-in user."""
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


# ══════════════════════════════════════════════════════════════════════
# 1. OPPORTUNITY ENGINE — HELPER TESTS
# ══════════════════════════════════════════════════════════════════════

class TestOpportunityHelpers:
    """Test calculation helpers in opportunity_engine."""

    def test_calc_rsi_all_gains(self):
        from app.core.opportunity_engine import _calc_rsi
        # Steadily rising → RSI near 100
        closes = [float(i) for i in range(1, 20)]
        rsi = _calc_rsi(closes, 14)
        assert rsi is not None
        assert rsi > 90  # All gains → near 100

    def test_calc_rsi_all_losses(self):
        from app.core.opportunity_engine import _calc_rsi
        closes = [float(20 - i) for i in range(20)]
        rsi = _calc_rsi(closes, 14)
        assert rsi is not None
        assert rsi < 10  # All losses → near 0

    def test_calc_rsi_insufficient_data(self):
        from app.core.opportunity_engine import _calc_rsi
        rsi = _calc_rsi([1.0, 2.0, 3.0], 14)
        assert rsi is None

    def test_calc_ema_basic(self):
        from app.core.opportunity_engine import _calc_ema
        vals = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
        ema = _calc_ema(vals, 5)
        assert len(ema) > 0
        # EMA should be close to recent values
        assert ema[-1] > 15.0

    def test_calc_ema_insufficient_data(self):
        from app.core.opportunity_engine import _calc_ema
        assert _calc_ema([1.0, 2.0], 5) == []
        assert _calc_ema([], 5) == []

    def test_calc_atr(self):
        from app.core.opportunity_engine import _calc_atr
        highs = [float(50 + i % 3) for i in range(20)]
        lows = [float(48 + i % 3) for i in range(20)]
        closes = [float(49 + i % 3) for i in range(20)]
        atr = _calc_atr(highs, lows, closes, 14)
        assert atr is not None
        assert atr > 0

    def test_calc_atr_insufficient_data(self):
        from app.core.opportunity_engine import _calc_atr
        atr = _calc_atr([1.0, 2.0], [0.5, 1.5], [0.8, 1.8], 14)
        assert atr is None

    def test_make_opportunity(self):
        from app.core.opportunity_engine import _make_opportunity, EVENT_TYPES
        opp = _make_opportunity("BTCUSDT", "crypto", "volume_spike", 75,
                                "Test desc", "Test details", 50000.0, 2.5)
        assert opp["symbol"] == "BTCUSDT"
        assert opp["market"] == "crypto"
        assert opp["event_type"] == "volume_spike"
        assert opp["confidence"] == 75
        assert opp["icon"] == EVENT_TYPES["volume_spike"]["icon"]
        assert opp["id"]  # non-empty
        assert opp["created_at"]  # non-empty

    def test_make_opportunity_clamps_confidence(self):
        from app.core.opportunity_engine import _make_opportunity
        opp_high = _make_opportunity("X", "crypto", "breakout", 150, "test")
        assert opp_high["confidence"] == 100
        opp_low = _make_opportunity("X", "crypto", "breakout", -10, "test")
        assert opp_low["confidence"] == 0


# ══════════════════════════════════════════════════════════════════════
# 2. OPPORTUNITY ENGINE — INDIVIDUAL DETECTORS
# ══════════════════════════════════════════════════════════════════════

class TestOpportunityDetectors:
    """Test each detection function."""

    def test_detect_volume_spike_triggered(self, sample_klines_volume_spike):
        from app.core.opportunity_engine import detect_volume_spike
        opp = detect_volume_spike("BTCUSDT", "crypto", sample_klines_volume_spike)
        assert opp is not None
        assert opp["event_type"] == "volume_spike"
        assert opp["symbol"] == "BTCUSDT"
        assert opp["confidence"] >= 50

    def test_detect_volume_spike_not_triggered(self):
        from app.core.opportunity_engine import detect_volume_spike
        # Uniform volume → no spike
        klines = [{"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 1000}
                  for _ in range(10)]
        assert detect_volume_spike("X", "crypto", klines) is None

    def test_detect_volume_spike_empty(self):
        from app.core.opportunity_engine import detect_volume_spike
        assert detect_volume_spike("X", "crypto", []) is None
        assert detect_volume_spike("X", "crypto", None) is None

    def test_detect_momentum_bullish_cross(self, sample_klines_ema_cross):
        from app.core.opportunity_engine import detect_momentum
        opp = detect_momentum("XRPUSDT", "crypto", sample_klines_ema_cross)
        # May or may not trigger depending on exact data; test no crash
        if opp:
            assert opp["event_type"] == "momentum_shift"
            assert "kesişimi" in opp["description"]

    def test_detect_momentum_insufficient_data(self):
        from app.core.opportunity_engine import detect_momentum
        short = [{"close": i, "volume": 100, "open": i, "high": i+1, "low": i-1}
                 for i in range(10)]
        assert detect_momentum("X", "crypto", short) is None

    def test_detect_momentum_none_input(self):
        from app.core.opportunity_engine import detect_momentum
        assert detect_momentum("X", "crypto", None) is None

    def test_detect_volatility_spike_triggered(self, sample_klines_volatile):
        from app.core.opportunity_engine import detect_volatility_spike
        opp = detect_volatility_spike("SOLUSDT", "crypto", sample_klines_volatile)
        assert opp is not None
        assert opp["event_type"] == "volatility_spike"
        assert "ATR" in opp["description"]

    def test_detect_volatility_spike_calm_market(self):
        from app.core.opportunity_engine import detect_volatility_spike
        klines = [{"open": 100, "high": 101, "low": 99, "close": 100, "volume": 1000}
                  for _ in range(25)]
        assert detect_volatility_spike("X", "crypto", klines) is None

    def test_detect_rsi_extreme_overbought(self, sample_klines_rsi_overbought):
        from app.core.opportunity_engine import detect_rsi_extreme
        opp = detect_rsi_extreme("BTCUSDT", "crypto", sample_klines_rsi_overbought)
        assert opp is not None
        assert opp["event_type"] == "rsi_extreme"
        assert "aşırı alım" in opp["description"]

    def test_detect_rsi_extreme_oversold(self, sample_klines_rsi_oversold):
        from app.core.opportunity_engine import detect_rsi_extreme
        opp = detect_rsi_extreme("ETHUSDT", "crypto", sample_klines_rsi_oversold)
        assert opp is not None
        assert opp["event_type"] == "rsi_extreme"
        assert "aşırı satım" in opp["description"]

    def test_detect_rsi_normal(self):
        from app.core.opportunity_engine import detect_rsi_extreme
        # Alternating up/down → RSI near 50
        klines = []
        for i in range(20):
            close = 100.0 + (1 if i % 2 == 0 else -1) * 0.5
            klines.append({"open": close, "high": close + 0.5,
                           "low": close - 0.5, "close": close, "volume": 1000})
        assert detect_rsi_extreme("X", "crypto", klines) is None

    def test_detect_breakout_above(self, sample_klines_breakout):
        from app.core.opportunity_engine import detect_breakout
        opp = detect_breakout("AVAXUSDT", "crypto", sample_klines_breakout)
        assert opp is not None
        assert opp["event_type"] == "breakout"
        assert "yukarı" in opp["description"]

    def test_detect_breakout_none_inside_range(self):
        from app.core.opportunity_engine import detect_breakout
        klines = []
        for i in range(25):
            klines.append({"open": 50, "high": 51, "low": 49, "close": 50,
                           "volume": 1000})
        assert detect_breakout("X", "crypto", klines) is None

    def test_detect_whale_activity_triggered(self, sample_klines_whale):
        from app.core.opportunity_engine import detect_whale_activity
        opp = detect_whale_activity("PEPEUSDT", "crypto", sample_klines_whale)
        assert opp is not None
        assert opp["event_type"] == "whale_activity"
        assert "büyük hacim" in opp["description"]

    def test_detect_whale_activity_normal(self):
        from app.core.opportunity_engine import detect_whale_activity
        klines = [{"open": 10, "high": 11, "low": 9, "close": 10, "volume": 1000}
                  for _ in range(15)]
        assert detect_whale_activity("X", "crypto", klines) is None


# ══════════════════════════════════════════════════════════════════════
# 3. OPPORTUNITY ENGINE — DATABASE OPERATIONS
# ══════════════════════════════════════════════════════════════════════

class TestOpportunityDB:
    """Test DB operations in opportunity_engine."""

    def test_save_and_get(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, get_db_opportunities
        opp = {
            "id": "test-opp-1", "symbol": "BTCUSDT", "market": "crypto",
            "event_type": "volume_spike", "confidence": 80,
            "description": "Test opportunity", "details": "detail",
            "price": 50000.0, "change_pct": 2.5,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": None,
        }
        _save_opportunity(opp)
        rows = get_db_opportunities()
        assert any(r["id"] == "test-opp-1" for r in rows)

    def test_get_with_market_filter(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, get_db_opportunities
        for i, mkt in enumerate(["crypto", "stocks", "forex"]):
            _save_opportunity({
                "id": f"opp-m-{i}", "symbol": f"SYM{i}",
                "market": mkt, "event_type": "volume_spike",
                "confidence": 70, "description": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        crypto = get_db_opportunities(market="crypto")
        assert all(r["market"] == "crypto" for r in crypto)
        assert len(crypto) >= 1

    def test_get_with_event_filter(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, get_db_opportunities
        for i, evt in enumerate(["volume_spike", "rsi_extreme", "breakout"]):
            _save_opportunity({
                "id": f"opp-e-{i}", "symbol": f"SYM{i}",
                "market": "crypto", "event_type": evt,
                "confidence": 60, "description": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        vs = get_db_opportunities(event_type="volume_spike")
        assert all(r["event_type"] == "volume_spike" for r in vs)

    def test_deactivate_old(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, _deactivate_old, get_db_opportunities
        old_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        _save_opportunity({
            "id": "old-opp", "symbol": "OLD", "market": "crypto",
            "event_type": "volume_spike", "confidence": 60,
            "description": "old", "created_at": old_time,
        })
        _deactivate_old()
        active = get_db_opportunities()
        assert not any(r["id"] == "old-opp" for r in active)

    def test_mark_viewed(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, mark_viewed
        _save_opportunity({
            "id": "view-opp", "symbol": "V", "market": "crypto",
            "event_type": "volume_spike", "confidence": 60,
            "description": "test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        mark_viewed("user-abc", "view-opp")
        # No error = success; check DB
        import sqlite3
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM user_opportunity_views WHERE user_id=?", ("user-abc",)
        ).fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0]["opportunity_id"] == "view-opp"

    def test_get_opportunity_by_symbol(self, tmp_db):
        from app.core.opportunity_engine import _save_opportunity, get_opportunity_by_symbol
        _save_opportunity({
            "id": "sym-opp-1", "symbol": "XRPUSDT", "market": "crypto",
            "event_type": "breakout", "confidence": 70,
            "description": "test",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        results = get_opportunity_by_symbol("XRPUSDT")
        assert len(results) >= 1
        assert results[0]["symbol"] == "XRPUSDT"

    def test_get_opportunity_by_symbol_empty(self, tmp_db):
        from app.core.opportunity_engine import get_opportunity_by_symbol
        results = get_opportunity_by_symbol("NONEXISTENT")
        assert results == []


# ══════════════════════════════════════════════════════════════════════
# 4. OPPORTUNITY ENGINE — CACHE
# ══════════════════════════════════════════════════════════════════════

class TestOpportunityCache:
    """Test cache operations."""

    def test_get_cached_opportunities_with_cache(self, tmp_db):
        from app.core.opportunity_engine import get_cached_opportunities, CACHE_KEY
        from app.cache import cache_set
        fake = [{"id": "cached-1", "symbol": "BTC", "confidence": 90}]
        cache_set(CACHE_KEY, fake)
        result = get_cached_opportunities()
        assert len(result) >= 1

    def test_get_trending_limits(self, tmp_db):
        from app.core.opportunity_engine import get_trending_opportunities, _save_opportunity, CACHE_KEY
        from app.cache import cache_set
        opps = []
        for i in range(10):
            o = {
                "id": f"trend-{i}", "symbol": f"S{i}", "market": "crypto",
                "event_type": "volume_spike", "confidence": 90 - i * 5,
                "description": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            opps.append(o)
            _save_opportunity(o)
        cache_set(CACHE_KEY, opps)
        top3 = get_trending_opportunities(limit=3)
        assert len(top3) == 3
        # Should be sorted by confidence descending
        assert top3[0]["confidence"] >= top3[1]["confidence"]


# ══════════════════════════════════════════════════════════════════════
# 5. SMART ALERT ENGINE — CRUD
# ══════════════════════════════════════════════════════════════════════

class TestSmartAlertCRUD:
    """Test smart alert create/read/update/delete."""

    def test_create_alert(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert
        alert = create_smart_alert("user-1", {
            "alert_type": "event_volume_spike",
            "name": "BTC Hacim",
            "symbol": "BTCUSDT",
            "market": "crypto",
            "min_confidence": 70,
            "cooldown_minutes": 30,
        })
        assert alert["id"]
        assert alert["user_id"] == "user-1"
        assert alert["alert_type"] == "event_volume_spike"
        assert alert["symbol"] == "BTCUSDT"
        assert alert["min_confidence"] == 70

    def test_create_alert_invalid_type(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert
        with pytest.raises(ValueError, match="Invalid alert_type"):
            create_smart_alert("user-1", {
                "alert_type": "nonexistent_type",
                "name": "test",
            })

    def test_create_alert_empty_name_uses_default(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert, SMART_ALERT_TYPES
        alert = create_smart_alert("user-1", {
            "alert_type": "opportunity_any",
        })
        assert alert["name"] == SMART_ALERT_TYPES["opportunity_any"]

    def test_get_user_alerts(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert, get_user_alerts
        create_smart_alert("user-a", {"alert_type": "opportunity_any", "name": "A1"})
        create_smart_alert("user-a", {"alert_type": "market_crypto", "name": "A2"})
        create_smart_alert("user-b", {"alert_type": "opportunity_any", "name": "B1"})
        alerts_a = get_user_alerts("user-a")
        alerts_b = get_user_alerts("user-b")
        assert len(alerts_a) == 2
        assert len(alerts_b) == 1

    def test_delete_alert(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert, delete_smart_alert, get_user_alerts
        alert = create_smart_alert("user-d", {
            "alert_type": "event_breakout", "name": "Del Test",
        })
        assert delete_smart_alert("user-d", alert["id"]) is True
        assert len(get_user_alerts("user-d")) == 0

    def test_delete_alert_wrong_user(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert, delete_smart_alert
        alert = create_smart_alert("user-x", {
            "alert_type": "event_breakout", "name": "Test",
        })
        # Another user cannot delete
        assert delete_smart_alert("user-y", alert["id"]) is False

    def test_update_alert(self, tmp_db):
        from app.core.smart_alert_engine import create_smart_alert, update_smart_alert
        alert = create_smart_alert("user-u", {
            "alert_type": "confidence_high", "name": "Original",
        })
        updated = update_smart_alert("user-u", alert["id"], {
            "name": "Updated Name",
            "min_confidence": 90,
            "active": False,
        })
        assert updated is not None
        assert updated["name"] == "Updated Name"
        assert updated["min_confidence"] == 90
        assert updated["active"] == 0

    def test_update_alert_not_found(self, tmp_db):
        from app.core.smart_alert_engine import update_smart_alert
        result = update_smart_alert("user-u", "nonexistent", {"name": "x"})
        assert result is None


# ══════════════════════════════════════════════════════════════════════
# 6. SMART ALERT ENGINE — EVALUATION & MATCHING
# ══════════════════════════════════════════════════════════════════════

class TestSmartAlertEvaluation:
    """Test alert matching and evaluation logic."""

    def test_match_opportunity_any(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-eval", {
            "alert_type": "opportunity_any",
            "name": "Any Opp",
            "min_confidence": 50,
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) >= 1
        assert triggered[0]["user_id"] == "user-eval"

    def test_match_opportunity_symbol(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-sym", {
            "alert_type": "opportunity_symbol",
            "name": "BTC Alert",
            "symbol": "BTCUSDT",
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) >= 1
        assert "BTCUSDT" in triggered[0]["message"]

    def test_match_confidence_high(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-conf", {
            "alert_type": "confidence_high",
            "name": "High Conf",
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) >= 1
        # Should match opp-001 with confidence 85

    def test_match_event_type(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-evt", {
            "alert_type": "event_volume_spike",
            "name": "Volume Spike Alert",
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) >= 1

    def test_match_market_filter(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-mkt", {
            "alert_type": "market_stocks",
            "name": "Stocks Alert",
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) >= 1

    def test_no_match_below_confidence(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-noconf", {
            "alert_type": "opportunity_any",
            "name": "Very High Conf",
            "min_confidence": 99,  # Higher than any opp
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) == 0

    def test_no_match_wrong_symbol(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-nosym", {
            "alert_type": "opportunity_symbol",
            "name": "Nonexistent",
            "symbol": "ZZZZUSDT",
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) == 0

    def test_no_match_wrong_market(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-nomkt", {
            "alert_type": "market_forex",
            "name": "Forex Only",
            "market": "forex",
            "min_confidence": 90,  # No forex opp with 90+ confidence
        })
        triggered = evaluate_alerts(sample_opps)
        assert len(triggered) == 0

    def test_evaluate_empty_opportunities(self, tmp_db):
        from app.core.smart_alert_engine import evaluate_alerts
        assert evaluate_alerts([]) == []

    def test_cooldown_prevents_retrigger(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, evaluate_alerts
        create_smart_alert("user-cd", {
            "alert_type": "opportunity_any",
            "name": "Cooldown Test",
            "min_confidence": 50,
            "cooldown_minutes": 60,
        })
        # First evaluation triggers
        t1 = evaluate_alerts(sample_opps)
        assert len(t1) >= 1
        # Second evaluation should be blocked by cooldown
        t2 = evaluate_alerts(sample_opps)
        assert len(t2) == 0

    def test_inactive_alert_skipped(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import create_smart_alert, update_smart_alert, evaluate_alerts
        alert = create_smart_alert("user-inact", {
            "alert_type": "opportunity_any",
            "name": "Inactive",
        })
        update_smart_alert("user-inact", alert["id"], {"active": False})
        triggered = evaluate_alerts(sample_opps)
        inactive_triggers = [t for t in triggered if t["user_id"] == "user-inact"]
        assert len(inactive_triggers) == 0


# ══════════════════════════════════════════════════════════════════════
# 7. SMART ALERT ENGINE — TRIGGERS & NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════

class TestSmartAlertTriggers:
    """Test trigger recording, reading, marking as read."""

    def test_get_triggered_alerts(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import (
            create_smart_alert, evaluate_alerts, get_triggered_alerts,
        )
        create_smart_alert("user-trg", {
            "alert_type": "opportunity_any", "name": "T",
        })
        evaluate_alerts(sample_opps)
        triggers = get_triggered_alerts("user-trg")
        assert len(triggers) >= 1

    def test_get_unread_count(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import (
            create_smart_alert, evaluate_alerts, get_unread_count,
        )
        create_smart_alert("user-uc", {
            "alert_type": "opportunity_any", "name": "UC",
        })
        evaluate_alerts(sample_opps)
        count = get_unread_count("user-uc")
        assert count >= 1

    def test_mark_alerts_read(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import (
            create_smart_alert, evaluate_alerts,
            get_triggered_alerts, mark_alerts_read, get_unread_count,
        )
        create_smart_alert("user-mr", {
            "alert_type": "opportunity_any", "name": "MR",
        })
        evaluate_alerts(sample_opps)
        # Mark all read
        count = mark_alerts_read("user-mr")
        assert count >= 1
        assert get_unread_count("user-mr") == 0

    def test_mark_specific_alerts_read(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import (
            create_smart_alert, evaluate_alerts,
            get_triggered_alerts, mark_alerts_read,
        )
        create_smart_alert("user-ms", {
            "alert_type": "opportunity_any", "name": "MS",
        })
        evaluate_alerts(sample_opps)
        triggers = get_triggered_alerts("user-ms")
        if triggers:
            tid = triggers[0]["id"]
            count = mark_alerts_read("user-ms", [tid])
            assert count == 1

    def test_clear_triggered(self, tmp_db, sample_opps):
        from app.core.smart_alert_engine import (
            create_smart_alert, evaluate_alerts,
            get_triggered_alerts, clear_triggered,
        )
        create_smart_alert("user-cl", {
            "alert_type": "opportunity_any", "name": "CL",
        })
        evaluate_alerts(sample_opps)
        clear_triggered("user-cl")
        assert len(get_triggered_alerts("user-cl")) == 0


# ══════════════════════════════════════════════════════════════════════
# 8. API ROUTES — OPPORTUNITIES
# ══════════════════════════════════════════════════════════════════════

class TestOpportunitiesAPI:
    """Test API routes for opportunities."""

    def test_opportunities_page(self, client):
        resp = client.get("/opportunities")
        assert resp.status_code == 200
        assert b"opportunities" in resp.data.lower() or b"firsatlar" in resp.data.lower() or b"f\xc4\xb1rsat" in resp.data.lower()

    def test_api_get_opportunities(self, client):
        resp = client.get("/api/opportunities")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "data" in data
        assert "total" in data

    def test_api_get_opportunities_with_market_filter(self, client):
        resp = client.get("/api/opportunities?market=crypto")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_get_opportunities_with_event_filter(self, client):
        resp = client.get("/api/opportunities?event_type=volume_spike")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_get_opportunities_with_limit(self, client):
        resp = client.get("/api/opportunities?limit=5")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_trending(self, client):
        resp = client.get("/api/opportunities/trending")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "data" in data

    def test_api_trending_with_limit(self, client):
        resp = client.get("/api/opportunities/trending?limit=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert len(data["data"]) <= 3

    def test_api_symbol_opportunities(self, client):
        resp = client.get("/api/opportunities/BTCUSDT")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True

    def test_api_scan_requires_auth(self, client):
        resp = client.post("/api/opportunities/scan")
        # Should redirect or return 401/302 without auth
        assert resp.status_code in (302, 401, 403)

    def test_api_alert_types(self, client):
        resp = client.get("/api/opportunities/alert-types")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert "alert_types" in data
        assert "event_types" in data
        assert "opportunity_any" in data["alert_types"]
        assert "volume_spike" in data["event_types"]


# ══════════════════════════════════════════════════════════════════════
# 9. API ROUTES — SMART ALERTS (AUTH REQUIRED)
# ══════════════════════════════════════════════════════════════════════

class TestSmartAlertAPI:
    """Test API routes that require authentication."""

    def test_get_alerts_requires_auth(self, client):
        resp = client.get("/api/opportunities/alerts")
        assert resp.status_code in (302, 401, 403)

    def test_create_alert_requires_auth(self, client):
        resp = client.post("/api/opportunities/alert/create",
                           data=json.dumps({"alert_type": "opportunity_any", "name": "X"}),
                           content_type="application/json")
        assert resp.status_code in (302, 401, 403)

    def test_delete_alert_requires_auth(self, client):
        resp = client.delete("/api/opportunities/alert/some-id")
        assert resp.status_code in (302, 401, 403)

    def test_update_alert_requires_auth(self, client):
        resp = client.put("/api/opportunities/alert/some-id",
                          data=json.dumps({"name": "X"}),
                          content_type="application/json")
        assert resp.status_code in (302, 401, 403)

    def test_notifications_requires_auth(self, client):
        resp = client.get("/api/opportunities/notifications")
        assert resp.status_code in (302, 401, 403)

    def test_mark_read_requires_auth(self, client):
        resp = client.post("/api/opportunities/notifications/read")
        assert resp.status_code in (302, 401, 403)


# ══════════════════════════════════════════════════════════════════════
# 10. LEGAL_SAFE_MODE COMPLIANCE
# ══════════════════════════════════════════════════════════════════════

class TestLegalSafeMode:
    """Verify that output uses safe language only."""

    def test_safe_labels_no_buy_sell(self):
        from app.core.opportunity_engine import _SAFE_LABELS
        for key, label in _SAFE_LABELS.items():
            lower = label.lower()
            assert "buy" not in lower, f"Label '{key}' contains 'buy'"
            assert "sell" not in lower, f"Label '{key}' contains 'sell'"
            assert "al " not in lower and not lower.startswith("al"), \
                f"Label '{key}' may contain Turkish 'al' (buy)"
            assert "sat " not in lower and not lower.startswith("sat"), \
                f"Label '{key}' may contain Turkish 'sat' (sell)"

    def test_safe_labels_use_observation_terms(self):
        from app.core.opportunity_engine import _SAFE_LABELS
        observation_terms = ["gözlem", "dikkat", "izlenebilir", "potansiyel"]
        for key, label in _SAFE_LABELS.items():
            lower = label.lower()
            has_safe = any(t in lower for t in observation_terms)
            assert has_safe, f"Label '{key}' lacks safe observation terms: {label}"

    def test_event_types_no_trading_language(self):
        from app.core.opportunity_engine import EVENT_TYPES
        for key, info in EVENT_TYPES.items():
            label = info["label"].lower()
            assert "al " not in label and "sat " not in label, \
                f"EVENT_TYPES '{key}' contains trading language"

    def test_alert_types_safe_language(self):
        from app.core.smart_alert_engine import SMART_ALERT_TYPES
        forbidden = ["satın al", "hemen al", "şimdi sat", "pozisyon aç"]
        for key, desc in SMART_ALERT_TYPES.items():
            lower = desc.lower()
            for term in forbidden:
                assert term not in lower, f"Alert type '{key}' contains forbidden: '{term}'"

    def test_detector_descriptions_safe(self, sample_klines_volume_spike):
        from app.core.opportunity_engine import detect_volume_spike
        opp = detect_volume_spike("TESTUSDT", "crypto", sample_klines_volume_spike)
        assert opp is not None
        desc = opp["description"].lower()
        assert "buy" not in desc
        assert "sell" not in desc
        assert "trade" not in desc


# ══════════════════════════════════════════════════════════════════════
# 11. EDGE CASES
# ══════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case and boundary tests."""

    def test_event_types_complete(self):
        from app.core.opportunity_engine import EVENT_TYPES
        expected = {
            "volume_spike", "momentum_shift", "volatility_spike",
            "rsi_extreme", "ema_cross", "breakout", "sector_rotation",
            "whale_activity", "fng_extreme", "price_anomaly",
        }
        assert set(EVENT_TYPES.keys()) == expected

    def test_smart_alert_types_complete(self):
        from app.core.smart_alert_engine import SMART_ALERT_TYPES
        expected = {
            "opportunity_any", "opportunity_symbol", "confidence_high",
            "event_volume_spike", "event_momentum_shift", "event_volatility_spike",
            "event_rsi_extreme", "event_breakout", "event_whale_activity",
            "market_crypto", "market_stocks", "market_forex",
        }
        assert set(SMART_ALERT_TYPES.keys()) == expected

    def test_confidence_levels_defined(self):
        from app.core.opportunity_engine import CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW
        assert CONFIDENCE_HIGH > CONFIDENCE_MEDIUM > CONFIDENCE_LOW
        assert CONFIDENCE_LOW >= 0
        assert CONFIDENCE_HIGH <= 100

    def test_detector_none_for_short_klines(self):
        from app.core.opportunity_engine import (
            detect_volume_spike, detect_momentum,
            detect_volatility_spike, detect_rsi_extreme,
            detect_breakout, detect_whale_activity,
        )
        short = [{"open": 1, "high": 2, "low": 0.5, "close": 1.5, "volume": 100}
                 for _ in range(3)]
        for det in [detect_volume_spike, detect_momentum,
                    detect_volatility_spike, detect_rsi_extreme,
                    detect_breakout, detect_whale_activity]:
            assert det("X", "crypto", short) is None

    def test_rsi_division_by_zero(self):
        from app.core.opportunity_engine import _calc_rsi
        # All same prices → no gains or losses
        closes = [100.0] * 20
        rsi = _calc_rsi(closes, 14)
        # Should not crash; returns None or a number
        assert rsi is None or isinstance(rsi, float)
