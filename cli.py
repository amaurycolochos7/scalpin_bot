"""
CLI Tool for Trading Bot
Test the bot locally before integrating with Telegram
"""
import sys
import argparse
from colorama import Fore, Style
from src.config import config
from src.binance_client import get_client
from src.technical_analysis import analyze_symbol, SignalType
from src.formatters import CLIFormatter


def command_analizar(args):
    """Analyze a specific cryptocurrency"""
    try:
        print(f"\n{Fore.CYAN}🔍 Analizando {args.symbol}...{Style.RESET_ALL}")
        
        client = get_client()
        symbol = client.normalize_symbol(args.symbol)
        
        if not client.validate_symbol(symbol):
            print(f"{Fore.RED}❌ Error: {symbol} no es un símbolo válido{Style.RESET_ALL}")
            return
        
        # Get analysis
        analysis = analyze_symbol(symbol, args.timeframe)
        
        # Format and print
        formatted = CLIFormatter.format_analysis(symbol, analysis)
        print(formatted)
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")


def command_oportunidades(args):
    """Find trading opportunities across multiple symbols"""
    try:
        print(f"\n{Fore.CYAN}🔍 Buscando oportunidades de trading...{Style.RESET_ALL}\n")
        
        client = get_client()
        opportunities = []
        
        # Analyze each symbol
        for symbol in config.TOP_SYMBOLS:
            try:
                print(f"  Analizando {symbol}...", end="\r")
                analysis = analyze_symbol(symbol, args.timeframe)
                
                # Only include signals above minimum score
                if analysis['score'] >= config.MIN_SIGNAL_SCORE:
                    # Only buy signals
                    if analysis['signal'] in [SignalType.STRONG_BUY, SignalType.BUY]:
                        opportunities.append({
                            'symbol': symbol,
                            'score': analysis['score'],
                            'signal': analysis['signal'],
                            'price': analysis['price'],
                            'reason': analysis['trend']['description'][:80]
                        })
                
            except Exception as e:
                print(f"{Fore.YELLOW}⚠️  No se pudo analizar {symbol}: {str(e)}{Style.RESET_ALL}")
                continue
        
        # Sort by score
        opportunities.sort(key=lambda x: x['score'], reverse=True)
        
        # Format and print
        formatted = CLIFormatter.format_opportunities(opportunities[:args.limit])
        print(formatted)
        
        if opportunities:
            print(f"{Fore.GREEN}✅ Se encontraron {len(opportunities)} oportunidades{Style.RESET_ALL}\n")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")


def command_top(args):
    """Show top cryptocurrencies by volume or change"""
    try:
        client = get_client()
        
        if args.by == 'volumen':
            print(f"\n{Fore.CYAN}🔍 Obteniendo top por volumen...{Style.RESET_ALL}")
            items = client.get_top_by_volume(args.limit)
            title = "🏆 TOP CRIPTOMONEDAS POR VOLUMEN 24H"
        else:
            print(f"\n{Fore.CYAN}🔍 Obteniendo top por cambio...{Style.RESET_ALL}")
            items = client.get_top_by_change(args.limit)
            title = "🏆 TOP CRIPTOMONEDAS POR CAMBIO 24H"
        
        formatted = CLIFormatter.format_top_list(title, items, args.by)
        print(formatted)
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")


