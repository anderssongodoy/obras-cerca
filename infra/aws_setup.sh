#!/usr/bin/env bash
# Setup completo de Obras Cerca en EC2 Ubuntu 24.04 t3.micro.
# IDEMPOTENTE: se puede correr más de una vez sin romper nada.
#
# Uso:
#   chmod +x aws_setup.sh
#   ./aws_setup.sh
#
# Pre-requisitos en la EC2:
#   - Ubuntu 24.04 LTS
#   - nginx, python3.12, certbot, git ya instalados (lo demás lo pone este script)
#   - 6+ GB disco libre, swap se crea automáticamente
#
# Lo que hace en orden:
#   1. Swap 2 GB (si no existe)
#   2. Postgres 17 + pgvector via repo oficial PGDG
#   3. Crea BD obrascerca_v2 + usuario obrascerca_app con password random
#   4. Clona el repo público en /opt/obras-cerca
#   5. venv + pip install + schema + restore demo
#   6. systemd unit para uvicorn en puerto 8000
#   7. nginx site para obrascerca.trinitylabs.app (sin SSL todavía)
#   8. Imprime instrucciones para configurar DNS y correr certbot

set -euo pipefail

# ---------- Parámetros (cambia si necesitas) ----------
REPO_URL="https://github.com/anderssongodoy/obras-cerca.git"
REPO_BRANCH="develop"
APP_DIR="/opt/obras-cerca"
DB_NAME="obrascerca_v2"
DB_USER="obrascerca_app"
DOMAIN="obrascerca.trinitylabs.app"
UVICORN_PORT="8000"
FRONTEND_WEBROOT="/var/www/obras-cerca"
SERVICE_NAME="obras-cerca-backend"

# ---------- Helpers ----------
log() { echo -e "\n\033[1;32m▶ $*\033[0m"; }
warn() { echo -e "\n\033[1;33m⚠ $*\033[0m"; }
err() { echo -e "\n\033[1;31m✗ $*\033[0m" >&2; }

# ---------- 1. Swap 2 GB ----------
log "Paso 1/8: Swap"
if swapon --show | grep -q '/swapfile'; then
    warn "Swap ya existe, salto"
else
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
    log "Swap 2 GB activado"
fi

# ---------- 2. Postgres 17 + pgvector via PGDG ----------
log "Paso 2/8: Postgres 17 + pgvector"
if command -v psql >/dev/null; then
    warn "Postgres ya instalado: $(psql --version)"
else
    sudo apt update -qq
    sudo apt install -y -qq curl ca-certificates lsb-release
    sudo install -d /usr/share/postgresql-common/pgdg
    sudo curl -fsSL -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc
    echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        | sudo tee /etc/apt/sources.list.d/pgdg.list >/dev/null
    sudo apt update -qq
    sudo apt install -y -qq postgresql-17 postgresql-17-pgvector postgresql-client-17
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
    log "Postgres instalado: $(psql --version)"
fi

# ---------- 3. BD + usuario ----------
log "Paso 3/8: BD obrascerca_v2 + usuario $DB_USER"
DB_PASS_FILE="/etc/obras-cerca-db-pass"
if sudo test -f "$DB_PASS_FILE"; then
    DB_PASS=$(sudo cat "$DB_PASS_FILE")
    warn "Password ya generado, reuso (en $DB_PASS_FILE)"
else
    DB_PASS=$(openssl rand -hex 16)
    echo "$DB_PASS" | sudo tee "$DB_PASS_FILE" >/dev/null
    sudo chmod 600 "$DB_PASS_FILE"
    log "Password DB nuevo generado y guardado en $DB_PASS_FILE"
fi

# Crear user si no existe
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 || {
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS' CREATEDB;"
}

# Crear DB si no existe
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 || {
    sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER ENCODING 'UTF8';"
}

# Habilitar extensión pgvector
sudo -u postgres psql -d "$DB_NAME" -c "CREATE EXTENSION IF NOT EXISTS vector;"

DSN="host=localhost user=$DB_USER password=$DB_PASS dbname=$DB_NAME"

# ---------- 4. Clone repo ----------
log "Paso 4/8: Clone repo en $APP_DIR"
sudo mkdir -p "$APP_DIR"
sudo chown ubuntu:ubuntu "$APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
    warn "Repo ya clonado, hago git pull"
    cd "$APP_DIR"
    git fetch --all --prune
    git checkout "$REPO_BRANCH"
    git pull origin "$REPO_BRANCH"
else
    git clone -b "$REPO_BRANCH" "$REPO_URL" "$APP_DIR"
fi

# ---------- 5. venv + pip install + schema + datos demo ----------
log "Paso 5/8: venv Python + dependencies"
cd "$APP_DIR/backend"
if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
log "Dependencies instaladas"

# .env
INGESTA_TOKEN=$(openssl rand -hex 32)
cat > "$APP_DIR/backend/.env" <<EOF
APP_ENV=production
DB_DSN=$DSN
ALLOWED_ORIGINS=https://$DOMAIN
LLM_PROVIDER=stub
INGESTA_TOKEN=$INGESTA_TOKEN
EOF
chmod 600 "$APP_DIR/backend/.env"
log ".env creado"

