# 🏗️ ObrasCerca

> Plataforma cívica que muestra las obras públicas reales del Perú sobre un mapa interactivo, con data oficial de MEF, Infobras y Contraloría.

**Demo en vivo →** https://obrascerca.trinitylabs.app/

---

## 🧠 ¿Qué es?

ObrasCerca cruza tres fuentes oficiales del Estado peruano (Invierte.pe del MEF, Infobras de la Contraloría y SEACE) y georreferencia cada obra pública sobre un mapa. El ciudadano ve qué se está construyendo cerca suyo, quién es responsable, cuánto cuesta y en qué estado real está — siempre con cita a la fuente pública.

Pensada para **periodistas, vecinos y servidores públicos** que necesitan transparencia accionable, no PDFs perdidos.

---

## ✨ Funcionalidades

- 🗺️ **Mapa interactivo con geolocalización** — Ves las obras públicas en un radio configurable alrededor tuyo
- 🚦 **Señales de revisión** — El sistema detecta automáticamente obras paralizadas, proyectos desactivados por el MEF, saldos de obra y contratistas con sanciones
- 💬 **Chat RAG sobre informes de Contraloría** — Pregunta en lenguaje natural sobre cualquier obra y la IA responde citando el informe oficial, página por página
- 🔍 **Cruce de fuentes** — Cada obra muestra su data del MEF, Infobras y Contraloría en una sola ficha
- 🏢 **Ficha de contratista** — Histórico de obras adjudicadas, sanciones OECE, RUC verificado
- 📊 **Dashboard de métricas** — Total de obras, paralizadas, saldos, señales activas por distrito
- 🤖 **Ingesta diaria automatizada** — Pipeline que actualiza la data desde MEF/Infobras vía AWS Lambda + EventBridge

---

## 🧰 Stack

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI (Python 3.11+) |
| Frontend | Angular 21 (signals + resource) + Leaflet |
| Base de datos | PostgreSQL 17 + pgvector |
| IA — Embeddings | sentence-transformers (local) o HuggingFace Inference API |
| IA — LLM | MiniMax M2.7 o Anthropic Claude Haiku 4.5 |
| Ingesta | Python scripts (MEF / Infobras / SEACE scrapers) |
| Deploy backend | EC2 + Uvicorn + Nginx |
| Deploy frontend | CloudFront + S3 |
| Ingesta programada | AWS Lambda + EventBridge |

---

## 🚀 Correr localmente

### Requisitos

