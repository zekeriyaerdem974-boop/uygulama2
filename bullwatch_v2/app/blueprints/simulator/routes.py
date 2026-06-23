# -*- coding: utf-8 -*-
"""Simulator API routes — FAZ 22 + FAZ 57.

Endpoints:
  GET  /api/simulator/account        – Get account info
  GET  /api/simulator/account/extended – Extended account with equity/PnL
  POST /api/simulator/account/reset  – Reset account
  GET  /api/simulator/positions      – List positions
  GET  /api/simulator/trades         – List trades
  GET  /api/simulator/summary        – Portfolio summary
  POST /api/simulator/buy            – Open buy position (market)
  POST /api/simulator/sell           – Open sell position (market)
  POST /api/simulator/order          – Place any order type
  GET  /api/simulator/orders         – List orders
  POST /api/simulator/order/<id>/cancel – Cancel pending order
  POST /api/simulator/close/<id>     – Close a position
  GET  /api/simulator/price          – Get live price
  GET  /api/simulator/orderbook      – Simulated order book
  POST /api/simulator/check-orders   – Check & fill pending orders
"""
from flask import jsonify, request, session

from app.blueprints.simulator import simulator_bp


def _get_user_id():
    """Get current user_id from session or default."""
    return session.get("user_id", "default")


@simulator_bp.route("/account", methods=["GET"])
def api_get_account():
    """Return paper trading account info."""
    try:
        from app.core.paper_trading_engine import get_account
        account = get_account(user_id=_get_user_id())
        return jsonify({"ok": True, "account": account})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/account/reset", methods=["POST"])
