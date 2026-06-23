# -*- coding: utf-8 -*-
"""Portfolio Engine — FAZ 39.

Kullanıcı portföy yönetimi: varlık ekleme/çıkarma, PnL hesaplama,
dağılım analizi, portföy özeti.

Storage: SQLite (data/portfolios.db)

Public API:
  get_or_create_portfolio(user_id)
  add_asset(user_id, symbol, market, amount, entry_price)
  remove_asset(user_id, symbol)
  update_asset_prices(user_id)
  calculate_pnl(user_id)
  calculate_allocation(user_id)
  portfolio_summary(user_id)
  get_assets(user_id)
"""
from __future__ import annotations

import logging
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.portfolio.engine")

# ── Configuration ─────────────────────────────────────────────────
_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "portfolios.db")
_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("portfolios.db")


def _init_db():
    conn = _get_db()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS portfolios (
                id          TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL UNIQUE,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS portfolio_assets (
                id            TEXT PRIMARY KEY,
                portfolio_id  TEXT NOT NULL,
                symbol        TEXT NOT NULL,
                market        TEXT NOT NULL DEFAULT 'crypto',
                amount        REAL NOT NULL,
                entry_price   REAL NOT NULL,
                current_price REAL DEFAULT 0,
                added_at      TEXT NOT NULL,
                FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_asset_symbol
                ON portfolio_assets(portfolio_id, symbol);
        """)
        conn.commit()
    finally:
        conn.close()


_init_db()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return uuid.uuid4().hex[:16]


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def get_or_create_portfolio(user_id: str) -> Dict:
    """Get existing portfolio or create a new one for user."""
    with _lock:
        conn = _get_db()
        try:
            row = conn.execute(
                "SELECT * FROM portfolios WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                return dict(row)
            pid = _gen_id()
            now = _now_iso()
            conn.execute(
                "INSERT INTO portfolios (id, user_id, created_at) VALUES (?, ?, ?)",
                (pid, user_id, now),
            )
            conn.commit()
            return {"id": pid, "user_id": user_id, "created_at": now}
        finally:
            conn.close()


def add_asset(
    user_id: str,
    symbol: str,
    market: str = "crypto",
    amount: float = 0.0,
    entry_price: float = 0.0,
) -> Dict:
    """Add or update an asset in the user's portfolio."""
    portfolio = get_or_create_portfolio(user_id)
    pid = portfolio["id"]
    symbol = symbol.upper().strip()

    if amount <= 0:
        raise ValueError("Miktar sıfırdan büyük olmalıdır")
    if entry_price <= 0:
        raise ValueError("Giriş fiyatı sıfırdan büyük olmalıdır")

    with _lock:
        conn = _get_db()
        try:
            existing = conn.execute(
                "SELECT * FROM portfolio_assets WHERE portfolio_id = ? AND symbol = ?",
                (pid, symbol),
            ).fetchone()

            if existing:
                # Update: weighted average entry price
                old_amount = existing["amount"]
                old_entry = existing["entry_price"]
                new_total = old_amount + amount
                avg_price = ((old_amount * old_entry) + (amount * entry_price)) / new_total
                conn.execute(
                    "UPDATE portfolio_assets SET amount = ?, entry_price = ? WHERE id = ?",
                    (new_total, avg_price, existing["id"]),
                )
                conn.commit()
                return {
                    "id": existing["id"],
                    "symbol": symbol,
                    "market": market,
                    "amount": new_total,
                    "entry_price": round(avg_price, 8),
                    "updated": True,
                }

            aid = _gen_id()
            now = _now_iso()
            conn.execute(
                """INSERT INTO portfolio_assets
                   (id, portfolio_id, symbol, market, amount, entry_price, current_price, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (aid, pid, symbol, market, amount, entry_price, entry_price, now),
            )
            conn.commit()
            return {
                "id": aid,
                "symbol": symbol,
                "market": market,
                "amount": amount,
                "entry_price": entry_price,
                "added_at": now,
            }
        finally:
            conn.close()


def remove_asset(user_id: str, symbol: str) -> bool:
    """Remove an asset from the user's portfolio."""
    portfolio = get_or_create_portfolio(user_id)
    symbol = symbol.upper().strip()
    with _lock:
        conn = _get_db()
        try:
            cur = conn.execute(
                "DELETE FROM portfolio_assets WHERE portfolio_id = ? AND symbol = ?",
                (portfolio["id"], symbol),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()


def get_assets(user_id: str) -> List[Dict]:
    """Get all assets in the user's portfolio."""
    portfolio = get_or_create_portfolio(user_id)
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM portfolio_assets WHERE portfolio_id = ? ORDER BY added_at",
            (portfolio["id"],),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_asset_prices(user_id: str) -> List[Dict]:
    """Update current prices for all assets using live market data.

    Uses the same data sources as the rest of the app:
    - Crypto: MarketDataService (Binance)
    - Stocks/BIST/Forex/Commodities: Yahoo client
    """
    assets = get_assets(user_id)
    if not assets:
        return assets

    updated = []
    conn = _get_db()
    try:
        for asset in assets:
            price = _fetch_live_price(asset["symbol"], asset["market"])
            if price and price > 0:
                conn.execute(
                    "UPDATE portfolio_assets SET current_price = ? WHERE id = ?",
                    (price, asset["id"]),
                )
                asset["current_price"] = price
            updated.append(asset)
        conn.commit()
    finally:
        conn.close()

    return updated


def calculate_pnl(user_id: str) -> Dict:
    """Calculate profit/loss for the portfolio."""
    assets = get_assets(user_id)
    total_cost = 0.0
    total_value = 0.0
    asset_pnls = []

    for a in assets:
        cost = a["amount"] * a["entry_price"]
        value = a["amount"] * (a["current_price"] or a["entry_price"])
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0.0

        total_cost += cost
        total_value += value
        asset_pnls.append({
            "symbol": a["symbol"],
            "market": a["market"],
            "amount": a["amount"],
            "entry_price": a["entry_price"],
            "current_price": a["current_price"] or a["entry_price"],
            "cost": round(cost, 2),
            "value": round(value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    return {
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
        "assets": sorted(asset_pnls, key=lambda x: x["value"], reverse=True),
    }


def calculate_allocation(user_id: str) -> Dict:
    """Calculate portfolio allocation percentages."""
    assets = get_assets(user_id)
    total_value = 0.0
    items = []

    for a in assets:
        value = a["amount"] * (a["current_price"] or a["entry_price"])
        total_value += value
        items.append({"symbol": a["symbol"], "market": a["market"], "value": value})

    allocations = []
    for item in items:
        pct = (item["value"] / total_value * 100) if total_value > 0 else 0.0
        allocations.append({
            "symbol": item["symbol"],
            "market": item["market"],
            "value": round(item["value"], 2),
            "allocation": round(pct, 1),
        })

    allocations.sort(key=lambda x: x["allocation"], reverse=True)
    return {
        "total_value": round(total_value, 2),
        "allocations": allocations,
    }


def portfolio_summary(user_id: str) -> Dict:
    """Full portfolio summary with PnL, allocation, and asset details."""
    update_asset_prices(user_id)
    pnl = calculate_pnl(user_id)
    alloc = calculate_allocation(user_id)

    # Market breakdown
    market_breakdown = {}
    for a in alloc["allocations"]:
        mkt = a["market"]
        market_breakdown[mkt] = market_breakdown.get(mkt, 0) + a["allocation"]

    return {
        "total_value": pnl["total_value"],
        "total_cost": pnl["total_cost"],
        "total_pnl": pnl["total_pnl"],
        "total_pnl_pct": pnl["total_pnl_pct"],
        "asset_count": len(pnl["assets"]),
        "allocation": {a["symbol"]: a["allocation"] for a in alloc["allocations"]},
        "market_breakdown": market_breakdown,
        "assets": pnl["assets"],
    }


# ══════════════════════════════════════════════════════════════════════
# PRICE FETCHING
# ══════════════════════════════════════════════════════════════════════

def _fetch_live_price(symbol: str, market: str) -> Optional[float]:
    """Fetch live price for a symbol from appropriate market source."""
    try:
        if market == "crypto":
            return _fetch_crypto_price(symbol)
        else:
            return _fetch_yahoo_price(symbol, market)
    except Exception as exc:
        _logger.warning("Price fetch failed for %s (%s): %s", symbol, market, exc)
        return None


def _fetch_crypto_price(symbol: str) -> Optional[float]:
    """Fetch crypto price from Binance via MarketDataService."""
    try:
        from flask import current_app
        md = current_app.extensions.get("market_data")
        if md:
            ticker = md.get_ticker_single(symbol)
            if ticker:
                return float(ticker.get("lastPrice", 0))
    except RuntimeError:
        pass
    # Fallback: direct HTTP
    try:
        import urllib.request
        import json
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        req = urllib.request.Request(url, headers={"User-Agent": "ZKR Analiz/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return float(data.get("price", 0))
    except Exception:
        return None


def _fetch_yahoo_price(symbol: str, market: str) -> Optional[float]:
    """Fetch price from Yahoo Finance via yahoo_client."""
    try:
        from app.core.yahoo_client import get_ticker
        data = get_ticker(symbol, market)
        if data:
            return float(data.get("lastPrice", 0))
    except Exception:
        return None
