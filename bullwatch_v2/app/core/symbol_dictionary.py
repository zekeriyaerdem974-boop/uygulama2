"""
Symbol Dictionary - Central Rosetta Stone for Multi-Source Symbol Normalization

Maps internal UI symbols to provider-specific formats:
- UI Format (Frontend): BTCUSDT, ETHUSDT, THYAO, AAPL, etc.
- Yahoo Finance: BTC-USD, ETH-USD, THYAO.IS, AAPL, etc.
- TwelveData: BTC/USD, ETH/USD, None (not available), AAPL, etc.

This is THE single source of truth for all symbol dialect conversions.
"""

SYMBOL_MAP = {
    # ═══ CRYPTO (Binance pairs) ═══
    "BTCUSDT": {
        "yahoo": "BTC-USD",
        "twelvedata": "BTC/USD",
        "type": "crypto",
        "display_name": "Bitcoin"
    },
    "ETHUSDT": {
        "yahoo": "ETH-USD",
        "twelvedata": "ETH/USD",
        "type": "crypto",
        "display_name": "Ethereum"
    },
    "SOLUSDT": {
        "yahoo": "SOL-USD",
        "twelvedata": "SOL/USD",
        "type": "crypto",
        "display_name": "Solana"
    },
    "BNBUSDT": {
        "yahoo": "BNB-USD",
        "twelvedata": "BNB/USD",
        "type": "crypto",
        "display_name": "Binance Coin"
    },
    "XRPUSDT": {
        "yahoo": "XRP-USD",
        "twelvedata": "XRP/USD",
        "type": "crypto",
        "display_name": "Ripple"
    },
    "AVAXUSDT": {
        "yahoo": "AVAX-USD",
        "twelvedata": "AVAX/USD",
        "type": "crypto",
        "display_name": "Avalanche"
    },
    "DOGEUSDT": {
        "yahoo": "DOGE-USD",
        "twelvedata": "DOGE/USD",
        "type": "crypto",
        "display_name": "Dogecoin"
    },
    "ADAUSDT": {
        "yahoo": "ADA-USD",
        "twelvedata": "ADA/USD",
        "type": "crypto",
        "display_name": "Cardano"
    },

    # ═══ BIST (Turkish Stocks) ═══
    "XU100": {
        "yahoo": "XU100.IS",
        "twelvedata": None,  # Not available in TwelveData - use DummyMarketSource
        "type": "bist",
        "display_name": "BIST 100"
    },
    "THYAO": {
        "yahoo": "THYAO.IS",
        "twelvedata": None,  # Not available - use DummyMarketSource
        "type": "bist",
        "display_name": "Turkish Airlines"
    },
    "GARAN": {
        "yahoo": "GARAN.IS",
        "twelvedata": None,
        "type": "bist",
        "display_name": "Garanti Bank"
    },
    "ASELS": {
        "yahoo": "ASELS.IS",
        "twelvedata": None,
        "type": "bist",
        "display_name": "Aselsan"
    },
    "SISE": {
        "yahoo": "SISE.IS",
        "twelvedata": None,
        "type": "bist",
        "display_name": "Şişecam"
    },

    # ═══ US STOCKS (NASDAQ/NYSE) ═══
    "AAPL": {
        "yahoo": "AAPL",
        "twelvedata": "AAPL",
        "type": "stock",
        "display_name": "Apple Inc."
    },
    "MSFT": {
        "yahoo": "MSFT",
        "twelvedata": "MSFT",
        "type": "stock",
        "display_name": "Microsoft Corp."
    },
    "GOOGL": {
        "yahoo": "GOOGL",
        "twelvedata": "GOOGL",
        "type": "stock",
        "display_name": "Alphabet Inc."
    },
    "NVDA": {
        "yahoo": "NVDA",
        "twelvedata": "NVDA",
        "type": "stock",
        "display_name": "NVIDIA Corp."
    },
    "TSLA": {
        "yahoo": "TSLA",
        "twelvedata": "TSLA",
        "type": "stock",
        "display_name": "Tesla Inc."
    },
    "META": {
        "yahoo": "META",
        "twelvedata": "META",
        "type": "stock",
        "display_name": "Meta Platforms"
    },

    # ═══ FOREX ═══
    "EURUSD": {
        "yahoo": "EURUSD=X",
        "twelvedata": "EUR/USD",
        "type": "forex",
        "display_name": "EUR/USD"
    },
    "GBPUSD": {
        "yahoo": "GBPUSD=X",
        "twelvedata": "GBP/USD",
        "type": "forex",
        "display_name": "GBP/USD"
    },
    "USDJPY": {
        "yahoo": "JPY=X",
        "twelvedata": "USD/JPY",
        "type": "forex",
        "display_name": "USD/JPY"
    },
    "USDTRY": {
        "yahoo": "USDTRY=X",
        "twelvedata": "USD/TRY",
        "type": "forex",
        "display_name": "USD/TRY"
    },

    # ═══ COMMODITIES ═══
    "GOLD": {
        "yahoo": "GC=F",
        "twelvedata": "XAU/USD",
        "type": "commodity",
        "display_name": "Gold"
    },
    "SILVER": {
        "yahoo": "SI=F",
        "twelvedata": "XAG/USD",
        "type": "commodity",
        "display_name": "Silver"
    },
    "CRUDE_OIL": {
        "yahoo": "CL=F",
        "twelvedata": "CRUDE_OIL",
        "type": "commodity",
        "display_name": "Crude Oil WTI"
    },

    # ═══ INDICES ═══
    "SPY": {
        "yahoo": "^GSPC",
        "twelvedata": "SPY",
        "type": "index",
        "display_name": "S&P 500"
    },
    "DXY": {
        "yahoo": "DX=F",
        "twelvedata": None,
        "type": "index",
        "display_name": "US Dollar Index"
    },
}


