#!/usr/bin/env bash
# Mueve el backend de obrascerca.trinitylabs.app a api.obrascerca.trinitylabs.app.
# Limpia el server block y el cert SSL del dominio anterior.
#
# Uso:
#   chmod +x switch_to_api_subdomain.sh
#   ./switch_to_api_subdomain.sh

set -euo pipefail

OLD_DOMAIN="obrascerca.trinitylabs.app"
NEW_DOMAIN="api.obrascerca.trinitylabs.app"

log() { echo -e "\n\033[1;32m▶ $*\033[0m"; }
warn() { echo -e "\n\033[1;33m⚠ $*\033[0m"; }

# ---------- 1. Borrar server block viejo ----------
log "1/4: Quitar nginx site $OLD_DOMAIN"
sudo rm -f /etc/nginx/sites-enabled/obras-cerca
sudo rm -f /etc/nginx/sites-available/obras-cerca

# /var/www/obras-cerca lo dejamos (es solo un index.html, no estorba)

# ---------- 2. Borrar cert SSL viejo ----------
log "2/4: Quitar certificado SSL de $OLD_DOMAIN"
if sudo test -d "/etc/letsencrypt/live/$OLD_DOMAIN"; then
    sudo certbot delete --cert-name "$OLD_DOMAIN" --non-interactive || \
        warn "certbot delete falló, sigue"
else
    warn "Cert no existe (¿ya borrado?), sigue"
fi

# ---------- 3. Crear server block nuevo para api.obrascerca ----------
log "3/4: Crear nginx site $NEW_DOMAIN"
sudo tee /etc/nginx/sites-available/obras-cerca-api > /dev/null <<EOF
server {
    listen 80;
    server_name $NEW_DOMAIN;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/obras-cerca-api /etc/nginx/sites-enabled/obras-cerca-api
sudo nginx -t
sudo systemctl reload nginx
log "Nginx recargado"

# ---------- 3.5. Actualizar ALLOWED_ORIGINS en .env ----------
log "3.5/4: Actualizar ALLOWED_ORIGINS en .env"
sudo sed -i 's|^ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=*|' /opt/obras-cerca/backend/.env
sudo systemctl restart obras-cerca-backend
sleep 2
if curl -fsS http://127.0.0.1:8000/api/health >/dev/null; then
    log "Backend respondiendo en 8000"
else
    warn "Backend NO responde. Revisar: sudo journalctl -u obras-cerca-backend -n 30"
fi

# ---------- 4. Resumen + siguientes pasos ----------
echo ""
echo "=============================================================="
echo "  LISTO. SIGUIENTES PASOS MANUALES:"
echo "=============================================================="
echo ""
echo "  1. En Hostinger DNS de trinitylabs.app:"
echo "     - BORRAR registro A actual: obrascerca → 34.230.30.239"
echo "     - AGREGAR registro A nuevo:"
echo "         Type:  A"
echo "         Name:  api.obrascerca"
echo "         Value: 34.230.30.239"
echo "         TTL:   3600"
echo ""
echo "  2. Cuando propague (5-15 min, verifica con:"
echo "       nslookup api.obrascerca.trinitylabs.app    ),"
echo "     corre certbot para el nuevo dominio:"
echo ""
echo "       sudo certbot --nginx -d $NEW_DOMAIN \\"
echo "         --non-interactive --agree-tos --email anderssongodoygarcia@gmail.com"
echo ""
echo "  3. Verifica:"
echo "       curl https://$NEW_DOMAIN/api/health"
echo "     Debe devolver {\"status\":\"ok\",...}"
echo ""
echo "=============================================================="
