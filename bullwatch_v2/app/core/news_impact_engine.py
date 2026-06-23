# -*- coding: utf-8 -*-
"""News Impact Engine — FAZ 37 (AI Market Radar).

Analyzes news articles to determine sector and asset impact.
Produces bullish/bearish sector & asset lists, confidence scores,
impact summaries, and time horizon predictions.

Public API:
  analyze(news_dict)              → dict (impact result)
  get_impact(news_id)             → dict | None
  get_trending_impacts(limit,..)  → list[dict]
  get_radar(market, limit)        → dict
  get_top_sectors(hours, limit)   → dict
  get_most_impacted_assets(h,l)   → dict
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

_logger = logging.getLogger("zkr_analiz.news_impact")

_DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "data")
_DB_PATH = os.path.join(_DB_DIR, "news_impact.db")

_lock = threading.Lock()


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id() -> str:
    return str(uuid.uuid4())[:12]


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


# ══════════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════════

def _get_conn() -> sqlite3.Connection:
    from app.core.db_manager import get_connection
    return get_connection("news_impact.db")


def _ensure_tables(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS news_impacts (
            id            TEXT PRIMARY KEY,
            news_id       TEXT NOT NULL,
            news_title    TEXT DEFAULT '',
            news_source   TEXT DEFAULT '',
            news_market   TEXT DEFAULT '',
            news_category TEXT DEFAULT '',
            bullish_sectors TEXT DEFAULT '[]',
            bearish_sectors TEXT DEFAULT '[]',
            bullish_assets  TEXT DEFAULT '[]',
            bearish_assets  TEXT DEFAULT '[]',
            confidence_score INTEGER DEFAULT 50,
            impact_summary  TEXT DEFAULT '',
            time_horizon    TEXT DEFAULT 'short_term',
            created_at    TEXT NOT NULL,
            updated_at    TEXT NOT NULL,
            UNIQUE(news_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ni_news_id
        ON news_impacts(news_id)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ni_market
        ON news_impacts(news_market)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ni_created
        ON news_impacts(created_at DESC)
    """)
    conn.commit()


def _init_db():
    conn = _get_conn()
    try:
        _ensure_tables(conn)
    finally:
        conn.close()


_init_db()


# ══════════════════════════════════════════════════════════════════
# SECTOR / ASSET MAPPING
# ══════════════════════════════════════════════════════════════════

# Keyword patterns → sectors they relate to
_SECTOR_KEYWORDS: Dict[str, List[str]] = {
    # -- Crypto --
    "bitcoin|btc": ["crypto"],
    "ethereum|eth|defi|smart contract": ["crypto", "defi"],
    "altcoin|token|blockchain|web3|nft": ["crypto"],
    "exchange|binance|coinbase|kraken": ["crypto", "exchanges"],
    "stablecoin|usdt|usdc|tether": ["crypto", "stablecoins"],
    "mining|miner|hashrate": ["crypto", "mining"],
    # -- Traditional --
    "bank|banking|credit|loan|mortgage": ["banking", "financials"],
    "interest rate|fed|federal reserve|central bank|monetary policy": ["banking", "bonds", "macro"],
    "inflation|cpi|ppi|consumer price": ["macro", "bonds"],
    "tech|technology|software|cloud|ai|artificial intelligence|semiconductor": ["technology"],
    "energy|oil|gas|petroleum|opec|crude": ["energy", "commodities"],
    "gold|silver|platinum|precious metal": ["commodities", "precious_metals"],
    "defense|military|weapon|arms": ["defense"],
    "aviation|airline|aircraft|boeing": ["aviation"],
    "auto|automotive|car|electric vehicle|ev|tesla": ["automotive", "technology"],
    "pharma|pharmaceutical|biotech|drug|vaccine|health": ["healthcare"],
    "real estate|housing|property|reit": ["real_estate"],
    "retail|consumer|e-commerce|amazon|shopping": ["consumer", "retail"],
    # -- Turkish / BIST --
    "bist|borsa istanbul|kap|spk": ["bist"],
    "türk|turk|tcmb|merkez bankası": ["bist", "turkish_macro"],
    "bist_bank|garanti|akbank|yapı kredi|iş bankası|halkbank|vakıfbank": ["bist_banks"],
    "thy|thyao|türk hava": ["bist_aviation"],
    "aselsan|asels|savunma": ["bist_defense"],
    "koç|sabancı|holding": ["bist_industrials"],
    # -- Forex --
    "dollar|usd|dxy|eur|gbp|jpy|forex|currency|fx": ["forex"],
    "usdtry|lira|türk lirası": ["forex", "turkish_macro"],
    # -- ETF/SEC --
    "etf|sec|securities|regulation|compliance": ["regulation"],
    "bitcoin etf|crypto etf|spot etf": ["crypto", "regulation", "etf"],
}

