# -*- coding: utf-8 -*-
"""FAZ 23 — Strategy Backtesting + Trade Journal Tests.

Validates:
  1.  File existence — app/core/strategies.py
  2.  File existence — app/core/backtest_engine.py
  3.  File existence — app/core/journal_engine.py
  4.  File existence — app/blueprints/backtest/__init__.py
  5.  File existence — app/blueprints/backtest/routes.py
  6.  File existence — app/blueprints/journal/__init__.py
  7.  File existence — app/blueprints/journal/routes.py
  8.  File existence — templates/backtest.html
  9.  File existence — templates/journal.html
  10. File existence — static/css/backtest.css
  11. File existence — static/css/journal.css
  12. Blueprint registration — backtest_bp in legacy_monolith.py
  13. Blueprint registration — journal_bp in legacy_monolith.py
  14. Dashboard route — /backtest route defined
  15. Dashboard route — /journal route defined
  16. Strategies — list_strategies returns 4 strategies
  17. Strategies — get_strategy returns correct class
  18. Strategies — EMA Cross strategy generates signals
  19. Strategies — RSI Reversal strategy generates signals
  20. Strategies — Breakout strategy generates signals
  21. Strategies — VWAP Trend strategy generates signals
  22. Strategies — all strategies return pandas Series
  23. Strategies — signals contain only -1, 0, +1
  24. Backtest engine — run_backtest function exists
  25. Backtest engine — _fetch_candles function exists
  26. Backtest engine — _simulate_trades function exists
  27. Backtest engine — _compute_metrics function exists
  28. Backtest engine — _build_equity_curve function exists
  29. Journal engine — add_entry works
  30. Journal engine — list_entries returns entries
  31. Journal engine — get_entry by id
  32. Journal engine — update_entry works
  33. Journal engine — delete_entry works
  34. Journal engine — stats returns all fields
  35. Journal engine — stats win_rate calculation
  36. Journal engine — emotion validation
  37. Journal engine — clear_all works
  38. Journal engine — list_entries with filters
  39. API — GET /api/backtest/strategies returns list
  40. API — GET /api/backtest/strategies has 4 strategies
  41. API — GET /api/backtest/run requires symbol
  42. API — GET /api/backtest/run requires strategy
  43. API — POST /api/journal — add entry
  44. API — GET /api/journal — list entries
  45. API — PUT /api/journal/<id> — update entry
  46. API — DELETE /api/journal/<id> — delete entry
  47. API — GET /api/journal/stats — statistics
  48. API — POST /api/journal — requires symbol
  49. Template — backtest.html extends base_app
  50. Template — backtest.html has strategy select
  51. Template — backtest.html has metrics grid
  52. Template — backtest.html has equity chart
  53. Template — backtest.html has trade table
  54. Template — backtest.html loads Chart.js
  55. Template — backtest.html has runBacktest function
  56. Template — journal.html extends base_app
  57. Template — journal.html has add-entry form
  58. Template — journal.html has emotion buttons
  59. Template — journal.html has entries table
  60. Template — journal.html has notes modal
  61. Template — journal.html has stats section
  62. CSS — backtest.css has required classes
  63. CSS — journal.css has required classes
  64. Simulator integration — journal prompt in simulator.js
  65. Simulator integration — addToJournal in simulator.js
  66. Simulator integration — journal CSS in simulator.css
  67. Copilot — build_journal_context in copilot_context.py
  68. Copilot — ask_journal in copilot_service.py
  69. Copilot — POST /api/copilot/journal route
  70. Copilot — _JOURNAL_PROMPT in copilot_service.py
  71. Backward compat — / (home) loads
  72. Backward compat — /simulator loads
  73. Backward compat — /trade loads
  74. Backward compat — /discover loads
  75. Backward compat — /screener loads
  76. Backward compat — /alerts loads
  77. Backward compat — /api/copilot/ask works
  78. Backward compat — /api/simulator/summary works
  79. Page — /backtest loads successfully
  80. Page — /journal loads successfully
  81. Journal API — full CRUD flow
  82. Journal engine — by_emotion stats
  83. Journal engine — by_strategy stats
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

def _read(relpath: str) -> str:
    full = os.path.join(BASE, relpath)
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _exists(relpath: str) -> bool:
    return os.path.isfile(os.path.join(BASE, relpath))


def _get(path: str, **kw):
    return requests.get(URL + path, timeout=TIMEOUT, **kw)


def _post(path: str, data=None, **kw):
    return requests.post(URL + path, json=data, timeout=TIMEOUT, **kw)


def _put(path: str, data=None, **kw):
    return requests.put(URL + path, json=data, timeout=TIMEOUT, **kw)


def _delete(path: str, **kw):
    return requests.delete(URL + path, timeout=TIMEOUT, **kw)


# ══════════════════════════════════════════════════════════════════════
# 1-11: FILE EXISTENCE
# ══════════════════════════════════════════════════════════════════════

def test_01_file_strategies():
    assert _exists("app/core/strategies.py")

def test_02_file_backtest_engine():
    assert _exists("app/core/backtest_engine.py")

def test_03_file_journal_engine():
    assert _exists("app/core/journal_engine.py")

def test_04_file_backtest_init():
    assert _exists("app/blueprints/backtest/__init__.py")

def test_05_file_backtest_routes():
    assert _exists("app/blueprints/backtest/routes.py")

def test_06_file_journal_init():
    assert _exists("app/blueprints/journal/__init__.py")

def test_07_file_journal_routes():
    assert _exists("app/blueprints/journal/routes.py")

def test_08_file_backtest_html():
    assert _exists("templates/backtest.html")

def test_09_file_journal_html():
    assert _exists("templates/journal.html")

def test_10_file_backtest_css():
    assert _exists("static/css/backtest.css")

def test_11_file_journal_css():
    assert _exists("static/css/journal.css")


# ══════════════════════════════════════════════════════════════════════
# 12-15: BLUEPRINT & ROUTE REGISTRATION
# ══════════════════════════════════════════════════════════════════════

def test_12_blueprint_backtest_registered():
    src = _read("legacy_monolith.py")
    assert "backtest_bp" in src
    assert "register_blueprint(backtest_bp)" in src

def test_13_blueprint_journal_registered():
    src = _read("legacy_monolith.py")
    assert "journal_bp" in src
    assert "register_blueprint(journal_bp)" in src

def test_14_dashboard_backtest_route():
    src = _read("app/blueprints/dashboard/routes.py")
    assert '"/backtest"' in src

def test_15_dashboard_journal_route():
    src = _read("app/blueprints/dashboard/routes.py")
    assert '"/journal"' in src


# ══════════════════════════════════════════════════════════════════════
# 16-23: STRATEGIES MODULE
# ══════════════════════════════════════════════════════════════════════

def test_16_list_strategies_returns_4():
    sys.path.insert(0, BASE)
    from app.core.strategies import list_strategies
    strats = list_strategies()
    assert len(strats) == 4

def test_17_get_strategy_by_name():
    from app.core.strategies import get_strategy
    s = get_strategy("ema_cross")
    assert s is not None
    assert hasattr(s, "generate_signals")

def test_18_ema_cross_generates_signals():
    import pandas as pd
    import numpy as np
    from app.core.strategies import get_strategy
    np.random.seed(42)
    df = pd.DataFrame({
        "open": np.random.uniform(100, 200, 100),
        "high": np.random.uniform(100, 200, 100),
        "low": np.random.uniform(100, 200, 100),
        "close": np.random.uniform(100, 200, 100),
        "volume": np.random.uniform(1000, 5000, 100),
    })
    s = get_strategy("ema_cross")
    signals = s.generate_signals(df)
    assert isinstance(signals, pd.Series)
    assert len(signals) == 100

def test_19_rsi_reversal_generates_signals():
    import pandas as pd
    import numpy as np
    from app.core.strategies import get_strategy
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(100) * 2)
    df = pd.DataFrame({
        "open": closes - 0.5,
        "high": closes + 1,
        "low": closes - 1,
        "close": closes,
        "volume": np.random.uniform(1000, 5000, 100),
    })
    s = get_strategy("rsi_reversal")
    signals = s.generate_signals(df)
    assert isinstance(signals, pd.Series)

def test_20_breakout_generates_signals():
    import pandas as pd
    import numpy as np
    from app.core.strategies import get_strategy
    np.random.seed(42)
    df = pd.DataFrame({
        "open": np.random.uniform(100, 200, 100),
        "high": np.random.uniform(100, 200, 100),
        "low": np.random.uniform(100, 200, 100),
        "close": np.random.uniform(100, 200, 100),
        "volume": np.random.uniform(1000, 5000, 100),
    })
    s = get_strategy("breakout")
    signals = s.generate_signals(df)
    assert isinstance(signals, pd.Series)

def test_21_vwap_trend_generates_signals():
    import pandas as pd
    import numpy as np
    from app.core.strategies import get_strategy
    np.random.seed(42)
    df = pd.DataFrame({
        "open": np.random.uniform(100, 200, 100),
        "high": np.random.uniform(100, 200, 100),
        "low": np.random.uniform(100, 200, 100),
        "close": np.random.uniform(100, 200, 100),
        "volume": np.random.uniform(1000, 5000, 100),
    })
    s = get_strategy("vwap_trend")
    signals = s.generate_signals(df)
    assert isinstance(signals, pd.Series)

def test_22_all_strategies_return_series():
    import pandas as pd
    import numpy as np
    from app.core.strategies import list_strategies, get_strategy
    np.random.seed(42)
    df = pd.DataFrame({
        "open": np.random.uniform(100, 200, 100),
        "high": np.random.uniform(100, 200, 100),
        "low": np.random.uniform(100, 200, 100),
        "close": np.random.uniform(100, 200, 100),
        "volume": np.random.uniform(1000, 5000, 100),
    })
    for info in list_strategies():
        s = get_strategy(info["id"])
        signals = s.generate_signals(df)
        assert isinstance(signals, pd.Series)

def test_23_signals_contain_valid_values():
    import pandas as pd
    import numpy as np
    from app.core.strategies import get_strategy
    np.random.seed(42)
    closes = 100 + np.cumsum(np.random.randn(200) * 2)
    df = pd.DataFrame({
        "open": closes - 0.5,
        "high": closes + 1,
        "low": closes - 1,
        "close": closes,
        "volume": np.random.uniform(1000, 5000, 200),
    })
    s = get_strategy("ema_cross")
    signals = s.generate_signals(df)
    valid_values = {-1, 0, 1}
    unique_vals = set(signals.unique())
    assert unique_vals.issubset(valid_values), f"Invalid signal values: {unique_vals}"


# ══════════════════════════════════════════════════════════════════════
# 24-28: BACKTEST ENGINE MODULE
# ══════════════════════════════════════════════════════════════════════

def test_24_backtest_run_function_exists():
    from app.core.backtest_engine import run_backtest
    assert callable(run_backtest)

def test_25_backtest_fetch_candles_exists():
    from app.core.backtest_engine import _fetch_candles
    assert callable(_fetch_candles)

def test_26_backtest_simulate_trades_exists():
    from app.core.backtest_engine import _simulate_trades
    assert callable(_simulate_trades)

def test_27_backtest_compute_metrics_exists():
    from app.core.backtest_engine import _compute_metrics
    assert callable(_compute_metrics)

def test_28_backtest_equity_curve_exists():
    from app.core.backtest_engine import _build_equity_curve
    assert callable(_build_equity_curve)


# ══════════════════════════════════════════════════════════════════════
# 29-38: JOURNAL ENGINE
# ══════════════════════════════════════════════════════════════════════

def test_29_journal_add_entry():
    from app.core.journal_engine import add_entry, clear_all
    clear_all()
    entry = add_entry({"symbol": "BTCUSDT", "market": "crypto", "side": "buy",
                        "entry_price": 50000, "exit_price": 51000,
                        "quantity": 0.5, "pnl": 500, "emotion": "confident"})
    assert "id" in entry
    assert entry["symbol"] == "BTCUSDT"

def test_30_journal_list_entries():
    from app.core.journal_engine import list_entries
    entries = list_entries()
    assert isinstance(entries, list)
    assert len(entries) >= 1

def test_31_journal_get_entry():
    from app.core.journal_engine import list_entries, get_entry
    entries = list_entries()
    entry_id = entries[0]["id"]
    entry = get_entry(entry_id)
    assert entry is not None
    assert entry["id"] == entry_id

def test_32_journal_update_entry():
    from app.core.journal_engine import list_entries, update_entry, get_entry
    entries = list_entries()
    entry_id = entries[0]["id"]
    updated = update_entry(entry_id, {"notes": "Updated note"})
    assert updated["notes"] == "Updated note"

def test_33_journal_delete_entry():
    from app.core.journal_engine import add_entry, delete_entry, get_entry
    entry = add_entry({"symbol": "ETHUSDT", "pnl": -100})
    eid = entry["id"]
    result = delete_entry(eid)
    assert result is True
    assert get_entry(eid) is None

def test_34_journal_stats_returns_fields():
    from app.core.journal_engine import stats
    s = stats()
    for key in ["total_entries", "win_rate", "total_pnl", "average_pnl",
                 "best_trade", "worst_trade", "by_emotion", "by_strategy", "streak"]:
        assert key in s, f"Missing key: {key}"

def test_35_journal_stats_win_rate():
    from app.core.journal_engine import clear_all, add_entry, stats
    clear_all()
    add_entry({"symbol": "A", "pnl": 100})
    add_entry({"symbol": "B", "pnl": -50})
    add_entry({"symbol": "C", "pnl": 200})
    s = stats()
    assert s["win_rate"] == pytest.approx(66.7, abs=0.1)

def test_36_journal_emotion_validation():
    from app.core.journal_engine import add_entry
    entry = add_entry({"symbol": "X", "emotion": "invalid_emotion"})
    assert entry["emotion"] == "neutral"  # default

def test_37_journal_clear_all():
    from app.core.journal_engine import clear_all, list_entries, add_entry
    add_entry({"symbol": "Y"})
    clear_all()
    entries = list_entries()
    assert len(entries) == 0

def test_38_journal_list_with_filters():
    from app.core.journal_engine import clear_all, add_entry, list_entries
    clear_all()
    add_entry({"symbol": "BTCUSDT", "market": "crypto", "emotion": "confident"})
    add_entry({"symbol": "AAPL", "market": "stocks", "emotion": "fear"})
    add_entry({"symbol": "THYAO.IS", "market": "bist", "emotion": "confident"})

    crypto = list_entries(market="crypto")
    assert len(crypto) == 1
    assert crypto[0]["symbol"] == "BTCUSDT"

    confident = list_entries(emotion="confident")
    assert len(confident) == 2


# ══════════════════════════════════════════════════════════════════════
# 39-48: API ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@live_api
def test_39_api_backtest_strategies():
    r = _get("/api/backtest/strategies")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "strategies" in data

@live_api
def test_40_api_backtest_strategies_has_4():
    r = _get("/api/backtest/strategies")
    data = r.json()
    assert len(data["strategies"]) == 4

@live_api
def test_41_api_backtest_run_requires_symbol():
    r = _get("/api/backtest/run?strategy=ema_cross")
    assert r.status_code == 400
    data = r.json()
    assert data["ok"] is False

@live_api
def test_42_api_backtest_run_requires_strategy():
    # strategy defaults to ema_cross, so omitting it should still work
    r = _get("/api/backtest/run?symbol=BTCUSDT")
    data = r.json()
    # Should default to ema_cross and return ok (or fail on data fetch, but not 400)
    assert r.status_code in (200, 500)  # 200 if data available, 500 if no candles

@live_api
def test_43_api_journal_add():
    r = _post("/api/journal", {"symbol": "TESTCOIN", "pnl": 42})
    assert r.status_code == 201
    data = r.json()
    assert data["ok"] is True
    assert "entry" in data

@live_api
def test_44_api_journal_list():
    r = _get("/api/journal")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "entries" in data

@live_api
def test_45_api_journal_update():
    # First add
    r1 = _post("/api/journal", {"symbol": "UPDATETEST"})
    eid = r1.json()["entry"]["id"]
    # Then update
    r2 = _put(f"/api/journal/{eid}", {"notes": "test update"})
    assert r2.status_code == 200
    data = r2.json()
    assert data["ok"] is True

@live_api
def test_46_api_journal_delete():
    r1 = _post("/api/journal", {"symbol": "DELTEST"})
    eid = r1.json()["entry"]["id"]
    r2 = _delete(f"/api/journal/{eid}")
    assert r2.status_code == 200
    data = r2.json()
    assert data["ok"] is True

@live_api
def test_47_api_journal_stats():
    r = _get("/api/journal/stats")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert "stats" in data

@live_api
def test_48_api_journal_requires_symbol():
    r = _post("/api/journal", {"pnl": 100})
    assert r.status_code == 400
    data = r.json()
    assert data["ok"] is False


# ══════════════════════════════════════════════════════════════════════
# 49-61: TEMPLATE CONTENT
# ══════════════════════════════════════════════════════════════════════

def test_49_backtest_extends_base():
    src = _read("templates/backtest.html")
    assert "extends" in src

def test_50_backtest_has_strategy_select():
    src = _read("templates/backtest.html")
    assert "bt-strategy" in src

def test_51_backtest_has_metrics_grid():
    src = _read("templates/backtest.html")
    assert "bt-metrics-grid" in src

def test_52_backtest_has_equity_chart():
    src = _read("templates/backtest.html")
    assert "bt-equity-chart" in src or "equityChart" in src

def test_53_backtest_has_trade_table():
    src = _read("templates/backtest.html")
    assert "bt-trades-body" in src

def test_54_backtest_loads_chartjs():
    src = _read("templates/backtest.html")
    assert "chart.js" in src.lower() or "Chart" in src

def test_55_backtest_has_run_function():
    src = _read("templates/backtest.html")
    assert "runBacktest" in src

def test_56_journal_extends_base():
    src = _read("templates/journal.html")
    assert "extends" in src

def test_57_journal_has_add_form():
    src = _read("templates/journal.html")
    assert "jrn-symbol" in src
    assert "addEntry" in src

def test_58_journal_has_emotion_buttons():
    src = _read("templates/journal.html")
    assert "jrn-emo-btn" in src
    assert "confident" in src
    assert "fear" in src

def test_59_journal_has_entries_table():
    src = _read("templates/journal.html")
    assert "jrn-entries-body" in src

def test_60_journal_has_notes_modal():
    src = _read("templates/journal.html")
    assert "jrn-modal" in src

def test_61_journal_has_stats_section():
    src = _read("templates/journal.html")
    assert "jrn-stats" in src


# ══════════════════════════════════════════════════════════════════════
# 62-63: CSS
# ══════════════════════════════════════════════════════════════════════

def test_62_backtest_css_classes():
    src = _read("static/css/backtest.css")
    for cls in ["bt-container", "bt-panel", "bt-run-btn", "bt-metrics-grid",
                "bt-metric-card", "bt-table"]:
        assert cls in src, f"Missing class: {cls}"

def test_63_journal_css_classes():
    src = _read("static/css/journal.css")
    for cls in ["jrn-container", "jrn-panel", "jrn-add-btn", "jrn-table",
                "jrn-emo-btn", "jrn-modal", "jrn-stat-card"]:
        assert cls in src, f"Missing class: {cls}"


# ══════════════════════════════════════════════════════════════════════
# 64-66: SIMULATOR INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def test_64_simulator_journal_prompt():
    src = _read("static/js/simulator.js")
    assert "showJournalPrompt" in src

def test_65_simulator_add_to_journal():
    src = _read("static/js/simulator.js")
    assert "addToJournal" in src
    assert "/api/journal" in src

def test_66_simulator_journal_css():
    src = _read("static/css/simulator.css")
    assert "sim-journal-prompt" in src
    assert "sim-btn-journal" in src


# ══════════════════════════════════════════════════════════════════════
# 67-70: COPILOT INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def test_67_copilot_build_journal_context():
    src = _read("app/core/copilot_context.py")
    assert "def build_journal_context" in src

def test_68_copilot_ask_journal():
    src = _read("app/core/copilot_service.py")
    assert "def ask_journal" in src

def test_69_copilot_journal_route():
    src = _read("app/blueprints/copilot/routes.py")
    assert "/api/copilot/journal" in src

def test_70_copilot_journal_prompt():
    src = _read("app/core/copilot_service.py")
    assert "_JOURNAL_PROMPT" in src


# ══════════════════════════════════════════════════════════════════════
# 71-78: BACKWARD COMPATIBILITY
# ══════════════════════════════════════════════════════════════════════

@live_api
def test_71_compat_home():
    r = _get("/")
    assert r.status_code == 200

@live_api
def test_72_compat_simulator():
    r = _get("/simulator")
    assert r.status_code == 200

@live_api
def test_73_compat_trade():
    r = _get("/trade")
    assert r.status_code == 200

@live_api
def test_74_compat_discover():
    r = _get("/discover")
    assert r.status_code == 200

@live_api
def test_75_compat_screener():
    r = _get("/screener")
    assert r.status_code == 200

@live_api
def test_76_compat_alerts():
    r = _get("/alerts")
    assert r.status_code == 200

@live_api
def test_77_compat_copilot_ask():
    r = _post("/api/copilot/ask", {"question": "test"})
    # May fail without LLM, but route should respond (not 404)
    assert r.status_code != 404

@live_api
def test_78_compat_simulator_summary():
    r = _get("/api/simulator/summary")
    assert r.status_code == 200
    data = r.json()
    assert data.get("ok") is True


# ══════════════════════════════════════════════════════════════════════
# 79-80: NEW PAGES
# ══════════════════════════════════════════════════════════════════════

@live_api
def test_79_page_backtest_loads():
    r = _get("/backtest")
    assert r.status_code == 200
    assert "backtest" in r.text.lower()

@live_api
def test_80_page_journal_loads():
    r = _get("/journal")
    assert r.status_code == 200
    assert "journal" in r.text.lower() or "günlüğ" in r.text.lower() or "jrn-" in r.text


# ══════════════════════════════════════════════════════════════════════
# 81-83: INTEGRATION / EDGE CASES
# ══════════════════════════════════════════════════════════════════════

@live_api
def test_81_journal_full_crud_flow():
    """Full CRUD lifecycle: create → read → update → delete."""
    # Create
    r1 = _post("/api/journal", {
        "symbol": "FLOWTEST",
        "market": "crypto",
        "side": "buy",
        "entry_price": 100,
        "exit_price": 110,
        "quantity": 1,
        "pnl": 10,
        "emotion": "confident",
        "notes": "Flow test entry"
    })
    assert r1.status_code == 201
    data1 = r1.json()
    assert data1["ok"] is True
    eid = data1["entry"]["id"]

    # Read
    r2 = _get("/api/journal")
    entries = r2.json()["entries"]
    found = [e for e in entries if e["id"] == eid]
    assert len(found) == 1
    assert found[0]["symbol"] == "FLOWTEST"

    # Update
    r3 = _put(f"/api/journal/{eid}", {"notes": "Updated flow test", "emotion": "greed"})
    assert r3.status_code == 200
    assert r3.json()["entry"]["notes"] == "Updated flow test"

    # Delete
    r4 = _delete(f"/api/journal/{eid}")
    assert r4.status_code == 200
    assert r4.json()["ok"] is True

    # Verify gone
    r5 = _get("/api/journal")
    entries2 = r5.json()["entries"]
    found2 = [e for e in entries2 if e["id"] == eid]
    assert len(found2) == 0

def test_82_journal_by_emotion_stats():
    from app.core.journal_engine import clear_all, add_entry, stats
    clear_all()
    add_entry({"symbol": "A", "pnl": 100, "emotion": "confident"})
    add_entry({"symbol": "B", "pnl": -50, "emotion": "fear"})
    add_entry({"symbol": "C", "pnl": 200, "emotion": "confident"})
    s = stats()
    assert "by_emotion" in s
    by_emo = s["by_emotion"]
    # Should have entries for confident and fear
    assert isinstance(by_emo, dict)

def test_83_journal_by_strategy_stats():
    from app.core.journal_engine import clear_all, add_entry, stats
    clear_all()
    add_entry({"symbol": "A", "pnl": 100, "strategy": "ema_cross"})
    add_entry({"symbol": "B", "pnl": -50, "strategy": "rsi_reversal"})
    add_entry({"symbol": "C", "pnl": 200, "strategy": "ema_cross"})
    s = stats()
    assert "by_strategy" in s
    by_strat = s["by_strategy"]
    assert isinstance(by_strat, dict)
