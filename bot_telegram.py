"""
Scalping Bot ML - Auto-Monitor Version
Simplified 2-button interface with automatic 24/7 monitoring
"""
import asyncio
import logging
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from src.config import config
from src.binance_client import get_client
from src.auto_monitor import AutoMonitor
from src.ml_config import MLConfig

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global
client = None
auto_monitor = None


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
        [InlineKeyboardButton("📊 Criptomonedas Monitoreadas", callback_data="view_monitored")],
        [InlineKeyboardButton("🔍 Analizar Otra Moneda", callback_data="analyze_other")]
    ]
    
    # Get monitor status
    status = auto_monitor.get_status() if auto_monitor else {'is_running': False, 'monitored_count': 0}
    
    msg = "┏━━━━━━━━━━━━━━━━━━━━┓\n"
    msg += "┃  SCALPING BOT ML   ┃\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    msg += "Monitoreo automático 24/7\n"
    msg += "Top 20 en Futuros Binance\n\n"
    
    if status['is_running']:
        msg += f"🟢 *Estado:* ACTIVO\n"
        msg += f"📊 *Monitoreando:* {status['monitored_count']} criptos\n"
        msg += f"⏱️ *Escaneo:* Cada 5 minutos\n\n"
    else:
        msg += f"🔴 *Estado:* INICIALIZANDO...\n\n"
    
    msg += "┏━ OPCIONES\n\n"
    msg += "➣ *Criptomonedas Monitoreadas*\n"
    msg += "   Ver Top 20 + análisis actual\n\n"
    msg += "➣ *Analizar Otra Moneda*\n"
    msg += "   Análisis manual de cualquier cripto\n\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━"
    
    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


# ========================
# VER MONEDAS MONITOREADAS
# ========================
async def view_monitored_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra lista de criptomonedas monitoreadas"""
    query = update.callback_query if update.callback_query else None
    
    if query:
        await query.answer()
    
    loading_msg = "┏━ CRIPTOMONEDAS MONITOREADAS\n\n▸ Cargando..."
    
    if query:
        await query.edit_message_text(loading_msg, parse_mode=ParseMode.MARKDOWN)
        msg_obj = query.message
    else:
        msg_obj = await update.message.reply_text(loading_msg, parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Get monitored symbols
        status = auto_monitor.get_status()
        
        if not status['monitored_symbols']:
            msg = "┏━ CRIPTOMONEDAS MONITOREADAS\n\n"
            msg += "❌ No hay modelos entrenados\n\n"
            msg += "Ejecuta primero:\n"
            msg += "  python train_all_models.py\n\n"
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
            
            keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
            await msg_obj.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        msg = "┏━ CRIPTOMONEDAS MONITOREADAS\n\n"
        msg += f"Total: *{len(status['monitored_symbols'])}* modelos\n"
        msg += f"Actualización: *Hace {datetime.now().strftime('%H:%M')}*\n\n"
        
        # Create buttons for each crypto
        keyboard = []
        for i, symbol in enumerate(status['monitored_symbols'][:20], 1):
            keyboard.append([InlineKeyboardButton(
                f"📊 {symbol}",
                callback_data=f"analyze_{symbol}"
            )])
        
        keyboard.append([InlineKeyboardButton("← Inicio", callback_data="menu_inicio")])
        
        msg += "Selecciona una moneda para\n"
        msg += "ver su análisis actual:\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        await msg_obj.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in view_monitored: {e}", exc_info=True)
        await msg_obj.edit_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)


# ========================
# ANALIZAR MONEDA
# ========================
async def analyze_crypto_command(update: Update, context: ContextTypes.DEFAULT_TYPE, symbol_name: str = None):
    """Analiza una crip tomoneda específica"""
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
        f"▸ Calculando features...\n"
        f"▸ Prediciendo con ML...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Analyze using auto_monitor
        symbol_info = {
            'symbol': symbol,
            'name': symbol_name,
            'model_path': os.path.join(MLConfig.MODEL_DIR, symbol_name)
        }
        
        result = await auto_monitor.analyze_single(symbol_info)
        
        if not result:
            await loading_msg.edit_text(f"✗ Error al analizar {display}", parse_mode=ParseMode.MARKDOWN)
            return
        
        # Format message
        prob = result['ml_probability']
        prob_emoji = "✅✅" if prob >= 97 else "✅" if prob >= 95 else "⚠️"
        
        msg = f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
        msg += f"┃   {display:^14}   ┃\n"
        msg += f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        msg += f"Precio: {format_price(result['entry_price'])}\n\n"
        
        msg += f"┏━ PREDICCIÓN ML\n\n"
        msg += f"Probabilidad: *{prob:.1f}%* {prob_emoji}\n"
        msg += f"Score Técnico: {result['technical_score']}/100\n\n"
        
        if result['signal']:
            action = "COMPRAR ▲" if result['signal'] == 'LONG' else "VENDER ▼"
            msg += f"Señal: *{action}*\n\n"
            
            msg += "Niveles:\n"
            msg += f"  Entry → {format_price(result['entry_price'])}\n"
            msg += f"  TP    → {format_price(result['tp_price'])} (+{result['tp_percent']:.1f}%)\n"
            msg += f"  SL    → {format_price(result['sl_price'])} (-{result['sl_percent']:.1f}%)\n\n"
        else:
            msg += "Señal: *ESPERAR* ▬\n"
            msg += f"(Probabilidad < {MLConfig.PROBABILITY_THRESHOLD*100:.0f}%)\n\n"
        
        msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol_name}: {e}", exc_info=True)
        await loading_msg.edit_text(
            f"✗ Error: {str(e)}\n\n"
            f"Puede que {symbol_name} no tenga modelo entrenado.",
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
    global client, auto_monitor
    
    if not config.TELEGRAM_BOT_TOKEN or 'your_' in config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return
    
    print("Conectando a Binance...")
    try:
        client = get_client()
        print(f"✅ Conectado a Binance")
        
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
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n" + "="*40)
    print("BOT INICIADO")
    print("="*40)
    print("Menú: /start")
    print("Analizar: escribe BTC, ETH, etc.")
    print("="*40)
    print("Presiona Ctrl+C para detener\n")
    
    # Start auto-monitor in background
    async def start_monitor(application):
        global auto_monitor
        
        print("🤖 Inicializando auto-monitor...")
        # Monitor will get chat_id when user sends /start
        auto_monitor = AutoMonitor(config.TELEGRAM_BOT_TOKEN, chat_id=0)
        print("✅ Auto-monitor listo")
    
    # Update chat_id when user sends /start
    original_start = app.handlers[0][0].callback
    
    async def start_with_monitor(update: Update, context: ContextTypes.DEFAULT_TYPE):
        global auto_monitor
        
        # Set chat_id for monitor
        if auto_monitor and update.effective_chat:
            auto_monitor.chat_id = update.effective_chat.id
            
            # Start monitoring if not already running
            if not auto_monitor.is_running:
                asyncio.create_task(auto_monitor.start())
                logger.info(f"Started auto-monitor for chat_id: {update.effective_chat.id}")
        
        # Call original start command
        await original_start(update, context)
    
    # Replace start handler with wrapped version
    app.handlers[0][0].callback = start_with_monitor
    
    app.post_init = start_monitor
    
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
