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
        self.chat_id = chat_id
        self.client = get_client()
        self.is_running = False
        self.monitored_symbols = []
        
        # Track signals to avoid spam
        self.last_signals = {}  # {symbol: {'signal': 'LONG/SHORT', 'time': datetime}}
        
        # Scan interval (5 minutes since we use 15m candles)
        self.scan_interval = 300  # 5 minutes
        
        # Minimum votes required (7/10 rule)
        self.min_votes = 6  # At least 6/10 for alert (7 for strong)
        
        logger.info("AutoMonitor initialized with MA7/MA25 strategy")
    
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
        Analyze a single symbol using MA7/MA25 strategy
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            
        Returns:
            Analysis result dict or None if no signal
        """
        try:
            # Get 15m OHLCV data
            df = self.client.get_ohlcv(symbol, '15m', limit=100)
            
            if df is None or len(df) < 30:
                return None
            
            # Create analyzer and calculate indicators
            analyzer = TechnicalAnalyzer(df)
            analyzer.calculate_all_indicators()
            
            # Get MA7/MA25 crossover
            crossover = analyzer.detect_ma_crossover()
            
            # Get TradingView 10-indicator votes
            tv_votes = analyzer.get_tradingview_votes()
            
            # Current price
            current_price = df['close'].iloc[-1]
            
            # Get symbol name for display (add USDT for futures)
            symbol_name = symbol.replace('/USDT:USDT', 'USDT').replace('/USDT', 'USDT')
            
            # Check for trading signal
            ma_signal = crossover['signal']
            long_votes = tv_votes['long_count']
            short_votes = tv_votes['short_count']
            
            # Determine if we should alert
            should_alert = False
            signal_type = None
            signal_strength = 'normal'
            reason = ''
            
            # FRESH CROSSOVER - Highest priority
            if ma_signal == 'LONG':
                should_alert = True
                signal_type = 'LONG'
                signal_strength = 'crossover'
                reason = f"🟢 CRUCE ALCISTA + {long_votes}/10 indicadores"
            
            elif ma_signal == 'SHORT':
                should_alert = True
                signal_type = 'SHORT'
                signal_strength = 'crossover'
                reason = f"🔴 CRUCE BAJISTA + {short_votes}/10 indicadores"
            
            # IN TREND + Strong confirmation (7/10)
            elif ma_signal == 'LONG_TREND' and long_votes >= 7:
                should_alert = True
                signal_type = 'LONG'
                signal_strength = 'trend'
                reason = f"📈 Tendencia ALCISTA + {long_votes}/10 indicadores"
            
            elif ma_signal == 'SHORT_TREND' and short_votes >= 7:
                should_alert = True
                signal_type = 'SHORT'
                signal_strength = 'trend'
                reason = f"📉 Tendencia BAJISTA + {short_votes}/10 indicadores"
            
            if not should_alert:
                return None
            
            # Check if we already sent this signal recently
            last_signal = self.last_signals.get(symbol_name)
            if last_signal:
                # Same signal within 2 hours? Skip
                elapsed = (datetime.now() - last_signal['time']).total_seconds() / 3600
                if elapsed < 2 and last_signal['signal'] == signal_type:
                    return None
                # Opposite signal? Always alert (reversal)
            
            # Calculate entry/exit levels
            if signal_type == 'LONG':
                entry = current_price
                sl = current_price * 0.98  # 2% stop loss
                tp = current_price * 1.04  # 4% take profit
            else:
                entry = current_price
                sl = current_price * 1.02  # 2% stop loss
                tp = current_price * 0.96  # 4% take profit
            
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
                'long_votes': long_votes,
                'short_votes': short_votes,
                'crossover': crossover,
                'tv_votes': tv_votes,
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
        """Send Telegram alert for a trading signal"""
        try:
            if not self.chat_id or self.chat_id == 0:
                logger.warning("No chat_id set, skipping notification")
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
            
            # Build message
            if strength == 'crossover':
                header = f"🔔 *CRUCE DETECTADO - {symbol_name}*"
            else:
                header = f"📊 *SEÑAL - {symbol_name}*"
            
            msg = f"{header}\n\n"
            msg += f"💰 Precio: {fmt_price(result['price'])}\n\n"
            
            # Crossover info
            msg += f"━━━ MA7/MA25 (15m) ━━━\n"
            msg += f"{result['crossover']['description']}\n\n"
            
            # Votes
            long_v = result['long_votes']
            short_v = result['short_votes']
            msg += f"━━━ Indicadores ━━━\n"
            msg += f"LONG: {long_v}  {'🟢' * long_v}\n"
            msg += f"SHORT: {short_v}  {'🔴' * short_v}\n\n"
            
            # Signal
            if signal == 'LONG':
                msg += f"┏━ *COMPRA ▲*\n\n"
            else:
                msg += f"┏━ *VENTA ▼*\n\n"
            
            msg += f"{result['reason']}\n\n"
            
            # Levels
            msg += f"📊 Niveles:\n"
            msg += f"  Entrada → {fmt_price(result['entry'])}\n"
            msg += f"  Stop    → {fmt_price(result['sl'])}\n"
            msg += f"  Target  → {fmt_price(result['tp'])}\n\n"
            
            msg += f"⏰ {datetime.now(MEXICO_TZ).strftime('%H:%M:%S')}"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode='Markdown'
            )
            
            # Record signal
            self.last_signals[symbol_name] = {
                'signal': signal,
                'time': datetime.now()
            }
            
            logger.info(f"Alert sent: {symbol_name} - {signal}")
            
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
    
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
