# -*- coding: utf-8 -*-
"""Simulator Engine — FAZ 57.

Advanced trading simulator with order types, order book simulation,
and PnL calculation. Wraps paper_trading_engine for core operations.

Features:
  - Market / Limit / Stop-Limit orders
  - Simulated order book (bid/ask ladder)
  - PnL calculation helpers
  - Order management (pending, filled, cancelled)
  - Balance tracking (equity, available, unrealized PnL)

Storage: SQLite (data/paper_trading.db) — extends existing tables
"""
from __future__ import annotations

import logging
import os
import random
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.simulator_engine")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "paper_trading.db")
_lock = threading.Lock()

ORDER_TYPES = ("market", "limit", "stop_limit")
ORDER_STATUSES = ("pending", "filled", "cancelled", "expired")


def _get_db() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    from app.core.db_manager import get_connection
    return get_connection("paper_trading.db")


def _init_orders_table():
    """Create orders table if it doesn't exist."""
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_orders (
                id           TEXT PRIMARY KEY,
                account_id   TEXT NOT NULL,
                symbol       TEXT NOT NULL,
                market       TEXT NOT NULL DEFAULT 'crypto',
                side         TEXT NOT NULL DEFAULT 'buy',
                order_type   TEXT NOT NULL DEFAULT 'market',
                quantity     REAL NOT NULL,
                price        REAL DEFAULT NULL,
                stop_price   REAL DEFAULT NULL,
                limit_price  REAL DEFAULT NULL,
                filled_price REAL DEFAULT NULL,
                status       TEXT NOT NULL DEFAULT 'pending',
                position_id  TEXT DEFAULT NULL,
                created_at   TEXT NOT NULL,
                filled_at    TEXT DEFAULT NULL,
                cancelled_at TEXT DEFAULT NULL,
                user_id      TEXT NOT NULL DEFAULT 'default',
                FOREIGN KEY (account_id) REFERENCES paper_accounts(id)
            );
            CREATE INDEX IF NOT EXISTS idx_orders_status
                ON paper_orders(status);
            CREATE INDEX IF NOT EXISTS idx_orders_user
                ON paper_orders(user_id);
        """)
        conn.commit()
    except Exception as e:
        _logger.warning("Orders table init: %s", e)
    finally:
        conn.close()


_init_orders_table()


# ══════════════════════════════════════════════════════════════════════
# PRICE HELPERS
# ══════════════════════════════════════════════════════════════════════

def get_current_price(symbol: str, market: str = "crypto") -> Optional[float]:
    """Fetch current price — delegates to paper_trading_engine."""
    from app.core.paper_trading_engine import fetch_current_price
    return fetch_current_price(symbol, market)


def calculate_pnl(entry_price: float, current_price: float,
                  quantity: float, side: str) -> Dict:
    """Calculate PnL for a position.

    Returns dict with pnl_abs, pnl_pct, pnl_usdt.
    """
    if entry_price <= 0:
        return {"pnl_abs": 0, "pnl_pct": 0, "pnl_usdt": 0}

    if side == "buy":
        pnl_abs = (current_price - entry_price) * quantity
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
    else:  # sell (short)
        pnl_abs = (entry_price - current_price) * quantity
        pnl_pct = ((entry_price - current_price) / entry_price) * 100

    return {
        "pnl_abs": round(pnl_abs, 4),
        "pnl_pct": round(pnl_pct, 4),
        "pnl_usdt": round(pnl_abs, 2),
    }


# ══════════════════════════════════════════════════════════════════════
# ORDER MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

def place_order(
    symbol: str,
    market: str,
    side: str,
    order_type: str,
    quantity: float,
    price: Optional[float] = None,
    stop_price: Optional[float] = None,
    user_id: str = "default",
) -> Dict:
    """Place a new order.

    For market orders: executes immediately via paper_trading_engine.
    For limit/stop_limit: creates pending order.
    """
    from app.core.paper_trading_engine import (
        get_account, open_position, TRADE_FEE_RATE
    )

    symbol = symbol.strip().upper()
    market = market.strip().lower()
    side = side.strip().lower()
    order_type = order_type.strip().lower()

    if side not in ("buy", "sell"):
        raise ValueError("side 'buy' veya 'sell' olmalı")
    if order_type not in ORDER_TYPES:
        raise ValueError(f"Geçersiz emir tipi: {order_type}")
    if quantity <= 0:
        raise ValueError("Miktar pozitif olmalı")

    # Market order — execute immediately
    if order_type == "market":
        result = open_position(symbol, market, side, quantity, user_id=user_id)
        # Record the order as filled immediately
        _record_order(
            symbol=symbol, market=market, side=side,
            order_type="market", quantity=quantity,
            filled_price=result["entry_price"],
            status="filled", position_id=result["id"],
            user_id=user_id,
        )
        return {
            "order_type": "market",
            "status": "filled",
            "position": result,
            "message": f"{'Long açıldı' if side == 'buy' else 'Short açıldı'}: {symbol}",
        }

    # Limit or Stop-Limit — validate price
    if order_type == "limit":
        if price is None or price <= 0:
            raise ValueError("Limit emri için fiyat gerekli")
    elif order_type == "stop_limit":
        if stop_price is None or stop_price <= 0:
            raise ValueError("Stop-Limit emri için stop fiyat gerekli")
        if price is None or price <= 0:
            raise ValueError("Stop-Limit emri için limit fiyat gerekli")

    # Check balance for pending order
    current_price = get_current_price(symbol, market)
    if current_price is None:
        raise ValueError(f"Fiyat alınamadı: {symbol}")

    est_price = price or stop_price or current_price
    est_notional = est_price * quantity
    est_fee = est_notional * TRADE_FEE_RATE
    est_cost = est_notional + est_fee

    account = get_account(user_id=user_id)
    if est_cost > account["current_balance"]:
        raise ValueError(
            f"Yetersiz bakiye. Tahmini maliyet: ${est_cost:,.2f}, "
            f"Mevcut: ${account['current_balance']:,.2f}"
        )

    # Create pending order
    order = _record_order(
        symbol=symbol, market=market, side=side,
        order_type=order_type, quantity=quantity,
        price=price, stop_price=stop_price,
        limit_price=price,
        status="pending", user_id=user_id,
    )

    type_label = "Limit" if order_type == "limit" else "Stop-Limit"
    return {
        "order_type": order_type,
        "status": "pending",
        "order": order,
        "message": f"{type_label} emir oluşturuldu: {symbol} @ ${price:,.2f}",
    }


def _record_order(
    symbol: str, market: str, side: str, order_type: str,
    quantity: float, price: Optional[float] = None,
    stop_price: Optional[float] = None,
    limit_price: Optional[float] = None,
    filled_price: Optional[float] = None,
    status: str = "pending",
    position_id: Optional[str] = None,
    user_id: str = "default",
) -> Dict:
    """Record an order in the database."""
    from app.core.paper_trading_engine import get_account

    account = get_account(user_id=user_id)
    order_id = str(uuid.uuid4())[:8]
    now = datetime.now(timezone.utc).isoformat()

    filled_at = now if status == "filled" else None

    conn = _get_db()
    try:
        conn.execute(
            """INSERT INTO paper_orders
               (id, account_id, symbol, market, side, order_type, quantity,
                price, stop_price, limit_price, filled_price, status,
                position_id, created_at, filled_at, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, account["id"], symbol, market, side, order_type,
             quantity, price, stop_price, limit_price, filled_price,
             status, position_id, now, filled_at, user_id),
        )
        conn.commit()
        return {
            "id": order_id,
            "symbol": symbol,
            "market": market,
            "side": side,
            "order_type": order_type,
            "quantity": quantity,
            "price": price,
            "stop_price": stop_price,
            "limit_price": limit_price,
            "filled_price": filled_price,
            "status": status,
            "position_id": position_id,
            "created_at": now,
            "filled_at": filled_at,
        }
    finally:
        conn.close()


