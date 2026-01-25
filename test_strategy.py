"""Test script for MA7/MA25 strategy - Simple version"""
from src.binance_client import get_client
from src.technical_analysis import TechnicalAnalyzer

client = get_client()
symbol = client.normalize_symbol('KAIA')
print('Testing', symbol)

df = client.get_ohlcv(symbol, '15m')
analyzer = TechnicalAnalyzer(df)
analyzer.calculate_all_indicators()

# Test MA crossover detection
crossover = analyzer.detect_ma_crossover()
print('')
print('=== MA7/MA25 Crossover ===')
print('Signal:', crossover['signal'])

# Test TradingView votes
votes = analyzer.get_tradingview_votes()
print('')
print('=== TradingView 10 Indicators ===')
print('LONG votes:', votes['long_count'])
print('SHORT votes:', votes['short_count'])
print('NEUTRAL:', votes['neutral_count'])
print('Final Signal:', votes['signal'])

print('')
print('=== Votes Breakdown ===')
for name, v in votes['votes'].items():
    vote_str = 'LONG' if v['vote'] > 0 else ('SHORT' if v['vote'] < 0 else 'NEUTRAL')
    print(name + ':', vote_str)

print('')
print('=== Summary ===')
if votes['short_count'] >= 7:
    print('RESULT: STRONG SHORT')
elif votes['short_count'] >= 6:
    print('RESULT: SHORT')
elif votes['long_count'] >= 7:
    print('RESULT: STRONG LONG')
elif votes['long_count'] >= 6:
    print('RESULT: LONG')
else:
    print('RESULT: WAIT')
