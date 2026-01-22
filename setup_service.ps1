# ============================================
# CONFIGURAR SERVICIO DE WINDOWS - SCALPING BOT
# ============================================
# Ejecuta este script DESPUÉS del install_bot.ps1
# Como Administrador en PowerShell

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "  CONFIGURAR SERVICIO WINDOWS   " -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

Set-Location C:\scalpin_bot

# ============================================
# PASO 1: CREAR SCRIPT DE INICIO
# ============================================
Write-Host "[1/4] Creando script de inicio..." -ForegroundColor Yellow

$startScript = @"
Set-Location C:\scalpin_bot
.\venv\Scripts\Activate.ps1
python bot_telegram.py
"@

$startScript | Out-File -FilePath "start.ps1" -Encoding UTF8

Write-Host "Script de inicio creado ✓" -ForegroundColor Green

# ============================================
# PASO 2: DESCARGAR E INSTALAR NSSM
# ============================================
Write-Host ""
Write-Host "[2/4] Instalando NSSM (Service Manager)..." -ForegroundColor Yellow

$nssmZip = "nssm-2.24.zip"
$nssmUrl = "https://nssm.cc/release/$nssmZip"

if (!(Test-Path "C:\Windows\System32\nssm.exe")) {
    Write-Host "Descargando NSSM..." -ForegroundColor Gray
    Invoke-WebRequest -Uri $nssmUrl -OutFile $nssmZip
    
    Write-Host "Extrayendo..." -ForegroundColor Gray
    Expand-Archive -Path $nssmZip -DestinationPath "C:\nssm" -Force
    
    Write-Host "Copiando ejecutable..." -ForegroundColor Gray
    Copy-Item "C:\nssm\nssm-2.24\win64\nssm.exe" "C:\Windows\System32\" -Force
    
    Write-Host "NSSM instalado ✓" -ForegroundColor Green
}
else {
    Write-Host "NSSM ya está instalado ✓" -ForegroundColor Green
}

# ============================================
# PASO 3: CREAR SERVICIO DE WINDOWS
# ============================================
Write-Host ""
Write-Host "[3/4] Creando servicio de Windows..." -ForegroundColor Yellow

# Verificar si el servicio ya existe
$serviceName = "ScalpingBot"
$serviceExists = Get-Service -Name $serviceName -ErrorAction SilentlyContinue

if ($serviceExists) {
    Write-Host "El servicio ya existe, eliminando..." -ForegroundColor Gray
    nssm stop $serviceName
    nssm remove $serviceName confirm
    Start-Sleep -Seconds 2
}

Write-Host "Creando nuevo servicio..." -ForegroundColor Gray

# Instalar servicio
nssm install $serviceName "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" "-ExecutionPolicy Bypass -File C:\scalpin_bot\start.ps1"

# Configurar servicio
nssm set $serviceName AppDirectory "C:\scalpin_bot"
nssm set $serviceName AppExit Default Restart
nssm set $serviceName AppRestartDelay 5000
nssm set $serviceName DisplayName "Scalping Trading Bot"
nssm set $serviceName Description "Bot de trading automatizado para Binance Futures"

Write-Host "Servicio creado ✓" -ForegroundColor Green

# ============================================
# PASO 4: INICIAR SERVICIO
# ============================================
Write-Host ""
Write-Host "[4/4] Iniciando servicio..." -ForegroundColor Yellow

nssm start $serviceName

Start-Sleep -Seconds 3

$status = nssm status $serviceName
Write-Host ""
Write-Host "Estado del servicio: $status" -ForegroundColor Cyan

if ($status -eq "SERVICE_RUNNING") {
    Write-Host ""
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host "  ✓ BOT INSTALADO Y CORRIENDO 24/7" -ForegroundColor Green
    Write-Host "════════════════════════════════════════" -ForegroundColor Green
    Write-Host ""
    Write-Host "Prueba tu bot en Telegram enviando /start" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "COMANDOS ÚTILES:" -ForegroundColor Cyan
    Write-Host "  nssm status ScalpingBot    - Ver estado" -ForegroundColor Gray
    Write-Host "  nssm stop ScalpingBot      - Detener" -ForegroundColor Gray
    Write-Host "  nssm restart ScalpingBot   - Reiniciar" -ForegroundColor Gray
    Write-Host ""
}
else {
    Write-Host ""
    Write-Host "⚠ ERROR: El servicio no inició correctamente" -ForegroundColor Red
    Write-Host "Ejecuta manualmente para ver el error:" -ForegroundColor Yellow
    Write-Host "  cd C:\scalpin_bot" -ForegroundColor Gray
    Write-Host "  .\start.ps1" -ForegroundColor Gray
}
