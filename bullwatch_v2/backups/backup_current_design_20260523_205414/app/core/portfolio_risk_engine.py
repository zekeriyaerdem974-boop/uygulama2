# -*- coding: utf-8 -*-
"""Portfolio Risk Engine — FAZ 39.

Portföy risk analizi: volatilite, drawdown, konsantrasyon riski,
korelasyon matrisi, genel risk skoru.

Public API:
  calculate_volatility(assets)
  calculate_drawdown(assets)
  calculate_concentration_risk(allocations)
  calculate_correlation_matrix(assets)
  calculate_risk_score(user_id)
"""
from __future__ import annotations

import logging
import math
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.portfolio.risk")

# ── Risk Score Bands ──────────────────────────────────────────────
RISK_BANDS = [
    (0, 20, "Very Low Risk", "Çok Düşük Risk"),
    (20, 40, "Low Risk", "Düşük Risk"),
    (40, 60, "Moderate Risk", "Orta Risk"),
    (60, 80, "High Risk", "Yüksek Risk"),
    (80, 100, "Extreme Risk", "Aşırı Yüksek Risk"),
]

# Known asset volatility estimates (annualized)
_VOLATILITY_ESTIMATES: Dict[str, float] = {
    # Crypto
    "BTCUSDT": 0.65, "ETHUSDT": 0.75, "SOLUSDT": 0.95, "BNBUSDT": 0.70,
    "XRPUSDT": 0.85, "DOGEUSDT": 1.10, "ADAUSDT": 0.90, "AVAXUSDT": 0.95,
    "DOTUSDT": 0.90, "LINKUSDT": 0.85, "MATICUSDT": 0.90,
    # Stablecoins
    "USDTUSDT": 0.01, "USDCUSDT": 0.01, "BUSDUSDT": 0.01,
    # Stocks / ETFs
    "SPY": 0.18, "QQQ": 0.22, "AAPL": 0.28, "MSFT": 0.25,
    "GOOGL": 0.28, "AMZN": 0.30, "TSLA": 0.55, "NVDA": 0.45,
    "META": 0.35, "AMD": 0.45,
    # Commodities
    "GC=F": 0.15, "SI=F": 0.25, "CL=F": 0.35, "NG=F": 0.50,
    # Forex
    "EURUSD=X": 0.08, "GBPUSD=X": 0.10, "USDJPY=X": 0.10,
    # BIST
    "XU100.IS": 0.30, "THYAO.IS": 0.40, "ASELS.IS": 0.38,
    "GARAN.IS": 0.42, "EREGL.IS": 0.35,
}

# Correlation groups — assets in same group are correlated
_CORRELATION_GROUPS = {
    "crypto_major": ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
    "crypto_alt": ["SOLUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
                    "MATICUSDT", "XRPUSDT", "DOGEUSDT"],
    "us_tech": ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "AMD", "QQQ"],
    "us_broad": ["SPY"],
    "precious_metals": ["GC=F", "SI=F"],
    "energy": ["CL=F", "NG=F"],
    "stablecoins": ["USDTUSDT", "USDCUSDT", "BUSDUSDT"],
    "bist": ["XU100.IS", "THYAO.IS", "ASELS.IS", "GARAN.IS", "EREGL.IS"],
    "forex": ["EURUSD=X", "GBPUSD=X", "USDJPY=X"],
}

