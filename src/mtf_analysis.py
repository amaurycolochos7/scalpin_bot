"""
Multi-Timeframe (MTF) Analysis Module - CANDLE COLOR STRATEGY
Based on friend's trading strategy:
- Revisar velas de 4H (tendencia principal)
- Revisar velas de 1H (confirmación intermedia)  
- Revisar velas de 15m: 3+ velas del mismo color = confirmación de cambio de tendencia
"""

from dataclasses import dataclass
from typing import Optional, Dict, List
from enum import Enum
import pandas as pd
from src.technical_analysis import TechnicalAnalyzer, SignalType


@dataclass
class TimeframeData:
    """Data for a single timeframe analysis"""
    timeframe: str
    score: float
    signal: SignalType
    trend: str
    rsi: float
    macd_bullish: bool
    volume_ok: bool
    ma7: float
    ma25: float
    # Candle color trend data
    candle_colors: str = ''  # Visual: 🟢🟢🟢🔴🔴🔴
    consecutive_same: int = 0  # Number of consecutive same color
    candle_trend: str = 'NONE'  # BULLISH, BEARISH, or NONE
    candle_confirmed: bool = False  # True if 3+ same color


@dataclass
class MTFAnalysis:
    """Results of multi-timeframe analysis with MA7/MA25 strategy"""
    symbol: str
    price: float
    
    # Timeframe data
    tf_15m: Optional[TimeframeData]
    tf_1h: Optional[TimeframeData]
    tf_4h: Optional[TimeframeData]
    
    # MA7/MA25 Crossover
    ma_crossover: dict
    
    # TradingView 10 Indicators
    tv_votes: dict
    
    # Candle Color Confirmation (NEW - Friend's strategy)
    candle_confirmation_15m: dict  # 15m candle color data
    
    # Final Decision
    should_trade: bool
    trade_direction: str  # 'LONG', 'SHORT', or 'NEUTRAL'
    confidence: int  # Percentage based on alignment
    reason: str
    warnings: List[str]


