# -*- coding: utf-8 -*-
"""Paper Trading Engine — FAZ 22.

Simülatör / Paper Trading sistemi.
Sanal bakiye ile deneme işlemleri.
Gerçek market fiyatları kullanılır, gerçek emir gönderilmez.

Storage: SQLite (data/paper_trading.db)
Models : PaperAccount, PaperPosition, PaperTrade

Public API:
  create_account(name, starting_balance, currency)
  get_account()
  reset_account()
  open_position(symbol, market, side, quantity)
  close_position(position_id)
  list_positions(status)
  list_trades(limit)
  refresh_positions()
  portfolio_summary()
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.paper_trading")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "paper_trading.db")

DEFAULT_BALANCE = 100_000.0
DEFAULT_CURRENCY = "USD"
TRADE_FEE_RATE = 0.001  # 0.1 % per trade

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════
# DATABASE INIT
# ══════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    """Get a thread-local SQLite connection."""
    from app.core.db_manager import get_connection
    return get_connection("paper_trading.db")


def _init_db():
    """Create tables if they don't exist."""
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS paper_accounts (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL DEFAULT 'Simülatör Hesabı',
                starting_balance REAL NOT NULL DEFAULT 100000.0,
                current_balance  REAL NOT NULL DEFAULT 100000.0,
                currency    TEXT NOT NULL DEFAULT 'USD',
                created_at  TEXT NOT NULL,
                resettable  INTEGER NOT NULL DEFAULT 1,
                user_id     TEXT NOT NULL DEFAULT 'default'
            );

            CREATE TABLE IF NOT EXISTS paper_positions (
                id          TEXT PRIMARY KEY,
                account_id  TEXT NOT NULL,
                symbol      TEXT NOT NULL,
                market      TEXT NOT NULL DEFAULT 'crypto',
                side        TEXT NOT NULL DEFAULT 'buy',
                quantity    REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL DEFAULT 0,
                pnl_abs     REAL DEFAULT 0,
                pnl_pct     REAL DEFAULT 0,
                opened_at   TEXT NOT NULL,
                closed_at   TEXT,
                status      TEXT NOT NULL DEFAULT 'open',
                FOREIGN KEY (account_id) REFERENCES paper_accounts(id)
            );

            CREATE TABLE IF NOT EXISTS paper_trades (
                id          TEXT PRIMARY KEY,
                account_id  TEXT NOT NULL,
                position_id TEXT,
                symbol      TEXT NOT NULL,
                market      TEXT NOT NULL DEFAULT 'crypto',
                side        TEXT NOT NULL,
                quantity    REAL NOT NULL,
                price       REAL NOT NULL,
                notional    REAL NOT NULL,
                fee         REAL NOT NULL DEFAULT 0,
                executed_at TEXT NOT NULL,
                note        TEXT DEFAULT '',
                FOREIGN KEY (account_id) REFERENCES paper_accounts(id)
            );

            CREATE INDEX IF NOT EXISTS idx_positions_status
                ON paper_positions(status);
            CREATE INDEX IF NOT EXISTS idx_positions_account
                ON paper_positions(account_id);
            CREATE INDEX IF NOT EXISTS idx_trades_account
                ON paper_trades(account_id);
        """)
        conn.commit()
        # Migration: add user_id column to existing tables
        try:
            conn.execute("ALTER TABLE paper_accounts ADD COLUMN user_id TEXT NOT NULL DEFAULT 'default'")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists
    finally:
        conn.close()


# Init DB on module load
_init_db()


# ══════════════════════════════════════════════════════════════════════
# PRICE FETCHING (real market prices)
# ══════════════════════════════════════════════════════════════════════

def fetch_current_price(symbol: str, market: str = "crypto") -> Optional[float]:
    """Fetch current market price from live endpoints.
    No mock data — uses Binance for crypto, Yahoo for others.
    """
    try:
        if market == "crypto":
            from app.core.binance_client import binance_klines
            df = binance_klines(symbol, interval="1m", limit=1)
            if not df.empty:
                return float(df.iloc[-1]["close"])
        else:
            from app.core.yahoo_client import get_ticker
            ticker = get_ticker(symbol)
            price = ticker.get("lastPrice", 0)
            if price and float(price) > 0:
                return float(price)
    except Exception as exc:
        _logger.warning("Price fetch failed %s/%s: %s", symbol, market, exc)

    # Fallback: try Binance API directly
    try:
        import requests
        r = requests.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": symbol}, timeout=5
        )
        if r.status_code == 200:
            return float(r.json().get("price", 0))
    except Exception:
        pass

    return None


# ══════════════════════════════════════════════════════════════════════
# ACCOUNT MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

def create_account(
    name: str = "Simülatör Hesabı",
    starting_balance: float = DEFAULT_BALANCE,
    currency: str = DEFAULT_CURRENCY,
    user_id: str = "default",
) -> Dict:
    """Create a new paper trading account (or return existing for user)."""
    with _lock:
        conn = _get_db()
        try:
            row = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
            if row:
                return dict(row)

            account_id = str(uuid.uuid4())[:8]
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """INSERT INTO paper_accounts
                   (id, name, starting_balance, current_balance, currency, created_at, user_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (account_id, name, starting_balance, starting_balance, currency, now, user_id),
            )
            conn.commit()
            return {
                "id": account_id,
                "name": name,
                "starting_balance": starting_balance,
                "current_balance": starting_balance,
                "currency": currency,
                "created_at": now,
                "resettable": 1,
                "user_id": user_id,
            }
        finally:
            conn.close()


