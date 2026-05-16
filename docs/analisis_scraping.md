# Análisis de scraping — Obras Cerca

**Estado:** verificado con `curl` real contra cada endpoint el 2026-05-15. Todas las URLs aquí devolvieron 200 + payload válido salvo donde se indica lo contrario.

---

## 1. Contraloría — Obras Paralizadas (gob.pe) ✅ Trivial

**Patrón CDN estable:**

```
https://cdn.www.gob.pe/uploads/document/file/{ID}/{slug}.{ext}?v={timestamp}
```

**Archivos del informe diciembre 2025 (extraídos por regex del HTML):**

| ID | Tipo | URL |
|---|---|---|
| 9416533 | PDF informe (996 KB) | `…/9416533/7715417-informe-de-obras-publicas-paralizadas-en-el-territorio-nacional-a-diciembre-2025f.PDF?v=1770658615` |
| 9416534 | Anexo 1 XLSX | `…/9416534/7715417-anexo-n-01-principales-obras-paralizadas-por-departamento-diciembre-2025.XLSX?v=1770658616` |
| 9416535 | Anexo 2 XLSX | `…/9416535/7715417-anexo-n-02-reporte-obras-paralizadas-diciembre-2025-vf.XLSX?v=1770658617` |
| 9416536 | Anexo 3 XLSX | `…/9416536/7715417-anexo-n-03-reporte-de-servicios-de-control-a-obras-paralizadas-diciembre-2025.XLSX?v=1770658617` |

**Flujo:**

1. `GET` al landing del informe con `User-Agent` de navegador real.
2. Regex `https://cdn\.www\.gob\.pe/uploads/document/file/[^"?]+\?v=\d+` sobre el HTML.
3. `GET` directo al CDN.

**Bonus:** la colección 18230 lista todos los informes trimestrales desde 2022 con URLs estables `/institucion/contraloria/informes-publicaciones/{id}-{slug}`. Permite armar serie histórica.

**Bloqueador:** gob.pe responde **HTTP 418** al `User-Agent` por defecto de `python-requests` y al WebFetch tool. Hay que mandar UA de Chrome/Firefox real. Sin captcha, sin Cloudflare challenge.

**Script:** `scrapers/01_contraloria_paralizadas.py`

---

## 2. Infobras DataSets (Contraloría) ✅ Endpoint público directo

**Endpoint extraído de `Archivo.js` línea 189:**

```
GET https://infobras.contraloria.gob.pe/InfobrasWeb/Archivo/DownloadFile
    ?filename={filename}
    &name={name}
    &contentType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    &extension=.xlsx
```

**Filenames públicos (data-filename del HTML, cambian con cada actualización):**

| filename | Última actualización |
|---|---|
| `DataSet-Obras-Paralizadas 12-03-2025` | 2025-03-12 |
| `DataSet-Obras-Publicas 15-05-2026` | 2026-05-15 |
| `DataSet-Obras-en-reconstruccion-con-Cambios 15-05-2026` | 2026-05-15 |
| `DataSet-Asociaciones-Publico-Privadas 15-05-2026` | 2026-05-15 |

**Probado:** descargué 989 KB de XLSX válido (firma `Microsoft Excel 2007+`) sin auth, sin cookies, sin token.

**Flujo del script:**

1. `GET /InfobrasWeb/DataSets` y regex `data-filename="([^"]+)"` para descubrir los 4 filenames vigentes (no hardcodear la fecha del filename).
2. Para cada filename, llamar al endpoint `Archivo/DownloadFile` con `extension=.xlsx`.

**Bonus — ficha individual:**

- `GET /InfobrasWeb/Mapa/Sumario?ObraId={N}` devuelve 800 KB+ de HTML server-side (Razor/MVC, no SPA). Datos parseables con BeautifulSoup.

**Script:** `scrapers/02_infobras_datasets.py` y `scrapers/03_infobras_ficha.py`

---

