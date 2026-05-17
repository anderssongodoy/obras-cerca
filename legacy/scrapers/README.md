# Scrapers — Obras Cerca

Cinco scripts independientes. Cada uno cubre una fuente y deja la salida en
`scrapers/data/raw/<fuente>/`. Pensados para correrse el día -1 del hackathon
y dejar todo en disco; la transformación a Postgres es otro paso.

## Setup

```powershell
cd C:\Users\uu\Desktop\Investigación\scrapers
pip install -r requirements.txt
```

## Scripts

| Script | Qué hace | Tiempo aprox |
|---|---|---|
| `01_contraloria_paralizadas.py` | Baja 3 XLSX + PDF del informe Contraloría dic-2025 (o el slug que pases) | <1 min |
| `02_infobras_datasets.py` | Descubre y baja los 4 DataSets bulk de Infobras (~5-50 MB cada uno) | 1-3 min |
| `03_infobras_ficha.py` | Guarda HTML server-side de fichas individuales por ObraId | <1 min por ficha |
| `04_ocds_files_catalog.py` | Lista el catálogo bulk OCDS, opcionalmente descarga mensuales | 1 min listar / horas si bajas todo |
| `05_ocds_releases.py` | Recorre `/api/v1/releases` y guarda NDJSON | Depende de páginas |

## Ejemplos rápidos

```powershell
# 1) Informe Contraloría dic-2025 (default)
python 01_contraloria_paralizadas.py

# Listar todos los informes históricos de la colección
python 01_contraloria_paralizadas.py --coleccion

# Otro informe (ej. dic-2024)
python 01_contraloria_paralizadas.py --slug 6555301-informe-de-obras-paralizadas-en-el-territorio-nacional-a-diciembre-2024
```

```powershell
# 2) Todos los DataSets Infobras
python 02_infobras_datasets.py

# Solo el de paralizadas
python 02_infobras_datasets.py --only Paralizadas
```

```powershell
# 3) Fichas individuales
python 03_infobras_ficha.py 52903 52904 52905
```

```powershell
# 4) Catálogo OCDS (solo listar)
python 04_ocds_files_catalog.py

# Bajar todos los xlsx_es de seace_v3 del 2025
python 04_ocds_files_catalog.py --download --source seace_v3 --year 2025 --format xlsx_es
```

```powershell
# 5) Releases OCDS (2 páginas de prueba)
python 05_ocds_releases.py --max-pages 2

# Producción: todas (puede tomar mucho)
python 05_ocds_releases.py --max-pages 0 --page-size 500
```

## Fuentes que NO scrapean estos scripts

- **Pentaho CONOSCE** (`bi.seace.gob.pe`) — los JSON internos requieren cookies de sesión que solo se obtienen ejecutando el JS del portal. Necesita Playwright. Ver `analisis_scraping.md` § 4.
- **INEI microdatos** — formularios ASP.NET con VIEWSTATE. Bajada manual recomendada para 3 datasets de un solo uso, o Playwright si se quiere automatizar.
- **SEACE buscador** y **MEF Consulta Amigable** — JSF stateful; documentados como "solo deep-link de salida" en el MD maestro.

## Notas técnicas

- gob.pe responde **HTTP 418** al UA por defecto de `requests`. `common.py` ya inyecta UA de Chrome real.
- Se usa `urllib3.util.retry.Retry` con backoff exponencial para GET/HEAD ante 429/5xx.
- Los archivos grandes (Infobras, OCDS bulk) se bajan con `stream=True` y chunks de 32 KB.
- `out_dir(...)` crea `data/raw/<fuente>/` idempotentemente. Los scripts saltan archivos ya bajados (chequea tamaño > 0).