# Schema + seed
log "Paso 5b/8: Schema + datos demo"
cd "$APP_DIR/db"
# setup.py espera que la BD no exista. Como ya la creamos arriba, vamos directo al schema.
PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f schema.sql
PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -f seed_distritos.sql
if [ -f "seeds/demo_snapshot.sql" ]; then
    # Filtrar meta-comandos \restrict/\unrestrict de pg_dump 17+
    grep -v '^\\' seeds/demo_snapshot.sql > /tmp/demo_clean.sql
    PGPASSWORD="$DB_PASS" psql -h localhost -U "$DB_USER" -d "$DB_NAME" \
        -c "SET session_replication_role = replica;" \
        -f /tmp/demo_clean.sql \
        -c "SET session_replication_role = origin;"
    rm /tmp/demo_clean.sql
    log "Snapshot demo aplicado"
else
    warn "seeds/demo_snapshot.sql no encontrado — BD queda vacía"
fi

# ---------- 6. systemd unit ----------
log "Paso 6/8: systemd unit $SERVICE_NAME"
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
sleep 2
if curl -fsS http://127.0.0.1:$UVICORN_PORT/api/health >/dev/null 2>&1; then
    log "Backend respondiendo en puerto $UVICORN_PORT"
else
    warn "Backend no respondió todavía. Ver logs: sudo journalctl -u $SERVICE_NAME -n 50"
fi

# ---------- 7. nginx site ----------
log "Paso 7/8: nginx site para $DOMAIN"
sudo mkdir -p "$FRONTEND_WEBROOT"
sudo chown ubuntu:ubuntu "$FRONTEND_WEBROOT"

# Placeholder index.html para que nginx no devuelva 404 antes del deploy del frontend
if [ ! -f "$FRONTEND_WEBROOT/index.html" ]; then
    cat > "$FRONTEND_WEBROOT/index.html" <<EOF
<!doctype html>
<html><body style="font-family:sans-serif;padding:40px">
<h1>Obras Cerca — backend OK</h1>
<p>API: <a href="/api/health">/api/health</a></p>
<p>Frontend aún no desplegado. Ejecuta deploy_frontend.ps1 desde tu PC.</p>
</body></html>
EOF
fi

sudo tee /etc/nginx/sites-available/obras-cerca > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;

    root $FRONTEND_WEBROOT;
    index index.html;

    # Angular SPA: cualquier ruta no-/api → index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # Backend FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:$UVICORN_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }

    # Gzip para Angular bundles
    gzip on;
    gzip_types text/css application/javascript application/json image/svg+xml;
    gzip_min_length 1024;
}
EOF

sudo ln -sf /etc/nginx/sites-available/obras-cerca /etc/nginx/sites-enabled/obras-cerca
sudo nginx -t
sudo systemctl reload nginx
log "Nginx recargado"

# ---------- 8. Resumen + siguientes pasos ----------
# IMDSv2 (token-based, default en EC2 modernas)
IMDS_TOKEN=$(curl -fsS -X PUT "http://169.254.169.254/latest/api/token" \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || echo "")
if [ -n "$IMDS_TOKEN" ]; then
    PUBLIC_IP=$(curl -fsS -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
        http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "")
fi
# Fallback IMDSv1 si IMDSv2 falla
if [ -z "${PUBLIC_IP:-}" ]; then
    PUBLIC_IP=$(curl -fsS http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null \
        || echo "(no IPv4 pública)")
fi

echo ""
echo "=============================================================="
echo "  SETUP COMPLETO"
echo "=============================================================="
echo "  Backend systemd:    $SERVICE_NAME"
echo "  Backend port:       $UVICORN_PORT (local solamente)"
echo "  Dominio HTTP:       http://$DOMAIN"
echo "  Frontend webroot:   $FRONTEND_WEBROOT"
echo "  Backend logs:       /var/log/obras-cerca-backend.log"
echo "  Ingesta logs:       /var/log/obras-cerca/*.log"
echo ""
echo "  IP pública EC2:     $PUBLIC_IP"
echo "  Password DB:        guardado en $DB_PASS_FILE"
echo ""
echo "  INGESTA_TOKEN para Terraform:"
echo "    $INGESTA_TOKEN"
echo "  Cópialo a infra/terraform.tfvars como  ingesta_token = \"...\""
echo ""
echo "=============================================================="
echo "  SIGUIENTES PASOS"
echo "=============================================================="
echo ""
echo "  1. En Hostinger (panel DNS de trinitylabs.app), agrega:"
echo "       Type:  A"
echo "       Name:  obrascerca"
echo "       Value: $PUBLIC_IP"
echo "       TTL:   3600"
echo ""
echo "  2. Espera 5-30 min y verifica:"
echo "       nslookup $DOMAIN"
echo ""
echo "  3. Cuando el DNS propague, corre HTTPS con certbot:"
echo "       sudo certbot --nginx -d $DOMAIN \\"
echo "         --non-interactive --agree-tos --email anderssongodoygarcia@gmail.com"
echo ""
echo "  4. Desde tu PC, sube el frontend Angular:"
echo "       infra/deploy_frontend.ps1"
echo ""
echo "  5. Desde tu PC, deploya Lambda + EventBridge con Terraform:"
echo "       cd infra && terraform init && terraform apply"
echo ""
echo "=============================================================="
