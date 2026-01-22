"""
Formatters Module
Format analysis output for CLI and Telegram
"""
from typing import Dict
from colorama import Fore, Back, Style, init
from src.technical_analysis import SignalType

# Initialize colorama for Windows support
init(autoreset=True)


class CLIFormatter:
    """Format analysis output for command-line interface with colors"""
    
    @staticmethod
    def format_analysis(symbol: str, analysis: Dict) -> str:
        """
        Format complete analysis for CLI output
        
        Args:
            symbol: Trading pair symbol
            analysis: Analysis dictionary from TechnicalAnalyzer
            
        Returns:
            Formatted string for console output
        """
        output = []
        
        # Header
        output.append("")
        output.append("=" * 80)
        output.append(f"{Fore.CYAN}{Style.BRIGHT}📊 ANÁLISIS TÉCNICO: {symbol}{Style.RESET_ALL}")
        output.append("=" * 80)
        output.append("")
        
        # Price and Score
        price = analysis['price']
        score = analysis['score']
        signal = analysis['signal']
        
        # Color based on signal
        if signal == SignalType.STRONG_BUY:
            signal_color = Fore.GREEN + Style.BRIGHT
            signal_emoji = "🚀"
        elif signal == SignalType.BUY:
            signal_color = Fore.GREEN
            signal_emoji = "📈"
        elif signal == SignalType.STRONG_SELL:
            signal_color = Fore.RED + Style.BRIGHT
            signal_emoji = "⚠️"
        elif signal == SignalType.SELL:
            signal_color = Fore.RED
            signal_emoji = "📉"
        else:
            signal_color = Fore.YELLOW
            signal_emoji = "➖"
        
        output.append(f"{Fore.WHITE}💰 Precio Actual: {Fore.CYAN}${price:,.2f}{Style.RESET_ALL}")
        output.append(f"{Fore.WHITE}📊 Score: {CLIFormatter._get_score_color(score)}{score}/100{Style.RESET_ALL}")
        output.append(f"{Fore.WHITE}🎯 Señal: {signal_color}{signal_emoji} {signal.value}{Style.RESET_ALL}")
        output.append("")
        
        # Trend Analysis
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ TENDENCIA ━━━{Style.RESET_ALL}")
        trend = analysis['trend']
        output.append(f"  Dirección: {CLIFormatter._get_trend_color(trend['direction'])}{trend['direction']}{Style.RESET_ALL}")
        output.append(f"  {Fore.WHITE}{trend['description']}{Style.RESET_ALL}")
        output.append("")
        
        # Momentum Analysis
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ MOMENTUM ━━━{Style.RESET_ALL}")
        momentum = analysis['momentum']
        output.append(f"  Estado: {CLIFormatter._get_momentum_color(momentum['state'])}{momentum['state']}{Style.RESET_ALL}")
        output.append(f"  {Fore.WHITE}{momentum['description']}{Style.RESET_ALL}")
        output.append("")
        
        # Volatility Analysis
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ VOLATILIDAD ━━━{Style.RESET_ALL}")
        volatility = analysis['volatility']
        output.append(f"  Estado: {Fore.CYAN}{volatility['state']}{Style.RESET_ALL}")
        output.append(f"  {Fore.WHITE}{volatility['description']}{Style.RESET_ALL}")
        output.append("")
        
        # Volume Analysis
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ VOLUMEN ━━━{Style.RESET_ALL}")
        volume = analysis['volume']
        output.append(f"  Estado: {Fore.CYAN}{volume['state']}{Style.RESET_ALL}")
        output.append(f"  {Fore.WHITE}{volume['description']}{Style.RESET_ALL}")
        output.append("")
        
        # Candlestick Patterns
        if analysis['patterns']:
            output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ PATRONES DE VELAS ━━━{Style.RESET_ALL}")
            for pattern in analysis['patterns']:
                output.append(f"  • {Fore.MAGENTA}{pattern}{Style.RESET_ALL}")
            output.append("")
        
        # Key Indicators
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ INDICADORES CLAVE ━━━{Style.RESET_ALL}")
        indicators = analysis['indicators']
        
        if indicators['rsi'] is not None:
            rsi_color = CLIFormatter._get_rsi_color(indicators['rsi'])
            output.append(f"  RSI(14): {rsi_color}{indicators['rsi']:.2f}{Style.RESET_ALL}")
        
        if indicators['macd'] is not None and indicators['macd_signal'] is not None:
            macd_color = Fore.GREEN if indicators['macd'] > indicators['macd_signal'] else Fore.RED
            output.append(f"  MACD: {macd_color}{indicators['macd']:.4f}{Style.RESET_ALL} | Signal: {indicators['macd_signal']:.4f}")
        
        output.append(f"  EMA(9): {Fore.CYAN}{indicators['ema_9']:,.2f}{Style.RESET_ALL}")
        output.append(f"  EMA(21): {Fore.CYAN}{indicators['ema_21']:,.2f}{Style.RESET_ALL}")
        output.append(f"  EMA(50): {Fore.CYAN}{indicators['ema_50']:,.2f}{Style.RESET_ALL}")
        output.append(f"  EMA(200): {Fore.CYAN}{indicators['ema_200']:,.2f}{Style.RESET_ALL}")
        
        if indicators['bb_upper'] and indicators['bb_lower']:
            output.append(f"  BB Superior: {Fore.CYAN}{indicators['bb_upper']:,.2f}{Style.RESET_ALL}")
            output.append(f"  BB Inferior: {Fore.CYAN}{indicators['bb_lower']:,.2f}{Style.RESET_ALL}")
        
        if indicators['volume_ratio']:
            vol_color = Fore.GREEN if indicators['volume_ratio'] > 1.5 else Fore.WHITE
            output.append(f"  Volumen Ratio: {vol_color}{indicators['volume_ratio']:.2f}x{Style.RESET_ALL}")
        
        output.append("")
        
        # Recommendation
        output.append(f"{Fore.YELLOW}{Style.BRIGHT}━━━ RECOMENDACIÓN ━━━{Style.RESET_ALL}")
        recommendation = CLIFormatter._get_recommendation(signal, score, analysis)
        output.append(f"  {Fore.WHITE}{recommendation}{Style.RESET_ALL}")
        output.append("")
        
        output.append("=" * 80)
        output.append("")
        
        return "\n".join(output)
    
    @staticmethod
    def format_opportunities(opportunities: list) -> str:
        """Format list of trading opportunities"""
        if not opportunities:
            return f"\n{Fore.YELLOW}No se encontraron oportunidades con el score mínimo requerido.{Style.RESET_ALL}\n"
        
        output = []
        output.append("")
        output.append("=" * 80)
        output.append(f"{Fore.CYAN}{Style.BRIGHT}🎯 OPORTUNIDADES DE TRADING{Style.RESET_ALL}")
        output.append("=" * 80)
        output.append("")
        
        for i, opp in enumerate(opportunities, 1):
            symbol = opp['symbol']
            score = opp['score']
            signal = opp['signal']
            price = opp['price']
            
            signal_emoji = "🚀" if signal == SignalType.STRONG_BUY else "📈"
            score_color = CLIFormatter._get_score_color(score)
            
            output.append(f"{Fore.WHITE}{i}. {Fore.CYAN}{Style.BRIGHT}{symbol}{Style.RESET_ALL}")
            output.append(f"   Precio: ${price:,.2f} | Score: {score_color}{score}/100{Style.RESET_ALL} | {signal_emoji} {signal.value}")
            output.append(f"   {Fore.WHITE}{opp['reason']}{Style.RESET_ALL}")
            output.append("")
        
        output.append("=" * 80)
        output.append("")
        
        return "\n".join(output)
    
    @staticmethod
    def format_top_list(title: str, items: list, sort_key: str) -> str:
        """Format top cryptocurrencies list"""
        output = []
        output.append("")
        output.append("=" * 80)
        output.append(f"{Fore.CYAN}{Style.BRIGHT}{title}{Style.RESET_ALL}")
        output.append("=" * 80)
        output.append("")
        
        for i, item in enumerate(items, 1):
            symbol = item['symbol']
            price = item['price']
            change = item['change_24h']
            volume = item['volume_24h']
            
            change_color = Fore.GREEN if change > 0 else Fore.RED
            change_sign = "+" if change > 0 else ""
            
            output.append(f"{Fore.WHITE}{i}. {Fore.CYAN}{Style.BRIGHT}{symbol}{Style.RESET_ALL}")
            output.append(f"   Precio: ${price:,.2f} | Cambio 24h: {change_color}{change_sign}{change:.2f}%{Style.RESET_ALL}")
            output.append(f"   Volumen 24h: ${volume:,.0f}")
            output.append("")
        
        output.append("=" * 80)
        output.append("")
        
        return "\n".join(output)
    
    @staticmethod
    def _get_score_color(score: float) -> str:
        """Get color based on score"""
        if score >= 70:
            return Fore.GREEN + Style.BRIGHT
        elif score >= 55:
            return Fore.GREEN
        elif score <= 30:
            return Fore.RED + Style.BRIGHT
        elif score <= 45:
            return Fore.RED
        else:
            return Fore.YELLOW
    
    @staticmethod
    def _get_trend_color(trend: str) -> str:
        """Get color based on trend"""
        if "ALCISTA" in trend:
            return Fore.GREEN + Style.BRIGHT
        elif "BAJISTA" in trend:
            return Fore.RED + Style.BRIGHT
        else:
            return Fore.YELLOW
    
    @staticmethod
    def _get_momentum_color(state: str) -> str:
        """Get color based on momentum state"""
        if "FUERTE ALCISTA" in state:
            return Fore.GREEN + Style.BRIGHT
        elif "ALCISTA" in state:
            return Fore.GREEN
        elif "FUERTE BAJISTA" in state:
            return Fore.RED + Style.BRIGHT
        elif "BAJISTA" in state:
            return Fore.RED
        else:
            return Fore.YELLOW
    
    @staticmethod
    def _get_rsi_color(rsi: float) -> str:
        """Get color based on RSI value"""
        if rsi < 30:
            return Fore.GREEN + Style.BRIGHT
        elif rsi < 40:
            return Fore.GREEN
        elif rsi > 70:
            return Fore.RED + Style.BRIGHT
        elif rsi > 60:
            return Fore.RED
        else:
            return Fore.YELLOW
    
    @staticmethod
    def _get_recommendation(signal: SignalType, score: float, analysis: Dict) -> str:
        """Generate trading recommendation"""
        if signal == SignalType.STRONG_BUY:
            return (
                f"🚀 SEÑAL FUERTE DE COMPRA (Score: {score}/100)\n"
                "  Esta es una excelente oportunidad de entrada. Múltiples indicadores confirman\n"
                "  tendencia alcista. Considera entrar con stop loss prudente."
            )
        elif signal == SignalType.BUY:
            return (
                f"📈 SEÑAL DE COMPRA (Score: {score}/100)\n"
                "  Los indicadores sugieren una oportunidad de compra. Espera confirmación adicional\n"
                "  o entrada escalonada. Usa stop loss."
            )
        elif signal == SignalType.STRONG_SELL:
            return (
                f"⚠️ SEÑAL FUERTE DE VENTA (Score: {score}/100)\n"
                "  Múltiples indicadores confirman debilidad. Considera salir de posiciones largas\n"
                "  o evaluar entradas cortas con gestión de riesgo."
            )
        elif signal == SignalType.SELL:
            return (
                f"📉 SEÑAL DE VENTA (Score: {score}/100)\n"
                "  Los indicadores sugieren debilidad. Precaución con nuevas entradas largas.\n"
                "  Considera tomar parciales si tienes posición."
            )
        else:
            return (
                f"➖ SEÑAL NEUTRAL (Score: {score}/100)\n"
                "  Sin señales claras en este momento. Espera mejor setup o busca otras\n"
                "  oportunidades con señales más definidas."
            )


