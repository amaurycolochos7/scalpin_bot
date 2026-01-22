"""
Technical Analysis Module
Advanced technical indicators and signal generation with multi-factor confirmation
"""
import pandas as pd
import ta
import numpy as np
from typing import Dict, Tuple, List
from enum import Enum


class SignalType(Enum):
    """Signal types for trading"""
    STRONG_BUY = "COMPRA FUERTE"
    BUY = "COMPRA"
    NEUTRAL = "NEUTRAL"
    SELL = "VENTA"
    STRONG_SELL = "VENTA FUERTE"


class TechnicalAnalyzer:
    """
    Advanced technical analysis with multiple indicators and confirmation system
    Uses a scoring system (0-100) to determine signal strength
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize analyzer with OHLCV data
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
        """
        self.df = df.copy()
        self.indicators = {}
        self.score = 0
        self.signal = SignalType.NEUTRAL
        
    def calculate_all_indicators(self):
        """Calculate all technical indicators"""
        self._calculate_trend_indicators()
        self._calculate_momentum_indicators()
        self._calculate_volatility_indicators()
        self._calculate_volume_indicators()
        
    def _calculate_trend_indicators(self):
        """Calculate trend-following indicators (EMAs, MACD)"""
        close = self.df['close']
        
        # Exponential Moving Averages
        self.df['ema_9'] = ta.trend.EMAIndicator(close, window=9).ema_indicator()
        self.df['ema_21'] = ta.trend.EMAIndicator(close, window=21).ema_indicator()
        self.df['ema_50'] = ta.trend.EMAIndicator(close, window=50).ema_indicator()
        self.df['ema_200'] = ta.trend.EMAIndicator(close, window=200).ema_indicator()
        
        # MACD (Moving Average Convergence Divergence)
        macd = ta.trend.MACD(close, window_fast=12, window_slow=26, window_sign=9)
        self.df['macd'] = macd.macd()
        self.df['macd_signal'] = macd.macd_signal()
        self.df['macd_hist'] = macd.macd_diff()
        
        # ADX (Average Directional Index)
        try:
            high = self.df['high']
            low = self.df['low']
            adx = ta.trend.ADXIndicator(high, low, close, window=14)
            self.df['adx'] = adx.adx()
        except:
            self.df['adx'] = 0
        
    def _calculate_momentum_indicators(self):
        """Calculate momentum indicators (RSI, Stochastic)"""
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        
        # RSI (Relative Strength Index)
        self.df['rsi'] = ta.momentum.RSIIndicator(close, window=14).rsi()
        
        # Stochastic Oscillator
        stoch = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
        self.df['stoch_k'] = stoch.stoch()
        self.df['stoch_d'] = stoch.stoch_signal()
        
    def _calculate_volatility_indicators(self):
        """Calculate volatility indicators (Bollinger Bands, ATR)"""
        close = self.df['close']
        high = self.df['high']
        low = self.df['low']
        
        # Bollinger Bands
        bbands = ta.volatility.BollingerBands(close, window=20, window_dev=2)
        self.df['bb_upper'] = bbands.bollinger_hband()
        self.df['bb_middle'] = bbands.bollinger_mavg()
        self.df['bb_lower'] = bbands.bollinger_lband()
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / self.df['bb_middle']
        
        # ATR (Average True Range)
        self.df['atr'] = ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range()
        
    def _calculate_volume_indicators(self):
        """Calculate volume-based indicators (OBV, Volume MA)"""
        close = self.df['close']
        volume = self.df['volume']
        
        # On Balance Volume
        self.df['obv'] = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
        
        # Volume Moving Average (simple rolling mean)
        self.df['volume_ma'] = volume.rolling(window=20).mean()
        
        # Volume ratio (current vs average)
        self.df['volume_ratio'] = volume / self.df['volume_ma']
    
    def analyze_trend(self) -> Tuple[str, int, str]:
        """
        Analyze trend using EMAs
        
        Returns:
            Tuple of (trend_direction, score, description)
        """
        last = self.df.iloc[-1]
        current_price = last['close']
        
        score = 0
        signals = []
        
        # EMA alignment check (strong trend confirmation)
        ema_9 = last['ema_9']
        ema_21 = last['ema_21']
        ema_50 = last['ema_50']
        ema_200 = last['ema_200']
        
        # Bullish EMA alignment
        if ema_9 > ema_21 > ema_50 > ema_200:
            score += 25
            signals.append("EMAs alcistas alineadas")
        elif ema_9 > ema_21 > ema_50:
            score += 15
            signals.append("EMAs cortas alcistas")
        elif ema_21 > ema_50 > ema_200:
            score += 10
            signals.append("EMAs largas alcistas")
        
        # Bearish EMA alignment
        elif ema_9 < ema_21 < ema_50 < ema_200:
            score -= 25
            signals.append("EMAs bajistas alineadas")
        elif ema_9 < ema_21 < ema_50:
            score -= 15
            signals.append("EMAs cortas bajistas")
        elif ema_21 < ema_50 < ema_200:
            score -= 10
            signals.append("EMAs largas bajistas")
        
        # Price vs EMAs
        if current_price > ema_9:
            score += 5
        else:
            score -= 5
            
        if current_price > ema_200:
            score += 10
            signals.append("Arriba de EMA 200")
        else:
            score -= 10
            signals.append("Debajo de EMA 200")
        
        # MACD analysis
        if not pd.isna(last.get('macd')) and not pd.isna(last.get('macd_signal')):
            macd_diff = last['macd'] - last['macd_signal']
            prev_macd_diff = self.df['macd'].iloc[-2] - self.df['macd_signal'].iloc[-2]
            
            # MACD crossover
            if macd_diff > 0 and prev_macd_diff <= 0:
                score += 15
                signals.append("🔥 MACD cruzó alcista")
            elif macd_diff > 0:
                score += 8
                signals.append("MACD alcista")
            elif macd_diff < 0 and prev_macd_diff >= 0:
                score -= 15
                signals.append("⚠️ MACD cruzó bajista")
            elif macd_diff < 0:
                score -= 8
                signals.append("MACD bajista")
        
        # Determine trend
        if score > 15:
            trend = "ALCISTA"
        elif score < -15:
            trend = "BAJISTA"
        else:
            trend = "LATERAL"
        
        description = " | ".join(signals) if signals else "Sin señales claras"
        
        return trend, score, description
    
    def analyze_momentum(self) -> Tuple[str, int, str]:
        """
        Analyze momentum using RSI and Stochastic
        
        Returns:
            Tuple of (momentum_state, score, description)
        """
        last = self.df.iloc[-1]
        score = 0
        signals = []
        
        # RSI Analysis
        rsi = last['rsi']
        
        if pd.isna(rsi):
            return "NEUTRAL", 0, "RSI no disponible"
        
        if rsi < 30:
            score += 20
            signals.append("🔥 RSI oversold (<30)")
        elif rsi < 40:
            score += 10
            signals.append("RSI bajo (30-40)")
        elif rsi > 70:
            score -= 20
            signals.append("⚠️ RSI overbought (>70)")
        elif rsi > 60:
            score -= 10
            signals.append("RSI alto (60-70)")
        else:
            signals.append(f"RSI neutral ({rsi:.1f})")
        
        # RSI divergence check (simplified)
        rsi_trend = self.df['rsi'].iloc[-5:].diff().mean()
        price_trend = self.df['close'].iloc[-5:].diff().mean()
        
        if rsi_trend > 0 > price_trend:
            score += 15
            signals.append("🔥 Divergencia alcista RSI")
        elif rsi_trend < 0 < price_trend:
            score -= 15
            signals.append("⚠️ Divergencia bajista RSI")
        
        # Stochastic Analysis
        stoch_k = last.get('stoch_k')
        stoch_d = last.get('stoch_d')
        
        if not pd.isna(stoch_k) and not pd.isna(stoch_d):
            if stoch_k < 20:
                score += 10
                signals.append("Stoch oversold")
            elif stoch_k > 80:
                score -= 10
                signals.append("Stoch overbought")
            
            # Stochastic crossover
            prev_k = self.df['stoch_k'].iloc[-2]
            prev_d = self.df['stoch_d'].iloc[-2]
            
            if stoch_k > stoch_d and prev_k <= prev_d and stoch_k < 50:
                score += 15
                signals.append("🔥 Stoch cruce alcista")
            elif stoch_k < stoch_d and prev_k >= prev_d and stoch_k > 50:
                score -= 15
                signals.append("⚠️ Stoch cruce bajista")
        
        # Determine momentum state
        if score > 15:
            state = "FUERTE ALCISTA"
        elif score > 5:
            state = "ALCISTA"
        elif score < -15:
            state = "FUERTE BAJISTA"
        elif score < -5:
            state = "BAJISTA"
        else:
            state = "NEUTRAL"
        
        description = " | ".join(signals)
        
        return state, score, description
    
    def analyze_volatility(self) -> Tuple[str, int, str]:
        """
        Analyze volatility using Bollinger Bands
        
        Returns:
            Tuple of (volatility_state, score, description)
        """
        last = self.df.iloc[-1]
        score = 0
        signals = []
        
        current_price = last['close']
        bb_upper = last.get('bb_upper')
        bb_lower = last.get('bb_lower')
        bb_middle = last.get('bb_middle')
        
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return "NEUTRAL", 0, "Bollinger Bands no disponibles"
        
        # Price position in Bollinger Bands
        bb_range = bb_upper - bb_lower
        price_position = (current_price - bb_lower) / bb_range
        
        if current_price <= bb_lower:
            score += 20
            signals.append("🔥 Precio en banda inferior")
        elif price_position < 0.3:
            score += 10
            signals.append("Cerca de banda inferior")
        elif current_price >= bb_upper:
            score -= 20
            signals.append("⚠️ Precio en banda superior")
        elif price_position > 0.7:
            score -= 10
            signals.append("Cerca de banda superior")
        else:
            signals.append("Precio en rango medio")
        
        # Bollinger Band squeeze (low volatility = potential breakout)
        bb_width = last['bb_width']
        avg_bb_width = self.df['bb_width'].iloc[-20:].mean()
        
        if bb_width < avg_bb_width * 0.7:
            signals.append("📊 Squeeze detectado (baja volatilidad)")
            score += 5  # Potential upcoming move
        
        # Determine state
        if score > 10:
            state = "OVERSOLD"
        elif score < -10:
            state = "OVERBOUGHT"
        else:
            state = "NORMAL"
        
        description = " | ".join(signals)
        
        return state, score, description
    
    def analyze_volume(self) -> Tuple[str, int, str]:
        """
        Analyze volume patterns
        
        Returns:
            Tuple of (volume_state, score, description)
        """
        last = self.df.iloc[-1]
        score = 0
        signals = []
        
        volume_ratio = last.get('volume_ratio', 1)
        
        # Volume analysis
        if volume_ratio > 2:
            score += 15
            signals.append("🔥 Volumen extremo (>2x)")
        elif volume_ratio > 1.5:
            score += 10
            signals.append("Volumen alto (>1.5x)")
        elif volume_ratio < 0.5:
            score -= 5
            signals.append("Volumen bajo")
        else:
            signals.append("Volumen normal")
        
        # OBV trend
        obv_trend = self.df['obv'].iloc[-5:].diff().mean()
        price_trend = self.df['close'].iloc[-5:].diff().mean()
        
        if obv_trend > 0 and price_trend > 0:
            score += 10
            signals.append("OBV confirma tendencia alcista")
        elif obv_trend < 0 and price_trend < 0:
            score -= 10
            signals.append("OBV confirma tendencia bajista")
        elif obv_trend > 0 > price_trend:
            score += 15
            signals.append("🔥 OBV divergencia alcista")
        elif obv_trend < 0 < price_trend:
            score -= 15
            signals.append("⚠️ OBV divergencia bajista")
        
        # Determine state
        if score > 10:
            state = "ACUMULACIÓN"
        elif score < -10:
            state = "DISTRIBUCIÓN"
        else:
            state = "NEUTRAL"
        
        description = " | ".join(signals)
        
        return state, score, description
    
    def detect_candlestick_patterns(self) -> Tuple[List[str], int]:
        """
        Detect candlestick patterns
        
        Returns:
            Tuple of (list of patterns, score)
        """
        patterns = []
        score = 0
        
        # Get last 3 candles
        if len(self.df) < 3:
            return patterns, score
        
        last = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        prev2 = self.df.iloc[-3]
        
        # Calculate candle properties
        last_body = abs(last['close'] - last['open'])
        last_range = last['high'] - last['low']
        last_upper_shadow = last['high'] - max(last['close'], last['open'])
        last_lower_shadow = min(last['close'], last['open']) - last['low']
        
        prev_body = abs(prev['close'] - prev['open'])
        
        # Doji (indecision)
        if last_body < last_range * 0.1:
            patterns.append("Doji")
        
        # Hammer / Hanging Man (reversal)
        if last_lower_shadow > last_body * 2 and last_upper_shadow < last_body * 0.3:
            if prev['close'] < prev['open']:  # Downtrend
                patterns.append("🔥 Hammer (reversal alcista)")
                score += 15
            else:
                patterns.append("Hanging Man")
                score -= 10
        
        # Shooting Star (bearish reversal)
        if last_upper_shadow > last_body * 2 and last_lower_shadow < last_body * 0.3:
            if prev['close'] > prev['open']:  # Uptrend
                patterns.append("⚠️ Shooting Star (reversal bajista)")
                score -= 15
        
        # Bullish Engulfing
        if (prev['close'] < prev['open'] and  # Prev bearish
            last['close'] > last['open'] and  # Current bullish
            last['open'] < prev['close'] and  # Opens below prev close
            last['close'] > prev['open']):    # Closes above prev open
            patterns.append("🔥 Bullish Engulfing")
            score += 20
        
        # Bearish Engulfing
        if (prev['close'] > prev['open'] and  # Prev bullish
            last['close'] < last['open'] and  # Current bearish
            last['open'] > prev['close'] and  # Opens above prev close
            last['close'] < prev['open']):    # Closes below prev open
            patterns.append("⚠️ Bearish Engulfing")
            score -= 20
        
        # Morning Star (bullish reversal - 3 candles)
        if (prev2['close'] < prev2['open'] and  # First bearish
            abs(prev['close'] - prev['open']) < prev_body * 0.3 and  # Small body
            last['close'] > last['open'] and  # Third bullish
            last['close'] > (prev2['open'] + prev2['close']) / 2):  # Closes above midpoint
            patterns.append("🔥 Morning Star")
            score += 25
        
        # Evening Star (bearish reversal - 3 candles)
        if (prev2['close'] > prev2['open'] and  # First bullish
            abs(prev['close'] - prev['open']) < prev_body * 0.3 and  # Small body
            last['close'] < last['open'] and  # Third bearish
            last['close'] < (prev2['open'] + prev2['close']) / 2):  # Closes below midpoint
            patterns.append("⚠️ Evening Star")
            score -= 25
        
        return patterns, score
    
    def generate_analysis(self) -> Dict:
        """
        Generate complete technical analysis with scoring system
        
        Returns:
            Dictionary with complete analysis results
        """
        # Calculate all indicators first
        self.calculate_all_indicators()
        
        # Analyze each component
        trend, trend_score, trend_desc = self.analyze_trend()
        momentum, momentum_score, momentum_desc = self.analyze_momentum()
        volatility, volatility_score, volatility_desc = self.analyze_volatility()
        volume, volume_score, volume_desc = self.analyze_volume()
        patterns, pattern_score = self.detect_candlestick_patterns()
        
        # Calculate total score (weighted)
        total_score = (
            trend_score * 0.35 +         # Trend is most important
            momentum_score * 0.30 +       # Momentum second
            volatility_score * 0.15 +     # Volatility third
            volume_score * 0.15 +         # Volume fourth
            pattern_score * 0.05          # Patterns as confirmation
        )
        
        # Normalize to 0-100
        total_score = max(0, min(100, (total_score + 50) * 1.0))
        
        # Determine signal
        if total_score >= 70:
            signal = SignalType.STRONG_BUY
        elif total_score >= 55:
            signal = SignalType.BUY
        elif total_score <= 30:
            signal = SignalType.STRONG_SELL
        elif total_score <= 45:
            signal = SignalType.SELL
        else:
            signal = SignalType.NEUTRAL
        
        # Get current price data
        last = self.df.iloc[-1]
        
        return {
            'price': last['close'],
            'timestamp': last.name,
            'score': round(total_score, 1),
            'signal': signal,
            'trend': {
                'direction': trend,
                'score': trend_score,
                'description': trend_desc
            },
            'momentum': {
                'state': momentum,
                'score': momentum_score,
                'description': momentum_desc
            },
            'volatility': {
                'state': volatility,
                'score': volatility_score,
                'description': volatility_desc
            },
            'volume': {
                'state': volume,
                'score': volume_score,
                'description': volume_desc
            },
            'patterns': patterns,
            'indicators': {
                'rsi': round(last['rsi'], 2) if not pd.isna(last['rsi']) else None,
                'macd': round(last['macd'], 4) if 'macd' in last and not pd.isna(last['macd']) else None,
                'macd_signal': round(last['macd_signal'], 4) if 'macd_signal' in last and not pd.isna(last['macd_signal']) else None,
                'ema_9': round(last['ema_9'], 2),
                'ema_21': round(last['ema_21'], 2),
                'ema_50': round(last['ema_50'], 2),
                'ema_200': round(last['ema_200'], 2),
                'bb_upper': round(last['bb_upper'], 2) if 'bb_upper' in last and not pd.isna(last['bb_upper']) else None,
                'bb_lower': round(last['bb_lower'], 2) if 'bb_lower' in last and not pd.isna(last['bb_lower']) else None,
                'volume_ratio': round(last['volume_ratio'], 2) if 'volume_ratio' in last else None,
                'adx': round(last['adx'], 2) if 'adx' in last else 0,
            }
        }


def analyze_symbol(symbol: str, timeframe: str = None) -> Dict:
    """
    Convenience function to analyze a symbol
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Timeframe for analysis
        
    Returns:
        Analysis dictionary
    """
    from src.binance_client import get_client
    
    client = get_client()
    df = client.get_ohlcv(symbol, timeframe)
    
    analyzer = TechnicalAnalyzer(df)
    return analyzer.generate_analysis()
