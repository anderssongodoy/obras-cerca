# Flujo de ingesta completo — Obras Cerca

> Documento técnico que describe **paso a paso** cómo se llena la BD `obrascerca_v2` desde cero,
> qué URLs se visitan, qué se extrae de cada respuesta, y cómo se inserta.
>
> Esto es el manual interno de cómo funciona el producto por dentro. Si querés correrlo a
> mano para entenderlo, cada fase es un script Python independiente bajo `backend/scripts/`.

---

## Diagrama general

```
                ┌────────────────────────────────────────────┐
                │   Portal de Transparencia (PTE)            │
FASE 1+2  ←─────┤   Lista de entidades del Perú              │
                │   + mapeo entidad → IdUE SIAF              │
                └───────────────┬────────────────────────────┘
                                ↓
                     entidad (~2,300 filas)
                                ↓
                ┌────────────────────────────────────────────┐
FASE 3    ←─────┤   MEF GetEjecucion                          │
                │   Por cada UE, lista paginada de CUIs       │
                └───────────────┬────────────────────────────┘
                                ↓
                  proyecto_mef (1 fila por CUI)
                                ↓
                ┌────────────────────────────────────────────┐
                │  4 endpoints MEF por cada CUI               │
FASE 4    ←─────┤  traeDetInvSSI  →  proyecto_mef (datos)     │
                │  verInfObras2   →  obra (1..N saldos)       │
                │  traeContrato…  →  procedimiento_seleccion  │
                │  traeListaParaliza → paralizacion_oficial   │
                └───────────────┬────────────────────────────┘
                                ↓
                ┌────────────────────────────────────────────┐
                │  Por cada NOBR_ID de Infobras:              │
FASE 5    ←─────┤  WFS Contraloría → coordenadas + estado     │
                │  Ficha pública HTML → datos visibles        │
                │  InformeControl JS → PDFs Contraloría       │
                └───────────────┬────────────────────────────┘
                                ↓
                ┌────────────────────────────────────────────┐
FASE 6    ←─────┤  Pentaho/CONOSCE XLSX mensuales             │
(paralelo)      │  Filtro Lima/Callao + ≤8 UIT               │
                │  → orden_compra_servicio                    │
                └───────────────┬────────────────────────────┘
                                ↓
                ┌────────────────────────────────────────────┐
FASE 7    ←─────┤  SQL determinístico                         │
                │  Detecta señales cruzando las 6 fuentes     │
                │  → senal_revision                           │
                └────────────────────────────────────────────┘
```

---

## ¿Por qué MEF es el maestro y no Infobras?

Antes de la fase 1, una decisión de arquitectura crítica. La primera versión del producto
usaba **Infobras como maestro** (porque tiene los XLSX bulk fáciles de bajar). Lo descartamos
después del caso JNJ:

- **NOBR_ID 42593** (Junta Nacional de Justicia) en Infobras bulk: `Existe Paralización = SI`,
  avance 99.86%, contratista "CONSORCIO SAN ISIDRO".
- **CUI 2171549** (la misma obra) en MEF SSI: avance real 76.85%, `costo_actualizado = S/88.2M`
  vs `mto_viable = S/41.1M` (sobrecosto del 114%), y `verInfObras2` devuelve **3 NOBR_IDs**
  (el original + 2 saldos de obra con avance 0% cada uno).

Es decir: Infobras te muestra una foto vieja de la obra original. **MEF te muestra que la
obra se cortó, que el contratista quebró y que hay saldos firmados que aún no arrancaron.**

**Regla:** MEF es la fuente de verdad financiera y de saldos. Infobras solo aporta
coordenadas (WFS) e informes de control (PDFs de auditoría).

---

## Fase 1 — Descubrir entidades públicas del Perú

**Script:** `backend/scripts/01_descubrir_entidades.py`
**Cliente:** `backend/app/clients/pte.py`
**Duración:** ~30 seg
**Output BD:** tabla `entidad` (~2,300 filas)

### Qué hace

Baja el catálogo del Portal de Transparencia Estándar (PTE) para los 5 tipos de poder
y consolida un catálogo nacional de entidades.

### URLs visitadas (5 requests)

```http
GET https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=5  # Gobiernos Locales (1,279)
GET https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx              # Ejecutivo (348)
GET https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=4  # Autónomos (99)
GET https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=7  # Regionales (534)
GET https://www.transparencia.gob.pe/buscador/pte_transparencia_listado_entidades_poder.aspx?Tipo_Pod=2  # Judicial (40)
```