## 3. OCDS Perú — Portal Contrataciones Abiertas ✅ La joya

API REST JSON pública sin auth. Rutas extraídas del bundle Angular `main.eb02d59670b1851d.js`:

```
GET /api/v1/files                                       → catálogo bulk
GET /api/v1/files/{page}/?page=N&paginateBy=M&source=X
GET /api/v1/file/{source}/{type}/{year}/{month}/        → bulk archive
GET /api/v1/releases?page=N&paginateBy=M                → OCDS Release Package
GET /api/v1/release/{id}
GET /api/v1/release/{sourceId}/{tenderId}
GET /api/v1/records
GET /api/v1/record/{ocid}
GET /api/v1/record/{sourceId}/{tenderId}
```

**Verificado en respuesta real:**

- `/api/v1/files`: catálogo de archivos mensuales con `source` ∈ {`seace_v1`, `seace_v2`, `seace_v3`} en formatos `csv`, `csv_es`, `xlsx`, `xlsx_es`, `json`, `sha`. Cobertura hasta mayo 2026 inclusive.
- `/api/v1/releases?page=1&paginateBy=2`: 74 KB de OCDS Release Package 1.1 con extensiones oficiales (`currencyName`, `department`, `dataSegmentation`, `releaseSource`, `exchangeRate`, `contract_completion`).

**Limitación estructural ya documentada:** OCDS Perú **no** incluye contratos sin procedimiento (menores a 3/8/9 UIT). Para ≤8 UIT, ir por DataSet de Infobras o por CONOSCE/Pentaho.

**Scripts:** `scrapers/04_ocds_files_catalog.py` y `scrapers/05_ocds_releases.py`

---

## 4. OECE CONOSCE — Pentaho ⚠️ Bloqueado sin headless browser

**Estado real probado:**

- `https://bi.seace.gob.pe/pentaho/api/repos/:public:portal:datosabiertos.html/content?userid=public&password=key` devuelve un shell HTML de 3 KB que construye el dashboard con `renderhtmlv2.js` desde el cliente.
- Llamadas directas a `…/plugin/pentaho-cdf-dd/api/resources/public/portal/json/datasets.json` → **HTTP 401**.
- El `userid=public&password=key` autentica el HTML público, pero los XHR internos que carga el JS requieren cookies de sesión Pentaho que el shell crea durante el render.

**Qué resolvería Playwright:** sí, completamente. Pentaho es exactamente el caso de uso de Playwright:

1. Lanzar el portal con `page.goto(...)`.
2. Esperar a que `renderhtmlv2.js` haga sus llamadas.
3. Interceptar las requests con `page.on("request")` para capturar el endpoint JSON real (la URL final que el JS arma con la cookie de sesión).
4. Una vez identificado el endpoint + el header `Cookie` que sí autoriza, replicarlo con `requests` para el resto del scraping.

**Sustituto que ya tienes:** la API OCDS Perú (sección 3) cubre los mismos datasets SEACE V1/V2/V3 con datos estructurados, sin necesidad de Pentaho. Pentaho solo aporta el "PAC" (Plan Anual de Contrataciones) y "Órdenes ≤8 UIT" que no están en OCDS.

**Decisión recomendada:** dejar Pentaho como link humano "ver fuente oficial". Si se necesitan las Órdenes ≤8 UIT vía Pentaho, usar Playwright.

---

## 5. INEI — Datasets de enriquecimiento ⚠️ Sin API; Playwright facilita los formularios

**Hallazgo real:**

- `https://www.gob.pe/institucion/inei/informes-publicaciones/2727403-catalogo-de-base-de-datos-2026` → solo PDFs catálogo (ES + EN). No descargas estructuradas desde aquí.
- Los datasets reales viven en `https://proyectos.inei.gob.pe/microdatos/`. Cada uno (ENAHO, RNM, Mapa de Pobreza, Centros Poblados) tiene una página con formulario que devuelve ZIP. Los IDs internos son estables, pero el flujo de selección no es REST.

