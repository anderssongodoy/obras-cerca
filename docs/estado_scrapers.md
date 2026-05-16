# Estado de los scrapers — Obras Cerca

**Última verificación:** 2026-05-15. Todos los scripts ejecutados contra los endpoints reales y se confirmó descarga válida.

---

## Estructura creada

```
C:\Users\uu\Desktop\Investigación\
├── obras_cerca_proyecto_maestro.md   ← documento maestro (existía)
├── analisis_scraping.md              ← análisis técnico por fuente
├── estado_scrapers.md                ← este archivo
└── scrapers\
    ├── README.md                     ← cómo correrlos
    ├── requirements.txt              ← solo requests
    ├── common.py                     ← sesión con UA Chrome + retries + stream-download
    ├── 01_contraloria_paralizadas.py ← gob.pe → CDN
    ├── 02_infobras_datasets.py       ← 4 bulks Infobras
    ├── 03_infobras_ficha.py          ← HTML por ObraId
    ├── 04_ocds_files_catalog.py      ← catálogo OCDS + descarga mensual
    ├── 05_ocds_releases.py           ← NDJSON paginando OCDS
    └── data\raw\                     ← salida de los scrapers
```

---

## Pruebas en vivo (no especulación)

| # | Script | Comando probado | Resultado real |
|---|---|---|---|
| 01 | `01_contraloria_paralizadas.py` | `--coleccion` | Listó 20+ informes históricos desde 2022 |
| 01 | `01_contraloria_paralizadas.py` | (default) | PDF informe **995,824 B** + 3 XLSX (**53,111 B + 1,481,264 B + 2,555,053 B**) — coincide exacto con los tamaños del MD maestro ("53KB, 1.5MB, 2.6MB") |
| 02 | `02_infobras_datasets.py` | `--only Paralizadas` | Descubrió 4 datasets vigentes, bajó **989,606 B** de XLSX válido |
| 03 | `03_infobras_ficha.py` | `52903` | Bajó **827,769 B** de HTML server-side de la ficha |
| 04 | `04_ocds_files_catalog.py` | (default) | Listó 5 entradas más recientes (seace_v3 ene-may 2026), escribió `files_catalog.json` |
| 05 | `05_ocds_releases.py` | `--max-pages 1 --page-size 5` | Bajó **20 releases** OCDS en NDJSON (el endpoint ignora `paginateBy` < 20) |