### Qué extrae

Regex sobre el HTML:

```regex
<a\s+[^>]*id_entidad=(\d+)[^>]*>([^<]+)</a>
```

Cada match es `(id_entidad, nombre_con_sigla)`. Ejemplo:

```html
<a href='../enlaces/pte_transparencia_enlaces.aspx?id_entidad=10080'>MUNICIPALIDAD DISTRITAL DE SAN ISIDRO LIMA (MDSI)</a>
```

→ `id_entidad=10080`, `nombre="MUNICIPALIDAD DISTRITAL DE SAN ISIDRO LIMA"`, `sigla="MDSI"`

### Lógica de clasificación

```python
TIPO_POD_MAP = {
  5: ("municipalidad_distrital", "local"),
  None: ("ministerio", "nacional"),
  4: ("organismo_autonomo", "nacional"),
  2: ("organismo_autonomo", "nacional"),
  7: ("gobierno_regional", "regional"),
}

def clasificar_local(nombre: str) -> str:
    n = norm(nombre)
    if "PROVINCIAL" in n:    return "municipalidad_provincial"
    if "MUNICIPALIDAD" in n: return "municipalidad_distrital"
    if "EMPRESA" in n:       return "empresa_estatal"
    if "UNIVERSIDAD" in n:   return "universidad_nacional"
    return "otro"
```

### Vinculación con distrito MVP

Para cada muni del MVP, busca match de su nombre normalizado (sin tildes, en mayúsculas,
sin sufijo "- LIMA") contra los 50 distritos. Aliases manejados:
- `LURIGANCHO-CHOSICA` → distrito LURIGANCHO
- `CARMEN DE LA LEGUA REYNOSO` → distrito CARMEN DE LA LEGUA REYNOSO
- `MAGDALENA VIEJA` → distrito PUEBLO LIBRE (alias histórico)

### Insert en BD

```sql
INSERT INTO entidad
    (pte_id_entidad, nombre, nombre_norm, sigla, tipo, tipo_pod_pte,
     nivel_gobierno, distrito_id)
VALUES (%s, %s, %s, %s, %s::tipo_entidad, %s, %s, %s)
ON CONFLICT (nombre_norm) DO UPDATE SET
    pte_id_entidad = EXCLUDED.pte_id_entidad,
    sigla = EXCLUDED.sigla,
    tipo = EXCLUDED.tipo,
    distrito_id = COALESCE(EXCLUDED.distrito_id, entidad.distrito_id);
```

### Resultado típico

```
Por tipo:
  municipalidad_distrital       1001
  gobierno_regional              534
  ministerio                     348
  municipalidad_provincial       197
  organismo_autonomo             141
  otro                            51
  empresa_estatal                 29

Entidades vinculadas a distrito MVP: 79
```

---

## Fase 2 — Mapear entidad → IdUE SIAF

**Script:** `backend/scripts/02_mapear_idue.py`
**Cliente:** `backend/app/clients/mef.py` → `scrape_idue_de_pte()`
**Duración:** ~1 req/seg = depende de cuántas entidades procesar
**Output BD:** `entidad.siaf_idue` poblado

### Qué hace

El PTE conoce las entidades por su `id_entidad` (clave PTE), pero MEF las identifica por
`IdUE` (código SIAF). Para conectar PTE→MEF hay que visitar la página de "Proyectos de
inversión e Infobras" de cada entidad y extraer su IdUE del HTML.

### URL por cada entidad

```http
GET https://www.transparencia.gob.pe/reportes_directos/pte_transparencia_pro_inv.aspx
    ?id_entidad={X}&id_tema=26&ver=1
```

### Qué extrae

Regex:

```regex
IdUE=(\d+)
```

Aparece dentro de `<object data="..." />` en el HTML.

### Ejemplo concreto

Para San Isidro (`id_entidad=10080`):

```http
GET https://www.transparencia.gob.pe/reportes_directos/pte_transparencia_pro_inv.aspx?id_entidad=10080&id_tema=26&ver=1
```

Devuelve HTML con `IdUE=301280` adentro. Ese es el código SIAF de la UE San Isidro.

### Insert en BD

```sql
UPDATE entidad SET siaf_idue = %s WHERE id = %s;
```

---

## Fase 3 — Descubrir CUIs por entidad

