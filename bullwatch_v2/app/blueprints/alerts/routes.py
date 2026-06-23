# -*- coding: utf-8 -*-
"""Alert API routes — FAZ 20.

GET    /api/alerts          — List all alerts
POST   /api/alerts          — Create a new alert
DELETE /api/alerts/<id>      — Delete an alert
GET    /api/alerts/triggered — Get recently triggered alerts
POST   /api/alerts/clear     — Clear triggered alerts list
"""
from __future__ import annotations

import logging

from flask import jsonify, request, session

from app.blueprints.alerts import alerts_bp
from app.core.alert_engine import (
    create_alert,
    delete_alert,
    get_alerts,
    get_triggered,
    clear_triggered,
    CONDITION_TYPES,
)

_logger = logging.getLogger("zkr_analiz.alerts.routes")


@alerts_bp.route("/api/alerts", methods=["GET"])
def api_alerts_list():
    """Return all alerts for the current user."""
    user_id = session.get('user_id')
    alerts = get_alerts(user_id=user_id)
    return jsonify({
        "ok": True,
        "count": len(alerts),
        "alerts": alerts,
    })


@alerts_bp.route("/api/alerts", methods=["POST"])
def api_alerts_create():
    """Create a new alert.

    JSON body:
        symbol: str (required)
        market: str (default "crypto")
        condition_type: str (required, one of CONDITION_TYPES)
        condition_value: number (required)
        indicator: str (optional)
        timeframe: str (optional, default "1d")
    """
    data = request.get_json(silent=True) or {}

    try:
        user_id = session.get('user_id', 'default')

        # FAZ 36 — alert limit check
        if user_id and user_id != 'default':
            from app.core.subscription_engine import can_create_alert
            check = can_create_alert(user_id)
            if not check["allowed"]:
                return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan")}), 403

        alert = create_alert(data, user_id=user_id)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400

    return jsonify({"ok": True, "alert": alert}), 201


@alerts_bp.route("/api/alerts/<alert_id>", methods=["DELETE"])
def api_alerts_delete(alert_id: str):
    """Delete an alert by ID."""
    deleted = delete_alert(alert_id)
    if not deleted:
        return jsonify({"ok": False, "error": "Alert not found"}), 404
    return jsonify({"ok": True, "deleted": alert_id})


@alerts_bp.route("/api/alerts/triggered", methods=["GET"])
def api_alerts_triggered():
    """Return recently triggered alerts."""
    triggered = get_triggered()
    return jsonify({
        "ok": True,
        "count": len(triggered),
        "triggered": triggered,
    })


@alerts_bp.route("/api/alerts/clear", methods=["POST"])
def api_alerts_clear():
    """Clear triggered alerts list."""
    clear_triggered()
    return jsonify({"ok": True})


@alerts_bp.route("/api/alerts/types", methods=["GET"])
def api_alerts_types():
    """Return available condition types."""
    return jsonify({
        "ok": True,
        "types": sorted(CONDITION_TYPES),
    })
