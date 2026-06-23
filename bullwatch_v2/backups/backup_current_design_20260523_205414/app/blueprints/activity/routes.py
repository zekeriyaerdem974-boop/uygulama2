# -*- coding: utf-8 -*-
"""Activity Stream API routes — FAZ 42.

Endpoints:
  GET  /activity                     — Activity Stream page (HTML)
  GET  /api/activity                 — List activity events (JSON)
  GET  /api/activity/trending        — Trending symbols by activity
  GET  /api/activity/<id>            — Single event detail
  GET  /api/activity/symbol/<symbol> — Events for a symbol
  GET  /api/activity/market/<market> — Events for a market
  POST /api/activity/mark-viewed     — Mark events as viewed
  GET  /api/activity/unread-count    — Get unread event count
  GET  /api/activity/summary         — AI summary of recent activity
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.activity import activity_bp

_logger = logging.getLogger("zkr_analiz.activity.routes")


# ── HTML Page ─────────────────────────────────────────────────────

@activity_bp.route("/activity")
def activity_page():
    """Render the Activity Stream page."""
    return render_template("activity.html")


# ── API: Events ──────────────────────────────────────────────────

@activity_bp.route("/api/activity")
def api_get_activity():
    """List activity events with filters.

    Query params:
      market, severity, event_type, symbol, min_confidence, hours, limit, offset
    """
    try:
        from app.core.activity_stream_engine import get_events

        market = request.args.get("market", "").strip().lower() or ""
        severity = request.args.get("severity", "").strip().lower() or ""
        event_type = request.args.get("event_type", "").strip() or ""
        symbol = request.args.get("symbol", "").strip().upper() or ""
        min_confidence = int(request.args.get("min_confidence", 0))
        hours = min(int(request.args.get("hours", 24)), 168)
        limit = min(int(request.args.get("limit", 50)), 200)
        offset = int(request.args.get("offset", 0))

        events = get_events(
            market=market,
            severity=severity,
            event_type=event_type,
            symbol=symbol,
            min_confidence=min_confidence,
            hours=hours,
            limit=limit,
            offset=offset,
        )

        return jsonify({"ok": True, "data": events, "total": len(events)})
    except Exception as exc:
        _logger.error("Get activity error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/trending")
def api_trending():
    """Trending symbols by activity count.

    Query params:
      hours (default 12), limit (default 10)
    """
    try:
        from app.core.activity_stream_engine import get_trending_symbols

        hours = min(int(request.args.get("hours", 12)), 168)
        limit = min(int(request.args.get("limit", 10)), 50)

        trending = get_trending_symbols(hours=hours, limit=limit)
        return jsonify({"ok": True, "data": trending})
    except Exception as exc:
        _logger.error("Trending activity error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/<event_id>")
def api_get_event(event_id):
    """Get a single activity event by ID."""
    try:
        from app.core.activity_stream_engine import get_event

        event = get_event(event_id)
        if not event:
            return jsonify({"ok": False, "error": "Event not found"}), 404
        return jsonify({"ok": True, "data": event})
    except Exception as exc:
        _logger.error("Get event error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/symbol/<symbol>")
def api_events_for_symbol(symbol):
    """Events for a specific symbol.

    Query params:
      hours (default 24), limit (default 20)
    """
    try:
        from app.core.activity_stream_engine import get_events_for_symbol

        symbol = symbol.strip().upper()
        hours = min(int(request.args.get("hours", 24)), 168)
        limit = min(int(request.args.get("limit", 20)), 100)

        events = get_events_for_symbol(symbol=symbol, hours=hours, limit=limit)
        return jsonify({"ok": True, "data": events, "symbol": symbol})
    except Exception as exc:
        _logger.error("Symbol activity error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/market/<market>")
def api_events_for_market(market):
    """Events for a specific market.

    Query params:
      hours (default 24), limit (default 50)
    """
    try:
        from app.core.activity_stream_engine import get_events_for_market

        market = market.strip().lower()
        hours = min(int(request.args.get("hours", 24)), 168)
        limit = min(int(request.args.get("limit", 50)), 200)

        events = get_events_for_market(market=market, hours=hours, limit=limit)
        return jsonify({"ok": True, "data": events, "market": market})
    except Exception as exc:
        _logger.error("Market activity error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/mark-viewed", methods=["POST"])
def api_mark_viewed():
    """Mark events as viewed by current user.

    Body: { "event_ids": ["id1", "id2", ...] }
    """
    try:
        from app.core.activity_stream_engine import mark_viewed

        user_id = session.get("user_id", "anon")
        body = request.get_json(force=True, silent=True) or {}
        event_ids = body.get("event_ids", [])

        if not isinstance(event_ids, list):
            return jsonify({"ok": False, "error": "event_ids must be a list"}), 400

        count = mark_viewed(user_id, event_ids)
        return jsonify({"ok": True, "marked": count})
    except Exception as exc:
        _logger.error("Mark viewed error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/unread-count")
def api_unread_count():
    """Get unread event count for current user.

    Query params:
      hours (default 24)
    """
    try:
        from app.core.activity_stream_engine import get_unread_count

        user_id = session.get("user_id", "anon")
        hours = min(int(request.args.get("hours", 24)), 168)

        count = get_unread_count(user_id, hours=hours)
        return jsonify({"ok": True, "unread": count})
    except Exception as exc:
        _logger.error("Unread count error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@activity_bp.route("/api/activity/summary")
def api_activity_summary():
    """AI-generated summary of recent market activity.

    Query params:
      hours (default 6)
    """
    try:
        from app.core.activity_stream_engine import get_activity_summary

        hours = min(int(request.args.get("hours", 6)), 48)
        summary = get_activity_summary(hours=hours)
        return jsonify({"ok": True, "data": summary})
    except Exception as exc:
        _logger.error("Activity summary error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500