**Script:** `backend/scripts/03_descubrir_cuis.py`
**Cliente:** `backend/app/clients/mef.py` → `get_ejecucion()`
**Duración:** ~1 req/seg, varias páginas por entidad
**Output BD:** tabla `proyecto_mef` (1 fila por CUI)

### Qué hace

Por cada `siaf_idue`, pagina el endpoint `GetEjecucion` del MEF para listar todos los
proyectos de inversión que esa unidad ejecutora gastó en el periodo (típicamente año vigente).

### URL

```http
POST https://ofi5.mef.gob.pe/proyectos_pte/forms/UnidadEjecutora.aspx/GetEjecucion
Content-Type: application/json; charset=UTF-8
X-Requested-With: XMLHttpRequest
Referer: https://ofi5.mef.gob.pe/proyectos_pte/forms/UnidadEjecutora.aspx?tipo=2&IdUE={IDUE}&IdUEBase={IDUE}&periodoBase=2026
```

### Body

```json
{
  "pPageSize": 30,
  "pPageNumber": 1,
  "pSortColumn": "codDGPP",
  "pSortOrder": "asc",
  "pPeriodo": "2026",
  "pCodEjecutora": "301280",
  "pCodDGPP": "",
  "pCodSNIP": "",
  "pNomProyecto": ""
}
```

### Respuesta

```json
{
  "d": "{\"rows\":[{\"CODIGO_UNICO\":2325535,\"NOM_INVERSION\":\"MEJORAMIENTO DEL SERVICIO DE SEGURIDAD CIUDADANA EN SAN ISIDRO...\",...},...]}"
}
```

Cada fila trae al menos `CODIGO_UNICO` (el CUI) y `NOM_INVERSION`. La paginación termina
cuando una página viene con menos de `pPageSize` filas.

### Insert en BD

```sql
INSERT INTO proyecto_mef (cui, nombre_inversion, entidad_id, estado)
VALUES (%s, %s, %s, 'NO_VERIFICADO'::estado_proyecto_mef)
ON CONFLICT (cui) DO UPDATE SET
    entidad_id = COALESCE(EXCLUDED.entidad_id, proyecto_mef.entidad_id);
```

En este punto la fila tiene solo el nombre y la entidad. Los datos completos los llena la fase 4.

---

## Fase 4 — Enriquecer cada CUI (4 endpoints en serie)

**Script:** `backend/scripts/04_enriquecer_cui.py`
**Cliente:** `backend/app/clients/mef.py` → 4 métodos
**Duración:** ~4 req × 0.5 seg = 2 seg por CUI

Por cada CUI nuevo, se llaman 4 endpoints distintos.

### 4a. traeDetInvSSI — Datos generales Invierte.pe

```http
POST https://ofi5.mef.gob.pe/invierteWS/Ssi/traeDetInvSSI
Content-Type: application/x-www-form-urlencoded; charset=UTF-8
Referer: https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo={CUI}

id={CUI}&tipo=SIAF
```

**Respuesta para CUI=2171549 (JNJ):**

```json
[{
  "NOMBRE_INVERSION": "MEJORAMIENTO DE LOS SERVICIOS DE SELECCION Y NOMBRAMIENTO...",
  "ENTIDAD": "CONSEJO NACIONAL DE LA MAGISTRATURA",
  "SECTOR": "JUSTICIA",
  "ESTADO": "ACTIVO",
  "SITUACION": "VIABLE",
  "MARCO": "SNIP",
  "MTO_VIABLE": 41117678,
  "COSTO_ACTUALIZADO": 88250571.72,
  "DEV_ACUMULADO": 65768505.07,
  "AVAN_FISICO": 76.85,
  "FEC_INI_EJ": "15/12/13",
  "FEC_FIN_EJ": "30/12/28",
  "MODAL_EJEC": "ADMINISTRACIÓN INDIRECTA - POR CONTRATA",
  "BENEFICIARIO": 24160
}]
```

**Update SQL:**

```sql
UPDATE proyecto_mef SET
    cod_snip          = COALESCE(%s, cod_snip),
    sector            = COALESCE(%s, sector),
    estado            = %s::estado_proyecto_mef,    -- 'ACTIVO' → ACTIVO / 'DESACTIVADO PERMANENTE' → DESACTIVADO_PERMANENTE
    mto_viable        = COALESCE(%s, mto_viable),
    costo_actualizado = COALESCE(%s, costo_actualizado),
    dev_acumulado     = COALESCE(%s, dev_acumulado),
    fec_ini_ejec      = COALESCE(%s, fec_ini_ejec),
    fec_fin_ejec      = COALESCE(%s, fec_fin_ejec),
    avance_fisico_mef = COALESCE(%s, avance_fisico_mef),
    modal_ejec        = COALESCE(%s, modal_ejec),
    beneficiarios     = COALESCE(%s, beneficiarios),
    verificado_mef_en = NOW()
WHERE cui = %s;
```

