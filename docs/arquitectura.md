# Arquitectura ObrasCerca

> Documento de referencia técnica para el equipo. Describe las capas, componentes, decisiones de diseño y estado del despliegue del MVP.

---

## Diagrama general

```
┌─────────────────────────────────────────────────────────────────┐
│                       FUENTES PÚBLICAS                          │
│                                                                 │
│  MEF / Infobras  │  Contraloría  │  Pentaho/CONOSCE  │  OCDS   │
└────────┬─────────┴──────┬────────┴────────┬──────────┴───┬─────┘
         │                │                 │              │
         └────────────────┴─────────────────┴──────────────┘
                                   │
                          ┌────────▼────────┐
                          │    SCRAPERS     │
                          │  Python +       │
                          │  Playwright     │
                          │  scripts 01–06  │
                          └────────┬────────┘
                                   │  XLSX / JSON
                          ┌────────▼────────┐
                          │   ETL / INGEST  │
                          │  pandas +       │
                          │  psycopg        │
                          │  db/*.py        │
                          └────────┬────────┘
                                   │
                     ┌─────────────▼───────────────┐
                     │       PostgreSQL 17          │
                     │   (Supabase en producción)   │
                     │                             │
                     │  13 tablas · 2 enums        │
                     │  obra / entidad /           │
                     │  contratista /              │
                     │  senal_revision / ...       │
                     │                             │
                     │  Haversine en SQL puro      │
                     │  (sin PostGIS en prod)      │
                     └─────────────┬───────────────┘
                                   │  psycopg pool
                     ┌─────────────▼───────────────┐
                     │      BACKEND FastAPI        │
                     │   (Railway / Fly.io)        │
                     │                             │
                     │  10 routers · 27 endpoints  │
                     │  CORS · async · Swagger UI  │
                     │                             │
                     │  ┌───────────────────────┐  │
                     │  │      CAPA IA (LLM)    │  │
                     │  │  stub → MiniMax →     │  │
                     │  │  Anthropic            │  │
                     │  │  (fallback determin.) │  │
                     │  └───────────────────────┘  │
                     └─────────────┬───────────────┘
                                   │  REST / JSON
                     ┌─────────────▼───────────────┐
                     │   FRONTEND Angular 18+      │
                     │        (Vercel)             │
                     │                             │
                     │  Mapa (Leaflet / MapLibre)  │
                     │  Ficha de obra              │
                     │  Filtros + búsqueda         │
                     │  Señales de revisión        │
                     │  Explicación IA ciudadana   │
                     └─────────────────────────────┘
```

---

## Capas y responsabilidades

| Capa | Tecnología | Ubicación en el repo | Responsabilidad |
|---|---|---|---|
| **Scrapers** | Python + Playwright | `scrapers/` | Descarga XLSX / JSON de las 5 fuentes oficiales |
| **ETL / Ingest** | pandas + psycopg | `db/*.py` | Limpieza, deduplicación, clasificación (vigente/dudosa/zombie), carga en BD |
| **Base de datos** | PostgreSQL 17 → Supabase | `db/schema.sql` | Fuente única de verdad; vistas `v_obra_ficha`, `v_resumen_distrito` |
| **API** | FastAPI + uvicorn | `backend/app/` | 27 endpoints, filtros Haversine, exportación CSV, caché de respuestas IA |
| **Capa IA** | stub / MiniMax / Anthropic | `backend/app/llm.py` | Traducción de datos a lenguaje ciudadano — **nunca clasifica ni decide** |
| **Frontend** | Angular 18 + Leaflet | *(pendiente)* | Mapa interactivo, ficha, señales, búsqueda por ubicación |
| **Deploy** | Vercel + Railway/Fly.io + Supabase | *(pendiente)* | Todo en tier gratuito |

---

## Modelo de datos (resumen)