def get_yahoo_symbol(ui_symbol: str) -> str:
    """
    Convert UI symbol to Yahoo Finance format.
    
    Args:
        ui_symbol: Frontend symbol (e.g., "BTCUSDT", "THYAO", "AAPL")
    
    Returns:
        Yahoo-formatted symbol (e.g., "BTC-USD", "THYAO.IS", "AAPL")
    
    Raises:
        KeyError: Symbol not found in dictionary
    """
    if ui_symbol not in SYMBOL_MAP:
        raise KeyError(f"Symbol '{ui_symbol}' not found in SYMBOL_MAP")
    
    return SYMBOL_MAP[ui_symbol]["yahoo"]


def get_twelvedata_symbol(ui_symbol: str) -> str:
    """
    Convert UI symbol to TwelveData format.
    
    Args:
        ui_symbol: Frontend symbol (e.g., "BTCUSDT", "THYAO", "AAPL")
    
    Returns:
        TwelveData-formatted symbol (e.g., "BTC/USD"), or None if not supported
    """
    if ui_symbol not in SYMBOL_MAP:
        raise KeyError(f"Symbol '{ui_symbol}' not found in SYMBOL_MAP")
    
    return SYMBOL_MAP[ui_symbol]["twelvedata"]


def is_supported_by_twelvedata(ui_symbol: str) -> bool:
    """Check if symbol is available in TwelveData free tier."""
    if ui_symbol not in SYMBOL_MAP:
        return False
    return SYMBOL_MAP[ui_symbol]["twelvedata"] is not None


def get_symbol_type(ui_symbol: str) -> str:
    """Get asset type (crypto, stock, forex, commodity, etc.)"""
    if ui_symbol not in SYMBOL_MAP:
        raise KeyError(f"Symbol '{ui_symbol}' not found in SYMBOL_MAP")
    
    return SYMBOL_MAP[ui_symbol]["type"]


def get_display_name(ui_symbol: str) -> str:
    """Get human-readable display name."""
    if ui_symbol not in SYMBOL_MAP:
        return ui_symbol
    
    return SYMBOL_MAP[ui_symbol].get("display_name", ui_symbol)


def normalize_ui_symbol(raw_input: str) -> str:
    """
    Normalize frontend symbol format (with prefix) to internal format.
    
    Examples:
        "BINANCE:BTCUSDT" -> "BTCUSDT"
        "BIST:THYAO" -> "THYAO"
        "NASDAQ:AAPL" -> "AAPL"
        "BTCUSDT" -> "BTCUSDT"  (already normalized)
    
    Args:
        raw_input: Symbol potentially with exchange prefix (e.g., "BINANCE:BTCUSDT")
    
    Returns:
        Normalized symbol without prefix (e.g., "BTCUSDT")
    """
    if ":" in raw_input:
        # Remove exchange prefix
        return raw_input.split(":", 1)[1]
    return raw_input


def get_all_symbols() -> dict:
    """Return entire SYMBOL_MAP for reference."""
    return SYMBOL_MAP
