# -*- coding: utf-8 -*-
"""Opportunities API routes — FAZ 40.

Endpoints:
  GET  /opportunities              — Opportunities page (HTML)
  GET  /api/opportunities          — List active opportunities (JSON)
  GET  /api/opportunities/trending — Top trending opportunities
  GET  /api/opportunities/<symbol> — Opportunities for a specific symbol
  POST /api/opportunities/scan     — Trigger a manual scan (auth required)
  GET  /api/opportunities/alerts   — Get user's smart alerts
  POST /api/opportunities/alert/create — Create a smart alert
  DELETE /api/opportunities/alert/<id> — Delete smart alert
  PUT  /api/opportunities/alert/<id>   — Update smart alert
  GET  /api/opportunities/notifications — Get triggered alert notifications
  POST /api/opportunities/notifications/read — Mark notifications as read
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request

from app.blueprints.opportunities import opportunities_bp
from app.blueprints.auth.routes import login_required, get_session_user_id

_logger = logging.getLogger("zkr_analiz.opportunities.routes")


# ── HTML Page ─────────────────────────────────────────────────────

@opportunities_bp.route("/opportunities")
def opportunities_page():
    """Render the opportunities dashboard page."""
    return render_template("opportunities.html")


# ── API: Opportunities ───────────────────────────────────────────

@opportunities_bp.route("/api/opportunities")
def api_get_opportunities():
    """List active opportunities with optional filters.

    Query params:
      market: filter by market (crypto/stocks/forex)
      event_type: filter by event type
      limit: max results (default 50)
    """
    try:
        from app.core.opportunity_engine import get_cached_opportunities, get_db_opportunities

        market = request.args.get("market", "").strip().lower() or None
        event_type = request.args.get("event_type", "").strip() or None
        limit = min(int(request.args.get("limit", 50)), 100)

        if market or event_type:
            opps = get_db_opportunities(market=market, event_type=event_type, limit=limit)
        else:
            opps = get_cached_opportunities()
            if opps:
                opps = opps[:limit]
            else:
                opps = get_db_opportunities(limit=limit)

        return jsonify({
            "ok": True,
            "data": opps,
            "total": len(opps),
        })
    except Exception as exc:
        _logger.error("Get opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/trending")
def api_trending_opportunities():
    """Top trending opportunities by confidence.

    Query params:
      limit: max results (default 10)
    """
    try:
        from app.core.opportunity_engine import get_trending_opportunities

        limit = min(int(request.args.get("limit", 10)), 50)
        opps = get_trending_opportunities(limit=limit)

        return jsonify({"ok": True, "data": opps, "total": len(opps)})
    except Exception as exc:
        _logger.error("Trending opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/<symbol>")
def api_symbol_opportunities(symbol):
    """Get opportunities for a specific symbol."""
    try:
        from app.core.opportunity_engine import get_opportunity_by_symbol

        opps = get_opportunity_by_symbol(symbol)
        return jsonify({"ok": True, "data": opps, "total": len(opps)})
    except Exception as exc:
        _logger.error("Symbol opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/scan", methods=["POST"])
@login_required
def api_scan_opportunities(user):
    """Trigger a manual opportunity scan (rate limited by auth)."""
    try:
        from app.core.opportunity_engine import scan_all_opportunities

        opps = scan_all_opportunities()

        # Also evaluate smart alerts
        try:
            from app.core.smart_alert_engine import evaluate_alerts
            triggered = evaluate_alerts(opps)
        except Exception:
            triggered = []

        return jsonify({
            "ok": True,
            "data": opps,
            "total": len(opps),
            "alerts_triggered": len(triggered),
        })
    except Exception as exc:
        _logger.error("Scan opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Smart Alerts ────────────────────────────────────────────

@opportunities_bp.route("/api/opportunities/alerts")
@login_required
def api_get_alerts(user):
    """Get the current user's smart alerts."""
    try:
        from app.core.smart_alert_engine import get_user_alerts

        alerts = get_user_alerts(user["id"])
        return jsonify({"ok": True, "data": alerts})
    except Exception as exc:
        _logger.error("Get alerts error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/alert/create", methods=["POST"])
@login_required
def api_create_alert(user):
    """Create a new smart alert.

    Body:
      {
        "alert_type": "event_volume_spike",
        "name": "BTC Hacim Artışı",
        "symbol": "BTCUSDT",          // optional
        "market": "crypto",           // optional
        "min_confidence": 60,          // optional
        "event_types": "volume_spike", // optional
        "cooldown_minutes": 60         // optional
      }
    """
    try:
        from app.core.smart_alert_engine import create_smart_alert

        body = request.get_json(force=True, silent=True) or {}
        alert = create_smart_alert(user["id"], body)

        return jsonify({"ok": True, "data": alert}), 201
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        _logger.error("Create alert error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/alert/<alert_id>", methods=["DELETE"])
@login_required
def api_delete_alert(user, alert_id):
    """Delete a smart alert."""
    try:
        from app.core.smart_alert_engine import delete_smart_alert

        deleted = delete_smart_alert(user["id"], alert_id)
        if not deleted:
            return jsonify({"ok": False, "error": "Alert not found"}), 404
        return jsonify({"ok": True})
    except Exception as exc:
        _logger.error("Delete alert error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/alert/<alert_id>", methods=["PUT"])
@login_required
def api_update_alert(user, alert_id):
    """Update a smart alert.

    Body: any fields from create_alert to update
    """
    try:
        from app.core.smart_alert_engine import update_smart_alert

        body = request.get_json(force=True, silent=True) or {}
        updated = update_smart_alert(user["id"], alert_id, body)
        if not updated:
            return jsonify({"ok": False, "error": "Alert not found"}), 404
        return jsonify({"ok": True, "data": updated})
    except Exception as exc:
        _logger.error("Update alert error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Notifications ───────────────────────────────────────────

@opportunities_bp.route("/api/opportunities/notifications")
@login_required
def api_get_notifications(user):
    """Get triggered alert notifications.

    Query params:
      unread: "1" to show only unread
      limit: max results (default 50)
    """
    try:
        from app.core.smart_alert_engine import get_triggered_alerts, get_unread_count

        unread_only = request.args.get("unread") == "1"
        limit = min(int(request.args.get("limit", 50)), 200)

        triggers = get_triggered_alerts(user["id"], unread_only=unread_only, limit=limit)
        unread = get_unread_count(user["id"])

        return jsonify({
            "ok": True,
            "data": triggers,
            "unread_count": unread,
        })
    except Exception as exc:
        _logger.error("Get notifications error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@opportunities_bp.route("/api/opportunities/notifications/read", methods=["POST"])
@login_required
def api_mark_notifications_read(user):
    """Mark notifications as read.

    Body:
      { "ids": ["id1", "id2"] }  // optional, marks all if omitted
    """
    try:
        from app.core.smart_alert_engine import mark_alerts_read

        body = request.get_json(force=True, silent=True) or {}
        ids = body.get("ids")
        count = mark_alerts_read(user["id"], ids)

        return jsonify({"ok": True, "marked": count})
    except Exception as exc:
        _logger.error("Mark read error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── API: Alert Types ─────────────────────────────────────────────

@opportunities_bp.route("/api/opportunities/alert-types")
def api_alert_types():
    """List available smart alert types."""
    from app.core.smart_alert_engine import SMART_ALERT_TYPES
    from app.core.opportunity_engine import EVENT_TYPES

    return jsonify({
        "ok": True,
        "alert_types": SMART_ALERT_TYPES,
        "event_types": {k: {"icon": v["icon"], "label": v["label"]} for k, v in EVENT_TYPES.items()},
    })
