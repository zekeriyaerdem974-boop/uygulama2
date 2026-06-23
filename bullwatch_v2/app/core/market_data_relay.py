# -*- coding: utf-8 -*-
"""
MarketDataRelay — SaaS Platform Market Data Distribution Engine

Architecture (Broadcaster Pattern):
  ┌──────────────────────────────────────────────────────────┐
  │  Kiralık API Sağlayıcı (TwelveData, Polygon.io, vb)      │
  │  • Faturası tek bir bağlantı ile optimize                │
  │  • Unlimited market data feed                            │
  └─────────┬──────────────────────────────────────────────┘
            │
            ↓
  ┌──────────────────────────────────────────────────────────┐
  │  MarketDataRelay → Single Data Ingestion Point           │
  │  • Fetch klines, tickers, quote data                     │
  │  • Parse ve normalize                                    │
  │  • Redis pub/sub broadcast                              │
  │  • In-memory cache per symbol                           │
  └─────────┬──────────────────────────────────────────────┘
            │
            ├──→ Redis Channel: market:BTCUSDT:1m
            ├──→ Redis Channel: market:ETHUSDT:4h
            └──→ Redis Channel: market_tickers_broadcast
                    │
                    ├─→ Flask-SocketIO: /ws/market-relay
                    ├─→ Flask-SocketIO: /ws/klines
                    └─→ REST API: /api/market-data/...

Veri Akışı:
  TwelveData → Relay → Redis → WebSocket → 1000s Browsers
  (1 API call)   (pool)  (fanout)  (multicast)

Maliyet Optimizasyonu:
  - API: 1 subscription/symbol
  - Network: Redis multicast (1→∞)
  - Storage: In-memory circular buffers
  - Broadcast: Batch updates per symbol
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple

import redis
from flask import current_app

# Strategy pattern for market data sources
from app.core.market_data_source import create_market_source, MarketDataSource

_logger = logging.getLogger("zkr_analiz.market_data_relay")

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

class RelayConfig:
    """Market Data Relay configuration"""
    # Paid API limits (example: TwelveData free tier)
    MAX_SYMBOLS_PER_SUBSCRIPTION = 100
    MAX_API_CALLS_PER_MINUTE = 800
    
    # Internal broadcast limits
    MAX_CANDLE_HISTORY = 500  # Store last 500 candles per symbol/interval
    TICKER_BROADCAST_INTERVAL = 1.5  # seconds
    CANDLE_BATCH_SIZE = 10  # Emit X candles per tick
    
    # Redis
    REDIS_CHANNEL_PREFIX = "market:"  # market:BTCUSDT:1m, market:ETHUSDT:4h, etc
    REDIS_TICKER_CHANNEL = "market_tickers_broadcast"
    REDIS_CONTROL_CHANNEL = "market_relay_control"

config = RelayConfig()

# ══════════════════════════════════════════════════════════════════════════════
# CORE DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

class Candle:
    """OHLCV candle"""
    def __init__(self, time: int, o: float, h: float, l: float, c: float, v: float):
        self.time = time
        self.o = o  # open
        self.h = h  # high
        self.l = l  # low
        self.c = c  # close
        self.v = v  # volume
    
    def to_dict(self):
        return {
            'time': self.time,
            'o': self.o,
            'h': self.h,
            'l': self.l,
            'c': self.c,
            'v': self.v,
        }

class TickerData:
    """Ticker snapshot"""
    def __init__(self, symbol: str, last: float, bid: float, ask: float, change_pct: float, volume: float):
        self.symbol = symbol
        self.last = last
        self.bid = bid
        self.ask = ask
        self.change_pct = change_pct
        self.volume = volume
        self.timestamp = time.time()
    
    def to_dict(self):
        return {
            's': self.symbol,
            'last': self.last,
            'bid': self.bid,
            'ask': self.ask,
            'change_pct': self.change_pct,
            'volume': self.volume,
            'ts': self.timestamp,
        }

# ══════════════════════════════════════════════════════════════════════════════
# PAID API ADAPTER (Mock TwelveData Simulation)
# ══════════════════════════════════════════════════════════════════════════════

class PaidAPIAdapter:
    """
    Adapter to kiralık API (TwelveData, Polygon.io, etc)
    
    For MVP: Mock implementation
    For Prod: Replace with actual API client
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or "mock_key"
        self.rate_limiter = RateLimiter(config.MAX_API_CALLS_PER_MINUTE)
        self.request_count = 0
        _logger.info("[PaidAPI] Adapter initialized (mock mode)")
    
    def fetch_klines(self, symbol: str, interval: str, limit: int = 100) -> List[Dict]:
        """
        Fetch historical candles from paid API
        
        symbol: BTCUSDT, EURUSD, AAPL, etc
        interval: 1m, 5m, 15m, 1h, 4h, 1d, 1w
        limit: Max 300 candles
        
        Returns: [{time, o, h, l, c, v}, ...]
        """
        # Rate limit check
        if not self.rate_limiter.allow():
            _logger.warning("[PaidAPI] Rate limit exceeded, returning cached")
            return []
        
        # Mock implementation
        _logger.info(f"[PaidAPI] Fetching klines: {symbol} {interval} ({limit} candles)")
        candles = self._generate_mock_candles(symbol, interval, limit)
        self.request_count += 1
        return candles
    
    def fetch_quote(self, symbol: str) -> Optional[Dict]:
        """
        Fetch real-time quote from paid API
        
        Returns: {last, bid, ask, change_pct, volume}
        """
        if not self.rate_limiter.allow():
            return None
        
        # Mock implementation
        _logger.debug(f"[PaidAPI] Fetching quote: {symbol}")
        return {
            'last': 64000 + (hash(symbol) % 1000),
            'bid': 63990 + (hash(symbol) % 1000),
            'ask': 64010 + (hash(symbol) % 1000),
            'change_pct': (hash(symbol) % 500 - 250) / 100,  # -2.5% to +2.5%
            'volume': hash(symbol) % 10000000,
        }
    
    def _generate_mock_candles(self, symbol: str, interval: str, count: int) -> List[Dict]:
        """Generate mock candle data for demo"""
        candles = []
        now = int(time.time())
        interval_seconds = {
            '1m': 60, '5m': 300, '15m': 900, '1h': 3600,
            '4h': 14400, '1d': 86400, '1w': 604800
        }.get(interval, 3600)
        
        price = 64000
        for i in range(count - 1, -1, -1):
            t = now - (i * interval_seconds)
            change = (hash(f"{symbol}{i}") % 200 - 100) / 100  # -1% to +1% per candle
            o = price
            c = price * (1 + change / 100)
            h = max(o, c) + (hash(f"{symbol}{i}h") % 50) / 100
            l = min(o, c) - (hash(f"{symbol}{i}l") % 50) / 100
            v = hash(f"{symbol}{i}v") % 5000000
            
            candles.append({
                'time': t,
                'o': round(o, 2),
                'h': round(h, 2),
                'l': round(l, 2),
                'c': round(c, 2),
                'v': v,
            })
            
            price = c
        
        return candles

