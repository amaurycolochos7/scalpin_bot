"""
Scalping Bot ML - Auto-Monitor Version
Simplified 2-button interface with automatic 24/7 monitoring
Uses MA7/MA25 crossover strategy with TradingView 10-indicator confirmation
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

# Mexico/Chiapas timezone (UTC-6)
MEXICO_TZ = timezone(timedelta(hours=-6))
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from src.config import config
from src.binance_client import get_client
from src.auto_monitor import AutoMonitor
from src.ml_config import MLConfig
from src.mtf_analysis import MultiTimeframeAnalyzer, format_mtf_analysis
from src.technical_analysis import TechnicalAnalyzer
from src.auth import AuthManager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global
client = None
auto_monitor = None
mtf_analyzer = None
auth_manager = None


def format_price(price: float) -> str:
    """Formatea precio según su magnitud"""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


# ========================
# MENÚ PRINCIPAL
# ========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal - 2 botones esenciales"""
    keyboard = [
        [InlineKeyboardButton("📊 Resumen del Mercado", callback_data="view_monitored")],
        [InlineKeyboardButton("🔍 Analizar Otra Moneda", callback_data="analyze_other")]
    ]
    
    # Get monitor status
    status = auto_monitor.get_status() if auto_monitor else {'is_running': False, 'monitored_count': 0}
    
    msg = "┏━━━━━━━━━━━━━━━━━━━━┓\n"
    msg += "┃  TRADING BOT MA7   ┃\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    msg += "Estrategia: MA7/MA25 + 10 Indicadores\n"
    msg += "Todas las criptos de Binance Futures\n\n"
    
    if status['is_running']:
        msg += f"🟢 *Estado:* ACTIVO\n"
        msg += f"📊 *Monitoreando:* {status['monitored_count']} criptos\n"
        msg += f"⏱️ *Escaneo:* Cada 5 minutos\n\n"
    else:
        msg += f"🔴 *Estado:* INICIALIZANDO...\n\n"

    
    msg += "┏━ OPCIONES\n\n"
    msg += "➣ *Resumen del Mercado*\n"
    msg += "   Top 10 alcistas + Top 10 bajistas\n\n"
    msg += "➣ *Analizar Moneda*\n"
    msg += "   Escribe símbolo: BTC, ETH, etc.\n\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━"
    
    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


