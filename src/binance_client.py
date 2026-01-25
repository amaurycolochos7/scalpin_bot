"""
Binance Client Module
Handles all interactions with Binance Futures API using ccxt
"""
import ccxt
from typing import Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
from src.config import config


class BinanceClient:
    """Client for interacting with Binance Futures API"""
    
    def __init__(self):
        """Initialize Binance client with API credentials"""
        try:
            # Initialize exchange
            if config.EXCHANGE == 'binanceusdm':
                self.exchange = ccxt.binanceusdm({
                    'apiKey': config.BINANCE_API_KEY,
                    'secret': config.BINANCE_SECRET_KEY,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',
                    }
                })
            else:
                self.exchange = ccxt.binance({
                    'apiKey': config.BINANCE_API_KEY,
                    'secret': config.BINANCE_SECRET_KEY,
                    'enableRateLimit': True,
                })
            
            # Load markets (may fail in restricted regions, but that's OK for public data)
            try:
                self.exchange.load_markets()
            except Exception as e:
                print(f"⚠ Warning: Could not load private markets (region restricted): {str(e)[:100]}")
                print("OK - Conectado a Binance Futures (solo funciones publicas)")
            else:
                print(f"✅ Connected to {config.EXCHANGE.upper()}")
            
        except Exception as e:
            print(f"ERROR: Failed to connect to Binance: {str(e)}")
            print("OK - Continuando sin conexion completa...")
    
    def get_ohlcv(self, symbol: str, timeframe: str = None, limit: int = None) -> pd.DataFrame:
        """
        Get OHLCV (candlestick) data for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '15m', '1h', '4h')
            limit: Number of candles to fetch
            
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        try:
            timeframe = timeframe or config.DEFAULT_TIMEFRAME
            limit = limit or config.CANDLES_LIMIT
            
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to datetime but keep as column (not index)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            raise ValueError(f"Error fetching OHLCV for {symbol}: {str(e)}")
    
    def get_ticker(self, symbol: str) -> Dict:
        """
        Get current ticker information for a symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            
        Returns:
            Dictionary with ticker data including price, volume, change%
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'change_24h': ticker['percentage'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'volume_24h': ticker['quoteVolume'],
                'bid': ticker['bid'],
                'ask': ticker['ask'],
            }
        except Exception as e:
            raise ValueError(f"Error fetching ticker for {symbol}: {str(e)}")
    
    def get_multiple_tickers(self, symbols: List[str]) -> List[Dict]:
        """
        Get ticker information for multiple symbols
        
        Args:
            symbols: List of trading pairs
            
        Returns:
            List of ticker dictionaries
        """
        tickers = []
        for symbol in symbols:
            try:
                ticker = self.get_ticker(symbol)
                tickers.append(ticker)
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch {symbol}: {str(e)}")
                continue
        return tickers
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol exists in Binance Futures
        Accepts any format: LTC, LTCUSDT, ltcusdt, LTC/USDT, etc.
        
        Args:
            symbol: Trading pair to validate (any format)
            
        Returns:
            True if valid, False otherwise
        """
        try:
            normalized = self.normalize_symbol(symbol)
            return normalized is not None and normalized in self.exchange.markets
        except Exception as e:
            return False
    
    def normalize_symbol(self, symbol: str) -> str:
        """
        Normalize any user input to Binance Futures perpetual format
        Accepts: LTC, LTCUSDT, ltc, ltcusdt, LTC/USDT, etc.
        
        Args:
            symbol: Symbol in any format
            
        Returns:
            Normalized symbol for Binance Futures perpetuals (e.g., LTC/USDT:USDT)
            Returns None if symbol cannot be found
        """
        # Clean input
        symbol = symbol.strip().upper()
        
        # Remove common suffixes to get base symbol
        base = symbol
        for suffix in ['/USDT:USDT', ':USDT', '/USDT', 'USDT', '/USD', 'USD']:
            if base.endswith(suffix):
                base = base[:-len(suffix)]
                break
        
        # Also handle format with slash in middle
        if '/' in base:
            base = base.split('/')[0]
        
        # Now try to find this symbol in markets
        target = f"{base}/USDT:USDT"  # Perpetual format
        
        if target in self.exchange.markets:
            return target
        
        # If not found, search for similar symbols
        for market in self.exchange.markets.keys():
            if market.startswith(f"{base}/") and ':USDT' in market:
                return market
        
        # Not found
        return None
    
    def get_display_symbol(self, symbol: str) -> str:
        """
        Get clean symbol for display (e.g., LTC/USDT from LTC/USDT:USDT)
        """
        if symbol:
            return symbol.replace(':USDT', '').replace(':USD', '')
        return symbol
    
    def get_all_futures_symbols(self) -> list:
        """
        Get list of all available USDT perpetual futures symbols
        """
        symbols = []
        for symbol in self.exchange.markets.keys():
            if symbol.endswith(':USDT') and '/USDT' in symbol:
                symbols.append(symbol)
        return sorted(symbols)
    
    def get_top_by_volume(self, limit: int = 10) -> List[Dict]:
        """
        Get top cryptocurrencies by 24h volume from ALL available pairs
        """
        try:
            # Fetch all tickers
            all_tickers = self.exchange.fetch_tickers()
            
            # Filter and format
            valid_tickers = []
            for symbol, t in all_tickers.items():
                if '/USDT' in symbol and ':USDT' in symbol:
                    valid_tickers.append({
                        'symbol': symbol,
                        'price': t['last'],
                        'change_24h': t['percentage'],
                        'volume_24h': t['quoteVolume'] or 0
                    })
            
            # Sort by volume
            valid_tickers.sort(key=lambda x: x['volume_24h'], reverse=True)
            
            return valid_tickers[:limit]
        except Exception as e:
            print(f"Error getting top volume (fallback to config list): {e}")
            return self.get_multiple_tickers(config.TOP_SYMBOLS)[:limit]
    
    def get_top_by_change(self, limit: int = 10) -> List[Dict]:
        """
        Get top cryptocurrencies by 24h price change % from ALL available pairs
        """
        try:
            # Fetch all tickers
            all_tickers = self.exchange.fetch_tickers()
            
            # Filter and format
            valid_tickers = []
            for symbol, t in all_tickers.items():
                if '/USDT' in symbol and ':USDT' in symbol:
                    valid_tickers.append({
                        'symbol': symbol,
                        'price': t['last'],
                        'change_24h': t['percentage'],
                        'volume_24h': t['quoteVolume'] or 0
                    })
            
            # Sort by percentage change (absolute value for volatility)
            valid_tickers.sort(key=lambda x: abs(x['change_24h']), reverse=True)
            
            return valid_tickers[:limit]
        except Exception as e:
            print(f"Error getting top change (fallback to config list): {e}")
            return self.get_multiple_tickers(config.TOP_SYMBOLS)[:limit]


# Singleton instance
_client_instance = None

def get_client() -> BinanceClient:
    """Get or create singleton Binance client instance"""
    global _client_instance
    if _client_instance is None:
        _client_instance = BinanceClient()
    return _client_instance
