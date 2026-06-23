"""Bull market heuristic estimator.

FAZ 11 — Extracted from legacy_monolith.py.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.cache import utcnow
from app.core.etf_tracker import fetch_dynamic_etf_events
from app.core.ta import simple_sma


def heuristic_bull_estimate(btc_df, fng, etf_events):
    """Score-based bull market phase estimator using BTC technicals + sentiment."""
    if btc_df is None or btc_df.empty:
        return {
            "bull_start_estimate": None,
            "bull_end_estimate": None,
            "phase_label": "unknown",
            "score": 0,
            "explain": ["Veri yok"],
        }

    closes = btc_df["close"].tolist()
    sma200 = simple_sma(closes, 200)
    sma50 = simple_sma(closes, 50)
    sma20 = simple_sma(closes, 20)
    last = closes[-1]

    checks, score = [], 0

    cond1 = last > (sma200 or last + 1)
    checks.append(("BTC 200D SMA üstünde", bool(cond1)))
    score += 1 if cond1 else 0

    cond2 = (sma50 or 0) > (sma200 or 1e12)
    checks.append(("50D > 200D", bool(cond2)))
    score += 1 if cond2 else 0

    cond3 = (sma20 or 0) > (sma50 or 1e12)
    checks.append(("20D > 50D", bool(cond3)))
    score += 1 if cond3 else 0

    ret90 = (closes[-1] / closes[-90] - 1.0) if len(closes) >= 90 else 0.0
    cond4 = ret90 > 0.20
    checks.append((f"Son 90g BTC getirisi {ret90:.1%}", bool(cond4)))
    score += 1 if cond4 else 0

    fng_val = fng.get("value")
    cond5 = (fng_val or 0) >= 55
    checks.append((f"FNG ≥ 55 (şu an: {fng_val})", bool(cond5)))
    score += 1 if cond5 else 0

    soon_cut = utcnow() + timedelta(days=60)
    near = []
    for e in etf_events:
        dt = e.get("next_deadline_est") or e.get("date")
        if not dt:
            continue
        try:
            d = datetime.fromisoformat(dt) if "T" in dt else datetime.fromisoformat(dt + "T00:00:00")
            d = d.replace(tzinfo=timezone.utc)
            if d <= soon_cut and e.get("status") != "none":
                near.append(e)
        except Exception:
            pass

    cond6 = len(near) > 0
    checks.append((f"ETF kritik pencereler (≤60g): {len(near)}", bool(cond6)))
    score += 1 if cond6 else 0

    if score <= 1:
        phase = "Dip Toplama"
    elif score <= 3:
        phase = "İnançlı Yükseliş"
    elif score in (4, 5):
        phase = "Genişleme"
    else:
        phase = "FOMO/Zirve Yakını"

    now = utcnow()
    start_in_days = max(0, 120 - score * 15)
    bull_start_est = now + timedelta(days=start_in_days)
    bull_end_est = now + timedelta(days=480 + (6 - score) * 15)
    explain = [f"{l}: {'✓' if ok else '×'}" for (l, ok) in checks]
    explain.append("Halving sonrası zirve penceresi ~ 2025-04 – 2025-10 (tarihsel bağlam)")

    return {
        "bull_start_estimate": bull_start_est.isoformat(),
        "bull_end_estimate": bull_end_est.isoformat(),
        "phase_label": phase,
        "score": int(score),
        "checks": checks,
        "explain": explain,
    }