def get_account(user_id: str = "default") -> Dict:
    """Get the paper trading account (auto-creates if none)."""
    conn = _get_db()
    try:
        row = conn.execute(
            "SELECT * FROM paper_accounts WHERE user_id = ? LIMIT 1",
            (user_id,),
        ).fetchone()
        if row:
            return dict(row)
    finally:
        conn.close()
    return create_account(user_id=user_id)


def reset_account(user_id: str = "default") -> Dict:
    """Reset account — close all positions, delete trades, reset balance."""
    with _lock:
        conn = _get_db()
        try:
            account = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
            if not account:
                conn.close()
                return create_account(user_id=user_id)

            account = dict(account)
            acc_id = account["id"]
            starting = account["starting_balance"]

            conn.execute(
                "UPDATE paper_accounts SET current_balance = ? WHERE id = ?",
                (starting, acc_id),
            )
            conn.execute(
                "DELETE FROM paper_positions WHERE account_id = ?", (acc_id,)
            )
            conn.execute(
                "DELETE FROM paper_trades WHERE account_id = ?", (acc_id,)
            )
            conn.commit()

            account["current_balance"] = starting
            return account
        finally:
            conn.close()


# ══════════════════════════════════════════════════════════════════════
# POSITION MANAGEMENT
# ══════════════════════════════════════════════════════════════════════

