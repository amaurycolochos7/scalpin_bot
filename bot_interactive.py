"""
Interactive Trading Bot for Binance Futures
Premium Design with Professional Analysis
"""
import os
import sys
from colorama import Fore, Back, Style, init
from src.config import config
from src.binance_client import get_client, BinanceClient
from src.technical_analysis import TechnicalAnalyzer, SignalType
import time

# Initialize colorama
init(autoreset=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DESIGN CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Colors
C_TITLE = Fore.CYAN + Style.BRIGHT
C_SUBTITLE = Fore.YELLOW + Style.BRIGHT
C_TEXT = Fore.WHITE
C_DIM = Fore.LIGHTBLACK_EX
C_SUCCESS = Fore.GREEN + Style.BRIGHT
C_WARNING = Fore.YELLOW
C_ERROR = Fore.RED + Style.BRIGHT
C_ACCENT = Fore.MAGENTA + Style.BRIGHT
C_PRICE = Fore.CYAN
C_POSITIVE = Fore.GREEN
C_NEGATIVE = Fore.RED
C_NEUTRAL = Fore.YELLOW
R = Style.RESET_ALL

# Box drawing characters
BOX_TL = "╔"
BOX_TR = "╗"
BOX_BL = "╚"
BOX_BR = "╝"
BOX_H = "═"
BOX_V = "║"
BOX_T = "╦"
BOX_B = "╩"
BOX_L = "╠"
BOX_R = "╣"
BOX_X = "╬"

# Light box
LB_TL = "┌"
LB_TR = "┐"
LB_BL = "└"
LB_BR = "┘"
LB_H = "─"
LB_V = "│"

WIDTH = 78


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def center_text(text, width=WIDTH):
    """Center text within given width"""
    clean_text = text
    for color in [C_TITLE, C_SUBTITLE, C_TEXT, C_DIM, C_SUCCESS, C_WARNING, C_ERROR, 
                  C_ACCENT, C_PRICE, C_POSITIVE, C_NEGATIVE, C_NEUTRAL, R, 
                  Fore.CYAN, Fore.YELLOW, Fore.WHITE, Fore.GREEN, Fore.RED, Style.BRIGHT]:
        clean_text = clean_text.replace(str(color), '')
    padding = (width - len(clean_text)) // 2
    return ' ' * padding + text


def print_box_line(char_l, char_m, char_r, width=WIDTH):
    print(f"{C_TITLE}{char_l}{char_m * (width - 2)}{char_r}{R}")


def print_header():
    """Print stunning header"""
    clear_screen()
    print()
    print_box_line(BOX_TL, BOX_H, BOX_TR)
    print(f"{C_TITLE}{BOX_V}{R}{center_text('')}{C_TITLE}{BOX_V}{R}")
    print(f"{C_TITLE}{BOX_V}{R}{center_text(f'{C_SUBTITLE}🚀 TRADING BOT PRO 🚀{R}')}{C_TITLE}{BOX_V}{R}")
    print(f"{C_TITLE}{BOX_V}{R}{center_text(f'{C_TEXT}Binance Futures - Análisis Técnico Profesional{R}')}{C_TITLE}{BOX_V}{R}")
    print(f"{C_TITLE}{BOX_V}{R}{center_text('')}{C_TITLE}{BOX_V}{R}")
    print_box_line(BOX_BL, BOX_H, BOX_BR)
    print()


def print_menu():
    """Print beautiful main menu"""
    print(f"""
    {C_SUBTITLE}╭{'─' * 50}╮{R}
    {C_SUBTITLE}│{R}          {C_TITLE}📋  MENÚ  PRINCIPAL  📋{R}           {C_SUBTITLE}│{R}
    {C_SUBTITLE}╰{'─' * 50}╯{R}

    {C_SUCCESS}[1]{R}  📊  Analizar una moneda
         {C_DIM}Análisis completo con estrategia de trading{R}

    {C_SUCCESS}[2]{R}  🎯  Buscar oportunidades
         {C_DIM}Encuentra las mejores señales del mercado{R}

    {C_SUCCESS}[3]{R}  📈  Escaneo rápido
         {C_DIM}Vista general de las principales cryptos{R}

    {C_SUCCESS}[4]{R}  🔥  Top movers
         {C_DIM}Monedas más activas por volumen/cambio{R}

    {C_SUCCESS}[5]{R}  ⚙️   Configuración
         {C_DIM}Timeframe y parámetros{R}

    {C_ERROR}[0]{R}  ❌  Salir

""")


def get_signal_display(signal: SignalType, score: float) -> tuple:
    """Get signal display with emoji and color"""
    if signal == SignalType.STRONG_BUY:
        return "🚀 COMPRA FUERTE", C_SUCCESS, Back.GREEN + Fore.BLACK
    elif signal == SignalType.BUY:
        return "📈 COMPRA", C_POSITIVE, Back.GREEN + Fore.BLACK
    elif signal == SignalType.STRONG_SELL:
        return "⛔ VENTA FUERTE", C_ERROR, Back.RED + Fore.WHITE
    elif signal == SignalType.SELL:
        return "📉 VENTA", C_NEGATIVE, Back.RED + Fore.WHITE
    else:
        return "➖ NEUTRAL", C_NEUTRAL, Back.YELLOW + Fore.BLACK


def get_score_bar(score: float, width: int = 20) -> str:
    """Create a visual score bar"""
    filled = int((score / 100) * width)
    empty = width - filled
    
    if score >= 70:
        bar_color = C_SUCCESS
    elif score >= 55:
        bar_color = C_POSITIVE
    elif score <= 30:
        bar_color = C_ERROR
    elif score <= 45:
        bar_color = C_NEGATIVE
    else:
        bar_color = C_NEUTRAL
    
    bar = f"{bar_color}{'█' * filled}{C_DIM}{'░' * empty}{R}"
    return bar


def get_trading_strategy(analysis: dict, ticker: dict, atr: float) -> dict:
    """Generate complete trading strategy"""
    current_price = analysis['price']
    score = analysis['score']
    signal = analysis['signal']
    
    if atr is None or atr == 0:
        atr = current_price * 0.02
    
    strategy = {
        'viable': False,
        'action': 'ESPERAR',
        'reason': '',
        'entry': None,
        'stop_loss': None,
        'take_profit_1': None,
        'take_profit_2': None,
        'take_profit_3': None,
        'risk_reward': None,
        'position_bias': 'NEUTRAL',
        'confidence': 'BAJA',
        'confidence_pct': 0,
        'warnings': []
    }
    
    rsi = analysis['indicators'].get('rsi', 50)
    
    # LONG Strategy
    if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
        strategy['viable'] = True
        strategy['position_bias'] = 'LONG'
        
        if signal == SignalType.STRONG_BUY:
            strategy['action'] = 'COMPRAR (LONG)'
            strategy['confidence'] = 'ALTA'
            strategy['confidence_pct'] = min(95, score + 10)
            strategy['entry'] = current_price
            strategy['stop_loss'] = round(current_price - (atr * 1.5), 4)
            strategy['take_profit_1'] = round(current_price + (atr * 1.5), 4)
            strategy['take_profit_2'] = round(current_price + (atr * 2.5), 4)
            strategy['take_profit_3'] = round(current_price + (atr * 4), 4)
        else:
            strategy['action'] = 'CONSIDERAR LONG'
            strategy['confidence'] = 'MEDIA'
            strategy['confidence_pct'] = score
            strategy['entry'] = round(current_price - (atr * 0.3), 4)
            strategy['stop_loss'] = round(current_price - (atr * 2), 4)
            strategy['take_profit_1'] = round(current_price + (atr * 1.5), 4)
            strategy['take_profit_2'] = round(current_price + (atr * 2.5), 4)
            strategy['take_profit_3'] = round(current_price + (atr * 3.5), 4)
        
        risk = abs(strategy['entry'] - strategy['stop_loss'])
        reward = abs(strategy['take_profit_2'] - strategy['entry'])
        strategy['risk_reward'] = round(reward / risk, 2) if risk > 0 else 0
        strategy['reason'] = f"Múltiples indicadores alcistas confirmando señal de compra"
        
        if rsi and rsi > 65:
            strategy['warnings'].append(f"RSI alto ({rsi:.1f}) - considerar esperar pullback")
    
    # SHORT Strategy
    elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
        strategy['viable'] = True
        strategy['position_bias'] = 'SHORT'
        
        if signal == SignalType.STRONG_SELL:
            strategy['action'] = 'VENDER (SHORT)'
            strategy['confidence'] = 'ALTA'
            strategy['confidence_pct'] = min(95, 100 - score + 10)
            strategy['entry'] = current_price
            strategy['stop_loss'] = round(current_price + (atr * 1.5), 4)
            strategy['take_profit_1'] = round(current_price - (atr * 1.5), 4)
            strategy['take_profit_2'] = round(current_price - (atr * 2.5), 4)
            strategy['take_profit_3'] = round(current_price - (atr * 4), 4)
        else:
            strategy['action'] = 'CONSIDERAR SHORT'
            strategy['confidence'] = 'MEDIA'
            strategy['confidence_pct'] = 100 - score
            strategy['entry'] = round(current_price + (atr * 0.3), 4)
            strategy['stop_loss'] = round(current_price + (atr * 2), 4)
            strategy['take_profit_1'] = round(current_price - (atr * 1.5), 4)
            strategy['take_profit_2'] = round(current_price - (atr * 2.5), 4)
            strategy['take_profit_3'] = round(current_price - (atr * 3.5), 4)
        
        risk = abs(strategy['stop_loss'] - strategy['entry'])
        reward = abs(strategy['entry'] - strategy['take_profit_2'])
        strategy['risk_reward'] = round(reward / risk, 2) if risk > 0 else 0
        strategy['reason'] = f"Múltiples indicadores bajistas confirmando señal de venta"
        
        if rsi and rsi < 35:
            strategy['warnings'].append(f"RSI bajo ({rsi:.1f}) - considerar esperar rebote")
    
    else:
        strategy['viable'] = False
        strategy['action'] = 'NO OPERAR'
        strategy['confidence'] = 'N/A'
        strategy['confidence_pct'] = 0
        strategy['reason'] = f"Sin señales claras - Score neutral ({score:.1f}/100)"
        strategy['warnings'].append("No hay confirmación suficiente")
        strategy['warnings'].append("Busca otras monedas o espera mejor setup")
    
    return strategy


def format_price(price: float) -> str:
    """Format price based on its value"""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.6f}"