# Market-level default volatility when symbol not in estimates
_MARKET_DEFAULT_VOL = {
    "crypto": 0.80,
    "stocks": 0.30,
    "bist": 0.35,
    "forex": 0.10,
    "commodities": 0.25,
}


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def calculate_volatility(assets: List[Dict]) -> Dict:
    """Estimate portfolio volatility from known asset volatilities.

    Returns weighted portfolio volatility (approximate — no live history).
    """
    if not assets:
        return {"portfolio_volatility": 0.0, "asset_volatilities": {}}

    total_value = sum(a["amount"] * (a.get("current_price") or a["entry_price"]) for a in assets)
    if total_value <= 0:
        return {"portfolio_volatility": 0.0, "asset_volatilities": {}}

    weighted_vol_sq = 0.0
    asset_vols = {}

    for a in assets:
        symbol = a["symbol"]
        market = a.get("market", "crypto")
        value = a["amount"] * (a.get("current_price") or a["entry_price"])
        weight = value / total_value

        vol = _VOLATILITY_ESTIMATES.get(symbol, _MARKET_DEFAULT_VOL.get(market, 0.50))
        asset_vols[symbol] = round(vol, 4)
        weighted_vol_sq += (weight * vol) ** 2

    # Simplified portfolio vol (assumes partial correlation via sqrt)
    port_vol = math.sqrt(weighted_vol_sq) * 1.3  # adjustment for correlation
    port_vol = min(port_vol, 1.5)  # cap

    return {
        "portfolio_volatility": round(port_vol, 4),
        "asset_volatilities": asset_vols,
    }


def calculate_drawdown(assets: List[Dict]) -> Dict:
    """Estimate potential max drawdown from portfolio composition.

    Uses entry vs current price to see realized drawdown and
    estimates forward-looking max drawdown from volatility.
    """
    if not assets:
        return {"current_drawdown": 0.0, "max_drawdown_estimate": 0.0}

    total_cost = 0.0
    total_value = 0.0

    for a in assets:
        cost = a["amount"] * a["entry_price"]
        value = a["amount"] * (a.get("current_price") or a["entry_price"])
        total_cost += cost
        total_value += value

    current_dd = 0.0
    if total_cost > 0 and total_value < total_cost:
        current_dd = ((total_value - total_cost) / total_cost) * 100

    # Estimate max drawdown from volatility (Boucaud formula approximation)
    vol_data = calculate_volatility(assets)
    port_vol = vol_data["portfolio_volatility"]
    # Empirical: max_dd ≈ -2.5 * annual_vol (rough approximation)
    max_dd_est = -2.5 * port_vol * 100

    return {
        "current_drawdown": round(current_dd, 2),
        "max_drawdown_estimate": round(max(max_dd_est, -95.0), 2),
    }


def calculate_concentration_risk(allocations: List[Dict]) -> Dict:
    """Calculate concentration risk (Herfindahl-Hirschman Index style).

    HHI: sum of squared allocation percentages.
    One asset = 10000 (100%), equal 10 assets = 1000.

    Returns score 0-100 where 100 is maximum concentration.
    """
    if not allocations:
        return {"concentration_score": 0, "top_asset": "", "top_allocation": 0, "hhi": 0}

    hhi = sum(a["allocation"] ** 2 for a in allocations)
    # Normalize: HHI range is [10000/n, 10000] → map to [0, 100]
    n = len(allocations)
    min_hhi = 10000 / n if n > 0 else 10000
    if hhi >= 10000:
        score = 100
    elif n <= 1:
        score = 100
    else:
        score = ((hhi - min_hhi) / (10000 - min_hhi)) * 100
    score = max(0, min(100, score))

    top = max(allocations, key=lambda x: x["allocation"])

    return {
        "concentration_score": round(score, 1),
        "top_asset": top["symbol"],
        "top_allocation": top["allocation"],
        "hhi": round(hhi, 1),
        "asset_count": n,
    }


