"""
Telegram Trading Bot - Clean Text Design
Normal Telegram text formatting (no code blocks)
Multi-Timeframe Analysis for higher reliability
"""
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from telegram.constants import ParseMode
from src.config import config
from src.binance_client import get_client, BinanceClient
from src.technical_analysis import TechnicalAnalyzer, SignalType
from src.mtf_analysis import MultiTimeframeAnalyzer, format_mtf_analysis

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

client = None

# Store user trading data for wizard
user_trading_data = {}


def get_signal_text(signal: SignalType) -> str:
    if signal == SignalType.STRONG_BUY:
        return "COMPRA FUERTE"
    elif signal == SignalType.BUY:
        return "COMPRA"
    elif signal == SignalType.STRONG_SELL:
        return "VENTA FUERTE"
    elif signal == SignalType.SELL:
        return "VENTA"
    return "NEUTRAL"


def format_price(price: float) -> str:
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


def get_strategy(analysis: dict, atr: float) -> dict:
    price = analysis['price']
    signal = analysis['signal']
    score = analysis['score']
    
    if atr is None or atr == 0:
        atr = price * 0.02
    
    strategy = {
        'viable': False, 'action': 'ESPERAR', 'position': 'NEUTRAL',
        'entry': None, 'sl': None, 'tp1': None, 'tp2': None, 'tp3': None,
        'rr': None, 'conf': 0
    }
    
    if signal in [SignalType.STRONG_BUY, SignalType.BUY]:
        strategy['viable'] = True
        strategy['position'] = 'LONG'
        strategy['action'] = 'COMPRAR' if signal == SignalType.STRONG_BUY else 'LONG'
        strategy['conf'] = min(95, score + 10) if signal == SignalType.STRONG_BUY else score
        strategy['entry'] = price
        strategy['sl'] = round(price - (atr * 1.0), 6)  # Scalping: SL más ajustado
        strategy['tp1'] = round(price + (atr * 1.2), 6)  # Ganancia rápida 1
        strategy['tp2'] = round(price + (atr * 2.0), 6)  # Ganancia rápida 2
        strategy['tp3'] = round(price + (atr * 3.0), 6)  # Ganancia extendida
        risk = abs(strategy['entry'] - strategy['sl'])
        strategy['rr'] = round((strategy['tp2'] - strategy['entry']) / risk, 2) if risk > 0 else 0
        
    elif signal in [SignalType.STRONG_SELL, SignalType.SELL]:
        strategy['viable'] = True
        strategy['position'] = 'SHORT'
        strategy['action'] = 'VENDER' if signal == SignalType.STRONG_SELL else 'SHORT'
        strategy['conf'] = min(95, 100 - score + 10) if signal == SignalType.STRONG_SELL else 100 - score
        strategy['entry'] = price
        strategy['sl'] = round(price + (atr * 1.0), 6)  # Scalping: SL más ajustado
        strategy['tp1'] = round(price - (atr * 1.2), 6)  # Ganancia rápida 1
        strategy['tp2'] = round(price - (atr * 2.0), 6)  # Ganancia rápida 2
        strategy['tp3'] = round(price - (atr * 3.0), 6)  # Ganancia extendida
        risk = abs(strategy['sl'] - strategy['entry'])
        strategy['rr'] = round((strategy['entry'] - strategy['tp2']) / risk, 2) if risk > 0 else 0
    
    return strategy


def get_recommended_leverage(confidence: float, volatility_state: str) -> dict:
    """Calculate recommended leverage based on analysis confidence and volatility"""
    # Base leverage on confidence
    if confidence >= 85:
        base_leverage = 10
    elif confidence >= 75:
        base_leverage = 7
    elif confidence >= 65:
        base_leverage = 5
    else:
        base_leverage = 3
    
    # Adjust for volatility
    volatility_multiplier = 1.0
    if "EXTREMA" in volatility_state or "MUY" in volatility_state:
        volatility_multiplier = 0.3
    elif "ALTA" in volatility_state:
        volatility_multiplier = 0.5
    elif "MEDIA" in volatility_state:
        volatility_multiplier = 0.8
    # BAJA keeps 1.0
    
    adjusted = int(base_leverage * volatility_multiplier)
    adjusted = max(2, min(adjusted, 20))  # Keep between 2x and 20x
    
    return {
        'recommended': adjusted,
        'min': max(2, adjusted - 2),
        'max': min(20, adjusted + 3),
        'risk_level': 'BAJO' if adjusted <= 5 else 'MEDIO' if adjusted <= 10 else 'ALTO'
    }