**Qué resolvería Playwright:** parcialmente útil. Los formularios ASP.NET de microdatos exigen reproducir `__VIEWSTATE` + `__EVENTVALIDATION` + clic en selectores encadenados. Con Playwright es 30 líneas; con `requests` es batalla de hidden fields.

**Decisión pragmática para 72h:**

- RNM 2025 + Mapa de Pobreza 2018 + Centros Poblados 2025 = 3 datasets que se bajan **una sola vez** en preparación del hackathon. Bajada manual de 30 min (clic en navegador, guardar ZIP) es más rápido que escribir 3 scrapers de un solo uso.
- Si se requiere refresco automático periódico (no es el caso del hackathon), Playwright es el camino.

---

## 6. SEACE Buscador Público ❌ JSF stateful — no scrapear

`buscadorPublico.xhtml` es JSF/PrimeFaces con `javax.faces.ViewState` y `javax.faces.partial.ajax`. Cada búsqueda exige:

1. `GET` inicial para capturar el `ViewState`.
2. `POST` con todos los hidden fields y el ViewState actualizado.
3. Sesión persistente con cookies `JSESSIONID`.
4. La paginación dispara nuevos `ViewState` cycles.

Factible (`requests` con `Session` o Playwright) pero **innecesario**: la API OCDS Perú cubre lo mismo en estructura limpia.

**Decisión del MD maestro (correcta):** deep-link de salida solamente.

---

## 7. MEF Consulta Amigable ❌ Misma estructura que SEACE

Tabla pivote JSF con drill-down stateful. Mismo perfil. Saltar.

---

## Resumen ejecutable

| # | Fuente | Esfuerzo | Cobertura | Script |
|---|---|---|---|---|
| 1 | Infobras DataSets | 20 min | 4 XLSX (obras públicas, paralizadas, reconstrucción, APPs) | `02_infobras_datasets.py` |
| 2 | Contraloría informe dic-2025 | 15 min | 3 XLSX + 1 PDF | `01_contraloria_paralizadas.py` |
| 3 | OCDS API `/files` | 30 min | Bulk CSV/XLSX/JSON mensual SEACE V1+V2+V3 | `04_ocds_files_catalog.py` |
| 4 | OCDS API `/releases` | 1 h | OCDS por proceso individual | `05_ocds_releases.py` |
| 5 | Infobras ficha | On-demand | HTML completo de una obra | `03_infobras_ficha.py` |
| 6 | INEI RNM / Mapa Pobreza | Manual 30 min | 3 ZIPs/XLSX | — (manual o Playwright) |
| 7 | Pentaho órdenes ≤8 UIT | Necesita Playwright | Órdenes que no están en OCDS | — (Playwright pendiente) |
| 8 | SEACE / MEF | N/A | — | Solo deep-link de salida |

---

## Lo que cambia si agregas Playwright al stack

| Caso | Sin Playwright | Con Playwright |
|---|---|---|
| Pentaho órdenes ≤8 UIT | ❌ 401 en los JSON internos | ✅ Captura el endpoint real y la cookie de sesión |
| INEI microdatos automatizado | 🟡 Reproducir VIEWSTATE manualmente | ✅ Form submit con 30 líneas |
| SEACE buscador (si lo necesitas) | 🟡 Sesión JSF a mano | ✅ Trivial |
| Infobras descubrimiento de filenames nuevos | ✅ Ya funciona | ✅ Igual |
| Contraloría CDN | ✅ Ya funciona | ✅ Igual |
| OCDS API | ✅ Ya funciona | ✅ Igual |

**Recomendación honesta:** instala Playwright solo si vas a perseguir órdenes ≤8 UIT desde Pentaho. Las 3 fuentes principales (Contraloría, Infobras, OCDS) ya están cubiertas con `requests` puro.

```
pip install playwright
playwright install chromium
```
