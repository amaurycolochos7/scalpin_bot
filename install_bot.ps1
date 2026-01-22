# ============================================
# INSTALADOR AUTOMÁTICO - SCALPING BOT
# ============================================
# Ejecuta este script en PowerShell como Administrador
# en tu RDP de AWS Windows Server

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  INSTALADOR SCALPING BOT v1.0  " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# PASO 1: INSTALAR PYTHON 3.11
# ============================================
Write-Host "[1/7] Instalando Python 3.11..." -ForegroundColor Yellow

$pythonInstaller = "python-3.11.7-amd64.exe"
$pythonUrl = "https://www.python.org/ftp/python/3.11.7/$pythonInstaller"

Write-Host "Descargando Python..." -ForegroundColor Gray
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonInstaller

Write-Host "Instalando Python (esto toma 1-2 minutos)..." -ForegroundColor Gray
Start-Process -FilePath $pythonInstaller -ArgumentList "/quiet", "InstallAllUsers=1", "PrependPath=1", "Include_test=0" -Wait

# Actualizar PATH en la sesión actual
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Python instalado ✓" -ForegroundColor Green
python --version

# ============================================
# PASO 2: INSTALAR GIT
# ============================================
Write-Host ""
Write-Host "[2/7] Instalando Git..." -ForegroundColor Yellow

$gitInstaller = "Git-2.43.0-64-bit.exe"
$gitUrl = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/$gitInstaller"

Write-Host "Descargando Git..." -ForegroundColor Gray
Invoke-WebRequest -Uri $gitUrl -OutFile $gitInstaller

Write-Host "Instalando Git..." -ForegroundColor Gray
Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT", "/NORESTART" -Wait

# Actualizar PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

Write-Host "Git instalado ✓" -ForegroundColor Green

# ============================================
# PASO 3: CLONAR REPOSITORIO
# ============================================
Write-Host ""
Write-Host "[3/7] Clonando repositorio del bot..." -ForegroundColor Yellow

Set-Location C:\

if (Test-Path "C:\scalpin_bot") {
    Write-Host "El directorio ya existe, eliminando..." -ForegroundColor Gray
    Remove-Item -Path "C:\scalpin_bot" -Recurse -Force
}

Write-Host "Clonando desde GitHub..." -ForegroundColor Gray
git clone https://github.com/amaurycolochos7/scalpin_bot.git

if (Test-Path "C:\scalpin_bot") {
    Write-Host "Repositorio clonado ✓" -ForegroundColor Green
} else {
    Write-Host "ERROR: No se pudo clonar el repositorio" -ForegroundColor Red
    exit 1
}

Set-Location C:\scalpin_bot

# ============================================
# PASO 4: CONFIGURAR ENTORNO VIRTUAL
# ============================================
Write-Host ""
Write-Host "[4/7] Configurando entorno virtual..." -ForegroundColor Yellow

# Permitir ejecución de scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

Write-Host "Creando entorno virtual..." -ForegroundColor Gray
python -m venv venv

Write-Host "Entorno virtual creado ✓" -ForegroundColor Green

# ============================================
# PASO 5: INSTALAR DEPENDENCIAS
# ============================================
Write-Host ""
Write-Host "[5/7] Instalando dependencias (esto toma 2-3 minutos)..." -ForegroundColor Yellow

.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Dependencias instaladas ✓" -ForegroundColor Green

# ============================================
# PASO 6: CONFIGURAR CREDENCIALES
# ============================================
Write-Host ""
Write-Host "[6/7] Configurando credenciales..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Write-Host "Archivo .env ya existe, saltando..." -ForegroundColor Gray
} else {
    Copy-Item ".env.example" ".env"
    Write-Host ""
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host "  CONFIGURAR CREDENCIALES" -ForegroundColor Cyan
    Write-Host "═══════════════════════════════════════════" -ForegroundColor Cyan
    Write-Host ""
    
    $binanceApiKey = Read-Host "Ingresa tu BINANCE_API_KEY"
    $binanceSecret = Read-Host "Ingresa tu BINANCE_SECRET_KEY"
    $telegramToken = Read-Host "Ingresa tu TELEGRAM_BOT_TOKEN"
    
    # Crear archivo .env con las credenciales
    $envContent = @"
# Binance API Configuration
BINANCE_API_KEY=$binanceApiKey
BINANCE_SECRET_KEY=$binanceSecret

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=$telegramToken

# Bot Settings
EXCHANGE=binanceusdm
DEFAULT_TIMEFRAME=5m
CANDLES_LIMIT=200
MIN_SIGNAL_SCORE=55
"@
    
    $envContent | Out-File -FilePath ".env" -Encoding UTF8
    Write-Host "Credenciales configuradas ✓" -ForegroundColor Green
}

# ============================================
# PASO 7: PROBAR EL BOT
# ============================================
Write-Host ""
Write-Host "[7/7] Probando el bot..." -ForegroundColor Yellow
Write-Host ""
Write-Host "Presiona Ctrl+C después de ver el mensaje de confirmación" -ForegroundColor Yellow
Write-Host "Luego ejecuta el segundo script para configurar el servicio" -ForegroundColor Yellow
Write-Host ""
Start-Sleep -Seconds 3

.\venv\Scripts\Activate.ps1
python bot_telegram.py