def print_analysis(symbol: str, analysis: dict, ticker: dict, strategy: dict):
    """Print beautiful analysis output"""
    
    price = analysis['price']
    score = analysis['score']
    signal = analysis['signal']
    signal_text, signal_color, signal_bg = get_signal_display(signal, score)
    
    # Main header
    print()
    print(f"    {C_TITLE}{'═' * 70}{R}")
    print(f"    {C_TITLE}║{R}  {C_SUBTITLE}📊 ANÁLISIS TÉCNICO PROFESIONAL{R}")
    print(f"    {C_TITLE}║{R}  {C_ACCENT}{symbol}{R}")
    print(f"    {C_TITLE}{'═' * 70}{R}")
    print()
    
    # Price and Score Box
    print(f"    {LB_TL}{LB_H * 68}{LB_TR}")
    print(f"    {LB_V}  {C_TEXT}💰 PRECIO:{R}     {C_PRICE}{format_price(price)}{R}")
    print(f"    {LB_V}")
    print(f"    {LB_V}  {C_TEXT}📊 SCORE:{R}      {get_score_bar(score)} {score:.1f}/100")
    print(f"    {LB_V}")
    print(f"    {LB_V}  {C_TEXT}🎯 SEÑAL:{R}      {signal_color}{signal_text}{R}")
    print(f"    {LB_V}")
    change = ticker['change_24h']
    change_color = C_POSITIVE if change > 0 else C_NEGATIVE
    change_sign = "+" if change > 0 else ""
    print(f"    {LB_V}  {C_TEXT}📈 24H:{R}        {change_color}{change_sign}{change:.2f}%{R}")
    print(f"    {LB_V}  {C_TEXT}📊 VOLUMEN:{R}    ${ticker['volume_24h']:,.0f}")
    print(f"    {LB_BL}{LB_H * 68}{LB_BR}")
    print()
    
    # Indicators Section
    print(f"    {C_SUBTITLE}▸ INDICADORES TÉCNICOS{R}")
    print(f"    {C_DIM}{'─' * 40}{R}")
    
    indicators = analysis['indicators']
    
    # RSI
    rsi = indicators.get('rsi')
    if rsi:
        if rsi < 30:
            rsi_status = f"{C_SUCCESS}OVERSOLD ✓{R}"
        elif rsi > 70:
            rsi_status = f"{C_ERROR}OVERBOUGHT ⚠{R}"
        elif rsi < 40:
            rsi_status = f"{C_POSITIVE}Bajo{R}"
        elif rsi > 60:
            rsi_status = f"{C_NEGATIVE}Alto{R}"
        else:
            rsi_status = f"{C_NEUTRAL}Neutral{R}"
        print(f"      RSI(14):     {C_PRICE}{rsi:.1f}{R}  {rsi_status}")
    
    # MACD
    macd = indicators.get('macd')
    macd_signal = indicators.get('macd_signal')
    if macd is not None and macd_signal is not None:
        macd_color = C_POSITIVE if macd > macd_signal else C_NEGATIVE
        macd_status = "Alcista ↑" if macd > macd_signal else "Bajista ↓"
        print(f"      MACD:        {macd_color}{macd:.4f}{R}  {macd_color}{macd_status}{R}")
    
    # EMAs
    print(f"      EMA(9):      {C_PRICE}{format_price(indicators['ema_9'])}{R}")
    print(f"      EMA(21):     {C_PRICE}{format_price(indicators['ema_21'])}{R}")
    print(f"      EMA(200):    {C_PRICE}{format_price(indicators['ema_200'])}{R}")
    
    # Bollinger
    if indicators.get('bb_upper') and indicators.get('bb_lower'):
        print(f"      BB Superior: {C_NEGATIVE}{format_price(indicators['bb_upper'])}{R}")
        print(f"      BB Inferior: {C_POSITIVE}{format_price(indicators['bb_lower'])}{R}")
    
    print()
    
    # Trend Analysis
    trend = analysis['trend']
    trend_color = C_POSITIVE if 'ALCISTA' in trend['direction'] else C_NEGATIVE if 'BAJISTA' in trend['direction'] else C_NEUTRAL
    print(f"    {C_SUBTITLE}▸ TENDENCIA{R}")
    print(f"    {C_DIM}{'─' * 40}{R}")
    print(f"      {trend_color}● {trend['direction']}{R}")
    print(f"      {C_DIM}{trend['description'][:60]}{R}")
    print()
    
    # Momentum
    momentum = analysis['momentum']
    mom_color = C_POSITIVE if 'ALCISTA' in momentum['state'] else C_NEGATIVE if 'BAJISTA' in momentum['state'] else C_NEUTRAL
    print(f"    {C_SUBTITLE}▸ MOMENTUM{R}")
    print(f"    {C_DIM}{'─' * 40}{R}")
    print(f"      {mom_color}● {momentum['state']}{R}")
    print(f"      {C_DIM}{momentum['description'][:60]}{R}")
    print()
    
    # Patterns
    if analysis['patterns']:
        print(f"    {C_SUBTITLE}▸ PATRONES DE VELAS{R}")
        print(f"    {C_DIM}{'─' * 40}{R}")
        for pattern in analysis['patterns']:
            print(f"      {C_ACCENT}⬢{R} {pattern}")
        print()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # STRATEGY SECTION
    # ═══════════════════════════════════════════════════════════════════════════
    
    if strategy['viable']:
        action_color = C_SUCCESS if strategy['position_bias'] == 'LONG' else C_ERROR
        
        print(f"    {C_TITLE}{'═' * 70}{R}")
        print(f"    {C_TITLE}║{R}  {C_SUBTITLE}🎯 ESTRATEGIA DE TRADING{R}")
        print(f"    {C_TITLE}{'═' * 70}{R}")
        print()
        
        # Action Box
        print(f"    {action_color}╭{'─' * 50}╮{R}")
        print(f"    {action_color}│{R}  {action_color}{Style.BRIGHT}{strategy['action']}{R}")
        print(f"    {action_color}│{R}")
        print(f"    {action_color}│{R}  Confianza: {C_SUCCESS if strategy['confidence'] in ['ALTA'] else C_WARNING}{strategy['confidence']} ({strategy['confidence_pct']:.0f}%){R}")
        print(f"    {action_color}│{R}  Posición:  {action_color}{strategy['position_bias']}{R}")
        print(f"    {action_color}│{R}  R/R Ratio: {C_SUCCESS if strategy['risk_reward'] >= 2 else C_WARNING}1:{strategy['risk_reward']}{R}")
        print(f"    {action_color}╰{'─' * 50}╯{R}")
        print()
        
        # Levels
        print(f"    {C_SUBTITLE}▸ NIVELES DE OPERACIÓN{R}")
        print(f"    {C_DIM}{'─' * 40}{R}")
        print(f"      {C_PRICE}➜{R}  Entrada:       {C_TEXT}{format_price(strategy['entry'])}{R}")
        print(f"      {C_ERROR}⬤{R}  Stop Loss:     {C_ERROR}{format_price(strategy['stop_loss'])}{R}")
        print()
        print(f"      {C_SUCCESS}◉{R}  Take Profit 1: {C_SUCCESS}{format_price(strategy['take_profit_1'])}{R}  {C_DIM}(cerrar 33%){R}")
        print(f"      {C_SUCCESS}◉{R}  Take Profit 2: {C_SUCCESS}{format_price(strategy['take_profit_2'])}{R}  {C_DIM}(cerrar 33%){R}")
        print(f"      {C_SUCCESS}◉{R}  Take Profit 3: {C_SUCCESS}{format_price(strategy['take_profit_3'])}{R}  {C_DIM}(cerrar 33%){R}")
        print()
        
        # Warnings
        if strategy['warnings']:
            print(f"    {C_WARNING}▸ ADVERTENCIAS{R}")
            print(f"    {C_DIM}{'─' * 40}{R}")
            for warning in strategy['warnings']:
                print(f"      {C_WARNING}⚠{R}  {warning}")
            print()
        
        # Tips
        print(f"    {C_SUBTITLE}▸ GESTIÓN DE RIESGO{R}")
        print(f"    {C_DIM}{'─' * 40}{R}")
        print(f"      {C_DIM}•{R} Arriesga máximo {C_WARNING}1-2%{R} de tu capital")
        print(f"      {C_DIM}•{R} Apalancamiento recomendado: {C_WARNING}3x-5x{R}")
        print(f"      {C_DIM}•{R} Mueve stop a {C_SUCCESS}breakeven{R} al llegar a TP1")
        print()
    
    else:
        # NOT VIABLE
        print(f"    {C_ERROR}{'═' * 70}{R}")
        print(f"    {C_ERROR}║{R}  {C_WARNING}⚠️  NO ES RECOMENDABLE OPERAR{R}")
        print(f"    {C_ERROR}{'═' * 70}{R}")
        print()
        print(f"    {C_TEXT}{strategy['reason']}{R}")
        print()
        for warning in strategy['warnings']:
            print(f"      {C_WARNING}•{R} {warning}")
        print()
        print(f"    {C_DIM}💡 Usa la opción 2 del menú para buscar mejores oportunidades{R}")
        print()


