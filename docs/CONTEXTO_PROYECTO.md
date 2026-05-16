# Obras Cerca

> Plataforma ciudadana que integra Infobras, OECE, Contraloría e INEI para que cualquier persona en el Perú pueda revisar las obras públicas cerca de su ubicación, su estado real y los contratistas detrás. **hack@latam 2026 — track Transparency & Corruption.**

**Ámbito MVP:** Lima Metropolitana (43 distritos) + Provincia Constitucional del Callao (7 distritos) = **50 distritos**.

---

## Estado al 2026-05-15

| Área | Estado |
|---|---|
| Análisis fuentes + scrapers | ✅ Completo (5 fuentes, 1 vía Playwright) |
| Schema PostgreSQL + ETLs | ✅ 13 tablas, 2 enums, 15 FKs reales |
| Datos cargados | ✅ 11k obras + 631k órdenes ≤8 UIT + 81 confirmadas Contraloría |
| Backend FastAPI | ✅ 27 endpoints en 10 routers, smoke test 25/25 OK |
| Capa IA (explicación ciudadana) | ✅ stub + MiniMax + Anthropic — fallback determinístico |
| Frontend Angular | ⏳ Pendiente |
| Deploy | ⏳ Pendiente (planeado Vercel + Supabase) |

---

## Quick start (clonar y levantar local)

Requisitos: **Python 3.12** y **PostgreSQL 17** local (usuario `postgres`, password `123`, puerto `5432`).

```powershell
# 1. Setup BD
cd db
pip install psycopg psycopg_pool python-dotenv pandas openpyxl requests anthropic
python setup.py                              # crea BD + schema + 50 distritos

# 2. Ingestar datos (necesitas los XLSX en scrapers/data/raw/ — bajarlos primero)
cd ..\scrapers
python 01_contraloria_paralizadas.py         # 3 XLSX Contraloría
python 02_infobras_datasets.py               # 4 XLSX Infobras (uno pesa 63 MB)
python 06_pentaho_ordenes_compra.py --meses 6  # Pentaho órdenes ≤8 UIT (300+ MB)

cd ..\db
python ingest_infobras.py                    # 11k obras MVP
python cargar_anexo_contraloria.py           # marca 81 con sello oficial
python clasificar_paralizaciones.py          # vigente/dudosa/zombie
python ingest_pentaho_ordenes.py             # 600k+ órdenes
python generar_senales_concentracion.py      # señales ≤8 UIT

# 3. Levantar API
cd ..\backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# Docs interactivas en http://localhost:8000/docs
```

Smoke test (prueba 25 endpoints):
```powershell
cd backend
python scripts/smoke_test.py
```

---

## Casos ancla verificables (data al 2026-05-15)

Datos reales en la BD, no hipótesis. Se pueden reproducir con SQL directo o con la API.

### 🎯 Paralización con monto masivo
**INFOBRAS 536317** — *"Cinco pasos a desnivel"* en San Juan de Lurigancho
- **S/ 489 M** · 11.31% avance · paralizada hace 103 días · causal "Conflictos sociales"
- Ejecutor: Fondo Metropolitano de Inversiones (Invermet)
- 1.1 M habitantes potencialmente afectados

### 🎯 Doble validación (única con sello Contraloría dic-2025)
**INFOBRAS 504340** — *"Movilidad urbana Av Santa Rosa"* en Chorrillos
- S/ 3.16 M · 79.43% avance · paralizada hace 103 días
- Confirmada por Contraloría dic-2025 ✅

### 🎯 Absurdo institucional
**INFOBRAS 42593** — *"Mejoramiento JNJ"* en San Isidro
- S/ 32 M · **99.86% avance** ← paralizada al milímetro del 100%
- Ejecutor: Junta Nacional de Justicia
- Causal: Resolución de contrato

### 🎯 Concentración de contratista
**PROTEGE SERVICIOS S.A.** (RUC `20600182197`)
- **195 órdenes ≤8 UIT** del MINJUS en últimos 12 meses
- **S/ 8.26 M** · **25.07%** del monto total de compras menores del ministerio
- Fórmula auditable visible en la señal de revisión

Verificar via API:
```
http://localhost:8000/api/obras?paralizadas=true&clasificacion=vigente&limit=20
http://localhost:8000/api/contratistas/20600182197
http://localhost:8000/api/contratistas/sospechosos?min_pct=20
```

---

## Datos en BD

| Tabla | Filas | Fuente |
|---|---:|---|
| `distrito` (MVP) | 50 | INEI ubigeos + centroides hardcoded |
| `obra` | 11,183 | Infobras Obras Públicas 2026-05-15 |
| `obra_paralizacion` | 275 | Infobras (45 vigentes, 48 dudosas, 181 zombies) |
| `entidad` | 503 | Infobras + Pentaho/CONOSCE |
| `contratista` | 207,449 | Infobras + Pentaho/CONOSCE |
| `orden_compra_servicio` | 631,759 | Pentaho/CONOSCE oct 2025 – abr 2026 (Lima/Callao, ≤8 UIT) |
| `procedimiento_seleccion` | 20 | OCDS Perú (prueba, falta paginar más) |
| `senal_revision` (activas) | 286 | 232 paralización + 43 prolongada + 11 concentración ≤8 UIT |
| Geocoding fino | 37 | Nominatim (paralizadas vigentes); resto centroide del distrito |

