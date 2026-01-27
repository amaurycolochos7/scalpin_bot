"""
Prueba simple de indicadores agrupados
"""
from src.binance_client import get_client
from src.technical_analysis import TechnicalAnalyzer

def test_single_symbol():
    """Prueba un solo símbolo para verificar grouped_votes"""
    
    client = get_client()
    
    # Obtener datos de BTC
    symbol = 'BTC/USDT:USDT'
    print(f"Analizando {symbol}...")
    
    df = client.get_ohlcv(symbol, '15m')
    analyzer = TechnicalAnalyzer(df)
    analyzer.calculate_all_indicators()
    
    # Probar la nueva función
    print("\n✅ Probando get_grouped_tradingview_votes()...")
    grouped = analyzer.get_grouped_tradingview_votes()
    
    print(f"\n📊 Osciladores:")
    osc = grouped['oscillators']
    print(f"   LONG: {osc['long_count']}, SHORT: {osc['short_count']}, NEUTRAL: {osc['neutral_count']}")
    print(f"   Señal: {osc['signal']}")
    
    print(f"\n📊 Medias Móviles:")
    ma = grouped['moving_averages']
    print(f"   LONG: {ma['long_count']}, SHORT: {ma['short_count']}, NEUTRAL: {ma['neutral_count']}")
    print(f"   Señal: {ma['signal']}")
    
    print(f"\n📊 Resumen:")
    summary = grouped['summary']
    print(f"   Señal: {summary['signal']}")
    print(f"   Razón: {summary['reason']}")
    print(f"   Total LONG: {summary['total_long']}/12")
    print(f"   Total SHORT: {summary['total_short']}/12")
    
    print("\n✅ ¡Función funciona correctamente!")
    
if __name__ == "__main__":
    test_single_symbol()
