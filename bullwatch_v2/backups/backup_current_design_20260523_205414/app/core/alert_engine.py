# -*- coding: utf-8 -*-
"""Alert Engine — FAZ 20.

In-memory alert management with real-time price/indicator checking.

Alert Model Fields:
    id, symbol, market, condition_type, condition_value,
    indicator, timeframe, created_at, active, triggered_at, trigger_price

Condition Types:
    price_above, price_below, rsi_above, rsi_below,
    ema_cross, breakout, volume_spike

Public API:
    create_alert(data) -> dict
    delete_alert(alert_id) -> bool
    get_alerts() -> list[dict]
    get_alert(alert_id) -> dict | None
    check_alerts() -> list[dict]   (returns newly triggered alerts)
    get_triggered() -> list[dict]  (returns recent triggered alerts)
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any

_logger = logging.getLogger("zkr_analiz.alert_engine")

# ── In-memory store ────────────────────────────────────────────────
_lock = threading.Lock()
_alerts: dict[str, dict] = {}          # id -> alert dict
_triggered: list[dict] = []           # recent triggered (max 50)
_MAX_TRIGGERED = 50

# Valid condition types
CONDITION_TYPES = {
    "price_above",
    "price_below",
    "rsi_above",
    "rsi_below",
    "ema_cross",
    "breakout",
    "volume_spike",
}


# ── CRUD ───────────────────────────────────────────────────────────
def create_alert(data: dict, user_id: str = "default") -> dict:
    """Create a new alert. Returns the created alert dict."""
    symbol = (data.get("symbol") or "").strip().upper()
    if not symbol:
        raise ValueError("symbol is required")

    market = (data.get("market") or "crypto").strip().lower()
    condition_type = (data.get("condition_type") or "").strip().lower()
    if condition_type not in CONDITION_TYPES:
        raise ValueError(f"Invalid condition_type: {condition_type}. Must be one of {CONDITION_TYPES}")

    condition_value = data.get("condition_value")
    try:
        condition_value = float(condition_value)
    except (TypeError, ValueError):
        raise ValueError("condition_value must be a number")

    alert = {
        "id": str(uuid.uuid4())[:8],
        "user_id": user_id,
        "symbol": symbol,
        "market": market,
        "condition_type": condition_type,
        "condition_value": condition_value,
        "indicator": data.get("indicator", ""),
        "timeframe": data.get("timeframe", "1d"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
        "triggered_at": None,
        "trigger_price": None,
    }

    with _lock:
        _alerts[alert["id"]] = alert

    _logger.info("Alert created: %s %s %s %.4f",
                 alert["id"], symbol, condition_type, condition_value)
    return alert


def delete_alert(alert_id: str) -> bool:
    """Delete an alert by ID. Returns True if found & deleted."""
    with _lock:
        if alert_id in _alerts:
            del _alerts[alert_id]
            _logger.info("Alert deleted: %s", alert_id)
            return True
    return False


def get_alerts(user_id: str = None) -> list[dict]:
    """Return all alerts. If user_id given, filter by that user."""
    with _lock:
        if user_id:
            return [a for a in _alerts.values() if a.get("user_id") == user_id]
        return list(_alerts.values())


def get_alert(alert_id: str) -> dict | None:
    """Return a single alert by ID."""
    with _lock:
        return _alerts.get(alert_id)


def get_triggered() -> list[dict]:
    """Return recently triggered alerts."""
    with _lock:
        return list(_triggered)


def clear_triggered() -> None:
    """Clear the triggered alerts list."""
    with _lock:
        _triggered.clear()


# ── Price / Indicator Fetchers ─────────────────────────────────────
def _get_ticker_endpoint(market: str) -> str:
    """Map market to its ticker API endpoint."""
    return {
        "crypto": "/api/market/ticker",
        "stocks": "/api/stocks/ticker",
        "bist": "/api/bist/ticker",
        "forex": "/api/forex/ticker",
        "commodities": "/api/commodities/ticker",
    }.get(market, "/api/market/ticker")


def _fetch_price(symbol: str, market: str) -> float | None:
    """Fetch current price via internal API call."""
    try:
        from flask import current_app
        with current_app.test_client() as client:
            ep = _get_ticker_endpoint(market)
            resp = client.get(f"{ep}?symbol={symbol}")
            if resp.status_code == 200:
                data = resp.get_json()
                if data and data.get("ok"):
                    return float(data.get("lastPrice", 0))
    except Exception as e:
        _logger.debug("Price fetch failed for %s: %s", symbol, e)

    # Fallback: try cache
    try:
        from app.cache import cache_get
        tickers = cache_get("binance_top_tickers_v1", ttl=30)
        if tickers:
            for t in tickers:
                if t.get("s") == symbol:
                    return float(t.get("c", 0))
    except Exception:
        pass

    return None


def _fetch_rsi(symbol: str, market: str) -> float | None:
    """Fetch RSI(14) for a symbol."""
    try:
        from flask import current_app
        with current_app.test_client() as client:
            klines_ep = {
                "crypto": "/api/market/klines",
                "stocks": "/api/stocks/klines",
                "bist": "/api/bist/klines",
                "forex": "/api/forex/klines",
                "commodities": "/api/commodities/klines",
            }.get(market, "/api/market/klines")

            resp = client.get(f"{klines_ep}?symbol={symbol}&interval=1d&limit=30")
            if resp.status_code == 200:
                data = resp.get_json()
                candles = data.get("candles", [])
                if len(candles) >= 15:
                    closes = [c["close"] for c in candles]
                    return _calc_rsi(closes, 14)
    except Exception as e:
        _logger.debug("RSI fetch failed for %s: %s", symbol, e)
    return None


def _calc_rsi(closes: list[float], period: int = 14) -> float:
    """Calculate RSI from close prices."""
    if len(closes) < period + 1:
        return 50.0  # neutral fallback

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _fetch_volume_ratio(symbol: str, market: str) -> float | None:
    """Fetch volume ratio (current vs average) for volume_spike detection."""
    try:
        from flask import current_app
        with current_app.test_client() as client:
            klines_ep = {
                "crypto": "/api/market/klines",
                "stocks": "/api/stocks/klines",
                "bist": "/api/bist/klines",
                "forex": "/api/forex/klines",
                "commodities": "/api/commodities/klines",
            }.get(market, "/api/market/klines")

            resp = client.get(f"{klines_ep}?symbol={symbol}&interval=1d&limit=14")
            if resp.status_code == 200:
                data = resp.get_json()
                candles = data.get("candles", [])
                if candles and "volume" in candles[0]:
                    volumes = [c.get("volume", 0) for c in candles]
                    if len(volumes) >= 2 and sum(volumes[:-1]) > 0:
                        avg_vol = sum(volumes[:-1]) / len(volumes[:-1])
                        if avg_vol > 0:
                            return volumes[-1] / avg_vol
    except Exception as e:
        _logger.debug("Volume fetch failed for %s: %s", symbol, e)
    return None


# ── Check & Trigger ───────────────────────────────────────────────
def _trigger_alert(alert: dict, current_price: float | None) -> None:
    """Mark an alert as triggered."""
    with _lock:
        alert["active"] = False
        alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
        alert["trigger_price"] = current_price

        triggered_copy = dict(alert)
        _triggered.insert(0, triggered_copy)
        if len(_triggered) > _MAX_TRIGGERED:
            _triggered.pop()

    _logger.info("🔔 Alert triggered: %s %s %s @ %.4f",
                 alert["id"], alert["symbol"],
                 alert["condition_type"],
                 current_price or 0)


def check_alerts() -> list[dict]:
    """Check all active alerts against current market data.

    Returns list of newly triggered alerts.
    """
    with _lock:
        active = [a for a in _alerts.values() if a.get("active")]

    if not active:
        return []

    newly_triggered = []

    for alert in active:
        try:
            ct = alert["condition_type"]
            cv = alert["condition_value"]
            sym = alert["symbol"]
            mkt = alert["market"]

            if ct in ("price_above", "price_below"):
                price = _fetch_price(sym, mkt)
                if price is None or price == 0:
                    continue
                if ct == "price_above" and price >= cv:
                    _trigger_alert(alert, price)
                    newly_triggered.append(alert)
                elif ct == "price_below" and price <= cv:
                    _trigger_alert(alert, price)
                    newly_triggered.append(alert)

            elif ct in ("rsi_above", "rsi_below"):
                rsi = _fetch_rsi(sym, mkt)
                if rsi is None:
                    continue
                if ct == "rsi_above" and rsi >= cv:
                    _trigger_alert(alert, rsi)
                    newly_triggered.append(alert)
                elif ct == "rsi_below" and rsi <= cv:
                    _trigger_alert(alert, rsi)
                    newly_triggered.append(alert)

            elif ct == "volume_spike":
                ratio = _fetch_volume_ratio(sym, mkt)
                if ratio is not None and ratio >= cv:
                    _trigger_alert(alert, ratio)
                    newly_triggered.append(alert)

            elif ct == "ema_cross":
                # EMA cross: check if price crossed above EMA value
                price = _fetch_price(sym, mkt)
                if price is not None and price >= cv:
                    _trigger_alert(alert, price)
                    newly_triggered.append(alert)

            elif ct == "breakout":
                # Breakout: price breaks above given level
                price = _fetch_price(sym, mkt)
                if price is not None and price >= cv:
                    _trigger_alert(alert, price)
                    newly_triggered.append(alert)

        except Exception as e:
            _logger.warning("Alert check error for %s: %s", alert.get("id"), e)

    return newly_triggered


# ── Background Loop ───────────────────────────────────────────────
def alert_check_loop() -> None:
    """Background loop: check alerts every 10 seconds."""
    _logger.info("Alert check loop started (interval=10s)")
    while True:
        try:
            triggered = check_alerts()
            if triggered:
                _logger.info("Triggered %d alert(s) this cycle", len(triggered))
        except Exception as e:
            _logger.warning("Alert check loop error: %s", e)
        time.sleep(10)
