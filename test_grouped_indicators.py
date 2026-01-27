"""
Script de prueba para verificar indicadores agrupados
"""
import sys
from src.binance_client import get_client
from src.mtf_analysis import MultiTimeframeAnalyzer

def test_grouped_indicators():
    """Prueba los indicadores agrupados en varias criptos"""
    
    # Símbolos a probar
    test_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT', 'BNB/USDT:USDT']
    
    client = get_client()
    analyzer = MultiTimeframeAnalyzer(client)
    
    print("=" * 60)
    print("VERIFICACIÓN DE INDICADORES AGRUPADOS")
    print("=" * 60)
    
    for symbol in test_symbols:
        try:
            print(f"\n{'='*60}")
            print(f"Analizando: {symbol}")
            print(f"{'='*60}")
            
            result = analyzer.analyze(symbol)
            
            # Verificar que grouped_votes existe
            if not hasattr(result, 'grouped_votes'):
                print(f"❌ ERROR: grouped_votes no existe en {symbol}")
                continue
            
            grouped = result.grouped_votes
            
            # Mostrar Osciladores
            osc = grouped['oscillators']
            print(f"\n📊 Osciladores:")
            print(f"   Venta: {osc['short_count']}, Neutral: {osc['neutral_count']}, Compra: {osc['long_count']}")
            print(f"   Señal: {osc['signal']}")
            
            # Mostrar Medias Móviles
            ma = grouped['moving_averages']
            print(f"\n📊 Medias Móviles:")
            print(f"   Venta: {ma['short_count']}, Neutral: {ma['neutral_count']}, Compra: {ma['long_count']}")
            print(f"   Señal: {ma['signal']}")
            
            # Mostrar Resumen
            summary = grouped['summary']
            print(f"\n📊 Resumen:")
            print(f"   Señal: {summary['signal']}")
            print(f"   Razón: {summary['reason']}")
            
            # Mostrar decisión de trading
            print(f"\n💡 Decisión del Bot:")
            if result.should_trade:
                print(f"   ✅ OPERAR: {result.trade_direction}")
                print(f"   Confianza: {result.confidence}%")
                print(f"   Razón: {result.reason}")
            else:
                print(f"   ⏳ ESPERAR")
                print(f"   Razón: {result.reason}")
            
        except Exception as e:
            print(f"\n❌ Error analizando {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("✅ Verificación completada")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_grouped_indicators()
