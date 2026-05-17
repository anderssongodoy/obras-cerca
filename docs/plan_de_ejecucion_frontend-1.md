# Plan de Ejecución Frontend v1 — ObrasCerca

**Origen del diseño**: `demo/index.html` (mapa Leaflet del Callao, paleta civic warm, panel de obra con story flow, drawer de filtros, marcadores custom).
**Destino**: `frontend-v2/` (Angular 21 standalone, signals, SCSS + Tailwind v4, sin NgModules).
**Backend**: FastAPI ya levantado en `http://localhost:8000/docs` con endpoints `/api/obras`, `/api/distritos`, `/api/contratistas`, `/api/senales`. **No se modifica en este plan** — los campos del demo que la API no expone (`conSenal`, `fuente`, `estado` de 5 buckets) se derivan en el front. Los gaps quedan registrados en Fase 7 para una iteración futura.

Este documento está pensado para ejecutarse por fases. **Cada fase es un prompt cerrado**: invocala diciendo "ejecutá Fase N" y se respetan los criterios de salida antes de pasar a la siguiente. Las skills recomendadas se invocan con el `Skill` tool.

---

## Mapeo demo ↔ API (lectura obligatoria antes de empezar)

| Campo demo | Campo API (`v_obra_mvp`) | Estado | Acción |
|---|---|---|---|
| `id` | `id` | OK | usar directo |
| `titulo` | `nombre_obra` ?? `nombre_inversion` | OK | coalesce en service |
| `estado` (5 buckets: `en_ejecucion`/`en_licitacion`/`verificada`/`informativo`/`senal`) | combinación de `estado_proyecto_mef` + `estado_obra_wfs` + presencia en `senal_revision` | derivable | derivar en **front** vía `estado-catalog.ts` (Fase 2). Sin tocar backend. |
| `monto` (string `"S/ 2.85 M"`) | `mto_viable` / `costo_actualizado` / `monto_contrato` (numeric) | OK | formatear con `Intl.NumberFormat('es-PE')` en front |
| `entidad` | `entidad_nombre` | OK | — |
| `distrito` | `distrito_nombre` | OK | — |
| `coords [lat,lon]` | `latitud`, `longitud` | OK | tupla `[lat, lon]` |
| `conSenal` (boolean) | NO viene en listado de `/api/obras`; sólo en `/api/obras/{id}` y en `/api/senales` | derivable | hacer **un fetch a `/api/senales`** y construir un `Set<obra_id>` en `ObrasService`; el flag se computa en front |
| `fuente` (`INFObras`/`SEACE`/`Ciudadanos`) | derivable: si tiene `nobr_id`→INFObras, si tiene procedimiento (señal `tipo=ciudadana`)→Ciudadanos, resto→SEACE/INFObras según contexto | derivable | función `derivarFuente(obra)` en `estado-catalog.ts` |
| `tramos[]` (polylines de avenidas) | NO existe | mock | hardcodear 4-6 tramos del Callao en `assets/mock/tramos.callao.json` (sin backend) |

**Endpoints útiles ya existentes**:
- `GET /api/obras?ubigeo=&lat=&lon=&radio_m=&q=&paralizadas_wfs=&inactivas_mef=&con_saldos=&limit=&offset=` → listado paginado con `total`
- `GET /api/obras/{id}` → ficha completa (saldos, procedimientos, paralizaciones, informes, señales)
- `GET /api/obras/{id}/verificar` → cruce LIVE de fuentes
- `GET /api/obras/{id}/explicacion` → texto IA cached
- `GET /api/distritos` y `/api/distritos/resumen`
- `GET /api/senales`

---

## Fase 0 — Inicialización SDD y contexto del proyecto

**Objetivo**: que SDD conozca el stack (Angular 21, vitest, SCSS, signals, sin specs según convención `al-orbita-gestor`) y se persista en engram.

**Skills a invocar**:
- `Skill(skill: "sdd-init")` — detecta stack, cachea testing capabilities, marca strict TDD si aplica.

**Acciones**:
1. Correr `sdd-init` apuntando a `frontend-v2/`.
2. Verificar que el contexto `sdd-init/obras-cerca` quede guardado en engram con: stack Angular 21, sin specs por convención, prefix `app`, SCSS.
3. Confirmar engram project: **`obras-cerca`** (consistente con `mem_current_project`).

**Criterio de salida**:
- `mem_search("sdd-init/obras-cerca")` devuelve resultado.
- Tabla `Model Assignments` cacheada para esta sesión.

---

## Fase 1 — Setup de librerías y design system base

**Objetivo**: dejar `frontend-v2` listo para crear componentes, con Tailwind v4 + tokens SCSS + Leaflet + tipografías sin que falte nada.

**Skills a invocar**:
- `Skill(skill: "angular-tailwind")` — guía oficial Tailwind v4 + Angular.
- `Skill(skill: "angular-developer")` — para `provideHttpClient` con `withFetch`, signals, OnPush.
- `Skill(skill: "context7")` con `tailwindcss` y `leaflet` si hay dudas de API.

**Librerías a instalar (`frontend-v2/`)**:
```bash
npm i leaflet @types/leaflet leaflet.markercluster @types/leaflet.markercluster @angular/cdk
npm i @fontsource/inter @fontsource/roboto-condensed
npm i -D tailwindcss @tailwindcss/postcss postcss
```

