# 🚀 Instalación Completa por PowerShell

## Prerrequisitos

- ✅ Instancia AWS Windows Server creada
- ✅ Conectado por RDP como Administrador
- ✅ Binance API Key y Secret
- ✅ Telegram Bot Token

---

## PASO 1: Ejecutar Instalador Principal

1. **Abrir PowerShell como Administrador**
   - Click derecho en el menú Start → "Windows PowerShell (Admin)"

2. **Descargar script de instalación**
   ```powershell
   # Descargar script
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/amaurycolochos7/scalpin_bot/main/install_bot.ps1" -OutFile "install_bot.ps1"
   
   # Ejecutar
   .\install_bot.ps1
   ```

3. **El script instalará automáticamente**:
   - ✅ Python 3.11
   - ✅ Git
   - ✅ Clonará el repositorio en `C:\scalpin_bot`
   - ✅ Creará entorno virtual
   - ✅ Instalará todas las dependencias

4. **Cuando te pida credenciales**, ingresa:
   - Tu Binance API Key
   - Tu Binance Secret Key
   - Tu Telegram Bot Token

5. **El bot iniciará automáticamente**
   - Verás: `✅ Connected to BINANCEUSDM`
   - Verás: `Bot iniciado - Abre Telegram y busca tu bot`

6. **Probar en Telegram**:
   - Abre Telegram
   - Busca tu bot
   - Envía `/start`
   - Escribe `BTC`

7. **Si funciona**, presiona **Ctrl+C** para detener

---

## PASO 2: Configurar como Servicio (24/7)

1. **Descargar script de servicio**
   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/amaurycolochos7/scalpin_bot/main/setup_service.ps1" -OutFile "setup_service.ps1"
   
   # Ejecutar
   .\setup_service.ps1
   ```

2. **El script configurará**:
   - ✅ Script de inicio automático
   - ✅ NSSM (Service Manager)
   - ✅ Servicio de Windows "ScalpingBot"
   - ✅ Reinicio automático si falla
   - ✅ Inicia el servicio

3. **Verificar**:
   ```powershell
   nssm status ScalpingBot
   ```
   Debe decir: `SERVICE_RUNNING`

4. **Probar en Telegram** que sigue funcionando

---

## ✅ ¡LISTO!

Tu bot ahora está corriendo 24/7 en AWS Windows Server.

### Comandos Útiles

```powershell
# Ver estado
nssm status ScalpingBot

# Detener
nssm stop ScalpingBot

# Reiniciar  
nssm restart ScalpingBot

# Ver logs (si hay problemas)
cd C:\scalpin_bot
type nssm.log
```

### Actualizar el Bot

```powershell
# Detener servicio
nssm stop ScalpingBot

# Actualizar código
cd C:\scalpin_bot
git pull

# Activar venv e instalar dependencias
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Reiniciar servicio
nssm start ScalpingBot
```

---

## ⚠️ Si Algo Falla

**Probar manualmente**:
```powershell
cd C:\scalpin_bot
.\venv\Scripts\Activate.ps1
python bot_telegram.py
```

Esto mostrará el error exacto.

**Los errores más comunes**:
- API Key/Secret incorrectos → Revisar `.env`
- Token de Telegram incorrecto → Revisar `.env`
- Puerto bloqueado → No aplica (bot solo hace conexiones salientes)

---

## 💰 Costos AWS

- **t2.micro**: Gratis primer año, luego ~$8/mes
- **t2.small**: ~$17/mes (recomendado)

---

¡Tu bot de scalping funcionando 24/7! 🎯