class TelegramFormatter:
    """Format analysis output for Telegram messages"""
    
    @staticmethod
    def format_analysis(symbol: str, analysis: Dict) -> str:
        """Format analysis for Telegram with emojis and markdown"""
        price = analysis['price']
        score = analysis['score']
        signal = analysis['signal']
        
        # Signal emoji
        if signal == SignalType.STRONG_BUY:
            signal_emoji = "🚀"
        elif signal == SignalType.BUY:
            signal_emoji = "📈"
        elif signal == SignalType.STRONG_SELL:
            signal_emoji = "⚠️"
        elif signal == SignalType.SELL:
            signal_emoji = "📉"
        else:
            signal_emoji = "➖"
        
        # Build message
        message = f"📊 *ANÁLISIS TÉCNICO: {symbol}*\n\n"
        message += f"💰 *Precio:* ${price:,.2f}\n"
        message += f"📊 *Score:* {score}/100\n"
        message += f"🎯 *Señal:* {signal_emoji} *{signal.value}*\n\n"
        
        # Trend
        message += f"*📈 TENDENCIA*\n"
        message += f"  • {analysis['trend']['direction']}\n"
        message += f"  • {analysis['trend']['description']}\n\n"
        
        # Momentum
        message += f"*⚡ MOMENTUM*\n"
        message += f"  • {analysis['momentum']['state']}\n"
        message += f"  • {analysis['momentum']['description']}\n\n"
        
        # Patterns
        if analysis['patterns']:
            message += f"*🕯 PATRONES*\n"
            for pattern in analysis['patterns']:
                message += f"  • {pattern}\n"
            message += "\n"
        
        # Key indicators
        message += f"*📊 INDICADORES CLAVE*\n"
        indicators = analysis['indicators']
        if indicators['rsi'] is not None:
            message += f"  • RSI: {indicators['rsi']:.1f}\n"
        if indicators['macd'] is not None:
            message += f"  • MACD: {indicators['macd']:.4f}\n"
        message += f"  • EMA(9): ${indicators['ema_9']:,.2f}\n"
        message += f"  • EMA(200): ${indicators['ema_200']:,.2f}\n\n"
        
        # Recommendation
        message += TelegramFormatter._get_recommendation(signal, score)
        
        return message
    
    @staticmethod
    def _get_recommendation(signal: SignalType, score: float) -> str:
        """Generate recommendation for Telegram"""
        if signal == SignalType.STRONG_BUY:
            return f"✅ *RECOMENDACIÓN:* Excelente oportunidad de compra (Score: {score}/100)"
        elif signal == SignalType.BUY:
            return f"👍 *RECOMENDACIÓN:* Buena oportunidad de compra (Score: {score}/100)"
        elif signal == SignalType.STRONG_SELL:
            return f"🛑 *RECOMENDACIÓN:* Evitar compras, considerar salidas (Score: {score}/100)"
        elif signal == SignalType.SELL:
            return f"⚠️ *RECOMENDACIÓN:* Precaución, debilidad detectada (Score: {score}/100)"
        else:
            return f"⏸ *RECOMENDACIÓN:* Esperar mejores señales (Score: {score}/100)"