def cancel_order(order_id: str, user_id: str = "default") -> Dict:
    """Cancel a pending order."""
    with _lock:
        conn = _get_db()
        try:
            row = conn.execute(
                "SELECT * FROM paper_orders WHERE id = ? AND user_id = ? AND status = 'pending'",
                (order_id, user_id),
            ).fetchone()
            if not row:
                raise ValueError(f"Bekleyen emir bulunamadı: {order_id}")

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "UPDATE paper_orders SET status = 'cancelled', cancelled_at = ? WHERE id = ?",
                (now, order_id),
            )
            conn.commit()
            order = dict(row)
            order["status"] = "cancelled"
            order["cancelled_at"] = now
            return order
        finally:
            conn.close()


def list_orders(
    status: str = "all",
    user_id: str = "default",
    limit: int = 50,
) -> List[Dict]:
    """List orders with optional status filter."""
    from app.core.paper_trading_engine import get_account
    account = get_account(user_id=user_id)
    acc_id = account["id"]

    conn = _get_db()
    try:
        if status == "all":
            rows = conn.execute(
                """SELECT * FROM paper_orders WHERE account_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (acc_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM paper_orders WHERE account_id = ? AND status = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (acc_id, status, limit),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def check_pending_orders(user_id: str = "default") -> List[Dict]:
    """Check pending limit/stop-limit orders against current prices.

    If conditions are met, execute the order.
    Returns list of filled orders.
    """
    from app.core.paper_trading_engine import open_position

    pending = list_orders(status="pending", user_id=user_id)
    filled = []

    for order in pending:
        try:
            current_price = get_current_price(order["symbol"], order["market"])
            if current_price is None or current_price <= 0:
                continue

            should_fill = False

            if order["order_type"] == "limit":
                target = order["price"] or order["limit_price"]
                if target is None:
                    continue
                # Buy limit: fill when price <= target
                if order["side"] == "buy" and current_price <= target:
                    should_fill = True
                # Sell limit: fill when price >= target
                elif order["side"] == "sell" and current_price >= target:
                    should_fill = True

            elif order["order_type"] == "stop_limit":
                stop = order["stop_price"]
                limit_p = order["limit_price"] or order["price"]
                if stop is None or limit_p is None:
                    continue
                # Buy stop-limit: stop triggered when price >= stop, fill at limit
                if order["side"] == "buy" and current_price >= stop:
                    if current_price <= limit_p:
                        should_fill = True
                # Sell stop-limit: stop triggered when price <= stop, fill at limit
                elif order["side"] == "sell" and current_price <= stop:
                    if current_price >= limit_p:
                        should_fill = True

            if should_fill:
                result = open_position(
                    order["symbol"], order["market"],
                    order["side"], order["quantity"],
                    user_id=user_id,
                )
                now = datetime.now(timezone.utc).isoformat()
                conn = _get_db()
                try:
                    conn.execute(
                        """UPDATE paper_orders
                           SET status = 'filled', filled_price = ?,
                               filled_at = ?, position_id = ?
                           WHERE id = ?""",
                        (result["entry_price"], now, result["id"], order["id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()

                order["status"] = "filled"
                order["filled_price"] = result["entry_price"]
                order["filled_at"] = now
                order["position_id"] = result["id"]
                filled.append(order)

        except Exception as exc:
            _logger.warning("Order check failed %s: %s", order["id"], exc)

    return filled


# ══════════════════════════════════════════════════════════════════════
# ORDER BOOK SIMULATION
# ══════════════════════════════════════════════════════════════════════

def generate_order_book(
    symbol: str,
    market: str = "crypto",
    levels: int = 12,
) -> Dict:
    """Generate a simulated order book around the current price.

    Creates realistic-looking bid/ask ladder with:
    - Spread based on price level
    - Random but realistic quantities
    - Decreasing density away from mid price
    """
    price = get_current_price(symbol, market)
    if price is None or price <= 0:
        return {"bids": [], "asks": [], "spread": 0, "mid_price": 0}

    # Spread varies by price level and market
    if market == "crypto":
        spread_pct = 0.0002 if price > 1000 else 0.001  # tighter for BTC
    elif market == "forex":
        spread_pct = 0.0001
    else:
        spread_pct = 0.0005

    half_spread = price * spread_pct / 2
    best_bid = price - half_spread
    best_ask = price + half_spread

    # Generate bid levels (decreasing price)
    bids = []
    for i in range(levels):
        step = price * spread_pct * (0.5 + i * 0.3 + random.random() * 0.2)
        level_price = round(best_bid - step * i, _price_decimals(price))
        if level_price <= 0:
            break
        # Quantity: larger near the top, random variation
        base_qty = random.uniform(0.5, 5.0) if market == "crypto" else random.uniform(10, 500)
        qty = round(base_qty * (1 + random.random() * 2), 4)
        total = round(level_price * qty, 2)
        bids.append({
            "price": level_price,
            "quantity": qty,
            "total": total,
        })

    # Generate ask levels (increasing price)
    asks = []
    for i in range(levels):
        step = price * spread_pct * (0.5 + i * 0.3 + random.random() * 0.2)
        level_price = round(best_ask + step * i, _price_decimals(price))
        base_qty = random.uniform(0.5, 5.0) if market == "crypto" else random.uniform(10, 500)
        qty = round(base_qty * (1 + random.random() * 2), 4)
        total = round(level_price * qty, 2)
        asks.append({
            "price": level_price,
            "quantity": qty,
            "total": total,
        })

    spread = round(best_ask - best_bid, _price_decimals(price))
    spread_pct_val = round((spread / price) * 100, 4) if price > 0 else 0

    return {
        "symbol": symbol,
        "market": market,
        "bids": bids,
        "asks": asks,
        "spread": spread,
        "spread_pct": spread_pct_val,
        "mid_price": round(price, _price_decimals(price)),
        "best_bid": round(best_bid, _price_decimals(price)),
        "best_ask": round(best_ask, _price_decimals(price)),
    }


def _price_decimals(price: float) -> int:
    """Determine decimal places based on price level."""
    if price >= 10000:
        return 2
    elif price >= 1:
        return 2
    elif price >= 0.01:
        return 4
    else:
        return 6


# ══════════════════════════════════════════════════════════════════════
# ACCOUNT EXTENDED INFO
# ══════════════════════════════════════════════════════════════════════

def get_account_extended(user_id: str = "default") -> Dict:
    """Get extended account information with equity, available balance,
    unrealized/realized PnL breakdown.
    """
    from app.core.paper_trading_engine import (
        get_account, refresh_positions, list_positions
    )

    account = get_account(user_id=user_id)
    open_positions = refresh_positions(user_id=user_id)

    # Calculate unrealized PnL from open positions
    unrealized_pnl = sum(p.get("pnl_abs", 0) for p in open_positions)
    open_notional = sum(
        p.get("entry_price", 0) * p.get("quantity", 0) for p in open_positions
    )

    # Calculate realized PnL from closed positions
    conn = _get_db()
    try:
        closed = conn.execute(
            """SELECT COALESCE(SUM(pnl_abs), 0) as total_pnl
               FROM paper_positions WHERE status = 'closed'
               AND account_id = ?""",
            (account["id"],),
        ).fetchone()
        realized_pnl = float(closed["total_pnl"]) if closed else 0
    finally:
        conn.close()

    balance = account["current_balance"]
    starting = account["starting_balance"]
    equity = balance + unrealized_pnl
    available = balance  # Available for new orders

    # Count pending orders and reserve estimated cost
    pending = list_orders(status="pending", user_id=user_id)
    pending_reserved = 0
    for o in pending:
        est_price = o.get("price") or o.get("limit_price") or 0
        if est_price > 0:
            pending_reserved += est_price * o.get("quantity", 0) * 1.001

    available = max(0, available - pending_reserved)

    return {
        "balance": round(balance, 2),
        "equity": round(equity, 2),
        "available": round(available, 2),
        "starting_balance": round(starting, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "realized_pnl": round(realized_pnl, 2),
        "total_pnl": round(equity - starting, 2),
        "total_pnl_pct": round(((equity - starting) / starting) * 100, 2) if starting > 0 else 0,
        "open_notional": round(open_notional, 2),
        "pending_reserved": round(pending_reserved, 2),
        "open_positions": open_positions,
        "pending_orders_count": len(pending),
        "currency": account.get("currency", "USD"),
    }


def clear_orders(user_id: str = "default"):
    """Clear all orders for a user (used in account reset)."""
    from app.core.paper_trading_engine import get_account
    account = get_account(user_id=user_id)
    conn = _get_db()
    try:
        conn.execute(
            "DELETE FROM paper_orders WHERE account_id = ?",
            (account["id"],),
        )
        conn.commit()
    finally:
        conn.close()
