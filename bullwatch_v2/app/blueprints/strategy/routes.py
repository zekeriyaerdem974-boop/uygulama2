# -*- coding: utf-8 -*-
"""Strategy Builder API routes — FAZ 25 + FAZ 28 (Live Signals).

Endpoints:
  POST /api/strategy/parse       — Parse & validate DSL code
  POST /api/strategy/run         — Run strategy backtest
  GET  /api/strategy/templates   — List builtin templates
  GET  /api/strategy/indicators  — List available indicators
  POST /api/strategy/save        — Save user strategy
  GET  /api/strategy/list        — List user strategies
  DELETE /api/strategy/delete    — Delete user strategy

FAZ 28 — Live Signals:
  POST /api/strategy/live/activate    — Activate strategy for live signals
  POST /api/strategy/live/deactivate  — Deactivate live strategy
  POST /api/strategy/live/toggle      — Toggle live strategy enabled state
  POST /api/strategy/live/remove      — Remove live strategy activation
  GET  /api/strategy/live/active      — List active strategies
  GET  /api/strategy/live/signals     — Get recent live signals
  GET  /api/strategy/live/stats       — Get live engine stats
  POST /api/strategy/live/clear       — Clear signal history
"""
from flask import jsonify, render_template, request, session

from app.core.compliance_filter import filter_api_response

from app.blueprints.strategy import strategy_bp


