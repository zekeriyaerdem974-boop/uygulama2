from __future__ import annotations

import numpy as np
import pandas as pd
from flask import Blueprint, current_app, jsonify, request

from app.core.ta import compute_rsi, compute_macd


bp = Blueprint("indicators", __name__, url_prefix="/api/indicators")


def _svc():
    return current_app.extensions["market_data"]


@bp.get("/rsi")
def rsi():
    svc = _svc()
    raw_symbol = (request.args.get("symbol") or "BTCUSDT").upper()
    symbol, requested = svc.normalize_symbol(raw_symbol)
    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "200")
    period = int(request.args.get("period") or "14")

    rows = svc.get_klines(symbol, interval, limit, ttl_s=2.0)
    closes = pd.Series([r["close"] for r in rows], dtype=float)
    t = [int(r["open_time"] // 1000) for r in rows]
    rsi_series = compute_rsi(closes, period)

    out = [
        {"time": int(t[i]), "value": None if pd.isna(rsi_series.iloc[i]) else float(rsi_series.iloc[i])}
        for i in range(len(t))
    ]
    resp = {"ok": True, "symbol": symbol, "interval": interval, "rsi": out}
    if requested:
        resp["requested_symbol"] = requested
    return jsonify(resp)


@bp.get("/macd")
def macd():
    svc = _svc()
    raw_symbol = (request.args.get("symbol") or "BTCUSDT").upper()
    symbol, requested = svc.normalize_symbol(raw_symbol)
    interval = request.args.get("interval") or "15m"
    limit = int(request.args.get("limit") or "300")

    rows = svc.get_klines(symbol, interval, limit, ttl_s=2.0)
    closes = pd.Series([r["close"] for r in rows], dtype=float)
    t = [int(r["open_time"] // 1000) for r in rows]

    m, s, h = compute_macd(closes)
    macd_series = [{"time": int(t[i]), "value": None if pd.isna(m.iloc[i]) else float(m.iloc[i])} for i in range(len(t))]
    sig_series = [{"time": int(t[i]), "value": None if pd.isna(s.iloc[i]) else float(s.iloc[i])} for i in range(len(t))]
    hist_series = [{"time": int(t[i]), "value": None if pd.isna(h.iloc[i]) else float(h.iloc[i])} for i in range(len(t))]

    resp = {
        "ok": True,
        "symbol": symbol,
        "interval": interval,
        "macd": macd_series,
        "signal": sig_series,
        "hist": hist_series,
    }
    if requested:
        resp["requested_symbol"] = requested
    return jsonify(resp)