**Archivos a crear/editar**:
- `postcss.config.js` con `@tailwindcss/postcss`.
- `src/styles.scss` → sólo `@use` de los partials + `@import "tailwindcss"` (v4 sintaxis).
- `src/styles/_tokens.scss` → migrar **literal** las variables del `:root` del demo (líneas 26-53 de `demo/index.html`): colores OKLCH (`--ink`, `--ink-2`, `--surface`, `--surface-raised`, `--bg-mute`, etc.), estados (`--orange`, `--red`, `--green`, `--blue`, `--yellow` y sus `-soft`), sombras (`--shadow-card`, `--shadow-elev`, `--shadow-marker`, `--shadow-btn`).
- `src/styles/_reset.scss` → `box-sizing: border-box`, `.sr-only`, focus-visible outline civic.
- `src/styles/_typography.scss` → `@fontsource/inter`, `@fontsource/roboto-condensed`, link a Material Symbols Outlined.
- `src/styles/_animations.scss` → `@keyframes marker-pulse`, `@media (prefers-reduced-motion)`.
- `src/styles/_leaflet-overrides.scss` → ocultar `.leaflet-control-zoom`, restilizar `.leaflet-control-attribution`, overrides de cluster.
- En `styles.scss` exponer tokens al `@theme` de Tailwind v4 para que `bg-state-ejecucion`, `text-ink`, etc., funcionen como utilities tipadas al token.
- `src/app/app.config.ts` → agregar `provideHttpClient(withFetch())` y `provideZonelessChangeDetection()` (Angular 21 zoneless).

**Verificaciones**:
- `ng serve` arranca sin errores.
- Un `<div class="bg-surface text-ink">hola</div>` se ve con la paleta civic.
- Importar `import 'leaflet/dist/leaflet.css'` no rompe el build.

**Criterio de salida**:
- `package.json` lista las 9 dependencias.
- `src/styles/` con 5 partials.
- Branch limpia, commits convencionales (`chore(setup): tailwind v4`, `feat(styles): civic design tokens`, etc.).
- **NO** se crearon componentes todavía.

---

## Fase 2 — Derivación en front + contrato de datos (cero backend)

**Objetivo**: que el front consuma `/api/obras` y `/api/senales` tal cual están **hoy** y derive en cliente los tres campos que el demo necesita (`estado` de 5 buckets, `conSenal`, `fuente`). **Nada se toca del backend en esta fase.**

**Skills a invocar**:
- `Skill(skill: "angular-developer")` — para el patrón `resource()` + `computed()` que cruza `/api/obras` con `/api/senales`.
- `Skill(skill: "context7")` con `angular` si hay dudas de `resource()` / `httpResource()`.

**Acciones**:
1. Crear `core/models/obra.model.ts` con:
   - `ObraApi` (shape literal del backend según `v_obra_mvp`: `id, nobr_id, cui, nombre_obra, nombre_inversion, entidad_nombre, distrito_nombre, latitud, longitud, estado_obra_wfs, estado_proyecto_mef, avance_fisico_infobras, avance_fisico_mef, mto_viable, costo_actualizado, monto_contrato, existe_informe_control, existe_paralizacion_mef, es_saldo_obra, sobrecosto_pct, url_*`).
   - `Obra` (shape **del demo**: `id, titulo, estado, monto, entidad, distrito, coords, conSenal, fuente`).
   - `EstadoObra = 'en_ejecucion'|'en_licitacion'|'verificada'|'informativo'|'senal'`.
   - `Fuente = 'INFObras'|'SEACE'|'Ciudadanos'`.
2. Crear `features/mapa/utils/estado-catalog.ts` con tres funciones puras y testeables:
   - `derivarEstado(o: ObraApi, tieneSenal: boolean): EstadoObra` con las reglas:
     - `'verificada'` si `existe_informe_control && (avance_fisico_infobras ?? 0) >= 95`
     - `'en_ejecucion'` si `estado_obra_wfs ∈ ['En Ejecución','Activa']`
     - `'en_licitacion'` si `estado_proyecto_mef === 'ACTIVO'` y `avance_fisico_infobras` es null/0
     - `'senal'` si `tieneSenal && !existe_informe_control && avance_fisico_infobras == null`
     - `'informativo'` resto
   - `derivarFuente(o: ObraApi, origenSenal?: 'ciudadana'|'oficial'): Fuente` (INFObras si `nobr_id`, Ciudadanos si la señal asociada es ciudadana, SEACE como fallback).
   - `formatoMonto(n: number | null): string` → `"S/ 2.85 M"` / `"—"`.
3. Crear `core/services/senales.service.ts` con `httpResource()` apuntando a `/api/senales?ubigeo=` y un `computed<Set<number>>()` con los `obra_id` que tienen señal.
4. Crear `core/services/obras.service.ts` con `httpResource()` apuntando a `/api/obras` y un `obras = computed<Obra[]>(() => mapApiToObra(apiResp(), tieneSenalSet()))` que cruza ambos resources.
5. **Cero cambios en `backend/`**. Si una regla del demo no se puede expresar con los datos disponibles, **se documenta el gap en este `.md`** y se pospone — no se modifica la API.

**Criterio de salida**:
- `obras.service.ts` retorna un signal `Obra[]` listo para consumir desde el componente de mapa.
- Las tres funciones de `estado-catalog.ts` están escritas y exportadas.
- Cero edits en `backend/` o `db/`.

