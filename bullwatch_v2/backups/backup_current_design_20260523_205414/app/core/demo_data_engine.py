# -*- coding: utf-8 -*-
"""Demo Data Engine — FAZ 46.

Generates synthetic demo content so that new users never see empty
screens.  All demo items are tagged ``"demo": True`` so they can be
filtered out once the user creates real data.

Public API:
  get_demo_activity(limit=10)      → list[dict]
  get_demo_opportunities(limit=6)  → list[dict]
  get_demo_portfolio()             → list[dict]
  get_demo_news(limit=5)           → list[dict]
  get_trending_assets()            → list[dict]
  get_popular_opportunities()      → list[dict]
  seed_demo_portfolio(user_id)     → bool
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List

_logger = logging.getLogger("zkr_analiz.demo_data")


# ══════════════════════════════════════════════════════════════════════
# DEMO ACTIVITY EVENTS
# ══════════════════════════════════════════════════════════════════════

_DEMO_EVENTS = [
    {
        "type": "volume_spike",
        "symbol": "BTCUSDT",
        "market": "crypto",
        "title": "BTC Volume Spike Detected",
        "description": "24h volume increased 340% — whale accumulation pattern.",
        "severity": "high",
    },
    {
        "type": "momentum_shift",
        "symbol": "NVDA",
        "market": "stocks",
        "title": "NVDA Momentum Shift",
        "description": "RSI crossed 70 with strong volume confirmation.",
        "severity": "medium",
    },
    {
        "type": "sector_activity",
        "symbol": "BIST_BANK",
        "market": "bist",
        "title": "BIST Banking Sector Activity",
        "description": "Banking index up 2.8%  — sector rotation underway.",
        "severity": "medium",
    },
    {
        "type": "breakout",
        "symbol": "ETHUSDT",
        "market": "crypto",
        "title": "ETH Breakout Alert",
        "description": "Price broke above $3,800 resistance with high volume.",
        "severity": "high",
    },
    {
        "type": "divergence",
        "symbol": "AAPL",
        "market": "stocks",
        "title": "AAPL RSI Divergence",
        "description": "Bearish divergence forming on the daily chart.",
        "severity": "low",
    },
    {
        "type": "correlation",
        "symbol": "XAUUSD",
        "market": "commodities",
        "title": "Gold-Dollar Correlation Break",
        "description": "Gold rising despite DXY strength — unusual pattern.",
        "severity": "medium",
    },
    {
        "type": "volume_spike",
        "symbol": "SOLUSDT",
        "market": "crypto",
        "title": "SOL DeFi Activity Surge",
        "description": "On-chain transaction volume hit 30-day high.",
        "severity": "medium",
    },
    {
        "type": "earnings",
        "symbol": "MSFT",
        "market": "stocks",
        "title": "MSFT Earnings Beat",
        "description": "Revenue beat estimates by 4.2%  — cloud growth strong.",
        "severity": "high",
    },
    {
        "type": "momentum_shift",
        "symbol": "THYAO",
        "market": "bist",
        "title": "THYAO Momentum Building",
        "description": "Stock up 5 consecutive days; MACD crossover confirmed.",
        "severity": "medium",
    },
    {
        "type": "whale_alert",
        "symbol": "BTCUSDT",
        "market": "crypto",
        "title": "Large BTC Transfer",
        "description": "2,500 BTC moved from exchange to cold wallet.",
        "severity": "high",
    },
]


def get_demo_activity(limit: int = 10) -> List[dict]:
    """Return demo activity-stream events."""
    now = datetime.now(timezone.utc)
    events = []
    for i, evt in enumerate(_DEMO_EVENTS[:limit]):
        events.append({
            **evt,
            "id": f"demo-evt-{i}",
            "demo": True,
            "demo_event": True,
            "created_at": (now - timedelta(minutes=i * 12)).isoformat(),
        })
    return events


# ══════════════════════════════════════════════════════════════════════
# DEMO OPPORTUNITIES
# ══════════════════════════════════════════════════════════════════════

_DEMO_OPPS = [
    {
        "symbol": "BTCUSDT",
        "market": "crypto",
        "direction": "long",
        "title": "BTC Accumulation Zone",
        "score": 87,
        "reason": "On-chain metrics show strong accumulation by long-term holders. Hash rate at ATH.",
    },
    {
        "symbol": "NVDA",
        "market": "stocks",
        "direction": "long",
        "title": "NVDA AI Demand Wave",
        "score": 82,
        "reason": "GPU demand outpacing supply. Data center revenue growing 150% YoY.",
    },
    {
        "symbol": "ETHUSDT",
        "market": "crypto",
        "direction": "long",
        "title": "ETH Network Upgrade",
        "score": 78,
        "reason": "EIP-4844 reducing L2 fees. TVL increasing across DeFi protocols.",
    },
    {
        "symbol": "XAUUSD",
        "market": "commodities",
        "direction": "long",
        "title": "Gold Safe Haven",
        "score": 75,
        "reason": "Central bank buying at record levels. Geopolitical uncertainty rising.",
    },
    {
        "symbol": "THYAO",
        "market": "bist",
        "direction": "long",
        "title": "THYAO Passenger Growth",
        "score": 72,
        "reason": "International passenger numbers up 18%. Fleet expansion on track.",
    },
    {
        "symbol": "SOLUSDT",
        "market": "crypto",
        "direction": "long",
        "title": "SOL Ecosystem Growth",
        "score": 70,
        "reason": "DeFi TVL surpassed $5B. Transaction throughput at network highs.",
    },
]


def get_demo_opportunities(limit: int = 6) -> List[dict]:
    """Return demo opportunity cards."""
    now = datetime.now(timezone.utc)
    opps = []
    for i, opp in enumerate(_DEMO_OPPS[:limit]):
        opps.append({
            **opp,
            "id": f"demo-opp-{i}",
            "demo": True,
            "created_at": (now - timedelta(hours=i * 3)).isoformat(),
        })
    return opps


# ══════════════════════════════════════════════════════════════════════
# DEMO PORTFOLIO
# ══════════════════════════════════════════════════════════════════════

_DEMO_PORTFOLIO = [
    {"symbol": "BTCUSDT", "market": "crypto", "amount": 0.5,
     "entry_price": 42000, "current_price": 67500},
    {"symbol": "ETHUSDT", "market": "crypto", "amount": 2.0,
     "entry_price": 2200, "current_price": 3750},
    {"symbol": "AAPL", "market": "stocks", "amount": 10,
     "entry_price": 175, "current_price": 198},
]


def get_demo_portfolio() -> List[dict]:
    """Return sample demo portfolio assets."""
    return [
        {**a, "demo": True, "id": f"demo-asset-{i}"}
        for i, a in enumerate(_DEMO_PORTFOLIO)
    ]


def seed_demo_portfolio(user_id: str) -> bool:
    """Insert demo portfolio assets for a user (if portfolio empty)."""
    try:
        from app.core.portfolio_engine import get_assets, add_asset
        existing = get_assets(user_id)
        if existing:
            return False
        for a in _DEMO_PORTFOLIO:
            add_asset(user_id, a["symbol"], a["market"],
                      a["amount"], a["entry_price"])
        _logger.info("Demo portfolio seeded for user %s", user_id)
        return True
    except Exception as e:
        _logger.warning("seed_demo_portfolio error: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════
# DEMO NEWS
# ══════════════════════════════════════════════════════════════════════

_DEMO_NEWS = [
    {
        "title": "Bitcoin Surges Past Key Resistance Level",
        "source": "CryptoInsight",
        "category": "crypto",
    },
    {
        "title": "Fed Signals Potential Rate Cut in Next Quarter",
        "source": "MarketWatch",
        "category": "macro",
    },
    {
        "title": "NVIDIA Reports Record Data Center Revenue",
        "source": "TechDaily",
        "category": "stocks",
    },
    {
        "title": "BIST 100 Hits All-Time High on Banking Sector Rally",
        "source": "BloombergHT",
        "category": "bist",
    },
    {
        "title": "Gold Demand From Central Banks Reaches Historic Levels",
        "source": "Reuters",
        "category": "commodities",
    },
]


def get_demo_news(limit: int = 5) -> List[dict]:
    """Return demo news items."""
    now = datetime.now(timezone.utc)
    return [
        {**n, "demo": True, "id": f"demo-news-{i}",
         "published_at": (now - timedelta(hours=i * 2)).isoformat()}
        for i, n in enumerate(_DEMO_NEWS[:limit])
    ]


# ══════════════════════════════════════════════════════════════════════
# TRENDING / POPULAR (for discover page when user has no history)
# ══════════════════════════════════════════════════════════════════════

_TRENDING = [
    {"symbol": "BTCUSDT", "market": "crypto", "name": "Bitcoin",
     "change_pct": 4.2, "volume_rank": 1},
    {"symbol": "ETHUSDT", "market": "crypto", "name": "Ethereum",
     "change_pct": 3.1, "volume_rank": 2},
    {"symbol": "SOLUSDT", "market": "crypto", "name": "Solana",
     "change_pct": 8.7, "volume_rank": 3},
    {"symbol": "NVDA", "market": "stocks", "name": "NVIDIA",
     "change_pct": 2.5, "volume_rank": 4},
    {"symbol": "THYAO", "market": "bist", "name": "Türk Hava Yolları",
     "change_pct": 3.9, "volume_rank": 5},
    {"symbol": "XAUUSD", "market": "commodities", "name": "Gold",
     "change_pct": 1.2, "volume_rank": 6},
]


def get_trending_assets() -> List[dict]:
    """Return trending assets for discover page."""
    return [{**a, "demo": True} for a in _TRENDING]


def get_popular_opportunities() -> List[dict]:
    """Alias for demo opportunities — shown on discover when no history."""
    return get_demo_opportunities(limit=4)
