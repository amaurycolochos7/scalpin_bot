"""
Configuration module for the Trading Bot
Loads settings from environment variables
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Bot configuration settings"""
    
    # Binance API
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
    
    # Exchange Settings
    EXCHANGE = os.getenv('EXCHANGE', 'binanceusdm')  # binanceusdm for futures
    DEFAULT_TIMEFRAME = os.getenv('DEFAULT_TIMEFRAME', '5m')  # 5m for scalping
    CANDLES_LIMIT = int(os.getenv('CANDLES_LIMIT', '200'))
    
    # Signal Settings
    MIN_SIGNAL_SCORE = int(os.getenv('MIN_SIGNAL_SCORE', '55'))  # Lower for more scalping opportunities
    
    # Top coins to monitor (Binance Futures USDT Perpetual pairs)
    TOP_SYMBOLS = [
        'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 'XRP/USDT:USDT', 'ADA/USDT:USDT',
        'SOL/USDT:USDT', 'DOGE/USDT:USDT', 'DOT/USDT:USDT', 'MATIC/USDT:USDT', 'AVAX/USDT:USDT',
        'LINK/USDT:USDT', 'UNI/USDT:USDT', 'ATOM/USDT:USDT', 'XLM/USDT:USDT', 'LTC/USDT:USDT',
        'NEAR/USDT:USDT', 'ALGO/USDT:USDT', 'BCH/USDT:USDT', 'ICP/USDT:USDT', 'FIL/USDT:USDT',
        'APT/USDT:USDT', 'ARB/USDT:USDT', 'OP/USDT:USDT', 'SUI/USDT:USDT', 'PEPE/USDT:USDT'
    ]
    
    @classmethod
    def validate(cls):
        """Validate that required configuration is set"""
        if not cls.BINANCE_API_KEY or not cls.BINANCE_SECRET_KEY:
            raise ValueError(
                "Binance API credentials not found. "
                "Please create a .env file with BINANCE_API_KEY and BINANCE_SECRET_KEY"
            )
        return True

# Export config instance
config = Config()