def calculate_correlation_matrix(assets: List[Dict]) -> Dict:
    """Build approximate correlation matrix from asset group memberships.

    Returns pairwise correlation estimates and overall diversification score.
    """
    if not assets:
        return {"matrix": {}, "diversification_score": 0}

    symbols = [a["symbol"] for a in assets]
    n = len(symbols)

    # Build group membership
    sym_groups = {}
    for sym in symbols:
        groups = []
        for gname, members in _CORRELATION_GROUPS.items():
            if sym in members:
                groups.append(gname)
        sym_groups[sym] = groups

    # Build pairwise correlation
    matrix = {}
    total_pairs = 0
    correlated_pairs = 0

    for i, s1 in enumerate(symbols):
        row = {}
        for j, s2 in enumerate(symbols):
            if i == j:
                row[s2] = 1.0
            else:
                # Same group → high correlation, different group → low
                common = set(sym_groups.get(s1, [])) & set(sym_groups.get(s2, []))
                if common:
                    row[s2] = 0.75
                    if i < j:
                        correlated_pairs += 1
                else:
                    # Same market type → moderate
                    m1 = next((a["market"] for a in assets if a["symbol"] == s1), "")
                    m2 = next((a["market"] for a in assets if a["symbol"] == s2), "")
                    if m1 == m2:
                        row[s2] = 0.45
                        if i < j:
                            correlated_pairs += 0.5
                    else:
                        row[s2] = 0.15
                if i < j:
                    total_pairs += 1
        matrix[s1] = row

    # Diversification score: lower correlation = better diversification
    if total_pairs > 0:
        avg_corr = correlated_pairs / total_pairs
        div_score = max(0, min(100, (1 - avg_corr) * 100))
    else:
        div_score = 0 if n <= 1 else 50

    return {
        "matrix": matrix,
        "diversification_score": round(div_score, 1),
        "total_assets": n,
    }


def calculate_risk_score(user_id: str) -> Dict:
    """Calculate overall portfolio risk score (0-100).

    Combines:
    - Volatility (35%)
    - Concentration (30%)
    - Drawdown (20%)
    - Diversification inverse (15%)
    """
    from app.core.portfolio_engine import get_assets, calculate_allocation

    assets = get_assets(user_id)
    if not assets:
        return {
            "risk_score": 0,
            "risk_label": "N/A",
            "risk_label_tr": "Portföy Boş",
            "volatility": 0,
            "drawdown": 0,
            "concentration_risk": 0,
            "diversification_score": 0,
            "top_asset": "",
            "components": {},
        }

    # Component calculations
    vol_data = calculate_volatility(assets)
    dd_data = calculate_drawdown(assets)
    alloc_data = calculate_allocation(user_id)
    conc_data = calculate_concentration_risk(alloc_data["allocations"])
    corr_data = calculate_correlation_matrix(assets)

    # Normalize scores to 0-100
    vol_score = min(100, (vol_data["portfolio_volatility"] / 1.0) * 100)
    dd_score = min(100, abs(dd_data["max_drawdown_estimate"]))
    conc_score = conc_data["concentration_score"]
    div_inv_score = 100 - corr_data["diversification_score"]

    # Weighted risk score
    risk_score = (
        vol_score * 0.35 +
        conc_score * 0.30 +
        dd_score * 0.20 +
        div_inv_score * 0.15
    )
    risk_score = max(0, min(100, risk_score))

    # Map to risk band
    risk_label = "Moderate Risk"
    risk_label_tr = "Orta Risk"
    for lo, hi, label_en, label_tr in RISK_BANDS:
        if lo <= risk_score < hi:
            risk_label = label_en
            risk_label_tr = label_tr
            break
    else:
        if risk_score >= 80:
            risk_label = "Extreme Risk"
            risk_label_tr = "Aşırı Yüksek Risk"

    return {
        "risk_score": round(risk_score, 1),
        "risk_label": risk_label,
        "risk_label_tr": risk_label_tr,
        "volatility": vol_data["portfolio_volatility"],
        "drawdown": dd_data["current_drawdown"],
        "max_drawdown_estimate": dd_data["max_drawdown_estimate"],
        "concentration_risk": conc_data["concentration_score"],
        "top_asset": conc_data["top_asset"],
        "top_allocation": conc_data.get("top_allocation", 0),
        "diversification_score": corr_data["diversification_score"],
        "asset_count": len(assets),
        "components": {
            "volatility_score": round(vol_score, 1),
            "concentration_score": round(conc_score, 1),
            "drawdown_score": round(dd_score, 1),
            "diversification_inv_score": round(div_inv_score, 1),
        },
        "asset_volatilities": vol_data["asset_volatilities"],
    }
