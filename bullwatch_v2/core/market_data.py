from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


@dataclass(frozen=True)
class CacheEntry:
    expires_at: float
    value: Any


class TTLCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any:
        now = time.time()
        with self._lock:
            ent = self._data.get(key)
            if not ent:
                return None
            if ent.expires_at < now:
                self._data.pop(key, None)
                return None
            return ent.value

    def set(self, key: str, value: Any, ttl_s: float) -> None:
        with self._lock:
            self._data[key] = CacheEntry(expires_at=time.time() + ttl_s, value=value)


class MarketDataService:
    """Shared market-data layer for the unified backend.

    Uses Binance public endpoints (fapi by default) + TTL cache + simple backoff.
    """

    # -- FAZ 11: Symbol normalization map --
    # Maps user-friendly short names to actual Binance Futures symbols.
    # e.g. SHIBUSDT -> 1000SHIBUSDT, PEPEUSDT -> 1000PEPEUSDT
    _SYMBOL_ALIASES: dict[str, str] = {}
    _aliases_loaded: bool = False

    def __init__(self) -> None:
        self._session = requests.Session()
        self._cache = TTLCache()
        self._lock = threading.Lock()
        self._last_req_at = 0.0

        self.fapi_base = "https://fapi.binance.com"
        self.alpha_base = "https://www.binance.com"
        self.api_timeout_s = 10
        # naive client-side throttling
        self.min_interval_s = 0.05

        self._alpha_headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ZKR Analiz/1.0",
            "Accept": "application/json, text/plain, */*",
        }

    def _throttle(self) -> None:
        with self._lock:
            now = time.time()
            dt = now - self._last_req_at
            if dt < self.min_interval_s:
                time.sleep(self.min_interval_s - dt)
            self._last_req_at = time.time()

    def request_json(self, path: str, *, params: Optional[Dict[str, Any]] = None, ttl_s: Optional[float] = None) -> Any:
        cache_key = None
        if ttl_s is not None:
            cache_key = f"{path}?{json.dumps(params or {}, sort_keys=True, ensure_ascii=False)}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        url = self.fapi_base + path
        backoff = 0.3
        for attempt in range(5):
            self._throttle()
            try:
                r = self._session.get(url, params=params, timeout=self.api_timeout_s)
                if r.status_code in (418, 429):
                    time.sleep(backoff + random.random() * 0.2)
                    backoff = min(backoff * 2, 3.0)
                    continue
                r.raise_for_status()
                data = r.json()
                if cache_key is not None:
                    self._cache.set(cache_key, data, ttl_s=ttl_s)
                return data
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(backoff + random.random() * 0.2)
                backoff = min(backoff * 2, 3.0)

        raise RuntimeError("request_json failed")

    def request_alpha_json(self, path: str, *, params: Optional[Dict[str, Any]] = None, ttl_s: Optional[float] = None) -> Any:
        cache_key = None
        if ttl_s is not None:
            cache_key = f"alpha:{path}?{json.dumps(params or {}, sort_keys=True, ensure_ascii=False)}"
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        url = self.alpha_base + path
        backoff = 0.3
        for attempt in range(5):
            self._throttle()
            try:
                r = self._session.get(url, params=params, timeout=self.api_timeout_s, headers=self._alpha_headers)
                if r.status_code in (418, 429):
                    time.sleep(backoff + random.random() * 0.2)
                    backoff = min(backoff * 2, 3.0)
                    continue
                r.raise_for_status()
                data = r.json()
                if cache_key is not None:
                    self._cache.set(cache_key, data, ttl_s=ttl_s)
                return data
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(backoff + random.random() * 0.2)
                backoff = min(backoff * 2, 3.0)

        raise RuntimeError("request_alpha_json failed")

    # ---- Symbol list & normalization ----

    def get_symbols(self, *, ttl_s: float = 60.0) -> List[str]:
        info = self.request_json("/fapi/v1/exchangeInfo", ttl_s=ttl_s)
        symbols = []
        for s in info.get("symbols", []):
            if s.get("contractType") not in (None, "PERPETUAL"):
                continue
            if s.get("status") != "TRADING":
                continue
            sym = s.get("symbol")
            if sym and sym.endswith("USDT"):
                symbols.append(sym)
        self._build_aliases(symbols)
        return symbols

    def _build_aliases(self, symbols: List[str]) -> None:
        """Build normalization map from short coin names to actual Futures symbols.

        Handles multiplier prefix coins:
          Numeric:  SHIBUSDT -> 1000SHIBUSDT, PEPEUSDT -> 1000PEPEUSDT
          1M:       BABYDOGEUSDT -> 1MBABYDOGEUSDT
        Also maps bare names: BTC -> BTCUSDT.
        """
        sym_set = set(symbols)
        aliases: dict[str, str] = {}

        # Numeric multiplier prefixes (1000, 10000, etc.)
        for sym in symbols:
            for pfx in ("1000000", "100000", "10000", "1000"):
                if sym.startswith(pfx) and sym.endswith("USDT"):
                    base = sym[len(pfx):-4]
                    short = base + "USDT"
                    if short not in sym_set and short not in aliases:
                        aliases[short] = sym

        # 1M prefix (1,000,000 multiplier shorthand used by Binance)
        for sym in symbols:
            if sym.startswith("1M") and sym.endswith("USDT"):
                base = sym[2:-4]  # strip "1M" and "USDT"
                short = base + "USDT"
                if short not in sym_set and short not in aliases:
                    aliases[short] = sym

        # Bare-name aliases (without USDT suffix)
        for sym in symbols:
            if sym.endswith("USDT"):
                bare = sym[:-4]
                if bare not in aliases:
                    aliases[bare] = sym

        MarketDataService._SYMBOL_ALIASES = aliases
        MarketDataService._aliases_loaded = True

    def normalize_symbol(self, symbol: str) -> Tuple[str, Optional[str]]:
        """Normalize a user symbol to the actual Futures symbol.

        Returns:
            (normalized_symbol, original_if_changed_or_None)
        Examples:
            normalize_symbol("SHIBUSDT")  -> ("1000SHIBUSDT", "SHIBUSDT")
            normalize_symbol("BTCUSDT")   -> ("BTCUSDT", None)
            normalize_symbol("BTC")       -> ("BTCUSDT", "BTC")
        """
        sym = symbol.strip().upper().replace("_", "")

        # Ensure aliases are loaded
        if not MarketDataService._aliases_loaded:
            try:
                self.get_symbols(ttl_s=120.0)
            except Exception:
                pass

        # Check alias map
        mapped = MarketDataService._SYMBOL_ALIASES.get(sym)
        if mapped:
            return mapped, sym

        # If it doesn't end with USDT, try adding it
        if not sym.endswith("USDT"):
            with_usdt = sym + "USDT"
            mapped2 = MarketDataService._SYMBOL_ALIASES.get(with_usdt)
            if mapped2:
                return mapped2, sym
            return with_usdt, sym

        # Return as-is
        return sym, None

    # ---- Ticker ----

    def get_ticker_24h(self, *, ttl_s: float = 3.0) -> List[Dict[str, Any]]:
        return self.request_json("/fapi/v1/ticker/24hr", ttl_s=ttl_s)

    def get_ticker_single(self, symbol: str, *, ttl_s: float = 2.0) -> Dict[str, Any]:
        """24h ticker for a single symbol (lighter than full ticker list)."""
        symbol = symbol.upper()
        data = self.request_json(
            "/fapi/v1/ticker/24hr",
            params={"symbol": symbol},
            ttl_s=ttl_s,
        )
        return data

    # ---- Klines ----

    def get_klines(self, symbol: str, interval: str, limit: int, *, ttl_s: float = 2.0) -> List[Dict[str, Any]]:
        symbol = symbol.upper()
        limit = max(1, min(int(limit), 1500))
        raw = self.request_json(
            "/fapi/v1/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            ttl_s=ttl_s,
        )
        out = []
        for k in raw:
            out.append(
                {
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": int(k[6]),
                }
            )
        return out

    # ---- Orderflow / Liquidation helpers ----

    def get_open_interest(self, symbol: str, *, ttl_s: float = 5.0) -> Dict[str, Any]:
        """Current aggregate open interest for a futures symbol."""
        symbol = symbol.upper()
        return self.request_json(
            "/fapi/v1/openInterest",
            params={"symbol": symbol},
            ttl_s=ttl_s,
        )

    def get_funding_rate(self, symbol: str, *, limit: int = 1, ttl_s: float = 10.0) -> List[Dict[str, Any]]:
        """Latest funding rate(s) for a futures symbol."""
        symbol = symbol.upper()
        return self.request_json(
            "/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
            ttl_s=ttl_s,
        )

    def get_depth(self, symbol: str, *, limit: int = 20, ttl_s: float = 2.0) -> Dict[str, Any]:
        """Order book depth snapshot (bids + asks)."""
        symbol = symbol.upper()
        limit = max(5, min(int(limit), 1000))
        return self.request_json(
            "/fapi/v1/depth",
            params={"symbol": symbol, "limit": limit},
            ttl_s=ttl_s,
        )

    def get_long_short_ratio(self, symbol: str, period: str = "5m", *, limit: int = 1, ttl_s: float = 30.0) -> List[Dict[str, Any]]:
        """Top trader long/short ratio (accounts)."""
        symbol = symbol.upper()
        return self.request_json(
            "/futures/data/topLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
            ttl_s=ttl_s,
        )

    def get_taker_volume(self, symbol: str, period: str = "5m", *, limit: int = 1, ttl_s: float = 30.0) -> List[Dict[str, Any]]:
        """Taker buy/sell volume ratio."""
        symbol = symbol.upper()
        return self.request_json(
            "/futures/data/takerlongshortRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
            ttl_s=ttl_s,
        )

    # ---- Alpha endpoints ----

    def get_alpha_symbols(self, *, ttl_s: float = 60.0) -> List[str]:
        pairs = self.get_alpha_pairs(ttl_s=ttl_s)
        return [p["pair"] for p in pairs]

    def get_alpha_pairs(self, *, ttl_s: float = 60.0) -> List[Dict[str, str]]:
        """Return Alpha market symbols from Binance Alpha public endpoints."""
        token_map = self._get_alpha_token_map(ttl_s=ttl_s)
        j = self.request_alpha_json(
            "/bapi/defi/v1/public/alpha-trade/get-exchange-info",
            ttl_s=ttl_s,
        )
        if str(j.get("code")) != "000000":
            raise RuntimeError(f"Alpha exchange info error: {j}")

        out: List[Dict[str, str]] = []
        for s in j.get("data", {}).get("symbols", []) or []:
            if s.get("quoteAsset") != "USDT":
                continue
            pair = s.get("symbol")
            base_id = s.get("baseAsset")
            if not pair or not base_id:
                continue
            meta = token_map.get(base_id, {})
            base_symbol = meta.get("symbol") or base_id
            name = meta.get("name") or base_symbol
            out.append(
                {
                    "pair": pair,
                    "base_id": base_id,
                    "base_symbol": base_symbol,
                    "name": name,
                    "readable": f"{base_symbol}/USDT",
                }
            )

        out.sort(key=lambda x: x.get("readable") or "")
        return out

    def _get_alpha_token_map(self, *, ttl_s: float = 3600.0) -> Dict[str, Dict[str, str]]:
        """Map Alpha base asset ids to human-readable symbol/name."""
        cache_key = "alpha:token_map"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        j = self.request_alpha_json(
            "/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list",
            ttl_s=ttl_s,
        )
        if str(j.get("code")) != "000000":
            raise RuntimeError(f"Alpha token list error: {j}")

        mp: Dict[str, Dict[str, str]] = {}
        for t in j.get("data", []) or []:
            num = t.get("number")
            if not num:
                continue
            key = f"ALPHA_{num}"
            mp[key] = {
                "symbol": t.get("symbol") or key,
                "name": t.get("name") or (t.get("symbol") or key),
            }

        self._cache.set(cache_key, mp, ttl_s=ttl_s)
        return mp

    def get_alpha_klines(self, pair: str, interval: str, limit: int, *, ttl_s: float = 2.0) -> List[Dict[str, Any]]:
        """Fetch Alpha klines from Binance Alpha endpoint (not fapi)."""
        pair = pair.upper()
        limit = max(1, min(int(limit), 1500))
        j = self.request_alpha_json(
            "/bapi/defi/v1/public/alpha-trade/klines",
            params={"symbol": pair, "interval": interval, "limit": limit},
            ttl_s=ttl_s,
        )
        if str(j.get("code")) != "000000":
            raise RuntimeError(f"Alpha klines error: {j}")
        data = j.get("data", []) or []
        out: List[Dict[str, Any]] = []
        for k in data:
            out.append(
                {
                    "open_time": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "close_time": int(k[6]),
                }
            )
        return out
