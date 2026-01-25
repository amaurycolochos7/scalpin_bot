"""
Multi-Timeframe (MTF) Analysis Module - MA7/MA25 STRATEGY
Based on friend's trading strategy:
- Primary signal: MA7/MA25 crossover on 15-minute timeframe
- Confirmation: TradingView 10 indicators (7/10 rule)
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


@dataclass
class MTFAnalysis:
    """Results of multi-timeframe analysis with MA7/MA25 strategy"""
    symbol: str
    price: float
    
    # Timeframe data
    tf_15m: Optional[TimeframeData]
    tf_1h: Optional[TimeframeData]
    tf_4h: Optional[TimeframeData]
    
    # MA7/MA25 Crossover (PRIMARY SIGNAL)
    ma_crossover: dict
    
    # TradingView 10 Indicators (CONFIRMATION)
    tv_votes: dict
    
    # Final Decision
    should_trade: bool
    trade_direction: str  # 'LONG', 'SHORT', or 'NEUTRAL'
    confidence: int  # Percentage based on indicator votes
    reason: str
    warnings: List[str]


class MultiTimeframeAnalyzer:
    """Analyzes crypto using MA7/MA25 crossover strategy with TradingView confirmation"""
    
    def __init__(self, client):
        self.client = client
        # Primary timeframe is 15 minutes (as friend recommended)
        self.primary_tf = '15m'
    
    def analyze(self, symbol: str) -> MTFAnalysis:
        """
        Analyze symbol using MA7/MA25 strategy
        
        Strategy:
        1. Get MA7/MA25 crossover on 15m timeframe (PRIMARY SIGNAL)
        2. Get TradingView 10-indicator votes (CONFIRMATION)
        3. If crossover + 7/10 indicators agree = TRADE
        """
        
        # Get data for 15m (primary) timeframe
        df_15m = self.client.get_ohlcv(symbol, '15m')
        analyzer_15m = TechnicalAnalyzer(df_15m)
        analyzer_15m.calculate_all_indicators()
        
        # Get MA7/MA25 crossover (PRIMARY SIGNAL)
        ma_crossover = analyzer_15m.detect_ma_crossover()
        
        # Get TradingView 10-indicator votes (CONFIRMATION)
        tv_votes = analyzer_15m.get_tradingview_votes()
        
        # Get analysis data for display
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
            ma25=ma_crossover['ma25']
        )
        
        # Get 1h and 4h for additional context (optional)
        tf_1h_data = None
        tf_4h_data = None
        
        try:
            df_1h = self.client.get_ohlcv(symbol, '1h')
            analyzer_1h = TechnicalAnalyzer(df_1h)
            analyzer_1h.calculate_all_indicators()
            ma_1h = analyzer_1h.detect_ma_crossover()
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
                ma25=ma_1h['ma25']
            )
        except:
            pass
        
        try:
            df_4h = self.client.get_ohlcv(symbol, '4h')
            analyzer_4h = TechnicalAnalyzer(df_4h)
            analyzer_4h.calculate_all_indicators()
            ma_4h = analyzer_4h.detect_ma_crossover()
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
                ma25=ma_4h['ma25']
            )
        except:
            pass
        
        # Get current price
        ticker = self.client.get_ticker(symbol)
        current_price = ticker['price']
        
        # Make trading decision
        should_trade, direction, confidence, reason = self._make_decision(
            ma_crossover, tv_votes, tf_1h_data, tf_4h_data
        )
        
        # Collect warnings
        warnings = self._collect_warnings(ma_crossover, tv_votes, tf_1h_data, tf_4h_data)
        
        return MTFAnalysis(
            symbol=symbol,
            price=current_price,
            tf_15m=tf_15m_data,
            tf_1h=tf_1h_data,
            tf_4h=tf_4h_data,
            ma_crossover=ma_crossover,
            tv_votes=tv_votes,
            should_trade=should_trade,
            trade_direction=direction,
            confidence=confidence,
            reason=reason,
            warnings=warnings
        )
    
    def _make_decision(self, ma_crossover: dict, tv_votes: dict, 
                       tf_1h: Optional[TimeframeData], tf_4h: Optional[TimeframeData]) -> tuple:
        """
        Make trading decision based on:
        1. MA7/MA25 crossover (primary)
        2. TradingView 10-indicator votes (confirmation with 7/10 rule)
        3. Higher timeframe alignment (bonus)
        """
        
        ma_signal = ma_crossover['signal']
        tv_signal = tv_votes['signal']
        long_votes = tv_votes['long_count']
        short_votes = tv_votes['short_count']
        
        # Calculate confidence based on votes
        max_votes = max(long_votes, short_votes)
        confidence = int((max_votes / 10) * 100)
        
        # CASE 1: Fresh crossover detected (strongest signal)
        if ma_signal == 'LONG':
            if long_votes >= 6:  # 6/10 or more confirms
                return True, 'LONG', confidence, f'🟢 CRUCE ALCISTA + {long_votes}/10 indicadores confirman'
            else:
                return True, 'LONG', confidence, f'🟢 CRUCE ALCISTA (solo {long_votes}/10 confirman)'
        
        if ma_signal == 'SHORT':
            if short_votes >= 6:  # 6/10 or more confirms
                return True, 'SHORT', confidence, f'🔴 CRUCE BAJISTA + {short_votes}/10 indicadores confirman'
            else:
                return True, 'SHORT', confidence, f'🔴 CRUCE BAJISTA (solo {short_votes}/10 confirman)'
        
        # CASE 2: In existing trend (MA7 above/below MA25)
        if ma_signal == 'LONG_TREND':
            if long_votes >= 7:  # 7/10 rule
                return True, 'LONG', confidence, f'📈 Tendencia ALCISTA + {long_votes}/10 indicadores'
            elif long_votes >= 5:
                return False, 'LONG', confidence, f'📈 Tendencia alcista pero solo {long_votes}/10'
            else:
                return False, 'NEUTRAL', confidence, f'Tendencia mixta ({long_votes} LONG vs {short_votes} SHORT)'
        
        if ma_signal == 'SHORT_TREND':
            if short_votes >= 7:  # 7/10 rule
                return True, 'SHORT', confidence, f'📉 Tendencia BAJISTA + {short_votes}/10 indicadores'
            elif short_votes >= 5:
                return False, 'SHORT', confidence, f'📉 Tendencia bajista pero solo {short_votes}/10'
            else:
                return False, 'NEUTRAL', confidence, f'Tendencia mixta ({long_votes} LONG vs {short_votes} SHORT)'
        
        # CASE 3: No clear signal
        return False, 'NEUTRAL', confidence, 'Sin señal clara - ESPERAR'
    
    def _collect_warnings(self, ma_crossover: dict, tv_votes: dict,
                          tf_1h: Optional[TimeframeData], tf_4h: Optional[TimeframeData]) -> List[str]:
        """Collect warnings for the user"""
        warnings = []
        
        # Check if higher timeframes disagree
        ma_signal = ma_crossover['signal']
        
        if tf_1h and tf_4h:
            # Check 1h alignment
            if 'LONG' in ma_signal and 'BAJISTA' in tf_1h.trend:
                warnings.append("⚠️ 1H muestra tendencia BAJISTA")
            elif 'SHORT' in ma_signal and 'ALCISTA' in tf_1h.trend:
                warnings.append("⚠️ 1H muestra tendencia ALCISTA")
            
            # Check 4h alignment
            if 'LONG' in ma_signal and 'BAJISTA' in tf_4h.trend:
                warnings.append("⚠️ 4H muestra tendencia BAJISTA")
            elif 'SHORT' in ma_signal and 'ALCISTA' in tf_4h.trend:
                warnings.append("⚠️ 4H muestra tendencia ALCISTA")
        
        # Check if indicators are split
        long_votes = tv_votes['long_count']
        short_votes = tv_votes['short_count']
        if abs(long_votes - short_votes) <= 2:
            warnings.append("⚠️ Indicadores muy divididos")
        
        return warnings


def format_mtf_analysis(mtf: MTFAnalysis, strategy: dict) -> str:
    """Format MTF analysis for Telegram with MA7/MA25 strategy display"""
    
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
    
    # MA7/MA25 STATUS
    msg += "━━━ MA7/MA25 (15m) ━━━\n"
    msg += f"{mtf.ma_crossover['description']}\n"
    msg += f"MA7: {format_price(mtf.ma_crossover['ma7'])}\n"
    msg += f"MA25: {format_price(mtf.ma_crossover['ma25'])}\n\n"
    
    # TRADINGVIEW INDICATORS (10 votes)
    msg += "━━━ Indicadores TradingView ━━━\n"
    long_votes = mtf.tv_votes['long_count']
    short_votes = mtf.tv_votes['short_count']
    neutral = mtf.tv_votes['neutral_count']
    
    # Visual vote bar
    bar_long = "🟢" * long_votes
    bar_short = "🔴" * short_votes
    bar_neutral = "⚪" * neutral
    
    msg += f"LONG: {long_votes}  {bar_long}\n"
    msg += f"SHORT: {short_votes}  {bar_short}\n"
    if neutral > 0:
        msg += f"NEUTRAL: {neutral}  {bar_neutral}\n"
    msg += "\n"
    
    # Individual votes breakdown
    msg += "Detalle:\n"
    for name, vote_data in mtf.tv_votes['votes'].items():
        vote = vote_data['vote']
        reason = vote_data['reason']
        if vote > 0:
            icon = "🟢"
        elif vote < 0:
            icon = "🔴"
        else:
            icon = "⚪"
        msg += f"  {icon} {name}: {reason}\n"
    msg += "\n"
    
    # MAIN SIGNAL
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    if mtf.should_trade:
        if mtf.trade_direction == "LONG":
            msg += "┏━ SEÑAL: COMPRA ▲\n\n"
        else:
            msg += "┏━ SEÑAL: VENTA ▼\n\n"
        
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
    
    # Higher timeframe context
    msg += "━━━ Contexto ━━━\n"
    if mtf.tf_1h:
        trend_icon = "▲" if "ALCISTA" in mtf.tf_1h.trend else ("▼" if "BAJISTA" in mtf.tf_1h.trend else "▬")
        msg += f"  1H: {trend_icon} {mtf.tf_1h.trend}\n"
    if mtf.tf_4h:
        trend_icon = "▲" if "ALCISTA" in mtf.tf_4h.trend else ("▼" if "BAJISTA" in mtf.tf_4h.trend else "▬")
        msg += f"  4H: {trend_icon} {mtf.tf_4h.trend}\n"
    
    msg += f"\n┗━━━━━━━━━━━━━━━━━━━━"
    
    return msg