### 4b. verInfObras2 — Los NOBR_IDs vinculados al CUI

```http
GET https://ofi5.mef.gob.pe/ssi/Ssi/verInfObras2/{CUI}
Accept: application/json
Referer: https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo={CUI}
```

**Respuesta para CUI=2171549:**

```json
[
  {"NOBR_ID": 553414, "COBR_DESCRI": "Ejecución de partidas no ejecutadas y deficientes de la obra: Mejoramiento...", "COPA_DESCRI": "Contrata", "AVANCEFISICO_REAL": 0},
  {"NOBR_ID": 553656, "COBR_DESCRI": "Ejecución de partidas no ejecutadas y deficientes de la obra: Mejoramiento...", "COPA_DESCRI": "Contrata", "AVANCEFISICO_REAL": 0}
]
```

**Lo importante:** un CUI puede tener N NOBR_IDs. Si más de uno y la descripción menciona
"saldo" o "no ejecutadas", se modela como saldos de obra hijos del NOBR original.

**Insert SQL:**

```sql
INSERT INTO obra (nobr_id, cui, descripcion, direccion, modalidad_ejecucion,
                  estado_obra_bulk, avance_fisico_infobras, fuente)
VALUES (%s, %s, %s, %s, %s, %s, %s, 'mef_ssi'::fuente_dato_tipo)
ON CONFLICT (nobr_id) DO UPDATE SET cui = EXCLUDED.cui;

-- Si hay más de 1 obra, marcar las "saldo" como hijas de la mayor avance:
WITH ordered AS (
    SELECT id, nobr_id,
           ROW_NUMBER() OVER (ORDER BY avance_fisico_infobras DESC NULLS LAST, nobr_id ASC) AS rn
    FROM obra WHERE cui = %s
),
padre AS (SELECT id FROM ordered WHERE rn = 1)
UPDATE obra SET obra_padre_id = (SELECT id FROM padre)
WHERE cui = %s
  AND id <> (SELECT id FROM padre)
  AND (descripcion ILIKE '%%saldo%%' OR descripcion ILIKE '%%no ejecutad%%');
```

### 4c. traeContratoSeaceDWH — Contratos SEACE

```http
POST https://ofi5.mef.gob.pe/invierteWS/Ssi/traeContratoSeaceDWH
Content-Type: application/x-www-form-urlencoded

id={CUI}&codsnip={CUI}&vers=v2
```

**Respuesta:** lista de contratos. Para cada uno extrae:

```json
{
  "PROCESO": "LP-SM-5-2024-CS/MPC-1",
  "OBJETO": "EJECUCION DE OBRA",
  "RUC": "20100128218",
  "CONTRATISTA": "CONSTRUCTORA J.Q. S.R.L.",
  "NUM_CONTRATO": "024-2025-MPC",
  "FECHA_SUSCRIPCION": "28/02/2025",
  "MONTO_CONTRATADO": 11581983.20,
  "URL_CONTRATO": "https://..."
}
```

**Insert SQL** (2 tablas — primero el contratista por RUC si no existe):

```sql
INSERT INTO contratista (ruc, razon_social, razon_social_norm)
VALUES (%s, %s, %s)
ON CONFLICT (ruc) DO UPDATE SET razon_social = EXCLUDED.razon_social
RETURNING id;

INSERT INTO procedimiento_seleccion
    (cui, contratista_id, nomenclatura, objeto_contractual,
     numero_contrato, fecha_suscripcion,
     valor_referencial, monto_contratado, url_contrato_pdf, fuente)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'seace_ocds_oece'::fuente_dato_tipo);
```

### 4d. traeListaParalizaPublico — Paralizaciones oficiales

```http
POST https://ofi5.mef.gob.pe/invierte/paraliza/traeListaParalizaPublico
Content-Type: application/x-www-form-urlencoded

id={CUI}
```

**Respuesta:** lista (a veces vacía). Si trae registros:

```json
[{
  "FECHA_PARALIZACION": "15/06/2019",
  "DIAS": 1200,
  "CAUSAL": "Resolución de contrato por incumplimiento del contratista",
  "ESTADO": "vigente"
}]
```

**Insert SQL:**

```sql
INSERT INTO paralizacion_oficial
    (cui, fecha_paralizacion, fecha_reinicio, dias_paralizado, causal, estado, detalle, fuente)
VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, 'mef_ssi'::fuente_dato_tipo);
```

> **Nota:** si el endpoint devuelve vacío, NO es "sin problema" — es "sin registro observado".
> Las paralizaciones reales pueden no estar declaradas formalmente. Por eso esta no es la
> única fuente de "obra paralizada" — la otra es la fase 5 (WFS Contraloría).

---

## Fase 5 — Verificar cada NOBR_ID contra Infobras

**Script:** `backend/scripts/05_verificar_nobr.py`
**Cliente:** `backend/app/clients/infobras.py`
**Duración:** ~3 req × 0.5 seg = 1.5 seg por NOBR_ID
**Output BD:** `obra.lat`/`lon`/`estado_obra_wfs` + tabla `informe_control`

Para cada NOBR_ID descubierto en la fase 4, 3 endpoints.

### 5a. WFS Contraloría — Coordenadas + estado oficial

```http
GET https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/MapaEstadistico/WmsProxy
    ?path=ows
    &service=WFS
    &request=GetFeature
    &typeName=inf_geoobrdef_4326_pt
    &outputFormat=application/json
    &CQL_FILTER=cdp1_codigo='{NOBR_ID}'
```

**Respuesta:** GeoJSON FeatureCollection. Para NOBR_ID=42593 (JNJ):

```json
{
  "type": "FeatureCollection",
  "totalFeatures": 1,
  "features": [{
    "type": "Feature",
    "geometry": {"type": "Point", "coordinates": [-77.0326996, -12.0514081]},
    "properties": {
      "cdp1_codigo": "42593",
      "cdp1_estadoobra": "Paralizada",
      "cdp1_departamento": "LIMA",
      "cdp1_provincia": "LIMA",
      "cdp1_distrito": "SAN ISIDRO"
    }
  }]
}
```

**Importante:** `cdp1_estadoobra` puede valer "En Ejecución", "Paralizada", "Finalizada" o "Suspendida". Es **la fuente más rigurosa** del estado físico de una obra (Contraloría auditando geográficamente). Si `totalFeatures=0`, NO significa "no existe", solo "no está en la capa".

**Update SQL:**

```sql
UPDATE obra SET
    latitud           = %s,
    longitud          = %s,
    geom_fuente       = 'wfs_infobras',
    estado_obra_wfs   = %s,                -- 'Paralizada', 'En Ejecución', etc
    verificado_wfs_en = NOW()
WHERE id = %s;
```

### 5b. Ficha pública HTML

```http
GET https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId={NOBR_ID}
```

Es server-side rendered. Scrape con regex por labels:

```python
labels = ["NOMBRE DE OBRA", "ESTADO DE OBRA", "PORCENTAJE DE AVANCE FÍSICO",
          "FECHA DEL ULTIMO AVANCE", "MONTO DE APROBACIÓN", "CONTRATISTA",
          "FECHA DE INICIO", "FECHA DE FIN", "MODALIDAD",
          "CONTRATO", "FECHA DE CONTRATO"]

for label in labels:
    pattern = re.escape(label) + r"\s*\n\s*([^\n<]+)"
    m = re.search(pattern, html, re.IGNORECASE)
    if m: out[label] = m.group(1).strip()
```

**Update SQL:** llena los campos visibles (`avance_fisico_infobras`, `fecha_ult_avance`,
`monto_aprobacion`, `numero_contrato`, etc.).

### 5c. InformeControl — PDFs de auditoría

```http
GET https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/InformeControl?obraId={NOBR_ID}
```

La tabla de informes no se carga vía XHR — **viene embebida como variable JS** en el HTML:

```javascript
var lInformeControl = [
  {
    "Anio": "2019",
    "NroInforme": "025-2019-OCI/0379-CC",
    "TituloInforme": "PROYECTO: INSTALACIÓN DEL COLECTOR...",
    "TipoServicio": "Servicios de Control Simultáneo",
    "Modalidad": "CONTROL CONCURRENTE",
    "FechaEmision": "2019-08-15",
    "FechaPublicacion": "2019-09-02",
    "RutaPublicacion": "http://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2019CSI037900025&TIPOARCHIVO=RE",
    "RutaInforme": "http://apps8.contraloria.gob.pe/SPIC/srvDownload/ViewPDF?CRES_CODIGO=2019CSI037900025&TIPOARCHIVO=ADJUNTO"
  }
]
```

