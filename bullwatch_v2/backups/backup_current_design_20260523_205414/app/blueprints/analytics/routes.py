# -*- coding: utf-8 -*-
"""Analytics tracking routes — FAZ 46.

Simple event tracking endpoint. Events are stored in an in-memory
buffer and can be queried for dashboards.

Tracked events:
  landing_visit, landing_register_click, signup, onboarding_completed,
  onboarding_step_N, invite_click
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone

from flask import jsonify, request, session

from app.blueprints.analytics import analytics_bp

_logger = logging.getLogger("zkr_analiz.analytics")

# ── In-memory event buffer (last 10 000 events) ──────────────────
_events: deque = deque(maxlen=10_000)
_lock = threading.Lock()

VALID_EVENTS = {
    "landing_visit", "landing_register_click", "landing_login_click",
    "signup", "onboarding_completed", "onboarding_step_1",
    "onboarding_step_2", "onboarding_step_3", "onboarding_step_4",
    "onboarding_step_5", "invite_click", "page_view",
}


@analytics_bp.route("/api/analytics/track", methods=["POST"])
def api_track():
    """Record an analytics event.

    Body: { event: "landing_visit", data: {...}, ts: "..." }
    """
    body = request.get_json(silent=True) or {}
    event_name = (body.get("event") or "").strip()

    if not event_name or event_name not in VALID_EVENTS:
        return jsonify({"ok": False, "error": "invalid event"}), 400

    entry = {
        "event": event_name,
        "data": body.get("data", {}),
        "page": body.get("page", ""),
        "user_id": session.get("user_id"),
        "ts": body.get("ts") or datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _events.append(entry)

    return jsonify({"ok": True})


@analytics_bp.route("/api/analytics/summary", methods=["GET"])
def api_summary():
    """Return event counts for analytics dashboard."""
    with _lock:
        events_copy = list(_events)

    counts: dict = {}
    for e in events_copy:
        name = e["event"]
        counts[name] = counts.get(name, 0) + 1

    return jsonify({"ok": True, "total": len(events_copy), "counts": counts})


def get_events() -> list:
    """Return current events list (for testing)."""
    with _lock:
        return list(_events)


def clear_events():
    """Clear events buffer (for testing)."""
    with _lock:
        _events.clear()
