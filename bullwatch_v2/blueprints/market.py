from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint("market", __name__, url_prefix="/api/market")

VALID_INTERVALS = {"1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w", "1M"}


def _svc():
    return current_app.extensions["market_data"]


@bp.get("/symbols")
def api_symbols():
    try:
        symbols = _svc().get_symbols()
        return jsonify({"ok": True, "symbols": symbols, "count": len(symbols)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@bp.get("/klines")
def api_klines():
    svc = _svc()
    raw_symbol = (request.args.get("symbol") or "BTCUSDT").upper()
    symbol, requested = svc.normalize_symbol(raw_symbol)
    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "500")

    # Validation
    if interval not in VALID_INTERVALS:
        return jsonify({"ok": False, "error": f"Invalid interval: {interval}"}), 400
    if limit < 1 or limit > 1500:
        return jsonify({"ok": False, "error": "limit must be 1-1500"}), 400

    try:
        rows = svc.get_klines(symbol, interval, limit)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    # Lightweight-charts friendly shape
    candles = [
        {
            "time": int(r["open_time"] // 1000),
            "open": r["open"],
            "high": r["high"],
            "low": r["low"],
            "close": r["close"],
        }
        for r in rows
    ]
    volume = [
        {
            "time": int(r["open_time"] // 1000),
            "value": r["volume"],
        }
        for r in rows
    ]

    resp = {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "candles": candles,
        "volume": volume,
    }
    if requested:
        resp["requested_symbol"] = requested
    return jsonify(resp)


@bp.get("/ticker")
def api_ticker():
    """Single symbol 24h ticker - real-time price, change, volume."""
    svc = _svc()
    raw_symbol = (request.args.get("symbol") or "BTCUSDT").upper()
    symbol, requested = svc.normalize_symbol(raw_symbol)
    try:
        t = svc.get_ticker_single(symbol)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    resp = {
        "ok": True,
        "symbol": t.get("symbol", symbol),
        "lastPrice": float(t.get("lastPrice", 0)),
        "priceChange": float(t.get("priceChange", 0)),
        "priceChangePercent": float(t.get("priceChangePercent", 0)),
        "highPrice": float(t.get("highPrice", 0)),
        "lowPrice": float(t.get("lowPrice", 0)),
        "volume": float(t.get("volume", 0)),
        "quoteVolume": float(t.get("quoteVolume", 0)),
        "weightedAvgPrice": float(t.get("weightedAvgPrice", 0)),
    }
    if requested:
        resp["requested_symbol"] = requested
    return jsonify(resp)
