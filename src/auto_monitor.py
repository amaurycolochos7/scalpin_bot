"""
Auto-Monitor System
Continuously monitors Top 20 cryptos and sends Telegram notifications
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List
from telegram import Bot
from src.binance_client import get_client
from src.confluence_scorer import ConfluenceScorer
from src.ml_config import MLConfig
from src.ml_engine import MLEngine
import os
import json

logger = logging.getLogger(__name__)


class AutoMonitor:
    """
    Automatic monitoring system for Top 20 cryptocurrencies
    Runs every 5 minutes and sends notifications when ML > 95%
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
        self.last_signals = {}  # To avoid spam
        
        # Load monitored symbols
        self._load_monitored_symbols()
    
    def _load_monitored_symbols(self):
        """Load Top 20 symbols that have trained models"""
        try:
            # Get top 20 by volume
            top_cryptos = self.client.get_top_by_volume(limit=20)
            
            # Filter only those with trained models
            models_dir = MLConfig.MODEL_DIR
            
            for crypto in top_cryptos:
                symbol = crypto['symbol']
                symbol_name = symbol.split('/')[0]
                model_path = os.path.join(models_dir, symbol_name, 'model.txt')
                
                if os.path.exists(model_path):
                    self.monitored_symbols.append({
                        'symbol': symbol,
                        'name': symbol_name,
                        'model_path': os.path.join(models_dir, symbol_name)
                    })
            
            logger.info(f"Loaded {len(self.monitored_symbols)} symbols with trained models")
            
        except Exception as e:
            logger.error(f"Error loading monitored symbols: {e}")
    
    async def analyze_single(self, symbol_info: Dict) -> Dict:
        """
        Analyze a single cryptocurrency
        
        Args:
            symbol_info: Dictionary with symbol, name, model_path
            
        Returns:
            Analysis result or None
        """
        try:
            symbol = symbol_info['symbol']
            symbol_name = symbol_info['name']
            
            # Create custom ML engine for this symbol
            ml_engine = MLEngine(load_latest=False)
            
            # Load symbol-specific model
            model_path = os.path.join(symbol_info['model_path'], 'model.txt')
            scaler_path = os.path.join(symbol_info['model_path'], 'scaler.pkl')
            features_path = os.path.join(symbol_info['model_path'], 'feature_names.json')
            metadata_path = os.path.join(symbol_info['model_path'], 'metadata.json')
            
            if not all(os.path.exists(p) for p in [model_path, scaler_path, features_path]):
                logger.warning(f"Model files missing for {symbol_name}")
                return None
            
            import lightgbm as lgb
            import joblib
            
            ml_engine.model = lgb.Booster(model_file=model_path)
            ml_engine.scaler = joblib.load(scaler_path)
            
            with open(features_path, 'r') as f:
                ml_engine.feature_names = json.load(f)
            
            with open(metadata_path, 'r') as f:
                ml_engine.metadata = json.load(f)
            
            # Get OHLCV data
            df = self.client.get_ohlcv(symbol, MLConfig.TIMEFRAME_PRIMARY, limit=200)
            
            if df is None or len(df) < 50:
                return None
            
            # Calculate features
            from src.feature_engineering import FeatureEngineer
            fe = FeatureEngineer(df)
            df_features = fe.calculate_all_features()
            
            # Get latest features
            latest_features = fe.get_latest_features()
            
            # Predict
            ml_probability, ml_prediction = ml_engine.predict(latest_features)
            
            # Calculate technical analysis
            from src.technical_analysis import TechnicalAnalyzer
            tech_analyzer = TechnicalAnalyzer(df)
            tech_analysis = tech_analyzer.generate_analysis()
            
            tech_score = tech_analysis.get('total_score', 0)
            tech_signal = tech_analysis.get('signal', 'NEUTRAL')
            
            # Determine signal
            entry_allowed = (
                ml_probability >= MLConfig.PROBABILITY_THRESHOLD and
                tech_score >= MLConfig.TECHNICAL_SCORE_MIN
            )
            
            signal_type = None
            if entry_allowed:
                if tech_signal in ['COMPRA FUERTE', 'COMPRA']:
                    signal_type = 'LONG'
                elif tech_signal in ['VENTA FUERTE', 'VENTA']:
                    signal_type = 'SHORT'
            
            # Get current price and calculate TP/SL
            current_price = df['close'].iloc[-1]
            atr_percent = df_features['atr_percent'].iloc[-1]
            
            tp_percent, sl_percent = MLConfig.get_tp_sl_by_atr(atr_percent)
            
            if signal_type == 'LONG':
                entry_price = current_price
                tp_price = entry_price * (1 + tp_percent / 100)
                sl_price = entry_price * (1 - sl_percent / 100)
            elif signal_type == 'SHORT':
                entry_price = current_price
                tp_price = entry_price * (1 - tp_percent / 100)
                sl_price = entry_price * (1 + sl_percent / 100)
            else:
                entry_price = current_price
                tp_price = None
                sl_price = None
            
            result = {
                'symbol': symbol,
                'symbol_name': symbol_name,
                'signal': signal_type,
                'ml_probability': ml_probability * 100,
                'technical_score': tech_score,
                'entry_allowed': entry_allowed,
                'entry_price': entry_price,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'tp_percent': tp_percent if signal_type else None,
                'sl_percent': sl_percent if signal_type else None,
                'timestamp': datetime.now().isoformat()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol_info['name']}: {e}")
            return None
    
    async def scan_all(self) -> List[Dict]:
        """
        Scan all monitored cryptocurrencies
        
        Returns:
            List of analysis results
        """
        logger.info(f"Starting scan of {len(self.monitored_symbols)} symbols...")
        
        tasks = []
        for symbol_info in self.monitored_symbols:
            task = self.analyze_single(symbol_info)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid results
        valid_results = []
        for r in results:
            if isinstance(r, dict) and r is not None:
                valid_results.append(r)
        
        logger.info(f"Scan complete: {len(valid_results)} valid results")
        
        return valid_results
    
    async def send_notification(self, result: Dict):
        """Send Telegram notification for a signal"""
        try:
            symbol_name = result['symbol_name']
            prob = result['ml_probability']
            signal = result['signal']
            
            # Format price
            def fmt_price(price):
                if price >= 1000:
                    return f"${price:,.2f}"
                elif price >= 1:
                    return f"${price:.4f}"
                else:
                    return f"${price:.8f}"
            
            msg = f"🔔 *SEÑAL DETECTADA - {symbol_name}*\n\n"
            msg += f"📈 Probabilidad ML: *{prob:.1f}%* {'✅✅' if prob >= 97 else '✅'}\n\n"
            
            if signal == 'LONG':
                msg += f"💰 *COMPRAR* ▲\n"
            else:
                msg += f"💰 *VENDER* ▼\n"
            
            msg += f"  Entry: {fmt_price(result['entry_price'])}\n"
            msg += f"  TP: {fmt_price(result['tp_price'])} (+{result['tp_percent']:.1f}%)\n"
            msg += f"  SL: {fmt_price(result['sl_price'])} (-{result['sl_percent']:.1f}%)\n\n"
            
            msg += f"⏰ {datetime.now().strftime('%H:%M:%S')}\n"
            
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=msg,
                parse_mode='Markdown'
            )
            
            logger.info(f"Notification sent for {symbol_name}")
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Starting auto-monitor loop...")
        
        while self.is_running:
            try:
                # Scan all symbols
                results = await self.scan_all()
                
                # Send notifications for signals > 95%
                for result in results:
                    if result['entry_allowed'] and result['signal']:
                        symbol_name = result['symbol_name']
                        
                        # Check if we already sent this signal recently (avoid spam)
                        last_signal_time = self.last_signals.get(symbol_name)
                        now = datetime.now()
                        
                        if last_signal_time:
                            elapsed = (now - last_signal_time).total_seconds() / 60
                            if elapsed < 60:  # Don't send same symbol within 1 hour
                                logger.info(f"Skipping {symbol_name} (sent {elapsed:.0f}min ago)")
                                continue
                        
                        await self.send_notification(result)
                        self.last_signals[symbol_name] = now
                
                # Wait 60 seconds (1 minute for scalping)
                logger.info("Waiting 60 seconds for next scan...")
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(60)
    
    async def start(self):
        """Start monitoring"""
        if self.is_running:
            logger.warning("Monitor already running")
            return
        
        self.is_running = True
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
            'monitored_symbols': [s['name'] for s in self.monitored_symbols]
        }
