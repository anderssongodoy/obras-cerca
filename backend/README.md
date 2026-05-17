# Backend — Obras Cerca v2

FastAPI sobre PostgreSQL 17 (BD `obrascerca_v2`). MEF/Invierte.pe es el maestro; Infobras es satélite con verificación cruzada.

## Setup rápido (recomendado para el equipo) — 2 minutos

Tu equipo ejecuta esto y tiene la **misma BD** que usé para hacer la demo (sin depender de que MEF/Infobras estén respondiendo igual hoy):

```powershell
cd backend
pip install -r requirements.txt
cp .env.example .env

# Crea BD obrascerca_v2 + aplica schema + carga el snapshot de demo
cd ..\db
python restore_demo.py

# Levanta la API
cd ..\backend
python -m uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

El restore deja: **50 distritos · 2,301 entidades · 7 proyectos MEF · 8 obras (con saldos JNJ) · 15 informes Contraloría · 36 contratos SEACE · 5 señales activas**.

> El snapshot vive en `db/seeds/demo_snapshot.sql` (908 KB, generado con `pg_dump --data-only --column-inserts`). Versionado en git para reproducibilidad.

## Setup desde cero (si quieres regenerar la BD llamando a las APIs reales)

Usa esto solo si quieres ver el flujo de ingesta funcionando. Tarda más y los datos cambian (porque MEF puede responder distinto):

```powershell
cd ..\db
python setup.py                              # BD vacía + schema

cd ..\backend
python scripts/01_descubrir_entidades.py     # 2,300+ entidades del Perú
python scripts/00_ingesta_demo.py            # 5 CUIs conocidos con su cruce completo
python scripts/06_generar_senales.py         # SQL determinístico
```

## Pipeline completo de ingesta (cuando quieras llenar TODA la BD)

```powershell
cd backend
python scripts/01_descubrir_entidades.py     # 2,300+ entidades del Perú
python scripts/02_mapear_idue.py             # scrape PTE -> IdUE SIAF
python scripts/03_descubrir_cuis.py          # GetEjecucion -> lista de CUIs
python scripts/04_enriquecer_cui.py          # 4 endpoints MEF por cada CUI
python scripts/05_verificar_nobr.py          # WFS + ficha + InformeControl
python scripts/06_generar_senales.py         # SQL determinístico
```

Cada script reanuda donde lo dejaste (idempotente).

## Regenerar el snapshot (cuando tu BD esté actualizada y quieras compartirla)

```powershell
# Asume que PostgreSQL está en C:\Program Files\PostgreSQL\17\bin
$env:PGPASSWORD = "123"
& "C:\Program Files\PostgreSQL\17\bin\pg_dump" -U postgres -h localhost -d obrascerca_v2 `
  --data-only --column-inserts --no-owner --no-privileges `
  --exclude-table=fuente_dato --exclude-table=distrito `
  --exclude-table=proyecto_avance_mensual --exclude-table=explicacion_ia `
  -f db\seeds\demo_snapshot.sql
```

## Estructura

```
backend/
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py           FastAPI + lifespan
│   ├── config.py         settings desde .env
│   ├── db.py             pool psycopg3
│   ├── llm.py            capa IA (stub/minimax/anthropic) con fallback
│   ├── clients/
│   │   ├── common.py     HTTP session compartida
│   │   ├── mef.py        endpoints Invierte.pe / SIAF / SEACE
│   │   ├── infobras.py   WFS + ficha + InformeControl
│   │   └── pte.py        catalogo PTE de entidades
│   └── routers/
│       ├── health.py     /api/health, /api/stats
│       ├── distritos.py
│       ├── obras.py      listado, ficha, /verificar (live), /explicacion (IA), /exportar
│       ├── contratistas.py
│       └── senales.py
└── scripts/
    ├── 00_ingesta_demo.py        mini-ingesta para empezar
    ├── 01_descubrir_entidades.py
    ├── 02_mapear_idue.py
    ├── 03_descubrir_cuis.py
    ├── 04_enriquecer_cui.py
    ├── 05_verificar_nobr.py
    └── 06_generar_senales.py
```

## Endpoints clave

```
GET /api/health
GET /api/stats
GET /api/distritos
GET /api/distritos/resumen
GET /api/obras?paralizadas_wfs=true&ubigeo=150101
GET /api/obras/{id}                # ficha con saldos + procedimientos + paralizaciones + informes + senales
GET /api/obras/{id}/verificar      # cruce LIVE en tiempo real contra MEF/Infobras/Contraloria
GET /api/obras/{id}/explicacion    # capa IA (stub/minimax/anthropic)
GET /api/obras/{id}/exportar       # CSV con toda la evidencia
GET /api/contratistas/{ruc}
GET /api/contratistas/sospechosos/top
GET /api/senales?tipo=paralizacion_real
```

Docs interactivas: **http://localhost:8000/docs**

## Activar capa IA real

Tu cupón de MiniMax o Anthropic en `.env`:

```
LLM_PROVIDER=minimax
MINIMAX_API_KEY=...
```

Si la API cae, devuelve texto stub determinístico. La app **nunca** queda muda.