**Bytes en disco tras pruebas:** 5.08 MB Contraloría + 989 KB Infobras bulk + 828 KB ficha + JSON/NDJSON OCDS. Todo en `scrapers\data\raw\<fuente>\`.

---

## Lo que NO logré scrapear y qué falta

### A) Pentaho CONOSCE — `bi.seace.gob.pe` → Playwright SÍ resuelve

**Bloqueador real verificado:**
- El portal `…/pentaho/api/repos/:public:portal:datosabiertos.html/content?userid=public&password=key` devuelve un shell HTML de 3 KB.
- El shell ejecuta `renderhtmlv2.js` que hace XHRs internos del tipo `/plugin/pentaho-cdf-dd/api/resources/.../json/datasets.json` → estos devuelven **HTTP 401** sin la cookie de sesión Pentaho.
- El query `?userid=public&password=key` autentica el HTML público pero **no** los XHRs internos. La cookie se crea durante el render del JS, no en la primera respuesta.

**Por qué Playwright lo resuelve:**

```python
# Idea del scraper que reemplaza a Pentaho directo
page = await browser.new_page()
captured_requests = []
page.on("request", lambda req: captured_requests.append({
    "url": req.url,
    "method": req.method,
    "headers": dict(req.headers),
}))
await page.goto(
    "https://bi.seace.gob.pe/pentaho/api/repos/"
    ":public:portal:datosabiertos.html/content?userid=public&password=key"
)
await page.wait_for_load_state("networkidle")
# captured_requests ahora tiene:
#   - la URL JSON real que el JS construye
#   - el header Cookie que sí autoriza
# Una vez conocidos, replico esos headers con requests para el bulk scrape
```

**Por qué importa para el proyecto:**
- Pentaho aporta **PAC** (Plan Anual de Contrataciones) y especialmente **Órdenes de Compra y Servicios ≤8 UIT**.
- Las Órdenes ≤8 UIT son el corazón de la sección 4.3 del MD maestro (vista de contratista con análisis de concentración).
- Sin esto, esa funcionalidad queda **coja**: no hay cómo calcular "X% de compras menores de esta entidad".

**Costo de agregar Playwright:**
```powershell
pip install playwright
playwright install chromium
```
~150 MB de descarga (Chromium headless) + ~10 min de programación del scraper.

### B) INEI microdatos — `proyectos.inei.gob.pe/microdatos` → Playwright opcional

**Bloqueador real:** formularios ASP.NET con `__VIEWSTATE` + `__EVENTVALIDATION` + selectores encadenados. Reproducible con `requests` pero costoso por dataset.

**Datasets que importan:**
- Registro Nacional de Municipalidades 2025
- Mapa de Pobreza 2018
- Directorio Centros Poblados 2025

**Mi recomendación honesta:** son 3 archivos que se bajan **una sola vez** en preparación del hackathon. **30 min de clics manuales el miércoles 13** es objetivamente más rápido que escribir 3 scrapers de un solo uso. Solo automatizar si requieres refresco periódico (no es el caso del hackathon).

### C) SEACE buscador / MEF Consulta Amigable → No hace falta

JSF stateful con `ViewState` cycles. **La API OCDS Perú (script 04 + 05) ya cubre todos los procedimientos** SEACE V1/V2/V3 en formato limpio. El MD maestro ya decide "deep-link de salida solamente" — la decisión es correcta y no la cambio.

---

## Mapa de cobertura final

| Fuente del MD §8.2 | Cubierta hoy | Por qué |
|---|---|---|
| Contraloría Obras Paralizadas | ✅ Script 01 | gob.pe + CDN directo, sin auth |
| OECE CONOSCE / Pentaho | ⚠️ Parcial vía OCDS API | Falta Órdenes ≤8 UIT — requiere Playwright |
| Portal Contrataciones Abiertas OCDS | ✅ Scripts 04 + 05 | API REST pública, OCDS 1.1 |
| Infobras DataSets bulk | ✅ Script 02 | Endpoint público `/Archivo/DownloadFile` |
| Infobras ficha individual | ✅ Script 03 | HTML server-side parseable |
| INEI RNM / Mapa Pobreza | ⚠️ Manual | 30 min de clics > escribir scraper de un solo uso |
| Plataforma Datos Abiertos | ✅ Indirecto | Las fuentes que importan ya están cubiertas |
| SEACE Buscador Público | ❌ Deep-link solo | Cubierto por OCDS API |
| MEF Consulta Amigable | ❌ Deep-link solo | Decisión del MD maestro |

---

## Próxima decisión a tomar

**¿Instalamos Playwright para cubrir Pentaho?**

- ✅ **Sí**, si quieres que la **vista de contratista con análisis de concentración ≤8 UIT** (§4.3 del MD maestro) tenga datos reales en la demo.
- ❌ **No**, si decides bajar el alcance de esa funcionalidad o limitarla a procedimientos OCDS (≥8 UIT) donde no aplica la lógica de "compras menores concentradas".

Si la respuesta es sí, el siguiente entregable es `scrapers/06_pentaho_ordenes.py` que:
1. Lanza Chromium headless con Playwright.
2. Navega al portal Pentaho y espera `networkidle`.
3. Intercepta los XHRs para descubrir la URL real del listado de Órdenes ≤8 UIT.
4. Captura la cookie de sesión.
5. Itera el bulk download con `requests` reutilizando esa cookie.
6. Guarda en `data/raw/pentaho_ordenes/`.
