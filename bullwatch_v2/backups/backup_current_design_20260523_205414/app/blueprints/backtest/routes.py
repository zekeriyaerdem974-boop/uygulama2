# -*- coding: utf-8 -*-
"""Backtest API routes — FAZ 23.

Endpoints:
  GET  /api/backtest/strategies  — List available strategies
  GET  /api/backtest/run         — Run a backtest
"""
from flask import jsonify, request

from app.blueprints.backtest import backtest_bp


@backtest_bp.route("/strategies", methods=["GET"])
def api_list_strategies():
    """Return list of available backtesting strategies."""
    try:
        from app.core.strategies import list_strategies
        strategies = list_strategies()
        return jsonify({"ok": True, "strategies": strategies})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@backtest_bp.route("/run", methods=["GET"])
def api_run_backtest():
    """Run a backtest.

    Query params:
      symbol    — e.g. BTCUSDT (required)
      strategy  — e.g. ema_cross (default: ema_cross)
      market    — e.g. crypto (default: crypto)
      interval  — e.g. 1d (default: 1d)
      limit     — e.g. 500 (default: 500)
    """
    try:
        symbol = (request.args.get("symbol") or "").strip().upper()
        if not symbol:
            return jsonify({"ok": False, "error": "symbol parametresi gerekli"}), 400

        strategy = request.args.get("strategy", "ema_cross").strip().lower()
        market = request.args.get("market", "crypto").strip().lower()
        interval = request.args.get("interval", "1d").strip()
        limit = request.args.get("limit", 500, type=int)

        from app.core.backtest_engine import run_backtest
        result = run_backtest(
            symbol=symbol,
            market=market,
            strategy_id=strategy,
            interval=interval,
            limit=limit,
        )

        return jsonify(result)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
