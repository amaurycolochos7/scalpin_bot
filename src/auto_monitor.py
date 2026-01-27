"""
Auto-Monitor System - MA7/MA25 Strategy
Continuously monitors ALL Binance Futures cryptos for crossover signals
Sends automatic Telegram alerts when:
  - MA7/MA25 crossover happens
  - 7/10 TradingView indicators confirm
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from telegram import Bot
from src.binance_client import get_client
from src.technical_analysis import TechnicalAnalyzer

# Mexico/Chiapas timezone (UTC-6)
MEXICO_TZ = timezone(timedelta(hours=-6))



logger = logging.getLogger(__name__)


class AutoMonitor:
    """
    Automatic monitoring system using MA7/MA25 crossover strategy
    Scans ALL Binance Futures cryptos and alerts on trading opportunities
    """
    
    def __init__(self, bot_token: str, chat_id: int):
        """
        Initialize monitor
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID to send notifications
        """
        self.bot = Bot(token=bot_token)
        self.subscribers = set()
        if chat_id:
            self.subscribers.add(chat_id)
            
        self.client = get_client()
        self.is_running = False
        self.monitored_symbols = []
        
        # Persistence file
        self.subscribers_file = "subscribers.json"
        self._load_subscribers()
        
        # Track signals to avoid spam
        self.last_signals = {}  # {symbol: {'signal': 'LONG/SHORT', 'time': datetime}}
        
        # Scan interval (5 minutes since we use 15m candles)
        self.scan_interval = 300  # 5 minutes
        
        # Minimum votes required (7/10 rule)
        self.min_votes = 6  # At least 6/10 for alert (7 for strong)
        
        logger.info("AutoMonitor initialized with MA7/MA25 strategy")

    def _load_subscribers(self):
        """Load subscribers from JSON file"""
        import json
        import os
        try:
            if os.path.exists(self.subscribers_file):
                with open(self.subscribers_file, 'r') as f:
                    data = json.load(f)
                    self.subscribers = set(data.get('subscribers', []))
                logger.info(f"Loaded {len(self.subscribers)} subscribers")
        except Exception as e:
            logger.error(f"Error loading subscribers: {e}")

    def _save_subscribers(self):
        """Save subscribers to JSON file"""
        import json
        try:
            with open(self.subscribers_file, 'w') as f:
                json.dump({'subscribers': list(self.subscribers)}, f)
        except Exception as e:
            logger.error(f"Error saving subscribers: {e}")

    def add_subscriber(self, chat_id: int):
        """Add a new subscriber"""
        if chat_id not in self.subscribers:
            self.subscribers.add(chat_id)
            self._save_subscribers()
            logger.info(f"New subscriber added: {chat_id}")
            return True
        return False

    
    def _load_all_futures_symbols(self) -> List[str]:
        """Load ALL available USDT perpetual futures symbols from Binance"""
        try:
            symbols = self.client.get_all_futures_symbols()
            logger.info(f"Loaded {len(symbols)} futures symbols from Binance")
            return symbols
        except Exception as e:
            logger.error(f"Error loading futures symbols: {e}")
            return []
    
    async def analyze_symbol(self, symbol: str) -> Optional[Dict]:
        """
        Analyze a single symbol using CANDLE COLOR STRATEGY
        
        Strategy (friend's method):
        1. Revisar velas de 4H (tendencia principal)
        2. Revisar velas de 1H (confirmación intermedia)
        3. Revisar velas de 15m: 3+ velas del mismo color = cambio confirmado
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            
        Returns:
            Analysis result dict or None if no signal
        """
        try:
            # Get symbol name for display
            symbol_name = symbol.replace('/USDT:USDT', 'USDT').replace('/USDT', 'USDT')
            
            # ========== 15M ANALYSIS (CONFIRMATION) ==========
            df_15m = self.client.get_ohlcv(symbol, '15m', limit=100)
            if df_15m is None or len(df_15m) < 30:
                return None
            
            analyzer_15m = TechnicalAnalyzer(df_15m)
            analyzer_15m.calculate_all_indicators()
            crossover = analyzer_15m.detect_ma_crossover()
            tv_votes = analyzer_15m.get_tradingview_votes()
            candle_15m = analyzer_15m.detect_candle_color_trend(lookback=6)
            
            current_price = df_15m['close'].iloc[-1]
            
            # ========== 1H ANALYSIS (INTERMEDIATE) ==========
            trend_1h = 'NONE'
            candle_1h = {'trend_change': 'NONE', 'candle_colors': '', 'consecutive_green': 0, 'consecutive_red': 0}
            try:
                df_1h = self.client.get_ohlcv(symbol, '1h', limit=50)
                if df_1h is not None and len(df_1h) >= 10:
                    analyzer_1h = TechnicalAnalyzer(df_1h)
                    analyzer_1h.calculate_all_indicators()
                    ma_1h = analyzer_1h.detect_ma_crossover()
                    candle_1h = analyzer_1h.detect_candle_color_trend(lookback=6)
                    
                    if 'LONG' in ma_1h['signal'] or ma_1h['ma7'] > ma_1h['ma25']:
                        trend_1h = 'BULLISH'
                    elif 'SHORT' in ma_1h['signal'] or ma_1h['ma7'] < ma_1h['ma25']:
                        trend_1h = 'BEARISH'
            except:
                pass
            
            # ========== 4H ANALYSIS (MAIN TREND) ==========
            trend_4h = 'NONE'
            candle_4h = {'trend_change': 'NONE', 'candle_colors': '', 'consecutive_green': 0, 'consecutive_red': 0}
            try:
                df_4h = self.client.get_ohlcv(symbol, '4h', limit=50)
                if df_4h is not None and len(df_4h) >= 10:
                    analyzer_4h = TechnicalAnalyzer(df_4h)
                    analyzer_4h.calculate_all_indicators()
                    ma_4h = analyzer_4h.detect_ma_crossover()
                    candle_4h = analyzer_4h.detect_candle_color_trend(lookback=6)
                    
                    if 'LONG' in ma_4h['signal'] or ma_4h['ma7'] > ma_4h['ma25']:
                        trend_4h = 'BULLISH'
                    elif 'SHORT' in ma_4h['signal'] or ma_4h['ma7'] < ma_4h['ma25']:
                        trend_4h = 'BEARISH'
            except:
                pass
            
            # ========== DECISION LOGIC (CANDLE COLOR STRATEGY) ==========
            candle_trend = candle_15m.get('trend_change', 'NONE')
            candle_confirmed = candle_15m.get('confirmed', False)
            consecutive = max(candle_15m.get('consecutive_green', 0), candle_15m.get('consecutive_red', 0))
            
            should_alert = False
            signal_type = None
            signal_strength = 'normal'
            reason = ''
            
            # LONG / COMPRA: 3+ green candles + timeframes aligned
            if candle_trend == 'BULLISH' and candle_confirmed:
                if trend_4h == 'BULLISH' and trend_1h == 'BULLISH':
                    should_alert = True
                    signal_type = 'LONG'
                    signal_strength = 'confirmed'
                    reason = f'✅ COMPRA / LONG confirmado\n   4H: ▲ | 1H: ▲ | 15m: {consecutive} velas verdes'
                elif trend_4h == 'BULLISH':
                    should_alert = True
                    signal_type = 'LONG'
                    signal_strength = 'partial'
                    reason = f'🟢 COMPRA / LONG (4H alcista)\n   15m: {consecutive} velas verdes'
                elif trend_1h == 'BULLISH':
                    should_alert = True
                    signal_type = 'LONG'
                    signal_strength = 'partial'
                    reason = f'🟢 COMPRA / LONG (1H alcista)\n   15m: {consecutive} velas verdes'
            
            # SHORT / VENTA: 3+ red candles + timeframes aligned
            elif candle_trend == 'BEARISH' and candle_confirmed:
                if trend_4h == 'BEARISH' and trend_1h == 'BEARISH':
                    should_alert = True
                    signal_type = 'SHORT'
                    signal_strength = 'confirmed'
                    reason = f'✅ VENTA / SHORT confirmado\n   4H: ▼ | 1H: ▼ | 15m: {consecutive} velas rojas'
                elif trend_4h == 'BEARISH':
                    should_alert = True
                    signal_type = 'SHORT'
                    signal_strength = 'partial'
                    reason = f'🔴 VENTA / SHORT (4H bajista)\n   15m: {consecutive} velas rojas'
                elif trend_1h == 'BEARISH':
                    should_alert = True
                    signal_type = 'SHORT'
                    signal_strength = 'partial'
                    reason = f'🔴 VENTA / SHORT (1H bajista)\n   15m: {consecutive} velas rojas'
            
            if not should_alert:
                return None
            
            # Check if we already sent this signal recently
            last_signal = self.last_signals.get(symbol_name)
            if last_signal:
                elapsed = (datetime.now() - last_signal['time']).total_seconds() / 3600
                if elapsed < 2 and last_signal['signal'] == signal_type:
                    return None
            
            # Calculate entry/exit levels
            if signal_type == 'LONG':
                entry = current_price
                sl = current_price * 0.95  # 5% stop loss
                tp = current_price * 1.10  # 10% take profit
            else:
                entry = current_price
                sl = current_price * 1.05  # 5% stop loss
                tp = current_price * 0.90  # 10% take profit
            
            
            # Get grouped votes
            grouped_votes = analyzer.get_grouped_tradingview_votes()
            
            return {
                'symbol': symbol,
                'symbol_name': symbol_name,
                'signal': signal_type,
                'signal_strength': signal_strength,
                'price': current_price,
                'entry': entry,
                'sl': sl,
                'tp': tp,
                'reason': reason,
                'long_votes': tv_votes['long_count'],
                'short_votes': tv_votes['short_count'],
                'crossover': crossover,
                'tv_votes': tv_votes,
                'grouped_votes': grouped_votes,  # NEW - Grouped indicators
                # Candle color data (NEW)
                'candle_15m': candle_15m,
                'candle_1h': candle_1h,
                'candle_4h': candle_4h,
                'trend_4h': trend_4h,
                'trend_1h': trend_1h,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.debug(f"Error analyzing {symbol}: {e}")
            return None
    
    async def scan_all_symbols(self) -> List[Dict]:
        """
        Scan ALL Binance futures symbols for signals
        
        Returns:
            List of symbols with trading signals
        """
        logger.info("Starting full market scan...")
        
        # Get all symbols
        all_symbols = self._load_all_futures_symbols()
        
        if not all_symbols:
            logger.warning("No symbols to scan")
            return []
        
        self.monitored_symbols = all_symbols
        
        # Analyze each symbol (with rate limiting)
        signals = []
        batch_size = 10
        
        for i in range(0, len(all_symbols), batch_size):
            batch = all_symbols[i:i+batch_size]
            tasks = [self.analyze_symbol(symbol) for symbol in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, dict) and result is not None:
                    signals.append(result)
            
            # Small delay to avoid rate limits
            await asyncio.sleep(0.5)
        
        # Sort by strength (crossovers first, then by vote count)
        signals.sort(key=lambda x: (
            x['signal_strength'] == 'crossover',  # Crossovers first
            max(x['long_votes'], x['short_votes'])  # Then by vote count
        ), reverse=True)
        
        logger.info(f"Scan complete: {len(signals)} signals found from {len(all_symbols)} symbols")
        
        return signals
    
    async def send_alert(self, result: Dict):
        """Send Telegram alert for a trading signal to ALL subscribers"""
        try:
            if not self.subscribers:
                logger.warning("No subscribers, skipping notification")
                return
            
            symbol_name = result['symbol_name']
            signal = result['signal']
            strength = result['signal_strength']
            
            # Format price
            def fmt_price(price):
                if price >= 1000:
                    return f"${price:,.2f}"
                elif price >= 1:
                    return f"${price:.4f}"
                else:
                    return f"${price:.8f}"
            
            # Build message with new format
            if strength == 'confirmed':
                header = f"✅ <b>CONFIRMADO - {symbol_name}</b>"
            else:
                header = f"📊 <b>SEÑAL - {symbol_name}</b>"
            
            msg = f"{header}\n\n"
            
            # Cripto copiable
            msg += f"Cripto: <code>{symbol_name}</code>\n\n"
            
            msg += f"💰 Precio: {fmt_price(result['price'])}\n\n"
            
            # ========== MULTI-TIMEFRAME ANALYSIS ==========
            msg += "━━━ Análisis Multi-Timeframe ━━━\n"
            
            # 4H
            trend_4h = result.get('trend_4h', 'NONE')
            candle_4h = result.get('candle_4h', {})
            if trend_4h == 'BULLISH':
                msg += f"📊 4H: ▲ ALCISTA\n"
            elif trend_4h == 'BEARISH':
                msg += f"📊 4H: ▼ BAJISTA\n"
            else:
                msg += f"📊 4H: ▬ LATERAL\n"
            if candle_4h.get('candle_colors'):
                msg += f"   Velas: {candle_4h['candle_colors']}\n"
            
            # 1H
            trend_1h = result.get('trend_1h', 'NONE')
            candle_1h = result.get('candle_1h', {})
            if trend_1h == 'BULLISH':
                msg += f"📊 1H: ▲ ALCISTA\n"
            elif trend_1h == 'BEARISH':
                msg += f"📊 1H: ▼ BAJISTA\n"
            else:
                msg += f"📊 1H: ▬ LATERAL\n"
            if candle_1h.get('candle_colors'):
                msg += f"   Velas: {candle_1h['candle_colors']}\n"
            
            # 15m (KEY)
            candle_15m = result.get('candle_15m', {})
            consecutive = max(candle_15m.get('consecutive_green', 0), candle_15m.get('consecutive_red', 0))
            if candle_15m.get('trend_change') == 'BULLISH':
                msg += f"📊 15m: ▲ {consecutive} velas VERDES\n"
            elif candle_15m.get('trend_change') == 'BEARISH':
                msg += f"📊 15m: ▼ {consecutive} velas ROJAS\n"
            else:
                msg += f"📊 15m: ▬ Sin tendencia\n"
            if candle_15m.get('candle_colors'):
                msg += f"   Velas: {candle_15m['candle_colors']}\n"
            
            if candle_15m.get('confirmed'):
                msg += "   ✅ <b>Confirmado (3+ velas)</b>\n"
            
            msg += "\n"
            
            # ========== INDICADORES (15M) - COMPLEMENTARIO ==========
            grouped_votes = result.get('grouped_votes', {})
            if grouped_votes:
                msg += "━━━ Indicadores (15m) ━━━\n\n"
                
                # OSCILLATORS
                osc = grouped_votes.get('oscillators', {})
                if osc:
                    osc_bar = "🟢" * osc.get('long_count', 0) + "🔴" * osc.get('short_count', 0)
                    msg += "📊 Osciladores\n"
                    msg += f"  Venta    Neutral   Compra\n"
                    msg += f"    {osc.get('short_count', 0)}         {osc.get('neutral_count', 0)}        {osc.get('long_count', 0)}\n"
                    msg += f"  \n"
                    msg += f"  {osc_bar} "
                    
                    osc_signal = osc.get('signal', 'NEUTRAL')
                    if osc_signal == 'STRONG_BUY':
                        msg += "Fuerte Compra\n\n"
                    elif osc_signal == 'BUY':
                        msg += "Compra\n\n"
                    elif osc_signal == 'STRONG_SELL':
                        msg += "Fuerte Venta\n\n"
                    elif osc_signal == 'SELL':
                        msg += "Venta\n\n"
                    else:
                        msg += "Neutral\n\n"
                
                # MOVING AVERAGES
                ma = grouped_votes.get('moving_averages', {})
                if ma:
                    ma_bar = "🟢" * ma.get('long_count', 0) + "🔴" * ma.get('short_count', 0)
                    msg += "📊 Medias Móviles\n"
                    msg += f"  Venta    Neutral   Compra\n"
                    msg += f"    {ma.get('short_count', 0)}         {ma.get('neutral_count', 0)}        {ma.get('long_count', 0)}\n"
                    msg += f"  \n"
                    msg += f"  {ma_bar} "
                    
                    ma_signal = ma.get('signal', 'NEUTRAL')
                    if ma_signal == 'STRONG_BUY':
                        msg += "Fuerte Compra\n\n"
                    elif ma_signal == 'BUY':
                        msg += "Compra\n\n"
                    elif ma_signal == 'STRONG_SELL':
                        msg += "Fuerte Venta\n\n"
                    elif ma_signal == 'SELL':
                        msg += "Venta\n\n"
                    else:
                        msg += "Neutral\n\n"
                
                # SUMMARY
                summary = grouped_votes.get('summary', {})
                summary_signal = summary.get('signal', 'NEUTRAL')
                if summary_signal == 'STRONG_BUY':
                    msg += "Resumen: 🟢 FUERTE COMPRA\n"
                elif summary_signal == 'BUY':
                    msg += "Resumen: 🟢 COMPRA\n"
                elif summary_signal == 'STRONG_SELL':
                    msg += "Resumen: 🔴 FUERTE VENTA\n"
                elif summary_signal == 'SELL':
                    msg += "Resumen: 🔴 VENTA\n"
                else:
                    msg += "Resumen: ⚪ NEUTRAL\n"
                
                if summary_signal in ['STRONG_BUY', 'STRONG_SELL']:
                    msg += "(Ambos grupos confirman)\n"
                
                msg += "\n"
            
            # ========== SIGNAL ==========
            msg += "━━━━━━━━━━━━━━━━━━━━\n"
            if signal == 'LONG':
                msg += f"┏━ <b>SEÑAL: COMPRA / LONG ▲</b>\n\n"
            else:
                msg += f"┏━ <b>SEÑAL: VENTA / SHORT ▼</b>\n\n"
            
            msg += f"{result['reason']}\n\n"
            
            # Levels - FORMATO COPIABLE (HTML)
            msg += f"━━━ COPIAR ━━━\n\n"
            msg += f"Moneda: <code>{symbol_name}</code>\n"
            msg += f"Take Profit: <code>{fmt_price(result['tp'])}</code>\n"
            msg += f"Stop Loss: <code>{fmt_price(result['sl'])}</code>\n\n"
            
            msg += f"⏰ {datetime.now(MEXICO_TZ).strftime('%H:%M:%S')}\n"
            msg += "┗━━━━━━━━━━━━━━━━━━━━"
            
            # Send to ALL subscribers
            for chat_id in self.subscribers:
                try:
                    await self.bot.send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode='HTML'
                    )
                except Exception as e:
                    logger.error(f"Error sending to {chat_id}: {e}")
            
            # Record signal
            self.last_signals[symbol_name] = {
                'signal': signal,
                'time': datetime.now()
            }
            
            logger.info(f"Alert sent to {len(self.subscribers)} users: {symbol_name} - {signal}")
            
        except Exception as e:
            logger.error(f"Error sending alert process: {e}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting MA7/MA25 auto-monitor loop...")
        
        while self.is_running:
            try:
                # Scan all symbols
                signals = await self.scan_all_symbols()
                
                # Send alerts for each signal (max 5 per scan to avoid spam)
                alerts_sent = 0
                for result in signals[:5]:
                    await self.send_alert(result)
                    alerts_sent += 1
                    await asyncio.sleep(1)  # 1 second between messages
                
                if alerts_sent > 0:
                    logger.info(f"Sent {alerts_sent} alerts")
                
                # Wait for next scan
                logger.info(f"Waiting {self.scan_interval} seconds for next scan...")
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start monitoring"""
        if self.is_running:
            logger.warning("Monitor already running")
            return
        
        self.is_running = True
        logger.info("MA7/MA25 Auto-Monitor started!")
        await self.monitor_loop()
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        logger.info("Monitor stopped")
    
    def get_status(self) -> Dict:
        """Get monitor status"""
        return {
            'is_running': self.is_running,
            'monitored_count': len(self.monitored_symbols),
            'monitored_symbols': [s.replace('/USDT:USDT', '') for s in self.monitored_symbols[:20]],
            'strategy': 'MA7/MA25 + TradingView 10 Indicators',
            'scan_interval': f'{self.scan_interval} seconds'
        }
    
    async def analyze_single(self, symbol_info: Dict) -> Optional[Dict]:
        """
        Analyze a single symbol - compatibility method
        Used by bot_telegram.py for manual analysis
        """
        symbol = symbol_info.get('symbol')
        if not symbol:
            return None
        return await self.analyze_symbol(symbol)