---

## Fase 3 — SDD del cambio frontend: explore + propose + spec + design + tasks

**Objetivo**: tener el plan SDD del cambio `migrar-demo-mapa-callao` aprobado y descompuesto en tareas atómicas **antes** de tocar componentes.

**Skills a invocar (en orden)**:
1. `Skill(skill: "sdd-new", args: "migrar-demo-mapa-callao")` — crea proposal vía sub-agente exploración + proposal.
2. `Skill(skill: "sdd-spec")` — genera specs delta.
3. `Skill(skill: "sdd-design")` — diseño técnico con: feature `mapa`, services (`obras`, `filtros`, `map`, `geolocation`), modelos, shared UI.
4. `Skill(skill: "sdd-tasks")` — descomposición.

**Inputs que tiene que considerar el design**:

- **Arquitectura de archivos** (referencia: proyecto `al-orbita-gestor` en engram — feature-based, signals, OnPush, sin NgModules):

```
frontend-v2/src/app/
├─ core/
│  ├─ models/
│  │  ├─ obra.model.ts             ← Obra, EstadoObra, Fuente, Tramo
│  │  └─ filtros.model.ts
│  ├─ services/
│  │  ├─ obras.service.ts          ← resource() Angular 21 → /api/obras
│  │  ├─ obra-detalle.service.ts   ← resource() → /api/obras/{id}
│  │  ├─ filtros.service.ts        ← signals de estado de filtros + URL sync
│  │  ├─ map.service.ts            ← wraps L.map, layers, cluster, polylines
│  │  └─ geolocation.service.ts    ← btn "Centrar en Callao"
│  └─ config/
│     ├─ map.config.ts             ← CENTER_CALLAO, ZOOM, TILE_URL
│     └─ api.config.ts             ← API_BASE_URL via inject token
├─ shared/ui/
│  ├─ chip/                        ← .chip del demo (toggle pressed)
│  ├─ estado-pill/                 ← banda + pill por estado (5 variantes)
│  ├─ icon/                        ← <app-icon name="construction"/>  Material Symbols
│  ├─ float-button/                ← .float-btn circular
│  ├─ icon-button/                 ← .btn-close
│  └─ overlay-backdrop/            ← base drawer/modal
├─ features/mapa/
│  ├─ mapa.page.ts                 ← container, orquesta selección + filtros
│  ├─ components/
│  │  ├─ topbar/                   ← logo, search, btn filtros, btn ubicación
│  │  ├─ topbar-strip/             ← strip inferior
│  │  ├─ leaflet-map/              ← presentational, usa MapService
│  │  ├─ obra-panel/               ← card izquierda con story flow
│  │  │  ├─ obra-panel.ts
│  │  │  ├─ obra-monto.ts
│  │  │  ├─ obra-meta.ts
│  │  │  ├─ obra-senal-alert.ts
│  │  │  └─ obra-context.ts
│  │  ├─ filtros-drawer/           ← drawer CDK FocusTrap
│  │  │  ├─ filtros-drawer.ts
│  │  │  ├─ filtros-chips.ts
│  │  │  └─ leyenda.ts
│  │  ├─ float-controls/           ← zoom in/out/layers
│  │  ├─ result-counter/
│  │  └─ marker-popup/             ← renderizado vía ApplicationRef.createComponent
│  └─ utils/
│     ├─ marker-factory.ts         ← L.divIcon por estado
│     ├─ radius-from-obra.ts       ← radio del círculo de impacto según monto
│     ├─ estado-catalog.ts         ← labels, pillClass, iconConfig (paridad demo)
│     └─ formato-monto.ts          ← numeric → "S/ 2.85 M"
└─ assets/mock/
   └─ tramos.callao.json
```

- **Reglas de oro** (no negociables):
  - `changeDetection: OnPush` en todo componente.
  - **Signals** para estado (`signal`, `computed`, `linkedSignal`, `resource`); **inputs/outputs como signals** (`input.required<T>()`, `output<T>()`).
  - **Cero hardcoded color**: todo va vía tokens SCSS / utilities Tailwind mapeadas a `@theme`.
  - **Sin specs** (`.spec.ts`) — convención de proyecto (igual a `al-orbita-gestor`).
  - **Conventional commits** sin Co-Authored-By.
  - El mapa Leaflet **no se renderiza dentro de Angular DOM**: el `LeafletMapComponent` crea `L.map(divRef)` en `afterNextRender`, pero la lógica de layers y markers vive en `MapService` (servicio singleton). Los markers reciben listeners que emiten un signal `selectedObraId` en `ObrasService`.

- **Estrategia de delivery**: dado que esto es un solo feature grande pero homogéneo, se sugiere `auto-chain` con slices de ≤400 líneas. Si los tasks superan eso, partir en `chained PRs`.

**Criterio de salida**:
- Engram tiene `sdd/migrar-demo-mapa-callao/proposal|spec|design|tasks`.
- Tasks list aprobada por el usuario.

---

## Fase 4 — Apply (implementación)

**Objetivo**: implementar el feature siguiendo los tasks de Fase 3.

