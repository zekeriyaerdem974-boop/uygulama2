# -*- coding: utf-8 -*-
"""AI Personal Market Agent — FAZ 49.

Aggregates signals from portfolio, opportunity, news, activity, and
market data engines to produce personalised AI intelligence.

LEGAL_SAFE_MODE: No buy/sell/trade instructions.  Uses only approved
terminology — bullish, bearish, momentum increasing/decreasing,
volatility spike, sector rotation, risk increasing/decreasing,
market activity.

Public API:
  generate_brief(user_id)            → dict   # AI Personal Brief
  analyze_portfolio(user_id)         → dict   # Portfolio intelligence
  analyze_watchlist(user_id)         → dict   # Watchlist intelligence
  explain_opportunity(opp_id)        → dict   # AI opportunity explanation
  get_market_summary()               → dict   # General market summary
  get_top_opportunities(limit)       → list   # Top AI opportunities
  ask_agent(user_id, question)       → dict   # Free-form question
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.cache import cache_get, cache_set

_logger = logging.getLogger("zkr_analiz.ai_market_agent")

# ── Cache TTLs ────────────────────────────────────────────────────
BRIEF_CACHE_TTL = 900       # 15 minutes
MARKET_CACHE_TTL = 900      # 15 minutes
PORTFOLIO_CACHE_TTL = 900   # 15 minutes
WATCHLIST_CACHE_TTL = 900   # 15 minutes
OPP_EXPLAIN_CACHE_TTL = 900 # 15 minutes

# ── LEGAL_SAFE_MODE — allowed wording ─────────────────────────────
SAFE_LABELS = {
    "bullish": "yukarı yönlü momentum gözlemleniyor",
    "bearish": "aşağı yönlü hareket gözlemleniyor",
    "momentum_up": "artan momentum dikkat çekiyor",
    "momentum_down": "azalan momentum gözlemleniyor",
    "volatility_spike": "yüksek volatilite gözlemleniyor",
    "sector_rotation": "sektör rotasyonu dikkat çekiyor",
    "risk_up": "risk seviyesi artıyor",
    "risk_down": "risk seviyesi azalıyor",
    "high_volume": "normalin üzerinde hacim dikkat çekiyor",
    "neutral": "nötr seyir gözlemleniyor",
}

BANNED_WORDS = frozenset({
    "BUY", "SELL", "ENTRY", "EXIT", "TAKE PROFIT", "STOP LOSS",
    "TRADE NOW", "AL", "SAT", "GİRİŞ", "ÇIKIŞ", "KÂR AL", "ZARAR KES",
})

# ── Sentiment labels ─────────────────────────────────────────────
_SENTIMENT_MAP = {
    "very_bullish": {"label": "Güçlü Yukarı Momentum", "icon": "🟢", "color": "#00C853"},
    "bullish":      {"label": "Yukarı Momentum",       "icon": "🟩", "color": "#4CAF50"},
    "neutral":      {"label": "Nötr Seyir",             "icon": "⬜", "color": "#9E9E9E"},
    "bearish":      {"label": "Aşağı Momentum",         "icon": "🟥", "color": "#F44336"},
    "very_bearish": {"label": "Güçlü Aşağı Momentum",  "icon": "🔴", "color": "#D50000"},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize(text: str) -> str:
    """Strip banned words from text."""
    result = text
    for word in BANNED_WORDS:
        # Case-insensitive replacement
        lower = result.lower()
        idx = lower.find(word.lower())
        while idx != -1:
            result = result[:idx] + "***" + result[idx + len(word):]
            lower = result.lower()
            idx = lower.find(word.lower())
    return result


# ══════════════════════════════════════════════════════════════════
# DATA COLLECTORS — gather signals from each engine
# ══════════════════════════════════════════════════════════════════

def _collect_market_data() -> Dict:
    """Collect top-level market snapshot data."""
    data = {
        "btc_price": None, "btc_change": None,
        "eth_price": None, "eth_change": None,
        "fng_value": None, "fng_label": None,
        "top_gainers": [], "top_losers": [],
        "total_market_cap_change": None,
    }
    try:
        from app.cache import cache_get as _cg
        tickers = _cg("tickers", ttl=300)
        if tickers and isinstance(tickers, dict):
            btc = tickers.get("BTCUSDT", {})
            data["btc_price"] = btc.get("price")
            data["btc_change"] = btc.get("change_pct")
            eth = tickers.get("ETHUSDT", {})
            data["eth_price"] = eth.get("price")
            data["eth_change"] = eth.get("change_pct")

            # Gather top gainers / losers
            items = []
            for sym, info in tickers.items():
                if isinstance(info, dict) and info.get("change_pct") is not None:
                    items.append({
                        "symbol": sym,
                        "price": info.get("price"),
                        "change_pct": info.get("change_pct"),
                    })
            items.sort(key=lambda x: float(x.get("change_pct") or 0), reverse=True)
            data["top_gainers"] = items[:5]
            data["top_losers"] = items[-5:][::-1] if len(items) >= 5 else []
    except Exception as e:
        _logger.debug("Market data collection error: %s", e)

    # Fear & Greed
    try:
        fng = cache_get("fng_latest", ttl=600)
        if fng and isinstance(fng, dict):
            data["fng_value"] = fng.get("value")
            data["fng_label"] = fng.get("classification") or fng.get("label")
    except Exception as e:
        _logger.debug("FNG collection error: %s", e)

    return data


def _collect_opportunities(limit: int = 10) -> List[Dict]:
    """Collect top opportunities."""
    try:
        from app.core.opportunity_engine import get_cached_opportunities
        opps = get_cached_opportunities()
        if opps:
            return opps[:limit]
    except Exception as e:
        _logger.debug("Opportunity collection error: %s", e)
    return []


def _collect_news_impacts(limit: int = 5) -> List[Dict]:
    """Collect recent high-impact news."""
    try:
        from app.core.news_impact_engine import get_trending_impacts
        return get_trending_impacts(limit=limit)
    except Exception as e:
        _logger.debug("News impact collection error: %s", e)
    return []


def _collect_activity(hours: int = 6, limit: int = 10) -> List[Dict]:
    """Collect recent activity stream events."""
    try:
        from app.core.activity_stream_engine import get_events
        return get_events(hours=hours, limit=limit, min_confidence=40)
    except Exception as e:
        _logger.debug("Activity collection error: %s", e)
    return []


def _collect_trending_symbols(hours: int = 12, limit: int = 10) -> List[Dict]:
    """Collect trending symbols from activity."""
    try:
        from app.core.activity_stream_engine import get_trending_symbols
        return get_trending_symbols(hours=hours, limit=limit)
    except Exception as e:
        _logger.debug("Trending symbols collection error: %s", e)
    return []


def _collect_portfolio(user_id: str) -> Dict:
    """Collect portfolio data for a user."""
    result = {"has_portfolio": False, "summary": {}, "risk": {}, "assets": []}
    try:
        from app.core.portfolio_engine import portfolio_summary, get_assets
        summary = portfolio_summary(user_id)
        assets = get_assets(user_id)
        if assets:
            result["has_portfolio"] = True
            result["summary"] = summary
            result["assets"] = assets
    except Exception as e:
        _logger.debug("Portfolio collection error: %s", e)

    try:
        from app.core.portfolio_risk_engine import calculate_risk_score
        risk = calculate_risk_score(user_id)
        result["risk"] = risk
    except Exception as e:
        _logger.debug("Portfolio risk collection error: %s", e)

    return result


def _collect_watchlist(user_id: str) -> List[Dict]:
    """Collect user watchlist symbols."""
    try:
        from app.core.user_engine import load_user_data
        wl = load_user_data(user_id, "watchlist")
        if wl and isinstance(wl, list):
            return wl
    except Exception as e:
        _logger.debug("Watchlist collection error: %s", e)
    return []


# ══════════════════════════════════════════════════════════════════
# INTELLIGENCE GENERATORS — build AI summaries
# ══════════════════════════════════════════════════════════════════

def _determine_market_sentiment(market_data: Dict, opps: List) -> Dict:
    """Determine overall market sentiment from available data."""
    score = 50  # neutral baseline

    # BTC change influence
    btc_change = market_data.get("btc_change")
    if btc_change is not None:
        try:
            btc_pct = float(btc_change)
            score += min(max(btc_pct * 5, -20), 20)
        except (ValueError, TypeError):
            pass

    # Fear & Greed influence
    fng = market_data.get("fng_value")
    if fng is not None:
        try:
            fng_val = int(fng)
            score += (fng_val - 50) * 0.3
        except (ValueError, TypeError):
            pass

    # Opportunity types influence
    bullish_count = sum(1 for o in opps
                        if o.get("event_type") in ("momentum_shift", "breakout", "ema_cross"))
    bearish_count = sum(1 for o in opps
                        if o.get("event_type") in ("rsi_extreme", "volatility_spike"))
    score += (bullish_count - bearish_count) * 3

    score = max(0, min(100, score))

    if score >= 70:
        key = "very_bullish"
    elif score >= 55:
        key = "bullish"
    elif score >= 45:
        key = "neutral"
    elif score >= 30:
        key = "bearish"
    else:
        key = "very_bearish"

    return {
        "score": round(score),
        "key": key,
        **_SENTIMENT_MAP[key],
    }


def _build_market_highlights(market_data: Dict, opps: List,
                              news: List, trending: List) -> List[str]:
    """Build list of market highlight sentences."""
    highlights = []

    # BTC status
    btc_price = market_data.get("btc_price")
    btc_change = market_data.get("btc_change")
    if btc_price is not None and btc_change is not None:
        try:
            change = float(btc_change)
            direction = "yukarı" if change >= 0 else "aşağı"
            highlights.append(
                f"BTC ${btc_price:,.0f} seviyesinde, "
                f"24 saatte %{abs(change):.1f} {direction} yönlü hareket gözlemleniyor."
            )
        except (ValueError, TypeError):
            pass

    # ETH status
    eth_price = market_data.get("eth_price")
    eth_change = market_data.get("eth_change")
    if eth_price is not None and eth_change is not None:
        try:
            change = float(eth_change)
            direction = "yukarı" if change >= 0 else "aşağı"
            highlights.append(
                f"ETH ${eth_price:,.0f} seviyesinde, "
                f"%{abs(change):.1f} {direction} yönlü hareket."
            )
        except (ValueError, TypeError):
            pass

    # Fear & Greed
    fng_val = market_data.get("fng_value")
    fng_label = market_data.get("fng_label")
    if fng_val is not None:
        highlights.append(
            f"Korku & Açgözlülük Endeksi: {fng_val} ({fng_label or 'N/A'})."
        )

    # Top opportunities summary
    if opps:
        opp_types = {}
        for o in opps:
            et = o.get("event_type", "unknown")
            opp_types[et] = opp_types.get(et, 0) + 1
        top_type = max(opp_types, key=opp_types.get)
        highlights.append(
            f"{len(opps)} aktif fırsat tespit edildi, "
            f"en yaygın sinyal: {top_type.replace('_', ' ')}."
        )

    # Trending symbols
    if trending:
        syms = [t.get("symbol", "") for t in trending[:3] if t.get("symbol")]
        if syms:
            highlights.append(
                f"Trend semboller: {', '.join(syms)}."
            )

    # News impacts
    if news:
        high_impact = [n for n in news if (n.get("confidence_score") or 0) >= 70]
        if high_impact:
            highlights.append(
                f"{len(high_impact)} yüksek etkili haber dikkat çekiyor."
            )

    return highlights


def _build_portfolio_insights(portfolio: Dict) -> List[Dict]:
    """Build portfolio AI insights."""
    insights = []
    if not portfolio.get("has_portfolio"):
        return insights

    summary = portfolio.get("summary", {})
    risk = portfolio.get("risk", {})
    assets = portfolio.get("assets", [])

    # Total value & PnL
    total_value = summary.get("total_value") or summary.get("total_current_value", 0)
    total_pnl = summary.get("total_pnl", 0)
    total_pnl_pct = summary.get("total_pnl_pct", 0)
    if total_value:
        direction = "pozitif" if total_pnl >= 0 else "negatif"
        insights.append({
            "type": "pnl_summary",
            "icon": "💰",
            "title": "Portföy Değeri",
            "text": _sanitize(
                f"Toplam değer: ${total_value:,.2f}. "
                f"PnL: ${total_pnl:,.2f} (%{total_pnl_pct:.1f}), "
                f"{direction} seyir gözlemleniyor."
            ),
            "severity": "info",
        })

    # Risk analysis
    risk_score = risk.get("risk_score", 0)
    risk_label = risk.get("risk_label_tr") or risk.get("risk_label", "N/A")
    if risk_score > 0:
        severity = "warning" if risk_score > 60 else "info"
        risk_text = f"Risk skoru: {risk_score}/100 ({risk_label})."
        concentration = risk.get("concentration_risk", 0)
        if concentration > 50:
            risk_text += f" Yoğunlaşma riski dikkat çekiyor (%{concentration:.0f})."
        insights.append({
            "type": "risk",
            "icon": "🛡️",
            "title": "Risk Analizi",
            "text": _sanitize(risk_text),
            "severity": severity,
        })

    # Top/bottom performers
    if assets and len(assets) >= 2:
        priced = [a for a in assets
                  if a.get("current_price") and a.get("entry_price")]
        if priced:
            for a in priced:
                cp = float(a.get("current_price", 0))
                ep = float(a.get("entry_price", 1))
                a["_pnl_pct"] = ((cp - ep) / ep * 100) if ep else 0

            priced.sort(key=lambda x: x["_pnl_pct"], reverse=True)
            best = priced[0]
            worst = priced[-1]
            insights.append({
                "type": "performers",
                "icon": "📊",
                "title": "Performans Gözlemi",
                "text": _sanitize(
                    f"En iyi performans: {best.get('symbol')} "
                    f"(%{best['_pnl_pct']:.1f}). "
                    f"En düşük performans: {worst.get('symbol')} "
                    f"(%{worst['_pnl_pct']:.1f})."
                ),
                "severity": "info",
            })

    return insights


def _build_watchlist_insights(watchlist: List[Dict],
                               market_data: Dict, opps: List) -> List[Dict]:
    """Build watchlist AI insights."""
    insights = []
    if not watchlist:
        return insights

    wl_symbols = {item.get("symbol", "").upper() for item in watchlist}

    # Check opportunities for watchlist symbols
    wl_opps = [o for o in opps if o.get("symbol", "").upper() in wl_symbols]
    if wl_opps:
        for opp in wl_opps[:3]:
            insights.append({
                "type": "watchlist_opportunity",
                "icon": "🎯",
                "symbol": opp.get("symbol", ""),
                "title": f"{opp.get('symbol', '')} — Fırsat Tespit",
                "text": _sanitize(
                    opp.get("description", "") or
                    f"{opp.get('event_type', 'signal').replace('_', ' ')} "
                    f"gözlemleniyor"
                ),
                "confidence": opp.get("confidence", 50),
                "event_type": opp.get("event_type", ""),
            })

    # Price movements for watchlist symbols from tickers
    tickers = cache_get("tickers", ttl=300)
    if tickers and isinstance(tickers, dict):
        movers = []
        for sym in wl_symbols:
            t = tickers.get(sym, {})
            if isinstance(t, dict) and t.get("change_pct") is not None:
                try:
                    movers.append({
                        "symbol": sym,
                        "price": t.get("price"),
                        "change_pct": float(t["change_pct"]),
                    })
                except (ValueError, TypeError):
                    pass

        if movers:
            movers.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
            for m in movers[:3]:
                direction = "yukarı" if m["change_pct"] >= 0 else "aşağı"
                insights.append({
                    "type": "watchlist_price",
                    "icon": "📈" if m["change_pct"] >= 0 else "📉",
                    "symbol": m["symbol"],
                    "title": f"{m['symbol']} Fiyat Hareketi",
                    "text": _sanitize(
                        f"{m['symbol']} ${m['price']:,.2f} — "
                        f"%{abs(m['change_pct']):.1f} {direction} yönlü hareket."
                    ) if m["price"] else _sanitize(
                        f"{m['symbol']}: %{abs(m['change_pct']):.1f} "
                        f"{direction} yönlü hareket gözlemleniyor."
                    ),
                    "change_pct": m["change_pct"],
                })

    if not insights:
        insights.append({
            "type": "watchlist_quiet",
            "icon": "✅",
            "title": "İzleme Listesi Sakin",
            "text": "İzleme listenizdeki semboller için dikkat çekici bir hareket yok.",
        })

    return insights


def _explain_single_opportunity(opp: Dict) -> Dict:
    """Generate AI explanation for a single opportunity."""
    sym = opp.get("symbol", "Unknown")
    event_type = opp.get("event_type", "signal")
    confidence = opp.get("confidence", 50)
    description = opp.get("description", "")
    details = opp.get("details", "")
    price = opp.get("price")
    change_pct = opp.get("change_pct")

    # Build explanation
    lines = []

    # Event type description
    type_descriptions = {
        "volume_spike": f"{sym} sembolünde normalin üzerinde hacim artışı gözlemleniyor. "
                        "Bu durum artan piyasa ilgisine işaret edebilir.",
        "momentum_shift": f"{sym} sembolünde momentum değişimi tespit edildi. "
                          "Trend yönünde önemli bir kayma dikkat çekiyor.",
        "volatility_spike": f"{sym} sembolünde yüksek volatilite gözlemleniyor. "
                            "Fiyat hareketleri genişliyor.",
        "rsi_extreme": f"{sym} sembolünde RSI aşırı bölgede. "
                       "Dikkatli izlenebilir.",
        "ema_cross": f"{sym} sembolünde EMA kesişimi gözlemleniyor. "
                     "Teknik açıdan dikkat çekici bir sinyal.",
        "breakout": f"{sym} sembolünde kırılım hareketi gözlemleniyor. "
                    "Fiyat önemli bir direnç/destek seviyesini test ediyor.",
        "sector_rotation": "Sektör rotasyonu gözlemleniyor. "
                           "Sermaye akışı sektörler arasında kayıyor.",
        "whale_activity": f"{sym} sembolünde büyük hacimli işlemler dikkat çekiyor.",
        "fng_extreme": "Korku & Açgözlülük endeksinde aşırı değer gözlemleniyor.",
        "price_anomaly": f"{sym} sembolünde olağandışı fiyat hareketi tespit edildi.",
    }

    lines.append(type_descriptions.get(
        event_type,
        f"{sym} sembolünde {event_type.replace('_', ' ')} sinyali gözlemleniyor."
    ))

    if price is not None:
        lines.append(f"Mevcut fiyat: ${price:,.2f}.")

    if change_pct is not None:
        try:
            pct = float(change_pct)
            direction = "pozitif" if pct >= 0 else "negatif"
            lines.append(f"24 saatlik değişim: %{abs(pct):.1f} ({direction}).")
        except (ValueError, TypeError):
            pass

    if confidence >= 80:
        lines.append("Sinyal güvenilirliği yüksek.")
    elif confidence >= 60:
        lines.append("Sinyal güvenilirliği orta seviyede.")
    else:
        lines.append("Sinyal güvenilirliği düşük — dikkatli izlenebilir.")

    if details:
        lines.append(_sanitize(str(details)[:200]))

    return {
        "symbol": sym,
        "event_type": event_type,
        "confidence": confidence,
        "explanation": _sanitize(" ".join(lines)),
        "highlights": [_sanitize(l) for l in lines[:3]],
        "risk_level": "high" if confidence < 50 else ("medium" if confidence < 75 else "low"),
        "generated_at": _now_iso(),
    }


# ══════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════

def generate_brief(user_id: str) -> Dict:
    """Generate personalised AI market brief for a user.

    Returns a comprehensive brief with market summary, portfolio
    insights, watchlist alerts, and top opportunities.
    Cached for 15 minutes per user.
    """
    cache_key = f"ai_brief:{user_id}"
    cached = cache_get(cache_key, ttl=BRIEF_CACHE_TTL)
    if cached:
        return cached

    t0 = time.time()

    # Collect all data
    market_data = _collect_market_data()
    opps = _collect_opportunities(limit=15)
    news = _collect_news_impacts(limit=5)
    activity = _collect_activity(hours=6, limit=10)
    trending = _collect_trending_symbols(hours=12, limit=5)
    portfolio = _collect_portfolio(user_id)
    watchlist = _collect_watchlist(user_id)

    # Build intelligence
    sentiment = _determine_market_sentiment(market_data, opps)
    highlights = _build_market_highlights(market_data, opps, news, trending)
    portfolio_insights = _build_portfolio_insights(portfolio)
    watchlist_insights = _build_watchlist_insights(watchlist, market_data, opps)
    top_opps = [_explain_single_opportunity(o) for o in opps[:5]]

    brief = {
        "user_id": user_id,
        "generated_at": _now_iso(),
        "generation_time_ms": 0,
        "sentiment": sentiment,
        "highlights": highlights,
        "portfolio": {
            "has_data": portfolio.get("has_portfolio", False),
            "insights": portfolio_insights,
        },
        "watchlist": {
            "count": len(watchlist),
            "insights": watchlist_insights,
        },
        "opportunities": {
            "total": len(opps),
            "top": top_opps,
        },
        "news_impacts": [{
            "title": n.get("news_title", ""),
            "confidence": n.get("confidence_score", 0),
            "summary": _sanitize(n.get("impact_summary", "")[:200]),
            "time_horizon": n.get("time_horizon", "short_term"),
        } for n in news[:3]],
        "trending_symbols": trending[:5],
        "recent_activity_count": len(activity),
    }

    elapsed = (time.time() - t0) * 1000
    brief["generation_time_ms"] = round(elapsed)

    cache_set(cache_key, brief)
    _logger.info("AI brief generated for user %s in %.0fms", user_id, elapsed)
    return brief


def analyze_portfolio(user_id: str) -> Dict:
    """Deep AI analysis of user's portfolio.

    Returns risk assessment, allocation insights, performance
    observations, and actionable intelligence. Cached 15 minutes.
    """
    cache_key = f"ai_portfolio:{user_id}"
    cached = cache_get(cache_key, ttl=PORTFOLIO_CACHE_TTL)
    if cached:
        return cached

    portfolio = _collect_portfolio(user_id)
    opps = _collect_opportunities(limit=20)
    market_data = _collect_market_data()

    if not portfolio.get("has_portfolio"):
        result = {
            "has_data": False,
            "message": "Portföyünüzde varlık bulunmuyor. "
                       "Varlık ekleyerek AI analizinden faydalanabilirsiniz.",
            "insights": [],
            "generated_at": _now_iso(),
        }
        cache_set(cache_key, result)
        return result

    insights = _build_portfolio_insights(portfolio)

    # Cross-reference portfolio assets with opportunities
    assets = portfolio.get("assets", [])
    asset_symbols = {a.get("symbol", "").upper() for a in assets}
    related_opps = [o for o in opps if o.get("symbol", "").upper() in asset_symbols]

    for opp in related_opps[:3]:
        insights.append({
            "type": "portfolio_opportunity",
            "icon": "🎯",
            "title": f"{opp.get('symbol', '')} — Portföy Sinyali",
            "text": _sanitize(
                f"Portföyünüzdeki {opp.get('symbol', '')} için "
                f"{opp.get('event_type', 'sinyal').replace('_', ' ')} "
                f"gözlemleniyor."
            ),
            "confidence": opp.get("confidence", 50),
            "severity": "info",
        })

    # Market-relative performance
    btc_change = market_data.get("btc_change")
    pnl_pct = portfolio.get("summary", {}).get("total_pnl_pct", 0)
    if btc_change is not None:
        try:
            btc_pct = float(btc_change)
            diff = pnl_pct - btc_pct
            if abs(diff) > 1:
                direction = "üzerinde" if diff > 0 else "altında"
                insights.append({
                    "type": "market_relative",
                    "icon": "📊",
                    "title": "Piyasa Karşılaştırması",
                    "text": _sanitize(
                        f"Portföyünüz BTC performansının {direction} seyrediyor "
                        f"(fark: %{abs(diff):.1f})."
                    ),
                    "severity": "info",
                })
        except (ValueError, TypeError):
            pass

    result = {
        "has_data": True,
        "summary": portfolio.get("summary", {}),
        "risk": portfolio.get("risk", {}),
        "insights": insights,
        "related_opportunities": len(related_opps),
        "generated_at": _now_iso(),
    }
    cache_set(cache_key, result)
    return result


def analyze_watchlist(user_id: str) -> Dict:
    """AI analysis of user's watchlist.

    Returns price movements, opportunity alerts, and intelligence
    for watched symbols. Cached 15 minutes.
    """
    cache_key = f"ai_watchlist:{user_id}"
    cached = cache_get(cache_key, ttl=WATCHLIST_CACHE_TTL)
    if cached:
        return cached

    watchlist = _collect_watchlist(user_id)
    market_data = _collect_market_data()
    opps = _collect_opportunities(limit=20)

    if not watchlist:
        result = {
            "has_data": False,
            "count": 0,
            "message": "İzleme listeniz boş. "
                       "Sembol ekleyerek AI takibinden faydalanabilirsiniz.",
            "insights": [],
            "generated_at": _now_iso(),
        }
        cache_set(cache_key, result)
        return result

    insights = _build_watchlist_insights(watchlist, market_data, opps)

    result = {
        "has_data": True,
        "count": len(watchlist),
        "symbols": [w.get("symbol", "") for w in watchlist],
        "insights": insights,
        "generated_at": _now_iso(),
    }
    cache_set(cache_key, result)
    return result


def explain_opportunity(opp_id: str) -> Dict:
    """Generate AI explanation for a specific opportunity.

    Returns detailed explanation with risk assessment.
    Cached 15 minutes per opportunity.
    """
    cache_key = f"ai_opp_explain:{opp_id}"
    cached = cache_get(cache_key, ttl=OPP_EXPLAIN_CACHE_TTL)
    if cached:
        return cached

    try:
        from app.core.opportunity_engine import get_opportunity_by_id
        opp = get_opportunity_by_id(opp_id)
    except (ImportError, AttributeError):
        # Fallback: search by ID in cached list
        opp = None
        try:
            from app.core.opportunity_engine import get_cached_opportunities
            all_opps = get_cached_opportunities() or []
            for o in all_opps:
                if o.get("id") == opp_id:
                    opp = o
                    break
        except Exception:
            pass

    if not opp:
        return {
            "found": False,
            "error": "Fırsat bulunamadı.",
            "generated_at": _now_iso(),
        }

    result = _explain_single_opportunity(opp)
    result["found"] = True
    cache_set(cache_key, result)
    return result


def get_market_summary() -> Dict:
    """Generate general market summary (not user-specific).

    Cached for 15 minutes.
    """
    cache_key = "ai_market_summary"
    cached = cache_get(cache_key, ttl=MARKET_CACHE_TTL)
    if cached:
        return cached

    t0 = time.time()

    market_data = _collect_market_data()
    opps = _collect_opportunities(limit=15)
    news = _collect_news_impacts(limit=5)
    trending = _collect_trending_symbols(hours=12, limit=10)

    sentiment = _determine_market_sentiment(market_data, opps)
    highlights = _build_market_highlights(market_data, opps, news, trending)

    result = {
        "sentiment": sentiment,
        "highlights": highlights,
        "market_data": {
            "btc_price": market_data.get("btc_price"),
            "btc_change": market_data.get("btc_change"),
            "eth_price": market_data.get("eth_price"),
            "eth_change": market_data.get("eth_change"),
            "fng_value": market_data.get("fng_value"),
            "fng_label": market_data.get("fng_label"),
            "top_gainers": market_data.get("top_gainers", [])[:5],
            "top_losers": market_data.get("top_losers", [])[:5],
        },
        "opportunities_count": len(opps),
        "news_impacts_count": len(news),
        "trending_symbols": trending[:5],
        "generated_at": _now_iso(),
        "generation_time_ms": round((time.time() - t0) * 1000),
    }

    cache_set(cache_key, result)
    return result


def get_top_opportunities(limit: int = 10) -> List[Dict]:
    """Get top opportunities with AI explanations.

    Returns explained opportunities sorted by confidence.
    """
    cache_key = f"ai_top_opps:{limit}"
    cached = cache_get(cache_key, ttl=MARKET_CACHE_TTL)
    if cached:
        return cached

    opps = _collect_opportunities(limit=limit)
    explained = [_explain_single_opportunity(o) for o in opps]
    explained.sort(key=lambda x: x.get("confidence", 0), reverse=True)

    cache_set(cache_key, explained)
    return explained


def ask_agent(user_id: str, question: str) -> Dict:
    """Answer a free-form question using aggregated market context.

    Builds context from all available data sources and returns
    a structured answer. No caching — each question is fresh.
    """
    if not question or not question.strip():
        return {
            "ok": False,
            "error": "Soru boş olamaz.",
            "generated_at": _now_iso(),
        }

    question = question.strip()[:500]  # limit length

    # Build comprehensive context
    market_data = _collect_market_data()
    opps = _collect_opportunities(limit=10)
    news = _collect_news_impacts(limit=5)
    trending = _collect_trending_symbols(hours=12, limit=5)
    portfolio = _collect_portfolio(user_id)
    watchlist = _collect_watchlist(user_id)

    sentiment = _determine_market_sentiment(market_data, opps)
    highlights = _build_market_highlights(market_data, opps, news, trending)

    # Build context dict for copilot
    context = {
        "question": question,
        "market_sentiment": sentiment,
        "highlights": highlights,
        "btc_price": market_data.get("btc_price"),
        "btc_change": market_data.get("btc_change"),
        "fng_value": market_data.get("fng_value"),
        "fng_label": market_data.get("fng_label"),
        "active_opportunities": len(opps),
        "trending_symbols": [t.get("symbol") for t in trending],
        "has_portfolio": portfolio.get("has_portfolio", False),
        "watchlist_count": len(watchlist),
    }

    # Try to use copilot service for AI answer
    try:
        from app.core.copilot_service import ask_market
        result = ask_market("crypto", question)
        result["context"] = context
        result["generated_at"] = _now_iso()
        return {"ok": True, "data": result}
    except Exception as e:
        _logger.debug("Copilot service unavailable: %s", e)

    # Fallback: structured answer from context
    answer_lines = [f"Piyasa durumu: {sentiment.get('label', 'N/A')} "
                    f"(skor: {sentiment.get('score', 50)}/100)."]
    answer_lines.extend(highlights[:3])

    if portfolio.get("has_portfolio"):
        answer_lines.append("Portföy bilginiz mevcut — "
                            "detaylı analiz için AI Portföy sekmesini kullanabilirsiniz.")

    return {
        "ok": True,
        "data": {
            "answer": _sanitize("\n".join(answer_lines)),
            "summary": _sanitize(highlights[0] if highlights else "Veri yükleniyor..."),
            "key_points": [_sanitize(h) for h in highlights],
            "context": context,
            "generated_at": _now_iso(),
        },
    }