```
distrito (50)
    │
    └── obra (11 183)
            ├── obra_paralizacion (275)
            ├── obra_avance (histórico futuro)
            └── procedimiento_seleccion (OCDS)

entidad (503) ──────────────────────────────────► obra
contratista (207 449) ──────────────────────────► obra
                      ──────────────────────────► orden_compra_servicio (631 759)

senal_revision (286 activas)
    ├── tipo: paralizacion
    ├── tipo: paralizacion_prolongada
    ├── tipo: concentracion_menores (≤ 8 UIT)
    ├── tipo: monto_atipico
    ├── tipo: sanciones_oece
    └── tipo: avance_fisico_estancado

fuente_dato          — trazabilidad de cada ingesta
inei_pobreza_distrito — enriquecimiento distrital (futuro)
```

### Vistas principales

| Vista | Uso |
|---|---|
| `v_obra_ficha` | Ficha completa de obra para el detalle del mapa |
| `v_obra_mvp` | Filtra solo las 50 distritos del ámbito Lima + Callao |
| `v_resumen_distrito` | Agregados por distrito para el sidebar / heatmap |

---

## API — Endpoints (27 en 10 routers)

> Swagger UI disponible en `http://localhost:8000/docs`

| Router | Prefijo | Endpoints destacados |
|---|---|---|
| health | `/api/health` | Liveness check |
| info | `/api/info` | `data-freshness`, `senales/resumen` |
| stats | `/api/stats` | KPIs globales, series de paralizadas |
| distritos | `/api/distritos` | Lista, resumen agregado, detalle por ubigeo |
| obras | `/api/obras` | 10 filtros (lat/lon/radio, paralizadas, sector…), detalle, exportar CSV |
| mapa | `/api/mapa` | `heatmap` (GeoJSON), `bounds` (bounding box) |
| contratistas | `/api/contratistas` | Detalle por RUC, explicación IA |
| sospechosos | `/api/contratistas/sospechosos` | Concentración ≤ 8 UIT con `min_pct` |
| senales | `/api/senales` | Lista priorizada por score |
| entidades | `/api/entidades` | Catálogo + sectores + búsqueda |

### Filtro estrella — "cerca de mí"

```
GET /api/obras?lat=-12.0959&lon=-77.0364&radio_m=1000
```

Utiliza Haversine en SQL puro (sin PostGIS) para devolver obras dentro del radio dado.

---

## Capa IA — diseño de fallback

```
petición ciudadana
        │
        ▼
  ¿caché en BD?  ──YES──► devolver texto cacheado
        │ NO
        ▼
  provider = stub
        │  falla → MiniMax (cupón hackathon)
        │           falla → Anthropic Claude
        │                    falla → texto determinístico
        ▼
  guardar en BD (caché)
        │
        ▼
  respuesta ciudadana
```

**Principio invariante:** la IA solo redacta. Los hechos (montos, fechas, avance, causal) vienen siempre del SQL. Si todos los LLM caen, el stub determinístico produce el mismo texto — la app nunca queda muda.

---

## Geocoding — estrategia degradada

| Nivel | Precisión | Volumen actual |
|---|---|---|
| Nominatim (dirección textual) | Alta (~50 m) | 37 obras paralizadas vigentes |
| Google Maps API | Alta | 198 obras (pendiente, requiere API key) |
| Centroide del distrito | Baja (~km) | 11 109 obras restantes |

El filtro Haversine funciona en todos los niveles; la precisión baja solo afecta obras sin geocoding fino.

---

## Clasificación de paralizaciones

Infobras reporta 275 paralizaciones. Sin filtro propio, mostrarlas todas es engañoso.

| Clasificación | Criterio | Cantidad |
|---|---|---|
| **vigente** | Flag activo · sin reactivación · ≤ 2 años | 45 |
| **dudosa** | Contradicción interna (flag + registros recientes) | 48 |
| **zombie** | > 2 años sin actividad — "cementerio Infobras" | 181 |

