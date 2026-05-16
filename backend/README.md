# Obras Cerca — Backend API

FastAPI + PostgreSQL 17 (BD `obrascerca`). Sirve toda la lógica del MVP del MD maestro y se consume desde el frontend Angular.

## Levantar local

```powershell
cd backend
pip install -r requirements.txt
cp .env.example .env       # ajusta LLM_PROVIDER si quieres IA real
python -m uvicorn app.main:app --reload --port 8000
```

- API:   http://localhost:8000
- Docs:  http://localhost:8000/docs  (Swagger UI interactivo)
- ReDoc: http://localhost:8000/redoc

## Endpoints (20 en 9 routers)

### Meta y salud
| GET | Ruta | Descripción |
|---|---|---|
| | `/` | Info de la API |
| | `/api/health` | Conexión PG + versión |
| | `/api/stats` | KPIs globales + top distritos |
| | `/api/stats/series-paralizadas` | Paralizaciones por año (para gráfico tendencia) |

### Distritos (50 del MVP)
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/distritos` | Catálogo + centroides (lat/lon) |
| | `/api/distritos/resumen` | Resumen por distrito (paralizadas, montos) |
| | `/api/distritos/{ubigeo}` | Detalle |

### Obras
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/obras` | Listado con filtros |
| | `/api/obras/{id}` | Ficha + paralización + señales |
| | `/api/obras/{id}/exportar` | CSV de evidencia |
| | `/api/obras/{id}/explicacion` | Texto ciudadano (cache + IA o stub) |

Filtros de `/api/obras` (combinables):
- `ubigeo=150101` · `lat&lon&radio_m` (cerca de mí) · `paralizadas=true|false`
- `clasificacion=vigente|dudosa|zombie` · `contratista_ruc` · `entidad_id`
- `sector` · `estado` · `q` (búsqueda en nombre) · `limit/offset`

### Mapa (para el frontend del mapa interactivo)
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/mapa/heatmap` | Agregados por distrito para capas/heatmap |
| | `/api/mapa/bounds?nw_lat&nw_lon&se_lat&se_lon` | Obras dentro del bbox visible |

### Contratistas
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/contratistas` | Listado/búsqueda |
| | `/api/contratistas/sospechosos?min_pct=20` | Top concentración ≤8 UIT (12m) |
| | `/api/contratistas/{ruc}` | Ficha + obras + procedimientos + concentración |
| | `/api/contratistas/{ruc}/exportar` | CSV de obras del RUC |
| | `/api/contratistas/{ruc}/explicacion` | Texto ciudadano (IA o stub) |

### Señales de revisión (priorizadas)
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/senales` | Feed priorizado |

Query: `tipo=paralizacion|paralizacion_prolongada|concentracion_menores`, `ubigeo`, `solo_confirmadas`, `solo_vigentes` (default true, excluye zombies).

### Entidades, sectores, búsqueda
| GET | Ruta | Descripción |
|---|---|---|
| | `/api/entidades?q=` | Autocomplete |
| | `/api/sectores` | Agregado por sector en MVP |
| | `/api/search?q=` | Búsqueda transversal — obras + contratistas + entidades |

## Capa IA — explicación ciudadana

Implementa el principio del MD §6.5 y §12: **la IA solo redacta**, nunca decide ni clasifica.
Los hechos vienen de SQL, el LLM los convierte en oraciones para el vecino. Si la API IA cae, el endpoint devuelve un texto determinístico (`stub`) construido con los mismos hechos — la app nunca queda muda.

Configurable por `.env`:

```
LLM_PROVIDER=stub|minimax|anthropic
MINIMAX_API_KEY=...
MINIMAX_BASE_URL=https://api.minimax.io/v1
MINIMAX_MODEL=MiniMax-M2.7
ANTHROPIC_API_KEY=...
ANTHROPIC_MODEL=claude-haiku-4-5-20251001
```

MiniMax se invoca con el SDK oficial de Anthropic (compatible). Las explicaciones se cachean en `explicacion_obra` / `explicacion_contratista` para no quemar tokens.

## Estructura

```
backend/
├── requirements.txt
├── .env.example
├── README.md
├── app/
│   ├── main.py            # FastAPI app + CORS + lifespan
│   ├── config.py          # Settings desde .env
│   ├── db.py              # Pool psycopg3 (dict_row)
│   ├── llm.py             # Capa IA (stub/minimax/anthropic) con fallback
│   └── routers/
│       ├── health.py
│       ├── stats.py
│       ├── distritos.py
│       ├── obras.py
│       ├── contratistas.py
│       ├── senales.py
│       ├── entidades.py
│       ├── explicacion.py
│       ├── mapa.py
│       └── sospechosos.py
└── scripts/
    ├── cargar_centroides.py     # lat/lon centroides Lima Metro + Callao
    ├── geocoding_nominatim.py   # geocoding paralizadas (Nominatim, 1 req/s)
    └── ingest_ocds.py           # OCDS releases → procedimiento_seleccion