def build_trade_config_msg(data: dict) -> str:
    """Build trade configuration message with all calculations"""
    symbol = data['symbol']
    direction = data['direction']
    entry = data['entry']
    sl = data['sl']
    tp1 = data['tp1']
    tp2 = data['tp2']
    capital = data['capital']
    leverage = data['leverage']
    margin_type = data.get('margin_type', 'Cruzado')
    order_type = data.get('order_type', 'Limit')
    
    # Calculations
    position_size = capital * leverage
    quantity = position_size / entry
    
    # Risk calculations
    sl_distance_pct = abs((sl - entry) / entry) * 100
    tp1_distance_pct = abs((tp1 - entry) / entry) * 100
    tp2_distance_pct = abs((tp2 - entry) / entry) * 100
    
    max_loss = capital * (sl_distance_pct / 100) * leverage
    potential_profit_tp1 = capital * (tp1_distance_pct / 100) * leverage
    potential_profit_tp2 = capital * (tp2_distance_pct / 100) * leverage
    
    # Liquidation estimate (simplified)
    liq_distance = 100 / leverage
    if direction == "LONG":
        liq_price = entry * (1 - liq_distance / 100)
    else:
        liq_price = entry * (1 + liq_distance / 100)
    
    msg = f"*CONFIGURACION DE OPERACION*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"*Par:* {symbol}\n"
    msg += f"*Direccion:* {'LONG (Comprar)' if direction == 'LONG' else 'SHORT (Vender)'}\n\n"
    
    msg += "*Configuracion para Binance:*\n"
    msg += "┌─────────────────────────┐\n"
    msg += f"│ Margen: {margin_type}         │\n"
    msg += f"│ Apalancamiento: {leverage}x      │\n"
    msg += f"│ Tipo: {order_type} Order       │\n"
    msg += f"│ Precio: {format_price(entry)}    │\n"
    msg += f"│ Cantidad: {quantity:.4f}      │\n"
    msg += "└─────────────────────────┘\n\n"
    
    msg += "*Inversion:*\n"
    msg += f"■ Capital: {capital} USDT\n"
    msg += f"■ Posicion total: {position_size:.2f} USDT\n"
    msg += f"■ Tokens: {quantity:.4f}\n\n"
    
    msg += "*Niveles configurados:*\n"
    msg += f"■ Stop Loss: {format_price(sl)} ({'-' if direction == 'LONG' else '+'}{sl_distance_pct:.1f}%)\n"
    msg += f"■ TP1: {format_price(tp1)} ({'+' if direction == 'LONG' else '-'}{tp1_distance_pct:.1f}%)\n"
    msg += f"■ TP2: {format_price(tp2)} ({'+' if direction == 'LONG' else '-'}{tp2_distance_pct:.1f}%)\n\n"
    
    msg += "*Riesgo/Ganancia:*\n"
    msg += f"▸ Perdida maxima: {max_loss:.2f} USDT\n"
    msg += f"▸ Ganancia TP1: {potential_profit_tp1:.2f} USDT\n"
    msg += f"▸ Ganancia TP2: {potential_profit_tp2:.2f} USDT\n"
    msg += f"▸ Liquidacion aprox: {format_price(liq_price)}\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "*PASOS EN BINANCE:*\n"
    msg += f"1. Configura apalancamiento a {leverage}x\n"
    msg += f"2. Selecciona modo {margin_type}\n"
    msg += f"3. {'Compra/Long' if direction == 'LONG' else 'Vende/Short'} a {format_price(entry)}\n"
    msg += f"4. Cantidad: {quantity:.4f}\n"
    msg += f"5. Activa TP/SL antes de confirmar\n"
    
    return msg


