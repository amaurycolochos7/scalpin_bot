"""
ML Engine Module
LightGBM-based classification model for high-probability trade prediction
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, classification_report
import joblib
import json
import os
from datetime import datetime
from typing import Dict, Tuple, Optional, List
from src.ml_config import MLConfig
from src.feature_engineering import FeatureEngineer


class MLEngine:
    """
    Machine Learning engine for trade signal prediction
    Uses LightGBM for binary classification
    """
    
    def __init__(self, load_latest: bool = True):
        """
        Initialize ML Engine
        
        Args:
            load_latest: If True, load latest trained model
        """
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.metadata = {}
        
        MLConfig.ensure_model_dirs()
        
        if load_latest:
            self.load_model()
    
    def label_dataset(
        self, 
        df: pd.DataFrame,
        tp_percent: float = None,
        sl_percent: float = None,
        lookahead: int = None
    ) -> pd.DataFrame:
        """
        Label each candle with success (1) or failure (0)
        Success = TP hit before SL in next N candles
        
        Args:
            df: DataFrame with OHLCV data
            tp_percent: Take profit percentage (uses ATR-based if None)
            sl_percent: Stop loss percentage (uses ATR-based if None)
            lookahead: Number of candles to look ahead
            
        Returns:
            DataFrame with 'label' column added
        """
        if lookahead is None:
            lookahead = MLConfig.LOOKAHEAD_CANDLES
        
        df = df.copy()
        labels = []
        
        # Calculate ATR for dynamic TP/SL if not provided
        if tp_percent is None or sl_percent is None:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean()
            atr_percent = (atr / df['close']) * 100
        
        for i in range(len(df)):
            # Can't label last N candles (no lookahead available)
            if i >= len(df) - lookahead:
                labels.append(-1)  # Invalid label
                continue
            
            entry_price = df['close'].iloc[i]
            
            # Determine TP/SL based on ATR if not fixed
            if tp_percent is None or sl_percent is None:
                current_atr = atr_percent.iloc[i]
                tp_pct, sl_pct = MLConfig.get_tp_sl_by_atr(current_atr)
            else:
                tp_pct, sl_pct = tp_percent, sl_percent
            
            # Calculate TP and SL levels for LONG
            tp_long = entry_price * (1 + tp_pct / 100)
            sl_long = entry_price * (1 - sl_pct / 100)
            
            # Calculate TP and SL levels for SHORT
            tp_short = entry_price * (1 - tp_pct / 100)
            sl_short = entry_price * (1 + sl_pct / 100)
            
            # Check next N candles
            future_highs = df['high'].iloc[i+1:i+1+lookahead]
            future_lows = df['low'].iloc[i+1:i+1+lookahead]
            
            # LONG scenario: Check if TP hit before SL
            tp_hit_long = (future_highs >= tp_long).any()
            sl_hit_long = (future_lows <= sl_long).any()
            
            if tp_hit_long and sl_hit_long:
                # Both hit, check which came first
                tp_idx_long = future_highs[future_highs >= tp_long].index[0]
                sl_idx_long = future_lows[future_lows <= sl_long].index[0]
                long_success = tp_idx_long < sl_idx_long
            elif tp_hit_long:
                long_success = True
            else:
                long_success = False
            
            # SHORT scenario: Check if TP hit before SL
            tp_hit_short = (future_lows <= tp_short).any()
            sl_hit_short = (future_highs >= sl_short).any()
            
            if tp_hit_short and sl_hit_short:
                # Both hit, check which came first
                tp_idx_short = future_lows[future_lows <= tp_short].index[0]
                sl_idx_short = future_highs[future_highs >= sl_short].index[0]
                short_success = tp_idx_short < sl_idx_short
            elif tp_hit_short:
                short_success = True
            else:
                short_success = False
            
            # Label: 1 if at least one direction successful, 0 otherwise
            # We'll train a model that predicts "tradeable moment" regardless of direction
            # Direction will be determined by other indicators (MA, trend, etc.)
            label = 1 if (long_success or short_success) else 0
            
            labels.append(label)
        
        df['label'] = labels
        
        # Remove invalid labels
        df = df[df['label'] != -1]
        
        return df
    
    def prepare_training_data(
        self,
        df: pd.DataFrame,
        balance_classes: bool = True
    ) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare features and labels for training
        
        Args:
            df: Labeled DataFrame with features
            balance_classes: Whether to balance positive/negative samples
            
        Returns:
            Tuple of (X, y, feature_names)
        """
        # Get feature names from FeatureEngineer
        exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                       'label', 'delta', 'cvd_ma20', 'volume_ma20', 'bb_upper', 
                       'bb_lower', 'vwap', 'vwap_rolling']
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].values
        y = df['label'].values
        
        # Handle NaN/Inf
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        
        # Balance classes if requested
        if balance_classes:
            from imblearn.over_sampling import SMOTE
            try:
                smote = SMOTE(random_state=42)
                X, y = smote.fit_resample(X, y)
            except:
                # If SMOTE fails, skip balancing
                pass
        
        return X, y, feature_cols
    
    def train(
        self,
        df_labeled: pd.DataFrame,
        validation_split: float = 0.2,
        save_model: bool = True
    ) -> Dict:
        """
        Train LightGBM model with time-series walk-forward validation
        
        Args:
            df_labeled: DataFrame with features and labels
            validation_split: Fraction of data for validation
            save_model: Whether to save the trained model
            
        Returns:
            Dictionary with training metrics
        """
        print(f"📊 Preparing training data from {len(df_labeled)} samples...")
        
        # Prepare data
        X, y, feature_names = self.prepare_training_data(df_labeled)
        self.feature_names = feature_names
        
        print(f"✅ Features prepared: {len(feature_names)} features")
        print(f"   Positive samples: {sum(y == 1)} ({sum(y == 1)/len(y)*100:.1f}%)")
        print(f"   Negative samples: {sum(y == 0)} ({sum(y == 0)/len(y)*100:.1f}%)")
        
        # Time-series split (no shuffling, preserves temporal order)
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_val_scaled = self.scaler.transform(X_val)
        
        # Train LightGBM
        print("\n🚀 Training LightGBM model...")
        
        train_data = lgb.Dataset(X_train_scaled, label=y_train)
        val_data = lgb.Dataset(X_val_scaled, label=y_val, reference=train_data)
        
        self.model = lgb.train(
            MLConfig.LGBM_PARAMS,
            train_data,
            num_boost_round=500,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'val'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50),
                lgb.log_evaluation(period=50)
            ]
        )
        
        # Evaluate
        print("\n📈 Evaluating model...")
        
        y_train_pred = (self.model.predict(X_train_scaled) > 0.5).astype(int)
        y_val_pred = (self.model.predict(X_val_scaled) > 0.5).astype(int)
        
        y_train_proba = self.model.predict(X_train_scaled)
        y_val_proba = self.model.predict(X_val_scaled)
        
        metrics = {
            'train_accuracy': accuracy_score(y_train, y_train_pred),
            'val_accuracy': accuracy_score(y_val, y_val_pred),
            'val_precision': precision_score(y_val, y_val_pred),
            'val_recall': recall_score(y_val, y_val_pred),
            'val_roc_auc': roc_auc_score(y_val, y_val_proba),
            'train_samples': len(y_train),
            'val_samples': len(y_val),
            'num_features': len(feature_names),
            'training_date': datetime.now().isoformat()
        }
        
        print("\n✅ Training Complete!")
        print(f"   Train Accuracy: {metrics['train_accuracy']:.4f}")
        print(f"   Val Accuracy: {metrics['val_accuracy']:.4f}")
        print(f"   Val Precision: {metrics['val_precision']:.4f}")
        print(f"   Val Recall: {metrics['val_recall']:.4f}")
        print(f"   Val ROC-AUC: {metrics['val_roc_auc']:.4f}")
        
        self.metadata = metrics
        
        # Save model
        if save_model:
            self.save_model()
        
        return metrics
    
    def predict(self, features: Dict) -> Tuple[float, int]:
        """
        Predict probability for a single set of features
        
        Args:
            features: Dictionary of feature_name -> value
            
        Returns:
            Tuple of (probability, prediction)
        """
        if self.model is None:
            raise ValueError("Model not loaded. Train or load a model first.")
        
        # Create feature vector in correct order
        X = np.array([features.get(fname, 0) for fname in self.feature_names])
        X = X.reshape(1, -1)
        
        # Handle NaN/Inf
        X = np.nan_to_num(X, nan=0.0, posinf=1e10, neginf=-1e10)
        
        # Scale
        X_scaled = self.scaler.transform(X)
        
        # Predict
        probability = self.model.predict(X_scaled)[0]
        prediction = 1 if probability > 0.5 else 0
        
        return probability, prediction
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """
        Get top N most important features
        
        Returns:
            Dictionary of feature_name -> importance
        """
        if self.model is None:
            return {}
        
        importance = self.model.feature_importance(importance_type='gain')
        
        feature_importance = dict(zip(self.feature_names, importance))
        
        # Sort by importance
        sorted_features = sorted(
            feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]
        
        return dict(sorted_features)
    
    def save_model(self):
        """Save model, scaler, feature names, and metadata"""
        print(f"\n💾 Saving model to {MLConfig.LATEST_MODEL_DIR}...")
        
        # Save model
        model_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'model.txt')
        self.model.save_model(model_path)
        
        # Save scaler
        scaler_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'scaler.pkl')
        joblib.dump(self.scaler, scaler_path)
        
        # Save feature names
        features_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'feature_names.json')
        with open(features_path, 'w') as f:
            json.dump(self.feature_names, f)
        
        # Save metadata
        metadata_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        # Archive copy with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_dir = os.path.join(MLConfig.ARCHIVE_MODEL_DIR, f'model_{timestamp}')
        os.makedirs(archive_dir, exist_ok=True)
        
        self.model.save_model(os.path.join(archive_dir, 'model.txt'))
        joblib.dump(self.scaler, os.path.join(archive_dir, 'scaler.pkl'))
        
        with open(os.path.join(archive_dir, 'feature_names.json'), 'w') as f:
            json.dump(self.feature_names, f)
        
        with open(os.path.join(archive_dir, 'metadata.json'), 'w') as f:
            json.dump(self.metadata, f, indent=2)
        
        print(f"✅ Model saved successfully!")
    
    def load_model(self):
        """Load latest trained model"""
        model_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'model.txt')
        scaler_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'scaler.pkl')
        features_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'feature_names.json')
        metadata_path = os.path.join(MLConfig.LATEST_MODEL_DIR, 'metadata.json')
        
        if not os.path.exists(model_path):
            print("⚠️  No trained model found. Train a model first.")
            return False
        
        try:
            self.model = lgb.Booster(model_file=model_path)
            self.scaler = joblib.load(scaler_path)
            
            with open(features_path, 'r') as f:
                self.feature_names = json.load(f)
            
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            
            print(f"✅ Model loaded successfully!")
            print(f"   Trained: {self.metadata.get('training_date', 'Unknown')}")
            print(f"   Val Accuracy: {self.metadata.get('val_accuracy', 0):.4f}")
            print(f"   Val ROC-AUC: {self.metadata.get('val_roc_auc', 0):.4f}")
            
            return True
        except Exception as e:
            print(f"❌ Error loading model: {e}")
            return False
