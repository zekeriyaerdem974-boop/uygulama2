# -*- coding: utf-8 -*-
"""Forex data service.

FAZ 16 + FAZ 17 — Real market data via Yahoo Finance.
Forex symbols use =X suffix on Yahoo Finance.
Expanded: Major + Minor + Exotic pairs (~25 pairs).
"""
from __future__ import annotations

import logging
from typing import List, Dict

from app.core.yahoo_client import get_symbols_info, get_ticker, get_klines

_logger = logging.getLogger("zkr_analiz.forex")

# ── Major + Minor + Exotic Forex Pairs ───────────────────────────────
DEFAULT_SYMBOLS = [
    # Majors
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X",
    "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
    # TRY pairs
    "USDTRY=X", "EURTRY=X", "GBPTRY=X",
    # Cross pairs
    "EURGBP=X", "EURJPY=X", "GBPJPY=X", "AUDJPY=X",
    "EURAUD=X", "EURNZD=X", "GBPAUD=X", "GBPNZD=X",
    "AUDNZD=X", "AUDCAD=X", "CADCHF=X", "CADJPY=X",
    "CHFJPY=X", "NZDJPY=X", "NZDCAD=X",
]


class ForexDataService:
    """Forex data service using Yahoo Finance."""

    MARKET_TYPE = "forex"

    @staticmethod
    def get_symbols() -> List[Dict]:
        """Return list of Forex symbols with prices."""
        return get_symbols_info(DEFAULT_SYMBOLS, market_type="forex")

    @staticmethod
    def get_ticker_single(symbol: str) -> Dict:
        """Return ticker data for a single Forex pair."""
        return get_ticker(symbol)

    @staticmethod
    def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> List[Dict]:
        """Return OHLCV kline data for a Forex pair."""
        return get_klines(symbol, interval, limit)
