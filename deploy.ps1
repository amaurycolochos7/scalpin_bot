# Script de deploy manual para Windows PowerShell
# Uso: .\deploy.ps1

Write-Host "🚀 DEPLOY MANUAL A AWS" -ForegroundColor Green
Write-Host "=====================" -ForegroundColor Green

# Configuración (edita estos valores)
$AWS_HOST = "tu-ip-aws.compute.amazonaws.com"
$AWS_USER = "ubuntu"
$AWS_KEY_PATH = "$env:USERPROFILE\.ssh\aws-key.pem"
$PROJECT_DIR = "/home/ubuntu/trading-bot"

Write-Host ""
Write-Host "🔐 Conectando a AWS..." -ForegroundColor Yellow

$commands = @"
cd $PROJECT_DIR

echo '🛑 Deteniendo bot...'
pkill -f bot_telegram.py || echo 'Bot no estaba corriendo'

echo '📥 Descargando actualización de Git...'
git pull origin main

if [ `$? -ne 0 ]; then
  echo '❌ Error al hacer git pull'
  exit 1
fi

echo '📦 Instalando dependencias...'
pip install -r requirements.txt

echo '🚀 Reiniciando bot en background...'
nohup python bot_telegram.py > bot.log 2>&1 &

sleep 2

echo ''
echo '✅ Deploy completado!'
echo ''
echo '📊 Estado del bot:'
ps aux | grep bot_telegram.py | grep -v grep
echo ''
echo '📄 Últimas 10 líneas del log:'
tail -10 bot.log
"@

ssh -i $AWS_KEY_PATH "$AWS_USER@$AWS_HOST" $commands

Write-Host ""
Write-Host "=====================" -ForegroundColor Green
Write-Host "✅ Script finalizado" -ForegroundColor Green
