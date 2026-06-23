from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint("alpha", __name__, url_prefix="/api/alpha")


def _svc():
    return current_app.extensions["market_data"]


@bp.get("/status")
def status():
    """Lightweight alpha status.

    Real (non-mock) integration: fetches ALPHA_*USDT symbols from Binance and optionally
    samples klines for a subset to detect data availability.

    Query:
      - sample (int): number of symbols to sample for kline availability (default 25)
      - interval (str): kline interval (default 15m)
      - limit (int): kline limit (default 60)
    """

    sample = int(request.args.get("sample") or "25")
    sample = max(0, min(sample, 200))
    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "60")

    # Fetch real Alpha pairs from Binance Alpha public endpoints
    try:
        pairs = _svc().get_alpha_pairs()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    symbols = [p["pair"] for p in pairs]
    failed = []
    scanned = 0
    if sample > 0:
        for sym in symbols[:sample]:
            scanned += 1
            try:
                rows = _svc().get_alpha_klines(sym, interval, limit, ttl_s=2.0)
                if not rows:
                    failed.append({"pair": sym, "error": "klines empty"})
            except Exception as e:
                failed.append({"pair": sym, "error": str(e)})

    return jsonify(
        {
            "ok": True,
            "generated_at": int(time.time()),
            "total_symbols": len(symbols),
            "scanned": scanned,
            "failed": failed,
        }
    )


@bp.get("/symbols")
def symbols():
    try:
        pairs = _svc().get_alpha_pairs()
        return jsonify({"ok": True, "count": len(pairs), "symbols": pairs})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@bp.get("/pair")
def pair_detail():
    """Detailed data for a single Alpha pair.

    Returns klines (lightweight-charts format), 24h summary derived from klines,
    and pair metadata.

    Query params:
      pair (str): Alpha pair symbol, e.g. ALPHA_123USDT
      interval (str): kline interval (default 15m)
      limit (int): number of candles (default 200)
    """
    pair = (request.args.get("pair") or "").upper()
    if not pair:
        return jsonify({"ok": False, "error": "pair parameter required"}), 400

    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "200")
    limit = max(1, min(limit, 1500))

    svc = _svc()

    out = {
        "ok": True,
        "pair": pair,
        "interval": interval,
        "generated_at": int(time.time()),
    }

    # Find pair metadata
    try:
        all_pairs = svc.get_alpha_pairs(ttl_s=60.0)
        meta = next((p for p in all_pairs if p["pair"] == pair), None)
        out["meta"] = meta or {"pair": pair, "readable": pair}
    except Exception as e:
        out["meta"] = {"pair": pair, "error": str(e)}

    # Fetch klines
    try:
        rows = svc.get_alpha_klines(pair, interval, limit, ttl_s=3.0)
    except Exception as e:
        out["candles"] = []
        out["volume"] = []
        out["summary"] = {"error": str(e)}
        return jsonify(out)

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

    out["candles"] = candles
    out["volume"] = volume

    # Summary from klines
    if rows:
        closes = [r["close"] for r in rows]
        highs = [r["high"] for r in rows]
        lows = [r["low"] for r in rows]
        vols = [r["volume"] for r in rows]
        last = closes[-1]
        first = closes[0]
        change_pct = ((last - first) / first * 100) if first > 0 else 0

        out["summary"] = {
            "lastClose": last,
            "periodHigh": max(highs),
            "periodLow": min(lows),
            "changePct": round(change_pct, 2),
            "totalVolume": round(sum(vols), 2),
            "avgVolume": round(sum(vols) / len(vols), 2) if vols else 0,
            "candleCount": len(rows),
        }
    else:
        out["summary"] = {"candleCount": 0}

    return jsonify(out)
