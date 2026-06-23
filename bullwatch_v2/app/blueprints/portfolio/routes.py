# -*- coding: utf-8 -*-
"""Portfolio API Routes — FAZ 39.

Portföy yönetimi, risk analizi ve AI içgörü endpoint'leri.

Pages:
  GET  /portfolio                 — Portfolio dashboard page

API Routes:
  GET    /api/portfolio            — Get portfolio assets
  POST   /api/portfolio/add        — Add asset to portfolio
  DELETE /api/portfolio/remove     — Remove asset from portfolio
  GET    /api/portfolio/summary    — Full portfolio summary with PnL
  GET    /api/portfolio/risk       — Risk analysis
  GET    /api/portfolio/ai         — AI portfolio insight
  POST   /api/portfolio/ai/ask    — Ask AI about portfolio
"""
from __future__ import annotations

import logging

from flask import jsonify, render_template, request

from app.blueprints.portfolio import portfolio_bp
from app.blueprints.auth.routes import login_required, get_session_user_id

_logger = logging.getLogger("zkr_analiz.portfolio.routes")


# ══════════════════════════════════════════════════════════════════════
# PAGE ROUTE
# ══════════════════════════════════════════════════════════════════════

@portfolio_bp.route("/portfolio")
def portfolio_page():
    """Portfolio dashboard page."""
    return render_template("portfolio.html")


# ══════════════════════════════════════════════════════════════════════
# API ROUTES
# ══════════════════════════════════════════════════════════════════════

@portfolio_bp.route("/api/portfolio")
@login_required
def api_get_portfolio(user):
    """Get all assets in the user's portfolio. Falls back to demo data."""
    try:
        from app.core.portfolio_engine import get_assets
        assets = get_assets(user["id"])
        if not assets:
            from app.core.demo_data_engine import get_demo_portfolio
            assets = get_demo_portfolio()
        return jsonify({"ok": True, "assets": assets})
    except Exception as exc:
        _logger.error("Portfolio get error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/add", methods=["POST"])
@login_required
def api_add_asset(user):
    """Add an asset to the portfolio.

    Body: { symbol, market, amount, entry_price }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        symbol = (body.get("symbol") or "").strip().upper()
        market = (body.get("market") or "crypto").strip().lower()
        amount = float(body.get("amount", 0))
        entry_price = float(body.get("entry_price", 0))

        if not symbol:
            return jsonify({"ok": False, "error": "Sembol gerekli"}), 400

        from app.core.portfolio_engine import add_asset
        result = add_asset(user["id"], symbol, market, amount, entry_price)
        return jsonify({"ok": True, "asset": result})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        _logger.error("Portfolio add error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/remove", methods=["DELETE"])
@login_required
def api_remove_asset(user):
    """Remove an asset from the portfolio.

    Body: { symbol }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        symbol = (body.get("symbol") or "").strip().upper()

        if not symbol:
            return jsonify({"ok": False, "error": "Sembol gerekli"}), 400

        from app.core.portfolio_engine import remove_asset
        removed = remove_asset(user["id"], symbol)
        if not removed:
            return jsonify({"ok": False, "error": "Varlık bulunamadı"}), 404
        return jsonify({"ok": True, "removed": symbol})
    except Exception as exc:
        _logger.error("Portfolio remove error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/summary")
@login_required
def api_portfolio_summary(user):
    """Get full portfolio summary with PnL, allocation, asset details."""
    try:
        from app.core.portfolio_engine import portfolio_summary, get_assets
        # FAZ 64B — Auto-seed demo data if portfolio is empty
        assets = get_assets(user["id"])
        if not assets:
            from app.core.demo_data_engine import seed_demo_portfolio
            seed_demo_portfolio(user["id"])
        summary = portfolio_summary(user["id"])
        return jsonify({"ok": True, "data": summary})
    except Exception as exc:
        _logger.error("Portfolio summary error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/risk")
@login_required
def api_portfolio_risk(user):
    """Get portfolio risk analysis."""
    try:
        from app.core.portfolio_risk_engine import calculate_risk_score
        from app.core.portfolio_engine import get_assets
        # FAZ 64B — Auto-seed demo data if portfolio is empty
        assets = get_assets(user["id"])
        if not assets:
            from app.core.demo_data_engine import seed_demo_portfolio
            seed_demo_portfolio(user["id"])
        risk = calculate_risk_score(user["id"])
        return jsonify({"ok": True, "data": risk})
    except Exception as exc:
        _logger.error("Portfolio risk error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/ai")
@login_required
def api_portfolio_ai(user):
    """Get AI-generated portfolio insight."""
    try:
        from app.core.portfolio_ai_advisor import generate_portfolio_insight
        insight = generate_portfolio_insight(user["id"])
        return jsonify({"ok": True, "data": insight})
    except Exception as exc:
        _logger.error("Portfolio AI error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/portfolio/ai/ask", methods=["POST"])
@login_required
def api_portfolio_ai_ask(user):
    """Ask a specific question about the portfolio using AI.

    Body: { question }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "").strip()
        if not question:
            question = "Portföyümü genel olarak değerlendir."

        from app.core.portfolio_ai_advisor import ask_portfolio
        result = ask_portfolio(user["id"], question)
        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Portfolio AI ask error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@portfolio_bp.route("/api/demo/portfolio")
def api_demo_portfolio():
    """Public demo portfolio for unauthenticated users."""
    from app.core.demo_data_engine import get_demo_portfolio
    return jsonify({"ok": True, "assets": get_demo_portfolio()})
