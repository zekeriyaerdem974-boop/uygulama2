# -*- coding: utf-8 -*-
"""Onboarding & Landing routes — FAZ 46."""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.onboarding import onboarding_bp

_logger = logging.getLogger("zkr_analiz.onboarding.routes")


# ══════════════════════════════════════════════════════════════════════
# PAGES
# ══════════════════════════════════════════════════════════════════════

@onboarding_bp.route("/landing")
def landing_page():
    """Public marketing landing page."""
    return render_template("landing.html")


@onboarding_bp.route("/onboarding")
def onboarding_page():
    """Onboarding wizard for new users."""
    return render_template("onboarding.html")


# ══════════════════════════════════════════════════════════════════════
# API
# ══════════════════════════════════════════════════════════════════════

@onboarding_bp.route("/api/onboarding/complete", methods=["POST"])
def api_onboarding_complete():
    """Save onboarding results (markets + symbols).

    Body: { markets: [...], symbols: [...] }
    """
    user_id = session.get("user_id")
    if not user_id:
        # Allow anonymous onboarding — store in session for later
        data = request.get_json(silent=True) or {}
        session["pending_onboarding"] = {
            "markets": data.get("markets", []),
            "symbols": data.get("symbols", []),
        }
        return jsonify({"ok": True, "saved": "session"})

    data = request.get_json(silent=True) or {}
    markets = data.get("markets", [])
    symbols = data.get("symbols", [])

    # Validate
    valid_markets = {"crypto", "stocks", "bist", "forex", "commodities"}
    markets = [m for m in markets if m in valid_markets]

    from app.core.onboarding_engine import complete_onboarding
    ok = complete_onboarding(user_id, markets, symbols)

    return jsonify({"ok": ok})


@onboarding_bp.route("/api/onboarding/status", methods=["GET"])
def api_onboarding_status():
    """Check if current user has completed onboarding."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"ok": True, "completed": False})

    from app.core.onboarding_engine import is_onboarding_completed
    completed = is_onboarding_completed(user_id)
    return jsonify({"ok": True, "completed": completed})


@onboarding_bp.route("/api/demo/activity", methods=["GET"])
def api_demo_activity():
    """Return demo activity events for empty-state UX."""
    from app.core.demo_data_engine import get_demo_activity
    limit = request.args.get("limit", 10, type=int)
    events = get_demo_activity(limit=min(limit, 20))
    return jsonify({"ok": True, "events": events})


@onboarding_bp.route("/api/demo/opportunities", methods=["GET"])
def api_demo_opportunities():
    """Return demo opportunities for empty-state UX."""
    from app.core.demo_data_engine import get_demo_opportunities
    limit = request.args.get("limit", 6, type=int)
    opps = get_demo_opportunities(limit=min(limit, 10))
    return jsonify({"ok": True, "opportunities": opps})


@onboarding_bp.route("/api/demo/portfolio", methods=["GET"])
def api_demo_portfolio():
    """Return demo portfolio for empty-state UX."""
    from app.core.demo_data_engine import get_demo_portfolio
    return jsonify({"ok": True, "assets": get_demo_portfolio()})


@onboarding_bp.route("/api/demo/trending", methods=["GET"])
def api_demo_trending():
    """Return trending assets for discover page."""
    from app.core.demo_data_engine import get_trending_assets
    return jsonify({"ok": True, "assets": get_trending_assets()})
