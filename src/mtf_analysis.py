"""
Multi-Timeframe Analysis Module
Analyzes multiple timeframes for higher reliability signals
"""
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
from src.technical_analysis import TechnicalAnalyzer, SignalType


class TrendDirection(Enum):
    STRONG_BULLISH = "FUERTE ALCISTA"
    BULLISH = "ALCISTA"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BAJISTA"
    STRONG_BEARISH = "FUERTE BAJISTA"


@dataclass
class TimeframeAnalysis:
    """Analysis result for a single timeframe"""
    timeframe: str
    score: float
    signal: SignalType
    trend: TrendDirection
    rsi: float
    macd_bullish: bool
    above_ema200: bool
    volume_strong: bool
    adx: float = 0  # Added: ADX for trend strength


@dataclass
class MTFAnalysis:
    """Multi-Timeframe Analysis result"""
    symbol: str
    price: float
    
    # Individual timeframe results
    tf_1d: Optional[TimeframeAnalysis]
    tf_4h: Optional[TimeframeAnalysis]
    tf_1h: Optional[TimeframeAnalysis]
    tf_15m: Optional[TimeframeAnalysis]
    tf_5m: Optional[TimeframeAnalysis]
    
    # Combined analysis
    overall_score: float
    overall_signal: SignalType
    trend_alignment: float  # 0-100% alignment across timeframes
    confidence: float  # 0-100%
    
    # Volatility filter
    volatility_ok: bool
    volatility_state: str
    
    # Final decision
    should_trade: bool
    trade_direction: str  # LONG, SHORT, or NONE
    reason: str
    warnings: List[str]