@strategy_bp.route("/templates", methods=["GET"])
def api_templates():
    """Return builtin strategy templates."""
    try:
        from app.core.strategy_engine import list_builtin_templates
        return jsonify({"ok": True, "templates": list_builtin_templates()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/indicators", methods=["GET"])
def api_indicators():
    """Return available indicators for the strategy DSL."""
    try:
        from app.core.strategy_engine import list_available_indicators
        return jsonify({"ok": True, "indicators": list_available_indicators()})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/parse", methods=["POST"])
def api_parse():
    """Parse and validate DSL code without running backtest."""
    try:
        data = request.get_json(force=True) or {}
        code = data.get("code", "").strip()
        if not code:
            return jsonify({"ok": False, "error": "Strateji kodu gerekli"}), 400

        from app.core.strategy_engine import parse_strategy, validate_strategy
        parsed = parse_strategy(code)
        validation = validate_strategy(parsed)

        return jsonify({
            "ok": True,
            "parsed": {
                "name": parsed.get("name", ""),
                "entry_conditions": parsed.get("entry_conditions", []),
                "exit_conditions": parsed.get("exit_conditions", []),
                "risk": parsed.get("risk", {}),
            },
            "validation": validation,
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/run", methods=["POST"])
def api_run():
    """Run a strategy backtest.

    Body JSON:
      code      — DSL code (required)
      symbol    — e.g. BTCUSDT (required)
      market    — e.g. crypto (default: crypto)
      interval  — e.g. 1d (default: 1d)
      limit     — e.g. 500 (default: 500)
    """
    try:
        data = request.get_json(force=True) or {}
        code = data.get("code", "").strip()
        symbol = (data.get("symbol") or "").strip().upper()

        if not code:
            return jsonify({"ok": False, "error": "Strateji kodu gerekli"}), 400
        if not symbol:
            return jsonify({"ok": False, "error": "Sembol gerekli"}), 400

        market = data.get("market", "crypto").strip().lower()
        interval = data.get("interval", "1d").strip()
        limit = int(data.get("limit", 500))

        from app.core.strategy_engine import run_strategy_backtest
        result = run_strategy_backtest(
            code=code,
            symbol=symbol,
            market=market,
            interval=interval,
            limit=limit,
        )

        return jsonify(filter_api_response(result))
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/save", methods=["POST"])
def api_save():
    """Save a user strategy.

    Body JSON:
      name    — Strategy name
      code    — DSL code
      id      — Optional strategy ID for update
    """
    try:
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        code = (data.get("code") or "").strip()

        if not name:
            return jsonify({"ok": False, "error": "Strateji adı gerekli"}), 400
        if not code:
            return jsonify({"ok": False, "error": "Strateji kodu gerekli"}), 400

        user_id = session.get('user_id') or data.get("user_id", "default")
        strategy_id = data.get("id", "")

        # FAZ 36 — saved strategy limit check (only for new strategies)
        if user_id and user_id != 'default' and not strategy_id:
            from app.core.subscription_engine import can_save_strategy
            check = can_save_strategy(user_id)
            if not check["allowed"]:
                return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan")}), 403

        from app.core.strategy_engine import save_strategy
        result = save_strategy(user_id, name, code, strategy_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/list", methods=["GET"])
def api_list():
    """List user strategies."""
    try:
        user_id = session.get('user_id') or request.args.get("user_id", "default")
        from app.core.strategy_engine import load_strategies
        strategies = load_strategies(user_id)
        return jsonify({"ok": True, "strategies": strategies})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/delete", methods=["DELETE", "POST"])
def api_delete():
    """Delete a user strategy."""
    try:
        data = request.get_json(force=True) or {}
        strategy_id = (data.get("id") or "").strip()
        user_id = session.get('user_id') or data.get("user_id", "default")

        if not strategy_id:
            return jsonify({"ok": False, "error": "Strateji ID gerekli"}), 400

        from app.core.strategy_engine import delete_strategy
        success = delete_strategy(user_id, strategy_id)
        if success:
            return jsonify({"ok": True})
        else:
            return jsonify({"ok": False, "error": "Strateji bulunamadı"}), 404
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════
# FAZ 28 — LIVE SIGNALS ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@strategy_bp.route("/live/activate", methods=["POST"])
def api_live_activate():
    """Activate a strategy for live signal generation.

    Body JSON:
      strategy_id  — saved strategy ID
      code         — strategy DSL code
      name         — strategy name
      symbol       — e.g. BTCUSDT
      market       — e.g. crypto (default: crypto)
      interval     — e.g. 15m (default: 15m)
    """
    try:
        data = request.get_json(force=True) or {}
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        code = (data.get("code") or "").strip()
        if not code:
            return jsonify({"ok": False, "error": "Strateji kodu gerekli"}), 400

        # FAZ 36 — active strategy limit check
        from app.core.subscription_engine import can_activate_strategy
        check = can_activate_strategy(user_id)
        if not check["allowed"]:
            return jsonify({"ok": False, "error": check["reason"], "upgrade_required": True, "required_plan": check.get("required_plan")}), 403

        symbol = (data.get("symbol") or "BTCUSDT").strip().upper()
        market = (data.get("market") or "crypto").strip().lower()
        interval = data.get("interval", "15m").strip()
        strategy_id = data.get("strategy_id", "")
        name = data.get("name", "Custom Strategy")

        # Validate the strategy code first
        from app.core.strategy_engine import parse_strategy, validate_strategy
        parsed = parse_strategy(code)
        validation = validate_strategy(parsed)
        if not validation["valid"]:
            return jsonify({
                "ok": False,
                "error": "Strateji geçersiz: " + "; ".join(validation["errors"]),
            }), 400

        from app.core.strategy_live_engine import activate_strategy
        result = activate_strategy(
            user_id=user_id,
            strategy_id=strategy_id,
            strategy_name=name or parsed.get("name", "Strategy"),
            code=code,
            symbol=symbol,
            market=market,
            interval=interval,
        )
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/deactivate", methods=["POST"])
def api_live_deactivate():
    """Deactivate a live strategy.

    Body JSON:
      activation_id — ID of the activation to deactivate
    """
    try:
        data = request.get_json(force=True) or {}
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        activation_id = (data.get("activation_id") or "").strip()
        if not activation_id:
            return jsonify({"ok": False, "error": "activation_id gerekli"}), 400

        from app.core.strategy_live_engine import deactivate_strategy
        result = deactivate_strategy(activation_id, user_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/toggle", methods=["POST"])
def api_live_toggle():
    """Toggle live strategy enabled state.

    Body JSON:
      activation_id — ID of the activation to toggle
    """
    try:
        data = request.get_json(force=True) or {}
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        activation_id = (data.get("activation_id") or "").strip()
        if not activation_id:
            return jsonify({"ok": False, "error": "activation_id gerekli"}), 400

        from app.core.strategy_live_engine import toggle_strategy
        result = toggle_strategy(activation_id, user_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/remove", methods=["POST"])
def api_live_remove():
    """Remove a live strategy activation permanently.

    Body JSON:
      activation_id — ID of the activation to remove
    """
    try:
        data = request.get_json(force=True) or {}
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        activation_id = (data.get("activation_id") or "").strip()
        if not activation_id:
            return jsonify({"ok": False, "error": "activation_id gerekli"}), 400

        from app.core.strategy_live_engine import remove_strategy
        result = remove_strategy(activation_id, user_id)
        return jsonify(result)
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/active", methods=["GET"])
def api_live_active():
    """List active strategies for the current user."""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        from app.core.strategy_live_engine import get_active_strategies
        strategies = get_active_strategies(user_id)
        return jsonify({"ok": True, "strategies": strategies})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/signals", methods=["GET"])
def api_live_signals():
    """Get recent live signals for the current user."""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        limit = min(int(request.args.get("limit", "50")), 200)

        from app.core.strategy_live_engine import get_live_signals
        signals = get_live_signals(user_id, limit)
        return jsonify({"ok": True, "signals": signals, "count": len(signals)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/stats", methods=["GET"])
def api_live_stats():
    """Get live engine statistics."""
    try:
        from app.core.strategy_live_engine import live_engine
        stats = live_engine.get_stats()
        return jsonify({"ok": True, "stats": stats})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@strategy_bp.route("/live/clear", methods=["POST"])
def api_live_clear():
    """Clear signal history for the current user."""
    try:
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"ok": False, "error": "Giriş yapmanız gerekiyor"}), 401

        from app.core.strategy_live_engine import clear_signals
        count = clear_signals(user_id)
        return jsonify({"ok": True, "cleared": count})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── Strategy Signals Page ────────────────────────────────────────
@strategy_bp.route("/signals-page", methods=["GET"])
def strategy_signals_page():
    """Render the strategy live signals page."""
    return render_template("strategy_signals.html")
