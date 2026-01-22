# 📘 Guía de Instalación y Configuración

Esta guía te llevará paso a paso por la instalación y configuración del Trading Bot.

## 📋 Requisitos Previos

- **Python 3.8+** instalado en tu sistema
- **Cuenta de Binance** (crear en https://www.binance.com si no tienes)
- Conexión a internet estable

## 🔧 Instalación Paso a Paso

### Paso 1: Verificar Python

Abre PowerShell o CMD y verifica que tienes Python instalado:

```powershell
python --version
```

Deberías ver algo como `Python 3.8.x` o superior. Si no, descarga Python desde https://www.python.org/downloads/

### Paso 2: Navegar al Proyecto

```powershell
cd C:\Users\Amaury\.gemini\antigravity\scratch\trading-bot
```

### Paso 3: Crear Entorno Virtual

```powershell
python -m venv venv
```

Esto creará una carpeta `venv` con un entorno Python aislado.

### Paso 4: Activar Entorno Virtual

**En Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```

**Si hay error de permisos, ejecuta esto primero:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**En Windows (CMD):**
```cmd
.\venv\Scripts\activate.bat
```

Verás `(venv)` al inicio de tu línea de comandos cuando esté activo.

### Paso 5: Instalar Dependencias

```powershell
pip install -r requirements.txt
```

Este proceso tomará unos minutos. Instalará todas las librerías necesarias.

### Paso 6: Configurar Variables de Entorno

1. **Copiar el archivo de ejemplo:**
   ```powershell
   copy .env.example .env
   ```

2. **Editar el archivo .env:**
   ```powershell
   notepad .env
   ```

3. **Obtener API Keys de Binance:**

   a. Ve a https://www.binance.com/en/my/settings/api-management
   
   b. Haz clic en "Create API"
   
   c. Dale un nombre como "Trading Bot"
   
   d. **MUY IMPORTANTE**: Solo habilita "Enable Reading" ✅
      - NO habilites "Enable Spot & Margin Trading" ❌
      - NO habilites "Enable Futures" ❌
      (Solo necesitamos LEER datos, no ejecutar trades)
   
   e. Copia la "API Key" y "Secret Key"
   
   f. Pega las keys en el archivo `.env`:
   ```env
   BINANCE_API_KEY=tu_api_key_aquí
   BINANCE_SECRET_KEY=tu_secret_key_aquí
   ```
   
   g. Guarda y cierra el archivo

## ✅ Verificación de Instalación

Ejecuta un comando de prueba:

```powershell
python cli.py analizar BTC
```

Si ves un análisis completo de Bitcoin con indicadores técnicos, ¡todo está funcionando! 🎉

## 🎯 Primeros Comandos

Prueba estos comandos para familiarizarte:

```powershell
# Analizar Bitcoin
python cli.py analizar BTC

# Analizar Ethereum
python cli.py analizar ETH

# Buscar oportunidades
python cli.py oportunidades

# Ver top por volumen
python cli.py top

# Escaneo rápido
python cli.py escanear
```

## 🔍 Troubleshooting

### Error: "BINANCE_API_KEY not found"

**Solución:**
- Asegúrate de que el archivo `.env` existe (no `.env.example`)
- Verifica que las keys están correctamente copiadas sin espacios extras
- El archivo debe estar en la raíz del proyecto (misma carpeta que `cli.py`)

### Error: "Failed to connect to Binance"

**Solución:**
- Verifica tu conexión a internet
- Asegúrate de que las API keys son correctas
- Confirma que habilitaste "Enable Reading" en Binance
- Espera unos minutos si acabas de crear las keys (pueden tardar en activarse)

### Error: "Invalid symbol"

**Solución:**
- Usa símbolos válidos de Binance Futures: BTC, ETH, BNB, etc.
- El bot automáticamente agregará "/USDT" si es necesario
- Verifica que el símbolo existe en Binance Futures

### Error de permisos en PowerShell

**Solución:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Módulo no encontrado

**Solución:**
```powershell
# Asegúrate de que el entorno virtual está activado (verás "venv" en tu prompt)
# Reinstala las dependencias
pip install -r requirements.txt
```

## 🔄 Uso Diario

Cada vez que quieras usar el bot:

1. Abre PowerShell
2. Navega al proyecto:
   ```powershell
   cd C:\Users\Amaury\.gemini\antigravity\scratch\trading-bot
   ```
3. Activa el entorno virtual:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
4. Ejecuta tus comandos:
   ```powershell
   python cli.py oportunidades
   ```

## 🚀 Próximos Pasos

Una vez que hayas verificado que todo funciona en modo CLI, estarás listo para:

1. **Fase 3**: Conectar el bot a Telegram
2. **Fase 4**: Configurar alertas automáticas
3. **Fase 5**: Agregar gráficos visuales

Para la integración con Telegram necesitarás:
- Crear un bot con @BotFather
- Obtener el Bot Token
- Agregarlo al archivo `.env`

¡Pero primero asegúrate de que el análisis técnico funciona correctamente en modo local!

## 📞 ¿Necesitas Ayuda?

Si encuentras algún problema:
1. Revisa esta guía de troubleshooting
2. Verifica que todos los pasos se siguieron correctamente
3. Asegúrate de que las API keys tienen los permisos correctos (solo lectura)

---

**¡Listo para comenzar!** 🎯 Ejecuta `python cli.py --help` para ver todos los comandos disponibles.