# Keyword patterns → specific assets affected
_ASSET_KEYWORDS: Dict[str, Dict[str, str]] = {
    # pattern : {asset: direction}  direction = "bullish" or "bearish" or "both"
    # Crypto
    "bitcoin|btc": {"BTC": "both"},
    "ethereum|eth|defi": {"ETH": "both"},
    "solana|sol": {"SOL": "both"},
    "ripple|xrp": {"XRP": "both"},
    "dogecoin|doge": {"DOGE": "both"},
    "bnb|binance coin": {"BNB": "both"},
    "cardano|ada": {"ADA": "both"},
    "avalanche|avax": {"AVAX": "both"},
    "coinbase|coin": {"COIN": "both"},
    "microstrategy|mstr": {"MSTR": "both"},
    # Stocks
    "apple|aapl": {"AAPL": "both"},
    "nvidia|nvda": {"NVDA": "both"},
    "microsoft|msft": {"MSFT": "both"},
    "tesla|tsla": {"TSLA": "both"},
    "amazon|amzn": {"AMZN": "both"},
    "google|alphabet|googl": {"GOOGL": "both"},
    "meta|facebook": {"META": "both"},
    "amd": {"AMD": "both"},
    "netflix|nflx": {"NFLX": "both"},
    "jpmorgan|jpm": {"JPM": "both"},
    "goldman sachs|gs": {"GS": "both"},
    "bank of america|bac": {"BAC": "both"},
    # BIST
    "thyao|thy|türk hava": {"THYAO.IS": "both"},
    "asels|aselsan": {"ASELS.IS": "both"},
    "garan|garanti": {"GARAN.IS": "both"},
    "tuprs|tüpraş": {"TUPRS.IS": "both"},
    "sise|şişecam": {"SISE.IS": "both"},
    "kchol|koç holding": {"KCHOL.IS": "both"},
    "akbnk|akbank": {"AKBNK.IS": "both"},
    "eregl|ereğli": {"EREGL.IS": "both"},
    "bimas|bim": {"BIMAS.IS": "both"},
    # Macro / Commodities / Forex
    "gold|altın": {"GC=F": "both"},
    "crude oil|petrol|wti": {"CL=F": "both"},
    "silver|gümüş": {"SI=F": "both"},
    "dolar|dollar|dxy": {"DXY": "both"},
    "usdtry|lira": {"USDTRY=X": "both"},
    "eurusd|euro dolar": {"EURUSD=X": "both"},
    "nasdaq|qqq": {"QQQ": "both"},
    "s&p 500|s&p500|spy": {"SPY": "both"},
}

