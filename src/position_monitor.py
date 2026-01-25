"""
Monitoreo continuo de posiciones activas
Verifica precio cada 60 segundos y envía alertas
"""

import asyncio
from datetime import datetime
from typing import Optional
import ccxt
from telegram import Bot

from src.position_tracker import PositionTracker
from src.ma_strategy import MAStrategy
from src.config import Config


class PositionMonitor:
    """Monitorea posiciones activas y envía alertas"""
    
    def __init__(self, chat_id: int):
        self.chat_id = chat_id
        self.tracker = PositionTracker()
        self.strategy = MAStrategy()
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.is_running = False
        self.last_pnl_percent = 0  # Para detectar cambios significativos
    
    async def start_monitoring(self):
        """Inicia el monitoreo continuo"""
        self.is_running = True
        print(f"▸ Monitoreo iniciado para chat_id: {self.chat_id}")
        
        while self.is_running:
            try:
                await self._check_active_position()
                await asyncio.sleep(60)  # Esperar 60 segundos
            except Exception as e:
                print(f"Error en monitoreo: {str(e)}")
                await asyncio.sleep(60)
    
    async def stop_monitoring(self):
        """Detiene el monitoreo"""
        self.is_running = False
        print(f"▸ Monitoreo detenido para chat_id: {self.chat_id}")
    
    async def _check_active_position(self):
        """Verifica posición activa y envía alertas si es necesario"""
        position = self.tracker.get_active_position()
        
        if not position:
            return  # No hay posición activa
        
        try:
            symbol = position['symbol']
            direction = position['direction']
            entry_price = position['entry_price']
            sl_price = position['sl_price']
            tp_price = position['tp_price']
            
            # Obtener precio actual
            ticker = self.strategy.exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calcular P&L
            pnl_data = self.tracker.calculate_pnl(position, current_price)
            pnl_percent = pnl_data['pnl_percent']
            
            # ========== VERIFICAR ALERTAS ==========
            
            # 1. TP alcanzado
            if direction == 'LONG' and current_price >= tp_price:
                await self._send_tp_alert(position, current_price, pnl_data)
                return
            elif direction == 'SHORT' and current_price <= tp_price:
                await self._send_tp_alert(position, current_price, pnl_data)
                return
            
            # 2. SL alcanzado
            if direction == 'LONG' and current_price <= sl_price:
                await self._send_sl_alert(position, current_price, pnl_data)
                return
            elif direction == 'SHORT' and current_price >= sl_price:
                await self._send_sl_alert(position, current_price, pnl_data)
                return
            
            # 3. Cruce de MAs en contra
            await self._check_reverse_cross(position, current_price, pnl_data)
            
            # 4. Actualización de P&L cada +/-3% o +/-5%
            pnl_change = abs(pnl_percent - self.last_pnl_percent)
            if pnl_change >= 3.0:  # Cambio significativo
                await self._send_pnl_update(position, current_price, pnl_data)
                self.last_pnl_percent = pnl_percent
        
        except Exception as e:
            print(f"Error verificando posición: {str(e)}")
    
    async def _send_tp_alert(self, position: dict, current_price: float, pnl_data: dict):
        """Envía alerta de TP alcanzado"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message = f"""
🎉 TP ALCANZADO - {position['symbol']}

Precio actual: ${current_price:,.2f}
P&L: {pnl_data['pnl_percent']:+.2f}% (${pnl_data['pnl_usd']:+,.2f})

Objetivo cumplido! 🎯

¿Cerraste la posición?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Cerré posición", callback_data=f"close_{position['id']}_TP")],
            [InlineKeyboardButton("⏳ Dejo correr", callback_data=f"keep_{position['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def _send_sl_alert(self, position: dict, current_price: float, pnl_data: dict):
        """Envía alerta de SL alcanzado"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        message = f"""
⛔ STOP LOSS ALCANZADO - {position['symbol']}

Precio actual: ${current_price:,.2f}
P&L: {pnl_data['pnl_percent']:+.2f}% (${pnl_data['pnl_usd']:+,.2f})

Cortar pérdidas rápido! ✂️

¿Cerraste la posición?
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ Cerré posición", callback_data=f"close_{position['id']}_SL")],
            [InlineKeyboardButton("⏳ Esperar", callback_data=f"keep_{position['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def _check_reverse_cross(self, position: dict, current_price: float, pnl_data: dict):
        """Verifica si hubo cruce de MAs en contra"""
        try:
            symbol = position['symbol']
            direction = position['direction']
            
            # Obtener velas recientes de 15M
            ohlcv = self.strategy.exchange.fetch_ohlcv(symbol, '15m', limit=50)
            import pandas as pd
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Detectar cruce
            ma_cross = self.strategy.calculate_ma_cross(df)
            
            # Si hay cruce en contra, alertar
            if direction == 'LONG' and ma_cross.get('cross') == 'bearish':
                await self._send_reverse_cross_alert(position, current_price, pnl_data, 'bearish')
            elif direction == 'SHORT' and ma_cross.get('cross') == 'bullish':
                await self._send_reverse_cross_alert(position, current_price, pnl_data, 'bullish')
        
        except Exception as e:
            print(f"Error verificando cruce: {str(e)}")
    
    async def _send_reverse_cross_alert(self, position: dict, current_price: float, 
                                       pnl_data: dict, cross_type: str):
        """Envía alerta de cruce contrario"""
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        cross_text = "ABAJO" if cross_type == 'bearish' else "ARRIBA"
        
        message = f"""
⚠️ ALERTA - {position['symbol']}

MA7 cruzó {cross_text} de MA25
Señal contraria detectada! 🔄

Precio actual: ${current_price:,.2f}
P&L actual: {pnl_data['pnl_percent']:+.2f}% (${pnl_data['pnl_usd']:+,.2f})

Considera cerrar posición para proteger {"ganancia" if pnl_data['status'] == 'profit' else "capital"}.

¿Qué haces?
"""
        
        keyboard = [
            [InlineKeyboardButton("🔴 Cerrar posición", callback_data=f"close_{position['id']}_CROSS")],
            [InlineKeyboardButton("⏳ Seguir", callback_data=f"keep_{position['id']}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message,
            reply_markup=reply_markup
        )
    
    async def _send_pnl_update(self, position: dict, current_price: float, pnl_data: dict):
        """Envía actualización de P&L"""
        emoji = "📈" if pnl_data['status'] == 'profit' else "📉"
        
        message = f"""
{emoji} {position['symbol']} - Actualización

Precio: ${current_price:,.2f}
P&L: {pnl_data['pnl_percent']:+.2f}% (${pnl_data['pnl_usd']:+,.2f})

Estado: {"En ganancia ✓" if pnl_data['status'] == 'profit' else "En pérdida"}
"""
        
        await self.bot.send_message(
            chat_id=self.chat_id,
            text=message
        )


# Instancia global para gestionar el monitor
_active_monitor: Optional[PositionMonitor] = None

async def start_position_monitor(chat_id: int):
    """Inicia el monitoreo global"""
    global _active_monitor
    
    if _active_monitor and _active_monitor.is_running:
        await _active_monitor.stop_monitoring()
    
    _active_monitor = PositionMonitor(chat_id)
    await _active_monitor.start_monitoring()

async def stop_position_monitor():
    """Detiene el monitoreo global"""
    global _active_monitor
    
    if _active_monitor:
        await _active_monitor.stop_monitoring()
        _active_monitor = None
