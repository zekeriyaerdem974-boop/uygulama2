# -*- coding: utf-8 -*-
"""News API routes.

FAZ 15 + FAZ 16 + FAZ 24B — Market intelligence endpoints.

GET /api/news          — General news (type=crypto|macro|market|stocks|bist|forex|commodities|etf|kap)
GET /api/news/coin     — Symbol-specific crypto news (symbol=BTCUSDT)
GET /api/news/symbol   — Universal symbol news (symbol=AAPL&market=stocks)
"""
from __future__ import annotations

import logging

from flask import jsonify, request

from app.blueprints.news import news_bp
from app.cache import cache_get_or_set
from app.core.news_service import NewsService

_logger = logging.getLogger("zkr_analiz.news.routes")

# Cache TTLs (seconds)
_CRYPTO_TTL = 180   # 3 minutes
_MACRO_TTL = 300    # 5 minutes
_COIN_TTL = 180     # 3 minutes
_MARKET_NEWS_TTL = 180  # 3 minutes

# Map type → fetcher
_FETCHER_MAP = {
    "crypto": ("news:crypto", _CRYPTO_TTL, NewsService.fetch_crypto_news),
    "macro": ("news:macro", _MACRO_TTL, NewsService.fetch_macro_news),
    "market": ("news:market", _CRYPTO_TTL, NewsService.fetch_market_news),
    "stocks": ("news:stocks", _MARKET_NEWS_TTL, NewsService.fetch_stocks_news),
    "bist": ("news:bist", _MARKET_NEWS_TTL, NewsService.fetch_bist_news),
    "forex": ("news:forex", _MARKET_NEWS_TTL, NewsService.fetch_forex_news),
    "commodities": ("news:commodities", _MARKET_NEWS_TTL, NewsService.fetch_commodities_news),
    "etf": ("news:etf", _MARKET_NEWS_TTL, NewsService.fetch_etf_news),
    "kap": ("news:kap", _MARKET_NEWS_TTL, NewsService.fetch_kap_news),
}


@news_bp.route("/api/news", methods=["GET"])
def api_news():
    """Return news articles.

    Query params:
        type: 'crypto' (default), 'macro', 'market', 'stocks', 'bist',
              'forex', 'commodities', 'etf', 'kap'
    """
    news_type = request.args.get("type", "crypto").lower()
    entry = _FETCHER_MAP.get(news_type, _FETCHER_MAP["crypto"])
    cache_key, ttl, fetcher = entry

    data = cache_get_or_set(cache_key, ttl, fetcher)
    if data is None:
        data = []

    return jsonify({"ok": True, "count": len(data), "data": data})


@news_bp.route("/api/news/coin", methods=["GET"])
def api_news_coin():
    """Return news filtered for a specific coin.

    Query params:
        symbol: Trading pair like 'BTCUSDT' or base like 'BTC'
    """
    symbol = request.args.get("symbol", "").strip().upper()
    if not symbol:
        return jsonify({"ok": False, "error": "Missing 'symbol' parameter"}), 400

    base = symbol.replace("USDT", "").replace("BUSD", "").replace("USDC", "")
    cache_key = f"news:coin:{base}"

    data = cache_get_or_set(cache_key, _COIN_TTL, NewsService.fetch_coin_news, symbol)
    if data is None:
        data = []

    return jsonify({"ok": True, "symbol": symbol, "count": len(data), "data": data})


@news_bp.route("/api/news/symbol", methods=["GET"])
def api_news_symbol():
    """Return news for any symbol across all markets.

    Query params:
        symbol: e.g. 'AAPL', 'THYAO.IS', 'BTCUSDT', 'EURUSD=X', 'GC=F'
        market: 'auto' (default), 'crypto', 'stocks', 'bist', 'forex', 'commodities'
    """
    symbol = request.args.get("symbol", "").strip().upper()
    market = request.args.get("market", "auto").lower()
    if not symbol:
        return jsonify({"ok": False, "error": "Missing 'symbol' parameter"}), 400

    cache_key = f"news:symbol:{symbol}:{market}"

    data = cache_get_or_set(
        cache_key, _COIN_TTL, NewsService.fetch_symbol_news, symbol, market
    )
    if data is None:
        data = []

    return jsonify({"ok": True, "symbol": symbol, "market": market,
                    "count": len(data), "data": data})
