# -*- coding: utf-8 -*-
"""Analytics tracking routes — FAZ 46.

Simple event tracking endpoint. Events are stored in an in-memory
buffer and can be queried for dashboards.

Tracked events:
  landing_visit, landing_register_click, signup, onboarding_completed,
  onboarding_step_N, invite_click

FAZE 5: Historical chart data endpoint for candlestick backfill.
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone

from flask import jsonify, request, session

from app.blueprints.analytics import analytics_bp
from app.core.yahoo_client import get_klines
from app.core.ai_market_analyst import analyze_market_brief
from app.core.symbol_dictionary import normalize_ui_symbol, get_yahoo_symbol, SYMBOL_MAP

_logger = logging.getLogger("zkr_analiz.analytics")

# ── In-memory event buffer (last 10 000 events) ──────────────────
_events: deque = deque(maxlen=10_000)
_lock = threading.Lock()

VALID_EVENTS = {
    "landing_visit", "landing_register_click", "landing_login_click",
    "signup", "onboarding_completed", "onboarding_step_1",
    "onboarding_step_2", "onboarding_step_3", "onboarding_step_4",
    "onboarding_step_5", "invite_click", "page_view",
}


@analytics_bp.route("/api/analytics/track", methods=["POST"])
def api_track():
    """Record an analytics event.

    Body: { event: "landing_visit", data: {...}, ts: "..." }
    """
    body = request.get_json(silent=True) or {}
    event_name = (body.get("event") or "").strip()

    if not event_name or event_name not in VALID_EVENTS:
        return jsonify({"ok": False, "error": "invalid event"}), 400

    entry = {
        "event": event_name,
        "data": body.get("data", {}),
        "page": body.get("page", ""),
        "user_id": session.get("user_id"),
        "ts": body.get("ts") or datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _events.append(entry)

    return jsonify({"ok": True})


@analytics_bp.route("/api/analytics/summary", methods=["GET"])
def api_summary():
    """Return event counts for analytics dashboard."""
    with _lock:
        events_copy = list(_events)

    counts: dict = {}
    for e in events_copy:
        name = e["event"]
        counts[name] = counts.get(name, 0) + 1

    return jsonify({"ok": True, "total": len(events_copy), "counts": counts})


def get_events() -> list:
    """Return current events list (for testing)."""
    with _lock:
        return list(_events)


def clear_events():
    """Clear events buffer (for testing)."""
    with _lock:
        _events.clear()


# ═══════════════════════════════════════════════════════════════════════════
# FAZE 5: CHART HISTORICAL DATA ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@analytics_bp.route("/api/v1/chart/historical", methods=["GET"])
def api_chart_historical():
    """
    Get historical OHLCV candlestick data for chart backfill.
    
    Query Parameters:
        symbol (str): Trading symbol (BTCUSDT, EURUSD, AAPL, etc.)
        interval (str): Timeframe (1m, 5m, 15m, 1h, 4h, 1d, 1w, 1M)
                       Default: 1d
        limit (int): Number of candles to return (default: 200)
    
    Response:
        {
            "ok": true,
            "symbol": "BTCUSDT",
            "interval": "1h",
            "count": 200,
            "candles": [
                {
                    "time": 1782084000000,  # milliseconds (LWC format)
                    "open": 63665.47,
                    "high": 63700.00,
                    "low": 63600.00,
                    "close": 63666.39,
                    "volume": 1234.56
                },
                ...
            ]
        }
    """
    try:
        # Get parameters
        raw_symbol = request.args.get("symbol", "BTCUSDT").strip().upper()
        interval = request.args.get("interval", "1d").strip().lower()
        limit = int(request.args.get("limit", 200))
        
        # Normalize symbol: remove exchange prefix if present (BINANCE:BTCUSDT → BTCUSDT)
        symbol = normalize_ui_symbol(raw_symbol)
        
        # Validate limit (max 500 to prevent abuse)
        if limit < 1 or limit > 500:
            limit = 200
        
        # Get Yahoo Finance symbol from centralized dictionary
        if symbol not in SYMBOL_MAP:
            _logger.warning(f"[Chart API] Unknown symbol: {symbol}")
            return jsonify({
                "ok": False,
                "error": f"Unknown symbol '{symbol}'",
                "symbol": symbol,
                "interval": interval,
                "candles": []
            }), 400
        
        try:
            symbol_for_yf = get_yahoo_symbol(symbol)
        except KeyError as e:
            _logger.error(f"[Chart API] Symbol mapping error: {e}")
            return jsonify({
                "ok": False,
                "error": f"Symbol mapping failed: {e}",
                "symbol": symbol
            }), 400
        
        _logger.info(f"[Chart API] Fetching {limit} {interval} candles for {symbol} (Yahoo: {symbol_for_yf})")
        
        # Fetch historical data from Yahoo Finance
        klines = get_klines(symbol=symbol_for_yf, interval=interval, limit=limit)
        
        if not klines:
            _logger.warning(f"[Chart API] No data for {symbol} / {interval}")
            return jsonify({
                "ok": False,
                "error": f"No historical data for {symbol}",
                "symbol": symbol,
                "interval": interval,
                "candles": []
            }), 404
        
        # Transform to LWC format (convert timestamps to ms and rename fields)
        candles = []
        for kline in klines:
            candle = {
                "time": kline.get("open_time") or int(kline.get("timestamp", 0) * 1000),
                "open": float(kline.get("open", 0)),
                "high": float(kline.get("high", 0)),
                "low": float(kline.get("low", 0)),
                "close": float(kline.get("close", 0)),
                "volume": float(kline.get("volume", 0)),
            }
            candles.append(candle)
        
        _logger.info(f"[Chart API] ✅ Returned {len(candles)} candles for {symbol}/{interval}")
        
        return jsonify({
            "ok": True,
            "symbol": symbol,
            "interval": interval,
            "count": len(candles),
            "candles": candles
        })
    
    except Exception as e:
        _logger.error(f"[Chart API] Error: {e}", exc_info=True)
        return jsonify({
            "ok": False,
            "error": str(e),
            "symbol": request.args.get("symbol", "?"),
            "interval": request.args.get("interval", "?"),
            "candles": []
        }), 500


# ═══════════════════════════════════════════════════════════════════════════
# FAZE 7: AI EDUCATIONAL MARKET BRIEF ENDPOINT
# ═══════════════════════════════════════════════════════════════════════════

@analytics_bp.route("/api/v1/market/brief", methods=["POST"])
def api_market_brief():
    """
    Generate AI educational market brief from candle data.
    Used for YMYL compliance: educational-only analysis without trading advice.
    
    Request Body:
        {
            "candles": [
                {"time": 1782084000000, "open": 63665.47, "high": 63700, "low": 63600, 
                 "close": 63666.39, "volume": 1234.56},
                ...
            ],
            "timeframe": "1h",           # 15m, 1h, 4h, 1d, etc.
            "symbol": "BTCUSDT"          # Optional, default BTCUSDT
        }
    
    Response:
        {
            "ok": true,
            "symbol": "BTCUSDT",
            "timeframe": "1h",
            "brief": "Seçili 1 saatlik periyodunda varlık yükselen bir fiyat kanalı...",
            "disclaimer": "*Bu analiz, geçmiş fiyat hareketlerine dayalı teorik bir simülasyondur..."
        }
    """
    try:
        body = request.get_json(silent=True) or {}
        
        # Extract parameters
        candles = body.get("candles", [])
        timeframe = body.get("timeframe", "1h").strip().lower()
        symbol = body.get("symbol", "BTCUSDT").strip().upper()
        
        # Validate inputs
        if not candles or not isinstance(candles, list):
            return jsonify({
                "ok": False,
                "error": "Invalid or missing candles array",
                "symbol": symbol,
                "timeframe": timeframe
            }), 400
        
        if not timeframe:
            return jsonify({
                "ok": False,
                "error": "Missing timeframe parameter",
                "symbol": symbol,
                "timeframe": timeframe
            }), 400
        
        _logger.info(f"[AI Brief] Generating brief for {symbol}/{timeframe} ({len(candles)} candles)")
        
        # Call AI analyzer
        result = analyze_market_brief(candles, timeframe, symbol)
        
        _logger.info(f"[AI Brief] ✅ Generated: {result.get('brief', '')[:60]}...")
        
        return jsonify(result)
    
    except Exception as e:
        _logger.error(f"[AI Brief] Error: {e}", exc_info=True)
        return jsonify({
            "ok": False,
            "error": str(e),
            "symbol": body.get("symbol", "?"),
            "timeframe": body.get("timeframe", "?")
        }), 500

