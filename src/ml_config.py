"""
ML Configuration Module
Centralized configuration for Machine Learning components
"""
import os
from typing import Dict, Any


class MLConfig:
    """Configuration for ML-based trading system"""
    
    # Signal Filtering
    PROBABILITY_THRESHOLD = float(os.getenv('ML_PROBABILITY_THRESHOLD', '0.90'))  # Lowered to 90% for more signals
    TECHNICAL_SCORE_MIN = int(os.getenv('ML_TECHNICAL_SCORE_MIN', '65'))  # Lowered for scalping
    
    # Timeframes (SCALPING)
    TIMEFRAME_PRIMARY = os.getenv('ML_TIMEFRAME_PRIMARY', '1m')  # Changed from 5m to 1m
    TIMEFRAME_SECONDARY = os.getenv('ML_TIMEFRAME_SECONDARY', '5m')  # Changed from 15m to 5m
    
    # TP/SL Configuration (SCALPING - Tighter targets)
    TP_LOW_VOL = float(os.getenv('ML_TP_LOW_VOL', '0.25'))      # 0.25% for scalping
    SL_LOW_VOL = float(os.getenv('ML_SL_LOW_VOL', '0.15'))      # 0.15% stop
    
    TP_MED_VOL = float(os.getenv('ML_TP_MED_VOL', '0.35'))      # 0.35% for scalping
    SL_MED_VOL = float(os.getenv('ML_SL_MED_VOL', '0.20'))      # 0.20% stop
    
    TP_HIGH_VOL = float(os.getenv('ML_TP_HIGH_VOL', '0.50'))    # 0.50% for scalping
    SL_HIGH_VOL = float(os.getenv('ML_SL_HIGH_VOL', '0.25'))    # 0.25% stop
    
    # Volatility thresholds (ATR percentages)
    ATR_LOW_THRESHOLD = 0.5
    ATR_HIGH_THRESHOLD = 1.5
    
    # Training Configuration
    TRAINING_DAYS = int(os.getenv('ML_TRAINING_DAYS', '90'))
    LOOKBACK_CANDLES = int(os.getenv('ML_LOOKBACK_CANDLES', '200'))
    LOOKAHEAD_CANDLES = int(os.getenv('ML_LOOKAHEAD_CANDLES', '50'))  # Increased from 20
    MIN_SAMPLES = int(os.getenv('ML_MIN_SAMPLES', '5000'))  # Reduced from 100000
    
    # Retraining
    RETRAIN_INTERVAL_DAYS = int(os.getenv('ML_RETRAIN_DAYS', '7'))
    ACCURACY_THRESHOLD = float(os.getenv('ML_ACCURACY_THRESHOLD', '0.65'))
    
    # Market Data
    ORDER_BOOK_DEPTH = int(os.getenv('ORDER_BOOK_DEPTH', '20'))
    CVD_TRADES_LOOKBACK = int(os.getenv('CVD_TRADES_LOOKBACK', '500'))
    
    # Model Hyperparameters
    LGBM_PARAMS: Dict[str, Any] = {
        'objective': 'binary',
        'metric': 'auc',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'force_col_wise': True,
        'n_jobs': -1
    }
    
    # Model Storage
    MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
    LATEST_MODEL_DIR = os.path.join(MODEL_DIR, 'latest')
    ARCHIVE_MODEL_DIR = os.path.join(MODEL_DIR, 'archive')
    
    @classmethod
    def get_tp_sl_by_atr(cls, atr_percent: float) -> tuple:
        """
        Get TP/SL percentages based on ATR volatility
        
        Args:
            atr_percent: ATR as percentage
            
        Returns:
            Tuple of (tp_percent, sl_percent)
        """
        if atr_percent < cls.ATR_LOW_THRESHOLD:
            return cls.TP_LOW_VOL, cls.SL_LOW_VOL
        elif atr_percent < cls.ATR_HIGH_THRESHOLD:
            return cls.TP_MED_VOL, cls.SL_MED_VOL
        else:
            return cls.TP_HIGH_VOL, cls.SL_HIGH_VOL
    
    @classmethod
    def ensure_model_dirs(cls):
        """Create model directories if they don't exist"""
        os.makedirs(cls.LATEST_MODEL_DIR, exist_ok=True)
        os.makedirs(cls.ARCHIVE_MODEL_DIR, exist_ok=True)
