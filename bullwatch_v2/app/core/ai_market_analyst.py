"""
Faze 7: AI Educational Market Brief Engine (Mock AI with algorithmic analysis)
Educational-only market analysis simulator for YMYL compliance
"""

import math
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class AIMockAnalyst:
    """
    Algorithmic market analyst that processes OHLCV candles and generates
    educational 3-sentence Turkish market briefs without real trading advice.
    """

    def __init__(self):
        self.sma_period = 20  # 20-candle simple moving average
        self.rsi_period = 14   # Standard RSI period

    def calculate_sma(self, closes: List[float], period: int) -> List[float]:
        """Calculate Simple Moving Average"""
        sma = []
        for i in range(len(closes)):
            if i < period - 1:
                sma.append(None)
            else:
                sma.append(sum(closes[i - period + 1:i + 1]) / period)
        return sma

    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index (simplified for last candle)"""
        if len(closes) < period + 1:
            return 50.0  # Neutral RSI if insufficient data

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [abs(d) if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period if period > 0 else 0
        avg_loss = sum(losses) / period if period > 0 else 0

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def calculate_volatility(self, closes: List[float]) -> float:
        """Calculate price volatility as percentage (std deviation)"""
        if len(closes) < 2:
            return 0.0

        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / len(closes)
        std_dev = math.sqrt(variance)
        volatility = (std_dev / mean * 100) if mean > 0 else 0
        return round(volatility, 2)

    def detect_trend(self, closes: List[float]) -> Tuple[str, float]:
        """
        Detect trend direction using SMA slope
        Returns: ('yükselen'/'düşen'/'yatay', strength_percentage)
        """
        if len(closes) < self.sma_period:
            return 'yatay', 0.0

        sma = self.calculate_sma(closes, self.sma_period)
        recent_sma = [s for s in sma[-5:] if s is not None]

        if len(recent_sma) < 2:
            return 'yatay', 0.0

        sma_slope = recent_sma[-1] - recent_sma[0]
        current_price = closes[-1]

        if sma_slope > current_price * 0.001:
            trend = 'yükselen'
        elif sma_slope < -current_price * 0.001:
            trend = 'düşen'
        else:
            trend = 'yatay'

        strength = abs(sma_slope) / current_price * 100 if current_price > 0 else 0
        return trend, round(min(strength, 100), 2)

    def detect_momentum_blocks(self, candles: List[Dict]) -> Tuple[str, int]:
        """
        Detect consecutive green/red candles (momentum blocks)
        Returns: ('yeşil'/'kırmızı', consecutive_count)
        """
        if not candles:
            return 'yeşil', 0

        colors = ['yeşil' if c['close'] >= c['open'] else 'kırmızı' for c in candles[-10:]]

        # Count consecutive last color blocks
        last_color = colors[-1]
        count = 1
        for i in range(len(colors) - 2, -1, -1):
            if colors[i] == last_color:
                count += 1
            else:
                break

        return last_color, count

    def format_market_brief(self, candles: List[Dict], timeframe: str) -> str:
        """
        Generate 3-sentence educational Turkish market brief
        
        Format:
        1. Current state (trend + timeframe)
        2. Academic theory (momentum blocks + buyer/seller pressure)
        3. Educational warning (RSI context)
        """
        if not candles or len(candles) < 2:
            return "Yetersiz veri: Analiz için en az 20 mum gereklidir."

        try:
            closes = [c['close'] for c in candles]
            
            # Analysis 1: Trend detection
            trend, strength = self.detect_trend(closes)
            timeframe_label = self._format_timeframe(timeframe)
            
            # Analysis 2: Momentum blocks
            color, consecutive = self.detect_momentum_blocks(candles)
            
            # Analysis 3: RSI
            rsi = self.calculate_rsi(closes)
            rsi_status = self._interpret_rsi(rsi)
            rsi_direction = 'Yaklaştığını' if rsi_status['zone'] else 'Uzaklaştığını'
            
            # Build sentences
            sentence_1 = f"Seçili {timeframe_label} periyodunda varlık {trend} bir fiyat kanalı sergilemektedir."
            
            buyer_seller = 'Alıcıların' if color == 'yeşil' else 'Satıcıların'
            momentum_direction = 'Güçlendiğine' if color == 'yeşil' else 'Zayıfladığına'
            sentence_2 = f"Teknik analizde bu tip ardışık {color} mum blokları, piyasada {buyer_seller} baskın olduğuna ve momentumun {momentum_direction} işaret eder."
            
            zone_name = 'Aşırı Alım' if rsi_status['zone'] == 'overbought' else 'Aşırı Satım'
            sentence_3 = f"RSI göstergesinin {rsi:.1f} seviyelerinde olması, varlığın teorik olarak {zone_name} bölgesine {rsi_direction} gösterir."
            
            brief = f"{sentence_1}\n\n{sentence_2}\n\n{sentence_3}"
            
            logger.info(f"[AI MARKET BRIEF] Generated for {timeframe}: {trend} trend, RSI {rsi:.1f}")
            return brief
            
        except Exception as e:
            logger.error(f"Error generating market brief: {e}")
            return "Analiz hatası: Lütfen sayfayı yenileyin."

    def _format_timeframe(self, timeframe: str) -> str:
        """Convert timeframe code to Turkish label"""
        mapping = {
            '1m': '1 dakikalık',
            '5m': '5 dakikalık',
            '15m': '15 dakikalık',
            '30m': '30 dakikalık',
            '1h': '1 saatlik',
            '4h': '4 saatlik',
            '1d': '1 günlük',
            '1w': '1 haftalık',
            '1M': '1 aylık'
        }
        return mapping.get(timeframe, timeframe + ' periyot')

    def _interpret_rsi(self, rsi: float) -> Dict:
        """Interpret RSI value"""
        if rsi >= 70:
            return {'zone': 'overbought', 'level': 'Aşırı Alım'}
        elif rsi <= 30:
            return {'zone': 'oversold', 'level': 'Aşırı Satım'}
        else:
            return {'zone': None, 'level': 'Nötr'}


def analyze_market_brief(candles: List[Dict], timeframe: str, symbol: str = 'BTCUSDT') -> Dict:
    """
    Public API endpoint for market brief generation
    
    Args:
        candles: List of OHLCV candles [{time, open, high, low, close, volume}, ...]
        timeframe: Timeframe string (e.g., '1h', '4h', '1d')
        symbol: Trading symbol (for logging)
    
    Returns:
        {
            'ok': bool,
            'symbol': str,
            'timeframe': str,
            'brief': str,  # 3-sentence educational brief
            'disclaimer': str  # Educational-only disclaimer
        }
    """
    disclaimer = "*Bu analiz, geçmiş fiyat hareketlerine dayalı teorik bir simülasyondur; al-sat tavsiyesi içermez."
    
    try:
        analyst = AIMockAnalyst()
        
        # Validate input
        if not candles or len(candles) < 20:
            return {
                'ok': False,
                'symbol': symbol,
                'timeframe': timeframe,
                'brief': 'Yetersiz veri: Analiz için en az 20 mum gereklidir.',
                'disclaimer': disclaimer,
                'error': 'insufficient_data'
            }
        
        # Generate brief
        brief = analyst.format_market_brief(candles, timeframe)
        
        return {
            'ok': True,
            'symbol': symbol,
            'timeframe': timeframe,
            'brief': brief,
            'disclaimer': disclaimer
        }
    
    except Exception as e:
        logger.error(f"Market brief analysis failed: {e}")
        return {
            'ok': False,
            'symbol': symbol,
            'timeframe': timeframe,
            'brief': 'Analiz hatası: Lütfen sayfayı yenileyin.',
            'disclaimer': disclaimer,
            'error': str(e)
        }
