# 🚀 Deployment en AWS Windows Server

Guía completa para desplegar el Scalping Trading Bot en una máquina virtual Windows Server en AWS.

---

## Prerrequisitos

Antes de empezar, necesitas:

- ✅ Cuenta de AWS con acceso a EC2
- ✅ Binance API Key y Secret (solo lectura)
- ✅ Telegram Bot Token (creado con @BotFather)
- ✅ Cliente RDP (Remote Desktop) instalado en tu computadora

---

## Paso 1: Crear Instancia EC2 en AWS

### 1.1 Ingresar a AWS Console

1. Ve a [AWS Console](https://console.aws.amazon.com/)
2. Busca "EC2" en el buscador superior
3. Click en "Launch Instance"

### 1.2 Configurar la Instancia

**Nombre y OS:**
- **Nombre**: `scalping-bot`
- **AMI**: Windows Server 2019 Base o 2022 Base
- **Tipo de instancia**: `t2.micro` (Free Tier) o `t2.small` (recomendado)

**Key Pair:**
- Crea un nuevo Key Pair o usa uno existente
- **Importante**: Guarda el archivo `.pem` en lugar seguro

**Security Group (Firewall):**
- ✅ RDP (3389) - Solo tu IP
- ⚠️ No abrir mas puertos (el bot solo necesita salida a internet)

**Storage:**
- 30 GB SSD (suficiente para el bot)

**Click en "Launch Instance"**

### 1.3 Obtener Contraseña de Windows

1. Espera 3-5 minutos a que la instancia inicie
2. Selecciona la instancia → "Connect" → "RDP Client"
3. Click en "Get Password"
4. Sube tu archivo `.pem` del Key Pair
5. Click "Decrypt Password"
6. **Guarda la contraseña** (la necesitarás para RDP)

---

## Paso 2: Conectar a la Instancia

### 2.1 Obtener IP Pública

1. En EC2 Console, copia la **Public IPv4 address** de tu instancia

### 2.2 Conectar por RDP

**En Windows:**
1. Abre "Remote Desktop Connection" (mstsc.exe)
2. Pega la IP pública
3. Click "Connect"
4. Usuario: `Administrator`
5. Contraseña: la que descifraste en paso 1.3

**En Mac:**
1. Descarga "Microsoft Remote Desktop" del App Store
2. Agrega nueva PC con la IP pública
3. Conecta con usuario/contraseña

---

## Paso 3: Preparar Windows Server

### 3.1 Instalar Python

1. Abre PowerShell como Administrador
2. Ejecuta:
   ```powershell
   # Descargar Python installer
   Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.7/python-3.11.7-amd64.exe" -OutFile "python_installer.exe"
   
   # Instalar Python (silencioso, con PATH)
   .\python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
   ```

3. **Reinicia PowerShell** para que tome el PATH
4. Verifica:
   ```powershell
   python --version
   # Debe mostrar: Python 3.11.7
   ```

### 3.2 Instalar Git (Opcional pero recomendado)

```powershell
# Descargar Git
Invoke-WebRequest -Uri "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe" -OutFile "git_installer.exe"

# Instalar Git
.\git_installer.exe /VERYSILENT /NORESTART
```

Reinicia PowerShell después de instalar Git.

---

## Paso 4: Descargar el Bot

### Opción A: Con Git (recomendado)

```powershell
cd C:\
git clone https://github.com/amaurycolochos7/scalpin_bot.git
cd scalpin_bot
```

### Opción B: Descarga Manual

1. Descarga el ZIP desde GitHub
2. Extrae en `C:\scalpin_bot`
3. Abre PowerShell en esa carpeta

---

## Paso 5: Configurar el Bot

### 5.1 Crear Entorno Virtual

```powershell
cd C:\scalpin_bot
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Si da error de permisos, ejecuta primero:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 5.2 Instalar Dependencias

```powershell
pip install -r requirements.txt
```

### 5.3 Configurar Credenciales

```powershell
# Copiar template
copy .env.example .env

# Editar archivo
notepad .env
```

Edita el archivo `.env` y agrega tus credenciales:

```env
# Binance API
BINANCE_API_KEY=tu_api_key_de_binance
BINANCE_SECRET_KEY=tu_secret_key_de_binance

# Telegram Bot
TELEGRAM_BOT_TOKEN=tu_bot_token_de_telegram

# Settings (ya están configurados)
EXCHANGE=binanceusdm
DEFAULT_TIMEFRAME=5m
CANDLES_LIMIT=200
MIN_SIGNAL_SCORE=55
```

**Guarda y cierra** (Ctrl+S, luego cierra Notepad)

---

## Paso 6: Probar el Bot

### 6.1 Ejecutar Manualmente

```powershell
cd C:\scalpin_bot
.\venv\Scripts\Activate.ps1
python bot_telegram.py
```

Deberías ver:
```
Conectando a Binance...
✅ Connected to BINANCEUSDM
OK - Conectado a Binance Futures
Iniciando bot de Telegram...
Bot iniciado - Abre Telegram y busca tu bot
```

### 6.2 Probar en Telegram

1. Abre Telegram en tu teléfono
2. Busca tu bot (el nombre que le diste en @BotFather)
3. Envía `/start`
4. Prueba analizar una moneda: escribe `BTC`

Si funciona correctamente, **presiona Ctrl+C** para detener el bot.

---

## Paso 7: Crear Servicio de Windows (Ejecutar 24/7)

Para que el bot se ejecute automáticamente y siempre esté activo:

### 7.1 Crear Script de Inicio

```powershell
cd C:\scalpin_bot

# Crear script start.ps1
@"
cd C:\scalpin_bot
.\venv\Scripts\Activate.ps1
python bot_telegram.py
"@ | Out-File -FilePath start.ps1 -Encoding UTF8
```

### 7.2 Instalar NSSM (Non-Sucking Service Manager)

```powershell
# Descargar NSSM
Invoke-WebRequest -Uri "https://nssm.cc/release/nssm-2.24.zip" -OutFile "nssm.zip"

# Extraer
Expand-Archive nssm.zip -DestinationPath C:\nssm

# Copiar ejecutable
copy C:\nssm\nssm-2.24\win64\nssm.exe C:\Windows\System32\
```

### 7.3 Crear el Servicio

```powershell
# Crear servicio
nssm install ScalpingBot "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" "-ExecutionPolicy Bypass -File C:\scalpin_bot\start.ps1"

# Configurar directorio de trabajo
nssm set ScalpingBot AppDirectory "C:\scalpin_bot"

# Configurar reinicio automático
nssm set ScalpingBot AppExit Default Restart
nssm set ScalpingBot AppRestartDelay 5000

# Iniciar servicio
nssm start ScalpingBot
```

### 7.4 Verificar el Servicio

```powershell
# Ver status
nssm status ScalpingBot

# Ver logs (si hay problemas)
Get-Content C:\scalpin_bot\nssm.log -Tail 20
```

**Prueba en Telegram** que el bot responde.

---

## Paso 8: Comandos Útiles

### Gestionar el Servicio

```powershell
# Ver status
nssm status ScalpingBot

# Detener
nssm stop ScalpingBot

# Reiniciar
nssm restart ScalpingBot

# Eliminar servicio (si necesitas)
nssm remove ScalpingBot confirm
```

### Ver Logs del Bot

```powershell
# Si el bot genera logs
Get-Content C:\scalpin_bot\bot.log -Tail 50 -Wait
```

---

## Paso 9: Configuración de Firewall (Opcional)

El bot **no necesita puertos de entrada** abiertos. Solo hace conexiones salientes a:
- Binance API (api.binance.com)
- Telegram API (api.telegram.org)

Windows Firewall permite esto por defecto.

---

## Troubleshooting

### El bot no se conecta a Binance

**Problema**: Error de credenciales

**Solución**:
1. Verifica que tu API Key tiene permisos de lectura
2. Verifica que copiaste correctamente API Key y Secret en `.env`
3. Asegúrate de usar `binanceusdm` para Futures

### El bot no responde en Telegram

**Problema**: Token inválido

**Solución**:
1. Verifica el token en `.env`
2. Prueba el token manualmente: `https://api.telegram.org/bot<TU_TOKEN>/getMe`
3. Si no funciona, crea un nuevo bot con @BotFather

### El servicio no inicia

**Problema**: Error de permisos o paths

**Solución**:
```powershell
# Ver logs de NSSM
nssm status ScalpingBot

# Probar start.ps1 manualmente
cd C:\scalpin_bot
.\start.ps1

# Ver errores específicos
```

### El bot se cae después de un tiempo

**Problema**: Error en el código o conexión perdida

**Solución**:
- El servicio NSSM reinicia automáticamente el bot
- Revisa logs para ver el error específico

### La instancia es demasiado lenta

**Problema**: t2.micro muy limitada

**Solución**:
1. Para al bot/servicio
2. En AWS Console, selecciona la instancia
3. Click "Instance state" → "Stop"
4. Click "Actions" → "Instance settings" → "Change instance type"
5. Selecciona `t2.small` o `t3.small`
6. Inicia la instancia de nuevo

---

## Costos Estimados de AWS

- **t2.micro** (Free Tier): $0/mes (primer año) o ~$8/mes después
- **t2.small**: ~$17/mes
- **t3.small**: ~$15/mes

💡 **Recomendación**: Empieza con t2.micro y upgradea si es necesario.

---

## Mantenimiento

### Actualizar el Bot

```powershell
cd C:\scalpin_bot

# Detener servicio
nssm stop ScalpingBot

#Actualizar código (si usas Git)
git pull origin main

# Activar venv e instalar dependencias nuevas
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Reiniciar servicio
nssm start ScalpingBot
```

### Backup de Configuración

```powershell
# Hacer backup del .env
copy C:\scalpin_bot\.env C:\scalpin_bot\.env.backup
```

---

## ✅ Checklist Final

- [ ] Instancia EC2 creada y corriendo
- [ ] Python 3.11+ instalado
- [ ] Bot descargado en `C:\scalpin_bot`
- [ ] Dependencias instaladas
- [ ] Archivo `.env` configurado con credenciales
- [ ] Bot probado manualmente (funciona en Telegram)
- [ ] Servicio de Windows creado con NSSM
- [ ] Bot ejecutándose 24/7
- [ ] Probado desde Telegram (responde correctamente)

---

¡Tu bot de scalping está ahora desplegado y corriendo 24/7 en AWS! 🚀