Extracción con regex sobre el HTML:

```python
m = re.search(r"lInformeControl\s*=\s*(\[.*?\]);", html, re.DOTALL)
informes = json.loads(m.group(1))
```

**Insert SQL** (con dedup por CRES_CODIGO extraído de la URL):

```sql
INSERT INTO informe_control
    (obra_id, anio, nro_informe, titulo, tipo_servicio, modalidad,
     fecha_emision, fecha_publicacion,
     url_pdf_resumen, url_pdf_completo, cres_codigo)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (cres_codigo) DO NOTHING;

UPDATE obra SET existe_informe_control = TRUE WHERE id = %s;
```

> Los PDFs no se bajan al disco — solo se guardan las URLs. El usuario los descarga cuando
> clickea "Ver PDF" en la ficha.

---

## Fase 6 — Compras menores ≤8 UIT (Pentaho/CONOSCE)

**Script:** `scrapers/06_pentaho_ordenes_compra.py` (legacy/scrapers para descubrimiento) + `db/ingest_pentaho_ordenes.py`
**Duración:** ~5 min por mes (XLSX de ~50 MB)
**Output BD:** tabla `orden_compra_servicio` (~100k filas por mes)

### Cómo se descubrió esta fuente (con Playwright)

El portal Pentaho de SEACE no exponía URLs públicas directamente. Tuvimos que abrirlo con
Playwright y observar las requests:

```http
GET https://bi.seace.gob.pe/pentaho/api/repos/:public:portal:dataset.html/content?userid=public&password=key&pagina=ordenes
```

El HTML renderizado contiene `<a>` con URLs codificadas en base64 que apuntan al CDN real
de OECE. Decodificando una:

```
aHR0cHM6Ly9jb25vc2NlLm9zY2UuZ29iLnBlL2J1c2NhZG9yL2Fzc2V0cy82N2FlNmM0YS9yZXBvcnRlcy9vcmRlbmVzLzIwMjYvQ09OT1NDRV9PUkRFTkVTQ09NUFJBQUJSSUwyMDI2XzAueGxzeA==

→ https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/ordenes/2026/CONOSCE_ORDENESCOMPRAABRIL2026_0.xlsx
```

### Patrón de URL (estable)

```
https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/ordenes/{YEAR}/CONOSCE_ORDENESCOMPRA{MES_MAYUS}{YEAR}_0.xlsx
```

Donde `MES_MAYUS` ∈ `{ENERO, FEBRERO, MARZO, ABRIL, MAYO, JUNIO, JULIO, AGOSTO, SETIEMBRE, OCTUBRE, NOVIEMBRE, DICIEMBRE}`.

### Procesamiento del XLSX

Columnas del archivo:

```
entidad · ruc_entidad · departamento_entidad · tipoorden · nro_de_orden ·
orden · descripcion_orden · objetocontractual · estadocontratacion ·
tipodecontratacion · monto_total_orden_original · moneda ·
ruc_contratista · nombre_razon_contratista · fecha_emision · fecha_registro · ...
```

### Filtros aplicados

```python
mask = (
    df["departamento_entidad"].str.upper().str.strip().isin(["LIMA", "CALLAO"])
    & df["tipodecontratacion"].str.lower().str.contains("hasta 8 uit", na=False)
)
sub = df[mask]
```

### Insert SQL (COPY masivo para velocidad)

```python
with cur.copy("""
    COPY orden_compra_servicio
        (numero_orden, tipo, entidad_id, contratista_id,
         monto_soles, fecha_emision, descripcion, url_documento, fuente)
    FROM STDIN
""") as copy:
    for r in rows_to_insert:
        copy.write_row(r)
```

> **Importante:** las entidades del archivo pueden no existir aún en `entidad` (la fase 1
> solo cubrió las del PTE). Antes de cada INSERT, hace `INSERT INTO entidad ... ON CONFLICT
> DO NOTHING` por el nombre normalizado. Lo mismo con contratistas por RUC.

---

## Fase 7 — Generar señales con SQL determinístico

