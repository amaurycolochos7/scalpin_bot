"""
Confluence Scorer Module
Combines technical analysis with ML predictions for high-confidence signals
"""
from typing import Dict, Optional, Tuple
import pandas as pd
from src.technical_analysis import TechnicalAnalyzer
from src.feature_engineering import FeatureEngineer  
from src.ml_engine import MLEngine
from src.ml_config import MLConfig
from src.binance_client import get_client


class ConfluenceScorer:
    """
    Combines technical indicators with ML predictions
    Only produces signals when ML probability > threshold
    """
    
    def __init__(self):
        """Initialize confluence scorer with ML engine"""
        self.ml_engine = MLEngine(load_latest=True)
        self.client = get_client()
    
    def get_unified_signal(
        self,
        symbol: str,
        timeframe: str = None
    ) -> Optional[Dict]:
        """
        Get unified signal combining technical + ML analysis
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT:USDT')
            timeframe: Timeframe for analysis
            
        Returns:
            Dictionary with signal details or None if no signal
        """
        if timeframe is None:
            timeframe = MLConfig.TIMEFRAME_PRIMARY
        
        # Get OHLCV data
        df = self.client.get_ohlcv(
            symbol,
            timeframe,
            limit=MLConfig.LOOKBACK_CANDLES
        )
        
        if df is None or len(df) < 50:
            return None
        
        # Calculate features
        fe = FeatureEngineer(df)
        df_features = fe.calculate_all_features()
        
        # Get latest features for ML
        latest_features = fe.get_latest_features()
        
        # ML Prediction
        if self.ml_engine.model is None:
            ml_probability = 0.0
            ml_prediction = 0
        else:
            ml_probability, ml_prediction = self.ml_engine.predict(latest_features)
        
        # Technical Analysis
        tech_analyzer = TechnicalAnalyzer(df)
        tech_analysis = tech_analyzer.generate_analysis()
        
        # Get signal components
        tech_score = tech_analysis.get('total_score', 0)
        tech_signal = tech_analysis.get('signal', 'NEUTRAL')
        
        # Determine confluence level
        confluence_level = self._calculate_confluence_level(
            ml_probability,
            tech_score
        )
        
        # Determine if entry is allowed
        entry_allowed = (
            ml_probability >= MLConfig.PROBABILITY_THRESHOLD and
            tech_score >= MLConfig.TECHNICAL_SCORE_MIN
        )
        
        # Determine signal direction
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
        
        # Calculate price levels
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
        
        # Get top features contributing to ML decision
        top_features = self._get_top_contributing_features(
            latest_features,
            df_features
        )
        
        result = {
            'symbol': symbol,
            'timeframe': timeframe,
            'signal': signal_type,
            'ml_probability': ml_probability * 100,  # Convert to percentage
            'technical_score': tech_score,
            'confluence_level': confluence_level,
            'entry_allowed': entry_allowed,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'tp_percent': tp_percent if signal_type else None,
            'sl_percent': sl_percent if signal_type else None,
            'atr_percent': atr_percent,
            'top_features': top_features,
            'technical_details': {
                'trend': tech_analysis.get('trend', {}).get('direction', 'Unknown'),
                'momentum': tech_analysis.get('momentum', {}).get('state', 'Unknown'),
                'volatility': tech_analysis.get('volatility', {}).get('state', 'Unknown'),
            }
        }
        
        return result
    
    def _calculate_confluence_level(
        self,
        ml_prob: float,
        tech_score: float
    ) -> str:
        """
        Calculate confluence level based on ML probability and technical score
        
        Returns:
            'ULTRA_HIGH', 'HIGH', 'MEDIUM', or 'LOW'
        """
        if ml_prob >= 0.95 and tech_score >= 80:
            return 'ULTRA_HIGH'
        elif ml_prob >= 0.90 and tech_score >= 70:
            return 'HIGH'
        elif ml_prob >= 0.80 and tech_score >= 60:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def _get_top_contributing_features(
        self,
        latest_features: Dict,
        df_features: pd.DataFrame,
        top_n: int = 5
    ) -> Dict:
        """
        Get top features contributing to the signal
        
        Returns:
            Dictionary of feature descriptions
        """
        features_desc = {}
        
        # Get latest values
        latest = df_features.iloc[-1]
        
        # CVD
        if 'cvd_momentum' in latest_features:
            cvd_mom = latest['cvd_momentum']
            if abs(cvd_mom) > 10:
                direction = "positivo" if cvd_mom > 0 else "negativo"
                features_desc['CVD'] = f"Momentum {direction} ({cvd_mom:.0f})"
        
        # FVG
        if latest.get('fvg_bullish', 0) == 1:
            features_desc['FVG'] = f"Gap alcista detectado ({latest.get('fvg_bullish_size', 0):.2f}%)"
        elif latest.get('fvg_bearish', 0) == 1:
            features_desc['FVG'] = f"Gap bajista detectado ({latest.get('fvg_bearish_size', 0):.2f}%)"
        
        # Order Blocks
        if latest.get('distance_to_ob_bull', 999) < 10:
            features_desc['Order Block'] = f"Order Block alcista cerca ({int(latest.get('distance_to_ob_bull', 0))} velas)"
        elif latest.get('distance_to_ob_bear', 999) < 10:
            features_desc['Order Block'] = f"Order Block bajista cerca ({int(latest.get('distance_to_ob_bear', 0))} velas)"
        
        # Hurst
        if 'hurst' in latest_features:
            hurst = latest['hurst']
            if hurst > 0.55:
                features_desc['Hurst'] = f"Mercado en tendencia ({hurst:.2f})"
            elif hurst < 0.45:
                features_desc['Hurst'] = f"Mercado en rango ({hurst:.2f})"
        
        # Volatility
        if 'volatility_zscore' in latest_features:
            vol_z = latest['volatility_zscore']
            if abs(vol_z) > 1.5:
                state = "alta" if vol_z > 0 else "baja"
                features_desc['Volatilidad'] = f"Volatilidad {state} (Z={vol_z:.2f})"
        
        # Buy/Sell Ratio
        if 'buy_sell_ratio' in latest_features:
            ratio = latest['buy_sell_ratio']
            if ratio > 1.5:
                features_desc['Presión'] = f"Presión compradora fuerte ({ratio:.2f}x)"
            elif ratio < 0.67:
                features_desc['Presión'] = f"Presión vendedora fuerte ({ratio:.2f}x)"
        
        # VWAP
        if 'vwap_deviation' in latest_features:
            vwap_dev = latest['vwap_deviation']
            if abs(vwap_dev) > 0.5:
                direction = "arriba" if vwap_dev > 0 else "abajo"
                features_desc['VWAP'] = f"Precio {direction} de VWAP ({vwap_dev:.2f}%)"
        
        return features_desc
    
    def scan_multiple_symbols(
        self,
        symbols: list,
        timeframe: str = None,
        min_probability: float = None
    ) -> list:
        """
        Scan multiple symbols and return those with high-probability signals
        
        Args:
            symbols: List of symbols to scan
            timeframe: Timeframe for analysis
            min_probability: Minimum ML probability (uses config default if None)
            
        Returns:
            List of signal dictionaries sorted by ML probability
        """
        if min_probability is None:
            min_probability = MLConfig.PROBABILITY_THRESHOLD
        
        signals = []
        
        for symbol in symbols:
            try:
                result = self.get_unified_signal(symbol, timeframe)
                
                if result and result['entry_allowed']:
                    if result['ml_probability'] >= min_probability * 100:
                        signals.append(result)
            except Exception as e:
                print(f"Error analyzing {symbol}: {e}")
                continue
        
        # Sort by ML probability descending
        signals.sort(key=lambda x: x['ml_probability'], reverse=True)
        
        return signals
