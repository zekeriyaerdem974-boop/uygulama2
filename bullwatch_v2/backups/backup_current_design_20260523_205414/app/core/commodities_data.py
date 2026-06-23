# -*- coding: utf-8 -*-
"""Commodities data service.

FAZ 16 + FAZ 17 — Real market data via Yahoo Finance.
Commodity futures use =F suffix on Yahoo Finance.
Expanded: Metals + Energy + Agriculture (~15 symbols).
"""
from __future__ import annotations

import logging
from typing import List, Dict

from app.core.yahoo_client import get_symbols_info, get_ticker, get_klines

_logger = logging.getLogger("zkr_analiz.commodities")

# ── Metals + Energy + Agriculture ────────────────────────────────────
DEFAULT_SYMBOLS = [
    # Precious Metals
    "GC=F",    # Gold
    "SI=F",    # Silver
    "PL=F",    # Platinum
    "PA=F",    # Palladium
    # Base Metals
    "HG=F",    # Copper
    # Energy
    "CL=F",    # Crude Oil WTI
    "BZ=F",    # Brent Crude
    "NG=F",    # Natural Gas
    "RB=F",    # Gasoline (RBOB)
    "HO=F",    # Heating Oil
    # Agriculture
    "ZW=F",    # Wheat
    "ZC=F",    # Corn
    "ZS=F",    # Soybeans
    "KC=F",    # Coffee
    "CC=F",    # Cocoa
    "CT=F",    # Cotton
    "SB=F",    # Sugar
]


class CommoditiesDataService:
    """Commodities data service using Yahoo Finance."""

    MARKET_TYPE = "commodities"

    @staticmethod
    def get_symbols() -> List[Dict]:
        """Return list of commodity symbols with prices."""
        return get_symbols_info(DEFAULT_SYMBOLS, market_type="commodities")

    @staticmethod
    def get_ticker_single(symbol: str) -> Dict:
        """Return ticker data for a single commodity."""
        return get_ticker(symbol)

    @staticmethod
    def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> List[Dict]:
        """Return OHLCV kline data for a commodity."""
        return get_klines(symbol, interval, limit)