**Skills a invocar**:
- `Skill(skill: "sdd-apply")` — implementa por lotes, marca tasks completados.
- `Skill(skill: "angular-developer")` — consulta de patterns.
- `Skill(skill: "angular-tailwind")` — uso correcto de utilities.
- `Skill(skill: "context7")` con `leaflet` y `leaflet.markercluster` cuando dude la API.

**Lotes sugeridos** (autocontenidos, commiteables uno a uno):

### Lote A — Núcleo de datos
- `core/models/obra.model.ts`
- `core/config/{api,map}.config.ts`
- `core/services/obras.service.ts` (con `resource()` apuntando a `/api/obras`)
- `core/services/obra-detalle.service.ts` (con `resource()` apuntando a `/api/obras/{id}`)
- `core/services/filtros.service.ts` (signals + URL sync con `Router`)

### Lote B — Shared UI atómicos
- `shared/ui/icon`
- `shared/ui/chip`
- `shared/ui/estado-pill`
- `shared/ui/icon-button`
- `shared/ui/float-button`
- `shared/ui/overlay-backdrop`

### Lote C — Mapa
- `features/mapa/utils/{marker-factory, radius-from-obra, estado-catalog, formato-monto}`
- `core/services/map.service.ts`
- `features/mapa/components/leaflet-map`
- `features/mapa/components/marker-popup` (renderizado dinámico)

### Lote D — UI flotante
- `features/mapa/components/topbar` + `topbar-strip`
- `features/mapa/components/float-controls`
- `features/mapa/components/result-counter`
- `core/services/geolocation.service.ts`

### Lote E — Panel obra
- `features/mapa/components/obra-panel/*` (5 subcomponentes)
- Conexión con `obra-detalle.service`

### Lote F — Drawer de filtros
- `features/mapa/components/filtros-drawer` con CDK `FocusTrap`
- `filtros-chips` + `leyenda`
- Sync con `FiltrosService`

### Lote G — Página container
- `features/mapa/mapa.page.ts` que orquesta todo
- Ruta `''` en `app.routes.ts` → `MapaPage`

**Criterio de salida por lote**:
- `ng serve` arranca, no rompe.
- Commit convencional limpio.
- Tasks marcados `[x]`.

---

## Fase 4.5 — Paridad visual con el demo (desbloqueador previo a Fase 5/6)

> **Por qué existe esta fase**: auditoría Playwright del 2026-05-17 detectó que frontend-v2 muestra 0 obras, usa tile OSM en vez de CARTO Positron y tiene markers/clusters/panel sin poder verificarse. Sin estos fixes, Fase 5 y 6 se validan sobre una pantalla incompleta.

**Objetivo**: que `http://localhost:4200/` se vea y se comporte como `http://127.0.0.1:5500/demo/index.html` antes de entrar en responsive/a11y/polish.

**No modifica backend ni DB.**

---

### Paso 1 — P0: diagnóstico y datos visibles

**Problema**: `GET /api/obras?ubigeo=150101&limit=200` devuelve `{ total: 0, items: [] }`.

**Causa probable**: la BD local no tiene datos. Verificar:

```powershell
# ¿Tiene datos?
$env:PGPASSWORD = "123"
& "C:\Program Files\PostgreSQL\17\bin\psql" -U postgres -h localhost -d obrascerca_v2 `
  -c "SELECT COUNT(*) FROM obra;"
```

**Si devuelve 0**: correr el restore del snapshot de demo:

```powershell
cd C:\__APLICACIONES\_Hackaton\obras-cerca\db
python restore_demo.py
```

Esto carga: 50 distritos · 2,301 entidades · 7 proyectos MEF · 8 obras · 15 informes · 36 contratos · 5 señales.

**Si el backend sigue devolviendo 0 obras con ubigeo=150101**: depurar la vista `v_obra_mvp` directamente:

```powershell
& "C:\Program Files\PostgreSQL\17\bin\psql" -U postgres -h localhost -d obrascerca_v2 `
  -c "SELECT id, nombre_obra, latitud, longitud FROM v_obra_mvp LIMIT 5;"
```

Si hay obras pero sin ubigeo 150101, cambiar el ubigeo por defecto en `map.config.ts` al que tenga data real, o quitar el filtro ubigeo temporalmente para ver datos.

**Archivo**: `frontend-v2/src/app/core/config/map.config.ts`

```ts
// Cambiar según ubigeo con data real en la BD
export const UBIGEO_CALLAO_DEFAULT = '150101';
```

**Criterio de salida**: `obras.length > 0` visible en devtools → `ObrasService.total()` > 0.

---

### Paso 2 — P1: tile layer → CARTO Positron

El demo usa CARTO Positron (`light_all`), no OSM. OSM tiene demasiado ruido visual para la paleta civic warm.

**Archivo**: `frontend-v2/src/app/core/config/map.config.ts`

```ts
export const TILE_URL =
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
```

No requiere API key. Atribución obligatoria incluida.

**Criterio de salida**: mapa con fondo claro/gris neutral — igual que el demo.

---

### Paso 3 — P1: markers y clusters visibles

Con datos en la BD, verificar que `MapService` recibe las obras y crea los markers. Si los markers no aparecen tras el fix de datos, depurar:

1. `LeafletMapComponent` — ¿`afterNextRender` inicializa el mapa correctamente?
2. `MapService.setObras(obras)` — ¿se llama desde `MapaPage` con el array no vacío?
3. `marker-factory.ts` — ¿`L.divIcon` genera HTML válido?
4. Consola del browser — ¿errores de Leaflet?

