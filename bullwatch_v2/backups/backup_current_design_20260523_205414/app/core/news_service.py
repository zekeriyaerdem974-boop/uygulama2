# -*- coding: utf-8 -*-
"""News Service — Market intelligence system.

FAZ 15 + FAZ 16 + FAZ 24B — Deep news system with detail views,
KAP integration, ETF/SEC tracking, and symbol-based matching.

Sources:
  * CoinDesk RSS
  * CoinTelegraph RSS
  * CryptoPanic API (free tier)
  * Google News RSS (crypto, macro, stocks, bist, forex, commodities, etf/sec)
  * KAP (Borsa Istanbul corporate disclosures via Google News)
  * Bitcoin Magazine RSS

All fetch functions return a unified list of dicts:
  { id, source, title, summary, url, published_at, sentiment, symbols,
    category, market, image_url }
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.error import URLError
from urllib.request import Request, urlopen
from html import unescape
import json

_logger = logging.getLogger("zkr_analiz.news")

# ── Sentiment keywords ──
_BULLISH_WORDS = {
    "surge", "rally", "bull", "bullish", "soar", "jump", "gain", "rise",
    "approval", "approve", "etf approved", "adopt", "adoption", "breakout",
    "record", "high", "inflow", "upgrade", "milestone", "growth", "positive",
    "accumulate", "institutional", "buy", "bought",
    "yüksel", "boğa", "artış", "rekor", "onay", "kâr", "temettü",
}
_BEARISH_WORDS = {
    "crash", "bear", "bearish", "drop", "plunge", "dump", "hack", "fraud",
    "ban", "regulate", "sell", "selloff", "decline", "loss", "risk", "fear",
    "liquidat", "bankruptcy", "bankrupt", "lawsuit", "investigation",
    "warning", "correction", "outflow", "panic", "collapse",
    "düşüş", "ayı", "çöküş", "kayıp", "zarar", "ceza",
}

# ── Symbol maps ──
_CRYPTO_SYMBOL_MAP = {
    "bitcoin": "BTC", "btc": "BTC", "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL", "ripple": "XRP", "xrp": "XRP",
    "cardano": "ADA", "ada": "ADA", "dogecoin": "DOGE", "doge": "DOGE",
    "bnb": "BNB", "binance coin": "BNB", "avalanche": "AVAX", "avax": "AVAX",
    "polygon": "MATIC", "matic": "MATIC", "polkadot": "DOT", "dot": "DOT",
    "chainlink": "LINK", "litecoin": "LTC", "ltc": "LTC",
    "shiba": "SHIB", "tron": "TRX", "trx": "TRX", "near": "NEAR",
    "sui": "SUI", "pepe": "PEPE", "arbitrum": "ARB", "optimism": "OP",
}

_STOCK_SYMBOL_MAP = {
    "apple": "AAPL", "aapl": "AAPL",
    "microsoft": "MSFT", "msft": "MSFT",
    "google": "GOOGL", "alphabet": "GOOGL", "googl": "GOOGL",
    "amazon": "AMZN", "amzn": "AMZN",
    "nvidia": "NVDA", "nvda": "NVDA",
    "tesla": "TSLA", "tsla": "TSLA",
    "meta": "META", "facebook": "META",
    "amd": "AMD", "netflix": "NFLX", "nflx": "NFLX",
    "intel": "INTC", "intc": "INTC",
    "disney": "DIS", "boeing": "BA",
    "jpmorgan": "JPM", "goldman sachs": "GS",
    "coinbase": "COIN", "microstrategy": "MSTR",
}

_BIST_SYMBOL_MAP = {
    "thyao": "THYAO", "thy": "THYAO", "türk hava": "THYAO",
    "asels": "ASELS", "aselsan": "ASELS",
    "garan": "GARAN", "garanti": "GARAN",
    "tuprs": "TUPRS", "tüpraş": "TUPRS",
    "sise": "SISE", "şişecam": "SISE",
    "kchol": "KCHOL", "koç holding": "KCHOL",
    "akbnk": "AKBNK", "akbank": "AKBNK",
    "eregl": "EREGL", "ereğli": "EREGL",
    "bimas": "BIMAS", "bim": "BIMAS",
    "sahol": "SAHOL", "sabancı": "SAHOL",
    "tcell": "TCELL", "turkcell": "TCELL",
    "pgsus": "PGSUS", "pegasus": "PGSUS",
    "arclk": "ARCLK", "arçelik": "ARCLK",
    "toaso": "TOASO", "tofaş": "TOASO",
    "froto": "FROTO", "ford otosan": "FROTO",
    "sasa": "SASA", "petkm": "PETKM", "petkim": "PETKM",
    "vestl": "VESTL", "vestel": "VESTL",
}

# Backward compat alias (used by old code)
_SYMBOL_MAP = _CRYPTO_SYMBOL_MAP

_USER_AGENT = "ZKR Analiz/2.0 NewsBot"
_TIMEOUT = 10

# ── Helpers ──

def _make_id(title: str, source: str) -> str:
    raw = f"{source}:{title}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:12]


def _detect_sentiment(text: str) -> str:
    lower = text.lower()
    bull = sum(1 for w in _BULLISH_WORDS if w in lower)
    bear = sum(1 for w in _BEARISH_WORDS if w in lower)
    if bull > bear:
        return "bullish"
    if bear > bull:
        return "bearish"
    return "neutral"


def _extract_symbols(text: str, market: str = "all") -> list[str]:
    lower = text.lower()
    found = set()
    maps = []
    if market in ("all", "crypto"):
        maps.append(_CRYPTO_SYMBOL_MAP)
    if market in ("all", "stocks"):
        maps.append(_STOCK_SYMBOL_MAP)
    if market in ("all", "bist", "kap"):
        maps.append(_BIST_SYMBOL_MAP)
    for sm in maps:
        for kw, sym in sm.items():
            if kw in lower:
                found.add(sym)
    return sorted(found) if found else []


def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def _parse_rfc822(datestr: str) -> str:
    if not datestr:
        return datetime.now(timezone.utc).isoformat()
    for fmt in (
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y %H:%M",
    ):
        try:
            dt = datetime.strptime(datestr.strip(), fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return datestr


def _fetch_url(url: str, timeout: int = _TIMEOUT) -> Optional[bytes]:
    try:
        req = Request(url, headers={"User-Agent": _USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (URLError, OSError, TimeoutError) as e:
        _logger.warning("Failed to fetch %s: %s", url, e)
        return None


def _parse_rss(url: str, source_name: str, max_items: int = 20,
               market: str = "all", category: str = "general") -> list[dict]:
    raw = _fetch_url(url)
    if not raw:
        return []
    items = []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        _logger.warning("RSS parse error for %s: %s", source_name, e)
        return []

    ns = {"atom": "http://www.w3.org/2005/Atom"}
    rss_items = root.findall(".//item")
    if not rss_items:
        rss_items = root.findall(".//atom:entry", ns)
        if not rss_items:
            rss_items = root.findall(".//{http://www.w3.org/2005/Atom}entry")

    for item in rss_items[:max_items]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = item.findtext("description") or ""
        pub = item.findtext("pubDate") or item.findtext("published") or ""

        if not title:
            title = item.findtext("{http://www.w3.org/2005/Atom}title") or ""
        if not link:
            link_el = item.find("{http://www.w3.org/2005/Atom}link")
            link = link_el.get("href", "") if link_el is not None else ""
        if not desc:
            desc = item.findtext("{http://www.w3.org/2005/Atom}summary") or ""
            if not desc:
                desc = item.findtext("{http://www.w3.org/2005/Atom}content") or ""
        if not pub:
            pub = item.findtext("{http://www.w3.org/2005/Atom}published") or ""
            if not pub:
                pub = item.findtext("{http://www.w3.org/2005/Atom}updated") or ""

        image_url = ""
        enc = item.find("enclosure")
        if enc is not None and "image" in (enc.get("type") or ""):
            image_url = enc.get("url", "")
        if not image_url:
            media = item.find("{http://search.yahoo.com/mrss/}thumbnail")
            if media is not None:
                image_url = media.get("url", "")

        title = _strip_html(title)
        summary = _strip_html(desc)
        full_text = f"{title} {summary}"

        items.append({
            "id": _make_id(title, source_name),
            "source": source_name,
            "title": title,
            "summary": summary[:400],
            "url": link,
            "published_at": _parse_rfc822(pub),
            "sentiment": _detect_sentiment(full_text),
            "symbols": _extract_symbols(full_text, market),
            "category": category,
            "market": market,
            "image_url": image_url,
        })
    return items


# ══════════════════════════════════════════════════════════════════════
# SOURCE FETCHERS
# ══════════════════════════════════════════════════════════════════════

def fetch_coindesk_rss():
    return _parse_rss("https://www.coindesk.com/arc/outboundfeeds/rss/",
                      "CoinDesk", market="crypto", category="crypto")

def fetch_cointelegraph_rss():
    return _parse_rss("https://cointelegraph.com/rss",
                      "CoinTelegraph", market="crypto", category="crypto")

def fetch_bitcoin_magazine_rss():
    return _parse_rss("https://bitcoinmagazine.com/feed",
                      "Bitcoin Magazine", market="crypto", category="crypto")

def fetch_google_news_crypto():
    return _parse_rss(
        "https://news.google.com/rss/search?q=cryptocurrency+OR+bitcoin+OR+ethereum&hl=en-US&gl=US&ceid=US:en",
        "Google News", market="crypto", category="crypto")

def fetch_google_news_macro():
    return _parse_rss(
        "https://news.google.com/rss/search?q=federal+reserve+OR+inflation+OR+interest+rate+OR+economy&hl=en-US&gl=US&ceid=US:en",
        "Macro News", market="macro", category="macro")

def fetch_google_news_stocks():
    return _parse_rss(
        "https://news.google.com/rss/search?q=stock+market+OR+Wall+Street+OR+S%26P+500+OR+NASDAQ+OR+earnings&hl=en-US&gl=US&ceid=US:en",
        "Stock News", market="stocks", category="stocks")

def fetch_google_news_stock_earnings():
    return _parse_rss(
        "https://news.google.com/rss/search?q=earnings+report+OR+quarterly+results+OR+analyst+upgrade+OR+guidance+OR+revenue+beat&hl=en-US&gl=US&ceid=US:en",
        "Earnings News", market="stocks", category="earnings")

def fetch_google_news_stock_company(symbol: str):
    name_map = {
        "AAPL": "Apple", "MSFT": "Microsoft", "GOOGL": "Google+Alphabet",
        "AMZN": "Amazon", "NVDA": "Nvidia", "TSLA": "Tesla",
        "META": "Meta+Platforms", "AMD": "AMD", "NFLX": "Netflix",
        "INTC": "Intel", "DIS": "Disney", "BA": "Boeing",
        "COIN": "Coinbase", "MSTR": "MicroStrategy",
    }
    query = name_map.get(symbol.upper(), symbol)
    return _parse_rss(
        f"https://news.google.com/rss/search?q={query}+stock+OR+{symbol}+earnings&hl=en-US&gl=US&ceid=US:en",
        "Company News", market="stocks", category="stocks")

def fetch_google_news_bist():
    return _parse_rss(
        "https://news.google.com/rss/search?q=borsa+istanbul+OR+BIST+OR+TCMB+OR+T%C3%BCrk+liras%C4%B1+OR+Borsa&hl=tr&gl=TR&ceid=TR:tr",
        "BIST News", market="bist", category="bist")

def fetch_kap_rss():
    items = _parse_rss(
        "https://news.google.com/rss/search?q=KAP+bildirimi+OR+%C3%B6zel+durum+a%C3%A7%C4%B1klamas%C4%B1+OR+KAP+duyuru&hl=tr&gl=TR&ceid=TR:tr",
        "KAP", market="bist", category="kap")
    items2 = _parse_rss(
        "https://news.google.com/rss/search?q=temett%C3%BC+da%C4%9F%C4%B1t%C4%B1m+OR+sermaye+art%C4%B1r%C4%B1m+OR+genel+kurul+OR+bilan%C3%A7o+borsa&hl=tr&gl=TR&ceid=TR:tr",
        "KAP", market="bist", category="kap")
    return items + items2

def fetch_google_news_bist_company(symbol: str):
    name_map = {
        "THYAO": "THY+Türk+Hava+Yolları", "ASELS": "Aselsan",
        "GARAN": "Garanti+BBVA", "TUPRS": "Tüpraş",
        "SISE": "Şişecam", "KCHOL": "Koç+Holding",
        "AKBNK": "Akbank", "EREGL": "Ereğli+Demir+Çelik",
        "BIMAS": "BİM+Mağazalar", "SAHOL": "Sabancı+Holding",
        "TCELL": "Turkcell", "PGSUS": "Pegasus",
    }
    base = symbol.upper().replace(".IS", "")
    query = name_map.get(base, base)
    return _parse_rss(
        f"https://news.google.com/rss/search?q={query}+hisse+OR+borsa+OR+bilanco&hl=tr&gl=TR&ceid=TR:tr",
        "BIST Company", market="bist", category="bist")

def fetch_google_news_forex():
    return _parse_rss(
        "https://news.google.com/rss/search?q=forex+OR+currency+OR+USD+OR+EUR+OR+central+bank+OR+FX+market&hl=en-US&gl=US&ceid=US:en",
        "Forex News", market="forex", category="forex")

def fetch_google_news_commodities():
    return _parse_rss(
        "https://news.google.com/rss/search?q=gold+price+OR+oil+price+OR+silver+OR+commodities+OR+crude+oil&hl=en-US&gl=US&ceid=US:en",
        "Commodity News", market="commodities", category="commodities")

def fetch_etf_sec_news():
    items = _parse_rss(
        "https://news.google.com/rss/search?q=bitcoin+ETF+OR+ethereum+ETF+OR+crypto+ETF+OR+spot+ETF+approval&hl=en-US&gl=US&ceid=US:en",
        "ETF News", market="crypto", category="etf")
    items2 = _parse_rss(
        "https://news.google.com/rss/search?q=SEC+crypto+OR+SEC+bitcoin+OR+SEC+regulation+OR+SEC+review+OR+SEC+deadline&hl=en-US&gl=US&ceid=US:en",
        "SEC News", market="regulation", category="sec")
    return items + items2

def fetch_cryptopanic(auth_token: Optional[str] = None):
    import os
    token = auth_token or os.getenv("CRYPTOPANIC_TOKEN", "")
    if not token:
        return _parse_rss("https://cryptopanic.com/news/rss/",
                          "CryptoPanic", market="crypto", category="crypto")
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={token}&kind=news&public=true"
    raw = _fetch_url(url)
    if not raw:
        return []
    items = []
    try:
        data = json.loads(raw)
        for post in (data.get("results") or [])[:20]:
            title = post.get("title", "")
            items.append({
                "id": _make_id(title, "CryptoPanic"),
                "source": "CryptoPanic",
                "title": title,
                "summary": title,
                "url": post.get("url", ""),
                "published_at": post.get("published_at", ""),
                "sentiment": _detect_sentiment(title),
                "symbols": [c.get("code", "") for c in (post.get("currencies") or [])],
                "category": "crypto", "market": "crypto", "image_url": "",
            })
    except (json.JSONDecodeError, KeyError) as e:
        _logger.warning("CryptoPanic parse error: %s", e)
    return items


# ══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════

class NewsService:

    @staticmethod
    def fetch_crypto_news():
        all_news = []
        for f in (fetch_coindesk_rss, fetch_cointelegraph_rss,
                  fetch_cryptopanic, fetch_google_news_crypto):
            try:
                all_news.extend(f())
            except Exception as e:
                _logger.warning("Crypto fetcher %s failed: %s", f.__name__, e)
        return NewsService._deduplicate(all_news)

    @staticmethod
    def fetch_macro_news():
        try:
            return NewsService._deduplicate(fetch_google_news_macro())
        except Exception as e:
            _logger.warning("Macro fetch failed: %s", e)
            return []

    @staticmethod
    def fetch_market_news():
        return NewsService._deduplicate(
            NewsService.fetch_crypto_news() + NewsService.fetch_macro_news())

    @staticmethod
    def fetch_stocks_news():
        all_news = []
        for f in (fetch_google_news_stocks, fetch_google_news_stock_earnings):
            try:
                all_news.extend(f())
            except Exception as e:
                _logger.warning("Stocks fetcher %s failed: %s", f.__name__, e)
        return NewsService._deduplicate(all_news)

    @staticmethod
    def fetch_bist_news():
        all_news = []
        for f in (fetch_google_news_bist, fetch_kap_rss):
            try:
                all_news.extend(f())
            except Exception as e:
                _logger.warning("BIST fetcher %s failed: %s", f.__name__, e)
        return NewsService._deduplicate(all_news)

    @staticmethod
    def fetch_kap_news():
        try:
            return NewsService._deduplicate(fetch_kap_rss())
        except Exception as e:
            _logger.warning("KAP fetch failed: %s", e)
            return []

    @staticmethod
    def fetch_forex_news():
        try:
            return NewsService._deduplicate(fetch_google_news_forex())
        except Exception as e:
            _logger.warning("Forex fetch failed: %s", e)
            return []

    @staticmethod
    def fetch_commodities_news():
        try:
            return NewsService._deduplicate(fetch_google_news_commodities())
        except Exception as e:
            _logger.warning("Commodities fetch failed: %s", e)
            return []

    @staticmethod
    def fetch_etf_news():
        try:
            return NewsService._deduplicate(fetch_etf_sec_news())
        except Exception as e:
            _logger.warning("ETF/SEC fetch failed: %s", e)
            return []

    @staticmethod
    def fetch_coin_news(symbol: str):
        base = symbol.upper().replace("USDT", "").replace("BUSD", "").replace("USDC", "")
        all_news = NewsService.fetch_crypto_news()
        filtered = []
        for item in all_news:
            syms = [s.upper() for s in item.get("symbols", [])]
            text = f"{item.get('title', '')} {item.get('summary', '')}".upper()
            if base in syms or base in text:
                filtered.append(item)
        if len(filtered) < 3:
            names = [k for k, v in _CRYPTO_SYMBOL_MAP.items() if v == base and len(k) > 3]
            for item in all_news:
                if item in filtered:
                    continue
                text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
                if any(n in text for n in names):
                    filtered.append(item)
        return filtered[:20]

    @staticmethod
    def fetch_symbol_news(symbol: str, market: str = "auto"):
        if market == "auto":
            if symbol.endswith("USDT") or symbol.endswith("BUSD"):
                market = "crypto"
            elif symbol.endswith(".IS"):
                market = "bist"
            elif symbol.endswith("=X"):
                market = "forex"
            elif symbol.endswith("=F"):
                market = "commodities"
            else:
                market = "stocks"

        if market == "crypto":
            return NewsService.fetch_coin_news(symbol)
        if market == "bist":
            base = symbol.replace(".IS", "").upper()
            all_news = NewsService.fetch_bist_news()
            try:
                all_news.extend(fetch_google_news_bist_company(base))
            except Exception:
                pass
            filtered = [it for it in all_news
                        if base in [s.upper() for s in it.get("symbols", [])]
                        or base in f"{it.get('title','')} {it.get('summary','')}".upper()]
            return NewsService._deduplicate(filtered)[:20] if filtered else all_news[:10]
        if market == "stocks":
            base = symbol.upper()
            all_news = NewsService.fetch_stocks_news()
            try:
                all_news.extend(fetch_google_news_stock_company(base))
            except Exception:
                pass
            filtered = [it for it in all_news
                        if base in [s.upper() for s in it.get("symbols", [])]
                        or base in f"{it.get('title','')} {it.get('summary','')}".upper()]
            return NewsService._deduplicate(filtered)[:20] if filtered else all_news[:10]
        if market == "forex":
            return NewsService.fetch_forex_news()
        if market == "commodities":
            return NewsService.fetch_commodities_news()
        return []

    @staticmethod
    def _deduplicate(items: list[dict]) -> list[dict]:
        seen = set()
        unique = []
        for item in items:
            key = re.sub(r"[^a-z0-9]", "", item.get("title", "").lower())[:60]
            if key and key not in seen:
                seen.add(key)
                if "id" not in item:
                    item["id"] = _make_id(item.get("title", ""), item.get("source", ""))
                unique.append(item)
        unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)
        return unique[:50]