def create_progress_bar(current: int, total: int, width: int = 10) -> str:
    """Create a Unicode progress bar"""
    progress = current / total if total > 0 else 0
    filled = int(progress * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(progress * 100)
    return f"▐{bar}▌ {pct}%"


def build_loading_msg(step: int, symbol: str = "") -> str:
    """Build loading message for MTF analysis with Unicode progress bars"""
    total_steps = 8  # Increased from 7 to 8 (added 5M analysis)
    progress_pct = int((step / total_steps) * 100)
    
    # Unicode progress bar (10 blocks)
    filled = int((step / total_steps) * 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    msg = "*▶ TRADING BOT PRO*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"*⟫ Analizando {symbol}*\n\n"
    msg += f"▐{bar}▌ {progress_pct}%\n\n"
    
    steps = [
        ("↻ Conectando a Binance", 1),
        ("▸ Analizando 1D (tendencia principal)", 2),
        ("▸ Analizando 4H (confirmación)", 3),
        ("▸ Analizando 1H (contexto)", 4),
        ("▸ Analizando 15M (timing)", 5),
        ("▸ Analizando 5M (entrada precisa)", 6),
        ("↻ Calculando alineacion", 7),
        ("◆ Generando estrategia", 8)
    ]
    
    for text, step_num in steps:
        if step >= step_num:
            msg += f"☑ {text}\n"
        elif step == step_num - 1:
            msg += f"↻ {text}...\n"
        else:
            msg += f"□ {text}\n"
    
    return msg


def build_analysis_msg(symbol: str, analysis: dict, ticker: dict, strategy: dict) -> str:
    """Build final analysis message - Clean text format"""
    price = analysis['price']
    score = analysis['score']
    signal = analysis['signal']
    change = ticker['change_24h']
    ind = analysis['indicators']
    trend = analysis['trend']
    mom = analysis['momentum']
    
    # Build message with normal Telegram formatting
    msg = f"*ANALISIS: {symbol}*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Price section
    msg += "*Precio y Mercado*\n"
    msg += f"Precio: *{format_price(price)}*\n"
    msg += f"Cambio 24h: *{'+' if change > 0 else ''}{change:.2f}%*\n"
    msg += f"Volumen: ${ticker['volume_24h']:,.0f}\n\n"
    
    # Score section
    msg += "*Puntuacion*\n"
    msg += f"Score: *{score:.1f}/100*\n"
    msg += f"Senal: *{get_signal_text(signal)}*\n\n"
    
    # Indicators
    msg += "*Indicadores*\n"
    msg += f"Tendencia: {trend['direction']}\n"
    msg += f"Momentum: {mom['state']}\n"
    if ind.get('rsi'):
        rsi = ind['rsi']
        rsi_zone = " (oversold)" if rsi < 30 else " (overbought)" if rsi > 70 else ""
        msg += f"RSI: {rsi:.1f}{rsi_zone}\n"
    msg += f"EMA 9: {format_price(ind['ema_9'])}\n"
    msg += f"EMA 200: {format_price(ind['ema_200'])}\n\n"
    
    # Strategy section
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "*ESTRATEGIA*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if strategy['viable']:
        msg += f"Accion: *{strategy['action']}*\n"
        msg += f"Posicion: *{strategy['position']}*\n"
        msg += f"Confianza: *{strategy['conf']:.0f}%*\n"
        msg += f"Ratio R/R: *1:{strategy['rr']}*\n\n"
        
        msg += "*Niveles de Operacion*\n"
        msg += f"Entrada: *{format_price(strategy['entry'])}*\n"
        msg += f"Stop Loss: *{format_price(strategy['sl'])}*\n"
        msg += f"TP1: {format_price(strategy['tp1'])}\n"
        msg += f"TP2: {format_price(strategy['tp2'])}\n"
        msg += f"TP3: {format_price(strategy['tp3'])}\n\n"
        
        msg += "_Gestion: Max 1-2% capital, Apalancamiento 3x-5x_\n\n"
    else:
        msg += "*NO OPERAR*\n\n"
        msg += "Score neutral sin senales claras.\n\n"
    
    # Next actions section
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "*Que puedes hacer ahora:*\n"
    msg += "• Escribe otra moneda (ej: ETH, SOL)\n"
    msg += "• /oportunidades - Ver mejores senales\n"
    msg += "• /escanear - Ver todo el mercado\n"
    msg += "• /ayuda - Ver todos los comandos"
    
    return msg


def get_analysis_buttons(symbol: str = None, has_signal: bool = False):
    """Get inline buttons to show after analysis"""
    buttons = []
    
    # Show config button if there's a viable signal
    if has_signal and symbol:
        buttons.append([
            InlineKeyboardButton("Configurar Operacion", callback_data=f"wizard_start_{symbol}")
        ])
    
    buttons.extend([
        [
            InlineKeyboardButton("Ver Oportunidades", callback_data="menu_oportunidades"),
            InlineKeyboardButton("Escanear Mercado", callback_data="menu_escanear")
        ],
        [
            InlineKeyboardButton("Analizar otra moneda", callback_data="menu_analizar")
        ],
        [
            InlineKeyboardButton("← Menu Principal", callback_data="menu_inicio")
        ]
    ])
    
    return InlineKeyboardMarkup(buttons)


def get_nav_buttons():
    """Get navigation buttons for all responses"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Analizar Moneda", callback_data="menu_analizar"),
            InlineKeyboardButton("Oportunidades", callback_data="menu_oportunidades")
        ],
        [
            InlineKeyboardButton("← Menu Principal", callback_data="menu_inicio")
        ]
    ])


def get_simple_nav():
    """Simple navigation back to menu"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("← Menu Principal", callback_data="menu_inicio")]
    ])


def build_opportunities_msg(opportunities: list, min_score: int) -> str:
    """Build opportunities message"""
    msg = "*OPORTUNIDADES DE TRADING*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if not opportunities:
        msg += f"No hay oportunidades con score mayor a {min_score} en este momento.\n\n"
        msg += "Intenta mas tarde."
    else:
        for i, opp in enumerate(opportunities[:5], 1):
            change = opp['change']
            msg += f"*{i}. {opp['symbol']}*\n"
            msg += f"Precio: {format_price(opp['price'])}\n"
            msg += f"Score: *{opp['score']:.0f}/100* | 24h: {'+' if change > 0 else ''}{change:.1f}%\n"
            msg += f"Senal: *{get_signal_text(opp['signal'])}*\n"
            msg += f"Entrada: {format_price(opp['strategy']['entry'])}\n"
            msg += f"SL: {format_price(opp['strategy']['sl'])} | TP: {format_price(opp['strategy']['tp2'])}\n\n"
        
        msg += "_Usa /analizar <moneda> para mas detalles_"
    
    return msg


