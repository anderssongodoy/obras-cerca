# Backend — Obras Cerca v2

FastAPI sobre PostgreSQL 17 (BD `obrascerca_v2`). MEF/Invierte.pe es el maestro; Infobras es satélite con verificación cruzada.

## Levantar local

```powershell
cd backend
pip install -r requirements.txt
cp .env.example .env

# 1) Crear BD vacia + schema
cd ..\db
python setup.py

# 2) (opcional) Poblar entidades del Peru desde PTE — ~30 seg
cd ..\backend
python scripts/01_descubrir_entidades.py

# 3) Mini-ingesta de demo: 5 CUIs conocidos con su cruce completo — ~1 min
python scripts/00_ingesta_demo.py

# 4) Generar senales con SQL deterministico
python scripts/06_generar_senales.py

# 5) Levantar API
python -m uvicorn app.main:app --reload --port 8000
# Docs: http://localhost:8000/docs
```

## Pipeline completo de ingesta (cuando quieras llenar TODA la BD)

```powershell
cd backend
python scripts/01_descubrir_entidades.py     # 2,300+ entidades del Peru
python scripts/02_mapear_idue.py             # scrape PTE -> IdUE SIAF
python scripts/03_descubrir_cuis.py          # GetEjecucion -> lista de CUIs
python scripts/04_enriquecer_cui.py          # 4 endpoints MEF por cada CUI
python scripts/05_verificar_nobr.py          # WFS + ficha + InformeControl
python scripts/06_generar_senales.py         # SQL deterministico
```

Cada script reanuda donde lo dejaste (idempotente).

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
