"""
Quick test script to verify bot functionality
"""
from src.binance_client import get_client
from src.technical_analysis import analyze_symbol

# Test connection and analysis
print("\n" + "="*60)
print("🧪 PROBANDO FUNCIONALIDAD DEL BOT")
print("="*60)

try:
    # Get client
    client = get_client()
    
    # Analyze Bitcoin
    print("\n📊 Analizando BTC/USDT...")
    analysis = analyze_symbol('BTC/USDT', '15m')
    
    print("\n✅ ANÁLISIS EXITOSO!")
    print("-" * 60)
    print(f"💰 Precio BTC: ${analysis['price']:,.2f}")
    print(f"📊 Score: {analysis['score']:.1f}/100")
    print(f"🎯 Señal: {analysis['signal'].value}")
    print(f"📈 RSI: {analysis['indicators']['rsi']:.1f}")
    print(f"📉 MACD: {analysis['indicators']['macd']:.4f}")
    print(f"🔄 Tendencia: {analysis['trend']['direction']}")
    print("-" * 60)
    
    print("\n✅ ¡EL BOT ESTÁ FUNCIONANDO PERFECTAMENTE!")
    print("="*60)
    print("\n🚀 Próximos pasos:")
    print("  1. Ejecuta: python cli.py oportunidades")
    print("  2. Ejecuta: python cli.py escanear")
    print("  3. Ejecuta: python cli.py analizar ETH")
    print()
    
except Exception as e:
    print(f"\n❌ Error: {str(e)}")
    print("Por favor revisa tu configuración en .env")
