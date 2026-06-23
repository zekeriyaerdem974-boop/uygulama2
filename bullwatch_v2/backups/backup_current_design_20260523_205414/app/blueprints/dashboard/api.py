"""Dashboard API endpoints.

FAZ 4 — Moved from ``legacy_monolith.py``.
All endpoint URLs, response shapes, and behaviours are preserved exactly.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd
from flask import jsonify, request

from app.blueprints.dashboard import dashboard_bp
from app.cache import cache_get, cache_set, cache_get_or_set, utcnow
from app.core.binance_client import (
    binance_klines,
    _fetch_exchange_info,
    fapi_open_interest,
    fapi_open_interest_hist,
    fng_latest,
    blockchain_hashrate,
    defillama_stablecoins,
    coinglass_coinbase_premium,
    pump_candidates,
)
from app.core.ta import (
    simple_sma,
    compute_rsi,
    compute_macd,
    compute_btc_indicators_from_df,
)
from app.core.etf_tracker import fetch_dynamic_etf_events
from app.core.thresholds import get_thresholds, update_thresholds

# Cache key shared with the Binance ticker WS loop in the monolith
TICKERS_KEY = "binance_top_tickers_v1"


# ── /api/mobile_snapshot ─────────────────────────────────────────────
@dashboard_bp.get("/api/mobile_snapshot")
def api_mobile_snapshot():
    """Mobile için tek istekle hafif snapshot."""
    return jsonify({
        "ok": True,
        "data": {
            "generated_at": utcnow().isoformat(),
            "tickers": cache_get(TICKERS_KEY, ttl=5) or [],
            "thresholds": get_thresholds(),
        }
    })


# ── /api/thresholds ─────────────────────────────────────────────────
@dashboard_bp.route("/api/thresholds", methods=["GET", "POST"])
def api_thresholds():
    try:
        if request.method == "GET":
            return jsonify({"ok": True, "data": get_thresholds()})
        # POST: eşikleri güncelle
        body = request.get_json(force=True, silent=True) or {}
        new_th = update_thresholds(body)
        # chat_context içinde de görünsün diye tazele
        # FAZ 11: build_chat_context removed (moved to chat blueprint)
        return jsonify({"ok": True, "data": new_th})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/fng ─────────────────────────────────────────────────────────
@dashboard_bp.route("/api/fng")
def api_fng():
    try:
        return jsonify({"ok": True, "data": fng_latest()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/btc_indicators ─────────────────────────────────────────────
@dashboard_bp.route("/api/btc_indicators")
def api_btc_indicators():
    try:
        df = cache_get_or_set("btc_1d_df", 300, binance_klines, "BTCUSDT", "1d", 400)
        data = compute_btc_indicators_from_df(df, now_iso=utcnow().isoformat())
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/coins_sma_summary ──────────────────────────────────────────
@dashboard_bp.route("/api/coins_sma_summary")
def api_coins_sma_summary():
    try:
        limit = int(request.args.get("limit", 60))

        # Return cached result if available (background computes this)
        cache_key = f"coins_sma_summary_{limit}"
        cached = cache_get(cache_key, ttl=600)
        if cached is not None:
            return jsonify({"ok": True, "data": cached})

        # Compute in background thread to avoid request timeout
        import threading

        def _compute():
            try:
                ex = cache_get_or_set("exchange_info", 600, _fetch_exchange_info)
                symbols = []
                for s in ex["symbols"]:
                    if s["status"] == "TRADING" and s["quoteAsset"] == "USDT" and s.get("isSpotTradingAllowed"):
                        symbols.append(s["symbol"])
                symbols = symbols[:limit]
                count_above, scan = 0, []
                for sb in symbols:
                    try:
                        df = binance_klines(sb, "1d", 220)
                        if df.empty or len(df) < 200:
                            continue
                        closes = df["close"].tolist()
                        sma200 = simple_sma(closes, 200)
                        last = closes[-1]
                        above = last > (sma200 or 1e18)
                        scan.append({"symbol": sb, "last": float(last), "sma200": float(sma200) if sma200 is not None else None, "above": bool(above)})
                        if above:
                            count_above += 1
                        time.sleep(0.03)
                    except Exception:
                        continue
                pct = (count_above / len(scan)) * 100 if scan else 0.0
                cache_set(cache_key, {
                    "scanned": len(scan), "above200": count_above, "percent_above200": pct, "rows": scan
                })
            except Exception:
                pass

        threading.Thread(target=_compute, daemon=True).start()

        # Return partial response while background computes
        return jsonify({"ok": True, "data": {
            "scanned": 0, "above200": 0, "percent_above200": 0.0, "rows": [],
            "computing": True
        }})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/pump_candidates ────────────────────────────────────────────
@dashboard_bp.route("/api/pump_candidates")
def api_pump_candidates():
    try:
        res = cache_get_or_set("pump_candidates_v1", 300, pump_candidates, limit_pairs=40)
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/bull_estimate ───────────────────────────────────────────────
@dashboard_bp.route("/api/bull_estimate")
def api_bull_estimate():
    try:
        from app.core.bull_estimate import heuristic_bull_estimate
        fng = fng_latest()
        df = cache_get_or_set("btc_1d_df", 300, binance_klines, "BTCUSDT", "1d", 400)
        est = heuristic_bull_estimate(df, fng, fetch_dynamic_etf_events())
        return jsonify({"ok": True, "data": est})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/oi ──────────────────────────────────────────────────────────
@dashboard_bp.route("/api/oi")
def api_oi():
    try:
        spot = {}
        for sym in ["BTCUSDT", "ETHUSDT"]:
            cur = fapi_open_interest(sym)
            hist = fapi_open_interest_hist(sym, period="1d", limit=30)
            spot[sym] = {"now": cur, "hist": hist}
        return jsonify({"ok": True, "data": spot})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/hashrate ────────────────────────────────────────────────────
@dashboard_bp.route("/api/hashrate")
def api_hashrate():
    try:
        return jsonify({"ok": True, "data": blockchain_hashrate(30)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/stablecoin_flow ─────────────────────────────────────────────
@dashboard_bp.route("/api/stablecoin_flow")
def api_stablecoin_flow():
    try:
        return jsonify({"ok": True, "data": defillama_stablecoins()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/coinbase_premium ────────────────────────────────────────────
@dashboard_bp.route("/api/coinbase_premium")
def api_coinbase_premium():
    try:
        res = coinglass_coinbase_premium()
        if "error" in res:
            return jsonify({"ok": False, "error": res["error"]}), 400
        return jsonify({"ok": True, "data": res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ── /api/trade_bundle ────────────────────────────────────────────────
@dashboard_bp.get("/api/trade_bundle")
def api_trade_bundle():
    """Unified chart bundle for the integrated trading UI.

    Returns candles + volume + RSI + MACD aligned by time.
    """
    try:
        symbol = (request.args.get("symbol") or "BTCUSDT").upper()
        interval = request.args.get("interval") or "15m"
        limit = int(request.args.get("limit") or "500")
        limit = max(50, min(limit, 1000))

        cache_key = f"trade_bundle:{symbol}:{interval}:{limit}"
        cached = cache_get(cache_key, ttl=3)
        if cached is not None:
            return jsonify({"ok": True, "data": cached})

        df = binance_klines(symbol, interval, limit)
        if df is None or df.empty:
            return jsonify({"ok": False, "error": "no_data"}), 502

        # Lightweight-charts uses seconds timestamps
        t = (df["open_time"].astype(np.int64) // 1000).tolist()
        o = df["open"].astype(float).tolist()
        h = df["high"].astype(float).tolist()
        l = df["low"].astype(float).tolist()
        c = df["close"].astype(float).tolist()
        v = df["volume"].astype(float).tolist()

        closes = df["close"].astype(float)
        rsi14 = compute_rsi(closes, 14)
        macd, macd_sig, macd_hist = compute_macd(closes)

        candles = []
        volume = []
        rsi_series = []
        macd_series = []
        sig_series = []
        hist_series = []

        for i in range(len(t)):
            candles.append({"time": int(t[i]), "open": o[i], "high": h[i], "low": l[i], "close": c[i]})
            volume.append({
                "time": int(t[i]),
                "value": v[i],
                "color": "rgba(45,212,191,.55)" if c[i] >= o[i] else "rgba(251,113,133,.55)",
            })

            rv = rsi14.iloc[i]
            rsi_series.append({"time": int(t[i]), "value": None if pd.isna(rv) else float(rv)})

            mv = macd.iloc[i]
            sv = macd_sig.iloc[i]
            hv = macd_hist.iloc[i]
            macd_series.append({"time": int(t[i]), "value": None if pd.isna(mv) else float(mv)})
            sig_series.append({"time": int(t[i]), "value": None if pd.isna(sv) else float(sv)})
            hist_series.append({
                "time": int(t[i]),
                "value": None if pd.isna(hv) else float(hv),
                "color": "rgba(45,212,191,.55)" if (not pd.isna(hv) and float(hv) >= 0) else "rgba(251,113,133,.55)",
            })

        last = {
            "open": o[-1],
            "high": h[-1],
            "low": l[-1],
            "close": c[-1],
            "volume": v[-1],
            "rsi14": None if pd.isna(rsi14.iloc[-1]) else float(rsi14.iloc[-1]),
            "macd": None if pd.isna(macd.iloc[-1]) else float(macd.iloc[-1]),
            "macd_signal": None if pd.isna(macd_sig.iloc[-1]) else float(macd_sig.iloc[-1]),
            "macd_hist": None if pd.isna(macd_hist.iloc[-1]) else float(macd_hist.iloc[-1]),
        }

        out = {
            "symbol": symbol,
            "interval": interval,
            "meta": {"generated_at": utcnow().isoformat()},
            "candles": candles,
            "volume": volume,
            "rsi14": rsi_series,
            "macd": macd_series,
            "macd_signal": sig_series,
            "macd_hist": hist_series,
            "last": last,
            # optional: if tickers are warmed, include 24h change for this symbol
            "change24": next((x.get("change") for x in (cache_get(TICKERS_KEY, ttl=5) or []) if x.get("symbol") == symbol), None),
        }

        cache_set(cache_key, out)
        return jsonify({"ok": True, "data": out})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
