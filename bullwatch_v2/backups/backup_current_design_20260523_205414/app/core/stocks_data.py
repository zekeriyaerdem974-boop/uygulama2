# -*- coding: utf-8 -*-
"""US Stocks data service.

FAZ 17 — Real market data via Yahoo Finance.
FAZ 24A — Validated symbol universe (~550 symbols, delisted/acquired removed).
"""
from __future__ import annotations

import logging
from typing import List, Dict

from app.core.yahoo_client import get_symbols_info, get_ticker, get_klines

_logger = logging.getLogger("zkr_analiz.stocks")

# ══════════════════════════════════════════════════════════════════════
# Full S&P 500 + NASDAQ-100 + Popular Growth/Meme
# ══════════════════════════════════════════════════════════════════════
DEFAULT_SYMBOLS = [
    # ── S&P 500 Complete (alphabetical) ──────────────────────────────
    "A", "AAL", "AAPL", "ABBV", "ABNB", "ABT", "ACGL", "ACN", "ADBE", "ADI",
    "ADM", "ADP", "ADSK", "AEE", "AEP", "AES", "AFL", "AIG", "AIZ", "AJG",
    "AKAM", "ALB", "ALGN", "ALK", "ALL", "ALLE", "AMAT", "AMCR", "AMD", "AME",
    "AMGN", "AMP", "AMT", "AMZN", "ANET", "AON", "AOS", "APA", "APD",
    "APH", "APO", "APTV", "ARE", "ATO", "AVB", "AVGO", "AVY", "AWK",
    "AXP", "AZO", "BA", "BAC", "BAX", "BBWI", "BBY", "BDX", "BEN", "BF-B",
    "BG", "BIIB", "BIO", "BK", "BKNG", "BKR", "BLK", "BMY", "BR", "BRK-B",
    "BRO", "BSX", "BWA", "BX", "BXP", "C", "CAG", "CAH", "CARR", "CAT",
    "CB", "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CE", "CEG",
    "CF", "CFG", "CHD", "CHRW", "CHTR", "CI", "CINF", "CL", "CLX",
    "CMCSA", "CME", "CMG", "CMI", "CMS", "CNC", "CNP", "COF", "COO", "COP",
    "COR", "COST", "CPAY", "CPB", "CPRT", "CPT", "CRL", "CRM", "CSCO", "CSGP",
    "CSX", "CTAS", "CTRA", "CTSH", "CTVA", "CVS", "CVX", "CZR", "D",
    "DAL", "DD", "DE", "DECK", "DG", "DGX", "DHI", "DHR",
    "DIS", "DLTR", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN",
    "DXCM", "EA", "EBAY", "ECL", "ED", "EFX", "EIX", "EL", "EMN", "EMR",
    "ENPH", "EOG", "EPAM", "EQIX", "EQR", "EQT", "ESS", "ETN", "ETR",
    "ETSY", "EVRG", "EW", "EXC", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST",
    "FCNCA", "FCX", "FDS", "FDX", "FE", "FFIV", "FICO", "FIS", "FISV",
    "FITB", "FMC", "FOX", "FOXA", "FRT", "FSLR", "FTNT", "FTV", "GD",
    "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL", "GLW", "GM",
    "GNRC", "GOOG", "GOOGL", "GPC", "GPN", "GRMN", "GS", "GWW", "HAL", "HAS",
    "HBAN", "HCA", "HD", "HIG", "HII", "HLT", "HOLX",
    "HON", "HPE", "HPQ", "HRL", "HSIC", "HST", "HSY", "HUBB", "HUM", "HWM",
    "IBM", "ICE", "IDXX", "IEX", "IFF", "ILMN", "INCY", "INTC", "INTU", "INVH",
    "IP", "IQV", "IR", "IRM", "ISRG", "IT", "ITW", "IVZ", "J",
    "JBHT", "JBL", "JCI", "JKHY", "JNJ", "JPM", "KDP", "KEY",
    "KEYS", "KHC", "KIM", "KKR", "KLAC", "KMB", "KMI", "KMX", "KO", "KR",
    "KVUE", "L", "LDOS", "LEN", "LH", "LHX", "LIN", "LKQ", "LLY", "LMT",
    "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LW", "LYB", "LYV", "MA",
    "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MCO", "MDLZ", "MDT", "MET",
    "META", "MGM", "MHK", "MKC", "MKTX", "MLM", "MMC", "MMM", "MNST", "MO",
    "MOH", "MOS", "MPC", "MPWR", "MRK", "MRNA", "MS", "MSCI", "MSFT",
    "MSI", "MTB", "MTCH", "MTD", "MU", "NCLH", "NDAQ", "NDSN", "NEE", "NEM",
    "NFLX", "NI", "NKE", "NOC", "NOW", "NRG", "NSC", "NTAP", "NTRS", "NUE",
    "NVDA", "NVR", "NWL", "NWS", "NWSA", "NXPI", "O", "ODFL", "OGN", "OKE",
    "OMC", "ON", "ORCL", "ORLY", "OTIS", "OXY", "PANW", "PAYC", "PAYX",
    "PCAR", "PCG", "PEG", "PEP", "PFE", "PFG", "PG", "PGR", "PH", "PHM",
    "PKG", "PLD", "PM", "PNC", "PNR", "PNW", "PODD", "POOL", "PPG", "PPL",
    "PRU", "PSA", "PSX", "PTC", "PVH", "PWR", "PYPL", "QCOM", "QRVO",
    "RCL", "REG", "REGN", "RF", "RHI", "RJF", "RL", "RMD", "ROK",
    "ROL", "ROP", "ROST", "RSG", "RTX", "RVTY", "SBAC", "SBUX", "SCHW", "SEE",
    "SHW", "SJM", "SLB", "SMCI", "SNA", "SNPS", "SO", "SPG", "SPGI",
    "SRE", "STE", "STLD", "STT", "STX", "STZ", "SWK", "SWKS", "SYF", "SYK",
    "SYY", "T", "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TFX",
    "TGT", "TJX", "TMO", "TMUS", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO",
    "TSLA", "TSN", "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UBER", "UDR",
    "UHS", "ULTA", "UNH", "UNP", "UPS", "URI", "USB", "V", "VFC", "VICI",
    "VLO", "VLTO", "VMC", "VRSK", "VRSN", "VRTX", "VTR", "VTRS", "VZ", "WAB",
    "WAT", "WBD", "WDC", "WEC", "WELL", "WFC", "WHR", "WM", "WMB",
    "WMT", "WRB", "WST", "WTW", "WY", "WYNN", "XEL", "XOM", "XRAY",
    "XYL", "YUM", "ZBH", "ZBRA", "ZION", "ZTS",
    # ── NASDAQ-100 extras (not in S&P) ───────────────────────────────
    "ASML", "AZN", "BIDU", "CRWD", "DDOG", "DOCU", "DXCM",
    "JD", "LCID", "LBRDK", "MELI", "MNDY", "NET", "OKTA", "PDD",
    "RIVN", "SNOW", "TEAM", "TTD", "WDAY", "ZM", "ZS",
    # ── Popular Growth / Meme / Speculative ──────────────────────────
    "COIN", "MSTR", "HOOD", "SOFI", "AFRM", "UPST", "SHOP",
    "RBLX", "SNAP", "PINS", "ROKU", "U", "PLTR", "IONQ", "RGTI",
    "NIO", "XPEV", "LI", "SEDG", "RUN", "PLUG", "FCEL", "CHPT",
    "DKNG", "PENN", "CVNA", "MARA", "RIOT", "CLSK",
    "XYZ", "RNR",
    "ARM", "SMCI", "SOUN", "JOBY", "ACHR", "GRAB", "SE", "BABA",
]

# Remove duplicates while preserving order
_seen = set()
_unique = []
for _s in DEFAULT_SYMBOLS:
    if _s not in _seen:
        _seen.add(_s)
        _unique.append(_s)
DEFAULT_SYMBOLS = _unique

class StocksDataService:
    """US Stocks data service using Yahoo Finance."""

    MARKET_TYPE = "stocks"

    @staticmethod
    def get_symbols() -> List[Dict]:
        """Return list of US stock symbols with prices."""
        return get_symbols_info(DEFAULT_SYMBOLS, market_type="stocks")

    @staticmethod
    def get_ticker_single(symbol: str) -> Dict:
        """Return ticker data for a single US stock."""
        return get_ticker(symbol)

    @staticmethod
    def get_klines(symbol: str, interval: str = "1d", limit: int = 500) -> List[Dict]:
        """Return OHLCV kline data for a US stock."""
        return get_klines(symbol, interval, limit)