def build_scan_msg(data: list) -> str:
    """Build scan message"""
    msg = "*ESCANEO DE MERCADO*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for d in data:
        name = d['symbol'].replace('/USDT', '')
        change = d['change']
        score = d['score']
        
        msg += f"*{name}*\n"
        msg += f"{format_price(d['price'])} | {'+' if change > 0 else ''}{change:.1f}% | Score: {score:.0f}\n\n"
    
    msg += "_/analizar <moneda> para detalles_"
    return msg


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Analizar Moneda", callback_data="menu_analizar")],
        [InlineKeyboardButton("Ver Oportunidades", callback_data="menu_oportunidades")],
        [InlineKeyboardButton("Escanear Mercado", callback_data="menu_escanear")],
        [InlineKeyboardButton("Top Movers", callback_data="menu_top")],
        [InlineKeyboardButton("Ayuda", callback_data="menu_ayuda")]
    ]
    
    msg = "*▶ TRADING BOT PRO*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += "Bot de analisis tecnico profesional para Binance Futures.\n\n"
    
    msg += "*⟫ Funciones disponibles:*\n\n"
    
    msg += "▸ *Analizar Moneda*\n"
    msg += "  → Escribe cualquier cripto (BTC, ETH, SOL)\n"
    msg += "  → Recibe analisis con estrategia de trading\n\n"
    
    msg += "◆ *Ver Oportunidades*\n"
    msg += "  → Mejores senales del mercado ahora\n"
    msg += "  → Monedas con score alto\n\n"
    
    msg += "▫ *Escanear Mercado*\n"
    msg += "  → Vista rapida de todas las monedas\n"
    msg += "  → Precio, cambio 24h y score\n\n"
    
    msg += "▲ *Top Movers*\n"
    msg += "  → Mayor movimiento en 24 horas\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━\n"
    msg += "_Selecciona una opcion o escribe una moneda:_"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "*AYUDA*\n"
    msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "*Como usar:*\n"
    msg += "Escribe el nombre de cualquier criptomoneda para analizarla:\n"
    msg += "_BTC, ETH, SOL, LTC, DOGE..._\n\n"
    msg += "O usa los comandos:\n"
    msg += "/analizar BTC\n"
    msg += "/oportunidades\n"
    msg += "/escanear\n\n"
    msg += "*Senales:*\n"
    msg += "COMPRA FUERTE - Score >= 70\n"
    msg += "COMPRA - Score >= 55\n"
    msg += "NEUTRAL - Score 45-55\n"
    msg += "VENTA - Score <= 45\n"
    msg += "VENTA FUERTE - Score <= 30"
    
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    
    if not context.args:
        msg = "*Uso:* /analizar <moneda>\n\n"
        msg += "Ejemplos:\n"
        msg += "/analizar BTC\n"
        msg += "/analizar ETH"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    symbol_input = context.args[0].upper()
    symbol = client.normalize_symbol(symbol_input)
    
    if symbol is None:
        msg = f"*Error:* {symbol_input} no existe en Binance Futures"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        return
    
    display = client.get_display_symbol(symbol)
    
    # Send initial loading message
    loading_msg = await update.message.reply_text(
        build_loading_msg(1, display),
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Create MTF analyzer
        mtf_analyzer = MultiTimeframeAnalyzer(client)
        
        # Step by step analysis with visual feedback (8 steps now)
        await asyncio.sleep(0.3)
        await loading_msg.edit_text(build_loading_msg(2, display), parse_mode=ParseMode.MARKDOWN)
        
        await asyncio.sleep(0.3)
        await loading_msg.edit_text(build_loading_msg(3, display), parse_mode=ParseMode.MARKDOWN)
        
        await asyncio.sleep(0.3)
        await loading_msg.edit_text(build_loading_msg(4, display), parse_mode=ParseMode.MARKDOWN)
        
        await asyncio.sleep(0.3)
        await loading_msg.edit_text(build_loading_msg(5, display), parse_mode=ParseMode.MARKDOWN)
        
        await asyncio.sleep(0.3)
        await loading_msg.edit_text(build_loading_msg(6, display), parse_mode=ParseMode.MARKDOWN)
        
        await asyncio.sleep(0.2)
        await loading_msg.edit_text(build_loading_msg(7, display), parse_mode=ParseMode.MARKDOWN)
        
        # Perform full MTF analysis
        mtf_result = mtf_analyzer.analyze(symbol)
        
        await asyncio.sleep(0.2)
        await loading_msg.edit_text(build_loading_msg(8, display), parse_mode=ParseMode.MARKDOWN)
        
        # Generate strategy based on MTF result
        df = client.get_ohlcv(symbol, '5m')  # Use 5m for scalping ATR
        atr = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / 20
        
        strategy = {
            'viable': mtf_result.should_trade,
            'action': mtf_result.trade_direction,
            'position': mtf_result.trade_direction,
            'entry': mtf_result.price,
            'sl': None,
            'tp1': None,
            'tp2': None,
            'tp3': None,
            'rr': None,
            'conf': mtf_result.confidence
        }
        
        if mtf_result.should_trade:
            # Usar porcentajes para TP/SL (mismo que get_strategy)
            SL_PERCENT = 0.10
            TP1_PERCENT = 0.05
            TP2_PERCENT = 0.10
            TP3_PERCENT = 0.15
            
            if mtf_result.trade_direction == "LONG":
                strategy['sl'] = round(mtf_result.price * (1 - SL_PERCENT), 6)
                strategy['tp1'] = round(mtf_result.price * (1 + TP1_PERCENT), 6)
                strategy['tp2'] = round(mtf_result.price * (1 + TP2_PERCENT), 6)
                strategy['tp3'] = round(mtf_result.price * (1 + TP3_PERCENT), 6)
            else:
                strategy['sl'] = round(mtf_result.price * (1 + SL_PERCENT), 6)
                strategy['tp1'] = round(mtf_result.price * (1 - TP1_PERCENT), 6)
                strategy['tp2'] = round(mtf_result.price * (1 - TP2_PERCENT), 6)
                strategy['tp3'] = round(mtf_result.price * (1 - TP3_PERCENT), 6)
            
            risk = abs(strategy['entry'] - strategy['sl'])
            strategy['rr'] = round(abs(strategy['tp2'] - strategy['entry']) / risk, 2) if risk > 0 else 0
            
            # Calculate recommended leverage
            leverage_rec = get_recommended_leverage(mtf_result.confidence, mtf_result.volatility_state)
            
            # Store data for wizard
            user_id = update.message.from_user.id
            user_trading_data[user_id] = {
                'symbol': display,
                'raw_symbol': symbol,
                'direction': mtf_result.trade_direction,
                'entry': strategy['entry'],
                'sl': strategy['sl'],
                'tp1': strategy['tp1'],
                'tp2': strategy['tp2'],
                'tp3': strategy['tp3'],
                'confidence': mtf_result.confidence,
                'volatility_state': mtf_result.volatility_state,
                'leverage_rec': leverage_rec
            }
        
        # Final result with MTF format
        await asyncio.sleep(0.3)
        final_msg = format_mtf_analysis(mtf_result, strategy)
        await loading_msg.edit_text(
            final_msg, 
            parse_mode=ParseMode.MARKDOWN, 
            reply_markup=get_analysis_buttons(display, has_signal=mtf_result.should_trade)
        )
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
        await loading_msg.edit_text(f"*Error:* {str(e)}", parse_mode=ParseMode.MARKDOWN)



async def opportunities_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    
    msg_obj = update.message or update.callback_query.message
    
    loading_msg = await msg_obj.reply_text(
        "*BUSCANDO OPORTUNIDADES*\n━━━━━━━━━━━━━━━━━━━━\n\n▐░░░░░░░░░░▌ 0%\n\n▸ Iniciando escaneo...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        opportunities = []
        total = len(config.TOP_SYMBOLS)
        mtf_analyzer = MultiTimeframeAnalyzer(client)  # Use MTF analyzer for consistency
        
        for i, symbol in enumerate(config.TOP_SYMBOLS):
            try:
                if i % 5 == 0:
                    bar = create_progress_bar(i + 1, total)
                    current_sym = client.get_display_symbol(symbol).replace('/USDT', '')
                    progress = f"*BUSCANDO OPORTUNIDADES*\n━━━━━━━━━━━━━━━━━━━━\n\n{bar}\n\n■ Analizando {i+1}/{total}\n▸ {current_sym}..."
                    await loading_msg.edit_text(progress, parse_mode=ParseMode.MARKDOWN)
                
                # Use MTF analysis for consistent results
                mtf_result = mtf_analyzer.analyze(symbol)
                
                # Only add if should_trade is True (same logic as analyze_command)
                if mtf_result.should_trade and mtf_result.trade_direction in ["LONG", "SHORT"]:
                    ticker = client.get_ticker(symbol)
                    df = client.get_ohlcv(symbol, '5m')
                    atr = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / 20
                    
                    # Build strategy with scalping TP/SL
                    strategy = {
                        'viable': True,
                        'action': mtf_result.trade_direction,
                        'position': mtf_result.trade_direction,
                        'entry': mtf_result.price,
                        'conf': mtf_result.confidence
                    }
                    
                    if mtf_result.trade_direction == "LONG":
                        strategy['sl'] = round(mtf_result.price - (atr * 1.0), 6)
                        strategy['tp1'] = round(mtf_result.price + (atr * 1.2), 6)
                        strategy['tp2'] = round(mtf_result.price + (atr * 2.0), 6)
                    else:
                        strategy['sl'] = round(mtf_result.price + (atr * 1.0), 6)
                        strategy['tp1'] = round(mtf_result.price - (atr * 1.2), 6)
                        strategy['tp2'] = round(mtf_result.price - (atr * 2.0), 6)
                    
                    opportunities.append({
                        'symbol': client.get_display_symbol(symbol),
                        'price': mtf_result.price,
                        'score': mtf_result.overall_score,
                        'signal': mtf_result.overall_signal,
                        'change': ticker['change_24h'],
                        'strategy': strategy
                    })
            except:
                continue
        
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        final_msg = build_opportunities_msg(opportunities, config.MIN_SIGNAL_SCORE)
        await loading_msg.edit_text(final_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_nav_buttons())
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await loading_msg.edit_text(f"*Error:* {str(e)}", parse_mode=ParseMode.MARKDOWN)


async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    
    msg_obj = update.message or update.callback_query.message
    
    loading_msg = await msg_obj.reply_text(
        "*ESCANEO DE MERCADO*\n━━━━━━━━━━━━━━━━━━━━\n\n▐░░░░░░░░░░▌ 0%\n\n▸ Iniciando escaneo...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        data = []
        symbols_to_scan = config.TOP_SYMBOLS[:12]
        total = len(symbols_to_scan)
        
        for i, symbol in enumerate(symbols_to_scan):
            try:
                if i % 3 == 0:
                    bar = create_progress_bar(i + 1, total)
                    current_sym = client.get_display_symbol(symbol).replace('/USDT', '')
                    progress = f"*ESCANEO DE MERCADO*\n━━━━━━━━━━━━━━━━━━━━\n\n{bar}\n\n■ Escaneando {i+1}/{total}\n▸ {current_sym}..."
                    await loading_msg.edit_text(progress, parse_mode=ParseMode.MARKDOWN)
                
                ticker = client.get_ticker(symbol)
                df = client.get_ohlcv(symbol, config.DEFAULT_TIMEFRAME)
                analyzer = TechnicalAnalyzer(df)
                analysis = analyzer.generate_analysis()
                
                data.append({
                    'symbol': client.get_display_symbol(symbol),
                    'price': analysis['price'],
                    'change': ticker['change_24h'],
                    'score': analysis['score']
                })
            except:
                continue
        
        final_msg = build_scan_msg(data)
        await loading_msg.edit_text(final_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_nav_buttons())
        
    except Exception as e:
        await loading_msg.edit_text(f"*Error:* {str(e)}", parse_mode=ParseMode.MARKDOWN)


async def top_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    
    loading_msg = await update.message.reply_text(
        "*TOP MOVERS 24H*\n━━━━━━━━━━━━━━━━━━━━\n\n▐░░░░░░░░░░▌ 0%\n\n▸ Obteniendo datos...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        tickers = client.get_top_by_change(10)
        
        msg = "*TOP MOVERS 24H*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, t in enumerate(tickers, 1):
            name = client.get_display_symbol(t['symbol']).replace('/USDT', '')
            change = t['change_24h']
            msg += f"*{i}. {name}*\n"
            msg += f"{format_price(t['price'])} | {'+' if change > 0 else ''}{change:.2f}%\n\n"
        
        await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN)
        
    except Exception as e:
        await loading_msg.edit_text(f"*Error:* {str(e)}", parse_mode=ParseMode.MARKDOWN)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "menu_inicio":
        # Return to main menu
        keyboard = [
            [InlineKeyboardButton("Analizar Moneda", callback_data="menu_analizar")],
            [InlineKeyboardButton("Ver Oportunidades", callback_data="menu_oportunidades")],
            [InlineKeyboardButton("Escanear Mercado", callback_data="menu_escanear")],
            [InlineKeyboardButton("Top Movers", callback_data="menu_top")],
            [InlineKeyboardButton("Ayuda", callback_data="menu_ayuda")]
        ]
        
        msg = "*TRADING BOT PRO*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "Bot de analisis tecnico profesional para Binance Futures.\n\n"
        msg += "*Funciones disponibles:*\n\n"
        msg += "Analizar Moneda\n"
        msg += "→ Escribe cualquier cripto (BTC, ETH, SOL)\n"
        msg += "→ Recibe analisis con estrategia de trading\n\n"
        msg += "Ver Oportunidades\n"
        msg += "→ Mejores senales del mercado ahora\n\n"
        msg += "Escanear Mercado\n"
        msg += "→ Vista rapida de todas las monedas\n\n"
        msg += "Top Movers\n"
        msg += "→ Mayor movimiento en 24 horas\n\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        msg += "_Selecciona una opcion o escribe una moneda:_"
        
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data == "menu_analizar":
        msg = "*Analizar una Moneda*\n\n"
        msg += "Escribe el nombre de la criptomoneda que quieres analizar.\n\n"
        msg += "Puedes escribir:\n"
        msg += "→ Solo el simbolo: BTC, ETH, SOL\n"
        msg += "→ Con USDT: BTCUSDT, ETHUSDT\n\n"
        msg += "_El bot analizara 4 timeframes (1D, 4H, 1H, 15M) para mayor fiabilidad._"
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_simple_nav())
    
    elif query.data == "menu_oportunidades":
        await opportunities_command(query, context)
    
    elif query.data == "menu_escanear":
        await scan_command(query, context)
    
    elif query.data == "menu_top":
        loading_msg = await query.message.reply_text("*TOP MOVERS 24H*\n━━━━━━━━━━━━━━━━━━━━\n\n▐░░░░░░░░░░▌ 0%\n\n▸ Obteniendo datos...", parse_mode=ParseMode.MARKDOWN)
        try:
            tickers = client.get_top_by_change(10)
            msg = "*TOP MOVERS 24H*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
            for i, t in enumerate(tickers, 1):
                name = client.get_display_symbol(t['symbol']).replace('/USDT', '')
                change = t['change_24h']
                msg += f"*{i}. {name}*\n"
                msg += f"{format_price(t['price'])} | {'+' if change > 0 else ''}{change:.2f}%\n\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n"
            msg += "_Escribe el nombre de cualquier moneda para analizarla_"
            await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_nav_buttons())
        except Exception as e:
            await loading_msg.edit_text(f"*Error:* {str(e)}", parse_mode=ParseMode.MARKDOWN, reply_markup=get_simple_nav())
    
    elif query.data == "menu_ayuda":
        msg = "*Ayuda*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += "*Como usar el bot:*\n"
        msg += "1. Escribe el nombre de cualquier cripto (ej: BTC)\n"
        msg += "2. O usa los botones del menu\n\n"
        msg += "*Sistema Multi-Timeframe:*\n"
        msg += "→ Analiza 1D, 4H, 1H, 15M\n"
        msg += "→ Solo da senal cuando hay alineacion\n"
        msg += "→ Mayor fiabilidad en las senales\n\n"
        msg += "*Senales:*\n"
        msg += "COMPRA FUERTE → Score 70+\n"
        msg += "COMPRA → Score 55-70\n"
        msg += "NEUTRAL → Score 45-55\n"
        msg += "VENTA → Score 30-45\n"
        msg += "VENTA FUERTE → Score menor a 30"
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_nav_buttons())
    
    # ===== WIZARD HANDLERS =====
    elif query.data.startswith("wizard_start_"):
        user_id = query.from_user.id
        if user_id not in user_trading_data:
            await query.message.reply_text("*Error:* No hay datos de analisis. Analiza una moneda primero.", parse_mode=ParseMode.MARKDOWN)
            return
        
        data = user_trading_data[user_id]
        leverage_rec = data['leverage_rec']
        
        msg = "*CONFIGURAR OPERACION*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"*Par:* {data['symbol']}\n"
        msg += f"*Direccion:* {data['direction']}\n"
        msg += f"*Entrada:* {format_price(data['entry'])}\n\n"
        msg += "*Apalancamiento Recomendado:*\n"
        msg += f"▸ Optimo: *{leverage_rec['recommended']}x*\n"
        msg += f"▸ Rango seguro: {leverage_rec['min']}x - {leverage_rec['max']}x\n"
        msg += f"▸ Nivel de riesgo: {leverage_rec['risk_level']}\n\n"
        msg += "_Basado en confianza del {:.0f}% y volatilidad {}_\n\n".format(data['confidence'], data['volatility_state'])
        msg += "*¿Cuanto capital deseas invertir?*\n"
        msg += "_Escribe la cantidad en USDT (ej: 50, 100, 200)_"
        
        # Mark user as waiting for capital input
        user_trading_data[user_id]['wizard_step'] = 'waiting_capital'
        
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=get_simple_nav())
    
    elif query.data.startswith("wizard_leverage_"):
        user_id = query.from_user.id
        leverage = int(query.data.split("_")[2])
        
        if user_id in user_trading_data:
            user_trading_data[user_id]['leverage'] = leverage
            user_trading_data[user_id]['wizard_step'] = 'selecting_margin'
            
            msg = "*TIPO DE MARGEN*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += f"*Apalancamiento seleccionado:* {leverage}x\n\n"
            msg += "*¿Que tipo de margen deseas?*\n\n"
            msg += "*Cruzado:* Todo tu balance es colateral\n"
            msg += "→ Menor riesgo de liquidacion\n"
            msg += "→ Recomendado para principiantes\n\n"
            msg += "*Aislado:* Solo el margen usado es colateral\n"
            msg += "→ Limite de perdida controlado\n"
            msg += "→ Mayor riesgo de liquidacion\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("Cruzado (Recomendado)", callback_data="wizard_margin_cross"),
                    InlineKeyboardButton("Aislado", callback_data="wizard_margin_isolated")
                ],
                [InlineKeyboardButton("← Cancelar", callback_data="menu_inicio")]
            ]
            await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif query.data.startswith("wizard_margin_"):
        user_id = query.from_user.id
        margin = "Cruzado" if "cross" in query.data else "Aislado"
        
        if user_id in user_trading_data:
            user_trading_data[user_id]['margin_type'] = margin
            user_trading_data[user_id]['order_type'] = 'Limit'  # Default
            
            # Generate final configuration
            data = user_trading_data[user_id]
            final_msg = build_trade_config_msg(data)
            
            keyboard = [
                [InlineKeyboardButton("← Menu Principal", callback_data="menu_inicio")],
                [InlineKeyboardButton("Analizar otra moneda", callback_data="menu_analizar")]
            ]
            await query.message.reply_text(final_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global client
    
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Check if user is in wizard mode waiting for capital
    if user_id in user_trading_data and user_trading_data[user_id].get('wizard_step') == 'waiting_capital':
        try:
            capital = float(text.replace(',', '.').replace('$', '').replace('usdt', '').replace('USDT', ''))
            if capital < 5:
                await update.message.reply_text("*Error:* El capital minimo es 5 USDT", parse_mode=ParseMode.MARKDOWN)
                return
            if capital > 100000:
                await update.message.reply_text("*Error:* Capital muy alto. Maximo 100,000 USDT", parse_mode=ParseMode.MARKDOWN)
                return
            
            user_trading_data[user_id]['capital'] = capital
            user_trading_data[user_id]['wizard_step'] = 'selecting_leverage'
            
            leverage_rec = user_trading_data[user_id]['leverage_rec']
            
            msg = "*SELECCIONA APALANCAMIENTO*\n"
            msg += "━━━━━━━━━━━━━━━━━━━━\n\n"
            msg += f"*Capital:* {capital} USDT\n\n"
            msg += f"*Recomendado:* {leverage_rec['recommended']}x (riesgo {leverage_rec['risk_level']})\n\n"
            msg += "*Selecciona el apalancamiento:*\n"
            
            # Generate leverage buttons
            rec = leverage_rec['recommended']
            keyboard = [
                [
                    InlineKeyboardButton(f"3x (Bajo)", callback_data="wizard_leverage_3"),
                    InlineKeyboardButton(f"5x (Bajo)", callback_data="wizard_leverage_5"),
                ],
                [
                    InlineKeyboardButton(f"7x (Medio)", callback_data="wizard_leverage_7"),
                    InlineKeyboardButton(f"10x (Medio)", callback_data="wizard_leverage_10"),
                ],
                [
                    InlineKeyboardButton(f"15x (Alto)", callback_data="wizard_leverage_15"),
                    InlineKeyboardButton(f"20x (Alto)", callback_data="wizard_leverage_20"),
                ],
                [InlineKeyboardButton("← Cancelar", callback_data="menu_inicio")]
            ]
            
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            return
            
        except ValueError:
            await update.message.reply_text("*Error:* Escribe solo el numero (ej: 100)", parse_mode=ParseMode.MARKDOWN)
            return
    
    # Normal message handling - analyze crypto
    text_upper = text.upper()
    if len(text_upper) >= 2 and len(text_upper) <= 10:
        clean = text_upper.replace('USDT', '').replace('/', '')
        if clean.isalpha():
            symbol = client.normalize_symbol(text_upper)
            if symbol:
                context.args = [text_upper]
                await analyze_command(update, context)
                return
    
    await update.message.reply_text(
        "Escribe un simbolo valido (BTC, ETH, SOL, etc.) o usa /ayuda",
        parse_mode=ParseMode.MARKDOWN
    )


def main():
    global client
    
    if not config.TELEGRAM_BOT_TOKEN or 'your_' in config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return
    
    print("Conectando a Binance...")
    try:
        client = get_client()
        print("OK - Conectado a Binance Futures")
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    print("Iniciando bot de Telegram...")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ayuda", help_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("analizar", analyze_command))
    app.add_handler(CommandHandler("a", analyze_command))
    app.add_handler(CommandHandler("oportunidades", opportunities_command))
    app.add_handler(CommandHandler("o", opportunities_command))
    app.add_handler(CommandHandler("escanear", scan_command))
    app.add_handler(CommandHandler("scan", scan_command))
    app.add_handler(CommandHandler("top", top_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("Bot iniciado - Abre Telegram y busca tu bot")
    print("Presiona Ctrl+C para detener")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
