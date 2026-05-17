# Despliegue de Obras Cerca en AWS

Setup para producción en la EC2 existente `i-0df1bb4d5b2dd7978` (t3.micro, Ubuntu 24.04).

## Arquitectura

```
                                  ┌─ Frontend Angular estático
   Hostinger DNS                  │  /var/www/obras-cerca/
   obrascerca.trinitylabs.app ─┐  │
                               ↓  ↓
                          ┌────────────────────────────┐
                          │  EC2 i-0df1bb4d5b2dd7978   │
                          │                            │
                          │  nginx :443 (HTTPS)        │
                          │   ├─ / → frontend static   │
                          │   └─ /api/* → uvicorn      │
                          │                            │
                          │  uvicorn :8000 (FastAPI)   │
                          │   └─ /api/admin/ingesta…   │
                          │           ↑                │
                          │  Postgres 17 + pgvector    │
                          │   └─ obrascerca_v2         │
                          └─────────────┬──────────────┘
                                        │ POST con token
                          ┌─────────────┴──────────────┐
                          │  Lambda obras-cerca-trigger │
                          │  + EventBridge (2 AM Lima)  │
                          └─────────────────────────────┘
```

## Orden de ejecución

### Paso 1 — Subir aws_setup.sh a la EC2

Desde tu PC (PowerShell):

```powershell
$EC2_IP = "<IP_PUBLICA_DE_LA_EC2>"   # sacar con: aws ec2 describe-instances --instance-ids i-0df1bb4d5b2dd7978 --query "Reservations[0].Instances[0].PublicIpAddress" --output text
scp -i $HOME\.ssh\my_key_pair.pem infra\aws_setup.sh ubuntu@$EC2_IP`:/home/ubuntu/
```

### Paso 2 — Correr el setup en la EC2

```powershell
ssh -i $HOME\.ssh\my_key_pair.pem ubuntu@$EC2_IP
```

Dentro de la EC2:

```bash
chmod +x ~/aws_setup.sh
~/aws_setup.sh 2>&1 | tee ~/setup.log
```

Al final, el script imprime un `INGESTA_TOKEN` largo. **Cópialo** — lo usamos en el paso 5.

Tiempo estimado: 5-8 min (descarga e instala Postgres, clona repo, aplica schema).

### Paso 3 — DNS en Hostinger

En el panel de Hostinger → DNS Zone de `trinitylabs.app` → Add record:

| Campo | Valor |
|---|---|
| Type | A |
| Name | obrascerca |
| Points to | (la IP pública de la EC2 — la misma que usaste en Paso 1) |
| TTL | 3600 |

Verificar propagación desde tu PC:

```powershell
nslookup obrascerca.trinitylabs.app
# Debe devolver la IP de la EC2
```

Si no responde, espera 5-15 min y vuelve a probar.

### Paso 4 — HTTPS con certbot

De vuelta en la EC2 (ssh):

```bash
sudo certbot --nginx -d obrascerca.trinitylabs.app \
  --non-interactive --agree-tos --email anderssongodoygarcia@gmail.com
```

Certbot detecta el server block que creó `aws_setup.sh`, agrega los bloques HTTPS, y actualiza para que HTTP 80 redirija a 443. Auto-renew ya está configurado por el paquete certbot.

Probar:

```bash
curl https://obrascerca.trinitylabs.app/api/health
# Debe devolver {"status":"ok",...}
```

### Paso 5 — Deploy del frontend

En tu PC, edita `infra/deploy_frontend.ps1` y reemplaza `<EC2_PUBLIC_IP>` con la IP real.

Luego:

```powershell
.\infra\deploy_frontend.ps1
```

Esto hace `npm run build` local y sube el `dist/` por SCP. Tiempo: 2-3 min.

### Paso 6 — Lambda + EventBridge (Terraform)

```powershell
cd infra
copy terraform.tfvars.example terraform.tfvars
# Edita terraform.tfvars con notepad y pega el INGESTA_TOKEN del Paso 2

terraform init
terraform plan
terraform apply
```

Cuando pregunte `Enter a value:`, responde `yes`. Tiempo: 30 segundos.

### Paso 7 — Probar el cron manualmente

```powershell
# Invocar la Lambda a mano para verificar que todo el flujo funciona
aws lambda invoke `
  --function-name obras-cerca-trigger `
  --payload '{}' `
  --cli-binary-format raw-in-base64-out `
  $env:TEMP\lambda_out.json