class RateLimiter:
    """Simple rate limiter"""
    def __init__(self, max_per_minute: int):
        self.max_per_minute = max_per_minute
        self.timestamps = deque()
    
    def allow(self) -> bool:
        now = time.time()
        # Remove old entries (>60s)
        while self.timestamps and self.timestamps[0] < now - 60:
            self.timestamps.popleft()
        # Check limit
        if len(self.timestamps) < self.max_per_minute:
            self.timestamps.append(now)
            return True
        return False

# ══════════════════════════════════════════════════════════════════════════════
# MARKET DATA RELAY — CORE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class MarketDataRelay:
    """
    Central market data distribution engine
    
    Responsibilities:
    1. Fetch data from kiralık API (TwelveData, etc)
    2. Cache and normalize data
    3. Broadcast via Redis pub/sub
    4. Emit to connected clients via WebSocket
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.api_adapter = PaidAPIAdapter()
        self.redis_client = None
        self.pubsub = None
        
        # Per-symbol caches
        self.candle_cache: Dict[str, Dict[str, deque]] = {}  # symbol -> {interval -> deque(Candle)}
        self.ticker_cache: Dict[str, TickerData] = {}  # symbol -> TickerData
        
        # Subscription tracking
        self.active_subscriptions: set = set()  # set of (symbol, interval) tuples
        
        # Threads
        self.ingestion_thread = None
        self.broadcast_thread = None
        self.market_source: Optional[MarketDataSource] = None  # Strategy pattern
        self.running = False
        
        _logger.info("[Relay] MarketDataRelay initialized (singleton)")
    
    def start(self):
        """Start relay engine with strategy pattern"""
        if self.running:
            _logger.warning("[Relay] Already running")
            return
        
        # Try to connect to Redis, but don't block if app context is unavailable
        try:
            from flask import current_app
            self.redis_client = redis.Redis(
                host=current_app.config.get('REDIS_HOST', 'localhost'),
                port=current_app.config.get('REDIS_PORT', 6379),
                db=0,
                decode_responses=True
            )
            self.redis_client.ping()
            _logger.info("[Relay] Redis connected")
        except RuntimeError as e:
            # No app context - this is OK for demo mode
            _logger.warning(f"[Relay] Redis skipped (no app context): {e}")
            self.redis_client = None  # Demo mode without Redis
        except Exception as e:
            _logger.error(f"[Relay] Redis connection failed: {e}")
            self.redis_client = None  # Demo mode without Redis
        
        self.running = True
        
        # Start background threads
        self.ingestion_thread = threading.Thread(target=self._ingestion_loop, daemon=True)
        self.ingestion_thread.start()
        
        self.broadcast_thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.broadcast_thread.start()
        
        # Initialize market data source (Strategy pattern)
        self._init_market_source()
        
        _logger.info("[Relay] MarketDataRelay started with market source")
    
    def stop(self):
        """Stop relay engine and cleanup market source"""
        self.running = False
        if self.market_source:
            self.market_source.stop_stream()
        _logger.info("[Relay] MarketDataRelay stopped")
    
    # ──────────────────────────────────────────────────────────────────────────
    # STRATEGY PATTERN: Market Data Source Initialization
    # ──────────────────────────────────────────────────────────────────────────
    
    def _init_market_source(self) -> None:
        """
        Initialize market data source with fallback mechanism
        
        Flow:
        1. Read MARKET_DATA_PROVIDER from .env (default: 'dummy')
        2. Try to create and start the configured provider
        3. If provider fails, fallback to dummy
        """
        provider = os.getenv("MARKET_DATA_PROVIDER", "dummy").lower().strip()
        api_key = os.getenv("TWELVEDATA_API_KEY", "").strip()
        symbol = "BTCUSDT"  # Default symbol
        
        _logger.info(f"[Relay] Initializing market source: provider={provider}")
        
        # Try the configured provider first
        if provider == "twelvedata":
            _logger.info(f"[Relay] Attempting TwelveData connection with API key: {api_key[:10] if api_key else 'NONE'}...")
            self.market_source = create_market_source(
                provider="twelvedata",
                symbol=symbol,
                api_key=api_key or "demo",
                on_tick_callback=self._on_market_tick
            )
            
            if not self.market_source.start_stream():
                # TwelveData failed - fallback to dummy
                _logger.error("[Relay] TwelveData failed to connect. Falling back to DummyMarketSource...")
                self.market_source = create_market_source(
                    provider="dummy",
                    symbol=symbol,
                    on_tick_callback=self._on_market_tick
                )
                self.market_source.start_stream()
        else:
            # Default to dummy
            _logger.info("[Relay] Using DummyMarketSource (default)")
            self.market_source = create_market_source(
                provider="dummy",
                symbol=symbol,
                on_tick_callback=self._on_market_tick
            )
            self.market_source.start_stream()
        
        _logger.info(f"[Relay] Market source started: {self.market_source.__class__.__name__}")
    
    def _on_market_tick(self, tick: Dict) -> None:
        """
        Callback when market source emits a price tick
        
        Receives: {symbol, price, volume, timestamp}
        Emits via SocketIO to all connected clients on /ws/market-relay
        """
        try:
            # Get socketio instance
            socketio = None
            try:
                from legacy_monolith import socketio as socketio_obj
                socketio = socketio_obj
            except:
                pass
            
            if socketio is None:
                try:
                    from app.extensions import socketio as socketio_obj
                    socketio = socketio_obj
                except Exception as e:
                    _logger.warning(f"[Relay] Cannot import socketio: {e}")
                    return
            
            # Create event packet (IMPORTANT: Keep 'dummy_heartbeat' for frontend compatibility)
            event_data = {
                'type': 'dummy_heartbeat',  # Frontend expects this name
                'symbol': tick['symbol'],
                'price': tick['price'],
                'volume': tick.get('volume', 0),
                'timestamp': tick['timestamp'],
            }
            
            # Emit to all connected clients on /ws/market-relay
            socketio.emit('dummy_heartbeat', event_data, namespace='/ws/market-relay')
            _logger.debug(f"[Relay] 💓 Emitted tick: {tick['symbol']} ${tick['price']}")
            
        except Exception as e:
            _logger.error(f"[Relay] Error emitting tick: {e}", exc_info=True)
    
    def subscribe(self, symbol: str, intervals: List[str] = None):
        """
        Subscribe to symbol candle updates
        
        symbol: BTCUSDT, EURUSD, AAPL, etc
        intervals: ['1m', '4h', '1d'] or None for all
        """
        if intervals is None:
            intervals = ['1m', '5m', '15m', '1h', '4h', '1d', '1w']
        
        for interval in intervals:
            key = (symbol, interval)
            if key not in self.active_subscriptions:
                self.active_subscriptions.add(key)
                _logger.info(f"[Relay] Subscribed: {symbol} {interval}")
                
                # Initialize cache
                if symbol not in self.candle_cache:
                    self.candle_cache[symbol] = {}
                if interval not in self.candle_cache[symbol]:
                    self.candle_cache[symbol][interval] = deque(maxlen=config.MAX_CANDLE_HISTORY)
    
    def unsubscribe(self, symbol: str, interval: str):
        """Unsubscribe from symbol candle updates"""
        key = (symbol, interval)
        self.active_subscriptions.discard(key)
        _logger.info(f"[Relay] Unsubscribed: {symbol} {interval}")
    
    def _ingestion_loop(self):
        """Background thread: Fetch data from API and cache"""
        while self.running:
            try:
                for symbol, interval in list(self.active_subscriptions):
                    # Fetch from API
                    candles_raw = self.api_adapter.fetch_klines(symbol, interval, limit=50)
                    
                    if candles_raw:
                        # Parse and cache
                        candles = [Candle(**c) for c in candles_raw]
                        self.candle_cache[symbol][interval].extend(candles)
                        
                        # Broadcast to Redis
                        channel = f"{config.REDIS_CHANNEL_PREFIX}{symbol}:{interval}"
                        msg = {
                            'type': 'kline_batch',
                            'symbol': symbol,
                            'interval': interval,
                            'candles': [c.to_dict() for c in candles[-config.CANDLE_BATCH_SIZE:]],
                            'ts': time.time(),
                        }
                        self.redis_client.publish(channel, json.dumps(msg))
                
                # Fetch tickers
                for symbol in set(s for s, _ in self.active_subscriptions):
                    quote = self.api_adapter.fetch_quote(symbol)
                    if quote:
                        self.ticker_cache[symbol] = TickerData(symbol, **quote)
                
                # Broadcast tickers every N seconds
                if self.ticker_cache:
                    msg = {
                        'type': 'tickers_batch',
                        'tickers': [t.to_dict() for t in self.ticker_cache.values()],
                        'ts': time.time(),
                    }
                    self.redis_client.publish(config.REDIS_TICKER_CHANNEL, json.dumps(msg))
                
                time.sleep(2)  # API poll interval
            
            except Exception as e:
                _logger.error(f"[Relay] Ingestion loop error: {e}")
                time.sleep(5)
    
    def _broadcast_loop(self):
        """Background thread: Listen to Redis and relay (WebSocket handled separately)"""
        if not self.redis_client:
            return
        
        try:
            pubsub = self.redis_client.pubsub()
            pubsub.psubscribe(f"{config.REDIS_CHANNEL_PREFIX}*", config.REDIS_TICKER_CHANNEL)
            _logger.info("[Relay] Broadcast listener subscribed to Redis")
            
            for message in pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'pmessage':
                    # Kline message (just log, WebSocket handler emits to clients)
                    try:
                        data = json.loads(message['data'])
                        _logger.debug(f"[Relay] Broadcast: kline {data.get('symbol')} {data.get('interval')}")
                    except Exception as e:
                        _logger.error(f"[Relay] Broadcast error: {e}")
                
                elif message['type'] == 'message' and message['channel'] == config.REDIS_TICKER_CHANNEL:
                    # Ticker message (just log, WebSocket handler emits to clients)
                    try:
                        data = json.loads(message['data'])
                        _logger.debug(f"[Relay] Broadcast: {len(data.get('tickers', []))} tickers")
                    except Exception as e:
                        _logger.error(f"[Relay] Ticker broadcast error: {e}")
        
        except Exception as e:
            _logger.error(f"[Relay] Broadcast loop error: {e}")
    
    
    def get_cached_candles(self, symbol: str, interval: str) -> List[Dict]:
        """Get cached candles for symbol/interval"""
        if symbol not in self.candle_cache or interval not in self.candle_cache[symbol]:
            return []
        return [c.to_dict() for c in self.candle_cache[symbol][interval]]
    
    def get_cached_ticker(self, symbol: str) -> Optional[Dict]:
        """Get cached ticker for symbol"""
        ticker = self.ticker_cache.get(symbol)
        return ticker.to_dict() if ticker else None

# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ══════════════════════════════════════════════════════════════════════════════

def get_relay() -> MarketDataRelay:
    """Get or create singleton relay instance"""
    return MarketDataRelay()

def start_relay():
    """Start the relay engine (called from app startup)"""
    relay = get_relay()
    relay.start()
    _logger.info("[Relay] Market Data Relay engine started")

def stop_relay():
    """Stop the relay engine (called on app shutdown)"""
    relay = get_relay()
    relay.stop()
    _logger.info("[Relay] Market Data Relay engine stopped")
