# -*- coding: utf-8 -*-
"""Multi-market API routes.

FAZ 16 — Unified API for Stocks, BIST, Forex, Commodities.

Endpoints:
  GET /api/stocks/symbols
  GET /api/stocks/ticker?symbol=AAPL
  GET /api/stocks/klines?symbol=AAPL&interval=1d&limit=500

  GET /api/bist/symbols
  GET /api/bist/ticker?symbol=THYAO.IS
  GET /api/bist/klines?symbol=THYAO.IS&interval=1d&limit=500

  GET /api/forex/symbols
  GET /api/forex/ticker?symbol=EURUSD=X
  GET /api/forex/klines?symbol=EURUSD=X&interval=1d&limit=500

  GET /api/commodities/symbols
  GET /api/commodities/ticker?symbol=GC=F
  GET /api/commodities/klines?symbol=GC=F&interval=1d&limit=500

Response formats match crypto /api/market/* as closely as possible.
"""
from __future__ import annotations

import logging

from flask import jsonify, request

from app.blueprints.markets import markets_bp
from app.cache import cache_get_or_set
from app.core.stocks_data import StocksDataService
from app.core.bist_data import BistDataService
from app.core.forex_data import ForexDataService
from app.core.commodities_data import CommoditiesDataService

_logger = logging.getLogger("zkr_analiz.markets.routes")

# ── Service registry ──
_SERVICES = {
    "stocks": StocksDataService,
    "bist": BistDataService,
    "forex": ForexDataService,
    "commodities": CommoditiesDataService,
}

# Valid intervals for Yahoo Finance data
_VALID_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"}

# Cache TTLs
_TICKER_TTL = 120    # 2 minutes for non-crypto tickers
_KLINES_TTL = 120    # 2 minutes


def _get_service(market: str):
    """Get market service by name."""
    svc = _SERVICES.get(market)
    if not svc:
        return None
    return svc


# ══════════════════════════════════════════════════════════════════════
# STOCKS
# ══════════════════════════════════════════════════════════════════════

@markets_bp.route("/api/stocks/symbols", methods=["GET"])
def stocks_symbols():
    """List US stock symbols."""
    try:
        data = StocksDataService.get_symbols()
        return jsonify({
            "ok": True,
            "market": "stocks",
            "items": data or [],
            "count": len(data or []),
        })
    except Exception as e:
        _logger.error("stocks symbols error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/stocks/ticker", methods=["GET"])
def stocks_ticker():
    """Single US stock ticker."""
    symbol = request.args.get("symbol", "AAPL").strip()
    try:
        data = cache_get_or_set(
            f"mkt:stocks:ticker:{symbol}", _TICKER_TTL,
            StocksDataService.get_ticker_single, symbol
        )
        return jsonify({"ok": True, **data})
    except Exception as e:
        _logger.error("stocks ticker error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/stocks/klines", methods=["GET"])