**Script:** `backend/scripts/06_generar_senales.py`
**Duración:** <1 seg
**Output BD:** tabla `senal_revision`

A diferencia de las fases anteriores, esta NO consulta APIs externas. Es **SQL puro sobre las
tablas ya pobladas**. Cada señal tiene una fórmula auditable visible en la UI.

### Señal 1 — Sobrecosto

```sql
INSERT INTO senal_revision (tipo, cui, entidad_id, titulo, resumen, score, formula, evidencia)
SELECT
    'sobrecosto'::tipo_senal,
    p.cui, p.entidad_id,
    'Sobrecosto del ' || ROUND(100.0*(p.costo_actualizado - p.mto_viable)/p.mto_viable, 1) || '%',
    ...
    'pct = 100 * (costo_actualizado - mto_viable) / mto_viable; umbral > 30%',
    jsonb_build_object('cui', p.cui, 'mto_viable', p.mto_viable,
                       'costo_actualizado', p.costo_actualizado,
                       'sobrecosto_pct', ROUND(100.0*(p.costo_actualizado - p.mto_viable)/p.mto_viable, 2))
FROM proyecto_mef p
WHERE p.mto_viable > 0 AND p.costo_actualizado > p.mto_viable * 1.30;
```

### Señal 2 — Discrepancia de avance

```sql
WHERE ABS(p.avance_fisico_mef - o.avance_fisico_infobras) > 10
```

### Señal 3 — Paralización confirmada por Contraloría

```sql
WHERE o.estado_obra_wfs = 'Paralizada'
```

Esta es la más rigurosa: viene del WFS oficial de Contraloría.

### Señal 4 — Proyecto desactivado en MEF

```sql
WHERE p.estado = 'DESACTIVADO_PERMANENTE'
```

### Señal 5 — Saldos pendientes

```sql
WHERE EXISTS (SELECT 1 FROM obra h WHERE h.obra_padre_id = padre.id)
```

### Señal 6 — Concentración compras ≤8 UIT

```sql
WITH por_entidad AS (
    SELECT entidad_id, SUM(monto_soles) AS monto
    FROM orden_compra_servicio
    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
    GROUP BY entidad_id HAVING COUNT(*) >= 20
),
por_ruc_ent AS (
    SELECT entidad_id, contratista_id, COUNT(*)::int AS n_ruc, SUM(monto_soles) AS monto_ruc
    FROM orden_compra_servicio
    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
      AND contratista_id IS NOT NULL
    GROUP BY entidad_id, contratista_id HAVING COUNT(*) >= 5
)
SELECT ... WHERE (100.0 * r.monto_ruc / pe.monto) >= 20
```

---

## Apéndice: caso JNJ end-to-end

El caso que descubrió toda la arquitectura. Trazado completo:

### 1. La entidad

```
PTE → id_entidad=44 → nombre "JUNTA NACIONAL DE JUSTICIA" → IdUE=300057
```

### 2. GetEjecucion con IdUE=300057

Una de las filas devueltas: `CODIGO_UNICO=2171549`, `NOM_INVERSION="MEJORAMIENTO DE LOS SERVICIOS DE SELECCION..."`.

### 3. traeDetInvSSI con CUI=2171549

```json
{
  "ESTADO": "ACTIVO",
  "MTO_VIABLE": 41117678,
  "COSTO_ACTUALIZADO": 88250571.72,
  "DEV_ACUMULADO": 65768505.07,
  "AVAN_FISICO": 76.85,
  "FEC_INI_EJ": "15/12/13",
  "FEC_FIN_EJ": "30/12/28"
}
```

**MEF la considera ACTIVA**, con sobrecosto del 114%, devengado 75% del costo actualizado, terminando en 2028.

### 4. verInfObras2 con CUI=2171549

Devuelve **2 NOBR_IDs**: 553414 y 553656, ambos con `AVANCEFISICO_REAL=0` y descripción
"Ejecución de partidas no ejecutadas y deficientes...".

Eso significa **saldos de obra** — el contrato original quebró. El NOBR_ID original
(42593) no aparece aquí porque MEF lo desvinculó cuando se resolvió el contrato.

### 5. WFS para NOBR_ID=42593 (la obra física)

```json
{"estado": "Paralizada", "coords": [-77.0326996, -12.0514081]}
```

**Contraloría WFS confirma: PARALIZADA**, en pleno San Isidro.

### 6. WFS para NOBR_ID 553414 y 553656