class MultiTimeframeAnalyzer:
    """
    Analyzes crypto using CANDLE COLOR strategy:
    - 4H: Tendencia principal
    - 1H: Confirmación intermedia
    - 15m: 3+ velas del mismo color = confirmación de cambio de tendencia
    """
    
    def __init__(self, client):
        self.client = client
        self.primary_tf = '15m'
    
    def analyze(self, symbol: str) -> MTFAnalysis:
        """
        Analyze symbol using Multi-Timeframe Candle Color strategy
        
        Strategy (friend's method):
        1. Revisar velas de 4H (tendencia principal)
        2. Revisar velas de 1H (confirmación intermedia)
        3. Revisar velas de 15m: 3+ velas del mismo color = cambio confirmado
        """
        
        # ========== 15M ANALYSIS (CONFIRMATION) ==========
        df_15m = self.client.get_ohlcv(symbol, '15m')
        analyzer_15m = TechnicalAnalyzer(df_15m)
        analyzer_15m.calculate_all_indicators()
        
        ma_crossover = analyzer_15m.detect_ma_crossover()
        tv_votes = analyzer_15m.get_tradingview_votes()
        candle_15m = analyzer_15m.detect_candle_color_trend(lookback=6)
        analysis_15m = analyzer_15m.generate_analysis()
        
        tf_15m_data = TimeframeData(
            timeframe='15m',
            score=analysis_15m['score'],
            signal=analysis_15m['signal'],
            trend=analysis_15m['trend']['direction'],
            rsi=analysis_15m['indicators']['rsi'] if analysis_15m['indicators']['rsi'] else 50,
            macd_bullish=analysis_15m['indicators']['macd'] > 0 if analysis_15m['indicators']['macd'] else False,
            volume_ok=analysis_15m['indicators']['volume_ratio'] > 1.0 if analysis_15m['indicators']['volume_ratio'] else True,
            ma7=ma_crossover['ma7'],
            ma25=ma_crossover['ma25'],
            candle_colors=candle_15m['candle_colors'],
            consecutive_same=max(candle_15m['consecutive_green'], candle_15m['consecutive_red']),
            candle_trend=candle_15m['trend_change'],
            candle_confirmed=candle_15m['confirmed']
        )
        
        # ========== 1H ANALYSIS (INTERMEDIATE) ==========
        tf_1h_data = None
        candle_1h = {'trend_change': 'NONE', 'confirmed': False, 'candle_colors': '', 'consecutive_green': 0, 'consecutive_red': 0}
        
        try:
            df_1h = self.client.get_ohlcv(symbol, '1h')
            analyzer_1h = TechnicalAnalyzer(df_1h)
            analyzer_1h.calculate_all_indicators()
            ma_1h = analyzer_1h.detect_ma_crossover()
            candle_1h = analyzer_1h.detect_candle_color_trend(lookback=6)
            analysis_1h = analyzer_1h.generate_analysis()
            
            tf_1h_data = TimeframeData(
                timeframe='1h',
                score=analysis_1h['score'],
                signal=analysis_1h['signal'],
                trend=analysis_1h['trend']['direction'],
                rsi=analysis_1h['indicators']['rsi'] if analysis_1h['indicators']['rsi'] else 50,
                macd_bullish=analysis_1h['indicators']['macd'] > 0 if analysis_1h['indicators']['macd'] else False,
                volume_ok=True,
                ma7=ma_1h['ma7'],
                ma25=ma_1h['ma25'],
                candle_colors=candle_1h['candle_colors'],
                consecutive_same=max(candle_1h['consecutive_green'], candle_1h['consecutive_red']),
                candle_trend=candle_1h['trend_change'],
                candle_confirmed=candle_1h['confirmed']
            )
        except:
            pass
        
        # ========== 4H ANALYSIS (MAIN TREND) ==========
        tf_4h_data = None
        candle_4h = {'trend_change': 'NONE', 'confirmed': False, 'candle_colors': '', 'consecutive_green': 0, 'consecutive_red': 0}
        
        try:
            df_4h = self.client.get_ohlcv(symbol, '4h')
            analyzer_4h = TechnicalAnalyzer(df_4h)
            analyzer_4h.calculate_all_indicators()
            ma_4h = analyzer_4h.detect_ma_crossover()
            candle_4h = analyzer_4h.detect_candle_color_trend(lookback=6)
            analysis_4h = analyzer_4h.generate_analysis()
            
            tf_4h_data = TimeframeData(
                timeframe='4h',
                score=analysis_4h['score'],
                signal=analysis_4h['signal'],
                trend=analysis_4h['trend']['direction'],
                rsi=analysis_4h['indicators']['rsi'] if analysis_4h['indicators']['rsi'] else 50,
                macd_bullish=analysis_4h['indicators']['macd'] > 0 if analysis_4h['indicators']['macd'] else False,
                volume_ok=True,
                ma7=ma_4h['ma7'],
                ma25=ma_4h['ma25'],
                candle_colors=candle_4h['candle_colors'],
                consecutive_same=max(candle_4h['consecutive_green'], candle_4h['consecutive_red']),
                candle_trend=candle_4h['trend_change'],
                candle_confirmed=candle_4h['confirmed']
            )
        except:
            pass
        
        # Get current price
        ticker = self.client.get_ticker(symbol)
        current_price = ticker['price']
        
        # Make trading decision using NEW candle color strategy
        should_trade, direction, confidence, reason = self._make_decision(
            tf_4h_data, tf_1h_data, tf_15m_data, candle_15m, tv_votes
        )
        
        # Collect warnings
        warnings = self._collect_warnings(tf_4h_data, tf_1h_data, tf_15m_data, candle_15m)
        
        return MTFAnalysis(
            symbol=symbol,
            price=current_price,
            tf_15m=tf_15m_data,
            tf_1h=tf_1h_data,
            tf_4h=tf_4h_data,
            ma_crossover=ma_crossover,
            tv_votes=tv_votes,
            candle_confirmation_15m=candle_15m,
            should_trade=should_trade,
            trade_direction=direction,
            confidence=confidence,
            reason=reason,
            warnings=warnings
        )
    
    def _make_decision(self, tf_4h: Optional[TimeframeData], tf_1h: Optional[TimeframeData], 
                       tf_15m: Optional[TimeframeData], candle_15m: dict, tv_votes: dict) -> tuple:
        """
        Make trading decision based on CANDLE COLOR STRATEGY:
        
        1. 4H: Tendencia principal (alcista/bajista)
        2. 1H: Confirmación intermedia
        3. 15m: 3+ velas del mismo color = confirmación de cambio
        
        Returns: (should_trade, direction, confidence, reason)
        """
        
        # Get 15m candle confirmation (KEY SIGNAL)
        candle_trend = candle_15m.get('trend_change', 'NONE')
        candle_confirmed = candle_15m.get('confirmed', False)
        consecutive = max(candle_15m.get('consecutive_green', 0), candle_15m.get('consecutive_red', 0))
        
        # Determine 4H and 1H trends
        trend_4h = 'NONE'
        trend_1h = 'NONE'
        
        if tf_4h:
            if 'ALCISTA' in tf_4h.trend or tf_4h.ma7 > tf_4h.ma25:
                trend_4h = 'BULLISH'
            elif 'BAJISTA' in tf_4h.trend or tf_4h.ma7 < tf_4h.ma25:
                trend_4h = 'BEARISH'
        
        if tf_1h:
            if 'ALCISTA' in tf_1h.trend or tf_1h.ma7 > tf_1h.ma25:
                trend_1h = 'BULLISH'
            elif 'BAJISTA' in tf_1h.trend or tf_1h.ma7 < tf_1h.ma25:
                trend_1h = 'BEARISH'
        
        # Calculate confidence based on alignment
        alignment_score = 0
        if trend_4h == 'BULLISH' and candle_trend == 'BULLISH':
            alignment_score += 35
        elif trend_4h == 'BEARISH' and candle_trend == 'BEARISH':
            alignment_score += 35
        
        if trend_1h == 'BULLISH' and candle_trend == 'BULLISH':
            alignment_score += 25
        elif trend_1h == 'BEARISH' and candle_trend == 'BEARISH':
            alignment_score += 25
        
        if candle_confirmed:
            alignment_score += 40
        
        confidence = min(alignment_score, 100)
        
        # ============ DECISION LOGIC ============
        
        # CASE 1: LONG / COMPRA - All timeframes bullish + 3+ green candles
        if candle_trend == 'BULLISH' and candle_confirmed:
            if trend_4h == 'BULLISH' and trend_1h == 'BULLISH':
                return True, 'LONG', confidence, f'✅ COMPRA / LONG confirmado\n   4H: ▲ | 1H: ▲ | 15m: {consecutive} velas verdes'
            elif trend_4h == 'BULLISH':
                return True, 'LONG', confidence - 15, f'🟢 COMPRA / LONG (4H alcista)\n   15m: {consecutive} velas verdes'
            elif trend_1h == 'BULLISH':
                return True, 'LONG', confidence - 20, f'🟢 COMPRA / LONG (1H alcista)\n   15m: {consecutive} velas verdes'
            else:
                return False, 'LONG', confidence - 30, f'⚠️ 15m alcista pero TFs superiores no confirman'
        
        # CASE 2: SHORT / VENTA - All timeframes bearish + 3+ red candles
        if candle_trend == 'BEARISH' and candle_confirmed:
            if trend_4h == 'BEARISH' and trend_1h == 'BEARISH':
                return True, 'SHORT', confidence, f'✅ VENTA / SHORT confirmado\n   4H: ▼ | 1H: ▼ | 15m: {consecutive} velas rojas'
            elif trend_4h == 'BEARISH':
                return True, 'SHORT', confidence - 15, f'🔴 VENTA / SHORT (4H bajista)\n   15m: {consecutive} velas rojas'
            elif trend_1h == 'BEARISH':
                return True, 'SHORT', confidence - 20, f'🔴 VENTA / SHORT (1H bajista)\n   15m: {consecutive} velas rojas'
            else:
                return False, 'SHORT', confidence - 30, f'⚠️ 15m bajista pero TFs superiores no confirman'
        
        # CASE 3: Partial confirmation - waiting for 3+ candles
        if consecutive > 0 and consecutive < 3:
            if candle_15m.get('consecutive_green', 0) > 0:
                return False, 'NEUTRAL', 20, f'⏳ ESPERAR - {consecutive} vela(s) verde(s)\n   Necesita 3+ para confirmar COMPRA / LONG'
            else:
                return False, 'NEUTRAL', 20, f'⏳ ESPERAR - {consecutive} vela(s) roja(s)\n   Necesita 3+ para confirmar VENTA / SHORT'
        
        # CASE 4: No clear signal
        return False, 'NEUTRAL', 10, '⏳ ESPERAR - Sin confirmación de tendencia'
    
    def _collect_warnings(self, tf_4h: Optional[TimeframeData], tf_1h: Optional[TimeframeData],
                          tf_15m: Optional[TimeframeData], candle_15m: dict) -> List[str]:
        """Collect warnings for the user"""
        warnings = []
        
        # Check timeframe misalignment
        if tf_4h and tf_1h:
            if tf_4h.candle_trend != tf_1h.candle_trend and tf_4h.candle_trend != 'NONE' and tf_1h.candle_trend != 'NONE':
                warnings.append("⚠️ 4H y 1H muestran tendencias opuestas")
        
        if tf_4h and tf_15m:
            if tf_4h.candle_trend != candle_15m.get('trend_change', 'NONE'):
                if 'BULLISH' in candle_15m.get('trend_change', '') and tf_4h.candle_trend == 'BEARISH':
                    warnings.append("⚠️ 15m alcista pero 4H bajista")
                elif 'BEARISH' in candle_15m.get('trend_change', '') and tf_4h.candle_trend == 'BULLISH':
                    warnings.append("⚠️ 15m bajista pero 4H alcista")
        
        # Check for conflicting candle colors
        consecutive = max(candle_15m.get('consecutive_green', 0), candle_15m.get('consecutive_red', 0))
        if consecutive < 3 and consecutive > 0:
            warnings.append(f"⏳ Esperando confirmación ({consecutive}/3 velas)")
        
        return warnings