def stocks_klines():
    """US stock OHLCV klines."""
    symbol = request.args.get("symbol", "AAPL").strip()
    interval = request.args.get("interval", "1d")
    limit = int(request.args.get("limit", "500"))

    if interval not in _VALID_INTERVALS:
        return jsonify({"ok": False, "error": f"Invalid interval: {interval}"}), 400
    if limit < 1 or limit > 1500:
        return jsonify({"ok": False, "error": "limit must be 1-1500"}), 400

    try:
        cache_key = f"mkt:stocks:klines:{symbol}:{interval}:{limit}"
        rows = cache_get_or_set(
            cache_key, _KLINES_TTL,
            StocksDataService.get_klines, symbol, interval, limit
        )
        return _klines_response(symbol, interval, rows)
    except Exception as e:
        _logger.error("stocks klines error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


# ══════════════════════════════════════════════════════════════════════
# BIST
# ══════════════════════════════════════════════════════════════════════

@markets_bp.route("/api/bist/symbols", methods=["GET"])
def bist_symbols():
    """List BIST symbols."""
    try:
        # No route-level cache — get_symbols_info() returns instantly
        # from its own stale-while-revalidate cache and manages refresh.
        data = BistDataService.get_symbols()
        return jsonify({
            "ok": True,
            "market": "bist",
            "items": data or [],
            "count": len(data or []),
        })
    except Exception as e:
        _logger.error("bist symbols error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/bist/ticker", methods=["GET"])
def bist_ticker():
    """Single BIST ticker."""
    symbol = request.args.get("symbol", "THYAO.IS").strip()
    try:
        data = cache_get_or_set(
            f"mkt:bist:ticker:{symbol}", _TICKER_TTL,
            BistDataService.get_ticker_single, symbol
        )
        return jsonify({"ok": True, **data})
    except Exception as e:
        _logger.error("bist ticker error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/bist/klines", methods=["GET"])
def bist_klines():
    """BIST OHLCV klines."""
    symbol = request.args.get("symbol", "THYAO.IS").strip()
    interval = request.args.get("interval", "1d")
    limit = int(request.args.get("limit", "500"))

    if interval not in _VALID_INTERVALS:
        return jsonify({"ok": False, "error": f"Invalid interval: {interval}"}), 400
    if limit < 1 or limit > 1500:
        return jsonify({"ok": False, "error": "limit must be 1-1500"}), 400

    try:
        cache_key = f"mkt:bist:klines:{symbol}:{interval}:{limit}"
        rows = cache_get_or_set(
            cache_key, _KLINES_TTL,
            BistDataService.get_klines, symbol, interval, limit
        )
        return _klines_response(symbol, interval, rows)
    except Exception as e:
        _logger.error("bist klines error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


# ══════════════════════════════════════════════════════════════════════
# FOREX
# ══════════════════════════════════════════════════════════════════════

@markets_bp.route("/api/forex/symbols", methods=["GET"])
def forex_symbols():
    """List Forex symbols."""
    try:
        data = ForexDataService.get_symbols()
        return jsonify({
            "ok": True,
            "market": "forex",
            "items": data or [],
            "count": len(data or []),
        })
    except Exception as e:
        _logger.error("forex symbols error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/forex/ticker", methods=["GET"])
def forex_ticker():
    """Single Forex ticker."""
    symbol = request.args.get("symbol", "EURUSD=X").strip()
    try:
        data = cache_get_or_set(
            f"mkt:forex:ticker:{symbol}", _TICKER_TTL,
            ForexDataService.get_ticker_single, symbol
        )
        return jsonify({"ok": True, **data})
    except Exception as e:
        _logger.error("forex ticker error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/forex/klines", methods=["GET"])
def forex_klines():
    """Forex OHLCV klines."""
    symbol = request.args.get("symbol", "EURUSD=X").strip()
    interval = request.args.get("interval", "1d")
    limit = int(request.args.get("limit", "500"))

    if interval not in _VALID_INTERVALS:
        return jsonify({"ok": False, "error": f"Invalid interval: {interval}"}), 400
    if limit < 1 or limit > 1500:
        return jsonify({"ok": False, "error": "limit must be 1-1500"}), 400

    try:
        cache_key = f"mkt:forex:klines:{symbol}:{interval}:{limit}"
        rows = cache_get_or_set(
            cache_key, _KLINES_TTL,
            ForexDataService.get_klines, symbol, interval, limit
        )
        return _klines_response(symbol, interval, rows)
    except Exception as e:
        _logger.error("forex klines error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


# ══════════════════════════════════════════════════════════════════════
# COMMODITIES
# ══════════════════════════════════════════════════════════════════════

@markets_bp.route("/api/commodities/symbols", methods=["GET"])
def commodities_symbols():
    """List Commodity symbols."""
    try:
        data = CommoditiesDataService.get_symbols()
        return jsonify({
            "ok": True,
            "market": "commodities",
            "items": data or [],
            "count": len(data or []),
        })
    except Exception as e:
        _logger.error("commodities symbols error: %s", e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/commodities/ticker", methods=["GET"])
def commodities_ticker():
    """Single Commodity ticker."""
    symbol = request.args.get("symbol", "GC=F").strip()
    try:
        data = cache_get_or_set(
            f"mkt:commodities:ticker:{symbol}", _TICKER_TTL,
            CommoditiesDataService.get_ticker_single, symbol
        )
        return jsonify({"ok": True, **data})
    except Exception as e:
        _logger.error("commodities ticker error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


@markets_bp.route("/api/commodities/klines", methods=["GET"])
def commodities_klines():
    """Commodity OHLCV klines."""
    symbol = request.args.get("symbol", "GC=F").strip()
    interval = request.args.get("interval", "1d")
    limit = int(request.args.get("limit", "500"))

    if interval not in _VALID_INTERVALS:
        return jsonify({"ok": False, "error": f"Invalid interval: {interval}"}), 400
    if limit < 1 or limit > 1500:
        return jsonify({"ok": False, "error": "limit must be 1-1500"}), 400

    try:
        cache_key = f"mkt:commodities:klines:{symbol}:{interval}:{limit}"
        rows = cache_get_or_set(
            cache_key, _KLINES_TTL,
            CommoditiesDataService.get_klines, symbol, interval, limit
        )
        return _klines_response(symbol, interval, rows)
    except Exception as e:
        _logger.error("commodities klines error %s: %s", symbol, e)
        return jsonify({"ok": False, "error": str(e)}), 502


# ══════════════════════════════════════════════════════════════════════
# Shared helpers
# ══════════════════════════════════════════════════════════════════════

def _klines_response(symbol: str, interval: str, rows: list):
    """Convert raw kline rows to LightweightCharts-friendly JSON."""
    candles = [
        {
            "time": int(r["open_time"] // 1000),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
        }
        for r in (rows or [])
    ]
    volume = [
        {
            "time": int(r["open_time"] // 1000),
            "value": r["volume"],
        }
        for r in (rows or [])
    ]
    return jsonify({
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "candles": candles,
        "volume": volume,
    })


# ════════════════════════════════════════════════════════════════════
# BATCH SNAPSHOT
# ════════════════════════════════════════════════════════════════════

@markets_bp.route("/api/snapshot", methods=["GET"])
def market_snapshot():
    """Return ticker data for multiple symbols across markets in one call.

    Query params:
        items: comma-separated list of market:symbol pairs
               e.g. crypto:BTCUSDT,crypto:ETHUSDT,commodities:GC=F,stocks:SPY
    """
    raw = request.args.get("items", "")
    if not raw:
        return jsonify({"ok": False, "error": "items param required"}), 400

    market_map = {
        "crypto": "/api/market/ticker",
        "stocks": "stocks",
        "bist": "bist",
        "forex": "forex",
        "commodities": "commodities",
    }
    svc_map = {
        "stocks": StocksDataService,
        "bist": BistDataService,
        "forex": ForexDataService,
        "commodities": CommoditiesDataService,
    }

    results = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" not in pair:
            continue
        market, symbol = pair.split(":", 1)
        market = market.strip().lower()
        symbol = symbol.strip()
        if not symbol or market not in market_map:
            continue

        try:
            if market == "crypto":
                from flask import current_app
                svc = current_app.extensions.get("market_data")
                if svc:
                    cache_key = f"mkt:crypto:ticker:{symbol}"
                    data = cache_get_or_set(cache_key, 15, svc.get_ticker_single, symbol)
                else:
                    data = None
            else:
                svc = svc_map[market]
                cache_key = f"mkt:{market}:ticker:{symbol}"
                data = cache_get_or_set(cache_key, _TICKER_TTL, svc.get_ticker_single, symbol)
            if data:
                results[pair] = {
                    "symbol": symbol,
                    "lastPrice": data.get("lastPrice", 0),
                    "priceChange": data.get("priceChange", 0),
                    "priceChangePercent": data.get("priceChangePercent", 0),
                }
        except Exception as e:
            _logger.debug("Snapshot %s error: %s", pair, e)
            results[pair] = {"symbol": symbol, "lastPrice": 0, "priceChange": 0, "priceChangePercent": 0}

    return jsonify({"ok": True, "data": results})
