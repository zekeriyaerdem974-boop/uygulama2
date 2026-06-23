# -*- coding: utf-8 -*-
"""FAZ 20 — Alert/Alarm System Tests.

Validates:
  1. File existence (engine, blueprint, routes, HTML, CSS, JS)
  2. Alert engine CRUD (create, get, delete, list)
  3. Alert engine validation & edge cases
  4. Alert engine RSI calculation
  5. Alert engine trigger mechanism
  6. Blueprint registration & API endpoints
  7. Template structure (HTML elements, form, tables, toast)
  8. CSS classes & responsive design
  9. JavaScript module structure
  10. Trade page integration (alert icon, trade_alerts.js)
  11. Background job registration
  12. Backward compatibility (existing routes still work)
"""
from __future__ import annotations

import os
import re
import json
import pytest
import requests

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "http://127.0.0.1:34000"
TIMEOUT = 12


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


def _delete(path: str, **kw) -> requests.Response:
    return requests.delete(URL + path, timeout=TIMEOUT, **kw)


# ═══════════════════════════════════════════════════════════════════
# 1) FILE EXISTENCE
# ═══════════════════════════════════════════════════════════════════
class TestFileExistence:
    def test_alert_engine_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/core/alert_engine.py"))

    def test_alerts_blueprint_init(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/alerts/__init__.py"))

    def test_alerts_routes_exists(self):
        assert os.path.isfile(os.path.join(BASE, "app/blueprints/alerts/routes.py"))

    def test_alerts_html_exists(self):
        assert os.path.isfile(os.path.join(BASE, "templates/alerts.html"))

    def test_alerts_css_exists(self):
        assert os.path.isfile(os.path.join(BASE, "static/css/alerts.css"))

    def test_alerts_js_exists(self):
        assert os.path.isfile(os.path.join(BASE, "static/js/alerts.js"))

    def test_trade_alerts_js_exists(self):
        assert os.path.isfile(os.path.join(BASE, "static/js/trade_alerts.js"))


# ═══════════════════════════════════════════════════════════════════
# 2) ALERT ENGINE — CRUD
# ═══════════════════════════════════════════════════════════════════
class TestAlertEngineCRUD:
    """Test the alert engine module directly (import-level tests)."""

    def _engine(self):
        import importlib
        import app.core.alert_engine as ae
        return ae

    def test_create_alert_basic(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({
            "symbol": "BTCUSDT",
            "condition_type": "price_above",
            "condition_value": 70000
        })
        assert alert["symbol"] == "BTCUSDT"
        assert alert["condition_type"] == "price_above"
        assert alert["condition_value"] == 70000.0
        assert alert["active"] is True
        assert alert["id"] is not None
        ae._alerts.clear()

    def test_create_alert_with_market(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({
            "symbol": "THYAO",
            "market": "bist",
            "condition_type": "price_below",
            "condition_value": 100
        })
        assert alert["market"] == "bist"
        assert alert["symbol"] == "THYAO"
        ae._alerts.clear()

    def test_create_alert_defaults_crypto(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({
            "symbol": "ETHUSDT",
            "condition_type": "rsi_above",
            "condition_value": 70
        })
        assert alert["market"] == "crypto"
        ae._alerts.clear()

    def test_get_alerts_empty(self):
        ae = self._engine()
        ae._alerts.clear()
        result = ae.get_alerts()
        assert result == []

    def test_get_alerts_returns_list(self):
        ae = self._engine()
        ae._alerts.clear()
        ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": 50000})
        ae.create_alert({"symbol": "ETH", "condition_type": "price_below", "condition_value": 3000})
        result = ae.get_alerts()
        assert len(result) == 2
        ae._alerts.clear()

    def test_get_alert_by_id(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "SOL", "condition_type": "price_above", "condition_value": 200})
        found = ae.get_alert(alert["id"])
        assert found is not None
        assert found["symbol"] == "SOL"
        ae._alerts.clear()

    def test_get_alert_not_found(self):
        ae = self._engine()
        ae._alerts.clear()
        result = ae.get_alert("nonexistent")
        assert result is None

    def test_delete_alert(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": 50000})
        assert ae.delete_alert(alert["id"]) is True
        assert ae.get_alert(alert["id"]) is None
        ae._alerts.clear()

    def test_delete_nonexistent(self):
        ae = self._engine()
        ae._alerts.clear()
        assert ae.delete_alert("nope") is False

    def test_alert_has_required_fields(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({
            "symbol": "XRPUSDT",
            "condition_type": "volume_spike",
            "condition_value": 2.5
        })
        for field in ["id", "symbol", "market", "condition_type", "condition_value",
                       "created_at", "active", "triggered_at", "trigger_price"]:
            assert field in alert, f"Missing field: {field}"
        ae._alerts.clear()

    def test_alert_id_is_string(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": 100})
        assert isinstance(alert["id"], str)
        ae._alerts.clear()


# ═══════════════════════════════════════════════════════════════════
# 3) ALERT ENGINE — VALIDATION
# ═══════════════════════════════════════════════════════════════════
class TestAlertEngineValidation:

    def _engine(self):
        import app.core.alert_engine as ae
        return ae

    def test_missing_symbol_raises(self):
        ae = self._engine()
        with pytest.raises(ValueError, match="symbol"):
            ae.create_alert({"condition_type": "price_above", "condition_value": 100})

    def test_empty_symbol_raises(self):
        ae = self._engine()
        with pytest.raises(ValueError, match="symbol"):
            ae.create_alert({"symbol": "", "condition_type": "price_above", "condition_value": 100})

    def test_invalid_condition_type_raises(self):
        ae = self._engine()
        with pytest.raises(ValueError, match="Invalid condition_type"):
            ae.create_alert({"symbol": "BTC", "condition_type": "bad_type", "condition_value": 100})

    def test_non_numeric_value_raises(self):
        ae = self._engine()
        with pytest.raises(ValueError, match="number"):
            ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": "abc"})

    def test_none_value_raises(self):
        ae = self._engine()
        with pytest.raises(ValueError, match="number"):
            ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": None})

    def test_symbol_uppercased(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "btcusdt", "condition_type": "price_above", "condition_value": 100})
        assert alert["symbol"] == "BTCUSDT"
        ae._alerts.clear()

    def test_condition_value_converted_to_float(self):
        ae = self._engine()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": "70000"})
        assert alert["condition_value"] == 70000.0
        assert isinstance(alert["condition_value"], float)
        ae._alerts.clear()

    def test_all_condition_types_accepted(self):
        ae = self._engine()
        ae._alerts.clear()
        for ct in ae.CONDITION_TYPES:
            alert = ae.create_alert({"symbol": "TEST", "condition_type": ct, "condition_value": 1})
            assert alert["condition_type"] == ct
        ae._alerts.clear()


# ═══════════════════════════════════════════════════════════════════
# 4) ALERT ENGINE — RSI CALCULATION
# ═══════════════════════════════════════════════════════════════════
class TestAlertEngineRSI:

    def _engine(self):
        import app.core.alert_engine as ae
        return ae

    def test_rsi_all_gains(self):
        ae = self._engine()
        closes = list(range(100, 120))  # 20 increasing
        rsi = ae._calc_rsi(closes, 14)
        assert rsi == 100.0

    def test_rsi_all_losses(self):
        ae = self._engine()
        closes = list(range(120, 100, -1))  # 20 decreasing
        rsi = ae._calc_rsi(closes, 14)
        assert rsi == 0.0

    def test_rsi_neutral_fallback(self):
        ae = self._engine()
        rsi = ae._calc_rsi([100, 101, 102], 14)  # too few
        assert rsi == 50.0

    def test_rsi_returns_float(self):
        ae = self._engine()
        closes = [44, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84,
                  46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41,
                  46.22, 45.64]
        rsi = ae._calc_rsi(closes, 14)
        assert isinstance(rsi, float)
        assert 0 <= rsi <= 100

    def test_rsi_range_valid(self):
        ae = self._engine()
        closes = [100 + i * (-1)**i for i in range(30)]
        rsi = ae._calc_rsi(closes, 14)
        assert 0 <= rsi <= 100


# ═══════════════════════════════════════════════════════════════════
# 5) ALERT ENGINE — TRIGGER
# ═══════════════════════════════════════════════════════════════════
class TestAlertEngineTrigger:

    def _engine(self):
        import app.core.alert_engine as ae
        return ae

    def test_trigger_marks_inactive(self):
        ae = self._engine()
        ae._alerts.clear()
        ae._triggered.clear()
        alert = ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": 100})
        ae._trigger_alert(alert, 105.0)
        assert alert["active"] is False
        assert alert["trigger_price"] == 105.0
        assert alert["triggered_at"] is not None
        ae._alerts.clear()
        ae._triggered.clear()

    def test_trigger_adds_to_triggered_list(self):
        ae = self._engine()
        ae._alerts.clear()
        ae._triggered.clear()
        alert = ae.create_alert({"symbol": "ETH", "condition_type": "price_below", "condition_value": 3000})
        ae._trigger_alert(alert, 2900.0)
        triggered = ae.get_triggered()
        assert len(triggered) >= 1
        assert triggered[0]["symbol"] == "ETH"
        ae._alerts.clear()
        ae._triggered.clear()

    def test_triggered_max_cap(self):
        ae = self._engine()
        ae._alerts.clear()
        ae._triggered.clear()
        for i in range(55):
            alert = ae.create_alert({"symbol": f"T{i}", "condition_type": "price_above", "condition_value": i})
            ae._trigger_alert(alert, float(i))
        assert len(ae._triggered) <= ae._MAX_TRIGGERED
        ae._alerts.clear()
        ae._triggered.clear()

    def test_clear_triggered(self):
        ae = self._engine()
        ae._triggered.clear()
        ae._alerts.clear()
        alert = ae.create_alert({"symbol": "BTC", "condition_type": "price_above", "condition_value": 100})
        ae._trigger_alert(alert, 105.0)
        assert len(ae.get_triggered()) > 0
        ae.clear_triggered()
        assert len(ae.get_triggered()) == 0
        ae._alerts.clear()

    def test_get_triggered_returns_copy(self):
        ae = self._engine()
        ae._triggered.clear()
        result = ae.get_triggered()
        assert isinstance(result, list)
        ae._triggered.clear()


# ═══════════════════════════════════════════════════════════════════
# 6) ALERT ENGINE — CONDITION TYPES SET
# ═══════════════════════════════════════════════════════════════════
class TestConditionTypes:

    def _engine(self):
        import app.core.alert_engine as ae
        return ae

    def test_seven_condition_types(self):
        ae = self._engine()
        assert len(ae.CONDITION_TYPES) == 7

    def test_price_above_in_types(self):
        ae = self._engine()
        assert "price_above" in ae.CONDITION_TYPES

    def test_price_below_in_types(self):
        ae = self._engine()
        assert "price_below" in ae.CONDITION_TYPES

    def test_rsi_above_in_types(self):
        ae = self._engine()
        assert "rsi_above" in ae.CONDITION_TYPES

    def test_rsi_below_in_types(self):
        ae = self._engine()
        assert "rsi_below" in ae.CONDITION_TYPES

    def test_ema_cross_in_types(self):
        ae = self._engine()
        assert "ema_cross" in ae.CONDITION_TYPES

    def test_breakout_in_types(self):
        ae = self._engine()
        assert "breakout" in ae.CONDITION_TYPES

    def test_volume_spike_in_types(self):
        ae = self._engine()
        assert "volume_spike" in ae.CONDITION_TYPES


# ═══════════════════════════════════════════════════════════════════
# 7) API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════
class TestAlertAPI:

    def test_get_alerts_endpoint(self):
        r = _get("/api/alerts")
        assert r.status_code == 200
        data = r.json()
        assert "alerts" in data

    def test_get_alert_types(self):
        r = _get("/api/alerts/types")
        assert r.status_code == 200
        data = r.json()
        assert "types" in data
        assert len(data["types"]) == 7

    def test_create_alert_api(self):
        r = _post("/api/alerts", {
            "symbol": "TESTBTC",
            "condition_type": "price_above",
            "condition_value": 99999
        })
        assert r.status_code == 201
        data = r.json()
        assert data.get("ok") is True
        assert "alert" in data
        assert data["alert"]["symbol"] == "TESTBTC"
        # cleanup
        alert_id = data["alert"]["id"]
        _delete(f"/api/alerts/{alert_id}")

    def test_create_alert_missing_symbol(self):
        r = _post("/api/alerts", {
            "condition_type": "price_above",
            "condition_value": 100
        })
        assert r.status_code == 400

    def test_create_alert_invalid_condition(self):
        r = _post("/api/alerts", {
            "symbol": "BTC",
            "condition_type": "invalid_type",
            "condition_value": 100
        })
        assert r.status_code == 400

    def test_create_alert_missing_value(self):
        r = _post("/api/alerts", {
            "symbol": "BTC",
            "condition_type": "price_above"
        })
        assert r.status_code == 400

    def test_delete_alert_api(self):
        # create first
        r = _post("/api/alerts", {
            "symbol": "DELTEST",
            "condition_type": "price_below",
            "condition_value": 100
        })
        alert_id = r.json()["alert"]["id"]
        # then delete
        r2 = _delete(f"/api/alerts/{alert_id}")
        assert r2.status_code == 200

    def test_delete_nonexistent_alert(self):
        r = _delete("/api/alerts/nonexistent_id_12345")
        assert r.status_code == 404

    def test_get_triggered_endpoint(self):
        r = _get("/api/alerts/triggered")
        assert r.status_code == 200
        data = r.json()
        assert "triggered" in data

    def test_clear_triggered_endpoint(self):
        r = _post("/api/alerts/clear")
        assert r.status_code == 200

    def test_create_alert_returns_json(self):
        r = _post("/api/alerts", {
            "symbol": "JSONTEST",
            "condition_type": "rsi_above",
            "condition_value": 70
        })
        assert r.headers.get("Content-Type", "").startswith("application/json")
        data = r.json()
        assert data["alert"]["condition_type"] == "rsi_above"
        _delete(f"/api/alerts/{data['alert']['id']}")

    def test_create_alert_no_json_body(self):
        r = requests.post(URL + "/api/alerts", timeout=TIMEOUT)
        assert r.status_code == 400


# ═══════════════════════════════════════════════════════════════════
# 8) ALERTS PAGE — HTML STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestAlertsHTML:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.html = _read("templates/alerts.html")

    def test_extends_base(self):
        assert "{% extends" in self.html

    def test_has_title(self):
        assert "Alarmlar" in self.html

    def test_has_create_button(self):
        assert "btnCreateAlert" in self.html

    def test_has_form_wrap(self):
        assert "alertFormWrap" in self.html

    def test_has_symbol_input(self):
        assert "alertSymbol" in self.html

    def test_has_market_select(self):
        assert "alertMarket" in self.html

    def test_has_condition_select(self):
        assert "alertCondition" in self.html

    def test_has_value_input(self):
        assert "alertValue" in self.html

    def test_has_save_button(self):
        assert "btnSaveAlert" in self.html

    def test_has_cancel_button(self):
        assert "btnCancelAlert" in self.html

    def test_has_active_alerts_table(self):
        assert "alertsBody" in self.html

    def test_has_triggered_table(self):
        assert "triggeredBody" in self.html

    def test_has_tabs(self):
        assert "alerts-tab" in self.html

    def test_has_toast_container(self):
        assert "alert-toast-container" in self.html

    def test_links_css(self):
        assert "alerts.css" in self.html

    def test_links_js(self):
        assert "alerts.js" in self.html

    def test_market_options(self):
        for market in ["crypto", "bist", "stocks", "forex", "commodities"]:
            assert f'value="{market}"' in self.html

    def test_condition_options(self):
        for ct in ["price_above", "price_below", "rsi_above", "rsi_below",
                    "ema_cross", "breakout", "volume_spike"]:
            assert ct in self.html

    def test_active_tab_default(self):
        assert 'class="alerts-tab active"' in self.html

    def test_triggered_wrap_hidden(self):
        assert 'alerts-table-wrap hidden' in self.html


# ═══════════════════════════════════════════════════════════════════
# 9) CSS STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestAlertsCSS:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.css = _read("static/css/alerts.css")

    def test_has_alerts_page(self):
        assert ".alerts-page" in self.css

    def test_has_alert_form(self):
        assert ".alert-form" in self.css

    def test_has_alerts_tabs(self):
        assert ".alerts-tabs" in self.css

    def test_has_alerts_table(self):
        assert ".alerts-table" in self.css

    def test_has_toast_container(self):
        assert ".alert-toast-container" in self.css

    def test_has_toast_animation(self):
        assert "toastIn" in self.css
        assert "toastOut" in self.css

    def test_has_status_badges(self):
        assert ".alert-status" in self.css
        assert ".alert-status.active" in self.css

    def test_has_delete_button(self):
        assert ".alert-btn-delete" in self.css

    def test_has_responsive(self):
        assert "@media" in self.css

    def test_has_alert_icon_btn(self):
        assert ".alert-icon-btn" in self.css

    def test_has_trade_alert_panel(self):
        assert ".trade-alert-panel" in self.css


# ═══════════════════════════════════════════════════════════════════
# 10) JAVASCRIPT STRUCTURE
# ═══════════════════════════════════════════════════════════════════
class TestAlertsJS:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.js = _read("static/js/alerts.js")

    def test_is_iife(self):
        assert "(function()" in self.js

    def test_has_api_constant(self):
        assert "'/api/alerts'" in self.js

    def test_has_condition_labels(self):
        assert "CONDITION_LABELS" in self.js

    def test_has_init_function(self):
        assert "function init()" in self.js

    def test_has_load_alerts(self):
        assert "function loadAlerts()" in self.js or "loadAlerts" in self.js

    def test_has_load_triggered(self):
        assert "loadTriggered" in self.js

    def test_has_delete_alert(self):
        assert "deleteAlert" in self.js

    def test_has_show_toast(self):
        assert "showToast" in self.js

    def test_has_polling(self):
        assert "startPolling" in self.js or "POLL_INTERVAL" in self.js

    def test_has_handle_create(self):
        assert "handleCreate" in self.js

    def test_has_switch_tab(self):
        assert "switchTab" in self.js

    def test_exports_alerts_app(self):
        assert "window.AlertsApp" in self.js

    def test_auto_init(self):
        assert "DOMContentLoaded" in self.js

    def test_references_correct_ids(self):
        assert "btnCreateAlert" in self.js
        assert "btnSaveAlert" in self.js
        assert "alertsBody" in self.js
        assert "triggeredBody" in self.js


# ═══════════════════════════════════════════════════════════════════
# 11) TRADE PAGE ALERTS JS
# ═══════════════════════════════════════════════════════════════════
class TestTradeAlertsJS:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.js = _read("static/js/trade_alerts.js")

    def test_is_iife(self):
        assert "(function()" in self.js

    def test_polls_triggered(self):
        assert "/api/alerts/triggered" in self.js

    def test_has_toast(self):
        assert "showToast" in self.js

    def test_has_condition_map(self):
        assert "price_above" in self.js
        assert "price_below" in self.js

    def test_poll_interval(self):
        assert "POLL_MS" in self.js or "setInterval" in self.js


# ═══════════════════════════════════════════════════════════════════
# 12) TRADE PAGE INTEGRATION
# ═══════════════════════════════════════════════════════════════════
class TestTradePageIntegration:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.html = _read("templates/trade.html")

    def test_has_alert_icon_button(self):
        assert "tradeAlertBtn" in self.html

    def test_alert_icon_links_to_alerts(self):
        assert "/alerts" in self.html

    def test_includes_alerts_css(self):
        assert "alerts.css" in self.html

    def test_includes_trade_alerts_js(self):
        assert "trade_alerts.js" in self.html

    def test_has_bell_icon_svg(self):
        assert "viewBox" in self.html
        # bell path
        assert "M18 8A6" in self.html or "alert-icon-btn" in self.html


# ═══════════════════════════════════════════════════════════════════
# 13) BLUEPRINT & ROUTE REGISTRATION
# ═══════════════════════════════════════════════════════════════════
class TestBlueprintRegistration:

    def test_blueprint_imported_in_monolith(self):
        src = _read("legacy_monolith.py")
        assert "from app.blueprints.alerts import alerts_bp" in src

    def test_blueprint_registered_in_monolith(self):
        src = _read("legacy_monolith.py")
        assert "app.register_blueprint(alerts_bp)" in src

    def test_alerts_route_in_dashboard(self):
        src = _read("app/blueprints/dashboard/routes.py")
        assert '"/alerts"' in src

    def test_background_job_import(self):
        src = _read("app/background/jobs.py")
        assert "from app.core.alert_engine import alert_check_loop" in src

    def test_background_job_registered(self):
        src = _read("app/background/jobs.py")
        assert "alert_check" in src


# ═══════════════════════════════════════════════════════════════════
# 14) ALERTS PAGE ROUTE (LIVE)
# ═══════════════════════════════════════════════════════════════════
class TestAlertsPageLive:

    def test_alerts_page_returns_200(self):
        r = _get("/alerts")
        assert r.status_code == 200

    def test_alerts_page_has_title(self):
        r = _get("/alerts")
        assert "Alarmlar" in r.text

    def test_alerts_page_has_form(self):
        r = _get("/alerts")
        assert "alertFormWrap" in r.text

    def test_alerts_page_has_table(self):
        r = _get("/alerts")
        assert "alertsBody" in r.text


# ═══════════════════════════════════════════════════════════════════
# 15) ALERT API — FULL CRUD CYCLE (LIVE)
# ═══════════════════════════════════════════════════════════════════
class TestAlertAPICycle:

    def test_full_crud_cycle(self):
        # Create
        r = _post("/api/alerts", {
            "symbol": "LIFECYCLETEST",
            "condition_type": "price_above",
            "condition_value": 12345
        })
        assert r.status_code == 201
        alert_id = r.json()["alert"]["id"]

        # Read — should be in list
        r2 = _get("/api/alerts")
        ids = [a["id"] for a in r2.json()["alerts"]]
        assert alert_id in ids

        # Delete
        r3 = _delete(f"/api/alerts/{alert_id}")
        assert r3.status_code == 200

        # Verify gone
        r4 = _get("/api/alerts")
        ids_after = [a["id"] for a in r4.json()["alerts"]]
        assert alert_id not in ids_after

    def test_multiple_creates(self):
        created = []
        for i in range(3):
            r = _post("/api/alerts", {
                "symbol": f"MULTI{i}",
                "condition_type": "price_below",
                "condition_value": 100 + i
            })
            assert r.status_code == 201
            created.append(r.json()["alert"]["id"])

        r = _get("/api/alerts")
        ids = [a["id"] for a in r.json()["alerts"]]
        for cid in created:
            assert cid in ids

        # cleanup
        for cid in created:
            _delete(f"/api/alerts/{cid}")


# ═══════════════════════════════════════════════════════════════════
# 16) BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════════════
class TestBackwardCompatibility:
    """Ensure existing routes still work after FAZ 20 changes."""

    def test_home_page(self):
        r = _get("/")
        assert r.status_code == 200

    def test_trade_page(self):
        r = _get("/trade")
        assert r.status_code == 200

    def test_discover_page(self):
        r = _get("/discover")
        assert r.status_code == 200

    def test_screener_page(self):
        r = _get("/screener")
        assert r.status_code == 200

    def test_chat_page(self):
        r = _get("/chat")
        assert r.status_code == 200

    def test_market_ticker_api(self):
        r = _get("/api/market/ticker?symbol=BTCUSDT")
        assert r.status_code == 200

    def test_signals_api(self):
        r = _get("/api/signals")
        assert r.status_code == 200

    def test_trade_page_has_scripts(self):
        r = _get("/trade")
        assert "trade.js" in r.text
        assert "multichart.js" in r.text