`totalFeatures: 0` — los saldos aún no están en la capa geográfica (son contratos
nuevos).

### 7. InformeControl para NOBR_ID=42593

Devuelve 5 informes de Contraloría:

```
2023 · 025-2023-CG/MPROY-AC  · Auditoría de Cumplimiento  (3 hallazgos)
2022 · 089-2022-CG/MPROY-AC  · Auditoría de Cumplimiento  (5 hallazgos)
2019 · CC-2019-156           · Control Concurrente         (2 hallazgos)
...
```

Esto explica por qué la obra se cortó y MEF la sigue marcando "ACTIVA" en su sistema.

### 8. Señales generadas

Tras correr `06_generar_senales.py` sobre esta obra:

- `sobrecosto` — score 114.6 — fórmula `100*(88.25 - 41.12)/41.12`
- `paralizacion_real` — score 100 — fórmula `estado_obra_wfs='Paralizada'`
- `saldos_pendientes` — score 80 — fórmula `obra padre tiene N saldos hijos`

3 señales activas para esta obra, todas con evidencia JSONB exportable.

---

## Anti-patrones aprendidos

Cosas que parecían buena idea y NO lo son:

| Anti-patrón | Por qué no |
|---|---|
| Usar Infobras bulk como maestro (XLSX masivo) | Solo refleja lo que la entidad reporta. No detecta saldos de obra ni desactivaciones MEF. |
| Confiar en `Existe Paralización=SI` del bulk | No se actualiza. Hay obras al 99% avance marcadas "paralizada" desde 2017. |
| Tomar el `monto_aprobacion` de Infobras como monto del proyecto | Es el monto del contrato original. El monto real del proyecto es `costo_actualizado` de MEF. |
| Asumir 1 CUI = 1 obra física | Falso. Un CUI puede tener 1..N NOBR_IDs (original + saldos). |
| Bajar OCDS de OECE como fuente principal de contratos | Funciona pero está incompleta. `traeContratoSeaceDWH` de MEF es más limpia para vincular a CUI. |
| Scrapear los PTE municipales individuales | No agrega valor. Los PTE son wrappers del mismo Infobras. La verdadera fuente independiente es MEF SIAF. |
| Generar señales al ingestar (durante el INSERT) | Las señales necesitan ver el cruce final entre fuentes. Se generan al final con SQL puro. |

---

## Reproducir todo desde cero

```powershell
# 1. Crear BD vacía con estructura
cd db
python setup.py

# 2. Catálogo de entidades (~30 seg, no usa MEF, solo PTE)
cd ..\backend
python scripts/01_descubrir_entidades.py

# 3. Mapear IdUE para entidades MVP (~1 min)
python scripts/02_mapear_idue.py

# 4. Descubrir CUIs por UE para el periodo vigente (depende de cuántas entidades)
python scripts/03_descubrir_cuis.py --periodo 2026 --solo-mvp

# 5. Enriquecer cada CUI con los 4 endpoints (~2 seg por CUI)
python scripts/04_enriquecer_cui.py

# 6. Verificar cada NOBR_ID contra Infobras (~1.5 seg por NOBR)
python scripts/05_verificar_nobr.py

# 7. Generar señales (SQL puro, <1 seg)
python scripts/06_generar_senales.py
```

O si querés la BD ya con los datos del demo:

```powershell
cd db
python restore_demo.py    # Aplica el snapshot pg_dump en seeds/demo_snapshot.sql
```

---

## Diagrama final de tablas pobladas tras todo el flujo

```
distrito          ←  seed inicial             (50 filas MVP)
fuente_dato       ←  seed inicial             (13 fuentes catalogadas)
entidad           ←  fase 1 + 2               (~2,300 filas)
proyecto_mef      ←  fase 3 + 4a              (CUIs con datos completos)
obra              ←  fase 4b + 5a + 5b        (NOBR_IDs con coords + estado WFS + datos ficha)
procedimiento_seleccion  ←  fase 4c           (contratos SEACE)
contratista       ←  fase 4c + 6              (RUCs únicos)
paralizacion_oficial     ←  fase 4d           (paralizaciones declaradas MEF)
informe_control   ←  fase 5c                  (PDFs Contraloría)
orden_compra_servicio   ←  fase 6             (compras ≤8 UIT mensuales)
senal_revision    ←  fase 7                   (SQL determinístico final)
explicacion_ia    ←  on-demand                (cache de explicaciones LLM)
```
