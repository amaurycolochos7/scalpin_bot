"""
Trading Bot Telegram - Versión Simplificada
Solo 2 opciones: Analizar Moneda + Escanear Mercado (lotes de 20)
Estrategia MA7x25 estricta
"""
import asyncio
import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from telegram.constants import ParseMode

from src.config import config
from src.binance_client import get_client
from src.ma_strategy import MAStrategy

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global
client = None
BATCH_SIZE = 20  # Lotes de 20 criptos

# Cache para lotes
market_batches = {
    'symbols': [],        # Lista completa de símbolos
    'batches': [],        # Lista dividida en lotes
    'results': {},        # Resultados por lote
    'current_batch': 0,   # Lote actual en análisis
    'analyzing': False,
}


def format_price(price: float) -> str:
    """Formatea precio según su magnitud"""
    if price >= 1000:
        return f"${price:,.2f}"
    elif price >= 1:
        return f"${price:.4f}"
    else:
        return f"${price:.8f}"


def create_progress_bar(current: int, total: int, width: int = 15) -> str:
    """Crea barra de progreso Unicode"""
    progress = current / total if total > 0 else 0
    filled = int(progress * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(progress * 100)
    return f"▐{bar}▌ {pct}%"


# ========================
# MENÚ PRINCIPAL
# ========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menú principal - Solo 2 botones"""
    keyboard = [
        [InlineKeyboardButton("📊 Analizar Moneda", callback_data="menu_analizar")],
        [InlineKeyboardButton("🔍 Escanear Mercado", callback_data="menu_escanear")],
        [InlineKeyboardButton("🚀 Analizar Todas", callback_data="scan_all_auto")]
    ]
    
    msg = "┏━━━━━━━━━━━━━━━━━━━━┓\n"
    msg += "┃  TRADING BOT PRO   ┃\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
    
    msg += "Bot de trading con estrategia MA7x25.\n\n"
    
    msg += "┏━ OPCIONES\n\n"
    msg += "➣ *Analizar Moneda*\n"
    msg += "   Escribe: BTC, ETH, SOL...\n\n"
    msg += "➣ *Escanear Mercado*\n"
    msg += "   Elige lotes manualmente\n\n"
    msg += "➣ *Analizar Todas*\n"
    msg += "   Escaneo automático completo\n\n"
    msg += "┗━━━━━━━━━━━━━━━━━━━━"
    
    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    elif update.callback_query:
        await update.callback_query.message.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))