**Archivos a revisar**:
- `frontend-v2/src/app/core/services/map.service.ts`
- `frontend-v2/src/app/features/mapa/components/leaflet-map/leaflet-map.ts`
- `frontend-v2/src/app/features/mapa/utils/marker-factory.ts`
- `frontend-v2/src/app/features/mapa/mapa.page.ts`

**Criterio de salida**: markers cívicos visibles en el mapa, clusters agrupando cuando hay solapamiento.

---

### Paso 4 — P1: panel obra seleccionable

Con markers visibles, verificar el flow de selección:

1. Click en marker → popup con "Ver detalle".
2. Click en "Ver detalle" → `selectedId` se setea → `obra-panel` abre con story flow.
3. Escape o btn-close → panel se cierra.

**Archivos a revisar**:
- `frontend-v2/src/app/features/mapa/components/obra-panel/obra-panel.ts`
- `frontend-v2/src/app/features/mapa/components/marker-popup/marker-popup.ts`
- `frontend-v2/src/app/features/mapa/mapa.page.ts` (señal `selectedId`)

**Criterio de salida**: story flow completo — estado-pill, título, monto, entidad/distrito, señal-alert si aplica, botón "Ver ficha".

---

### Paso 5 — P2: topbar y strip alineados al demo

Diferencias detectadas:
- Ícono logo: frontend-v2 usa `public`, demo usa `construction`. Alinear.
- Counter: muestra `0` porque no hay obras → se resuelve con Paso 1.
- Copy del strip: verificar contra el demo (líneas 200-230 aprox de `demo/index.html`).

**Archivo**: `frontend-v2/src/app/features/mapa/components/topbar/topbar.ts` y su template.

**Criterio de salida**: topbar visualmente idéntica al demo en desktop 1440px.

---

### Paso 6 — P2: drawer mobile y conteos reales

Con datos visibles, los chips del drawer mostrarán conteos reales por estado. Verificar:
- Conteos por estado en cada chip (`en_ejecucion`, `en_licitacion`, `verificada`, `con_senal`).
- En mobile (390px): drawer ocupa fullscreen al abrir.

**Archivos**: `filtros-drawer/filtros-chips.ts`, `filtros.service.ts`.

**Criterio de salida**: chips con conteos > 0 cuando hay obras cargadas.

---

### Criterio de salida de Fase 4.5

- `localhost:4200` muestra mapa con tile CARTO Positron, markers cívicos, clusters y panel funcional.
- Comparativa Playwright demo vs frontend-v2: sin P0/P1 abiertos.
- Commits convencionales por paso (`fix(map): carto positron tile`, `fix(data): ubigeo default 150101`, etc.).

**Recién entonces: ejecutar Fase 5.**

---

## Fase 4.6 — Limpieza visual del mapa + validación UX de clusters

> **Contexto**: prueba manual del 2026-05-17 sobre `localhost:4200` después de Fase 4.5. El mapa ya carga markers, pero todavía hay ruido visual que no existe en la demo y falta validar la UX de agrupación al alejar/acercar.

**Objetivo**: dejar el mapa de `frontend-v2` visualmente limpio — **solo markers**, sin líneas/círculos SVG extra — y confirmar que el comportamiento de clusters al hacer zoom coincide con `demo/index.html`.

**Skills a invocar**:
- `Skill(skill: "angular-developer")` — para tocar `MapService` sin romper Angular 21 standalone, signals, OnPush ni el puente imperativo con Leaflet.
- `Skill(skill: "playwright-cli")` — para comparar UX demo vs `frontend-v2`: zoom out/in, aparición/desaparición de clusters y DOM real de `.leaflet-interactive`.
- `Skill(skill: "context7")` con `leaflet` / `leaflet.markercluster` sólo si hay dudas de API o comportamiento del plugin.

**Nota de coherencia**: cuando una fase del plan menciona validación visual/UX o librerías específicas, la fase debe declarar explícitamente las skills necesarias antes de listar acciones. No dejar skills implícitas.

---

### Tarea 1 — Quitar líneas/círculos `leaflet-interactive` del mapa

**Problema observado**: en `http://localhost:4200/` aparecen elementos SVG con clase `leaflet-interactive` como líneas/círculos sobre el mapa. En `http://127.0.0.1:5500/demo/index.html` esos elementos no aparecen en el estado base.

**Regla visual**: en el mapa base de `frontend-v2` deben verse **solo markers**. No deben renderizarse círculos de radio, polylines ni overlays SVG si no existen en la demo.

**Archivos candidatos a revisar**:
- `frontend-v2/src/app/core/services/map.service.ts`
  - `circleLayer`
  - `circlesById`
  - creación de `L.circle(...)`
  - `syncTramos(...)` y creación de `L.polyline(...)`
- `frontend-v2/src/app/features/mapa/mapa.page.ts`
  - effect que llama `mapService.syncTramos(...)`
- `frontend-v2/src/app/core/services/tramos.service.ts`
- `frontend-v2/src/app/assets/mock/tramos.callao.json`

**Acción esperada**:
1. Identificar qué layer produce los `.leaflet-interactive` visibles.
2. Eliminar o desactivar ese layer para el estado base.
3. Si el origen son `L.circle`, no crear/agregar círculos al mapa.
4. Si el origen son `L.polyline`/tramos, no sincronizar tramos en esta fase.