def analyze_single_coin(client: BinanceClient, timeframe: str):
    """Analyze a specific cryptocurrency"""
    print()
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print(f"    {C_TITLE}║{R}  {C_SUBTITLE}📊 ANÁLISIS DE MONEDA{R}")
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print()
    print(f"    {C_TEXT}Ingresa el símbolo de la criptomoneda:{R}")
    print(f"    {C_DIM}Ejemplos: BTC, ETH, SOL, LTC, DOGE, PEPE, etc.{R}")
    print()
    
    symbol_input = input(f"    {C_SUCCESS}➜{R}  Símbolo: ").strip()
    
    if not symbol_input:
        print(f"\n    {C_ERROR}❌ No ingresaste ningún símbolo{R}")
        return
    
    symbol = client.normalize_symbol(symbol_input)
    
    if symbol is None:
        print(f"\n    {C_ERROR}❌ '{symbol_input.upper()}' no existe en Binance Futures{R}")
        print(f"    {C_DIM}Verifica que esté disponible en la sección Futuros{R}")
        return
    
    display_symbol = client.get_display_symbol(symbol)
    
    print()
    print(f"    {C_PRICE}🔍 Analizando {display_symbol}...{R}")
    print(f"    {C_DIM}Timeframe: {timeframe}{R}")
    print()
    
    try:
        ticker = client.get_ticker(symbol)
        df = client.get_ohlcv(symbol, timeframe)
        analyzer = TechnicalAnalyzer(df)
        analysis = analyzer.generate_analysis()
        
        atr = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / 20
        strategy = get_trading_strategy(analysis, ticker, atr)
        
        print_analysis(display_symbol, analysis, ticker, strategy)
        
    except Exception as e:
        print(f"    {C_ERROR}❌ Error: {str(e)}{R}")


