#!/usr/bin/env bash
# Termina el setup desde donde aws_setup.sh murió.
# Idempotente: lo puedes correr más de una vez.
#
# Uso:
#   chmod +x setup_continue.sh
#   ./setup_continue.sh 2>&1 | tee ~/setup_continue.log

set -euo pipefail

APP_DIR="/opt/obras-cerca"
DB_NAME="obrascerca_v2"
DB_USER="obrascerca_app"
DOMAIN="obrascerca.trinitylabs.app"
UVICORN_PORT="8000"
FRONTEND_WEBROOT="/var/www/obras-cerca"
SERVICE_NAME="obras-cerca-backend"

log() { echo -e "\n\033[1;32m▶ $*\033[0m"; }
warn() { echo -e "\n\033[1;33m⚠ $*\033[0m"; }

DB_PASS=$(sudo cat /etc/obras-cerca-db-pass)

# ---------- 1. Resetear BD ----------
log "1/6: Resetear obrascerca_v2"
sudo -u postgres psql -c "DROP DATABASE IF EXISTS $DB_NAME;"
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8';"
sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# ---------- 2. Schema + seed como user app ----------
log "2/6: Schema + distritos"
cd "$APP_DIR/db"
PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f schema.sql >/dev/null
PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f seed_distritos.sql >/dev/null
log "Schema y 50 distritos cargados"

# ---------- 3. Snapshot demo como postgres ----------
log "3/6: Snapshot demo (como superuser para deferir FKs)"
grep -v '^\\' seeds/demo_snapshot.sql > /tmp/demo_clean.sql
sudo -u postgres psql -d "$DB_NAME" \
    -c "SET session_replication_role = replica;" \
    -f /tmp/demo_clean.sql \
    -c "SET session_replication_role = origin;" >/dev/null
rm /tmp/demo_clean.sql
log "Demo cargado"

# ---------- 4. Verificación ----------
log "4/6: Verificación de datos"
sudo -u postgres psql -d "$DB_NAME" -c "
SELECT 'entidades' AS tabla, COUNT(*) FROM entidad
UNION ALL SELECT 'obras', COUNT(*) FROM obra
UNION ALL SELECT 'distritos_mvp', COUNT(*) FROM distrito WHERE ambito_mvp
UNION ALL SELECT 'senales', COUNT(*) FROM senal_revision
UNION ALL SELECT 'informes', COUNT(*) FROM informe_control
UNION ALL SELECT 'procedimientos', COUNT(*) FROM procedimiento_seleccion
UNION ALL SELECT 'proyectos_mef', COUNT(*) FROM proyecto_mef;
"

# ---------- 5. systemd unit ----------
log "5/6: systemd unit $SERVICE_NAME"
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Obras Cerca FastAPI backend
After=network.target postgresql.service

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/.venv/bin:/usr/bin:/bin"
EnvironmentFile=$APP_DIR/backend/.env
ExecStart=$APP_DIR/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port $UVICORN_PORT --workers 1
Restart=always
RestartSec=3
StandardOutput=append:/var/log/obras-cerca-backend.log
StandardError=append:/var/log/obras-cerca-backend.log

[Install]
WantedBy=multi-user.target
EOF

sudo touch /var/log/obras-cerca-backend.log
sudo chown ubuntu:ubuntu /var/log/obras-cerca-backend.log
sudo mkdir -p /var/log/obras-cerca
sudo chown ubuntu:ubuntu /var/log/obras-cerca

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl restart $SERVICE_NAME
sleep 3

if curl -fsS http://127.0.0.1:$UVICORN_PORT/api/health >/dev/null 2>&1; then
    log "Backend OK en puerto $UVICORN_PORT"
    curl -s http://127.0.0.1:$UVICORN_PORT/api/health
    echo ""
    curl -s http://127.0.0.1:$UVICORN_PORT/api/stats
    echo ""
else
    warn "Backend NO responde. Logs:"
    sudo journalctl -u $SERVICE_NAME -n 30 --no-pager
    exit 1
fi

# ---------- 6. nginx site ----------
log "6/6: nginx site $DOMAIN"
sudo mkdir -p "$FRONTEND_WEBROOT"
sudo chown ubuntu:ubuntu "$FRONTEND_WEBROOT"

if [ ! -f "$FRONTEND_WEBROOT/index.html" ]; then
    cat > "$FRONTEND_WEBROOT/index.html" <<'EOF'
<!doctype html>
<html><body style="font-family:sans-serif;padding:40px;background:#faf8f5">
<h1 style="color:#9f5442;font-family:Georgia,serif">Obras Cerca — backend OK</h1>
<p>API: <a href="/api/health">/api/health</a></p>
<p>Frontend aún no desplegado.</p>
</body></html>
EOF
fi

sudo tee /etc/nginx/sites-available/obras-cerca > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    root $FRONTEND_WEBROOT;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:$UVICORN_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
EOF

sudo ln -sf /etc/nginx/sites-available/obras-cerca /etc/nginx/sites-enabled/obras-cerca
sudo nginx -t
sudo systemctl reload nginx

# ---------- Final ----------
echo ""
echo "=============================================================="
echo "  ✓ SETUP COMPLETO"
echo "=============================================================="
echo ""
echo "  TOKEN PARA TERRAFORM (cópialo entero):"
echo ""
grep INGESTA "$APP_DIR/backend/.env"
echo ""
echo "  IP pública: 34.230.30.239"
echo "  Backend systemd: $SERVICE_NAME"
echo "  Backend logs: /var/log/obras-cerca-backend.log"
echo ""
echo "=============================================================="
echo "  SIGUIENTES PASOS"
echo "=============================================================="
echo ""
echo "  1. En Hostinger DNS de trinitylabs.app, agrega:"
echo "       Type:  A"
echo "       Name:  obrascerca"
echo "       Value: 34.230.30.239"
echo "       TTL:   3600"
echo ""
echo "  2. Cuando propague (5-15 min), corre certbot:"
echo "       sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email anderssongodoygarcia@gmail.com"
echo ""
echo "  3. Desde tu PC, sube el frontend:"
echo "       .\\infra\\deploy_frontend.ps1"
echo ""
echo "  4. Desde tu PC, deploya el cron:"
echo "       cd infra; copy terraform.tfvars.example terraform.tfvars"
echo "       notepad terraform.tfvars   (pega el INGESTA_TOKEN de arriba)"
echo "       terraform init; terraform apply"
echo ""
echo "=============================================================="
