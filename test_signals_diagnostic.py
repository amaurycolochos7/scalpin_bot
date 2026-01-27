"""
Script de Diagnóstico Rápido
Verifica cuántas criptomonedas cumplen los criterios de señal AHORA MISMO
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.auto_monitor import AutoMonitor
from dotenv import load_dotenv

load_dotenv()

async def quick_diagnostic():
    """Escanea mercado y muestra estadísticas de señales"""
    
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE SEÑALES - ANÁLISIS EN VIVO")
    print("=" * 60)
    print()
    
    # Initialize monitor
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("❌ ERROR: Falta configuración en .env")
        return
    
    monitor = AutoMonitor(bot_token, int(chat_id))
    
    print("📊 Escaneando mercado...")
    print("⏱️  Esto tomará ~30-60 segundos...")
    print()
    
    # Get all signals
    signals = await monitor.scan_all_symbols()
    
    total_symbols = len(monitor.monitored_symbols)
    total_signals = len(signals)
    
    print("=" * 60)
    print("📈 RESULTADOS DEL ESCANEO")
    print("=" * 60)
    print()
    print(f"✅ Criptomonedas analizadas: {total_symbols}")
    print(f"🎯 Señales encontradas: {total_signals}")
    
    if total_signals > 0:
        percentage = (total_signals / total_symbols) * 100
        print(f"📊 Porcentaje: {percentage:.2f}%")
        print()
        print("🔔 SEÑALES DETECTADAS:")
        print("-" * 60)
        
        for i, signal in enumerate(signals[:10], 1):  # Show top 10
            symbol = signal['symbol_name']
            signal_type = signal['signal']
            strength = signal['signal_strength']
            price = signal['price']
            
            strength_emoji = {
                'confirmed': '✅',
                'partial': '🟡',
                'normal': '⚪'
            }.get(strength, '⚪')
            
            print(f"{i}. {strength_emoji} {symbol}")
            print(f"   Tipo: {signal_type} | Fuerza: {strength}")
            print(f"   Precio: ${price:.8f}")
            print(f"   {signal['reason']}")
            print()
    else:
        print()
        print("❌ NO SE ENCONTRARON SEÑALES")
        print()
        print("💡 Posibles razones:")
        print("   1. Criterios muy estrictos (requiere 3+ velas + MTF)")
        print("   2. Mercado en consolidación/lateral")
        print("   3. Señales ya enviadas en las últimas 2 horas")
        print()
        print("🔧 Soluciones recomendadas:")
        print("   • Reducir velas requeridas de 3+ a 2+")
        print("   • Reducir intervalo anti-spam de 2h a 1h")
        print("   • Permitir señales parciales (solo 15m)")
    
    print()
    print("=" * 60)
    print("📋 ESTADÍSTICAS DE CONFIGURACIÓN ACTUAL")
    print("=" * 60)
    print()
    print("⚙️  Configuración actual:")
    print("   • Velas consecutivas requeridas: 3+")
    print("   • Validación multi-timeframe: SÍ (4H/1H/15m)")
    print("   • Intervalo anti-spam: 2 horas")
    print("   • Frecuencia de escaneo: 5 minutos")
    print()
    
    # Show sample cryptos that are close but didn't meet criteria
    print("🔍 ANÁLISIS DETALLADO (primeras 5 criptos):")
    print("-" * 60)
    
    sample_symbols = monitor.monitored_symbols[:5]
    for symbol in sample_symbols:
        result = await monitor.analyze_symbol(symbol)
        symbol_name = symbol.replace('/USDT:USDT', '')
        
        if result:
            print(f"✅ {symbol_name}: CUMPLE todos los criterios")
        else:
            # Try to get partial info
            print(f"❌ {symbol_name}: No cumple (analizar manualmente)")
    
    print()
    print("=" * 60)
    print("✅ Diagnóstico completado")
    print("=" * 60)

if __name__ == '__main__':
    asyncio.run(quick_diagnostic())