def find_opportunities(client: BinanceClient, timeframe: str, min_score: int):
    """Find best trading opportunities"""
    print()
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print(f"    {C_TITLE}║{R}  {C_SUBTITLE}🎯 BUSCANDO OPORTUNIDADES{R}")
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print()
    print(f"    {C_DIM}Timeframe: {timeframe} | Score mínimo: {min_score}/100{R}")
    print()
    
    opportunities = []
    total = len(config.TOP_SYMBOLS)
    
    for i, symbol in enumerate(config.TOP_SYMBOLS, 1):
        try:
            pct = int((i / total) * 30)
            bar = f"{C_SUCCESS}{'█' * pct}{C_DIM}{'░' * (30 - pct)}{R}"
            print(f"\r    {bar} {i}/{total} Analizando...", end="", flush=True)
            
            ticker = client.get_ticker(symbol)
            df = client.get_ohlcv(symbol, timeframe)
            analyzer = TechnicalAnalyzer(df)
            analysis = analyzer.generate_analysis()
            
            if analysis['score'] >= min_score and analysis['signal'] in [SignalType.STRONG_BUY, SignalType.BUY]:
                atr = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / 20
                strategy = get_trading_strategy(analysis, ticker, atr)
                
                opportunities.append({
                    'symbol': client.get_display_symbol(symbol),
                    'price': analysis['price'],
                    'score': analysis['score'],
                    'signal': analysis['signal'],
                    'change': ticker['change_24h'],
                    'strategy': strategy
                })
        except:
            continue
    
    print("\r" + " " * 60 + "\r", end="")
    
    if not opportunities:
        print(f"    {C_WARNING}⚠️  No se encontraron oportunidades con score >= {min_score}{R}")
        print(f"    {C_DIM}Intenta reducir el score mínimo en configuración{R}")
        return
    
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"    {C_SUCCESS}✓ Se encontraron {len(opportunities)} oportunidades{R}")
    print()
    
    for i, opp in enumerate(opportunities, 1):
        signal_text, signal_color, _ = get_signal_display(opp['signal'], opp['score'])
        change_color = C_POSITIVE if opp['change'] > 0 else C_NEGATIVE
        
        print(f"    {C_ACCENT}#{i}{R} {C_TITLE}{opp['symbol']}{R}")
        print(f"       Precio: {C_PRICE}{format_price(opp['price'])}{R}  |  24h: {change_color}{'+' if opp['change'] > 0 else ''}{opp['change']:.2f}%{R}")
        print(f"       Score:  {get_score_bar(opp['score'], 15)} {opp['score']:.1f}")
        print(f"       Señal:  {signal_color}{signal_text}{R}")
        print(f"       Entry:  {format_price(opp['strategy']['entry'])}  →  TP: {format_price(opp['strategy']['take_profit_2'])}")
        print()


