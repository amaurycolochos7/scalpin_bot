# 🤖 Scalping Trading Bot

Bot de análisis técnico profesional para Binance Futures optimizado para scalping.

## Características

- 📊 **Análisis Multi-Timeframe (MTF)**: Analiza 5 timeframes (1D, 4H, 1H, 15M, 5M)
- ⚡ **Optimizado para Scalping**: TP/SL ajustados para movimientos rápidos
- 🎯 **Alta Precisión**: Solo muestra señales con alineación de múltiples timeframes
- 💡 **Wizard Interactivo**: Configuración guiada paso a paso
- 📱 **Telegram Bot**: Control completo desde tu teléfono

## Requisitos

- Python 3.9 o superior
- Cuenta de Binance con API Key (solo permisos de lectura)
- Bot de Telegram (crear con @BotFather)

## Instalación

### Windows (Local o AWS Windows Server)

1. **Clonar el repositorio**
   ```powershell
   git clone https://github.com/amaurycolochos7/scalpin_bot.git
   cd scalpin_bot
   ```

2. **Crear entorno virtual**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Instalar dependencias**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Configurar credenciales**
   ```powershell
   copy .env.example .env
   notepad .env
   ```
   
   Edita el archivo `.env` y agrega:
   - Tu Binance API Key y Secret
   - Tu Telegram Bot Token

5. **Ejecutar el bot**
   ```powershell
   python bot_telegram.py
   ```

### Deployment en AWS Windows Server

Ver guía detallada: [DEPLOYMENT_AWS.md](DEPLOYMENT_AWS.md)

## Uso

1. Abre Telegram y busca tu bot
2. Envía `/start` para ver el menú principal
3. Opciones disponibles:
   - **Analizar Moneda**: Escribe BTC, ETH, SOL, etc.
   - **Ver Oportunidades**: Escanea las mejores señales del mercado
   - **Escanear Mercado**: Vista rápida de todas las monedas
   - **Top Movers**: Monedas con mayor movimiento en 24h

## Estructura del Proyecto

```
scalpin_bot/
├── bot_telegram.py          # Bot principal de Telegram
├── src/
│   ├── config.py           # Configuración
│   ├── binance_client.py   # Cliente de Binance
│   ├── technical_analysis.py  # Análisis técnico
│   ├── mtf_analysis.py     # Análisis multi-timeframe
│   └── formatters.py       # Formateo de mensajes
├── .env.example            # Plantilla de configuración
├── .gitignore             # Archivos ignorados
├── requirements.txt        # Dependencias
└── README.md              # Este archivo
```

## Seguridad

⚠️ **IMPORTANTE**: Nunca compartas tu archivo `.env` ni lo subas a GitHub

- El archivo `.gitignore` ya está configurado para proteger tus credenciales
- Usa solo permisos de LECTURA en tu Binance API Key
- No actives permisos de trading ni retiros

## Soporte

Si encuentras algún error, abre un issue en GitHub.

## Licencia

MIT License - Ver archivo LICENSE para más detalles
