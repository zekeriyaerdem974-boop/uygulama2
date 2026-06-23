# -*- coding: utf-8 -*-
"""Copilot API routes — FAZ 21.

AI Trading Copilot endpoints:
  POST /api/copilot/ask      — General copilot question (auto-detect context)
  POST /api/copilot/symbol   — Symbol-specific question with market context
  POST /api/copilot/discover — Discover page AI summary
  POST /api/copilot/screener — Screener results interpretation

All endpoints return:
  {
    ok: true,
    data: {
      answer: "...",
      summary: "...",
      key_points: [...],
      risk_points: [...],
      suggested_alerts: [...]
    }
  }
"""
from __future__ import annotations

import logging

from flask import jsonify, request, session

from app.blueprints.copilot import copilot_bp

_logger = logging.getLogger("zkr_analiz.copilot.routes")


def _check_copilot_limit():
    """FAZ 36 — Check copilot daily usage limit."""
    uid = session.get("user_id")
    if not uid:
        return None  # allow anonymous for now
    from app.core.subscription_engine import enforce_limit, increment_copilot_usage
    check = enforce_limit(uid, "copilot")
    if not check["allowed"]:
        return jsonify({
            "ok": False, "error": check["reason"],
            "upgrade_required": True, "required_plan": check.get("required_plan"),
        }), 429
    increment_copilot_usage(uid)
    return None