```

## Datos cargados al 2026-05-15

| Tabla | Filas | Fuente |
|---|---:|---|
| `distrito` (MVP) | 50 | INEI ubigeos + centroides hardcoded |
| `obra` | 11,183 | Infobras Obras Públicas 2026-05-15 |
| `obra_paralizacion` | 275 | Infobras (`Existe Paralización = SI`) |
| `entidad` | 442 | Infobras + Pentaho/CONOSCE |
| `contratista` | 110,261 | Infobras + Pentaho/CONOSCE |
| `orden_compra_servicio` | 164,319 | Pentaho/CONOSCE feb + mar 2026 (Lima/Callao, ≤8 UIT) |
| `procedimiento_seleccion` | 20 | OCDS Perú (prueba; falta paginar más) |
| `senal_revision` (activas) | 284 | 232 paralizacion + 43 prolongada + 9 concentracion_menores |
| `fuente_dato` | 1+ | Trazabilidad de cada ingesta |

## Clasificación honesta de paralizaciones

De las 275 paralizaciones que Infobras marca, la columna `clasificacion_paralizacion` distingue:

- **`vigente`** (45): paralización ≤ 2 años AND sin reactivación posterior → confiable hoy
- **`dudosa`** (48): contradicción interna (flag activo pero hay registros recientes)
- **`zombie`** (181): cementerio Infobras (paralización vieja Y nadie tocó el registro)

Además: **81 obras** tienen sello oficial de Contraloría dic-2025 (Anexo N°02).

El endpoint `/api/senales?solo_vigentes=true` por default oculta los zombies.

## Caso ancla verificable

`PROTEGE SERVICIOS S.A.` (RUC `20600182197`) concentra **27.13% del monto de compras menores ≤8 UIT del MINJUS** en los últimos 12 meses (82 órdenes, S/ 3.48M). Probar:

```
http://localhost:8000/api/contratistas/20600182197
http://localhost:8000/api/contratistas/20600182197/explicacion
http://localhost:8000/api/contratistas/sospechosos?min_pct=20
```

## Notas técnicas

- **Sin PostGIS**: la BD usa `latitud`/`longitud` NUMERIC y Haversine en SQL puro. Funciona para Lima sin extensión geoespacial.
- **CORS abierto en local** (APP_ENV=local), restrictivo en producción según `ALLOWED_ORIGINS`.
- **Pool conexiones**: 2 min / 10 max psycopg3. Suficiente para hackathon.
- **Streaming CSV** para exportar caso — no carga todo en memoria.
- **Cache LLM** en `explicacion_obra`/`explicacion_contratista` (key: obra_id/contratista_id + tipo). Pasar `?refresh=true` para regenerar.

## Gaps conocidos

- **Lat/Lon de las 11k obras** = centroide del distrito (geocoding individual pendiente). Filtro "cerca de mí" funciona pero sin precisión por obra.
- **`procedimiento_seleccion`** tiene solo 20 filas (prueba). Falta paginar más OCDS.
- **`orden_compra_servicio`** tiene 2 meses (feb+mar 2026). Idealmente 12 meses para concentración robusta.
- **Encoding mojibake** en algunos campos (`EducaciÃ“N` por doble-encode UTF-8). No bloquea API pero el front lo verá feo — limpiable con UPDATE SQL.