- [Python](https://www.python.org/) >= 3.11
- [Node.js](https://nodejs.org/) >= 20
- [PostgreSQL](https://www.postgresql.org/) 17 con extensión **pgvector**
- Una API key de [MiniMax](https://www.minimax.io/) **o** [Anthropic](https://www.anthropic.com/)

### Instalación

```bash
# Clonar el repo
git clone https://github.com/<tu-usuario>/obras-cerca.git
cd obras-cerca

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .venv\Scripts\activate     # Windows PowerShell
pip install -r requirements.txt
pip install -r requirements-rag.txt   # opcional, solo si querés embeddings locales

# Frontend
cd ../frontend
npm install
```

### Variables de entorno

Creá `backend/.env` a partir de `backend/.env.example`:

```env
# Base de datos
DB_DSN=host=localhost user=postgres password=123 dbname=obrascerca_v2

# CORS (separar por coma)
ALLOWED_ORIGINS=http://localhost:4200,http://localhost:5173
APP_ENV=local

# LLM (al menos una requerida)
LLM_PROVIDER=minimax              # o "anthropic" / "stub"
MINIMAX_API_KEY=
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M2.7
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-haiku-4-5-20251001

# Embeddings RAG
EMBED_PROVIDER=auto               # auto | local | hf_api
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
HF_TOKEN=                         # solo si EMBED_PROVIDER=hf_api

# Token compartido para la Lambda de ingesta diaria
INGESTA_TOKEN=
```

### Inicializar la base de datos

Requiere PostgreSQL corriendo con la extensión `pgvector` instalada. Este comando **elimina y recrea** la BD desde el snapshot demo:

```bash
cd db
python restore_demo.py
```

Después aplicá la migración del RAG (tablas `documento_chunk` y `chat_qa_cache`):

```bash
psql -h localhost -U postgres -d obrascerca_v2 -f db/migrations/001_pgvector_rag.sql
```

> Si pgvector no está instalado en tu Postgres local, podés levantar uno con Docker:
> ```bash
> docker run -d --name obrascerca-pg -e POSTGRES_PASSWORD=123 -p 5432:5432 pgvector/pgvector:pg17
> ```

### Levantar el proyecto

En dos terminales separadas:

```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

```bash
# Frontend
cd frontend
npm start
```

- Frontend: http://localhost:4200
- Backend: http://localhost:8000
- API docs (Swagger): http://localhost:8000/docs

---

## 🗂️ Estructura

```
obras-cerca/
├── backend/
│   ├── app/
│   │   ├── routers/          # Endpoints REST (obras, senales, chat, etc.)
│   │   ├── clients/          # Conectores a MEF, Infobras, PTE, SEACE
│   │   ├── config.py         # Variables de entorno
│   │   ├── db.py             # Pool psycopg + helpers
│   │   ├── llm.py            # MiniMax / Anthropic / stub
│   │   ├── rag.py            # Embeddings + retrieval
│   │   └── main.py           # FastAPI app
│   ├── scripts/              # Pipeline de ingesta (00-07)
│   ├── requirements.txt
│   └── requirements-rag.txt
├── frontend-v2/
│   └── src/app/
│       ├── core/             # Services, models, config (API)
│       ├── features/         # Mapa, señales, chat de obra
│       └── shared/           # UI kit (icon, icon-button, etc.)
├── db/
│   ├── schema.sql            # Estructura base
│   ├── seed_distritos.sql    # 50 distritos MVP + fuentes
│   ├── seeds/demo_snapshot.sql  # Data demo congelada
│   ├── migrations/           # pgvector_rag.sql, etc.
│   └── restore_demo.py       # Rebuild full de la BD
├── infra/                    # Lambda + EventBridge (ingesta diaria)
└── docs/
```

---

## 📡 API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/health` | Estado del servidor y de la BD |
| GET | `/api/stats` | KPIs globales (totales por tipo) |
| GET | `/api/distritos` | Lista de distritos MVP |
| GET | `/api/distritos/resumen` | Resumen agregado por distrito |
| GET | `/api/obras` | Listado de obras (filtros: ubigeo, lat/lon/radio, paralizadas, saldos, etc.) |
| GET | `/api/obras/{id}` | Ficha completa con cruce MEF/Infobras/Contraloría |
| GET | `/api/contratistas` | Listado de contratistas (búsqueda por RUC o razón social) |
| GET | `/api/contratistas/{ruc}` | Ficha de contratista con histórico |
| GET | `/api/senales` | Señales activas de revisión (filtros: tipo, ubigeo) |
| GET | `/api/obras/{id}/preguntar/health` | Disponibilidad del chat RAG para una obra |
| GET | `/api/obras/{id}/preguntar/sugerencias` | Preguntas sugeridas para esa obra |
| POST | `/api/obras/{id}/preguntar` | Chat RAG sobre los informes de Contraloría |
| POST | `/api/admin/ingesta-diaria` | Dispara la ingesta (requiere `X-Admin-Token`) |

Documentación interactiva en `/docs` (Swagger) y `/redoc`.

---

## 🏆 Hackathon

Proyecto desarrollado para **Hack@Latam 2026** (hack.indies.la · 15–17 mayo 2026).

- **Track**: Transparencia y Anticorrupción
- **Ámbito MVP**: Lima Metropolitana + Provincia Constitucional del Callao
- **Lenguaje**: Cívico y no acusatorio, siempre con cita a la fuente pública

---

*🏗️ Porque cada obra pública merece ser visible.*