# ========================
# VER MONEDAS MONITOREADAS
# ========================
async def view_monitored_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra Top 10 alcistas y Top 10 bajistas"""
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
    
    loading_msg = "┏━ ESCANEANDO MERCADO\n\n▸ Analizando criptos...\n▸ Esto puede tomar 1-2 minutos..."
    
    if query:
        await query.edit_message_text(loading_msg, parse_mode=ParseMode.MARKDOWN)
        msg_obj = query.message
    else:
        msg_obj = await update.message.reply_text(loading_msg, parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Get top symbols by volume (analyze top 100 for speed)
        top_symbols = client.get_top_by_volume(limit=100)
        
        bullish_list = []
        bearish_list = []
        
        # Analyze each symbol
        for crypto in top_symbols[:50]:  # Limit to 50 for speed
            try:
                symbol = crypto['symbol']
                df = client.get_ohlcv(symbol, '15m', limit=50)
                
                if df is None or len(df) < 30:
                    continue
                
                analyzer = TechnicalAnalyzer(df)
                analyzer.calculate_all_indicators()
                
                crossover = analyzer.detect_ma_crossover()
                tv_votes = analyzer.get_tradingview_votes()
                
                symbol_name = symbol.replace('/USDT:USDT', 'USDT').replace('/USDT', 'USDT')
                
                result = {
                    'name': symbol_name,
                    'signal': crossover['signal'],
                    'long_votes': tv_votes['long_count'],
                    'short_votes': tv_votes['short_count']
                }
                
                # Classify by trend
                if crossover['signal'] in ['LONG', 'LONG_TREND'] and tv_votes['long_count'] >= 5:
                    result['score'] = tv_votes['long_count']
                    bullish_list.append(result)
                elif crossover['signal'] in ['SHORT', 'SHORT_TREND'] and tv_votes['short_count'] >= 5:
                    result['score'] = tv_votes['short_count']
                    bearish_list.append(result)
                    
            except Exception as e:
                continue
        
        # Sort by score (votes)
        bullish_list.sort(key=lambda x: x['score'], reverse=True)
        bearish_list.sort(key=lambda x: x['score'], reverse=True)
        
        # Build message
        msg = "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        msg += "┃  RESUMEN MERCADO   ┃\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        # TOP 10 BULLISH
        msg += "🟢 *TOP 10 ALCISTAS*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        for i, crypto in enumerate(bullish_list[:10], 1):
            votes = crypto['long_votes']
            is_cross = "🔥" if crypto['signal'] == 'LONG' else ""
            msg += f"{i}. {crypto['name']} ({votes}/10) {is_cross}\n"
        
        if not bullish_list:
            msg += "No hay señales alcistas fuertes\n"
        
        msg += "\n"
        
        # TOP 10 BEARISH
        msg += "🔴 *TOP 10 BAJISTAS*\n"
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        for i, crypto in enumerate(bearish_list[:10], 1):
            votes = crypto['short_votes']
            is_cross = "🔥" if crypto['signal'] == 'SHORT' else ""
            msg += f"{i}. {crypto['name']} ({votes}/10) {is_cross}\n"
        
        if not bearish_list:
            msg += "No hay señales bajistas fuertes\n"
        
        msg += "\n"
        msg += f"⏰ {datetime.now(MEXICO_TZ).strftime('%H:%M:%S')}\n"
        msg += "🔥 = Cruce reciente\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await msg_obj.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in view_monitored: {e}", exc_info=True)
        await msg_obj.edit_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)



# ========================
# ANALIZAR MONEDA
# ========================
async def analyze_crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol_name: str = None):
    """Analiza una criptomoneda usando estrategia MA7/MA25 + 10 indicadores TradingView"""
    global mtf_analyzer
    
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
        msg_obj = query.message
    else:
        msg_obj = update.message
    
    # Get symbol from argument or callback
    if not symbol_name and context.args:
        symbol_name = context.args[0].upper()
    
    if not symbol_name:
        msg = "┏━ ANÁLISIS MANUAL\n\n"
        msg += "Escribe el símbolo:\n\n"
        msg += "Ejemplos: BTC, ETH, SOL\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await msg_obj.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # Normalize symbol
    symbol = client.normalize_symbol(symbol_name)
    
    if not symbol:
        await msg_obj.reply_text(f"✗ {symbol_name} no existe en Binance Futures", parse_mode=ParseMode.MARKDOWN)
        return
    
    display = client.get_display_symbol(symbol).replace('/USDT', '')
    
    # Loading message
    loading_msg = await msg_obj.reply_text(
        f"┏━ Analizando {display}\n\n"
        f"▸ Obteniendo datos 15m...\n"
        f"▸ Calculando MA7/MA25...\n"
        f"▸ Votando con 10 indicadores...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Initialize MTF analyzer if needed
        if mtf_analyzer is None:
            mtf_analyzer = MultiTimeframeAnalyzer(client)
        
        # Analyze using new MA7/MA25 strategy
        mtf_result = mtf_analyzer.analyze(symbol)
        
        # Get current price for strategy levels
        price = mtf_result.price
        
        # Calculate entry/exit levels based on ATR or simple percentage
        if mtf_result.trade_direction == 'LONG':
            entry = price
            sl = price * 0.95  # 5% stop loss
            tp1 = price * 1.10  # 10% take profit
        elif mtf_result.trade_direction == 'SHORT':
            entry = price
            sl = price * 1.05  # 5% stop loss
            tp1 = price * 0.90  # 10% take profit
        else:
            entry = price
            sl = price * 0.95
            tp1 = price * 1.10
        
        strategy = {
            'entry': entry,
            'sl': sl,
            'tp1': tp1
        }
        
        # Format message using new format
        msg = f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
        msg += f"┃   {display:^14}   ┃\n"
        msg += f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        msg += f"💰 Precio: {format_price(price)}\n\n"
        
        # MA7/MA25 STATUS
        msg += "━━━ MA7/MA25 (15m) ━━━\n"
        msg += f"{mtf_result.ma_crossover['description']}\n"
        msg += f"MA7: {format_price(mtf_result.ma_crossover['ma7'])}\n"
        msg += f"MA25: {format_price(mtf_result.ma_crossover['ma25'])}\n\n"
        
        # TRADINGVIEW INDICATORS (10 votes)
        msg += "━━━ Indicadores TradingView ━━━\n"
        long_votes = mtf_result.tv_votes['long_count']
        short_votes = mtf_result.tv_votes['short_count']
        neutral = mtf_result.tv_votes['neutral_count']
        
        # Visual vote bar
        bar_long = "🟢" * long_votes
        bar_short = "🔴" * short_votes
        
        msg += f"LONG: {long_votes}  {bar_long}\n"
        msg += f"SHORT: {short_votes}  {bar_short}\n\n"
        
        # Individual votes breakdown (compact)
        msg += "Detalle:\n"
        for name, vote_data in mtf_result.tv_votes['votes'].items():
            vote = vote_data['vote']
            if vote > 0:
                icon = "🟢"
            elif vote < 0:
                icon = "🔴"
            else:
                icon = "⚪"
            msg += f"  {icon} {name}\n"
        msg += "\n"
        
        # MAIN SIGNAL
        msg += "━━━━━━━━━━━━━━━━━━━━\n"
        if mtf_result.should_trade:
            if mtf_result.trade_direction == "LONG":
                msg += "┏━ SEÑAL: COMPRA ▲\n\n"
            else:
                msg += "┏━ SEÑAL: VENTA ▼\n\n"
            
            msg += f"Confianza: {mtf_result.confidence}% ({long_votes if mtf_result.trade_direction == 'LONG' else short_votes}/10)\n"
            msg += f"Razón: {mtf_result.reason}\n\n"
            
            # Entry/exit levels - FORMATO COPIABLE
            msg += "━━━ COPIAR ━━━\n\n"
            msg += f"Moneda: `{display}`\n"
            msg += f"Take Profit: `{format_price(tp1)}`\n"
            msg += f"Stop Loss: `{format_price(sl)}`\n\n"
        else:
            msg += "┏━ SEÑAL: ESPERAR ⏳\n\n"
            msg += f"{mtf_result.reason}\n\n"
        
        # Warnings
        if mtf_result.warnings:
            msg += "⚠️ Advertencias:\n"
            for w in mtf_result.warnings:
                msg += f"  {w}\n"
            msg += "\n"
        
        # Higher timeframe context
        msg += "━━━ Contexto ━━━\n"
        if mtf_result.tf_1h:
            trend_icon = "▲" if "ALCISTA" in mtf_result.tf_1h.trend else ("▼" if "BAJISTA" in mtf_result.tf_1h.trend else "▬")
            msg += f"  1H: {trend_icon} {mtf_result.tf_1h.trend}\n"
        if mtf_result.tf_4h:
            trend_icon = "▲" if "ALCISTA" in mtf_result.tf_4h.trend else ("▼" if "BAJISTA" in mtf_result.tf_4h.trend else "▬")
            msg += f"  4H: {trend_icon} {mtf_result.tf_4h.trend}\n"
        
        msg += f"\n⏰ {datetime.now().strftime('%H:%M:%S')}\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol_name}: {e}", exc_info=True)
        await loading_msg.edit_text(
            f"✗ Error: {str(e)}\n\n"
            f"Intenta de nuevo.",
            parse_mode=ParseMode.MARKDOWN
        )


# ========================
# CALLBACK HANDLER
# ========================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja todos los callbacks de botones"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "menu_inicio":
        await start_command(update, context)
    
    elif data == "view_monitored":
        await view_monitored_command(update, context)
    
    elif data == "analyze_other":
        msg = "┏━ ANÁLISIS MANUAL\n\n"
        msg += "Escribe el símbolo:\n\n"
        msg += "Ejemplos: BTC, ETH, SOL\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("analyze_"):
        symbol_name = data.replace("analyze_", "")
        await analyze_crypto_command(update, context, symbol_name=symbol_name)


# ========================
# MESSAGE HANDLER
# ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto (análisis directo)"""
    text = update.message.text.strip().upper()
    
    # Intentar analizar como símbolo
    if len(text) <= 10 and text.isalpha():
        await analyze_crypto_command(update, context, symbol_name=text)
    else:
        await update.message.reply_text(
            "Escribe un símbolo válido (BTC, ETH, SOL...)\n"
            "o usa /start para ver el menú",
            parse_mode=ParseMode.MARKDOWN
        )


