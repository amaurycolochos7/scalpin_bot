"""
Verificación completa de indicadores agrupados
"""
from src.binance_client import get_client
from src.mtf_analysis import MultiTimeframeAnalyzer
import json

def verify_all():
    """Verifica que los indicadores agrupados funcionen en múltiples criptos"""
    
    symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
    
    client = get_client()
    analyzer = MultiTimeframeAnalyzer(client)
    
    results = []
    
    print("\n" + "="*70)
    print(" VERIFICACIÓN DE INDICADORES AGRUPADOS ".center(70))
    print("="*70 + "\n")
    
    for symbol in symbols:
        try:
            symbol_name = symbol.replace('/USDT:USDT', '').replace('/USDT', '')
            print(f"📊 {symbol_name}... ", end='', flush=True)
            
            result = analyzer.analyze(symbol)
            
            # Verificar estructura
            assert hasattr(result, 'grouped_votes'), "❌ No tiene grouped_votes"
            grouped = result.grouped_votes
            
            assert 'oscillators' in grouped, "❌ Falta oscillators"
            assert 'moving_averages' in grouped, "❌ Falta moving_averages"
            assert 'summary' in grouped, "❌ Falta summary"
            
            osc = grouped['oscillators']
            ma = grouped['moving_averages']
            summary = grouped['summary']
            
            print("✅")
            
            # Mostrar resumen
            print(f"   Osciladores: {osc['signal']}")
            print(f"   Medias Móviles: {ma['signal']}")
            print(f"   Resumen: {summary['signal']}")
            print(f"   Decisión: {'✅ ' + result.trade_direction if result.should_trade else '⏳ ESPERAR'}")
            print()
            
            results.append({
                'symbol': symbol_name,
                'osc_signal': osc['signal'],
                'ma_signal': ma['signal'],
                'summary_signal': summary['signal'],
                'should_trade': result.should_trade,
                'direction': result.trade_direction if result.should_trade else 'NONE',
                'confidence': result.confidence
            })
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
            results.append({
                'symbol': symbol_name,
                'error': str(e)
            })
    
    print("="*70)
    print("\n📋 RESUMEN DE RESULTADOS:\n")
    
    for r in results:
        if 'error' in r:
            print(f"❌ {r['symbol']}: ERROR - {r['error']}")
        else:
            status = "✅ OPERAR" if r['should_trade'] else "⏳ ESPERAR"
            print(f"{status} {r['symbol']}: {r['summary_signal']} (Confianza: {r['confidence']}%)")
    
    print("\n" + "="*70)
    
    # Verificar que al menos una funcionó
    success_count = sum(1 for r in results if 'error' not in r)
    print(f"\n✅ {success_count}/{len(symbols)} criptos analizadas exitosamente")
    
    if success_count == len(symbols):
        print("\n🎉 ¡TODOS LOS TESTS PASARON! Los indicadores agrupados funcionan correctamente.\n")
    else:
        print(f"\n⚠️  Algunos tests fallaron. Revisar errores arriba.\n")
    
    return results

if __name__ == "__main__":
    verify_all()