# Cross-market impact rules: certain news themes systematically
# affect assets in predictable directions
_CROSS_IMPACT_RULES: List[Dict] = [
    {
        "trigger": r"interest rate.*(hike|raise|increase)|fed.*raise|rate hike|faiz.*art",
        "bullish_sectors": ["banking", "bonds"],
        "bearish_sectors": ["technology", "crypto", "real_estate"],
        "bullish_assets": ["DXY", "JPM", "BAC"],
        "bearish_assets": ["BTC", "ETH", "QQQ", "NVDA"],
        "horizon": "short_term",
    },
    {
        "trigger": r"interest rate.*(cut|lower|decrease)|fed.*cut|rate cut|faiz.*indir",
        "bullish_sectors": ["technology", "crypto", "real_estate"],
        "bearish_sectors": ["banking"],
        "bullish_assets": ["BTC", "ETH", "QQQ", "NVDA", "AAPL"],
        "bearish_assets": ["DXY"],
        "horizon": "mid_term",
    },
    {
        "trigger": r"bitcoin etf.*approv|sec.*approv.*bitcoin|btc etf.*onay",
        "bullish_sectors": ["crypto", "exchanges", "digital_assets"],
        "bearish_sectors": ["precious_metals"],
        "bullish_assets": ["BTC", "ETH", "COIN", "MSTR"],
        "bearish_assets": ["GC=F"],
        "horizon": "mid_term",
    },
    {
        "trigger": r"crypto.*ban|bitcoin.*ban|china.*crypto|yasakla.*kripto",
        "bullish_sectors": [],
        "bearish_sectors": ["crypto", "exchanges"],
        "bullish_assets": ["DXY", "GC=F"],
        "bearish_assets": ["BTC", "ETH", "BNB", "COIN"],
        "horizon": "short_term",
    },
    {
        "trigger": r"inflation.*(rise|high|surge|increase)|enflasyon.*(art|yüksel)",
        "bullish_sectors": ["commodities", "energy", "precious_metals"],
        "bearish_sectors": ["technology", "consumer", "bonds"],
        "bullish_assets": ["GC=F", "CL=F"],
        "bearish_assets": ["QQQ", "SPY"],
        "horizon": "mid_term",
    },
    {
        "trigger": r"recession|resesyon|economic.*slowdown|daralma",
        "bullish_sectors": ["bonds", "precious_metals", "healthcare"],
        "bearish_sectors": ["technology", "consumer", "energy", "banking"],
        "bullish_assets": ["GC=F"],
        "bearish_assets": ["SPY", "QQQ", "CL=F"],
        "horizon": "long_term",
    },
    {
        "trigger": r"war|geopolit|tension|savaş|gerginlik|çatışma",
        "bullish_sectors": ["defense", "energy", "precious_metals"],
        "bearish_sectors": ["aviation", "consumer", "tourism"],
        "bullish_assets": ["GC=F", "CL=F"],
        "bearish_assets": ["SPY"],
        "horizon": "short_term",
    },
    {
        "trigger": r"tcmb.*faiz|merkez.*faiz|türk.*lira.*(düş|devalue)",
        "bullish_sectors": ["bist_exporters"],
        "bearish_sectors": ["bist_banks", "turkish_macro"],
        "bullish_assets": [],
        "bearish_assets": ["USDTRY=X", "GARAN.IS"],
        "horizon": "short_term",
    },
    {
        "trigger": r"oil.*(surge|spike|rally)|petrol.*(art|yüksel)|opec.*cut",
        "bullish_sectors": ["energy", "commodities"],
        "bearish_sectors": ["aviation", "automotive", "consumer"],
        "bullish_assets": ["CL=F", "TUPRS.IS"],
        "bearish_assets": ["THYAO.IS"],
        "horizon": "short_term",
    },
    {
        "trigger": r"ai|artificial intelligence|yapay zeka|nvidia.*earn|chip.*demand",
        "bullish_sectors": ["technology", "semiconductor"],
        "bearish_sectors": [],
        "bullish_assets": ["NVDA", "AMD", "MSFT", "GOOGL"],
        "bearish_assets": [],
        "horizon": "mid_term",
    },
]

# Confidence boost sources (higher = more trusted)
_SOURCE_CONFIDENCE: Dict[str, int] = {
    "Reuters": 15, "Bloomberg": 15, "CoinDesk": 10,
    "CoinTelegraph": 8, "Bitcoin Magazine": 8,
    "Google News": 5, "CryptoPanic": 7,
    "KAP": 12, "SEC": 14,
}


# ══════════════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ══════════════════════════════════════════════════════════════════

def _match_sectors(text: str) -> Dict[str, List[str]]:
    """Find sectors mentioned in news text."""
    lower = text.lower()
    matched = set()
    for pattern, sectors in _SECTOR_KEYWORDS.items():
        if re.search(pattern, lower):
            matched.update(sectors)
    return sorted(matched)


def _match_assets(text: str, sentiment: str) -> Dict[str, List[str]]:
    """Find assets and classify as bullish/bearish based on news sentiment."""
    lower = text.lower()
    bullish = set()
    bearish = set()

    for pattern, assets in _ASSET_KEYWORDS.items():
        if re.search(pattern, lower):
            for asset_sym, direction in assets.items():
                if direction == "both":
                    if sentiment in ("bullish", "positive"):
                        bullish.add(asset_sym)
                    elif sentiment in ("bearish", "negative"):
                        bearish.add(asset_sym)
                    else:
                        bullish.add(asset_sym)
                elif direction == "bullish":
                    bullish.add(asset_sym)
                else:
                    bearish.add(asset_sym)

    return {"bullish": sorted(bullish), "bearish": sorted(bearish)}


