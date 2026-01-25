# 🚀 Sistema de Auto-Deploy a AWS

## 📋 Opciones Disponibles

### Opción 1: GitHub Actions (Recomendado - Automático 100%)
### Opción 2: Script Manual (Rápido, sin configurar GitHub)

---

## 🎯 Opción 1: GitHub Actions (Automático como Vercel)

### Paso 1: Configurar SSH en AWS

```bash
# En tu máquina AWS (conecta vía SSH)
cd /home/ubuntu
git clone https://github.com/TU_USUARIO/trading-bot.git
cd trading-bot
pip install -r requirements.txt
```

### Paso 2: Agregar Secrets en GitHub

1. Ve a tu repositorio en GitHub
2. Settings → Secrets and variables → Actions → New repository secret
3. Agrega estos 3 secrets:

**AWS_HOST**
```
tu-ec2-ip.compute-1.amazonaws.com
# O la IP pública de tu instancia
```

**AWS_USERNAME**
```
ubuntu
# O el usuario que uses
```

**AWS_SSH_KEY**
```
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
(Tu clave privada .pem completa)
-----END RSA PRIVATE KEY-----
```

### Paso 3: Subir el Workflow a GitHub

El archivo `.github/workflows/deploy.yml` ya está creado.

```bash
git add .github/workflows/deploy.yml
git commit -m "Add auto-deploy workflow"
git push origin main
```

### Paso 4: ¡Listo!

Ahora cada vez que hagas:
```bash
git push origin main
```

GitHub automáticamente:
1. ✅ Detiene el bot en AWS
2. ✅ Hace git pull
3. ✅ Instala dependencias
4. ✅ Reinicia el bot
5. ✅ Te muestra logs

**Ver el deploy:**
- Ve a tu repo → Actions
- Verás el workflow corriendo en tiempo real

---

## 🛠️ Opción 2: Script Manual (Sin GitHub Actions)

Si prefieres no usar GitHub Actions, usa los scripts manuales.

### Para Linux/Mac:

```bash
# 1. Edita deploy.sh con tus datos de AWS
nano deploy.sh

# 2. Dale permisos
chmod +x deploy.sh

# 3. Ejecuta cuando quieras deployar
./deploy.sh
```

### Para Windows:

```powershell
# 1. Edita deploy.ps1 con tus datos de AWS
notepad deploy.ps1

# 2. Ejecuta cuando quieras deployar
.\deploy.ps1
```

---

## 🔧 Configuración Inicial en AWS

### 1. Instalar Git en AWS

```bash
sudo apt update
sudo apt install git -y
```

### 2. Configurar Git Credentials

```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@email.com"

# Para repos privados, usa token de GitHub
git config --global credential.helper store
```

### 3. Crear Servicio Systemd (Opcional - Bot como Servicio)

```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Contenido:
```ini
[Unit]
Description=Trading Bot ML
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/trading-bot
ExecStart=/usr/bin/python3 /home/ubuntu/trading-bot/bot_telegram.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot

# Ver status
sudo systemctl status trading-bot

# Ver logs
journalctl -u trading-bot -f
```

Ahora el deploy script debe usar:
```bash
sudo systemctl restart trading-bot
```

---

## 📊 Monitoreo del Deploy

### Ver Logs en Tiempo Real (AWS)

```bash
# Conecta a AWS
ssh -i ~/.ssh/aws-key.pem ubuntu@tu-ip-aws

# Ver logs del bot
tail -f /home/ubuntu/trading-bot/bot.log

# O si usas systemd
journalctl -u trading-bot -f
```

### Verificar Estado del Bot

```bash
# Ver si está corriendo
ps aux | grep bot_telegram.py

# Ver puerto usado
netstat -tulpn | grep python
```

---

## 🚨 Troubleshooting

### ❌ Error: "Permission denied (publickey)"

**Solución:** Verifica que la clave SSH esté correcta en GitHub Secrets.

```bash
# En tu local, verifica tu clave:
cat ~/.ssh/aws-key.pem

# Debe coincidir con AWS_SSH_KEY en GitHub
```

### ❌ Error: "git pull failed"

**Solución:** Hay conflictos locales en AWS.

```bash
# Conecta a AWS
ssh -i ~/.ssh/aws-key.pem ubuntu@tu-ip-aws

cd /home/ubuntu/trading-bot

# Reset forzado
git fetch origin
git reset --hard origin/main
```

### ❌ Bot no reinicia después del deploy

**Solución:** Ver logs y reiniciar manualmente.

```bash
# Ver último error
tail -50 bot.log

# Reiniciar manualmente
pkill -f bot_telegram.py
nohup python bot_telegram.py > bot.log 2>&1 &
```

---

## 🎯 Workflow Recomendado

### Desarrollo Local:

```bash
# 1. Haz cambios en tu código local
nano bot_telegram.py

# 2. Prueba localmente
python bot_telegram.py

# 3. Cuando esté listo, sube
git add .
git commit -m "Add new feature"
git push origin main

# 4. GitHub Actions hace el deploy automáticamente
# 5. Verifica en GitHub Actions que salió bien
# 6. ¡Listo!
```

### Ver Deploy en GitHub Actions:

1. Ve a tu repo
2. Click en "Actions"
3. Verás el workflow "Auto Deploy to AWS"
4. Click para ver logs en tiempo real

---

## 💡 Tips Avanzados

### Deploy Solo en Tags (Producción)

Edita `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    tags:
      - 'v*'  # Solo cuando haces git tag v1.0.0
```

Luego:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Múltiples Ambientes (Dev + Prod)

Crea 2 workflows:
- `.github/workflows/deploy-dev.yml` → branch `develop`
- `.github/workflows/deploy-prod.yml` → branch `main`

### Rollback Rápido

```bash
# Conecta a AWS
ssh -i ~/.ssh/aws-key.pem ubuntu@tu-ip-aws

cd /home/ubuntu/trading-bot

# Vuelve al commit anterior
git log --oneline  # Ve el hash del commit anterior
git reset --hard HASH_ANTERIOR

# Reinicia
sudo systemctl restart trading-bot
```

---

## ✅ Resumen

**Opción 1 (Automático):**
- Configura GitHub Secrets
- Haz `git push`
- Todo se deployea solo

**Opción 2 (Manual):**
- Ejecuta `./deploy.sh` o `.\deploy.ps1`
- Deploy instantáneo

Ambas opciones funcionan perfectamente. La opción 1 es más "Vercel-like".
