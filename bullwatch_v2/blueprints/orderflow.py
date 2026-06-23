from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify, request


bp = Blueprint("orderflow", __name__, url_prefix="/api/orderflow")


def _svc():
    return current_app.extensions["market_data"]


@bp.get("/health")
def health():
    return jsonify({"ok": True, "status": "ok"})


@bp.get("/symbols")
def symbols():
    try:
        syms = _svc().get_symbols()
        return jsonify({"ok": True, "symbols": syms, "count": len(syms)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502


@bp.get("/symbol/<symbol>")
def symbol_detail(symbol: str):
    """Unified orderflow summary for a single symbol.

    Aggregates: 24h ticker, open interest, funding rate,
    long/short ratio, taker buy/sell ratio, and order book imbalance.
    All from Binance Futures public endpoints - no separate port needed.
    """
    svc = _svc()
    symbol, requested = svc.normalize_symbol(symbol)

    out = {
        "ok": True,
        "symbol": symbol,
        "generated_at": int(time.time()),
    }
    if requested:
        out["requested_symbol"] = requested

    # 1) 24h ticker
    try:
        t = svc.get_ticker_single(symbol, ttl_s=2.0)
        out["ticker"] = {
            "lastPrice": float(t.get("lastPrice", 0)),
            "priceChangePercent": float(t.get("priceChangePercent", 0)),
            "volume": float(t.get("volume", 0)),
            "quoteVolume": float(t.get("quoteVolume", 0)),
            "highPrice": float(t.get("highPrice", 0)),
            "lowPrice": float(t.get("lowPrice", 0)),
        }
    except Exception as e:
        out["ticker"] = {"error": str(e)}

    # 2) Open Interest
    try:
        oi = svc.get_open_interest(symbol, ttl_s=5.0)
        out["openInterest"] = {
            "openInterest": float(oi.get("openInterest", 0)),
            "symbol": oi.get("symbol", symbol),
        }
    except Exception as e:
        out["openInterest"] = {"error": str(e)}

    # 3) Funding Rate
    try:
        fr = svc.get_funding_rate(symbol, limit=1, ttl_s=10.0)
        if fr:
            latest = fr[0]
            out["fundingRate"] = {
                "fundingRate": float(latest.get("fundingRate", 0)),
                "fundingTime": int(latest.get("fundingTime", 0)),
                "markPrice": float(latest.get("markPrice", 0)),
            }
        else:
            out["fundingRate"] = {"fundingRate": 0}
    except Exception as e:
        out["fundingRate"] = {"error": str(e)}

    # 4) Long/Short Ratio (top trader accounts)
    try:
        ls = svc.get_long_short_ratio(symbol, period="5m", limit=1, ttl_s=30.0)
        if ls:
            latest = ls[0]
            out["longShortRatio"] = {
                "longShortRatio": float(latest.get("longShortRatio", 0)),
                "longAccount": float(latest.get("longAccount", 0)),
                "shortAccount": float(latest.get("shortAccount", 0)),
                "timestamp": int(latest.get("timestamp", 0)),
            }
        else:
            out["longShortRatio"] = {"longShortRatio": 0}
    except Exception as e:
        out["longShortRatio"] = {"error": str(e)}

    # 5) Taker Buy/Sell Volume
    try:
        tv = svc.get_taker_volume(symbol, period="5m", limit=1, ttl_s=30.0)
        if tv:
            latest = tv[0]
            out["takerVolume"] = {
                "buySellRatio": float(latest.get("buySellRatio", 0)),
                "buyVol": float(latest.get("buyVol", 0)),
                "sellVol": float(latest.get("sellVol", 0)),
                "timestamp": int(latest.get("timestamp", 0)),
            }
        else:
            out["takerVolume"] = {"buySellRatio": 0}
    except Exception as e:
        out["takerVolume"] = {"error": str(e)}

    # 6) Order Book Imbalance (top 20 levels)
    try:
        depth = svc.get_depth(symbol, limit=20, ttl_s=2.0)
        bids = depth.get("bids", [])
        asks = depth.get("asks", [])
        bid_total = sum(float(b[1]) for b in bids) if bids else 0
        ask_total = sum(float(a[1]) for a in asks) if asks else 0
        total = bid_total + ask_total
        out["bookImbalance"] = {
            "bidTotal": round(bid_total, 4),
            "askTotal": round(ask_total, 4),
            "imbalance": round((bid_total - ask_total) / total, 4) if total > 0 else 0,
            "levels": len(bids),
        }
    except Exception as e:
        out["bookImbalance"] = {"error": str(e)}

    return jsonify(out)


@bp.get("/depth/<symbol>")
def symbol_depth(symbol: str):
    """Order book depth for a symbol."""
    svc = _svc()
    symbol, requested = svc.normalize_symbol(symbol)
    limit = int(request.args.get("limit") or "20")
    limit = max(5, min(limit, 1000))
    try:
        depth = svc.get_depth(symbol, limit=limit, ttl_s=2.0)
        bids = [[float(b[0]), float(b[1])] for b in depth.get("bids", [])]
        asks = [[float(a[0]), float(a[1])] for a in depth.get("asks", [])]
        resp = {
            "ok": True,
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "bidCount": len(bids),
            "askCount": len(asks),
        }
        if requested:
            resp["requested_symbol"] = requested
        return jsonify(resp)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502