# ========================
# ANALIZAR MONEDA
# ========================
async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analiza una moneda específica con estrategia MA7x25"""
    global client
    
    # Obtener mensaje origen
    if update.callback_query:
        msg_obj = update.callback_query.message
    else:
        msg_obj = update.message
    
    # Obtener símbolo
    symbol_input = None
    if context.args and len(context.args) > 0:
        symbol_input = context.args[0]
    elif update.message and update.message.text:
        text = update.message.text.strip()
        if not text.startswith('/'):
            symbol_input = text
    
    if not symbol_input:
        await msg_obj.reply_text(
            "┏━ ANALIZAR MONEDA\n\n"
            "Escribe el nombre de la moneda:\n\n"
            "Ejemplos: BTC, ETH, SOL\n\n"
            "┗━━━━━━━━━━━━━━━━━━━━",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]])
        )
        return
    
    # Normalizar símbolo
    symbol = client.normalize_symbol(symbol_input)
    
    if symbol is None:
        await msg_obj.reply_text(
            f"✗ {symbol_input} no existe en Binance Futures",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]])
        )
        return
    
    display = client.get_display_symbol(symbol).replace('/USDT', '')
    
    # Mensaje de carga
    loading_msg = await msg_obj.reply_text(
        f"┏━ Analizando {display}\n\n"
        f"▸ Usando estrategia MA7x25...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Analizar con estrategia MA7x25
        strategy = MAStrategy()
        signal = strategy.get_expert_signal(symbol)
        
        if signal:
            # ¡Hay señal!
            if signal['signal'] == 'LONG':
                action = "COMPRAR ▲"
            else:
                action = "VENDER ▼"
            
            msg = f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
            msg += f"┃   {display:^14}   ┃\n"
            msg += f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            
            msg += f"Precio: {format_price(signal['entry_price'])}\n\n"
            
            msg += f"┏━ SEÑAL: *{action}*\n\n"
            
            msg += f"Confianza: {signal['confidence']}\n\n"
            
            msg += "Niveles:\n"
            msg += f"  Entrada → {format_price(signal['entry_price'])}\n"
            msg += f"  Stop   → {format_price(signal['sl_price'])} (±10%)\n"
            msg += f"  Target → {format_price(signal['tp_price'])} (±10%)\n\n"
            
            msg += "Validación:\n"
            msg += "  ✓ MA7 x MA25: Confirmado\n"
            msg += f"  ✓ Tendencia 4H: {signal['4h_trend']}\n"
            msg += f"  ✓ TradingView: {signal['tradingview']['summary']}\n\n"
            
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
            
        else:
            # Sin señal
            ticker = client.get_ticker(symbol)
            
            msg = f"┏━━━━━━━━━━━━━━━━━━━━┓\n"
            msg += f"┃   {display:^14}   ┃\n"
            msg += f"┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
            
            msg += f"Precio: {format_price(ticker['price'])}\n\n"
            
            msg += "┏━ SEÑAL: *ESPERAR* ▬\n\n"
            msg += "No hay cruce MA7 x MA25\n"
            msg += "o no hay confirmación 4H\n\n"
            
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
        await loading_msg.edit_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)


# ========================
# ESCANEAR MERCADO
# ========================
async def scan_market_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra lotes disponibles para escanear"""
    global client, market_batches
    
    if update.callback_query:
        msg_obj = update.callback_query.message
    else:
        msg_obj = update.message
    
    loading_msg = await msg_obj.reply_text(
        "┏━ ESCANEAR MERCADO\n\n"
        "▸ Obteniendo lista de criptos...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Obtener TODOS los símbolos de futuros
        all_symbols = client.get_all_futures_symbols()
        total = len(all_symbols)
        
        # Dividir en lotes de 20
        batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
        num_batches = len(batches)
        
        # Guardar en cache
        market_batches['symbols'] = all_symbols
        market_batches['batches'] = batches
        market_batches['results'] = {}
        
        # Crear botones para cada lote
        keyboard = []
        for i in range(num_batches):
            start = i * BATCH_SIZE + 1
            end = min((i + 1) * BATCH_SIZE, total)
            btn_text = f"Lote {i + 1}: #{start}-#{end}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"scan_batch_{i}")])
        
        keyboard.append([InlineKeyboardButton("← Inicio", callback_data="menu_inicio")])
        
        msg = "┏━━━━━━━━━━━━━━━━━━━━┓\n"
        msg += "┃  ESCANEAR MERCADO  ┃\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━┛\n\n"
        
        msg += f"Total: *{total}* criptomonedas\n"
        msg += f"Lotes: *{num_batches}* (de {BATCH_SIZE} cada uno)\n\n"
        
        msg += "┏━ SELECCIONA UN LOTE\n\n"
        msg += "Cada lote analiza 20 criptos\n"
        msg += "con estrategia MA7x25\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        await loading_msg.edit_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in scan: {e}", exc_info=True)
        await loading_msg.edit_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)