---

## Endpoints API (27 en 10 routers)

`http://localhost:8000/docs` para explorar Swagger UI.

| Categoría | Ruta principal |
|---|---|
| Meta | `/`, `/api/health`, `/api/info/data-freshness`, `/api/info/senales/resumen` |
| KPIs | `/api/stats`, `/api/stats/series-paralizadas` |
| Distritos | `/api/distritos`, `/api/distritos/resumen`, `/api/distritos/{ubigeo}` |
| Obras | `/api/obras` (10 filtros), `/api/obras/{id}`, `/api/obras/{id}/exportar`, `/api/obras/{id}/explicacion` |
| Mapa | `/api/mapa/heatmap`, `/api/mapa/bounds` (bounding box) |
| Contratistas | `/api/contratistas`, `/api/contratistas/sospechosos`, `/api/contratistas/{ruc}`, `/api/contratistas/{ruc}/explicacion` |
| Señales | `/api/senales` (priorizado) |
| Catálogos | `/api/entidades`, `/api/sectores`, `/api/search` |

**Filtro estrella:** `/api/obras?lat=-12.0959&lon=-77.0364&radio_m=1000` → "obras cerca de mí" con Haversine.

---

## Stack técnico (decisiones tomadas)

- **Frontend:** Angular 18+ (el equipo lo domina; velocidad > novedad — no pivotamos a Next.js + v0)
- **Mapa:** Leaflet/MapLibre + OpenStreetMap
- **Backend:** FastAPI Python (10x más rápido de levantar que Express en hackathon, docs Swagger gratis)
- **BD:** PostgreSQL 17 (local hoy; deploy a Supabase free tier)
- **PostGIS:** NO usamos (la extensión no está disponible local) — usamos `latitud`/`longitud` NUMERIC + Haversine en SQL puro
- **ETL:** Python + pandas + openpyxl. Polars descartado (overkill en 72h)
- **Capa IA:** wrapper local con providers `stub` / `minimax` (cupón hackathon) / `anthropic`. Caché en BD. Si el LLM cae, el endpoint devuelve texto determinístico — la app nunca queda muda.
- **Scraping:** `requests` para todo + `playwright-cli` solo para descubrir URLs de Pentaho/CONOSCE

---

## Decisiones honestas que hacen la diferencia

### 1. Clasificación vigente/dudosa/zombie
Infobras tiene problema de calidad: muchas obras "paralizadas" llevan años sin que la entidad toque el registro. Sin filtro mostrar 275 paralizaciones es engañoso. Nuestra clasificación:

- **`vigente`** (45): paralización ≤ 2 años AND sin reactivación → confiable HOY
- **`dudosa`** (48): contradicción interna (flag activo pero hay registros recientes)
- **`zombie`** (181): cementerio Infobras

Ningún portal del Estado hace esta distinción. **El 66% de las paralizaciones oficiales son zombies** — dato que descubrimos y vendemos como feature.

### 2. Cruce con Contraloría dic-2025
81 obras tienen doble validación oficial (Infobras + Anexo N°02 del informe Contraloría). Estas son las que firmaríamos sin duda.

### 3. IA solo redacta, nunca decide
La capa LLM toma hechos del SQL y los traduce a lenguaje ciudadano. **No clasifica, no prioriza, no inventa.** Si MiniMax/Anthropic caen, el stub determinístico produce el mismo texto. Diferencia clave para el criterio "Complejidad técnica" — no es solo prompting.

### 4. Concentración ≤8 UIT con fórmula auditable
Cada señal lleva su fórmula visible: `pct_monto = 100 × Σmonto(RUC,entidad,12m) / Σmonto(entidad,12m)`. El usuario puede reproducir el cálculo y exportar la evidencia.

---

## Limitaciones conocidas (decirlas en el pitch antes que el jurado las descubra)

1. **No verificamos contra portales municipales (PTE de cada entidad).** Infobras es lo que la entidad reporta. La municipalidad puede tener data divergente en su Portal de Transparencia. Mitigación: cruzamos con Contraloría dic-2025 como auditoría independiente. Roadmap v2: scrapear los 50 PTE.
2. **Lat/lon de las 11k obras** = centroide del distrito (no precisión por dirección). Solo 37 paralizadas tienen geocoding Nominatim fino. Filtro "cerca de mí" funciona pero sin precisión exacta por obra.
3. **OCDS** está parcialmente cargado (20 procedimientos de prueba). Falta paginar para tener cruce robusto con contratistas.
4. **6 obras paralizadas sin dirección textual** (entidad no la reportó) — quedan a nivel distrito.
5. **0 obras del Callao** en Infobras bajo `(CALLAO, CALLAO)`. Las obras del Callao podrían estar bajo otra clasificación; investigación pendiente.