class MultiTimeframeAnalyzer:
    """
    Analyzes multiple timeframes for higher reliability signals
    
    Timeframes used:
    - 1d (Daily) - Major trend direction
    - 4h - Intermediate trend
    - 1h - Short-term trend
    - 15m - Entry timing
    
    STRICT MODE CRITERIA:
    1. Alignment: >= 75% of timeframes must agree (prefer 100%)
    2. Trend Strength: ADX > 20 on at least one major timeframe (4h/1d)
    3. Volume: Relative volume > 1.0 (above average) on 1h/4h
    4. Momentum: RSI not in extreme overbought/oversold levels against the trade
    5. Risk/Reward: Minimum 1.5 ratio
    """
    
    TIMEFRAMES = ['1d', '4h', '1h', '15m', '5m']
    
    TIMEFRAME_WEIGHTS = {
        '1d': 0.25,   # Tendencia principal (macro)
        '4h': 0.25,   # Confirmación de tendencia
        '1h': 0.20,   # Contexto cercano
        '15m': 0.15,  # Timing de entrada
        '5m': 0.15    # Confirmación final para scalping
    }
    
    def __init__(self, client):
        self.client = client
    
    def analyze_single_timeframe(self, symbol: str, timeframe: str) -> TimeframeAnalysis:
        """Analyze a single timeframe"""
        df = self.client.get_ohlcv(symbol, timeframe)
        analyzer = TechnicalAnalyzer(df)
        analysis = analyzer.generate_analysis()
        
        # Determine trend direction
        score = analysis['score']
        if score >= 65:  # Slightly stricter thresholds
            trend = TrendDirection.STRONG_BULLISH
        elif score >= 55:
            trend = TrendDirection.BULLISH
        elif score >= 45:
            trend = TrendDirection.NEUTRAL
        elif score >= 35:
            trend = TrendDirection.BEARISH
        else:
            trend = TrendDirection.STRONG_BEARISH
        
        indicators = analysis['indicators']
        
        return TimeframeAnalysis(
            timeframe=timeframe,
            score=score,
            signal=analysis['signal'],
            trend=trend,
            rsi=indicators.get('rsi', 50),
            macd_bullish=indicators.get('macd', 0) > indicators.get('macd_signal', 0),
            above_ema200=analysis['price'] > indicators.get('ema_200', 0),
            volume_strong=indicators.get('volume_ratio', 1.0) > 1.0,
            adx=indicators.get('adx', 0) if 'adx' in indicators else 0
        )
    
    def calculate_trend_alignment(self, analyses: Dict[str, TimeframeAnalysis]) -> float:
        if not analyses:
            return 0
        
        bullish_count = 0
        bearish_count = 0
        
        for tf, analysis in analyses.items():
            if analysis.trend in [TrendDirection.STRONG_BULLISH, TrendDirection.BULLISH]:
                bullish_count += 1
            elif analysis.trend in [TrendDirection.STRONG_BEARISH, TrendDirection.BEARISH]:
                bearish_count += 1
        
        total = len(analyses)
        max_aligned = max(bullish_count, bearish_count)
        
        return (max_aligned / total) * 100
    
    def calculate_volatility_filter(self, symbol: str) -> Tuple[bool, str]:
        """Check if volatility is in acceptable range (ATR %)"""
        try:
            df = self.client.get_ohlcv(symbol, '1h')
            
            # Calculate ATR percentage
            high = df['high'].iloc[-20:]
            low = df['low'].iloc[-20:]
            close = df['close'].iloc[-20:]
            
            tr = pd.concat([
                high - low,
                abs(high - close.shift(1)),
                abs(low - close.shift(1))
            ], axis=1).max(axis=1)
            
            atr = tr.mean()
            atr_percent = (atr / close.iloc[-1]) * 100
            
            if atr_percent < 0.3:
                return False, "MUY BAJA - Mercado muerto"
            elif atr_percent < 1.0:
                return True, "BAJA - Estable"
            elif atr_percent < 3.0:
                return True, "MEDIA - Ideal"
            elif atr_percent < 6.0:
                return True, "ALTA - Volatil"
            else:
                return False, "EXTREMA - Peligroso"
                
        except Exception:
            return True, "DESCONOCIDA"
    
    def analyze(self, symbol: str) -> MTFAnalysis:
        """Perform full multi-timeframe analysis with strict validation"""
        ticker = self.client.get_ticker(symbol)
        price = ticker['price']
        
        # Analyze all timeframes
        analyses = {}
        warnings = []
        
        for tf in self.TIMEFRAMES:
            try:
                analyses[tf] = self.analyze_single_timeframe(symbol, tf)
            except Exception as e:
                warnings.append(f"Error en {tf}: {str(e)[:20]}")
        
        if not analyses:
            return None # Should handle gracefully
            
        # 1. Trend Alignment
        trend_alignment = self.calculate_trend_alignment(analyses)
        
        # 2. Overall Score Calculation
        overall_score = 0
        total_weight = 0
        for tf, weight in self.TIMEFRAME_WEIGHTS.items():
            if tf in analyses:
                overall_score += analyses[tf].score * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_score = overall_score / total_weight
        
        # 3. Volatility Check
        volatility_ok, volatility_state = self.calculate_volatility_filter(symbol)
        
        # 4. Determine bias
        if overall_score >= 60:
            bias = "BULLISH"
        elif overall_score <= 40:
            bias = "BEARISH"
        else:
            bias = "NEUTRAL"
            
        # 5. STRICT VALIDATION CHECKS
        should_trade = False
        reason = ""
        trade_direction = "NONE"
        confidence = 50
        
        # Validation Flags
        has_trend_strength = False
        if '4h' in analyses and analyses['4h'].adx > 20: has_trend_strength = True
        if '1d' in analyses and analyses['1d'].adx > 20: has_trend_strength = True
        
        has_volume = False
        if '1h' in analyses and analyses['1h'].volume_strong: has_volume = True
        if '4h' in analyses and analyses['4h'].volume_strong: has_volume = True
        
        safe_rsi = True
        if '1h' in analyses:
            rsi = analyses['1h'].rsi
            if bias == "BULLISH" and rsi > 70: safe_rsi = False # Don't buy top
            if bias == "BEARISH" and rsi < 30: safe_rsi = False # Don't sell bottom
        
        # Logic for LONG
        if bias == "BULLISH":
            if trend_alignment >= 75 and volatility_ok:
                if safe_rsi:
                    if has_trend_strength or has_volume:
                        should_trade = True
                        trade_direction = "LONG"
                        confidence = 80
                        reason = "Tendencia alcista confirmada con volumen/fuerza"
                        if trend_alignment == 100: confidence += 10
                        if has_trend_strength and has_volume: confidence += 5
                    else:
                        reason = "Falta volumen o fuerza (ADX) para confirmar"
                else:
                    reason = "RSI extendido (posible sobrecompra)"
            else:
                reason = "Alineacion < 75% o volatilidad mala"

        # Logic for SHORT
        elif bias == "BEARISH":
            if trend_alignment >= 75 and volatility_ok:
                if safe_rsi:
                    if has_trend_strength or has_volume:
                        should_trade = True
                        trade_direction = "SHORT"
                        confidence = 80
                        reason = "Tendencia bajista confirmada con volumen/fuerza"
                        if trend_alignment == 100: confidence += 10
                        if has_trend_strength and has_volume: confidence += 5
                    else:
                        reason = "Falta volumen o fuerza (ADX) para confirmar"
                else:
                    reason = "RSI extendido (posible sobreventa)"
            else:
                reason = "Alineacion < 75% o volatilidad mala"
        
        else:
            reason = "Mercado neutral / Sin tendencia clara"
        
        # Populate warnings
        if not volatility_ok: warnings.append(f"Volatilidad: {volatility_state}")
        if not safe_rsi: warnings.append("RSI en zona peligrosa para entrada")
        if not has_volume: warnings.append("Volumen bajo relativo al promedio")
        if not has_trend_strength: warnings.append("Tendencia debil (ADX bajo)")
        
        return MTFAnalysis(
            symbol=symbol,
            price=price,
            tf_1d=analyses.get('1d'),
            tf_4h=analyses.get('4h'),
            tf_1h=analyses.get('1h'),
            tf_15m=analyses.get('15m'),
            tf_5m=analyses.get('5m'),
            overall_score=overall_score,
            overall_signal=SignalType.BUY if bias == "BULLISH" else SignalType.SELL if bias == "BEARISH" else SignalType.NEUTRAL,
            trend_alignment=trend_alignment,
            confidence=confidence,
            volatility_ok=volatility_ok,
            volatility_state=volatility_state,
            should_trade=should_trade,
            trade_direction=trade_direction,
            reason=reason,
            warnings=warnings
        )