type $env:TEMP\lambda_out.json
```

Debe imprimir `{"statusCode": 202, "body": ...}`. Eso significa:
1. Lambda corrió
2. Lambda llamó al backend con el token correcto
3. Backend aceptó y arrancó el pipeline en background

Para ver el progreso del pipeline en la EC2:

```bash
ssh -i $HOME\.ssh\my_key_pair.pem ubuntu@$EC2_IP
tail -f /var/log/obras-cerca/$(date +%Y-%m-%d).log
```

### Paso 8 — Verificación end-to-end

Desde tu PC, abre:

```
https://obrascerca.trinitylabs.app
https://obrascerca.trinitylabs.app/mapa
https://obrascerca.trinitylabs.app/api/stats
https://obrascerca.trinitylabs.app/api/health
```

Lo último debe imprimir `{"status":"ok","db":"obrascerca_v2",...}`.

---

## Costo mensual

| Recurso | Free Tier (12 meses) | Después |
|---|---|---|
| EC2 t3.micro (ya existente) | 750 hrs/mes | ~$8/mes |
| Lambda + EventBridge | Sí (1M invocaciones/mes) | $0 (gastamos ~30/mes) |
| CloudWatch Logs (14 días retención) | 5 GB free | ~$0.50/mes |
| Tráfico saliente | 100 GB/mes free | $0.09/GB |
| **Total estimado** | **$0** | **~$10/mes** |

## Mantenimiento

### Actualizar el código del backend

```bash
ssh -i $HOME\.ssh\my_key_pair.pem ubuntu@$EC2_IP
cd /opt/obras-cerca
git pull origin develop
cd backend
source .venv/bin/activate
pip install -q -r requirements.txt
sudo systemctl restart obras-cerca-backend
sudo journalctl -u obras-cerca-backend -n 30
```

### Actualizar el frontend

Desde tu PC:

```powershell
.\infra\deploy_frontend.ps1
```

### Cambiar el horario del cron

Edita `main.tf` línea con `schedule_expression`. Sintaxis cron AWS:
- `cron(0 7 * * ? *)` = 7 UTC = 2 AM Lima
- `cron(0 12 * * ? *)` = 12 UTC = 7 AM Lima
- `rate(6 hours)` = cada 6 horas

```powershell
terraform apply
```

### Borrar todo

```powershell
cd infra
terraform destroy
```

Esto elimina **solo la Lambda + EventBridge**. La EC2, BD y datos quedan intactos.

Para borrar la EC2 también (lo cual borraría el backend, frontend y BD), eso se hace manual desde la consola AWS o con `aws ec2 terminate-instances --instance-ids i-0df1bb4d5b2dd7978` — **no recomendado a menos que estés seguro**.

## Troubleshooting

### Backend no arranca

```bash
sudo journalctl -u obras-cerca-backend -n 100 --no-pager
sudo systemctl status obras-cerca-backend
```

Causas comunes:
- DB_DSN incorrecto → revisar `/opt/obras-cerca/backend/.env`
- Postgres no arrancó → `sudo systemctl status postgresql`
- pgvector no instalado → `sudo -u postgres psql -d obrascerca_v2 -c "\dx"`

### Lambda devuelve 401

El INGESTA_TOKEN en Lambda no coincide con el del backend. Verificar:

```powershell
# Token que la Lambda envía
aws lambda get-function-configuration --function-name obras-cerca-trigger --query "Environment.Variables.INGESTA_TOKEN" --output text
```

```bash
# Token que el backend espera
ssh ... 'cat /opt/obras-cerca/backend/.env | grep INGESTA'
```

Si no coinciden, ajustar el `terraform.tfvars` con el valor correcto y `terraform apply`.

### Nginx devuelve 502 Bad Gateway

El backend uvicorn no está escuchando en 8000.

```bash
sudo systemctl restart obras-cerca-backend
sudo ss -tlnp | grep :8000
```

### Certbot falla

Asegúrate de que el DNS ya propagó:

```bash
host obrascerca.trinitylabs.app
# Debe devolver la IP de tu EC2
```

Si recién agregaste el registro DNS, espera 10-15 min más.