async def analyze_batch(update: Update, context: ContextTypes.DEFAULT_TYPE, batch_index: int):
    """Analiza un lote específico de criptos"""
    global client, market_batches
    
    query = update.callback_query
    
    if batch_index >= len(market_batches['batches']):
        await query.edit_message_text("✗ Lote no válido", parse_mode=ParseMode.MARKDOWN)
        return
    
    batch = market_batches['batches'][batch_index]
    total = len(batch)
    
    # Mensaje inicial
    start_num = batch_index * BATCH_SIZE + 1
    end_num = start_num + total - 1
    
    await query.edit_message_text(
        f"┏━ LOTE {batch_index + 1}: #{start_num}-#{end_num}\n\n"
        f"{create_progress_bar(0, total)}\n\n"
        f"▸ Iniciando análisis...\n\n"
        "┗━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        strategy = MAStrategy()
        results = []
        
        for idx, symbol in enumerate(batch):
            try:
                # Actualizar progreso cada 5
                if idx % 3 == 0:
                    bar = create_progress_bar(idx + 1, total)
                    display = client.get_display_symbol(symbol).replace('/USDT', '')
                    
                    await query.edit_message_text(
                        f"┏━ LOTE {batch_index + 1}: #{start_num}-#{end_num}\n\n"
                        f"{bar}\n\n"
                        f"▸ Analizando {display}...\n\n"
                        "┗━━━━━━━━━━━━━━━━━━━━",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Analizar con estrategia MA7x25
                signal = await asyncio.to_thread(strategy.get_expert_signal, symbol)
                
                if signal:
                    results.append({
                        'symbol': symbol,
                        'signal': signal,
                        'display': client.get_display_symbol(symbol).replace('/USDT', '')
                    })
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Guardar resultados
        market_batches['results'][batch_index] = results
        
        # Mostrar resultados
        if not results:
            msg = f"┏━ LOTE {batch_index + 1} COMPLETADO\n\n"
            msg += "No se encontraron señales\n"
            msg += "La estrategia MA7x25 es estricta\n\n"
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
            
            keyboard = [
                [InlineKeyboardButton("← Volver a lotes", callback_data="menu_escanear")],
                [InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]
            ]
        else:
            msg = f"┏━ LOTE {batch_index + 1} COMPLETADO\n\n"
            msg += f"Señales encontradas: *{len(results)}*\n\n"
            
            for r in results[:10]:  # Máximo 10
                s = r['signal']
                action = "COMPRAR" if s['signal'] == 'LONG' else "VENDER"
                msg += f"▸ *{r['display']}*: {action}\n"
                msg += f"   Entrada: {format_price(s['entry_price'])}\n\n"
            
            if len(results) > 10:
                msg += f"_...y {len(results) - 10} más_\n\n"
            
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
            
            # Botones para analizar cada resultado
            keyboard = []
            for r in results[:5]:
                keyboard.append([InlineKeyboardButton(
                    f"📊 Analizar {r['display']}", 
                    callback_data=f"do_analyze_{r['display']}"
                )])
            
            keyboard.append([InlineKeyboardButton("← Volver a lotes", callback_data="menu_escanear")])
            keyboard.append([InlineKeyboardButton("← Inicio", callback_data="menu_inicio")])
        
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in batch analysis: {e}", exc_info=True)
        await query.edit_message_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)


# ========================
# ANALIZAR TODAS (AUTOMÁTICO)
# ========================
async def scan_all_auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Analiza TODAS las criptos automáticamente y notifica señales en tiempo real"""
    global client, market_batches
    
    query = update.callback_query
    
    # Obtener TODOS los símbolos
    all_symbols = client.get_all_futures_symbols()
    total = len(all_symbols)
    batches = [all_symbols[i:i + BATCH_SIZE] for i in range(0, len(all_symbols), BATCH_SIZE)]
    num_batches = len(batches)
    
    # Mensaje inicial
    await query.edit_message_text(
        f"┏━ ANÁLISIS AUTOMÁTICO COMPLETO\n\n"
        f"Total: *{total}* criptos\n"
        f"Lotes: *{num_batches}* de {BATCH_SIZE}\n\n"
        f"{create_progress_bar(0, num_batches)}\n\n"
        f"▸ Iniciando escaneo automático...\n\n"
        "┗━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        strategy = MAStrategy()
        all_signals = []
        
        for batch_idx, batch in enumerate(batches):
            # Actualizar progreso
            bar = create_progress_bar(batch_idx, num_batches)
            start_num = batch_idx * BATCH_SIZE + 1
            end_num = start_num + len(batch) - 1
            
            await query.edit_message_text(
                f"┏━ ANÁLISIS AUTOMÁTICO\n\n"
                f"{bar}\n\n"
                f"Lote {batch_idx + 1}/{num_batches}: #{start_num}-#{end_num}\n"
                f"Señales encontradas: *{len(all_signals)}*\n\n"
                f"▸ Analizando...\n\n"
                "┗━━━━━━━━━━━━━━━━━━━━",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Analizar el lote
            for symbol in batch:
                try:
                    signal = await asyncio.to_thread(strategy.get_expert_signal, symbol)
                    
                    if signal:
                        display = client.get_display_symbol(symbol).replace('/USDT', '')
                        all_signals.append({
                            'symbol': symbol,
                            'signal': signal,
                            'display': display
                        })
                        
                        # ⚡ NOTIFICAR INMEDIATAMENTE
                        action = "COMPRAR ▲" if signal['signal'] == 'LONG' else "VENDER ▼"
                        notification = f"🔔 *SEÑAL ENCONTRADA*\n\n"
                        notification += f"*{display}*: {action}\n"
                        notification += f"Entrada: {format_price(signal['entry_price'])}\n"
                        notification += f"Stop: {format_price(signal['sl_price'])}\n"
                        notification += f"Target: {format_price(signal['tp_price'])}\n\n"
                        notification += f"Lote {batch_idx + 1}, Total: {len(all_signals)}"
                        
                        # Enviar notificación separada
                        await context.bot.send_message(
                            chat_id=query.message.chat_id,
                            text=notification,
                            parse_mode=ParseMode.MARKDOWN
                        )
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    continue
        
        # Resumen final
        final_msg = f"┏━ ANÁLISIS COMPLETO ✅\n\n"
        final_msg += f"Total analizadas: *{total}*\n"
        final_msg += f"Señales encontradas: *{len(all_signals)}*\n\n"
        
        if all_signals:
            final_msg += "┏━ RESUMEN DE SEÑALES\n\n"
            for r in all_signals[:10]:
                s = r['signal']
                action = "COMPRAR" if s['signal'] == 'LONG' else "VENDER"
                final_msg += f"▸ *{r['display']}*: {action}\n"
            
            if len(all_signals) > 10:
                final_msg += f"\n_...y {len(all_signals) - 10} más_\n"
        else:
            final_msg += "No se encontraron señales.\n"
            final_msg += "La estrategia MA7x25 es estricta.\n"
        
        final_msg += "\n┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await query.edit_message_text(final_msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
        
    except Exception as e:
        logger.error(f"Error in auto scan: {e}", exc_info=True)
        await query.edit_message_text(f"✗ Error: {str(e)}", parse_mode=ParseMode.MARKDOWN)


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
    
    elif data == "scan_all_auto":
        await scan_all_auto(update, context)
    
    elif data == "menu_analizar":
        msg = "┏━ ANALIZAR MONEDA\n\n"
        msg += "Escribe el nombre de la moneda:\n\n"
        msg += "Ejemplos:\n"
        msg += "  → BTC\n"
        msg += "  → ETH\n"
        msg += "  → SOL\n\n"
        msg += "┗━━━━━━━━━━━━━━━━━━━━"
        
        keyboard = [[InlineKeyboardButton("← Inicio", callback_data="menu_inicio")]]
        await query.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_escanear":
        await scan_market_command(update, context)
    
    elif data.startswith("scan_batch_"):
        batch_idx = int(data.replace("scan_batch_", ""))
        await analyze_batch(update, context, batch_idx)
    
    elif data.startswith("do_analyze_"):
        symbol = data.replace("do_analyze_", "")
        context.args = [symbol]
        await analyze_command(update, context)


# ========================
# MESSAGE HANDLER
# ========================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Maneja mensajes de texto (análisis directo)"""
    text = update.message.text.strip().upper()
    
    # Intentar analizar como símbolo
    if len(text) <= 10 and text.isalpha():
        context.args = [text]
        await analyze_command(update, context)
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
    global client
    
    if not config.TELEGRAM_BOT_TOKEN or 'your_' in config.TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN no configurado")
        return
    
    print("Conectando a Binance...")
    try:
        client = get_client()
        
        # Mostrar estadísticas
        all_symbols = client.get_all_futures_symbols()
        print(f"OK - {len(all_symbols)} pares de futuros disponibles")
        print(f"OK - {len(all_symbols) // BATCH_SIZE + 1} lotes de {BATCH_SIZE}")
        
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
    app.add_handler(CommandHandler("analizar", analyze_command))
    app.add_handler(CommandHandler("a", analyze_command))
    app.add_handler(CommandHandler("escanear", scan_market_command))
    app.add_handler(CommandHandler("scan", scan_market_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("\n" + "="*40)
    print("BOT INICIADO")
    print("="*40)
    print("Menú: /start")
    print("Analizar: escribe BTC, ETH, etc.")
    print("Escanear: /escanear")
    print("="*40)
    print("Presiona Ctrl+C para detener\n")
    
    try:
        app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    except KeyboardInterrupt:
        print("\nBot detenido por el usuario")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
