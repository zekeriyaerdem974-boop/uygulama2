# -*- coding: utf-8 -*-
"""AI Agent API routes — FAZ 49.

Pages:
  GET  /ai-agent                    — AI Agent page (HTML)

API Routes:
  GET  /api/ai/brief                — Personal AI market brief
  GET  /api/ai/market-summary       — General market summary
  GET  /api/ai/portfolio            — AI portfolio intelligence
  GET  /api/ai/watchlist            — AI watchlist intelligence
  GET  /api/ai/opportunities        — Top AI-explained opportunities
  GET  /api/ai/opportunity/<id>     — AI explanation for one opportunity
  POST /api/ai/ask                  — Free-form AI question
  POST /api/copilot/agent           — Copilot integration endpoint
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request, session

from app.blueprints.ai_agent import ai_agent_bp
from app.blueprints.auth.routes import login_required, get_session_user_id

_logger = logging.getLogger("zkr_analiz.ai_agent.routes")


# ══════════════════════════════════════════════════════════════════════
# PAGE ROUTE
# ══════════════════════════════════════════════════════════════════════

@ai_agent_bp.route("/ai-agent")
def ai_agent_page():
    """Render the AI Agent page."""
    return render_template("ai_agent.html")


# ══════════════════════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════════════════════

@ai_agent_bp.route("/api/ai/brief")
@login_required
def api_ai_brief(user):
    """Get personalised AI market brief.

    Returns comprehensive market intelligence tailored to the user's
    portfolio and watchlist.
    """
    try:
        from app.core.ai_market_agent import generate_brief
        brief = generate_brief(user["id"])
        return jsonify({"ok": True, "data": brief})
    except Exception as exc:
        _logger.error("AI brief error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/market-summary")
def api_market_summary():
    """Get general market summary (no auth required).

    Returns market sentiment, highlights, and top data.
    """
    try:
        from app.core.ai_market_agent import get_market_summary
        summary = get_market_summary()
        return jsonify({"ok": True, "data": summary})
    except Exception as exc:
        _logger.error("AI market summary error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/portfolio")
@login_required
def api_ai_portfolio(user):
    """Get AI portfolio intelligence.

    Returns risk assessment, allocation insights, and performance
    observations for the user's portfolio.
    """
    try:
        from app.core.ai_market_agent import analyze_portfolio
        result = analyze_portfolio(user["id"])
        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("AI portfolio error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/watchlist")
@login_required
def api_ai_watchlist(user):
    """Get AI watchlist intelligence.

    Returns price movements, opportunity alerts, and intelligence
    for the user's watched symbols.
    """
    try:
        from app.core.ai_market_agent import analyze_watchlist
        result = analyze_watchlist(user["id"])
        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("AI watchlist error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/opportunities")
def api_ai_opportunities():
    """Get top AI-explained opportunities.

    Query params:
      limit: max results (default 10, max 20)
    """
    try:
        from app.core.ai_market_agent import get_top_opportunities
        limit = min(int(request.args.get("limit", 10)), 20)
        opps = get_top_opportunities(limit=limit)
        return jsonify({"ok": True, "data": opps, "total": len(opps)})
    except Exception as exc:
        _logger.error("AI opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/opportunity/<opp_id>")
def api_ai_opportunity_explain(opp_id):
    """Get AI explanation for a specific opportunity."""
    try:
        from app.core.ai_market_agent import explain_opportunity
        result = explain_opportunity(opp_id)
        if not result.get("found", False):
            return jsonify({"ok": False, "error": result.get("error", "Not found")}), 404
        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("AI opportunity explain error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@ai_agent_bp.route("/api/ai/ask", methods=["POST"])
@login_required
def api_ai_ask(user):
    """Ask a free-form question to the AI agent.

    Body: { "question": "..." }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "").strip()
        if not question:
            return jsonify({"ok": False, "error": "Soru gerekli"}), 400
        if len(question) > 500:
            return jsonify({"ok": False, "error": "Soru çok uzun (max 500 karakter)"}), 400

        from app.core.ai_market_agent import ask_agent
        result = ask_agent(user["id"], question)
        return jsonify(result)
    except Exception as exc:
        _logger.error("AI ask error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════
# COPILOT INTEGRATION — FAZ 49
# ══════════════════════════════════════════════════════════════════════

@ai_agent_bp.route("/api/copilot/agent", methods=["POST"])
@login_required
def api_copilot_agent(user):
    """Copilot integration endpoint — ask the AI agent via copilot.

    Body: {
      "question": "...",
      "context": "brief|portfolio|watchlist|market"  // optional
    }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "").strip()
        context_type = (body.get("context") or "").strip().lower()

        if not question:
            return jsonify({"ok": False, "error": "Soru gerekli"}), 400
        if len(question) > 500:
            return jsonify({"ok": False, "error": "Soru çok uzun"}), 400

        from app.core.ai_market_agent import (
            generate_brief, analyze_portfolio, analyze_watchlist,
            get_market_summary, ask_agent,
        )

        # Route to specific context if requested
        if context_type == "brief":
            data = generate_brief(user["id"])
            return jsonify({"ok": True, "data": data, "source": "ai_agent_brief"})
        elif context_type == "portfolio":
            data = analyze_portfolio(user["id"])
            return jsonify({"ok": True, "data": data, "source": "ai_agent_portfolio"})
        elif context_type == "watchlist":
            data = analyze_watchlist(user["id"])
            return jsonify({"ok": True, "data": data, "source": "ai_agent_watchlist"})
        elif context_type == "market":
            data = get_market_summary()
            return jsonify({"ok": True, "data": data, "source": "ai_agent_market"})
        else:
            result = ask_agent(user["id"], question)
            if isinstance(result, dict) and "data" in result:
                result["source"] = "ai_agent_ask"
            return jsonify(result)
    except Exception as exc:
        _logger.error("Copilot agent error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500
