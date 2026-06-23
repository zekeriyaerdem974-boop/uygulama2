from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint("liquidation", __name__, url_prefix="/api/liquidation")


def _svc():
    return current_app.extensions["market_data"]


@bp.get("/symbols")
def symbols():
    try:
        tickers = _svc().get_ticker_24h()
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    items = []
    for t in tickers:
        sym = t.get("symbol")
        if not sym or not sym.endswith("USDT"):
            continue
        try:
            quote_vol = float(t.get("quoteVolume", 0) or 0)
            pct = float(t.get("priceChangePercent", 0) or 0)
            last_price = float(t.get("lastPrice", 0) or 0)
            volume = float(t.get("volume", 0) or 0)
            high_price = float(t.get("highPrice", 0) or 0)
            low_price = float(t.get("lowPrice", 0) or 0)
        except Exception:
            continue

        base = sym[:-4]
        items.append({
            "symbol": sym, "base": base, "pct": pct,
            "quoteVolume": quote_vol, "lastPrice": last_price,
            "volume": volume, "highPrice": high_price, "lowPrice": low_price,
        })

    items.sort(key=lambda x: x.get("quoteVolume", 0), reverse=True)
    return jsonify({"ok": True, "count": len(items), "items": items})


@bp.get("/price_profile")
def price_profile():
    """Volume-weighted price profile for a symbol.

    Builds a real volume profile from recent klines:
    - Groups candles into price bins
    - Calculates volume at each price level
    - Identifies high-volume nodes (potential support/resistance / liquidation clusters)
    - Provides 24h range, current position within range

    Query params:
      symbol (str): e.g. BTCUSDT
      interval (str): kline interval (default 15m)
      limit (int): number of candles (default 200)
      bins (int): number of price bins (default 20)
    """
    svc = _svc()
    raw_symbol = (request.args.get("symbol") or "BTCUSDT").upper()
    symbol, requested = svc.normalize_symbol(raw_symbol)
    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "200")
    bins = int(request.args.get("bins") or "20")
    bins = max(5, min(bins, 100))

    out = {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "generated_at": int(time.time()),
    }
    if requested:
        out["requested_symbol"] = requested

    # 1) Klines for volume profile
    try:
        rows = svc.get_klines(symbol, interval, limit, ttl_s=3.0)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    if not rows:
        out["profile"] = []
        out["summary"] = {"error": "no kline data"}
        return jsonify(out)

    # Build volume profile
    all_highs = [r["high"] for r in rows]
    all_lows = [r["low"] for r in rows]
    price_high = max(all_highs)
    price_low = min(all_lows)
    price_range = price_high - price_low
    last_close = rows[-1]["close"]

    if price_range <= 0:
        out["profile"] = []
        out["summary"] = {"lastClose": last_close, "high": price_high, "low": price_low}
        return jsonify(out)

    bin_size = price_range / bins
    profile = []
    for i in range(bins):
        lo = price_low + i * bin_size
        hi = lo + bin_size
        mid = (lo + hi) / 2
        vol = 0.0
        count = 0
        for r in rows:
            # Candle overlaps this bin if candle_low <= hi and candle_high >= lo
            if r["low"] <= hi and r["high"] >= lo:
                # Approximate: distribute volume proportionally
                candle_range = r["high"] - r["low"]
                if candle_range > 0:
                    overlap = min(hi, r["high"]) - max(lo, r["low"])
                    fraction = max(0, overlap / candle_range)
                else:
                    fraction = 1.0
                vol += r["volume"] * fraction
                count += 1
        profile.append({
            "priceLow": round(lo, 8),
            "priceHigh": round(hi, 8),
            "priceMid": round(mid, 8),
            "volume": round(vol, 4),
            "candleCount": count,
        })

    # Identify top volume nodes (POC - point of control)
    max_vol = max(p["volume"] for p in profile) if profile else 0
    poc_price = None
    for p in profile:
        if p["volume"] == max_vol:
            poc_price = p["priceMid"]
            break

    # Value area (70% of total volume)
    total_vol = sum(p["volume"] for p in profile)
    sorted_bins = sorted(profile, key=lambda x: x["volume"], reverse=True)
    va_vol = 0.0
    va_bins = []
    for b in sorted_bins:
        va_vol += b["volume"]
        va_bins.append(b["priceMid"])
        if total_vol > 0 and va_vol / total_vol >= 0.70:
            break
    va_high = max(va_bins) if va_bins else price_high
    va_low = min(va_bins) if va_bins else price_low

    # 24h ticker for additional context
    try:
        t = svc.get_ticker_single(symbol, ttl_s=2.0)
        price_24h_pct = float(t.get("priceChangePercent", 0))
        volume_24h = float(t.get("quoteVolume", 0))
    except Exception:
        price_24h_pct = 0
        volume_24h = 0

    # Position within range (0 = at low, 1 = at high)
    range_position = (last_close - price_low) / price_range if price_range > 0 else 0.5

    out["profile"] = profile
    out["summary"] = {
        "lastClose": round(last_close, 8),
        "high": round(price_high, 8),
        "low": round(price_low, 8),
        "poc": round(poc_price, 8) if poc_price else None,
        "valueAreaHigh": round(va_high, 8),
        "valueAreaLow": round(va_low, 8),
        "rangePosition": round(range_position, 4),
        "totalVolume": round(total_vol, 2),
        "priceChange24hPct": round(price_24h_pct, 2),
        "quoteVolume24h": round(volume_24h, 2),
        "candlesAnalyzed": len(rows),
        "bins": bins,
    }

    return jsonify(out)