def open_position(
    symbol: str,
    market: str = "crypto",
    side: str = "buy",
    quantity: float = 0,
    user_id: str = "default",
) -> Dict:
    """Open a new paper position.

    Validates:
      - symbol and quantity
      - current market price available
      - sufficient balance
    Deducts notional + fee from balance.
    """
    symbol = symbol.strip().upper()
    market = market.strip().lower()
    side = side.strip().lower()
    if side not in ("buy", "sell"):
        raise ValueError("side must be 'buy' or 'sell'")
    if quantity <= 0:
        raise ValueError("quantity must be positive")

    # Fetch real market price
    price = fetch_current_price(symbol, market)
    if price is None or price <= 0:
        raise ValueError(f"Cannot fetch price for {symbol} ({market})")

    notional = price * quantity
    fee = notional * TRADE_FEE_RATE

    with _lock:
        conn = _get_db()
        try:
            account = conn.execute(
                "SELECT * FROM paper_accounts WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
            if not account:
                conn.close()
                account = create_account(user_id=user_id)
                conn = _get_db()
                account = conn.execute(
                    "SELECT * FROM paper_accounts WHERE user_id = ? LIMIT 1",
                    (user_id,),
                ).fetchone()

            account = dict(account)
            balance = account["current_balance"]
            total_cost = notional + fee

            if total_cost > balance:
                raise ValueError(
                    f"Yetersiz bakiye. Gerekli: ${total_cost:,.2f}, "
                    f"Mevcut: ${balance:,.2f}"
                )

            # Create position
            pos_id = str(uuid.uuid4())[:8]
            now = datetime.now(timezone.utc).isoformat()

            conn.execute(
                """INSERT INTO paper_positions
                   (id, account_id, symbol, market, side, quantity,
                    entry_price, current_price, pnl_abs, pnl_pct,
                    opened_at, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'open')""",
                (pos_id, account["id"], symbol, market, side, quantity,
                 price, price, now),
            )

            # Record trade
            trade_id = str(uuid.uuid4())[:8]
            conn.execute(
                """INSERT INTO paper_trades
                   (id, account_id, position_id, symbol, market, side,
                    quantity, price, notional, fee, executed_at, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trade_id, account["id"], pos_id, symbol, market, side,
                 quantity, price, notional, fee, now,
                 f"Pozisyon açıldı: {side.upper()} {quantity} {symbol} @ ${price:,.2f}"),
            )

            # Deduct from balance
            new_balance = balance - total_cost
            conn.execute(
                "UPDATE paper_accounts SET current_balance = ? WHERE id = ?",
                (new_balance, account["id"]),
            )
            conn.commit()

            return {
                "id": pos_id,
                "symbol": symbol,
                "market": market,
                "side": side,
                "quantity": quantity,
                "entry_price": price,
                "current_price": price,
                "pnl_abs": 0.0,
                "pnl_pct": 0.0,
                "opened_at": now,
                "status": "open",
                "notional": notional,
                "fee": fee,
                "new_balance": new_balance,
            }
        finally:
            conn.close()


def close_position(position_id: str) -> Dict:
    """Close an open paper position.

    Fetches current price, calculates PnL, credits balance.
    """
    with _lock:
        conn = _get_db()
        try:
            pos = conn.execute(
                "SELECT * FROM paper_positions WHERE id = ? AND status = 'open'",
                (position_id,),
            ).fetchone()
            if not pos:
                raise ValueError(f"Open position not found: {position_id}")

            pos = dict(pos)
            symbol = pos["symbol"]
            market = pos["market"]
            side = pos["side"]
            quantity = pos["quantity"]
            entry_price = pos["entry_price"]

            # Fetch current price
            current_price = fetch_current_price(symbol, market)
            if current_price is None or current_price <= 0:
                raise ValueError(f"Cannot fetch price for {symbol}")

            # Calculate PnL
            if side == "buy":
                pnl_abs = (current_price - entry_price) * quantity
            else:  # sell (short simulation)
                pnl_abs = (entry_price - current_price) * quantity

            pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
            if side == "sell":
                pnl_pct = -pnl_pct

            notional_close = current_price * quantity
            fee = notional_close * TRADE_FEE_RATE
            now = datetime.now(timezone.utc).isoformat()

            # Update position
            conn.execute(
                """UPDATE paper_positions
                   SET current_price = ?, pnl_abs = ?, pnl_pct = ?,
                       closed_at = ?, status = 'closed'
                   WHERE id = ?""",
                (current_price, pnl_abs, pnl_pct, now, position_id),
            )

            # Record closing trade
            account = conn.execute(
                "SELECT * FROM paper_accounts LIMIT 1"
            ).fetchone()
            account = dict(account)

            trade_id = str(uuid.uuid4())[:8]
            close_side = "sell" if side == "buy" else "buy"
            conn.execute(
                """INSERT INTO paper_trades
                   (id, account_id, position_id, symbol, market, side,
                    quantity, price, notional, fee, executed_at, note)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (trade_id, account["id"], position_id, symbol, market,
                 close_side, quantity, current_price, notional_close, fee, now,
                 f"Pozisyon kapatıldı: PnL ${pnl_abs:+,.2f} ({pnl_pct:+.2f}%)"),
            )

            # Credit balance: return notional + pnl - fee
            credit = notional_close - fee
            new_balance = account["current_balance"] + credit
            conn.execute(
                "UPDATE paper_accounts SET current_balance = ? WHERE id = ?",
                (new_balance, account["id"]),
            )
            conn.commit()

            return {
                "id": position_id,
                "symbol": symbol,
                "market": market,
                "side": side,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current_price,
                "pnl_abs": round(pnl_abs, 2),
                "pnl_pct": round(pnl_pct, 2),
                "opened_at": pos["opened_at"],
                "closed_at": now,
                "status": "closed",
                "fee": fee,
                "new_balance": round(new_balance, 2),
            }
        finally:
            conn.close()


def list_positions(status: str = "all", user_id: str = "default") -> List[Dict]:
    """List paper positions, optionally filtered by status."""
    account = get_account(user_id=user_id)
    acc_id = account["id"]
    conn = _get_db()
    try:
        if status == "all":
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE account_id = ? ORDER BY opened_at DESC",
                (acc_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM paper_positions WHERE account_id = ? AND status = ? ORDER BY opened_at DESC",
                (acc_id, status),
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def list_trades(limit: int = 50, user_id: str = "default") -> List[Dict]:
    """List recent paper trades."""
    account = get_account(user_id=user_id)
    acc_id = account["id"]
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM paper_trades WHERE account_id = ? ORDER BY executed_at DESC LIMIT ?",
            (acc_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def refresh_positions(user_id: str = "default") -> List[Dict]:
    """Refresh current prices and PnL for all open positions."""
    account = get_account(user_id=user_id)
    acc_id = account["id"]
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM paper_positions WHERE status = 'open' AND account_id = ?",
            (acc_id,),
        ).fetchall()
        updated = []
        for row in rows:
            pos = dict(row)
            try:
                price = fetch_current_price(pos["symbol"], pos["market"])
                if price and price > 0:
                    entry = pos["entry_price"]
                    qty = pos["quantity"]
                    side = pos["side"]

                    if side == "buy":
                        pnl_abs = (price - entry) * qty
                    else:
                        pnl_abs = (entry - price) * qty

                    pnl_pct = ((price - entry) / entry * 100) if entry > 0 else 0
                    if side == "sell":
                        pnl_pct = -pnl_pct

                    conn.execute(
                        """UPDATE paper_positions
                           SET current_price = ?, pnl_abs = ?, pnl_pct = ?
                           WHERE id = ?""",
                        (price, round(pnl_abs, 4), round(pnl_pct, 4), pos["id"]),
                    )
                    pos["current_price"] = price
                    pos["pnl_abs"] = round(pnl_abs, 2)
                    pos["pnl_pct"] = round(pnl_pct, 2)
            except Exception as exc:
                _logger.warning("Refresh failed for %s: %s", pos["symbol"], exc)
            updated.append(pos)
        conn.commit()
        return updated
    finally:
        conn.close()


def portfolio_summary(user_id: str = "default") -> Dict:
    """Generate portfolio summary with total PnL, positions overview."""
    account = get_account(user_id=user_id)
    positions = refresh_positions(user_id=user_id)

    open_positions = [p for p in positions if p["status"] == "open"]

    conn = _get_db()
    try:
        closed_rows = conn.execute(
            """SELECT COUNT(*) as cnt, COALESCE(SUM(pnl_abs), 0) as total_pnl
               FROM paper_positions WHERE status = 'closed'
               AND account_id = ?""",
            (account["id"],),
        ).fetchone()
        trade_count = conn.execute(
            "SELECT COUNT(*) as cnt FROM paper_trades WHERE account_id = ?",
            (account["id"],),
        ).fetchone()
    finally:
        conn.close()

    total_open_pnl = sum(p.get("pnl_abs", 0) for p in open_positions)
    total_open_notional = sum(
        p.get("entry_price", 0) * p.get("quantity", 0) for p in open_positions
    )
    closed_pnl = float(closed_rows["total_pnl"]) if closed_rows else 0

    starting = account["starting_balance"]
    current = account["current_balance"]
    total_pnl = current - starting + total_open_pnl

    return {
        "account": {
            "id": account["id"],
            "name": account["name"],
            "starting_balance": starting,
            "current_balance": round(current, 2),
            "currency": account["currency"],
            "created_at": account["created_at"],
        },
        "open_positions_count": len(open_positions),
        "open_positions": open_positions,
        "total_open_pnl": round(total_open_pnl, 2),
        "total_open_notional": round(total_open_notional, 2),
        "closed_trades_count": int(closed_rows["cnt"]) if closed_rows else 0,
        "closed_pnl": round(closed_pnl, 2),
        "total_trade_count": int(trade_count["cnt"]) if trade_count else 0,
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round((total_pnl / starting * 100), 2) if starting > 0 else 0,
    }