# ========================
# MAIN
# ========================
def main():
    global client, auto_monitor, mtf_analyzer, auth_manager
    
    if not config.TELEGRAM_BOT_TOKEN or 'your_' in config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return
    
    print("Conectando a Binance...")
    try:
        client = get_client()
        mtf_analyzer = MultiTimeframeAnalyzer(client)
        auth_manager = AuthManager()
        print(f"✅ Conectado a Binance")
        print(f"✅ Estrategia MA7/MA25 + 10 indicadores lista")
        
    except Exception as e:
        print(f"ERROR: {e}")
        return
    
    print("Iniciando bot de Telegram...")
    
    app = (
        Application.builder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30)
        .build()
    )
    
    # Handlers
    start_handler = CommandHandler("start", start_command)
    callback_handler = CallbackQueryHandler(handle_callback)
    message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    
    app.add_handler(start_handler)
    app.add_handler(callback_handler)
    app.add_handler(message_handler)
    
    print("\n" + "="*40)
    print("BOT INICIADO")
    print("="*40)
    print("Menú: /start")
    print("Analizar: escribe BTC, ETH, etc.")
    print("="*40)
    print("Presiona Ctrl+C para detener\n")
    

    
    # Update chat_id when user sends /start
    original_start_callback = start_handler.callback
    
    async def start_with_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global auto_monitor, auth_manager
        
        user = update.effective_user
        if not user:
            return

        # Check authorization
        if not auth_manager.is_authorized(user.id):
            await update.message.reply_text(
                "⛔ *ACCESO DENEGADO*\n\n"
                "Para usar este bot, necesitas una llave de acceso.\n"
                "Por favor, envía tu llave a continuación.\n\n"
                "Ejemplo: `AAAA-BBBB-CCCC`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Add subscriber for monitor
        if auto_monitor and update.effective_chat:
            auto_monitor.add_subscriber(update.effective_chat.id)
            
            # Start monitoring if not already running
            if not auto_monitor.is_running:
                asyncio.create_task(auto_monitor.start())
                logger.info(f"Started auto-monitor process")
        
        # Call original start command
        await original_start_callback(update, context)
    
    # Replace start handler callback
    start_handler.callback = start_with_monitor
    
    # Wrap text handler for key redemption
    original_message_callback = message_handler.callback
    
    async def handle_message_with_auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global auth_manager, auto_monitor
        
        user = update.effective_user
        if not user:
            return

        # If not authorized, check if message is a key
        if not auth_manager.is_authorized(user.id):
            text = update.message.text.strip().upper()
            
            # Attempt access redemption
            if auth_manager.redeem_key(text, user.id):
                await update.message.reply_text(
                    "✅ *ACCESO CONCEDIDO*\n\n"
                    "Bienvenido. Ahora puedes usar el bot.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
                # Auto-register for signals
                if auto_monitor and update.effective_chat:
                    auto_monitor.add_subscriber(update.effective_chat.id)
                
                # Show main menu
                await start_command(update, context)
            else:
                await update.message.reply_text(
                    "❌ *LLAVE INVÁLIDA*\n\n"
                    "La llave no existe o ya fue usada.\n"
                    "Contacta al administrador.",
                    parse_mode=ParseMode.MARKDOWN
                )
            return
            
        # If authorized, proceed to normal handler
        await original_message_callback(update, context)

    # Replace message handler callback
    message_handler.callback = handle_message_with_auth

    
    # Initialize AutoMonitor (Global)
    print("🤖 Inicializando auto-monitor...")
    try:
        auto_monitor = AutoMonitor(config.TELEGRAM_BOT_TOKEN, chat_id=0)
        print("✅ Auto-monitor listo")
    except Exception as e:
        print(f"❌ Error al iniciar AutoMonitor: {e}")
    
    # Start auto-monitor task in background
    async def start_monitor_task(application):
        global auto_monitor
        if auto_monitor and not auto_monitor.is_running:
            asyncio.create_task(auto_monitor.start())
            logger.info("Auto-monitor task started via post_init")
    
    app.post_init = start_monitor_task
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\nBot detenido por el usuario")
        if auto_monitor:
            auto_monitor.stop()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