**Criterio de salida**:
- En DevTools no hay líneas/círculos visibles sobre el mapa base.
- Visualmente, `frontend-v2` muestra mapa + markers, sin overlays SVG extra.
- Los markers siguen siendo clickeables y abren popup/panel.

---

### Tarea 2 — Validar UX de agrupación de markers contra la demo con Playwright

**Objetivo**: comprobar, con Playwright, cómo se agrupan/desagrupan los markers al alejar/acercar en la demo y usar ese comportamiento como fuente de verdad para `frontend-v2`.

**URLs de comparación**:
- Demo fuente: `http://127.0.0.1:5500/demo/index.html`
- App Angular: `http://localhost:4200/`

**Acción esperada**:
1. Abrir la demo con Playwright.
2. Hacer zoom out hasta que los markers se agrupen.
3. Registrar el comportamiento esperado:
   - cuándo aparece el cluster;
   - cómo se ve el número dentro del cluster;
   - cómo se desagrupa al hacer zoom in;
   - si el cluster es clickeable/expande.
4. Repetir el mismo flujo en `frontend-v2`.
5. Ajustar `MapService.createClusterIcon(...)` o configuración de `markerClusterGroup(...)` solo si hay diferencias reales contra la demo.

**Criterio de salida**:
- Al hacer zoom out, los markers de `frontend-v2` se agrupan igual que en la demo.
- Al hacer zoom in, se desagrupan igual que en la demo.
- El cluster se ve como círculo oscuro con número blanco, sin HTML crudo visible.
- La interacción de cluster no rompe selección de markers ni popup.

---

### Criterio de salida de Fase 4.6

- Mapa base: solo markers, sin líneas/círculos `leaflet-interactive` visibles.
- Clusters: comportamiento de zoom validado contra demo mediante Playwright.
- Sin regresión en click de marker → popup → panel.
- `tsc --noEmit` limpio.

**Recién entonces: ejecutar Fase 4.7.**

---

## Fase 4.7 — UX marker → detalle automático + títulos largos

> **Contexto**: prueba manual del 2026-05-17. Al hacer click en un marker aparece el popup correctamente, pero no se abre automáticamente el panel **Detalle de obra seleccionada**. Además, cuando el título de la obra es muy largo, el detalle lo corta o lo muestra mal, generando mala UX.

**Objetivo**: que el click sobre un marker seleccione la obra y abra el detalle automáticamente, y que los títulos largos sean legibles sin romper el layout.

---

### Skills a invocar

- `Skill(skill: "angular-developer")` — para ajustar signals/eventos entre `MapService`, `marker-popup` y `MapaPage` sin romper Angular 21 standalone + OnPush.
- `Skill(skill: "clarify")` — para decidir la microcopy del popup ahora que el botón "Ver detalle" deja de tener sentido.
- `Skill(skill: "layout")` — para corregir overflow, wrapping y jerarquía visual del título largo en el panel.
- `Skill(skill: "playwright-cli")` — para verificar el flujo real: click marker → popup visible → panel detalle abierto → título legible.

---

### SDD necesario para esta fase

**Change name**: `fase-4-7-marker-detalle-ux`

Como es un fix UX acotado, no requiere abrir un cambio SDD grande con `sdd-new`. Sí requiere **SDD mínimo documentado** antes de tocar código:

#### Proposal

El usuario debe poder entender una obra con un solo click en el mapa. El popup queda como resumen contextual; el panel lateral es el lugar principal del detalle.

#### Spec

- Al hacer click en un marker, el sistema MUST setear `selectedId` inmediatamente.
- Al setear `selectedId`, el panel `ObraPanel` MUST abrirse automáticamente con la obra seleccionada.
- El popup MAY seguir mostrándose, pero no MUST contener un CTA redundante "Ver detalle" si el detalle ya se abre automáticamente.
- El título de la obra en el panel MUST ser legible aunque sea largo.
- El título en el panel MUST envolver texto (`wrap`) y no debe quedar cortado por `overflow`, altura fija o `line-clamp` agresivo.
- En mobile, el título largo MUST poder leerse dentro del bottom-sheet sin tapar acciones principales.

#### Design decision

**Decisión UX**: marker click = selección directa.

| Elemento | Decisión |
|---|---|
| Marker | Click selecciona obra y abre detalle automáticamente. |
| Popup | Queda como resumen rápido: estado + título corto. Sin botón "Ver detalle" redundante. |
| Panel | Fuente de verdad del detalle. Debe mostrar título completo o una versión expandible legible. |
| CTA principal | Vive en el panel, no en el popup. Ej: "Ver ficha" / link externo si existe. |

**Tradeoff**: se pierde un paso explícito de confirmación (botón en popup), pero se gana velocidad y claridad. Para mapa ciudadano, un click debe revelar información útil, no pedir otro click. MENOS fricción.

#### Tasks

1. Revisar `MapService`:
   - Confirmar que click de marker o popup emite `clickedId$`.
   - Si hoy sólo emite cuando se clickea el botón del popup, mover la emisión al click del marker.
2. Revisar `popup-html.ts` / `marker-popup`:
   - Eliminar botón "Ver detalle" si queda redundante.
   - Mantener popup como resumen visual compacto.