@copilot_bp.route("/api/copilot/ask", methods=["POST"])
def copilot_ask():
    """General copilot question — auto-detects context type.

    Body:
      {
        "question": "BTC şu an neden yükseliyor?",
        "symbol": "BTCUSDT",      // optional
        "market": "crypto",        // optional, default crypto
        "timeframe": "15m",        // optional, default 1d
        "model": "..."             // optional
      }
    """
    try:
        # FAZ 36 — copilot daily limit
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "").strip()
        if not question:
            return jsonify({"ok": False, "error": "question is required"}), 400

        symbol = (body.get("symbol") or "").strip().upper()
        market = (body.get("market") or "crypto").strip().lower()
        timeframe = (body.get("timeframe") or "1d").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        if symbol:
            from app.core.copilot_service import ask_symbol
            result = ask_symbol(symbol, market, timeframe, question, **kwargs)
        else:
            from app.core.copilot_service import ask_market
            result = ask_market(market, question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot ask error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/symbol", methods=["POST"])
def copilot_symbol():
    """Symbol-specific copilot question.

    Body:
      {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "timeframe": "15m",
        "question": "Bu grafikte ne görüyorsun?"
      }
    """
    try:
        # FAZ 36 — copilot daily limit
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        symbol = (body.get("symbol") or "").strip().upper()
        if not symbol:
            return jsonify({"ok": False, "error": "symbol is required"}), 400

        market = (body.get("market") or "crypto").strip().lower()
        timeframe = (body.get("timeframe") or "1d").strip()
        question = (body.get("question") or "Bu sembolü analiz et").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_symbol
        result = ask_symbol(symbol, market, timeframe, question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot symbol error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/discover", methods=["POST"])
def copilot_discover():
    """Discover page AI summary.

    Body:
      {
        "question": "Bugün piyasada ne öne çıkıyor?"
      }
    """
    try:
        # FAZ 36 — copilot daily limit
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "Bugün piyasada ne öne çıkıyor? Özetle.").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_discover
        result = ask_discover(question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot discover error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/screener", methods=["POST"])
def copilot_screener():
    """Screener results AI interpretation.

    Body:
      {
        "market": "crypto",
        "filters": ["strong_uptrend", "rsi_above_60"],
        "question": "Bu sonuçları yorumla"
      }
    """
    try:
        # FAZ 36 — copilot daily limit
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        market = (body.get("market") or "crypto").strip().lower()
        filters = body.get("filters") or []
        question = (body.get("question") or "Bu screener sonuçlarını yorumla.").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_screener
        result = ask_screener(market, filters, question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot screener error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/simulator", methods=["POST"])
def copilot_simulator():
    """Simulator / Paper Trading AI analysis.

    Body:
      {
        "question": "Portföyümü değerlendir"
      }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "Simülatör portföyümü analiz et ve önerilerde bulun.").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_simulator
        result = ask_simulator(question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot simulator error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/portfolio", methods=["POST"])
def copilot_portfolio():
    """Portfolio AI analysis — FAZ 39.

    Body:
      {
        "question": "Portföy riskimi analiz et"
      }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "Portföyümü analiz et.").strip()

        from app.core.portfolio_ai_advisor import ask_portfolio
        from app.blueprints.auth.routes import get_session_user_id
        uid = get_session_user_id() or "default"
        result = ask_portfolio(uid, question)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot portfolio error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/journal", methods=["POST"])
def copilot_journal():
    """Trade Journal AI analysis — FAZ 23.

    Body:
      {
        "question": "İşlem günlüğümü analiz et"
      }
    """
    try:
        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "İşlem günlüğümü analiz et ve önerilerde bulun.").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_journal
        result = ask_journal(question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot journal error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


@copilot_bp.route("/api/copilot/opportunities", methods=["POST"])
def copilot_opportunities():
    """Market Opportunities AI analysis — FAZ 40.

    Body:
      {
        "question": "Tespit edilen fırsatları analiz et"
      }
    """
    try:
        # FAZ 36 — copilot daily limit
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        question = (body.get("question") or "Tespit edilen piyasa fırsatlarını analiz et ve özetle.").strip()
        model = body.get("model") or None

        kwargs = {}
        if model:
            kwargs["model"] = model

        from app.core.copilot_service import ask_opportunities
        result = ask_opportunities(question, **kwargs)

        return jsonify({"ok": True, "data": result})
    except Exception as exc:
        _logger.error("Copilot opportunities error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── FAZ 42 — Copilot Activity Summary ────────────────────────────

@copilot_bp.route("/api/copilot/activity", methods=["POST"])
def copilot_activity():
    """Activity stream AI summary — answers questions about recent market activity.

    Body:
      {
        "question": "What critical events happened today?",   // optional
        "hours": 6                                            // optional
      }
    """
    try:
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        hours = min(int(body.get("hours", 6)), 48)

        from app.core.activity_stream_engine import get_activity_summary
        summary = get_activity_summary(hours=hours)

        return jsonify({"ok": True, "data": {
            "answer": summary.get("summary", ""),
            "summary": summary.get("summary", ""),
            "total_events": summary.get("total_events", 0),
            "critical_count": summary.get("critical_count", 0),
            "trending_symbols": summary.get("trending_symbols", []),
            "by_type": summary.get("by_type", {}),
        }})
    except Exception as exc:
        _logger.error("Copilot activity error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── FAZ 44 — Copilot Referral Stats ────────────────────────────

@copilot_bp.route("/api/copilot/referrals", methods=["POST"])
def copilot_referrals():
    """AI referral summary — answers questions about referral stats.

    Body:
      {
        "user_id": "user123"   // optional, defaults to session user
      }
    """
    try:
        limit_err = _check_copilot_limit()
        if limit_err:
            return limit_err

        body = request.get_json(force=True, silent=True) or {}
        user_id = str(body.get("user_id", "")).strip()
        if not user_id:
            user_id = session.get("user_id", "demo_user")

        from app.core.referral_engine import get_referral_stats, get_growth_stats
        stats = get_referral_stats(user_id)
        growth = get_growth_stats()

        summary = (
            f"You have {stats.get('total_referrals', 0)} total referrals "
            f"({stats.get('active_referrals', 0)} active). "
            f"You have earned {stats.get('rewards_earned', 0)} rewards. "
            f"Platform-wide: {growth.get('total_referrals', 0)} total referrals, "
            f"{growth.get('today', 0)} today, {growth.get('this_week', 0)} this week."
        )

        return jsonify({"ok": True, "data": {
            "answer": summary,
            "user_stats": stats,
            "growth": growth,
        }})
    except Exception as exc:
        _logger.error("Copilot referrals error: %s", exc, exc_info=True)
        return jsonify({"ok": False, "error": str(exc)}), 500
