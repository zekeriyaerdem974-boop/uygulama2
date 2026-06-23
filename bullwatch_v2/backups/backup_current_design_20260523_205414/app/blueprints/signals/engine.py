"""Signal evaluation engine.

FAZ 5 — ``evaluate_entry_signal()`` extracted from ``legacy_monolith.py``.
All decision logic, tick generation, pullback targets, and risk
calculations are preserved **exactly** as before.

Dependencies:
  - app.core.ta          → simple_sma, ema_last, atr_last, vwap_last
  - app.core.binance_client → binance_klines, fetch_klines_df
  - app.core.thresholds  → get_thresholds
  - app.cache            → cache_get_or_set, utcnow
"""
from __future__ import annotations

from typing import Dict

from app.cache import cache_get_or_set, utcnow
from app.core.ta import simple_sma, ema_last, atr_last, vwap_last
from app.core.binance_client import binance_klines, fetch_klines_df
from app.core.thresholds import get_thresholds


def evaluate_entry_signal(symbol: str, pump_row: Dict = None, thresholds: Dict = None) -> Dict:
    """
    Karar: AL / PULLBACK BEKLE / ALMA
    Kullanılan eşikler: get_thresholds() -> runtime (POST /api/thresholds ile güncellenir)
    """
    th = thresholds or get_thresholds()
    ticks = []

    # --- 1) BTC rejimi ---
    try:
        btc_df = cache_get_or_set("btc_1d_df", 300, binance_klines, "BTCUSDT", "1d", 400)
        closes_btc = btc_df["close"].tolist()
        btc_sma200 = simple_sma(closes_btc, 200)
        btc_sma50 = simple_sma(closes_btc, 50)
        btc_last = closes_btc[-1]
        btc_regime = (btc_last > (btc_sma200 or 1e18)) and ((btc_sma50 or 0) > (btc_sma200 or 1e18))
    except Exception:
        btc_regime = False
    ticks.append({"label": "BTC rejimi (SMA200 üstü & 50>200)", "ok": (not th["require_btc_regime"]) or bool(btc_regime)})

    # --- 2) Coin 1D trend/momentum ---
    try:
        ddf = binance_klines(symbol, "1d", 220)
        dcl = ddf["close"].tolist()
        if len(dcl) >= 200:
            sma200_c = simple_sma(dcl, 200)
            last_c = dcl[-1]
            above200 = last_c > (sma200_c or 1e18)
        else:
            above200 = False
        ret7_pct = (dcl[-1]/dcl[-8]-1.0)*100 if len(dcl) >= 8 else 0.0
        if pump_row and "change24_pct" in pump_row:
            change24 = float(pump_row["change24_pct"])
        else:
            change24 = ((dcl[-1] / dcl[-2]) - 1.0) * 100 if len(dcl) >= 2 else 0.0
    except Exception:
        above200, ret7_pct, change24 = False, 0.0, 0.0

    # Trend ve momentum tick'leri
    ticks.append({"label": "Coin 1D trend (SMA200 üstü)", "ok": (not th["require_above200"]) or bool(above200)})
    ticks.append({"label": f"Haftalık momentum (ret7 ≥ {th['min_ret7_pct']:.1f}%)", "ok": ret7_pct >= th["min_ret7_pct"]})
    ticks.append({"label": f"Günlük momentum (change24 ≥ {th['min_change24_pct']:.1f}%)", "ok": change24 >= th["min_change24_pct"]})

    # Aşırı uzama ve ideal aralık tick'leri
    overextended = change24 >= th["overextended_change24_max"]
    ideal_upto = change24 <= th["max_change24_pct"]
    ticks.append({"label": f"Aşırı uzama değil (24h ≤ {th['overextended_change24_max']:.1f}%)", "ok": not overextended})
    ticks.append({"label": f"İdeal aralıkta (24h ≤ {th['max_change24_pct']:.1f}%)", "ok": ideal_upto})

    # --- 3) 15m teyit: EMA20 & VWAP & sıcaklık ---
    last15 = ema20_15 = atr14_15 = vwap96_15 = None
    cond_reclaim = False
    try:
        m15 = fetch_klines_df(symbol, "15m", 200)
        close_series = m15["close"].astype(float).tolist()
        last15 = float(close_series[-1])
        ema20_15 = ema_last(close_series, 20)
        atr14_15 = atr_last(m15, 14)
        vwap96_15 = vwap_last(m15, 96)
        cond_reclaim = (ema20_15 is not None and last15 > ema20_15) and (vwap96_15 is not None and last15 > vwap96_15)
        ticks.append({"label": "15m EMA20 üstü", "ok": (ema20_15 is not None and last15 > ema20_15)})
        ticks.append({"label": "15m VWAP üstü", "ok": (vwap96_15 is not None and last15 > vwap96_15)})

        heat_ok = False
        if atr14_15 and ema20_15:
            heat = (last15 - ema20_15) / max(atr14_15, 1e-9)
            heat_ok = heat <= th["heat_atr_max"]
            ticks.append({"label": f"Sıcaklık (EMA mesafesi ≤ {th['heat_atr_max']:.2f} ATR)", "ok": heat_ok})
        else:
            ticks.append({"label": f"Sıcaklık (EMA/ATR hesaplandı)", "ok": False})
    except Exception:
        ticks.append({"label": "15m EMA20/VWAP teyidi", "ok": False})

    # --- 4) Karar mantığı ---
    decision = "ALMA"
    note = ""
    sl = tp1 = tp2 = None
    pullbacks = []

    # Pullback hedefleri (her durumda üret)
    try:
        if ema20_15:
            pullbacks.append({"label": "EMA20 (15m)", "price": round(ema20_15, 6)})
        if vwap96_15:
            pullbacks.append({"label": "VWAP (15m, ~son 24s)", "price": round(vwap96_15, 6)})
        if 'm15' in locals() and m15 is not None and len(m15) >= 30:
            h = float(m15["high"].iloc[-96:].max())
            l = float(m15["low"].iloc[-96:].min())
            rng = h - l
            for lv, name in [(0.236, "Fibo 23.6%"), (0.382, "Fibo 38.2%"), (0.5, "Fibo 50%")]:
                pullbacks.append({"label": name, "price": round(h - rng*lv, 6)})
    except Exception:
        pass

    # Karar ağaçları
    if th["require_btc_regime"] and not btc_regime:
        decision = "ALMA"; note = "BTC rejimi uygun değil."
    elif th["require_above200"] and not above200:
        decision = "ALMA"; note = "Coin 1D trendi zayıf (SMA200 altı)."
    elif ret7_pct < th["min_ret7_pct"] or change24 < th["min_change24_pct"]:
        decision = "ALMA"; note = "Momentum yetersiz."
    elif overextended:
        decision = "PULLBACK BEKLE"; note = f"Günlük değişim yüksek (≈ {change24:.1f}%). Çekilme/konsolidasyon bekleyin."
    elif not cond_reclaim:
        decision = "PULLBACK BEKLE"; note = "15m EMA20 ve/veya VWAP üzeri kapanış teyidi yok."
    else:
        decision = "AL"; note = "Rejim + trend + 15m reclaim uyumlu."

    # SL/TP önerisi (bilgilendirici)
    if last15 and atr14_15:
        sl = round(last15 - 1.5 * atr14_15, 6)
        tp1 = round(last15 + 1.0 * atr14_15, 6)
        tp2 = round(last15 + 2.0 * atr14_15, 6)

    return {
        "symbol": symbol,
        "now": utcnow().isoformat(),
        "decision": decision,              # "AL" | "PULLBACK BEKLE" | "ALMA"
        "note": note,
        "ticks": ticks,                    # [{label, ok}]
        "context": {
            "change24_pct": round(change24, 2),
            "ret7_pct": round(ret7_pct, 2),
            "above200_1d": bool(above200),
            "btc_regime_ok": bool(btc_regime),
            "last15": last15,
            "ema20_15": ema20_15,
            "vwap96_15": vwap96_15,
            "atr14_15": atr14_15,
        },
        "risk": {
            "suggested_risk_level": sl,
            "target_1": tp1,
            "target_2": tp2,
            "rationale": "Risk=1.5×ATR(14,15m); T1=+1R, T2=+2R; kalan için ATR-trailing önerilir."
        },
        "pullback_targets": pullbacks      # potansiyel gerileme hedefleri
    }