def _apply_cross_impact(text: str) -> Optional[Dict]:
    """Apply cross-market impact rules for macro events."""
    lower = text.lower()
    for rule in _CROSS_IMPACT_RULES:
        if re.search(rule["trigger"], lower, re.IGNORECASE):
            return rule
    return None


def _calculate_confidence(news: dict, matched_sectors: list,
                          matched_assets: dict) -> int:
    """Calculate confidence score 0-100."""
    score = 40  # base

    # Source reliability
    source = news.get("source", "")
    score += _SOURCE_CONFIDENCE.get(source, 3)

    # Text clarity: longer text = more context = higher confidence
    text = (news.get("title", "") + " " + news.get("summary", "")).strip()
    if len(text) > 200:
        score += 10
    elif len(text) > 100:
        score += 5

    # Match breadth
    if len(matched_sectors) >= 3:
        score += 10
    elif len(matched_sectors) >= 1:
        score += 5

    total_assets = len(matched_assets.get("bullish", [])) + len(matched_assets.get("bearish", []))
    if total_assets >= 4:
        score += 10
    elif total_assets >= 2:
        score += 5

    # Cross-impact rule matched = strong signal
    cross = _apply_cross_impact(text)
    if cross:
        score += 15

    return min(100, max(0, score))


def _determine_horizon(text: str) -> str:
    """Determine time horizon of impact."""
    lower = text.lower()
    long_kw = r"long.term|uzun vadeli|year|yıl|structural|yapısal"
    mid_kw = r"mid.term|orta vadeli|month|quarter|çeyrek"
    if re.search(long_kw, lower):
        return "long_term"
    if re.search(mid_kw, lower):
        return "mid_term"
    return "short_term"


def _generate_summary(news: dict, bullish_sectors: list,
                      bearish_sectors: list, bullish_assets: list,
                      bearish_assets: list, horizon: str) -> str:
    """Generate a concise impact summary."""
    title = news.get("title", "Haber")
    parts = []

    if bullish_sectors:
        parts.append(f"Olumlu etkilenen sektörler: {', '.join(bullish_sectors[:3])}")
    if bearish_sectors:
        parts.append(f"Olumsuz etkilenen sektörler: {', '.join(bearish_sectors[:3])}")
    if bullish_assets:
        parts.append(f"Yükselebilecek varlıklar: {', '.join(bullish_assets[:4])}")
    if bearish_assets:
        parts.append(f"Düşebilecek varlıklar: {', '.join(bearish_assets[:4])}")

    horizon_map = {
        "short_term": "Kısa vadeli etki bekleniyor",
        "mid_term": "Orta vadeli etki bekleniyor",
        "long_term": "Uzun vadeli yapısal etki bekleniyor",
    }
    parts.append(horizon_map.get(horizon, ""))

    return ". ".join(p for p in parts if p) + "."


# ══════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════

