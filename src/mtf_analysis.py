"""
Multi-Timeframe (MTF) Analysis Module - SIMPLIFIED VERSION
Analyzes multiple timeframes and combines them for better signals
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
    trend: str  # Using string instead of TrendDirection
    rsi: float
    macd_bullish: bool
    volume_ok: bool


@dataclass
class MTFAnalysis:
    """Results of multi-timeframe analysis"""
    symbol: str
    price: float
    tf_1d: Optional[TimeframeData]
    tf_4h: Optional[TimeframeData]
    tf_1h: Optional[TimeframeData]  # Keep for compatibility
    tf_15m: Optional[TimeframeData]
    tf_5m: Optional[TimeframeData]  # Keep for compatibility
    overall_score: float
    trend_alignment: float
    confidence: float
    volatility_ok: bool
    volatility_state: str
    should_trade: bool
    trade_direction: str
    reason: str
    warnings: List[str]


class MultiTimeframeAnalyzer:
    """Analyzes crypto across multiple timeframes"""
    
    def __init__(self, client):
        self.client = client
        
        # Timeframe weights (adjust these to change importance)
        self.tf_weights = {
            '1d': 0.25,   # 25% - Long term trend
            '4h': 0.25,   # 25% - Medium term confirmation
            '1h': 0.20,   # 20% - Short term trend
            '15m': 0.15,  # 15% - Entry timing
            '5m': 0.15    # 15% - Precise entry
        }
    
    def analyze(self, symbol: str) -> MTFAnalysis:
        """Analyze symbol across all timeframes"""
        
        # Analyze each timeframe (REDUCED TO 3 FOR SPEED)
        tf_results = {}
        analyzers = {}
        
        for tf in ['1d', '4h', '15m']:  # Only 3 timeframes instead of 5
            try:
                # Get OHLCV data for this timeframe
                df = self.client.get_ohlcv(symbol, tf)
                
                # Create analyzer with DataFrame
                analyzer = TechnicalAnalyzer(df)
                analysis = analyzer.generate_analysis()
                
                tf_results[tf] = TimeframeData(
                    timeframe=tf,
                    score=analysis['score'],
                    signal=analysis['signal'],
                    trend=analysis['trend']['direction'],  # Get string from trend dict
                    rsi=analysis['indicators']['rsi'] if analysis['indicators']['rsi'] else 50,
                    macd_bullish=analysis['indicators']['macd'] > 0 if analysis['indicators']['macd'] else False,
                    volume_ok=analysis['indicators']['volume_ratio'] > 1.0 if analysis['indicators']['volume_ratio'] else True
                )
                analyzers[tf] = analyzer
                
            except Exception as e:
                print(f"Error analyzing {tf}: {str(e)}")
                tf_results[tf] = None
        
        # Get current price
        ticker = self.client.get_ticker(symbol)
        current_price = ticker['price']
        
        # Calculate overall metrics
        overall_score = self._calculate_overall_score(tf_results)
        trend_alignment = self._calculate_trend_alignment(tf_results)
        confidence = self._calculate_confidence(tf_results, overall_score, trend_alignment)
        
        # Volatility check
        volatility_ok, volatility_state = self._check_volatility(tf_results)
        
        # Trading decision
        should_trade, direction, reason = self._make_decision(
            overall_score, trend_alignment, confidence, volatility_ok
        )
        
        # Collect warnings
        warnings = self._collect_warnings(tf_results, volatility_ok)
        
        return MTFAnalysis(
            symbol=symbol,
            price=current_price,
            tf_1d=tf_results.get('1d'),
            tf_4h=tf_results.get('4h'),
            tf_1h=None,  # Not analyzed for speed
            tf_15m=tf_results.get('15m'),
            tf_5m=None,  # Not analyzed for speed
            overall_score=overall_score,
            trend_alignment=trend_alignment,
            confidence=confidence,
            volatility_ok=volatility_ok,
            volatility_state=volatility_state,
            should_trade=should_trade,
            trade_direction=direction,
            reason=reason,
            warnings=warnings
        )
    
    def _calculate_overall_score(self, tf_results: Dict) -> float:
        """Calculate weighted average score across timeframes"""
        total_score = 0
        total_weight = 0
        
        for tf, weight in self.tf_weights.items():
            if tf_results.get(tf):
                total_score += tf_results[tf].score * weight
                total_weight += weight
        
        return (total_score / total_weight) if total_weight > 0 else 50
    
    def _calculate_trend_alignment(self, tf_results: Dict) -> float:
        """Calculate how aligned the trends are"""
        trends = []
        for tf_data in tf_results.values():
            if tf_data:
                if "ALCISTA" in tf_data.trend or "BULLISH" in tf_data.trend:
                    trends.append(1)
                elif "BAJISTA" in tf_data.trend or "BEARISH" in tf_data.trend:
                    trends.append(-1)
                else:
                    trends.append(0)
        
        if not trends:
            return 0
        
        # Perfect alignment = all same direction
        avg_trend = sum(trends) / len(trends)
        alignment = abs(avg_trend) * 100
        
        return alignment
    
    def _calculate_confidence(self, tf_results: Dict, score: float, alignment: float) -> float:
        """Calculate confidence level"""
        # Base confidence on score
        confidence = score
        
        # Boost for good alignment
        if alignment > 70:
            confidence += 10
        elif alignment > 50:
            confidence += 5
        
        # Reduce for poor alignment
        if alignment < 30:
            confidence -= 15
        
        # Cap at 100
        return min(100, max(0, confidence))
    
    def _check_volatility(self, tf_results: Dict) -> tuple:
        """Check volatility state"""
        # Use ATR from 1H timeframe as reference
        if tf_results.get('1h'):
            # Simple volatility check (can be improved)
            return True, "Normal"
        return True, "Unknown"
    
    def _make_decision(self, score: float, alignment: float, confidence: float, volatility_ok: bool) -> tuple:
        """Make trading decision"""
        
        # Minimum thresholds
        MIN_SCORE = 55
        MIN_ALIGNMENT = 40
        MIN_CONFIDENCE = 50
        
        # No trade conditions
        if score < MIN_SCORE:
            return False, "NEUTRAL", f"Score muy bajo ({score:.0f}/100)"
        
        if alignment < MIN_ALIGNMENT:
            return False, "NEUTRAL", f"Timeframes desalineados ({alignment:.0f}%)"
        
        if confidence < MIN_CONFIDENCE:
            return False, "NEUTRAL", f"Confianza baja ({confidence:.0f}%)"
        
        # Determine direction
        if score > 55:
            return True, "LONG", f"Señal alcista confirmada"
        elif score < 45:
            return True, "SHORT", f"Señal bajista confirmada"
        
        return False, "NEUTRAL", "Señal neutral, esperar"
    
    def _collect_warnings(self, tf_results: Dict, volatility_ok: bool) -> List[str]:
        """Collect any warnings"""
        warnings = []
        
        # Check for conflicting signals
        bullish_count = sum(1 for tf in tf_results.values() 
                           if tf and ("BULLISH" in tf.trend or "ALCISTA" in tf.trend))
        bearish_count = sum(1 for tf in tf_results.values() 
                           if tf and ("BEARISH" in tf.trend or "BAJISTA" in tf.trend))
        
        if bullish_count > 0 and bearish_count > 0:
            warnings.append("Señales mixtas en diferentes timeframes")
        
        if not volatility_ok:
            warnings.append("Alta volatilidad detectada")
        
        return warnings


def format_mtf_analysis(mtf: MTFAnalysis, strategy: dict) -> str:
    """Format MTF analysis for Telegram - ULTRA SIMPLIFIED"""
    
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
    
    msg += f"Precio: {format_price(mtf.price)}\n\n"
    
    # MAIN SIGNAL - SUPER CLEAR
    if mtf.should_trade:
        if mtf.trade_direction == "LONG":
            msg += "┏━ SEÑAL: COMPRA ▲\n\n"
        else:
            msg += "┏━ SEÑAL: VENTA ▼\n\n"
        
        msg += f"Confianza: {mtf.confidence:.0f}%\n\n"
        
        # Simple entry/exit levels
        msg += "Niveles:\n"
        msg += f"  Entrada → {format_price(strategy['entry'])}\n"
        msg += f"  Stop   → {format_price(strategy['sl'])}\n"
        msg += f"  Target → {format_price(strategy['tp1'])}\n\n"
    else:
        msg += "┏━ SEÑAL: ESPERAR\n\n"
        msg += f"{mtf.reason}\n\n"
    
    # Simple timeframes status
    msg += "Timeframes:\n"
    for tf_name, tf_data in[('1D', mtf.tf_1d), ('4H', mtf.tf_4h), ('15M', mtf.tf_15m)]:
        if tf_data:
            if "ALCISTA" in tf_data.trend or "BULLISH" in tf_data.trend:
                arrow = "▲"
            elif "BAJISTA" in tf_data.trend or "BEARISH" in tf_data.trend:
                arrow = "▼"
            else:
                arrow = "▬"
            msg += f"  {tf_name} {arrow}\n"
    
    msg += f"\n┗━━━━━━━━━━━━━━━━━━━━"
    
    return msg
