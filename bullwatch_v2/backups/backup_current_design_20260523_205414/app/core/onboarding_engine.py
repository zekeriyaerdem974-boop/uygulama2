# -*- coding: utf-8 -*-
"""Onboarding & User Preferences Engine — FAZ 46.

Manages user preferences, onboarding state, and watchlist initialization
for new users.

Uses the existing ``user_data`` table (key-value store per user) via
:mod:`app.core.user_engine`.

Public API:
  get_preferences(user_id)        → dict
  save_preferences(user_id, prefs) → bool
  is_onboarding_completed(user_id) → bool
  complete_onboarding(user_id, markets, symbols) → bool
  init_default_watchlist(user_id, markets) → list
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from app.core.user_engine import save_user_data, load_user_data

_logger = logging.getLogger("zkr_analiz.onboarding")

# ── Default watchlist per market ──────────────────────────────────
DEFAULT_WATCHLISTS: Dict[str, List[dict]] = {
    "crypto": [
        {"symbol": "BTCUSDT", "market": "crypto"},
        {"symbol": "ETHUSDT", "market": "crypto"},
        {"symbol": "SOLUSDT", "market": "crypto"},
    ],
    "stocks": [
        {"symbol": "AAPL", "market": "stocks"},
        {"symbol": "NVDA", "market": "stocks"},
        {"symbol": "MSFT", "market": "stocks"},
    ],
    "bist": [
        {"symbol": "THYAO", "market": "bist"},
        {"symbol": "ASELS", "market": "bist"},
        {"symbol": "GARAN", "market": "bist"},
    ],
    "forex": [
        {"symbol": "EURUSD", "market": "forex"},
        {"symbol": "GBPUSD", "market": "forex"},
        {"symbol": "USDJPY", "market": "forex"},
    ],
    "commodities": [
        {"symbol": "XAUUSD", "market": "commodities"},
        {"symbol": "XAGUSD", "market": "commodities"},
        {"symbol": "CLUSD", "market": "commodities"},
    ],
}

_PREF_KEY = "preferences"
_WATCHLIST_KEY = "watchlist"


# ══════════════════════════════════════════════════════════════════════
# PREFERENCES
# ══════════════════════════════════════════════════════════════════════

def get_preferences(user_id: str) -> dict:
    """Load user preferences. Returns empty dict if none saved."""
    data = load_user_data(user_id, _PREF_KEY)
    if data is None:
        return {}
    return data


def save_preferences(user_id: str, prefs: dict) -> bool:
    """Save user preferences (merge with existing)."""
    current = get_preferences(user_id)
    current.update(prefs)
    return save_user_data(user_id, _PREF_KEY, current)


def is_onboarding_completed(user_id: str) -> bool:
    """Check if user has completed onboarding."""
    prefs = get_preferences(user_id)
    return prefs.get("onboarding_completed", False)


def complete_onboarding(user_id: str, markets: List[str],
                        symbols: List[str]) -> bool:
    """Mark onboarding as complete and save chosen markets/symbols.

    Also initialises the default watchlist based on selected markets.
    """
    prefs = {
        "onboarding_completed": True,
        "preferred_markets": markets,
        "watchlist_symbols": symbols,
    }
    ok = save_preferences(user_id, prefs)
    if ok:
        init_default_watchlist(user_id, markets)
        _logger.info("Onboarding completed for user %s", user_id)
    return ok


# ══════════════════════════════════════════════════════════════════════
# WATCHLIST INITIALISATION
# ══════════════════════════════════════════════════════════════════════

def init_default_watchlist(user_id: str,
                           markets: List[str]) -> List[dict]:
    """Build and save a default watchlist from the selected markets.

    Does NOT overwrite an existing watchlist — only creates if empty.
    Returns the watchlist that was saved.
    """
    existing = load_user_data(user_id, _WATCHLIST_KEY)
    if existing:
        return existing if isinstance(existing, list) else []

    watchlist: List[dict] = []
    seen = set()
    for mkt in markets:
        for item in DEFAULT_WATCHLISTS.get(mkt, []):
            if item["symbol"] not in seen:
                watchlist.append(item)
                seen.add(item["symbol"])

    save_user_data(user_id, _WATCHLIST_KEY, watchlist)
    _logger.info("Default watchlist created for user %s: %d items",
                 user_id, len(watchlist))
    return watchlist