3. Revisar `MapaPage`:
   - Confirmar que `clickedId` actualiza `selectedId` y eso abre `ObraPanel`.
4. Revisar `obra-panel` styles:
   - Quitar cualquier `white-space: nowrap`, `overflow: hidden`, `text-overflow: ellipsis` o `line-clamp` en el título principal.
   - Agregar `overflow-wrap: anywhere`, `hyphens: auto`, `line-height` cómodo y contenedor scroll si hace falta.
5. Validar con Playwright:
   - click en marker;
   - popup visible;
   - panel abierto;
   - título largo visible/legible;
   - sin regresión en cierre con Escape/botón cerrar.

---

### Archivos candidatos a revisar

- `frontend-v2/src/app/core/services/map.service.ts`
- `frontend-v2/src/app/features/mapa/utils/popup-html.ts`
- `frontend-v2/src/app/features/mapa/components/marker-popup/marker-popup.ts` si existe/está activo
- `frontend-v2/src/app/features/mapa/mapa.page.ts`
- `frontend-v2/src/app/features/mapa/components/obra-panel/obra-panel.ts`
- `frontend-v2/src/app/features/mapa/components/obra-panel/obra-panel.html`
- `frontend-v2/src/app/features/mapa/components/obra-panel/obra-panel.scss`

---

### Criterio de salida de Fase 4.7

- Click en marker abre popup **y** abre automáticamente `Detalle de obra seleccionada`.
- Popup no tiene CTA redundante si el detalle ya se abre solo.
- Título largo en el panel se lee correctamente; no queda cortado ni pisa otros elementos.
- Panel sigue cerrando con Escape y botón cerrar.
- Validación Playwright documentada.
- `tsc --noEmit` limpio.

**Recién entonces: ejecutar Fase 5.**

---

## Fase 5 — Responsive + a11y

**Objetivo**: validar responsive + accesibilidad sobre el flujo real post 4.5/4.6/4.7: mapa base sólo markers, clusters al alejar, click en marker abre popup resumen **y** panel automático, título largo legible.

**Skills a invocar**:
- `Skill(skill: "adapt")` — ajustar desktop/mobile sin romper el flujo marker → panel.
- `Skill(skill: "audit")` — a11y + perf + theming check, severidades P0/P1/P2.
- `Skill(skill: "playwright-cli")` — validar interacción real en desktop 1440px y mobile 390px.
- `Skill(skill: "layout")` — si el bottom-sheet/panel queda apretado por títulos largos.
- `Skill(skill: "clarify")` — si el texto del popup `Detalle abierto en el panel` no ayuda o genera ruido.

**Acciones**:
- Desktop 1440px:
  1. Click en marker → popup resumen visible + `ObraPanel` abierto automáticamente.
  2. Título largo del panel envuelve sin cortarse y el panel scrollea si hace falta.
  3. Escape cierra panel sin dejar estado visual seleccionado roto.
- Mobile 390px:
  1. `ObraPanel` funciona como bottom-sheet, no tapa topbar/controles críticos más de lo necesario.
  2. Título largo se lee dentro del bottom-sheet sin pisar monto/acciones.
  3. `FiltrosDrawer` ocupa pantalla completa, con focus trap y cierre claro.
- Mapa:
  1. Estado base: sólo markers, sin `path.leaflet-interactive` de circles/tramos.
  2. Zoom out/in: clusters aparecen y desaparecen sin romper marker click.
- A11y:
  1. `aria-label="Detalle de obra seleccionada"` sigue correcto para el panel.
  2. Drawer con `aria-modal`, foco contenido y retorno de foco al botón filtros.
  3. Botones flotantes tienen labels útiles.
  4. `prefers-reduced-motion` honrado.
  5. Contraste OKLCH ≥ AA en popup, panel, drawer, chips y topbar.

**Criterio de salida**:
- Reporte de `audit` con 0 P0/P1 abiertos.
- Evidencia Playwright desktop + mobile del flujo marker → popup + panel.
- Sin regresión: popup sin CTA redundante, panel automático, títulos largos legibles.
- `npx tsc --noEmit` limpio. **No ejecutar `ng build`**.

---

## Fase 6 — Verify + polish + archive

**Objetivo**: cerrar el ciclo SDD validando el estado real del feature después de las fases correctivas 4.5, 4.6 y 4.7.

**Skills a invocar (en orden)**:
1. `Skill(skill: "polish")` — última pasada visual sobre mapa, popup, panel, drawer y mobile.
2. `Skill(skill: "playwright-cli")` — evidencia final end-to-end en desktop/mobile.
3. `Skill(skill: "sdd-verify")` — validación contra specs + adendas 4.5/4.6/4.7.
4. `Skill(skill: "sdd-archive")` — sync specs y cierre.

**Checklist de verificación final**:

### Datos + mapa
- Backend local responde `/api/obras` y el front muestra obras con coordenadas.
- Mapa usa CARTO Positron.
- Mapa base muestra sólo markers, sin circles/tramos/polylines visibles.
- Zoom out agrupa markers en cluster; zoom in los desagrupa.

### Flujo marker → detalle
- Click en marker abre popup resumen.
- El mismo click abre automáticamente `Detalle de obra seleccionada`.
- Popup no tiene botón "Ver detalle" redundante.
- Panel se cierra con Escape y botón cerrar.
- Título largo no queda truncado, no pisa monto/acciones y permite scroll del panel.