> El 66 % de las paralizaciones oficiales son zombies. Esta distinción no existe en ningún portal del Estado peruano.

---

## Despliegue (plan)

```
┌──────────────┐     ┌───────────────────┐     ┌─────────────────┐
│   Vercel     │────►│  Railway / Fly.io │────►│    Supabase     │
│  (Frontend)  │     │   (FastAPI API)   │     │  (PostgreSQL)   │
│  Angular SPA │     │   uvicorn · async │     │  free tier      │
│  CDN global  │     │   auto-deploy     │     │  500 MB         │
└──────────────┘     └───────────────────┘     └─────────────────┘
```

### Variables de entorno necesarias

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string (Supabase) |
| `MINIMAX_API_KEY` | Cupón hackathon MiniMax |
| `ANTHROPIC_API_KEY` | Fallback LLM |
| `APP_ENV` | `local` / `production` (controla CORS) |

---

## Estado actual y tareas pendientes

| Área | Estado | Notas |
|---|---|---|
| Scrapers (5 fuentes) | ✅ Completo | Playwright solo para descubrir URLs Pentaho |
| Schema PostgreSQL + ETLs | ✅ Completo | 13 tablas, 2 enums, 15 FKs |
| Datos cargados | ✅ Completo | 11 k obras + 631 k órdenes + 81 Contraloría |
| Backend FastAPI | ✅ Completo | 27 endpoints, smoke test 25/25 OK |
| Capa IA | ✅ Completo | stub + MiniMax + Anthropic + fallback |
| Frontend Angular | ⏳ Pendiente | **Bloqueante para score máximo** |
| Deploy | ⏳ Pendiente | Supabase + Railway/Fly.io + Vercel |
| Geocoding 198 paralizadas | ⏳ Pendiente | Requiere Google Maps API key |
| Paginar OCDS (50 páginas) | ⏳ Pendiente | ~1 000 procedimientos adicionales |
| Nuevas señales (`monto_atipico`, `avance_estancado`) | ⏳ Pendiente | 2–3 h de SQL |

---

## Estructura del repositorio

```
obras-cerca/
├── README.md                        ← Quick start + estado
├── docs/
│   ├── arquitectura.md              ← este archivo
│   ├── CONTEXTO_PROYECTO.md
│   ├── proyecto_maestro.md
│   ├── criterios_hackathon.md
│   ├── analisis_scraping.md
│   ├── estado_scrapers.md
│   └── data_distritos_lima.md
│
├── backend/                         ← FastAPI
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── llm.py                   ← capa IA con 3 providers + fallback
│   │   └── routers/                 ← 10 routers
│   └── scripts/
│       ├── smoke_test.py
│       ├── cargar_centroides.py
│       ├── geocoding_nominatim.py
│       └── ingest_ocds.py
│
├── db/                              ← Schema + ingestores
│   ├── schema.sql
│   ├── schema.dbml                  ← para dbdiagram.io
│   ├── seed_distritos.sql
│   ├── setup.py
│   ├── ingest_infobras.py
│   ├── ingest_pentaho_ordenes.py
│   ├── cargar_anexo_contraloria.py
│   ├── clasificar_paralizaciones.py
│   └── generar_senales_concentracion.py
│
└── scrapers/                        ← Scripts de descarga
    ├── common.py
    ├── 01_contraloria_paralizadas.py
    ├── 02_infobras_datasets.py
    ├── 03_infobras_ficha.py
    ├── 04_ocds_files_catalog.py
    ├── 05_ocds_releases.py
    └── 06_pentaho_ordenes_compra.py  ← URLs vía Playwright
```

---

## Referencias

- Swagger UI local: `http://localhost:8000/docs`
- Schema visual: pegar `db/schema.dbml` en [dbdiagram.io](https://dbdiagram.io)
- Smoke test: `cd backend && python scripts/smoke_test.py`
