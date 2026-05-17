# Build del frontend Angular en tu PC y subida vía SCP al EC2.
#
# Uso (desde la raíz del proyecto):
#   .\infra\deploy_frontend.ps1
#
# Pre-requisitos:
#   - Node + npm instalados (verifica con: node --version, npm --version)
#   - SSH key en $HOME\.ssh\my_key_pair.pem
#   - El frontend buildea sin errores (verifica con: cd frontend; npm run build)
#
# Lo que hace:
#   1. cd frontend
#   2. npm install (si node_modules no existe)
#   3. npm run build -- --configuration=production
#   4. scp del dist/frontend/browser/* al EC2
#   5. recarga nginx (no es necesario porque es estático, pero limpia cache)

$ErrorActionPreference = "Stop"

# ---------- Parámetros ----------
$EC2_HOST   = "ubuntu@<EC2_PUBLIC_IP>"    # ← REEMPLAZA con la IP pública o usa Elastic IP
$KEY_PATH   = "$HOME\.ssh\my_key_pair.pem"
$REMOTE_DIR = "/var/www/obras-cerca"
$FRONTEND_DIR = "frontend"
$BUILD_OUTPUT = "frontend\dist\frontend\browser"

# ---------- Verificaciones ----------
if (-not (Test-Path $KEY_PATH)) {
    Write-Host "✗ SSH key no encontrada: $KEY_PATH" -ForegroundColor Red
    exit 1
}
if ($EC2_HOST -like "*<EC2_PUBLIC_IP>*") {
    Write-Host "✗ Editar este script y reemplazar <EC2_PUBLIC_IP> con la IP real" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $FRONTEND_DIR)) {
    Write-Host "✗ Carpeta '$FRONTEND_DIR' no existe. Corre desde la raíz del proyecto." -ForegroundColor Red
    exit 1
}

# ---------- 1. Build local ----------
Write-Host "`n▶ Building Angular (production)..." -ForegroundColor Green
Push-Location $FRONTEND_DIR
try {
    if (-not (Test-Path "node_modules")) {
        npm install
    }
    npm run build -- --configuration=production
    if ($LASTEXITCODE -ne 0) { throw "Build falló" }
} finally {
    Pop-Location
}

if (-not (Test-Path $BUILD_OUTPUT)) {
    Write-Host "✗ Build output no existe en $BUILD_OUTPUT" -ForegroundColor Red
    exit 1
}

# Verificar tamaño del bundle
$bundleSize = (Get-ChildItem -Path $BUILD_OUTPUT -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "▶ Bundle: $([math]::Round($bundleSize, 2)) MB" -ForegroundColor Green

# ---------- 2. Upload con SCP ----------
Write-Host "`n▶ Subiendo a $EC2_HOST`:$REMOTE_DIR ..." -ForegroundColor Green

# Limpia el destino primero (preserva el directorio, borra el contenido)
ssh -i $KEY_PATH $EC2_HOST "find $REMOTE_DIR -mindepth 1 -delete"

# Sube todo el contenido del build
scp -i $KEY_PATH -r "$BUILD_OUTPUT\*" "$EC2_HOST`:$REMOTE_DIR/"

# Permisos correctos
ssh -i $KEY_PATH $EC2_HOST "sudo chown -R www-data:www-data $REMOTE_DIR && sudo chmod -R 755 $REMOTE_DIR"

# Limpiar cache del navegador del cliente forzando que nginx mande no-cache para index.html
# (ya viene en el config nginx por defecto, pero por si acaso)

Write-Host "`n✓ Frontend desplegado" -ForegroundColor Green
Write-Host "  Abre: https://obrascerca.trinitylabs.app" -ForegroundColor Cyan