def quick_scan(client: BinanceClient, timeframe: str):
    """Quick market scan"""
    print()
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print(f"    {C_TITLE}║{R}  {C_SUBTITLE}📈 ESCANEO RÁPIDO DEL MERCADO{R}")
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print()
    
    print(f"    {C_DIM}{'SÍMBOLO':<12} {'PRECIO':<14} {'24H':<10} {'SCORE':<8} {'SEÑAL':<15}{R}")
    print(f"    {C_DIM}{'─' * 60}{R}")
    
    for symbol in config.TOP_SYMBOLS:
        try:
            ticker = client.get_ticker(symbol)
            df = client.get_ohlcv(symbol, timeframe)
            analyzer = TechnicalAnalyzer(df)
            analysis = analyzer.generate_analysis()
            
            display = client.get_display_symbol(symbol)
            change_color = C_POSITIVE if ticker['change_24h'] > 0 else C_NEGATIVE
            signal_text, signal_color, _ = get_signal_display(analysis['signal'], analysis['score'])
            
            score = analysis['score']
            score_color = C_SUCCESS if score >= 60 else C_ERROR if score <= 40 else C_NEUTRAL
            
            print(f"    {C_TEXT}{display:<12}{R} {C_PRICE}{format_price(analysis['price']):<14}{R} {change_color}{'+' if ticker['change_24h'] > 0 else ''}{ticker['change_24h']:<9.2f}%{R} {score_color}{score:<7.1f}{R} {signal_color}{signal_text:<15}{R}")
        except:
            continue
    
    print(f"    {C_DIM}{'─' * 60}{R}")
    print()