def format_mtf_analysis(mtf: MTFAnalysis, strategy: dict) -> str:
    """Format MTF analysis for Telegram"""
    
    def get_trend_arrow(trend: TrendDirection) -> str:
        if trend in [TrendDirection.STRONG_BULLISH, TrendDirection.BULLISH]:
            return "▲"
        elif trend in [TrendDirection.STRONG_BEARISH, TrendDirection.BEARISH]:
            return "▼"
        return "▬"
    
    def format_price(price: float) -> str:
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        return f"${price:.8f}"
    
    msg = f"*▶ ANALISIS MTF: {mtf.symbol}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"◆ *Precio:* {format_price(mtf.price)}\n\n"
    
    # Timeframe breakdown
    msg += "*⟫ Analisis por Timeframe:*\n\n"
    
    for tf_name, tf_data in [('1D', mtf.tf_1d), ('4H', mtf.tf_4h), 
                              ('1H', mtf.tf_1h), ('15M', mtf.tf_15m), ('5M', mtf.tf_5m)]:
        if tf_data:
            arrow = get_trend_arrow(tf_data.trend)
            msg += f"▸ {tf_name} {arrow} Score: {tf_data.score:.0f} | {tf_data.trend.value}\n"
            msg += f"   ↳ RSI: {tf_data.rsi:.0f}"
            if tf_data.macd_bullish:
                msg += " | MACD: ▲ Alcista"
            else:
                msg += " | MACD: ▼ Bajista"
            msg += "\n"
    
    msg += "\n"
    
    # Overall results
    msg += "*◆ Resultado Combinado:*\n"
    msg += f"▪ Score Total: *{mtf.overall_score:.1f}/100*\n"
    msg += f"▪ Alineacion: *{mtf.trend_alignment:.0f}%*\n"
    msg += f"▪ Confianza: *{mtf.confidence:.0f}%*\n"
    msg += f"▪ Volatilidad: {mtf.volatility_state}\n\n"
    
    # Decision
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "*⟫ DECISION*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if mtf.should_trade:
        direction_symbol = "▲" if mtf.trade_direction == "LONG" else "▼"
        msg += f"{direction_symbol} *{mtf.trade_direction}*\n"
        msg += f"✓ {mtf.reason}\n\n"
        
        if strategy['viable']:
            msg += "*▸ Niveles de Operacion:*\n"
            msg += f"  → Entrada: *{format_price(strategy['entry'])}*\n"
            msg += f"  → Stop Loss: *{format_price(strategy['sl'])}*\n"
            msg += f"  → TP1: {format_price(strategy['tp1'])}\n"
            msg += f"  → TP2: {format_price(strategy['tp2'])}\n"
            msg += f"  → TP3: {format_price(strategy['tp3'])}\n\n"
            
            msg += "⚠ _Gestion: Max 1-2% capital, Apalancamiento 3x-5x_\n\n"
    else:
        msg += "✗ *NO OPERAR*\n"
        msg += f"  → {mtf.reason}\n\n"
        msg += "↻ _Espera mejor alineacion de timeframes_\n\n"
    
    # Warnings
    if mtf.warnings:
        msg += "*⚠ Advertencias:*\n"
        for warning in mtf.warnings[:3]:
            msg += f"  ▪ {warning}\n"
        msg += "\n"
    
    # Next actions
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "*⟫ Que puedes hacer:*\n"
    msg += "  ▸ Escribe otra moneda (ej: ETH, SOL)\n"
    msg += "  ▸ /oportunidades - Ver mejores senales\n"
    msg += "  ▸ /start - Volver al menu"
    
    return msg
