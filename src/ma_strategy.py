"""
Estrategia MA7 x MA25 con confirmación 4H y TradingView 3-arrow
Basado en la recomendación del experto

Señal LONG:
- MA7 cruza ARRIBA de MA25 en 15M
- Tendencia 4H: Alcista
- 3 flechas TradingView: ARRIBA

Señal SHORT:
- MA7 cruza ABAJO de MA25 en 15M
- Tendencia 4H: Bajista
- 3 flechas TradingView: ABAJO
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import ccxt
from src.config import Config


class MAStrategy:
    """Estrategia basada en cruces de MA7 y MA25"""
    
    def __init__(self):
        self.exchange = ccxt.binanceusdm({
            'apiKey': Config.BINANCE_API_KEY,
            'secret': Config.BINANCE_SECRET_KEY,
            'enableRateLimit': True,
        })
    
    def calculate_ma_cross(self, df: pd.DataFrame, fast_period: int = 7, slow_period: int = 25) -> Dict:
        """
        Detecta cruces de medias móviles
        
        Returns:
            dict: {
                'cross': 'bullish' / 'bearish' / None,
                'ma7': float,
                'ma25': float,
                'ma7_prev': float,
                'ma25_prev': float
            }
        """
        if len(df) < slow_period + 2:
            return {'cross': None, 'error': 'Insufficient data'}
        
        # Calcular MAs
        df['MA7'] = df['close'].rolling(window=fast_period).mean()
        df['MA25'] = df['close'].rolling(window=slow_period).mean()
        
        # Valores actuales y previos
        ma7_current = df['MA7'].iloc[-1]
        ma25_current = df['MA25'].iloc[-1]
        ma7_prev = df['MA7'].iloc[-2]
        ma25_prev = df['MA25'].iloc[-2]
        
        # Detectar cruce
        cross = None
        if ma7_prev <= ma25_prev and ma7_current > ma25_current:
            cross = 'bullish'  # Cruce alcista
        elif ma7_prev >= ma25_prev and ma7_current < ma25_current:
            cross = 'bearish'  # Cruce bajista
        
        return {
            'cross': cross,
            'ma7': ma7_current,
            'ma25': ma25_current,
            'ma7_prev': ma7_prev,
            'ma25_prev': ma25_prev,
            'position': 'above' if ma7_current > ma25_current else 'below'
        }
    
    def check_4h_trend(self, symbol: str) -> str:
        """
        Verifica tendencia en timeframe 4H
        
        Returns:
            'bullish' / 'bearish' / 'neutral'
        """
        try:
            # Obtener velas de 4H
            ohlcv = self.exchange.fetch_ohlcv(symbol, '4h', limit=50)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Calcular MA de 20 periodos en 4H
            df['MA20'] = df['close'].rolling(window=20).mean()
            
            current_price = df['close'].iloc[-1]
            ma20 = df['MA20'].iloc[-1]
            
            # Determinar tendencia
            if current_price > ma20:
                return 'bullish'
            elif current_price < ma20:
                return 'bearish'
            else:
                return 'neutral'
        
        except Exception as e:
            print(f"Error checking 4H trend: {str(e)}")
            return 'neutral'
    
    def calculate_tradingview_indicators(self, df: pd.DataFrame) -> Dict:
        """
        Calcula indicadores tipo TradingView
        
        Returns:
            dict: {
                'oscillators': 'buy' / 'sell' / 'neutral',
                'moving_averages': 'buy' / 'sell' / 'neutral',
                'summary': 'buy' / 'sell' / 'neutral'
            }
        """
        if len(df) < 200:
            return {'oscillators': 'neutral', 'moving_averages': 'neutral', 'summary': 'neutral'}
        
        current_price = df['close'].iloc[-1]
        
        # ============ OSCILLATORS ============
        oscillator_signals = []
        
        # RSI
        from ta.momentum import RSIIndicator
        rsi = RSIIndicator(df['close'], window=14)
        rsi_value = rsi.rsi().iloc[-1]
        if rsi_value < 40:
            oscillator_signals.append('buy')
        elif rsi_value > 60:
            oscillator_signals.append('sell')
        else:
            oscillator_signals.append('neutral')
        
        # Stochastic
        from ta.momentum import StochasticOscillator
        stoch = StochasticOscillator(df['high'], df['low'], df['close'])
        stoch_k = stoch.stoch().iloc[-1]
        if stoch_k < 20:
            oscillator_signals.append('buy')
        elif stoch_k > 80:
            oscillator_signals.append('sell')
        else:
            oscillator_signals.append('neutral')
        
        # CCI
        from ta.trend import CCIIndicator
        cci = CCIIndicator(df['high'], df['low'], df['close'])
        cci_value = cci.cci().iloc[-1]
        if cci_value < -100:
            oscillator_signals.append('buy')
        elif cci_value > 100:
            oscillator_signals.append('sell')
        else:
            oscillator_signals.append('neutral')
        
        # Resumen de osciladores
        buy_count = oscillator_signals.count('buy')
        sell_count = oscillator_signals.count('sell')
        
        if buy_count > sell_count:
            oscillators_summary = 'buy'
        elif sell_count > buy_count:
            oscillators_summary = 'sell'
        else:
            oscillators_summary = 'neutral'
        
        # ============ MOVING AVERAGES ============
        ma_signals = []
        
        # EMAs principales
        for period in [10, 20, 30, 50, 100, 200]:
            ema = df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
            if current_price > ema:
                ma_signals.append('buy')
            elif current_price < ema:
                ma_signals.append('sell')
            else:
                ma_signals.append('neutral')
        
        # Resumen de MAs
        buy_ma_count = ma_signals.count('buy')
        sell_ma_count = ma_signals.count('sell')
        
        if buy_ma_count > sell_ma_count:
            ma_summary = 'buy'
        elif sell_ma_count > buy_ma_count:
            ma_summary = 'sell'
        else:
            ma_summary = 'neutral'
        
        # ============ SUMMARY (3 ARROWS) ============
        # Contamos: osciladores + MAs + tendencia de precio
        signals = [oscillators_summary, ma_summary]
        
        buy_total = signals.count('buy')
        sell_total = signals.count('sell')
        
        if buy_total >= 2:
            summary = 'buy'
        elif sell_total >= 2:
            summary = 'sell'
        else:
            summary = 'neutral'
        
        return {
            'oscillators': oscillators_summary,
            'moving_averages': ma_summary,
            'summary': summary,
            'details': {
                'rsi': rsi_value,
                'stoch': stoch_k,
                'cci': cci_value
            }
        }
    
    def get_expert_signal(self, symbol: str) -> Optional[Dict]:
        """
        Obtiene señal según estrategia del experto
        
        Returns:
            dict o None: {
                'symbol': str,
                'signal': 'LONG' / 'SHORT',
                'entry_price': float,
                'sl_price': float (-10%),
                'tp_price': float (+10%),
                'ma7': float,
                'ma25': float,
                '4h_trend': str,
                'tradingview': dict,
                'confidence': str
            }
        """
        try:
            # Obtener velas de 15M
            ohlcv = self.exchange.fetch_ohlcv(symbol, '15m', limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # 1. Detectar cruce de MAs en 15M
            ma_cross = self.calculate_ma_cross(df)
            
            if not ma_cross.get('cross'):
                return None  # No hay cruce
            
            # 2. Verificar tendencia en 4H
            trend_4h = self.check_4h_trend(symbol)
            
            # 3. Calcular indicadores TradingView
            tv_indicators = self.calculate_tradingview_indicators(df)
            
            # Validar coincidencia
            cross_type = ma_cross['cross']  # 'bullish' o 'bearish'
            
            # Para LONG: cruce bullish + tendencia 4H bullish + TV buy
            # Para SHORT: cruce bearish + tendencia 4H bearish + TV sell
            
            signal = None
            if cross_type == 'bullish' and trend_4h == 'bullish' and tv_indicators['summary'] == 'buy':
                signal = 'LONG'
            elif cross_type == 'bearish' and trend_4h == 'bearish' and tv_indicators['summary'] == 'sell':
                signal = 'SHORT'
            
            if not signal:
                return None  # No cumple todas las condiciones
            
            # Calcular precios de entrada, SL y TP
            entry_price = df['close'].iloc[-1]
            
            if signal == 'LONG':
                sl_price = entry_price * 0.90  # -10%
                tp_price = entry_price * 1.10  # +10%
            else:  # SHORT
                sl_price = entry_price * 1.10  # +10%
                tp_price = entry_price * 0.90  # -10%
            
            # Determinar nivel de confianza
            confidence = 'HIGH'
            if trend_4h == 'neutral':
                confidence = 'MEDIUM'
            
            return {
                'symbol': symbol,
                'signal': signal,
                'entry_price': entry_price,
                'sl_price': sl_price,
                'tp_price': tp_price,
                'ma7': ma_cross['ma7'],
                'ma25': ma_cross['ma25'],
                '4h_trend': trend_4h,
                'tradingview': tv_indicators,
                'confidence': confidence,
                'timestamp': pd.Timestamp.now().isoformat()
            }
        
        except Exception as e:
            print(f"Error getting expert signal for {symbol}: {str(e)}")
            return None
