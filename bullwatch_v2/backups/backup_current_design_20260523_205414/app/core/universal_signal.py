# -*- coding: utf-8 -*-
"""Universal signal engine — works for ALL markets.

FAZ 17 — Market-agnostic signal evaluation using Yahoo Finance data.

Generates:
  - Entry signals (AL / PULLBACK BEKLE / ALMA)
  - Support / Resistance levels
  - SL / TP targets
  - Pullback / Fibonacci targets
  - Technical ticks (checklist)

Supports: stocks, bist, forex, commodities (+ crypto fallback)
Uses: app.core.yahoo_client for data, app.core.ta for indicators.

Market Index References:
  - stocks → ^GSPC (S&P 500)
  - bist   → XU100.IS (BIST-100)
  - forex  → DX-Y.NYB (Dollar Index)
  - commodities → ^GSPC (S&P 500 as risk proxy)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from app.cache import cache_get_or_set, utcnow
from app.core.ta import simple_sma, ema_last, atr_last, vwap_last, compute_rsi, compute_macd
from app.core.yahoo_client import get_klines

_logger = logging.getLogger("zkr_analiz.signal.universal")

# ── Market index symbols for regime checks ───────────────────────────
_MARKET_INDEX = {
    "stocks": "^GSPC",        # S&P 500
    "bist": "XU100.IS",       # BIST-100
    "forex": "DX-Y.NYB",     # US Dollar Index
    "commodities": "^GSPC",   # S&P 500 (risk proxy)
}

# ── Market-specific thresholds ───────────────────────────────────────
_MARKET_THRESHOLDS = {
    "stocks": {
        "min_ret7_pct": 1.0,
        "min_change24_pct": 0.3,
        "max_change24_pct": 8.0,
        "overextended_change24_max": 12.0,
        "heat_atr_max": 2.0,
        "require_index_regime": True,
        "require_above200": True,
    },
    "bist": {
        "min_ret7_pct": 1.5,
        "min_change24_pct": 0.5,
        "max_change24_pct": 10.0,
        "overextended_change24_max": 15.0,
        "heat_atr_max": 2.0,
        "require_index_regime": True,
        "require_above200": True,
    },
    "forex": {
        "min_ret7_pct": 0.2,
        "min_change24_pct": 0.05,
        "max_change24_pct": 2.0,
        "overextended_change24_max": 3.0,
        "heat_atr_max": 2.5,
        "require_index_regime": False,
        "require_above200": False,
    },
    "commodities": {
        "min_ret7_pct": 0.5,
        "min_change24_pct": 0.2,
        "max_change24_pct": 6.0,
        "overextended_change24_max": 10.0,
        "heat_atr_max": 2.0,
        "require_index_regime": False,
        "require_above200": True,
    },
}


def _klines_to_df(klines: List[Dict]) -> pd.DataFrame:
    """Convert klines list-of-dicts to DataFrame."""
    if not klines:
        return pd.DataFrame()
    df = pd.DataFrame(klines)
    for c in ("open", "high", "low", "close", "volume"):
        if c in df.columns:
            df[c] = df[c].astype(float)
    return df


def _compute_support_resistance(df: pd.DataFrame, n_levels: int = 3) -> Dict:
    """Compute support & resistance levels using pivot points and recent swing highs/lows."""
    if df is None or df.empty or len(df) < 20:
        return {"support": [], "resistance": []}

    closes = df["close"].astype(float)
    highs = df["high"].astype(float)
    lows = df["low"].astype(float)
    last = float(closes.iloc[-1])

    # Method 1: Classic Pivot Points (from last period)
    h = float(highs.iloc[-1])
    l = float(lows.iloc[-1])
    c = last
    pivot = (h + l + c) / 3.0
    r1 = 2 * pivot - l
    r2 = pivot + (h - l)
    r3 = h + 2 * (pivot - l)
    s1 = 2 * pivot - h
    s2 = pivot - (h - l)
    s3 = l - 2 * (h - pivot)

    # Method 2: Recent 20-bar swing highs/lows
    lookback = min(50, len(df))
    recent = df.iloc[-lookback:]
    swing_highs = []
    swing_lows = []

    for i in range(2, len(recent) - 2):
        h_val = float(recent["high"].iloc[i])
        l_val = float(recent["low"].iloc[i])
        if (h_val >= float(recent["high"].iloc[i-1]) and
            h_val >= float(recent["high"].iloc[i-2]) and
            h_val >= float(recent["high"].iloc[i+1]) and
            h_val >= float(recent["high"].iloc[i+2])):
            swing_highs.append(h_val)
        if (l_val <= float(recent["low"].iloc[i-1]) and
            l_val <= float(recent["low"].iloc[i-2]) and
            l_val <= float(recent["low"].iloc[i+1]) and
            l_val <= float(recent["low"].iloc[i+2])):
            swing_lows.append(l_val)

    # Combine — resistances above current price, supports below
    all_res = sorted(set([r1, r2, r3] + [h for h in swing_highs if h > last]), key=lambda x: x)
    all_sup = sorted(set([s1, s2, s3] + [l for l in swing_lows if l < last]), key=lambda x: -x)

    # Take closest n_levels
    resistances = [{"label": f"R{i+1}", "price": round(p, 6)} for i, p in enumerate(all_res[:n_levels])]
    supports = [{"label": f"S{i+1}", "price": round(p, 6)} for i, p in enumerate(all_sup[:n_levels])]

    return {"support": supports, "resistance": resistances}


def evaluate_market_signal(symbol: str, market: str) -> Dict:
    """Universal signal evaluation for any market.

    Parameters
    ----------
    symbol : str
        Ticker symbol (e.g. "AAPL", "THYAO.IS", "EURUSD=X", "GC=F")
    market : str
        Market type: "stocks", "bist", "forex", "commodities"

    Returns
    -------
    dict with: symbol, now, decision, note, ticks, context, risk,
               pullback_targets, support_resistance
    """
    th = _MARKET_THRESHOLDS.get(market, _MARKET_THRESHOLDS["stocks"])
    ticks = []
    index_regime = False

    # --- 1) Market Index Regime Check ---
    try:
        index_sym = _MARKET_INDEX.get(market, "^GSPC")
        cache_key = f"usig:index:{index_sym}:1d"
        idx_klines = cache_get_or_set(cache_key, 600, get_klines, index_sym, "1d", 250)
        idx_df = _klines_to_df(idx_klines)
        if not idx_df.empty and len(idx_df) >= 200:
            idx_closes = idx_df["close"].tolist()
            idx_sma200 = simple_sma(idx_closes, 200)
            idx_sma50 = simple_sma(idx_closes, 50)
            idx_last = idx_closes[-1]
            index_regime = (idx_last > (idx_sma200 or 1e18)) and ((idx_sma50 or 0) > (idx_sma200 or 1e18))
        elif not idx_df.empty:
            # Not enough data for SMA200, check SMA50 only
            idx_closes = idx_df["close"].tolist()
            idx_sma50 = simple_sma(idx_closes, 50)
            idx_last = idx_closes[-1]
            index_regime = idx_last > (idx_sma50 or 1e18) if idx_sma50 else True
        else:
            index_regime = True  # fallback: don't block
    except Exception as exc:
        _logger.debug("Index regime check failed for %s: %s", market, exc)
        index_regime = True  # fallback: don't block on error

    index_label = {
        "stocks": "S&P 500", "bist": "BIST-100",
        "forex": "Dollar Index", "commodities": "S&P 500",
    }.get(market, "Index")
    ticks.append({
        "label": f"{index_label} rejimi (SMA200 üstü & 50>200)",
        "ok": (not th["require_index_regime"]) or bool(index_regime),
    })

    # --- 2) Asset Daily Trend & Momentum ---
    above200 = False
    ret7_pct = 0.0
    change24 = 0.0
    daily_df = pd.DataFrame()

    try:
        cache_key = f"usig:daily:{symbol}:1d"
        day_klines = cache_get_or_set(cache_key, 300, get_klines, symbol, "1d", 250)
        daily_df = _klines_to_df(day_klines)

        if not daily_df.empty:
            dcl = daily_df["close"].tolist()
            if len(dcl) >= 200:
                sma200_c = simple_sma(dcl, 200)
                above200 = dcl[-1] > (sma200_c or 1e18)
            elif len(dcl) >= 50:
                sma50_c = simple_sma(dcl, 50)
                above200 = dcl[-1] > (sma50_c or 1e18)
            else:
                above200 = True  # not enough history

            ret7_pct = (dcl[-1] / dcl[-8] - 1.0) * 100 if len(dcl) >= 8 else 0.0
            change24 = ((dcl[-1] / dcl[-2]) - 1.0) * 100 if len(dcl) >= 2 else 0.0
    except Exception as exc:
        _logger.debug("Daily data failed for %s: %s", symbol, exc)

    ticks.append({"label": "Günlük trend (SMA200 üstü)", "ok": (not th["require_above200"]) or bool(above200)})
    ticks.append({"label": f"Haftalık momentum (ret7 ≥ {th['min_ret7_pct']:.1f}%)", "ok": ret7_pct >= th["min_ret7_pct"]})
    ticks.append({"label": f"Günlük momentum (change24 ≥ {th['min_change24_pct']:.1f}%)", "ok": change24 >= th["min_change24_pct"]})

    overextended = change24 >= th["overextended_change24_max"]
    ideal_upto = change24 <= th["max_change24_pct"]
    ticks.append({"label": f"Aşırı uzama değil (24h ≤ {th['overextended_change24_max']:.1f}%)", "ok": not overextended})
    ticks.append({"label": f"İdeal aralıkta (24h ≤ {th['max_change24_pct']:.1f}%)", "ok": ideal_upto})

    # --- 3) RSI & MACD (Daily) ---
    rsi_val = None
    macd_bullish = False
    try:
        if not daily_df.empty and len(daily_df) >= 26:
            rsi_series = compute_rsi(daily_df["close"], 14)
            rsi_val = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None

            macd_line, signal_line, hist = compute_macd(daily_df["close"])
            if not pd.isna(hist.iloc[-1]):
                macd_bullish = float(hist.iloc[-1]) > 0
    except Exception:
        pass

    rsi_ok = rsi_val is not None and 30 <= rsi_val <= 70
    ticks.append({"label": f"RSI aralıkta (30-70) → {rsi_val:.1f}" if rsi_val else "RSI hesaplanamadı", "ok": rsi_ok})
    ticks.append({"label": "MACD histogram pozitif", "ok": macd_bullish})

    # --- 4) Intraday Confirmation (1h data for non-crypto) ---
    last_h = ema20_h = atr14_h = vwap_h = None
    cond_reclaim = False
    try:
        cache_key = f"usig:hourly:{symbol}:1h"
        h_klines = cache_get_or_set(cache_key, 120, get_klines, symbol, "1h", 200)
        h_df = _klines_to_df(h_klines)

        if not h_df.empty and len(h_df) >= 20:
            close_series = h_df["close"].tolist()
            last_h = float(close_series[-1])
            ema20_h = ema_last(close_series, 20)
            atr14_h = atr_last(h_df, 14)
            vwap_h = vwap_last(h_df, 96)
            cond_reclaim = (
                (ema20_h is not None and last_h > ema20_h) and
                (vwap_h is not None and last_h > vwap_h)
            )
            ticks.append({"label": "1h EMA20 üstü", "ok": ema20_h is not None and last_h > ema20_h})
            ticks.append({"label": "1h VWAP üstü", "ok": vwap_h is not None and last_h > vwap_h})

            heat_ok = False
            if atr14_h and ema20_h:
                heat = (last_h - ema20_h) / max(atr14_h, 1e-9)
                heat_ok = heat <= th["heat_atr_max"]
                ticks.append({"label": f"Sıcaklık (EMA mesafesi ≤ {th['heat_atr_max']:.2f} ATR)", "ok": heat_ok})
            else:
                ticks.append({"label": "Sıcaklık (EMA/ATR hesaplandı)", "ok": False})
    except Exception as exc:
        _logger.debug("Hourly data failed for %s: %s", symbol, exc)
        ticks.append({"label": "1h EMA20/VWAP teyidi", "ok": False})

    # --- 5) Decision Logic ---
    decision = "ALMA"
    note = ""

    if th["require_index_regime"] and not index_regime:
        decision = "ALMA"
        note = f"{index_label} rejimi uygun değil."
    elif th["require_above200"] and not above200:
        decision = "ALMA"
        note = "Günlük trend zayıf (SMA200 altı)."
    elif ret7_pct < th["min_ret7_pct"] or change24 < th["min_change24_pct"]:
        decision = "ALMA"
        note = "Momentum yetersiz."
    elif overextended:
        decision = "PULLBACK BEKLE"
        note = f"Günlük değişim yüksek (≈ {change24:.1f}%). Çekilme bekleyin."
    elif not cond_reclaim:
        decision = "PULLBACK BEKLE"
        note = "1h EMA20 ve/veya VWAP üzeri kapanış teyidi yok."
    elif rsi_val and rsi_val > 70:
        decision = "PULLBACK BEKLE"
        note = f"RSI aşırı alım bölgesinde ({rsi_val:.1f})."
    else:
        decision = "AL"
        note = "Rejim + trend + teknik teyit uyumlu."

    # --- 6) SL/TP ---
    sl = tp1 = tp2 = None
    ref_price = last_h or (float(daily_df["close"].iloc[-1]) if not daily_df.empty else None)
    ref_atr = atr14_h

    if not ref_atr and not daily_df.empty and len(daily_df) >= 15:
        ref_atr = atr_last(daily_df, 14)

    if ref_price and ref_atr:
        sl = round(ref_price - 1.5 * ref_atr, 6)
        tp1 = round(ref_price + 1.0 * ref_atr, 6)
        tp2 = round(ref_price + 2.0 * ref_atr, 6)

    # --- 7) Pullback Targets ---
    pullbacks = []
    try:
        if ema20_h:
            pullbacks.append({"label": "EMA20 (1h)", "price": round(ema20_h, 6)})
        if vwap_h:
            pullbacks.append({"label": "VWAP (1h, ~son 96 bar)", "price": round(vwap_h, 6)})

        # Daily EMA20 as major pullback level
        if not daily_df.empty and len(daily_df) >= 20:
            d_ema20 = ema_last(daily_df["close"].tolist(), 20)
            if d_ema20:
                pullbacks.append({"label": "EMA20 (Günlük)", "price": round(d_ema20, 6)})

        # Fibonacci levels from hourly data
        if 'h_df' in dir() and h_df is not None and not h_df.empty and len(h_df) >= 30:
            h = float(h_df["high"].iloc[-96:].max())
            l_val = float(h_df["low"].iloc[-96:].min())
            rng = h - l_val
            if rng > 0:
                for lv, name in [(0.236, "Fibo 23.6%"), (0.382, "Fibo 38.2%"), (0.5, "Fibo 50%"), (0.618, "Fibo 61.8%")]:
                    pullbacks.append({"label": name, "price": round(h - rng * lv, 6)})
    except Exception:
        pass

    # --- 8) Support / Resistance ---
    sr = _compute_support_resistance(daily_df)

    return {
        "symbol": symbol,
        "market": market,
        "now": utcnow().isoformat(),
        "decision": decision,
        "note": note,
        "ticks": ticks,
        "context": {
            "change24_pct": round(change24, 2),
            "ret7_pct": round(ret7_pct, 2),
            "above200_1d": bool(above200),
            "index_regime_ok": bool(index_regime),
            "rsi": round(rsi_val, 2) if rsi_val else None,
            "macd_bullish": macd_bullish,
            "last_h": last_h,
            "ema20_h": ema20_h,
            "vwap_h": vwap_h,
            "atr14_h": atr14_h,
        },
        "risk": {
            "suggested_risk_level": sl,
            "target_1": tp1,
            "target_2": tp2,
            "rationale": "Risk=1.5×ATR(14,1h); T1=+1R, T2=+2R; ATR-trailing önerilir.",
        },
        "pullback_targets": pullbacks,
        "support_resistance": sr,
    }


def scan_market_signals(market: str, symbols: List[str], top_n: int = 20) -> List[Dict]:
    """Scan a list of symbols and return top signals sorted by strength.

    Parameters
    ----------
    market : str
        Market type
    symbols : list of str
        Symbol list to scan
    top_n : int
        Max results to return

    Returns
    -------
    list of signal dicts, sorted by decision strength
    """
    results = []
    for sym in symbols:
        try:
            sig = evaluate_market_signal(sym, market)
            # Score: AL=3, PULLBACK BEKLE=2, ALMA=1
            score = 3 if sig["decision"] == "AL" else (2 if "BEKLE" in sig["decision"] else 1)
            sig["_score"] = score
            results.append(sig)
        except Exception as exc:
            _logger.debug("Signal scan failed for %s: %s", sym, exc)
            continue

    # Sort by score descending, then by change24 descending
    results.sort(key=lambda x: (x.get("_score", 0), x.get("context", {}).get("change24_pct", 0)), reverse=True)

    # Clean up internal score
    for r in results:
        r.pop("_score", None)

    return results[:top_n]
