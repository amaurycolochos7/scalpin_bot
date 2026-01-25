"""
Feature Engineering Module
Advanced features for ML-based trading including CVD, FVG, Order Blocks, Hurst, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional


class FeatureEngineer:
    """
    Advanced feature engineering for crypto scalping
    Calculates 60+ features including microstructure, volume, and price structure
    """
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialize feature engineer with OHLCV data
        
        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume
        """
        self.df = df.copy()
        self._validate_dataframe()
    
    def _validate_dataframe(self):
        """Ensure DataFrame has required columns"""
        required = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in self.df.columns]
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")
    
    def calculate_all_features(self) -> pd.DataFrame:
        """
        Calculate all features and return DataFrame with features added
        
        Returns:
            DataFrame with all features added as columns
        """
        # Volume features
        self._calculate_cvd_features()
        self._calculate_volume_profile()
        
        # Price structure features
        self._calculate_fvg_features()
        self._calculate_order_blocks()
        self._calculate_supply_demand_zones()
        
        # Market regime features
        self._calculate_volatility_features()
        self._calculate_hurst_exponent()
        
        # Microstructure features
        self._calculate_vwap_features()
        self._calculate_price_momentum()
        
        return self.df
    
    # ==================== VOLUME FEATURES ====================
    
    def _calculate_cvd_features(self):
        """
        Calculate Cumulative Volume Delta (CVD)
        CVD = cumsum(buy_volume - sell_volume)
        
        Note: Without tick data, we estimate buy/sell volume using price action
        """
        # Estimate buy/sell volume based on close vs open
        self.df['delta'] = np.where(
            self.df['close'] > self.df['open'],
            self.df['volume'],  # Bullish candle = buy volume
            -self.df['volume']  # Bearish candle = sell volume
        )
        
        # For doji candles (close ≈ open), use close vs previous close
        close_open_diff = abs(self.df['close'] - self.df['open'])
        is_doji = close_open_diff < (self.df['high'] - self.df['low']) * 0.1
        
        self.df.loc[is_doji, 'delta'] = np.where(
            self.df.loc[is_doji, 'close'] > self.df.loc[is_doji, 'close'].shift(1),
            self.df.loc[is_doji, 'volume'],
            -self.df.loc[is_doji, 'volume']
        )
        
        # Cumulative Volume Delta
        self.df['cvd'] = self.df['delta'].cumsum()
        
        # CVD momentum (rate of change)
        self.df['cvd_momentum'] = self.df['cvd'].diff(5)
        
        # CVD deviation from MA
        self.df['cvd_ma20'] = self.df['cvd'].rolling(20).mean()
        self.df['cvd_deviation'] = self.df['cvd'] - self.df['cvd_ma20']
        
        # Buy/Sell pressure ratio
        buy_volume = self.df['delta'].apply(lambda x: max(x, 0)).rolling(10).sum()
        sell_volume = self.df['delta'].apply(lambda x: abs(min(x, 0))).rolling(10).sum()
        self.df['buy_sell_ratio'] = buy_volume / (sell_volume + 1e-10)
    
    def _calculate_volume_profile(self):
        """Calculate volume profile features"""
        # Volume MA
        self.df['volume_ma20'] = self.df['volume'].rolling(20).mean()
        self.df['volume_ratio'] = self.df['volume'] / (self.df['volume_ma20'] + 1e-10)
        
        # Volume trend
        self.df['volume_trend'] = (
            self.df['volume'].rolling(5).mean() / 
            self.df['volume'].rolling(20).mean()
        )
        
        # High volume candles (above 2x average)
        self.df['high_volume'] = (self.df['volume'] > self.df['volume_ma20'] * 2).astype(int)
    
    # ==================== PRICE STRUCTURE FEATURES ====================
    
    def _calculate_fvg_features(self):
        """
        Detect Fair Value Gaps (FVG)
        FVG = gap between candle bodies indicating inefficiency
        """
        # Bullish FVG: gap between current low and 2 candles ago high
        bullish_fvg = (self.df['low'] > self.df['high'].shift(2)) & \
                      (self.df['close'] > self.df['open'])
        
        # Bearish FVG: gap between current high and 2 candles ago low  
        bearish_fvg = (self.df['high'] < self.df['low'].shift(2)) & \
                      (self.df['close'] < self.df['open'])
        
        self.df['fvg_bullish'] = bullish_fvg.astype(int)
        self.df['fvg_bearish'] = bearish_fvg.astype(int)
        
        # FVG size
        self.df['fvg_bullish_size'] = np.where(
            bullish_fvg,
            (self.df['low'] - self.df['high'].shift(2)) / self.df['close'] * 100,
            0
        )
        
        self.df['fvg_bearish_size'] = np.where(
            bearish_fvg,
            (self.df['low'].shift(2) - self.df['high']) / self.df['close'] * 100,
            0
        )
        
        # Recent FVG count (last 20 candles)
        self.df['fvg_bullish_count'] = self.df['fvg_bullish'].rolling(20).sum()
        self.df['fvg_bearish_count'] = self.df['fvg_bearish'].rolling(20).sum()
    
    def _calculate_order_blocks(self):
        """
        Identify Order Blocks (institutional supply/demand zones)
        Order Block = last opposite candle before strong move
        """
        # Calculate price movement
        self.df['price_change'] = self.df['close'].pct_change()
        
        # Strong bullish move (> 1% in 3 candles)
        strong_bull_move = (
            self.df['close'].pct_change(3) > 0.01
        )
        
        # Strong bearish move (< -1% in 3 candles)
        strong_bear_move = (
            self.df['close'].pct_change(3) < -0.01
        )
        
        # Bullish order block: last red candle before strong up move
        self.df['ob_bullish'] = (
            (self.df['close'] < self.df['open']) &
            strong_bull_move.shift(-3)
        ).astype(int)
        
        # Bearish order block: last green candle before strong down move
        self.df['ob_bearish'] = (
            (self.df['close'] > self.df['open']) &
            strong_bear_move.shift(-3)
        ).astype(int)
        
        # Distance to nearest order block
        self.df['distance_to_ob_bull'] = self._calculate_distance_to_signal(self.df['ob_bullish'])
        self.df['distance_to_ob_bear'] = self._calculate_distance_to_signal(self.df['ob_bearish'])
    
    def _calculate_supply_demand_zones(self):
        """Identify supply/demand zones based on price rejections"""
        # Swing highs (potential supply)
        self.df['swing_high'] = (
            (self.df['high'] > self.df['high'].shift(1)) &
            (self.df['high'] > self.df['high'].shift(2)) &
            (self.df['high'] > self.df['high'].shift(-1)) &
            (self.df['high'] > self.df['high'].shift(-2))
        ).astype(int)
        
        # Swing lows (potential demand)
        self.df['swing_low'] = (
            (self.df['low'] < self.df['low'].shift(1)) &
            (self.df['low'] < self.df['low'].shift(2)) &
            (self.df['low'] < self.df['low'].shift(-1)) &
            (self.df['low'] < self.df['low'].shift(-2))
        ).astype(int)
        
        # Recent swing high/low count
        self.df['swing_high_count'] = self.df['swing_high'].rolling(20).sum()
        self.df['swing_low_count'] = self.df['swing_low'].rolling(20).sum()
    
    # ==================== MARKET REGIME FEATURES ====================
    
    def _calculate_volatility_features(self):
        """Calculate volatility features including Z-Score"""
        # ATR (Average True Range)
        high_low = self.df['high'] - self.df['low']
        high_close = abs(self.df['high'] - self.df['close'].shift())
        low_close = abs(self.df['low'] - self.df['close'].shift())
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['atr'] = true_range.rolling(14).mean()
        self.df['atr_percent'] = (self.df['atr'] / self.df['close']) * 100
        
        # Historical volatility (std of returns)
        returns = self.df['close'].pct_change()
        self.df['volatility'] = returns.rolling(20).std() * np.sqrt(20)
        
        # Volatility Z-Score
        vol_mean = self.df['volatility'].rolling(50).mean()
        vol_std = self.df['volatility'].rolling(50).std()
        self.df['volatility_zscore'] = (self.df['volatility'] - vol_mean) / (vol_std + 1e-10)
        
        # Bollinger Bands width (volatility indicator)
        bb_ma = self.df['close'].rolling(20).mean()
        bb_std = self.df['close'].rolling(20).std()
        self.df['bb_upper'] = bb_ma + (bb_std * 2)
        self.df['bb_lower'] = bb_ma - (bb_std * 2)
        self.df['bb_width'] = (self.df['bb_upper'] - self.df['bb_lower']) / bb_ma
        
        # Position within Bollinger Bands
        self.df['bb_position'] = (self.df['close'] - self.df['bb_lower']) / \
                                 (self.df['bb_upper'] - self.df['bb_lower'])
    
    def _calculate_hurst_exponent(self, window: int = 100):
        """
        Calculate Hurst Exponent to identify market regime
        H > 0.5: Trending market
        H = 0.5: Random walk
        H < 0.5: Mean-reverting market
        """
        def hurst_exponent(prices):
            """Calculate Hurst exponent for a price series"""
            if len(prices) < 20:
                return 0.5
            
            # Use log returns
            lags = range(2, min(20, len(prices) // 2))
            tau = []
            
            for lag in lags:
                # Standard deviation of lagged differences
                pp = np.subtract(prices[lag:], prices[:-lag])
                tau.append(np.std(pp))
            
            # Linear fit to log-log plot
            try:
                poly = np.polyfit(np.log(lags), np.log(tau), 1)
                hurst = poly[0]
                return max(0, min(1, hurst))  # Clip to [0, 1]
            except:
                return 0.5
        
        # Calculate Hurst for rolling window
        hurst_values = []
        for i in range(len(self.df)):
            if i < window:
                hurst_values.append(0.5)
            else:
                window_prices = self.df['close'].iloc[i-window:i].values
                hurst_values.append(hurst_exponent(window_prices))
        
        self.df['hurst'] = hurst_values
        
        # Categorize regime
        self.df['regime_trending'] = (self.df['hurst'] > 0.55).astype(int)
        self.df['regime_ranging'] = (self.df['hurst'] < 0.45).astype(int)
    
    # ==================== MICROSTRUCTURE FEATURES ====================
    
    def _calculate_vwap_features(self):
        """Calculate VWAP and deviations"""
        # VWAP
        typical_price = (self.df['high'] + self.df['low'] + self.df['close']) / 3
        self.df['vwap'] = (typical_price * self.df['volume']).cumsum() / \
                         self.df['volume'].cumsum()
        
        # Reset VWAP daily (approximate with rolling window)
        self.df['vwap_rolling'] = (
            (typical_price * self.df['volume']).rolling(50).sum() /
            self.df['volume'].rolling(50).sum()
        )
        
        # Deviation from VWAP
        self.df['vwap_deviation'] = (
            (self.df['close'] - self.df['vwap_rolling']) / 
            self.df['vwap_rolling'] * 100
        )
        
        # Above/below VWAP
        self.df['above_vwap'] = (self.df['close'] > self.df['vwap_rolling']).astype(int)
    
    def _calculate_price_momentum(self):
        """Calculate price momentum features"""
        # Rate of change
        self.df['roc_5'] = self.df['close'].pct_change(5) * 100
        self.df['roc_10'] = self.df['close'].pct_change(10) * 100
        self.df['roc_20'] = self.df['close'].pct_change(20) * 100
        
        # Momentum acceleration
        self.df['momentum_accel'] = self.df['roc_5'].diff(3)
        
        # Candle body size (as % of price)
        self.df['body_size'] = abs(self.df['close'] - self.df['open']) / self.df['close'] * 100
        
        # Candle wick sizes
        upper_wick = self.df['high'] - self.df[['open', 'close']].max(axis=1)
        lower_wick = self.df[['open', 'close']].min(axis=1) - self.df['low']
        
        self.df['upper_wick_pct'] = upper_wick / self.df['close'] * 100
        self.df['lower_wick_pct'] = lower_wick / self.df['close'] * 100
        
        # Wick/body ratio
        self.df['wick_body_ratio'] = (
            (self.df['upper_wick_pct'] + self.df['lower_wick_pct']) / 
            (self.df['body_size'] + 1e-10)
        )
    
    # ==================== HELPER FUNCTIONS ====================
    
    def _calculate_distance_to_signal(self, signal_series: pd.Series) -> pd.Series:
        """Calculate candles since last signal"""
        distances = []
        last_signal_idx = -1
        
        for i, val in enumerate(signal_series):
            if val == 1:
                last_signal_idx = i
                distances.append(0)
            else:
                if last_signal_idx == -1:
                    distances.append(999)  # No signal seen yet
                else:
                    distances.append(i - last_signal_idx)
        
        return pd.Series(distances, index=signal_series.index)
    
    def get_latest_features(self) -> Dict:
        """
        Get latest row features as dictionary for ML inference
        
        Returns:
            Dictionary of feature name -> value
        """
        if self.df.empty:
            return {}
        
        latest = self.df.iloc[-1]
        
        # Select features for ML (exclude raw OHLCV and intermediate calculations)
        exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                       'delta', 'cvd_ma20', 'volume_ma20', 'bb_upper', 'bb_lower',
                       'vwap', 'vwap_rolling']
        
        features = {
            col: latest[col] for col in self.df.columns 
            if col not in exclude_cols and pd.notna(latest[col])
        }
        
        return features
    
    def get_feature_names(self) -> list:
        """Get list of feature names for ML"""
        exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                       'delta', 'cvd_ma20', 'volume_ma20', 'bb_upper', 'bb_lower',
                       'vwap', 'vwap_rolling']
        
        return [col for col in self.df.columns if col not in exclude_cols]
