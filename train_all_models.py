"""
Multi-Model Training Script
Trains ML models for Top 20 cryptocurrencies by volume
"""
import argparse
import pandas as pd
from datetime import datetime
import os
import time
from src.binance_client import get_client
from src.feature_engineering import FeatureEngineer
from src.ml_engine import MLEngine
from src.ml_config import MLConfig


def train_single_model(symbol: str, timeframe: str, days: int) -> dict:
    """
    Train a model for a single cryptocurrency
    
    Returns:
        dict with training results or None if failed
    """
    print(f"\n{'='*60}")
    print(f"🎯 Training model for {symbol}")
    print(f"{'='*60}")
    
    try:
        client = get_client()
        
        # Download data
        print(f"📥 Downloading {days} days of {symbol} data...")
        
        # Calculate candles needed
        timeframe_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        
        minutes_per_candle = timeframe_minutes.get(timeframe, 5)
        candles_per_day = 1440 // minutes_per_candle
        total_candles = days * candles_per_day
        
        # Download in batches
        all_data = []
        batch_size = 1500
        
        for i in range(0, total_candles, batch_size):
            remaining = min(batch_size, total_candles - i)
            df_batch = client.get_ohlcv(symbol, timeframe, limit=remaining)
            
            if df_batch is not None and not df_batch.empty:
                all_data.append(df_batch)
                print(f"  ✓ Downloaded {len(df_batch)} candles")
            else:
                break
            
            time.sleep(0.5)  # Rate limiting
        
        if not all_data:
            print(f"❌ Failed to download data for {symbol}")
            return None
        
        df = pd.concat(all_data, ignore_index=True)
        df = df.drop_duplicates(subset=['timestamp'], keep='first')
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"✅ Downloaded {len(df)} candles")
        
        # Calculate features
        print("🔧 Calculating features...")
        fe = FeatureEngineer(df)
        df_features = fe.calculate_all_features()
        print(f"✅ Calculated {len(fe.get_feature_names())} features")
        
        # Label data
        print("🏷️  Labeling data...")
        ml_engine = MLEngine(load_latest=False)
        df_labeled = ml_engine.label_dataset(df_features)
        
        print(f"✅ Labeled {len(df_labeled)} samples")
        
        if len(df_labeled) < 500:
            print(f"⚠️  Warning: Only {len(df_labeled)} samples (very low)")
        
        # Train model
        print("\n🚀 Training model...")
        metrics = ml_engine.train(df_labeled, validation_split=0.2, save_model=False)
        
        # Save to symbol-specific directory
        symbol_name = symbol.split('/')[0]
        symbol_dir = os.path.join(MLConfig.MODEL_DIR, symbol_name)
        os.makedirs(symbol_dir, exist_ok=True)
        
        # Save model files
        ml_engine.model.save_model(os.path.join(symbol_dir, 'model.txt'))
        
        import joblib
        import json
        joblib.dump(ml_engine.scaler, os.path.join(symbol_dir, 'scaler.pkl'))
        
        with open(os.path.join(symbol_dir, 'feature_names.json'), 'w') as f:
            json.dump(ml_engine.feature_names, f)
        
        metrics['symbol'] = symbol
        metrics['timeframe'] = timeframe
        with open(os.path.join(symbol_dir, 'metadata.json'), 'w') as f:
            json.dump(metrics, f, indent=2)
        
        print(f"\n✅ Model saved to: {symbol_dir}")
        print(f"   Accuracy: {metrics['val_accuracy']:.2%}")
        print(f"   Precision: {metrics['val_precision']:.2%}")
        print(f"   ROC-AUC: {metrics['val_roc_auc']:.3f}")
        
        return metrics
        
    except Exception as e:
        print(f"❌ Error training {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    parser = argparse.ArgumentParser(description='Train models for Top 20 cryptocurrencies')
    parser.add_argument('--timeframe', type=str, default='5m',
                       help='Timeframe for training (default: 5m)')
    parser.add_argument('--days', type=int, default=30,
                       help='Days of training data (default: 30)')
    parser.add_argument('--limit', type=int, default=20,
                       help='Number of top cryptos to train (default: 20)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 MULTI-MODEL TRAINING")
    print("=" * 60)
    print(f"Timeframe: {args.timeframe}")
    print(f"Training Days: {args.days}")
    print(f"Top Cryptos: {args.limit}")
    print("=" * 60)
    print()
    
    # Get top cryptos by volume
    print("📊 Getting top cryptocurrencies by volume...")
    client = get_client()
    top_cryptos = client.get_top_by_volume(limit=args.limit)
    
    symbols = [crypto['symbol'] for crypto in top_cryptos]
    
    print(f"\n✅ Will train models for {len(symbols)} cryptocurrencies:")
    for i, symbol in enumerate(symbols, 1):
        display = client.get_display_symbol(symbol).replace('/USDT', '')
        print(f"  {i:2d}. {display}")
    
    print("\n" + "=" * 60)
    input("Press ENTER to start training (or Ctrl+C to cancel)...")
    print()
    
    # Train all models
    results = []
    successful = 0
    failed = 0
    
    start_time = time.time()
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\n{'='*60}")
        print(f"Progress: {i}/{len(symbols)}")
        print(f"{'='*60}")
        
        result = train_single_model(symbol, args.timeframe, args.days)
        
        if result:
            results.append(result)
            successful += 1
        else:
            failed += 1
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("📊 TRAINING SUMMARY")
    print("=" * 60)
    print(f"Total Time: {elapsed/60:.1f} minutes")
    print(f"Successful: {successful}/{len(symbols)}")
    print(f"Failed: {failed}/{len(symbols)}")
    print()
    
    if results:
        print("Model Performance:")
        print("-" * 60)
        for r in results:
            display = client.get_display_symbol(r['symbol']).replace('/USDT', '')
            print(f"{display:8s} | Acc: {r['val_accuracy']:.1%} | "
                  f"Prec: {r['val_precision']:.1%} | "
                  f"AUC: {r['val_roc_auc']:.3f}")
    
    print("\n" + "=" * 60)
    print("✅ TRAINING COMPLETE!")
    print("=" * 60)
    print("\nYou can now start the bot with:")
    print("  python bot_telegram.py")
    print()


if __name__ == '__main__':
    main()