def analyze(news: dict) -> dict:
    """Analyze a news article and return impact data.

    Args:
        news: dict with keys: id, title, summary, source, sentiment,
              market, category, symbols, etc.

    Returns:
        dict with impact analysis results.
    """
    if not news or not news.get("title"):
        raise ValueError("News article must have a title")

    news_id = news.get("id") or _gen_id()
    text = (news.get("title", "") + " " + news.get("summary", "")).strip()
    sentiment = news.get("sentiment", "neutral")

    # 1) Match sectors
    all_sectors = _match_sectors(text)

    # 2) Match assets based on sentiment
    asset_match = _match_assets(text, sentiment)

    # 3) Check cross-market impact rules
    cross = _apply_cross_impact(text)

    # 4) Merge cross-impact results
    bullish_sectors = list(set(all_sectors)) if sentiment in ("bullish", "positive") else []
    bearish_sectors = list(set(all_sectors)) if sentiment in ("bearish", "negative") else []

    if cross:
        bullish_sectors = sorted(set(bullish_sectors + cross.get("bullish_sectors", [])))
        bearish_sectors = sorted(set(bearish_sectors + cross.get("bearish_sectors", [])))
        # Merge assets from cross-impact
        cross_bull = cross.get("bullish_assets", [])
        cross_bear = cross.get("bearish_assets", [])
        asset_match["bullish"] = sorted(set(asset_match["bullish"] + cross_bull))
        asset_match["bearish"] = sorted(set(asset_match["bearish"] + cross_bear))

    # If neutral sentiment but we have sectors, distribute
    if sentiment == "neutral" and all_sectors:
        bullish_sectors = sorted(set(bullish_sectors + all_sectors[:len(all_sectors)//2 + 1]))
        bearish_sectors = sorted(set(bearish_sectors + all_sectors[len(all_sectors)//2 + 1:]))

    bullish_assets = asset_match["bullish"]
    bearish_assets = asset_match["bearish"]

    # 5) Determine time horizon
    horizon = cross["horizon"] if cross and cross.get("horizon") else _determine_horizon(text)

    # 6) Calculate confidence
    confidence = _calculate_confidence(news, all_sectors, asset_match)

    # 7) Generate summary
    summary = _generate_summary(
        news, bullish_sectors, bearish_sectors,
        bullish_assets, bearish_assets, horizon,
    )

    now = _now_iso()

    impact = {
        "id": _gen_id(),
        "news_id": news_id,
        "news_title": news.get("title", ""),
        "news_source": news.get("source", ""),
        "news_market": news.get("market", ""),
        "news_category": news.get("category", ""),
        "bullish_sectors": bullish_sectors,
        "bearish_sectors": bearish_sectors,
        "bullish_assets": bullish_assets,
        "bearish_assets": bearish_assets,
        "confidence_score": confidence,
        "impact_summary": summary,
        "time_horizon": horizon,
        "created_at": now,
        "updated_at": now,
    }

    # 8) Store in DB
    _save_impact(impact)

    return impact


def _save_impact(impact: dict):
    """Store impact in database (upsert on news_id)."""
    with _lock:
        conn = _get_conn()
        try:
            conn.execute("""
                INSERT INTO news_impacts
                    (id, news_id, news_title, news_source, news_market,
                     news_category, bullish_sectors, bearish_sectors,
                     bullish_assets, bearish_assets, confidence_score,
                     impact_summary, time_horizon, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(news_id) DO UPDATE SET
                    bullish_sectors = excluded.bullish_sectors,
                    bearish_sectors = excluded.bearish_sectors,
                    bullish_assets  = excluded.bullish_assets,
                    bearish_assets  = excluded.bearish_assets,
                    confidence_score= excluded.confidence_score,
                    impact_summary  = excluded.impact_summary,
                    time_horizon    = excluded.time_horizon,
                    updated_at      = excluded.updated_at
            """, (
                impact["id"],
                impact["news_id"],
                impact["news_title"],
                impact["news_source"],
                impact["news_market"],
                impact["news_category"],
                json.dumps(impact["bullish_sectors"]),
                json.dumps(impact["bearish_sectors"]),
                json.dumps(impact["bullish_assets"]),
                json.dumps(impact["bearish_assets"]),
                impact["confidence_score"],
                impact["impact_summary"],
                impact["time_horizon"],
                impact["created_at"],
                impact["updated_at"],
            ))
            conn.commit()
        finally:
            conn.close()


def _parse_impact_row(row: sqlite3.Row) -> dict:
    """Parse a DB row into a dict with JSON fields deserialized."""
    d = dict(row)
    for field in ("bullish_sectors", "bearish_sectors", "bullish_assets", "bearish_assets"):
        val = d.get(field, "[]")
        if isinstance(val, str):
            try:
                d[field] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                d[field] = []
    return d


def get_impact(news_id: str) -> Optional[dict]:
    """Get impact analysis for a specific news article."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM news_impacts WHERE news_id = ?", (news_id,)
        ).fetchone()
        return _parse_impact_row(row) if row else None
    finally:
        conn.close()


def get_impact_by_id(impact_id: str) -> Optional[dict]:
    """Get impact by its own ID."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM news_impacts WHERE id = ?", (impact_id,)
        ).fetchone()
        return _parse_impact_row(row) if row else None
    finally:
        conn.close()


def get_trending_impacts(limit: int = 10, market: str = "",
                         min_confidence: int = 0) -> List[dict]:
    """Get recent high-impact news analyses."""
    conn = _get_conn()
    try:
        sql = "SELECT * FROM news_impacts WHERE confidence_score >= ?"
        params: list = [min_confidence]

        if market:
            sql += " AND news_market = ?"
            params.append(market)

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        return [_parse_impact_row(r) for r in rows]
    finally:
        conn.close()


def get_radar(market: str = "", limit: int = 20,
              hours: int = 24, min_confidence: int = 0) -> dict:
    """Get market radar data: aggregated sector/asset impacts.

    Returns:
        dict with top_bullish_sectors, top_bearish_sectors,
        trending_assets, most_impactful_news
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    conn = _get_conn()
    try:
        sql = """SELECT * FROM news_impacts
                 WHERE created_at >= ? AND confidence_score >= ?"""
        params: list = [cutoff, min_confidence]

        if market:
            sql += " AND news_market = ?"
            params.append(market)

        sql += " ORDER BY confidence_score DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        impacts = [_parse_impact_row(r) for r in rows]

        # Aggregate sectors
        bull_sector_counts: Dict[str, int] = {}
        bear_sector_counts: Dict[str, int] = {}
        bull_asset_counts: Dict[str, int] = {}
        bear_asset_counts: Dict[str, int] = {}

        for imp in impacts:
            for s in imp.get("bullish_sectors", []):
                bull_sector_counts[s] = bull_sector_counts.get(s, 0) + 1
            for s in imp.get("bearish_sectors", []):
                bear_sector_counts[s] = bear_sector_counts.get(s, 0) + 1
            for a in imp.get("bullish_assets", []):
                bull_asset_counts[a] = bull_asset_counts.get(a, 0) + 1
            for a in imp.get("bearish_assets", []):
                bear_asset_counts[a] = bear_asset_counts.get(a, 0) + 1

        return {
            "top_bullish_sectors": sorted(bull_sector_counts.items(),
                                          key=lambda x: -x[1])[:10],
            "top_bearish_sectors": sorted(bear_sector_counts.items(),
                                          key=lambda x: -x[1])[:10],
            "trending_bullish_assets": sorted(bull_asset_counts.items(),
                                              key=lambda x: -x[1])[:10],
            "trending_bearish_assets": sorted(bear_asset_counts.items(),
                                              key=lambda x: -x[1])[:10],
            "most_impactful_news": impacts[:5],
            "total_analyzed": len(impacts),
            "market_filter": market or "all",
            "hours": hours,
        }
    finally:
        conn.close()


def get_top_sectors(hours: int = 24, limit: int = 5) -> dict:
    """Get top bullish and bearish sectors in the time window."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM news_impacts WHERE created_at >= ? ORDER BY confidence_score DESC",
            (cutoff,)
        ).fetchall()
        impacts = [_parse_impact_row(r) for r in rows]

        bull: Dict[str, int] = {}
        bear: Dict[str, int] = {}
        for imp in impacts:
            for s in imp.get("bullish_sectors", []):
                bull[s] = bull.get(s, 0) + 1
            for s in imp.get("bearish_sectors", []):
                bear[s] = bear.get(s, 0) + 1

        return {
            "bullish": sorted(bull.items(), key=lambda x: -x[1])[:limit],
            "bearish": sorted(bear.items(), key=lambda x: -x[1])[:limit],
        }
    finally:
        conn.close()


def get_most_impacted_assets(hours: int = 24, limit: int = 10) -> dict:
    """Get most mentioned assets in impact analyses."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM news_impacts WHERE created_at >= ? ORDER BY confidence_score DESC",
            (cutoff,)
        ).fetchall()
        impacts = [_parse_impact_row(r) for r in rows]

        counts: Dict[str, Dict[str, int]] = {}
        for imp in impacts:
            for a in imp.get("bullish_assets", []):
                if a not in counts:
                    counts[a] = {"bullish": 0, "bearish": 0}
                counts[a]["bullish"] += 1
            for a in imp.get("bearish_assets", []):
                if a not in counts:
                    counts[a] = {"bullish": 0, "bearish": 0}
                counts[a]["bearish"] += 1

        ranked = sorted(counts.items(),
                        key=lambda x: -(x[1]["bullish"] + x[1]["bearish"]))[:limit]
        return [
            {"asset": a, "bullish_mentions": c["bullish"],
             "bearish_mentions": c["bearish"],
             "total": c["bullish"] + c["bearish"]}
            for a, c in ranked
        ]
    finally:
        conn.close()


def analyze_batch(news_list: List[dict]) -> List[dict]:
    """Analyze multiple news articles."""
    results = []
    for news in news_list:
        try:
            result = analyze(news)
            results.append(result)
        except Exception as e:
            _logger.warning("Failed to analyze news '%s': %s",
                            news.get("title", "?")[:50], e)
    return results


def delete_impact(news_id: str) -> bool:
    """Delete impact record."""
    with _lock:
        conn = _get_conn()
        try:
            cur = conn.execute(
                "DELETE FROM news_impacts WHERE news_id = ?", (news_id,)
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()
