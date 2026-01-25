"""
Model Training Script
Downloads historical data and trains the ML model
"""
import argparse
import pandas as pd
from datetime import datetime, timedelta
from src.binance_client import get_client
from src.feature_engineering import FeatureEngineer
from src.ml_engine import MLEngine
from src.ml_config import MLConfig


def download_training_data(
    symbol: str,
    timeframe: str,
    days: int
) -> pd.DataFrame:
    """
    Download historical OHLCV data for training
    
    Args:
        symbol: Trading pair
        timeframe: Timeframe (e.g., '5m', '15m')
        days: Number of days of history
        
    Returns:
        DataFrame with OHLCV data
    """
    print(f"📥 Downloading {days} days of {symbol} data at {timeframe}...")
    
    client = get_client()
    
    # Calculate number of candles needed
    timeframe_minutes = {
        '1m': 1, '5m': 5, '15m': 15, '30m': 30,
        '1h': 60, '4h': 240, '1d': 1440
    }
    
    minutes_per_candle = timeframe_minutes.get(timeframe, 5)
    candles_per_day = 1440 // minutes_per_candle
    total_candles = days * candles_per_day
    
    # Download in batches (Binance limit is 1500 per request)
    all_data = []
    batch_size = 1500
    
    for i in range(0, total_candles, batch_size):
        remaining = min(batch_size, total_candles - i)
        
        df_batch = client.get_ohlcv(symbol, timeframe, limit=remaining)
        
        if df_batch is not None and not df_batch.empty:
            all_data.append(df_batch)
            print(f"  Downloaded {len(df_batch)} candles ({len(all_data) * batch_size}/{total_candles})")
        else:
            break
    
    if not all_data:
        raise ValueError("Failed to download data")
    
    df = pd.concat(all_data, ignore_index=True)
    df = df.drop_duplicates(subset=['timestamp'], keep='first')
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    print(f"✅ Downloaded {len(df)} candles")
    
    return df


def main():
    parser = argparse.ArgumentParser(description='Train ML model for trading')
    parser.add_argument('--symbol', type=str, default='BTC/USDT:USDT',
                       help='Trading pair (default: BTC/USDT:USDT)')
    parser.add_argument('--timeframe', type=str, default='5m',
                       help='Timeframe (default: 5m)')
    parser.add_argument('--days', type=int, default=MLConfig.TRAINING_DAYS,
                       help=f'Days of training data (default: {MLConfig.TRAINING_DAYS})')
    parser.add_argument('--no-save', action='store_true',
                       help='Do not save the model after training')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 ML MODEL TRAINING")
    print("=" * 60)
    print(f"Symbol: {args.symbol}")
    print(f"Timeframe: {args.timeframe}")
    print(f"Training Days: {args.days}")
    print("=" * 60)
    print()
    
    # Download data
    df = download_training_data(args.symbol, args.timeframe, args.days)
    
    # Calculate features
    print("\n🔧 Calculating features...")
    fe = FeatureEngineer(df)
    df_features = fe.calculate_all_features()
    print(f"✅ Calculated {len(fe.get_feature_names())} features")
    
    # Label data
    print("\n🏷️  Labeling data...")
    ml_engine = MLEngine(load_latest=False)
    df_labeled = ml_engine.label_dataset(df_features)
    
    print(f"✅ Labeled {len(df_labeled)} samples")
    print(f"   Positive: {sum(df_labeled['label'] == 1)} ({sum(df_labeled['label'] == 1)/len(df_labeled)*100:.1f}%)")
    print(f"   Negative: {sum(df_labeled['label'] == 0)} ({sum(df_labeled['label'] == 0)/len(df_labeled)*100:.1f}%)")
    
    # Check minimum samples
    if len(df_labeled) < MLConfig.MIN_SAMPLES:
        print(f"⚠️  Warning: Only {len(df_labeled)} samples (recommended: {MLConfig.MIN_SAMPLES}+)")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Training cancelled.")
            return
    
    # Train model
    print("\n" + "=" * 60)
    metrics = ml_engine.train(
        df_labeled,
        validation_split=0.2,
        save_model=not args.no_save
    )
    
    # Show feature importance
    print("\n📊 Top 10 Most Important Features:")
    print("=" * 60)
    feature_importance = ml_engine.get_feature_importance(top_n=10)
    for i, (feature, importance) in enumerate(feature_importance.items(), 1):
        print(f"{i:2d}. {feature:25s} | {importance:10.2f}")
    
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE!")
    print("=" * 60)
    
    if not args.no_save:
        print(f"\nModel saved to: {MLConfig.LATEST_MODEL_DIR}")
        print("\nYou can now use the model with:")
        print("  python bot_telegram.py")
    
    print()


if __name__ == '__main__':
    main()