def format_mtf_analysis(mtf: MTFAnalysis, strategy: dict) -> str:
    """Format MTF analysis for Telegram with CANDLE COLOR strategy display"""
    
    def format_price(price: float) -> str:
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        return f"${price:.8f}"
    
    # Simple coin name
    coin = mtf.symbol.replace('/USDT:USDT', '').replace('/USDT', '')
    
    msg = f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
    msg += f"┃   {coin:^14}   ┃\n"
    msg += f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    msg += f"💰 Precio: {format_price(mtf.price)}\n\n"
    
    # ========== MULTI-TIMEFRAME ANALYSIS ==========
    msg += "━━━ Análisis Multi-Timeframe ━━━\n\n"
    
    # 4H Timeframe
    if mtf.tf_4h:
        trend_icon = "▲" if mtf.tf_4h.candle_trend == 'BULLISH' or 'ALCISTA' in mtf.tf_4h.trend else ("▼" if mtf.tf_4h.candle_trend == 'BEARISH' or 'BAJISTA' in mtf.tf_4h.trend else "▬")
        trend_text = "ALCISTA" if mtf.tf_4h.candle_trend == 'BULLISH' or 'ALCISTA' in mtf.tf_4h.trend else ("BAJISTA" if mtf.tf_4h.candle_trend == 'BEARISH' or 'BAJISTA' in mtf.tf_4h.trend else "LATERAL")
        msg += f"📊 4H: {trend_icon} {trend_text}\n"
        if mtf.tf_4h.candle_colors:
            msg += f"   Velas: {mtf.tf_4h.candle_colors}\n"
    else:
        msg += "📊 4H: ─ (datos no disponibles)\n"
    
    # 1H Timeframe
    if mtf.tf_1h:
        trend_icon = "▲" if mtf.tf_1h.candle_trend == 'BULLISH' or 'ALCISTA' in mtf.tf_1h.trend else ("▼" if mtf.tf_1h.candle_trend == 'BEARISH' or 'BAJISTA' in mtf.tf_1h.trend else "▬")
        trend_text = "ALCISTA" if mtf.tf_1h.candle_trend == 'BULLISH' or 'ALCISTA' in mtf.tf_1h.trend else ("BAJISTA" if mtf.tf_1h.candle_trend == 'BEARISH' or 'BAJISTA' in mtf.tf_1h.trend else "LATERAL")
        msg += f"📊 1H: {trend_icon} {trend_text}\n"
        if mtf.tf_1h.candle_colors:
            msg += f"   Velas: {mtf.tf_1h.candle_colors}\n"
    else:
        msg += "📊 1H: ─ (datos no disponibles)\n"
    
    # 15m Timeframe (KEY CONFIRMATION)
    if mtf.tf_15m:
        candle_data = mtf.candle_confirmation_15m
        consecutive = max(candle_data.get('consecutive_green', 0), candle_data.get('consecutive_red', 0))
        
        if candle_data.get('trend_change') == 'BULLISH':
            msg += f"📊 15m: ▲ {consecutive} velas VERDES\n"
        elif candle_data.get('trend_change') == 'BEARISH':
            msg += f"📊 15m: ▼ {consecutive} velas ROJAS\n"
        else:
            msg += f"📊 15m: ▬ Sin tendencia clara\n"
        
        if mtf.tf_15m.candle_colors:
            msg += f"   Velas: {mtf.tf_15m.candle_colors}\n"
        
        # Show confirmation status
        if candle_data.get('confirmed', False):
            msg += f"   ✅ Confirmado (3+ velas)\n"
        elif consecutive > 0:
            msg += f"   ⏳ Esperando ({consecutive}/3 velas)\n"
    
    msg += "\n"
    
    # ========== MAIN SIGNAL ==========
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    
    if mtf.should_trade:
        if mtf.trade_direction == "LONG":
            msg += "┏━ SEÑAL: COMPRA / LONG ▲\n\n"
        else:
            msg += "┏━ SEÑAL: VENTA / SHORT ▼\n\n"
        
        msg += f"Confianza: {mtf.confidence}%\n"
        msg += f"Razón: {mtf.reason}\n\n"
        
        # Entry/exit levels
        msg += "📊 Niveles:\n"
        msg += f"  Entrada → {format_price(strategy['entry'])}\n"
        msg += f"  Stop    → {format_price(strategy['sl'])}\n"
        msg += f"  Target  → {format_price(strategy['tp1'])}\n\n"
    else:
        msg += "┏━ SEÑAL: ESPERAR ⏳\n\n"
        msg += f"{mtf.reason}\n\n"
    
    # Warnings
    if mtf.warnings:
        msg += "⚠️ Advertencias:\n"
        for w in mtf.warnings:
            msg += f"  {w}\n"
        msg += "\n"
    
    # MA7/MA25 info (secondary)
    msg += "━━━ MA7/MA25 (15m) ━━━\n"
    msg += f"MA7:  {format_price(mtf.ma_crossover['ma7'])}\n"
    msg += f"MA25: {format_price(mtf.ma_crossover['ma25'])}\n"
    
    msg += f"\n┗━━━━━━━━━━━━━━━━━━━━"
    
    return msg