def api_reset_account():
    """Reset account to starting balance, clear all positions, trades, and orders."""
    try:
        from app.core.paper_trading_engine import reset_account
        from app.core.simulator_engine import clear_orders
        account = reset_account(user_id=_get_user_id())
        clear_orders(user_id=_get_user_id())
        return jsonify({"ok": True, "account": account, "message": "Hesap sıfırlandı"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/positions", methods=["GET"])
def api_list_positions():
    """List positions. Query param: ?status=open|closed|all (default: all)."""
    try:
        from app.core.paper_trading_engine import list_positions
        status = request.args.get("status", "all")
        positions = list_positions(status, user_id=_get_user_id())
        return jsonify({"ok": True, "positions": positions, "count": len(positions)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/trades", methods=["GET"])
def api_list_trades():
    """List recent trades. Query param: ?limit=50."""
    try:
        from app.core.paper_trading_engine import list_trades
        limit = request.args.get("limit", 50, type=int)
        trades = list_trades(limit, user_id=_get_user_id())
        return jsonify({"ok": True, "trades": trades, "count": len(trades)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/summary", methods=["GET"])
def api_portfolio_summary():
    """Get portfolio summary with total PnL, open positions, etc."""
    try:
        from app.core.paper_trading_engine import portfolio_summary
        summary = portfolio_summary(user_id=_get_user_id())
        return jsonify({"ok": True, **summary})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/buy", methods=["POST"])
def api_buy():
    """Open a buy (long) position.
    Body: { symbol, market?, quantity }
    """
    try:
        from app.core.paper_trading_engine import open_position
        data = request.get_json(force=True)
        symbol = data.get("symbol", "").strip().upper()
        market = data.get("market", "crypto").strip().lower()
        quantity = float(data.get("quantity", 0))

        if not symbol:
            return jsonify({"ok": False, "error": "symbol gerekli"}), 400
        if quantity <= 0:
            return jsonify({"ok": False, "error": "quantity > 0 olmalı"}), 400

        result = open_position(symbol, market, "buy", quantity, user_id=_get_user_id())
        return jsonify({"ok": True, "position": result, "message": f"✅ {symbol} alındı"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/sell", methods=["POST"])
def api_sell():
    """Open a sell (short) position.
    Body: { symbol, market?, quantity }
    """
    try:
        from app.core.paper_trading_engine import open_position
        data = request.get_json(force=True)
        symbol = data.get("symbol", "").strip().upper()
        market = data.get("market", "crypto").strip().lower()
        quantity = float(data.get("quantity", 0))

        if not symbol:
            return jsonify({"ok": False, "error": "symbol gerekli"}), 400
        if quantity <= 0:
            return jsonify({"ok": False, "error": "quantity > 0 olmalı"}), 400

        result = open_position(symbol, market, "sell", quantity, user_id=_get_user_id())
        return jsonify({"ok": True, "position": result, "message": f"✅ {symbol} satıldı (short)"})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/close/<position_id>", methods=["POST"])
def api_close_position(position_id):
    """Close an open position by id."""
    try:
        from app.core.paper_trading_engine import close_position
        result = close_position(position_id)
        pnl = result.get("pnl_abs", 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        return jsonify({
            "ok": True,
            "position": result,
            "message": f"{emoji} Pozisyon kapatıldı — PnL: ${pnl:+,.2f}",
        })
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/price", methods=["GET"])
def api_get_price():
    """Get live price for any symbol/market combo.

    Query params: ?symbol=BTCUSDT&market=crypto
    Uses the same fetch_current_price() that the engine uses for trades.
    """
    try:
        from app.core.paper_trading_engine import fetch_current_price
        symbol = request.args.get("symbol", "").strip().upper()
        market = request.args.get("market", "crypto").strip().lower()
        if not symbol:
            return jsonify({"ok": False, "error": "symbol gerekli"}), 400
        price = fetch_current_price(symbol, market)
        if price is None or price <= 0:
            return jsonify({"ok": False, "error": f"Fiyat alınamadı: {symbol}", "price": None})
        return jsonify({"ok": True, "symbol": symbol, "market": market, "price": round(price, 6)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ══════════════════════════════════════════════════════════════════════
# FAZ 57 — Advanced Simulator Endpoints
# ══════════════════════════════════════════════════════════════════════

@simulator_bp.route("/account/extended", methods=["GET"])
def api_get_account_extended():
    """Extended account info with equity, available balance, PnL breakdown."""
    try:
        from app.core.simulator_engine import get_account_extended
        data = get_account_extended(user_id=_get_user_id())
        return jsonify({"ok": True, **data})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/order", methods=["POST"])
def api_place_order():
    """Place an order (market, limit, or stop_limit).

    Body: { symbol, market?, side, order_type, quantity, price?, stop_price? }
    """
    try:
        from app.core.simulator_engine import place_order
        data = request.get_json(force=True)
        symbol = data.get("symbol", "").strip().upper()
        market = data.get("market", "crypto").strip().lower()
        side = data.get("side", "").strip().lower()
        order_type = data.get("order_type", "market").strip().lower()
        quantity = float(data.get("quantity", 0))
        price = data.get("price")
        stop_price = data.get("stop_price")

        if price is not None:
            price = float(price)
        if stop_price is not None:
            stop_price = float(stop_price)

        if not symbol:
            return jsonify({"ok": False, "error": "symbol gerekli"}), 400
        if not side:
            return jsonify({"ok": False, "error": "side gerekli"}), 400
        if quantity <= 0:
            return jsonify({"ok": False, "error": "quantity > 0 olmalı"}), 400

        result = place_order(
            symbol=symbol, market=market, side=side,
            order_type=order_type, quantity=quantity,
            price=price, stop_price=stop_price,
            user_id=_get_user_id(),
        )
        return jsonify({"ok": True, **result})
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/orders", methods=["GET"])
def api_list_orders():
    """List orders. Query param: ?status=pending|filled|cancelled|all."""
    try:
        from app.core.simulator_engine import list_orders
        status = request.args.get("status", "all")
        limit = request.args.get("limit", 50, type=int)
        orders = list_orders(status=status, user_id=_get_user_id(), limit=limit)
        return jsonify({"ok": True, "orders": orders, "count": len(orders)})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/order/<order_id>/cancel", methods=["POST"])
def api_cancel_order(order_id):
    """Cancel a pending order."""
    try:
        from app.core.simulator_engine import cancel_order
        result = cancel_order(order_id, user_id=_get_user_id())
        return jsonify({
            "ok": True,
            "order": result,
            "message": "Emir iptal edildi",
        })
    except ValueError as ve:
        return jsonify({"ok": False, "error": str(ve)}), 400
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/orderbook", methods=["GET"])
def api_orderbook():
    """Get simulated order book for a symbol.

    Query params: ?symbol=BTCUSDT&market=crypto&levels=12
    """
    try:
        from app.core.simulator_engine import generate_order_book
        symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
        market = request.args.get("market", "crypto").strip().lower()
        levels = request.args.get("levels", 12, type=int)
        levels = max(1, min(levels, 25))  # clamp
        book = generate_order_book(symbol, market, levels)
        return jsonify({"ok": True, **book})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@simulator_bp.route("/check-orders", methods=["POST"])
def api_check_orders():
    """Check pending orders against current prices and fill if conditions met."""
    try:
        from app.core.simulator_engine import check_pending_orders
        filled = check_pending_orders(user_id=_get_user_id())
        return jsonify({
            "ok": True,
            "filled": filled,
            "filled_count": len(filled),
        })
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