### Filtros + estado
- Chips filtran markers visibles.
- Conteos del drawer coinciden con markers/obras visibles.
- Cluster no rompe filtros activos.

### Responsive + a11y
- Desktop 1440px y mobile 390px verificados con Playwright.
- Drawer mobile fullscreen con focus trap.
- Bottom-sheet/panel mobile usable con título largo.
- Contraste AA y focus-visible correctos.

### Técnica
- `npx tsc --noEmit` limpio.
- Sin `.spec.ts` agregados.
- Sin cambios en backend/db.
- Sin `ng build` automático.

**Criterio de salida**:
- `verify-report` con verdict `PASS` o `PASS WITH WARNINGS` (sin CRITICAL).
- Change archivado en engram.
- Demo navegable end-to-end contra `localhost:8000`.
- Si `sdd-verify` encuentra divergencias entre specs originales y decisiones 4.5/4.6/4.7, actualizar el artifact de verificación con esas adendas antes de archivar.

---

## Fase 7 — Gaps documentados (fuera de scope de este plan)

**Esta fase NO se ejecuta**. Sólo deja registro de lo que quedó sin cubrir y por qué, para que cuando se decida tocar backend exista trazabilidad.

**Gaps registrados**:

1. **`tiene_senal` en el listado `/api/obras`** — hoy se resuelve haciendo un segundo fetch a `/api/senales`. Es ineficiente con datasets grandes; en su momento se podrá agregar el flag al `SELECT` del listado.
2. **`fuente_primaria` derivada en backend** — hoy se infiere en front desde `nobr_id` y el origen de la señal. Cuando se quiera unificar lógica, mover a SQL.
3. **`estado_calculado` (5 buckets demo)** — hoy se deriva en `estado-catalog.ts`. Si entran nuevos clientes (mobile, terceros), conviene moverlo a la vista.
4. **Tramos/radios de impacto** — Fase 4.6 decidió que el mapa base queda **solo con markers**. `syncTramos()` queda desactivado y no se renderizan `L.circle`/`L.polyline` para evitar overlays `path.leaflet-interactive`. Si se reintroducen tramos o radios, debe abrirse un cambio SDD aparte con diseño visual explícito y comparación contra demo.
5. **`/api/distritos/{ubigeo}/bbox`** — hoy se hardcodea `CENTER_CALLAO = [-12.0800, -77.0400]`, `ZOOM_DEFAULT = 12` y `ZOOM_MIN = 8` para cubrir el snapshot demo de Lima Metro y permitir clustering. Cuando haya endpoint de bbox, el centro/zoom deben venir de backend o configuración por distrito.
6. **Ubigeo por defecto** — `UBIGEO_CALLAO_DEFAULT = null` para mostrar todas las obras con coordenadas del snapshot demo. Cuando la BD tenga datos concentrados en un distrito, volver a un ubigeo explícito.

**Cuándo abrir esta fase**: sólo si se decide explícitamente tocar backend. Mientras tanto, **todo se resuelve en front**.

---

## Skills NO usar en este plan (y por qué)

Para evitar ruido y consumo innecesario de contexto, **NO** invocar estas skills durante el plan:

- `angular-new-app` — el proyecto ya existe.
- `frontend-design`, `impeccable`, `design-taste-frontend`, `ui-ux-pro-max`, `gpt-taste`, `high-end-visual-design`, `industrial-brutalist-ui`, `minimalist-ui`, `frontend-ui-dark-ts`, `bolder`, `quieter`, `colorize`, `distill`, `delight`, `overdrive`, `shape`, `typeset`, `critique`, `optimize` — el diseño ya está clavado en el demo, no hay que reinventarlo. Excepciones acotadas: `layout`/`clarify` cuando una fase corrija UX concreta ya detectada; `audit` y `polish` en Fase 5/6.
- `brandkit`, `imagegen-frontend-*`, `stitch-*` — no se necesitan assets generados.
- `judgment-day`, `chained-pr`, `branch-pr`, `issue-creation`, `comment-writer` — para el flujo de PR/colaboración, no para esta migración.
- `graphify`, `security-review`, `razcode-capture` — irrelevantes.
- `playwright-cli` — **sí usar** sólo en fases con validación visual/UX explícita (4.5, 4.6, 4.7, 5 y 6). No usarlo para exploración genérica.
- `database-schema-designer` — no se toca DB en este plan.
- `sdd-new` para `scraper-tramos-wfs` — explícitamente fuera de scope (ver Fase 7).

---

## Convenciones del proyecto (recordatorio)

- Engram project: **`obras-cerca`**.
- Spanish Rioplatense en commits y comunicación interna.
- **No** ejecutar `ng build` automáticamente después de cambios.
- **No** `Co-Authored-By` en commits.
- **No** `.spec.ts`.
- Conventional commits (`feat`, `fix`, `chore`, `style`, `refactor`).
- Cero color hardcoded — todo vía tokens / utilities tipadas al `@theme`.
- OnPush + signals + standalone everywhere.

---

## Cómo arrancar

Decí literalmente: **"ejecutá Fase 0"**, **"ejecutá Fase 1"**, etc. Cada fase tiene criterio de salida; no avancés a la siguiente sin que esté cerrada. Si una fase encuentra un blocker, parar, reportar y pedir decisión.