def show_settings(timeframe: str, min_score: int) -> tuple:
    """Show and modify settings"""
    print()
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print(f"    {C_TITLE}║{R}  {C_SUBTITLE}⚙️  CONFIGURACIÓN{R}")
    print(f"    {C_TITLE}{'═' * 50}{R}")
    print()
    print(f"    {C_TEXT}Configuración actual:{R}")
    print(f"      • Timeframe:    {C_PRICE}{timeframe}{R}")
    print(f"      • Score mínimo: {C_PRICE}{min_score}/100{R}")
    print()
    print(f"    {C_DIM}Timeframes: 1m, 5m, 15m, 30m, 1h, 4h, 1d{R}")
    print()
    
    new_tf = input(f"    {C_SUCCESS}➜{R}  Nuevo timeframe ({timeframe}): ").strip() or timeframe
    new_score = input(f"    {C_SUCCESS}➜{R}  Score mínimo ({min_score}): ").strip()
    
    try:
        new_score = int(new_score) if new_score else min_score
        new_score = max(0, min(100, new_score))
    except:
        new_score = min_score
    
    print()
    print(f"    {C_SUCCESS}✓ Configuración actualizada{R}")
    return new_tf, new_score


def main():
    """Main entry point"""
    print_header()
    
    print(f"    {C_PRICE}🔄 Conectando a Binance Futures...{R}")
    
    try:
        client = get_client()
        print(f"    {C_SUCCESS}✓ Conexión exitosa{R}")
        time.sleep(1)
    except Exception as e:
        print(f"    {C_ERROR}❌ Error: {str(e)}{R}")
        sys.exit(1)
    
    timeframe = config.DEFAULT_TIMEFRAME
    min_score = config.MIN_SIGNAL_SCORE
    
    while True:
        print_header()
        print_menu()
        
        choice = input(f"    {C_SUCCESS}➜{R}  Opción: ").strip()
        
        if choice == '0':
            print(f"\n    {C_PRICE}👋 ¡Hasta luego! Buenos trades.{R}\n")
            break
        elif choice == '1':
            analyze_single_coin(client, timeframe)
        elif choice == '2':
            find_opportunities(client, timeframe, min_score)
        elif choice == '3':
            quick_scan(client, timeframe)
        elif choice == '4':
            print(f"\n    {C_DIM}Esta función usa los mismos datos del escaneo rápido...{R}")
            quick_scan(client, timeframe)
        elif choice == '5':
            timeframe, min_score = show_settings(timeframe, min_score)
        else:
            print(f"\n    {C_ERROR}❌ Opción no válida{R}")
        
        input(f"\n    {C_DIM}Presiona Enter para continuar...{R}")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n    {C_WARNING}👋 Bot cerrado{R}\n")
        sys.exit(0)