def command_escanear(args):
    """Scan multiple symbols and show quick summary"""
    try:
        print(f"\n{Fore.CYAN}🔍 Escaneando símbolos principales...{Style.RESET_ALL}\n")
        
        symbols_to_scan = config.TOP_SYMBOLS[:args.limit]
        
        print(f"{'SÍMBOLO':<12} {'PRECIO':<12} {'SCORE':<8} {'SEÑAL':<20} {'RSI':<8}")
        print("=" * 70)
        
        for symbol in symbols_to_scan:
            try:
                analysis = analyze_symbol(symbol, args.timeframe)
                
                # Get signal emoji
                if analysis['signal'] == SignalType.STRONG_BUY:
                    signal_str = f"{Fore.GREEN}🚀 {analysis['signal'].value}{Style.RESET_ALL}"
                elif analysis['signal'] == SignalType.BUY:
                    signal_str = f"{Fore.GREEN}📈 {analysis['signal'].value}{Style.RESET_ALL}"
                elif analysis['signal'] == SignalType.STRONG_SELL:
                    signal_str = f"{Fore.RED}⚠️  {analysis['signal'].value}{Style.RESET_ALL}"
                elif analysis['signal'] == SignalType.SELL:
                    signal_str = f"{Fore.RED}📉 {analysis['signal'].value}{Style.RESET_ALL}"
                else:
                    signal_str = f"{Fore.YELLOW}➖ {analysis['signal'].value}{Style.RESET_ALL}"
                
                # Get score color
                score = analysis['score']
                if score >= 70:
                    score_str = f"{Fore.GREEN}{score:.1f}{Style.RESET_ALL}"
                elif score >= 55:
                    score_str = f"{Fore.LIGHTGREEN_EX}{score:.1f}{Style.RESET_ALL}"
                elif score <= 30:
                    score_str = f"{Fore.RED}{score:.1f}{Style.RESET_ALL}"
                elif score <= 45:
                    score_str = f"{Fore.LIGHTRED_EX}{score:.1f}{Style.RESET_ALL}"
                else:
                    score_str = f"{Fore.YELLOW}{score:.1f}{Style.RESET_ALL}"
                
                rsi = analysis['indicators']['rsi']
                rsi_str = f"{rsi:.1f}" if rsi else "N/A"
                
                print(f"{symbol:<12} ${analysis['price']:<11,.2f} {score_str:<15} {signal_str:<35} {rsi_str:<8}")
                
            except Exception as e:
                print(f"{symbol:<12} {Fore.RED}Error: {str(e)[:40]}{Style.RESET_ALL}")
                continue
        
        print("=" * 70)
        print("")
        
    except Exception as e:
        print(f"{Fore.RED}❌ Error: {str(e)}{Style.RESET_ALL}")


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="🤖 Trading Bot CLI - Análisis Técnico de Criptomonedas",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Analizar command
    parser_analizar = subparsers.add_parser('analizar', help='Analizar una criptomoneda específica')
    parser_analizar.add_argument('symbol', help='Símbolo de la moneda (ej: BTC, BTCUSDT, BTC/USDT)')
    parser_analizar.add_argument('-t', '--timeframe', default=config.DEFAULT_TIMEFRAME,
                                help=f'Timeframe para el análisis (default: {config.DEFAULT_TIMEFRAME})')
    parser_analizar.set_defaults(func=command_analizar)
    
    # Oportunidades command
    parser_oportunidades = subparsers.add_parser('oportunidades', help='Buscar oportunidades de trading')
    parser_oportunidades.add_argument('-t', '--timeframe', default=config.DEFAULT_TIMEFRAME,
                                     help=f'Timeframe para el análisis (default: {config.DEFAULT_TIMEFRAME})')
    parser_oportunidades.add_argument('-l', '--limit', type=int, default=10,
                                     help='Número máximo de oportunidades a mostrar (default: 10)')
    parser_oportunidades.set_defaults(func=command_oportunidades)
    
    # Top command
    parser_top = subparsers.add_parser('top', help='Top criptomonedas por volumen o cambio')
    parser_top.add_argument('-b', '--by', choices=['volumen', 'cambio'], default='volumen',
                           help='Ordenar por volumen o cambio (default: volumen)')
    parser_top.add_argument('-l', '--limit', type=int, default=10,
                           help='Número de resultados (default: 10)')
    parser_top.set_defaults(func=command_top)
    
    # Escanear command
    parser_escanear = subparsers.add_parser('escanear', help='Escaneo rápido de múltiples símbolos')
    parser_escanear.add_argument('-t', '--timeframe', default=config.DEFAULT_TIMEFRAME,
                                help=f'Timeframe para el análisis (default: {config.DEFAULT_TIMEFRAME})')
    parser_escanear.add_argument('-l', '--limit', type=int, default=15,
                                help='Número de símbolos a escanear (default: 15)')
    parser_escanear.set_defaults(func=command_escanear)
    
    # Parse arguments
    args = parser.parse_args()
    
    # Show help if no command
    if not args.command:
        parser.print_help()
        print(f"\n{Fore.CYAN}Ejemplos de uso:{Style.RESET_ALL}")
        print(f"  python cli.py analizar BTC")
        print(f"  python cli.py oportunidades")
        print(f"  python cli.py top --by cambio")
        print(f"  python cli.py escanear")
        print("")
        sys.exit(0)
    
    # Validate configuration
    try:
        config.validate()
    except ValueError as e:
        print(f"\n{Fore.RED}❌ Error de configuración:{Style.RESET_ALL}")
        print(f"  {str(e)}\n")
        print(f"{Fore.YELLOW}💡 Solución:{Style.RESET_ALL}")
        print(f"  1. Copia el archivo .env.example a .env")
        print(f"  2. Edita .env y agrega tus API keys de Binance")
        print(f"  3. Ejecuta el comando nuevamente\n")
        sys.exit(1)
    
    # Execute command
    try:
        args.func(args)
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}⚠️  Operación cancelada por el usuario{Style.RESET_ALL}\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error inesperado: {str(e)}{Style.RESET_ALL}\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
