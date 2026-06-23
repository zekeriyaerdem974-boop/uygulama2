# -*- coding: utf-8 -*-
"""
Market Data Source — Strategy Pattern for Real/Dummy Market Data

Architecture:
  MarketDataSource (Abstract Interface)
    ├── DummyMarketSource (DEMO: Random price ticks)
    └── TwelveDataMarketSource (LIVE: Real market data via WebSocket)

Responsibility:
  - Connect to data source (or simulate)
  - Stream price ticks every 1.5s
  - Emit via SocketIO to /ws/market-relay namespace
  - Automatic fallback on connection failure
"""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable

_logger = logging.getLogger("zkr_analiz.market_data_source")


class MarketDataSource(ABC):
    """
    Abstract interface for market data sources
    
    Contract:
    - start_stream() → Begin streaming price ticks
    - stop_stream() → Stop and cleanup
    - on_tick() → Callback when price tick arrives
    """
    
    def __init__(self, symbol: str = "BTCUSDT", on_tick_callback: Optional[Callable] = None):
        """
        Initialize data source
        
        Args:
            symbol: Trading symbol (BTCUSDT, EURUSD, etc)
            on_tick_callback: Function to call on each price tick
                             Called with: {symbol, price, volume, timestamp}
        """
        self.symbol = symbol
        self.on_tick_callback = on_tick_callback
        self.running = False
        self.stream_thread = None
    
    @abstractmethod
    def start_stream(self) -> bool:
        """
        Start streaming price data
        
        Returns:
            True if successful, False if failed
        """
        pass
    
    @abstractmethod
    def stop_stream(self) -> None:
        """Stop streaming and cleanup resources"""
        pass
    
    def emit_tick(self, data: Dict) -> None:
        """
        Internal: Emit a price tick
        
        Args:
            data: {symbol, price, volume, timestamp}
        """
        if self.on_tick_callback:
            try:
                self.on_tick_callback(data)
            except Exception as e:
                _logger.error(f"[{self.__class__.__name__}] Error in tick callback: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# DUMMY MARKET SOURCE — DEMO DATA
# ═══════════════════════════════════════════════════════════════════════════════

class DummyMarketSource(MarketDataSource):
    """
    Dummy market data source for DEMO/BACKTEST
    
    Generates random price ticks every 1.5 seconds
    Simulates live market behavior with realistic price movement
    """
    
    def __init__(self, symbol: str = "BTCUSDT", on_tick_callback: Optional[Callable] = None):
        super().__init__(symbol, on_tick_callback)
        self.price = 64000.0  # Starting price
        self.tick_count = 0
        _logger.info(f"[DummyMarketSource] Initialized for {symbol}")
    
    def start_stream(self) -> bool:
        """Start generating dummy price ticks"""
        if self.running:
            _logger.warning("[DummyMarketSource] Already running")
            return True
        
        self.running = True
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        
        _logger.info("[DummyMarketSource] ✅ Stream started (dummy ticks every 1.5s)")
        return True
    
    def stop_stream(self) -> None:
        """Stop dummy stream"""
        self.running = False
        _logger.info("[DummyMarketSource] Stream stopped")
    
    def _stream_loop(self) -> None:
        """Background thread: Generate dummy ticks"""
        while self.running:
            try:
                # Generate random price movement (-2.0 to +2.0)
                change = random.uniform(-2.0, 2.0)
                self.price = max(self.price + change, 1000)
                
                self.tick_count += 1
                now_ms = int(time.time() * 1000)
                
                # Create tick packet
                tick = {
                    'symbol': self.symbol,
                    'price': round(self.price, 2),
                    'volume': random.uniform(5, 50),
                    'timestamp': now_ms,
                }
                
                # Emit tick
                self.emit_tick(tick)
                _logger.debug(f"[DummyMarketSource] Tick #{self.tick_count}: {self.symbol} ${self.price:.2f}")
                
                time.sleep(1.5)  # Every 1.5 seconds
                
            except Exception as e:
                _logger.error(f"[DummyMarketSource] Stream loop error: {e}")
                time.sleep(1.5)


# ═══════════════════════════════════════════════════════════════════════════════
# TWELVEDATA MARKET SOURCE — LIVE MARKET DATA
# ═══════════════════════════════════════════════════════════════════════════════

class TwelveDataMarketSource(MarketDataSource):
    """
    Live market data source via TwelveData WebSocket API
    
    Connects to: wss://ws.twelvedata.com/v1/quotes/price?apikey=...
    
    API Documentation:
    - Public demo key available
    - Real-time price quotes every 1-2 seconds
    - Fallback: DummyMarketSource on connection failure
    """
    
    # TwelveData WebSocket endpoint
    WS_URL = "wss://ws.twelvedata.com/v1/quotes/price"
    
    def __init__(self, symbol: str = "BTCUSDT", api_key: str = "demo", on_tick_callback: Optional[Callable] = None):
        super().__init__(symbol, on_tick_callback)
        self.api_key = api_key
        self.ws_client = None
        self.last_price = None
        self.normalized_symbol = self._normalize_symbol(symbol)
        self.connection_ready = False  # Flag: subscription successful
        _logger.info(f"[TwelveDataMarketSource] Initialized for {symbol} → {self.normalized_symbol} with API key: {api_key[:10]}...")
    
    def start_stream(self) -> bool:
        """
        Connect to TwelveData WebSocket and start streaming
        
        Returns:
            True if connection successful, False if failed (fallback to dummy)
        """
        if self.running:
            _logger.warning("[TwelveDataMarketSource] Already running")
            return True
        
        try:
            import websocket
            from websocket import create_connection
        except ImportError:
            _logger.error("[TwelveDataMarketSource] websocket-client not installed. Install: pip install websocket-client")
            return False
        
        self.running = True
        self.connection_ready = False  # Flag to track successful subscription
        self.stream_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self.stream_thread.start()
        
        # ⚠️ CRITICAL: Wait up to 3 seconds for subscription confirmation
        # If subscription fails or times out, return False to trigger fallback
        import time
        for i in range(30):  # 30 * 0.1s = 3 seconds max
            if self.connection_ready:
                _logger.info("[TwelveDataMarketSource] ✅ Connection ready - subscribed successfully")
                return True
            if not self.running:  # Thread exited (subscription failed)
                _logger.error("[TwelveDataMarketSource] ❌ Connection failed - subscription rejected")
                return False
            time.sleep(0.1)
        
        # Timeout - assume failure
        _logger.error("[TwelveDataMarketSource] ⏱️ Connection timeout - no subscription confirmation")
        self.running = False
        return False
    
    def stop_stream(self) -> None:
        """Close WebSocket connection"""
        self.running = False
        if self.ws_client:
            try:
                self.ws_client.close()
            except:
                pass
        _logger.info("[TwelveDataMarketSource] Stream stopped")
    
    def _normalize_symbol(self, symbol: str) -> str:
        """
        Convert our symbol format to TwelveData format
        
        TwelveData expects:
        - Crypto: Quote pairs with /USD for stability (e.g., "BTC/USD", "ETH/USD")
        - Forex: Base/Quote pairs (e.g., "EUR/USD", "GBP/USD")
        - Stocks: Ticker symbol (e.g., "AAPL", "GOOGL")
        
        Examples:
            BTCUSDT → BTC/USD (crypto - most stable for free tier)
            BTCUSD → BTC/USD (crypto)
            EURUSD → EUR/USD (forex)
        
        Args:
            symbol: Our internal symbol format (e.g., "BTCUSDT", "EURUSD")
        
        Returns:
            TwelveData format (e.g., "BTC/USD", "EUR/USD")
        """
        if "/" in symbol:
            # Already normalized
            return symbol
        
        # Crypto: BTCUSDT (3+4=7) → BTC/USD (most stable on free tier)
        if symbol.endswith("USDT"):
            base = symbol[:-4]  # Remove USDT → "BTC", "ETH"
            normalized = f"{base}/USD"  # Use USD instead of USDT for free tier stability
            _logger.debug(f"[TwelveDataMarketSource] Normalize: {symbol} → {normalized} (Crypto with USD pair)")
            return normalized
        
        # Crypto: BTCUSD (3+3=6) or similar → BTC/USD
        if symbol.endswith("USD") and len(symbol) == 6:
            base = symbol[:3]  # First 3 letters → "BTC", "EUR", "GBP", etc.
            quote = symbol[3:]  # Last 3 letters → "USD"
            
            # Check if it's forex (EUR, GBP, AUD, etc.) or crypto (BTC, ETH, XRP, etc.)
            forex_bases = ["EUR", "GBP", "AUD", "CAD", "CHF", "CNY", "INR", "JPY", "NZD", "SGD"]
            
            if base in forex_bases:
                # Forex: EUR/USD
                normalized = f"{base}/{quote}"
                _logger.debug(f"[TwelveDataMarketSource] Normalize: {symbol} → {normalized} (Forex pair)")
            else:
                # Crypto: BTC → BTC/USD
                normalized = f"{base}/USD"
                _logger.debug(f"[TwelveDataMarketSource] Normalize: {symbol} → {normalized} (Crypto with USD pair)")
            return normalized
        
        # Forex only: EURUSD (6 chars, base is known forex) → EUR/USD
        if len(symbol) == 6:
            base = symbol[:3]
            quote = symbol[3:]
            normalized = f"{base}/{quote}"
            _logger.debug(f"[TwelveDataMarketSource] Normalize: {symbol} → {normalized} (Pair format)")
            return normalized
        
        # Fallback: return as-is
        _logger.warning(f"[TwelveDataMarketSource] Cannot normalize symbol: {symbol}, using as-is")
        return symbol
    
    def _denormalize_symbol(self, normalized: str) -> str:
        """
        Convert TwelveData format back to our symbol format
        
        Examples:
            BTC/USD → BTCUSDT (for frontend compatibility)
            EUR/USD → EURUSD
            BTC/USDT → BTCUSDT
        
        Args:
            normalized: TwelveData format (e.g., "BTC/USD", "EUR/USD")
        
        Returns:
            Our internal format (e.g., "BTCUSDT", "EURUSD")
        """
        if "/" not in normalized:
            # Already denormalized or stock ticker
            return normalized
        
        parts = normalized.split("/")
        if len(parts) == 2:
            base, quote = parts
            
            # Crypto with USD → Add USDT suffix for frontend standardization
            # BTC/USD → BTCUSDT (our standard crypto format)
            if quote.upper() == "USD":
                denormalized = f"{base}USDT"
                _logger.debug(f"[TwelveDataMarketSource] Denormalize: {normalized} → {denormalized} (Frontend format)")
                return denormalized
            
            # Forex or other pairs → Remove slash
            # EUR/USD → EURUSD
            denormalized = f"{base}{quote}"
            _logger.debug(f"[TwelveDataMarketSource] Denormalize: {normalized} → {denormalized} (Pair format)")
            return denormalized
        
        # Fallback
        return normalized.replace("/", "")
    
    def _stream_loop(self) -> None:
        """Background thread: Connect to TwelveData and stream quotes"""
        import websocket
        import json
        
        try:
            # Build WebSocket URL with API key and symbol
            url = f"{self.WS_URL}?apikey={self.api_key}"
            
            _logger.info(f"[TwelveDataMarketSource] Connecting to {url}...")
            self.ws_client = websocket.create_connection(url, timeout=10)
            
            # Subscribe to NORMALIZED symbol (TwelveData format)
            subscribe_msg = json.dumps({
                "action": "subscribe",
                "params": {"symbols": self.normalized_symbol}
            })
            self.ws_client.send(subscribe_msg)
            _logger.info(f"[TwelveDataMarketSource] ✅ Subscribed to {self.symbol} (normalized as {self.normalized_symbol})")
            
            # Read messages
            while self.running:
                try:
                    msg = self.ws_client.recv()
                    if not msg:
                        _logger.debug("[TwelveDataMarketSource] Empty message received")
                        continue
                    
                    _logger.debug(f"[TwelveDataMarketSource] Raw message: {msg[:200]}")
                    
                    try:
                        data = json.loads(msg)
                    except json.JSONDecodeError:
                        _logger.debug(f"[TwelveDataMarketSource] Non-JSON message: {msg[:100]}")
                        continue
                    
                    # Check for heartbeat
                    if data.get("event") == "subscribe-status" and data.get("status") == "ok":
                        _logger.info(f"[TwelveDataMarketSource] ✅ Subscribe OK: {data['success']}")
                        self.connection_ready = True  # ✅ Subscription successful!
                        continue
                    
                    # Check for subscription failure
                    if data.get("event") == "subscribe-status" and data.get("status") == "error":
                        _logger.error(f"[TwelveDataMarketSource] ❌ Subscription failed: {data['fails']}")
                        self.running = False
                        break
                    
                    # Check for errors
                    if "error" in data:
                        _logger.error(f"[TwelveDataMarketSource] API Error: {data}")
                        break
                    
                    # Extract price tick
                    if "price" in data and "symbol" in data:
                        received_symbol = data["symbol"]  # e.g., "BTC/USDT"
                        price = float(data["price"])
                        
                        # Only emit if symbol matches (both formats: BTC/USDT and our BTCUSDT)
                        if received_symbol == self.normalized_symbol or received_symbol == self.symbol:
                            # Denormalize symbol back to our format for frontend
                            frontend_symbol = self._denormalize_symbol(received_symbol)
                            
                            now_ms = int(time.time() * 1000)
                            
                            tick = {
                                'symbol': frontend_symbol,  # e.g., BTCUSDT (frontend format)
                                'price': round(price, 2),
                                'volume': data.get("volume", 0),  # TwelveData includes volume
                                'timestamp': now_ms,
                            }
                            
                            self.last_price = price
                            self.emit_tick(tick)
                            _logger.info(f"[TwelveDataMarketSource] 🔵 Tick: {received_symbol} → {frontend_symbol} @ ${price}")
                    else:
                        _logger.debug(f"[TwelveDataMarketSource] Unhandled message: {data}")
                
                except json.JSONDecodeError:
                    _logger.debug(f"[TwelveDataMarketSource] Non-JSON message received")
                    continue
                except Exception as e:
                    _logger.error(f"[TwelveDataMarketSource] Message handling error: {e}")
                    break
        
        except websocket.WebSocketConnectionClosedException:
            _logger.warning("[TwelveDataMarketSource] WebSocket connection closed")
        except websocket.WebSocketTimeoutException:
            _logger.error("[TwelveDataMarketSource] WebSocket connection timeout")
        except Exception as e:
            _logger.error(f"[TwelveDataMarketSource] Connection error: {e}")
        
        finally:
            self.running = False
            _logger.warning(f"[TwelveDataMarketSource] Stream ended - connection failed or closed")


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

def create_market_source(
    provider: str = "dummy",
    symbol: str = "BTCUSDT",
    api_key: str = "",
    on_tick_callback: Optional[Callable] = None
) -> MarketDataSource:
    """
    Factory function to create market data source
    
    Args:
        provider: 'dummy' or 'twelvedata'
        symbol: Trading symbol
        api_key: API key for paid providers
        on_tick_callback: Function to call on each tick
    
    Returns:
        MarketDataSource instance
    """
    provider = provider.lower().strip()
    
    if provider == "twelvedata":
        _logger.info(f"[Factory] Creating TwelveDataMarketSource with key {api_key[:10]}...")
        return TwelveDataMarketSource(symbol, api_key, on_tick_callback)
    else:
        _logger.info("[Factory] Creating DummyMarketSource (default)")
        return DummyMarketSource(symbol, on_tick_callback)