---

## Criterios del hackathon (meta permanente)

Ver `criterios_hackathon.md` para el detalle. Resumen:

| Criterio | Peso | Score hoy backend solo | Techo con frontend + deploy |
|---|---:|---:|---:|
| Impacto social | 30% | 24 | 28 |
| Moonshot | 20% | 14 | 17 |
| Complejidad técnica | 20% | 19 | 19 |
| Factor de novedad | 15% | 11 | 13 |
| Listo para usar | 15% | 6 | 13 |
| **Total** | | **74** | **90** |

**Bloqueante #1 para top score:** deploy + frontend.

---

## Documentación completa

Archivos MD del repo (en orden de lectura sugerido para un compañero nuevo):

| Archivo | Para qué sirve |
|---|---|
| `README.md` (este) | Quick start + estado |
| `obras_cerca_proyecto_maestro.md` | Documento maestro: visión, MVP, fuentes, principios |
| `criterios_hackathon.md` | Rúbrica del jurado + plan de subida |
| `analisis_scraping.md` | Cómo se scrapearon las 5 fuentes (con evidencia técnica) |
| `estado_scrapers.md` | Estado scripts + qué Playwright resolvió |
| `data_distritos_lima.md` | Análisis preliminar 3 distritos piloto |
| `backend/README.md` | API completa: endpoints + filtros + ejemplos |
| `db/schema.dbml` | Diagrama de BD (pegar en dbdiagram.io) |

---

## Estructura del repositorio

```
Investigación/
├── README.md                            ← este archivo
├── obras_cerca_proyecto_maestro.md      ← documento maestro original
├── criterios_hackathon.md               ← rúbrica del jurado
├── analisis_scraping.md                 ← análisis técnico de cada fuente
├── estado_scrapers.md                   ← estado scripts
├── data_distritos_lima.md               ← análisis de 3 distritos piloto
│
├── backend/                             ← FastAPI API
│   ├── README.md
│   ├── requirements.txt
│   ├── .env.example
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db.py
│   │   ├── llm.py                       ← capa IA con 3 providers
│   │   └── routers/                     ← 10 routers
│   └── scripts/
│       ├── smoke_test.py                ← prueba 25 endpoints
│       ├── cargar_centroides.py
│       ├── geocoding_nominatim.py
│       └── ingest_ocds.py
│
├── db/                                  ← Schema + ingestores
│   ├── schema.sql
│   ├── schema.dbml                      ← para dbdiagram.io
│   ├── seed_distritos.sql               ← 50 ubigeos
│   ├── setup.py
│   ├── ingest_infobras.py
│   ├── ingest_pentaho_ordenes.py
│   ├── cargar_anexo_contraloria.py
│   ├── clasificar_paralizaciones.py
│   └── generar_senales_concentracion.py
│
└── scrapers/                            ← Scripts de descarga
    ├── README.md
    ├── common.py                        ← UA, retries, stream-download
    ├── 01_contraloria_paralizadas.py
    ├── 02_infobras_datasets.py
    ├── 03_infobras_ficha.py
    ├── 04_ocds_files_catalog.py
    ├── 05_ocds_releases.py
    ├── 06_pentaho_ordenes_compra.py     ← URLs descubiertas vía Playwright
    └── data/                            ← XLSX/JSON crudos (NO subir al repo)
```

---

## Cómo contribuir / dividir el trabajo restante

| Tarea | Tiempo aprox | Pre-requisitos |
|---|---|---|
| Frontend Angular: mapa + ficha + filtros | 8-12 h | Backend corriendo, leer `backend/README.md` |
| Deploy Postgres a Supabase + backend a Fly.io o Railway | 2-3 h | Cuenta gratis Supabase |
| Activar capa IA con MiniMax cupón | 5 min | `MINIMAX_API_KEY` en `backend/.env` |
| Paginar más OCDS (50 páginas → ~1000 procedimientos) | 1 h | Red estable |
| Geocoding restante 198 paralizadas con Google API | 1 h | API key Google |
| Mejorar señales: agregar `monto_atipico` y `avance_estancado` | 2-3 h | SQL skills |
| Pitch deck (Faces cupón) | 2 h | Casos ancla decididos |

---

## Cupones de la hackathon — recomendación de uso

| Cupón | Para Obras Cerca | Acción |
|---|---|---|
| **Context7** `HACK_LATAM` | ✅ Docs FastAPI/Angular/Postgres al vuelo | Canjear ya |
| **MiniMax** | ✅ Capa IA ya integrada (`backend/app/llm.py`) | API key en `.env` |
| **v0** `HACK-INDIES-V0` | 🟡 Solo si pivotamos a Next.js (no recomendado) | Pasar |
| **Faces** `HACKINDIES` | 🟢 Útil para diapositivas del pitch | Día del pitch |
| Struere, Make, Zavu, Monologue | ❌ No aplican | Pasar |

---

## Contacto

Equipo Obras Cerca — hack@latam 2026, track Transparency & Corruption.
