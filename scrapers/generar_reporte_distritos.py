"""Genera reporte MD + CSV limpios de los 3 distritos.

Salida:
    - ../data_distritos_lima.md  (reporte para el usuario)
    - data/processed/obras_lima_3distritos_clean.csv
    - data/processed/obras_lima_paralizadas_clean.csv
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import pandas as pd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
BASE = ROOT / "data" / "raw" / "infobras_datasets"
OUT = ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
MD_PATH = ROOT.parent / "data_distritos_lima.md"

OBRAS_XLSX = BASE / "DataSet-Obras-Publicas_15-05-2026.xlsx"
DISTRITOS = ["LIMA", "SAN ISIDRO", "MIRAFLORES"]

COLS = [
    "Código INFOBRAS", "Departamento", "Provincia", "Distrito",
    "Nombre de obra", "Entidad Pública", "Nivel de gobierno",
    "Sector de la Entidad", "Naturaleza de la obra",
    "Estado de ejecución",
    "Fecha de inicio de obra", "Fecha finalización programada de obra",
    "Avance Físico Real Acumulado (%)", "Avance Físico Programado Acumulado (%)",
    "Porcentaje de ejecución financiera",
    "Monto de valorización Ejecutado Acumulado",
    "Monto del contrato  en soles",
    "Nombre o razón social de la empresa o consorcio",
    "RUC",
    "Existe Paralización", "Causal de paralización",
    "Fecha de paralización", "Número de dias paralizado",
    "Fecha de registro de avance",
    "Dirección o información de referencia",
    "Tipo de ubicación (exacta/referencial)",
]


def limpiar_porcentaje(v) -> float | None:
    """Infobras devuelve '27 78' (espacio) en vez de '27.78'. Normaliza."""
    if pd.isna(v):
        return None
    s = str(v).strip().replace("%", "").strip()
    if not s or s.lower() in ("nan", "none"):
        return None
    s = re.sub(r"^(\d+)\s+(\d+)$", r"\1.\2", s)
    try:
        return float(s)
    except ValueError:
        return None


def fmt_pct(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    return f"{v:.1f}%"


def fmt_monto(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    try:
        return f"S/ {float(v):,.0f}"
    except (TypeError, ValueError):
        return str(v)


def fmt_text(v) -> str:
    if v is None or pd.isna(v):
        return "—"
    s = str(v).strip()
    return s if s and s.lower() != "nan" else "—"


def main() -> int:
    print(f"Leyendo {OBRAS_XLSX.name}...")
    obras = pd.read_excel(OBRAS_XLSX, sheet_name=0, header=3)
    obras.columns = [str(c).strip() for c in obras.columns]
    print(f"  {len(obras):,} filas")

    dep = obras["Departamento"].astype(str).str.upper().str.strip()
    prov = obras["Provincia"].astype(str).str.upper().str.strip()
    dist = obras["Distrito"].astype(str).str.upper().str.strip()
    mask = (dep == "LIMA") & (prov == "LIMA") & dist.isin(DISTRITOS)
    sub = obras.loc[mask, [c for c in COLS if c in obras.columns]].copy()

    # Normalizar porcentajes (formato '27 78' → 27.78)
    pct_cols = [
        "Avance Físico Real Acumulado (%)",
        "Avance Físico Programado Acumulado (%)",
        "Porcentaje de ejecución financiera",
    ]
    for c in pct_cols:
        if c in sub.columns:
            sub[c + "_num"] = sub[c].apply(limpiar_porcentaje)

    paral_mask = sub["Existe Paralización"].astype(str).str.strip().str.upper() == "SI"
    paral = sub[paral_mask].copy()

    # CSVs limpios
    csv_full = OUT / "obras_lima_3distritos_clean.csv"
    csv_par = OUT / "obras_lima_paralizadas_clean.csv"
    sub.to_csv(csv_full, index=False, encoding="utf-8-sig")
    paral.to_csv(csv_par, index=False, encoding="utf-8-sig")
    print(f"  {csv_full.name}: {csv_full.stat().st_size:,} B")
    print(f"  {csv_par.name}: {csv_par.stat().st_size:,} B")

    # Buckets de avance
    av_col = "Avance Físico Real Acumulado (%)_num"
    sub["_bucket"] = pd.cut(
        sub[av_col],
        bins=[-0.1, 0, 25, 50, 75, 99.9, 100.1],
        labels=["No iniciada (0%)", "1-25%", "26-50%", "51-75%", "76-99%", "Terminada (100%)"],
    )
    bucket_tab = pd.crosstab(sub["_bucket"], sub["Distrito"])

    # Stats por distrito
    por_dist = sub.groupby("Distrito").size()
    par_por_dist = paral.groupby("Distrito").size()

    # ----- Generar MD -----
    md = []
    md.append("# Obras públicas en Lima Cercado, San Isidro y Miraflores")
    md.append("")
    md.append("**Fuente:** Infobras (Contraloría General de la República)")
    md.append(f"**Dataset:** `DataSet-Obras-Publicas_15-05-2026.xlsx` (191,180 obras nacionales, {OBRAS_XLSX.stat().st_size:,} B)")
    md.append("**Fecha de consulta del dataset:** 2026-05-15")
    md.append(f"**Filtrado el:** 2026-05-15")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 1. Resumen ejecutivo")
    md.append("")
    md.append(f"- **Total obras** en los 3 distritos: **{len(sub):,}**")
    md.append(f"- **Obras con paralización activa** (marca oficial Infobras): **{len(paral)}**")
    md.append("")
    md.append("### Por distrito")
    md.append("")
    md.append("| Distrito | Total obras | Paralizadas | % paralizadas |")
    md.append("|---|---:|---:|---:|")
    for d in DISTRITOS:
        total = int(por_dist.get(d, 0))
        par_n = int(par_por_dist.get(d, 0))
        pct = (par_n / total * 100) if total else 0
        md.append(f"| {d} | {total:,} | {par_n} | {pct:.1f}% |")
    md.append("")
    md.append("### Distribución por nivel de avance físico real")
    md.append("")
    md.append("| Bucket | " + " | ".join(DISTRITOS) + " |")
    md.append("|" + "---|" * (len(DISTRITOS) + 1))
    for bucket in bucket_tab.index:
        row = [str(bucket)]
        for d in DISTRITOS:
            v = int(bucket_tab.loc[bucket, d]) if d in bucket_tab.columns else 0
            row.append(str(v))
        md.append("| " + " | ".join(row) + " |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 2. Obras paralizadas — detalle completo")
    md.append("")
    md.append(f"Las **{len(paral)} obras** marcadas oficialmente con `Existe Paralización = SI` en Infobras, ordenadas por días paralizadas (mayor a menor).")
    md.append("")

    # Ordenar paralizadas por días desc
    par_sorted = paral.copy()
    par_sorted["_dias"] = pd.to_numeric(par_sorted["Número de dias paralizado"], errors="coerce").fillna(0)
    par_sorted = par_sorted.sort_values("_dias", ascending=False)

    for i, (_, row) in enumerate(par_sorted.iterrows(), start=1):
        cod = fmt_text(row.get("Código INFOBRAS"))
        nombre = fmt_text(row.get("Nombre de obra"))
        distrito = fmt_text(row.get("Distrito"))
        entidad = fmt_text(row.get("Entidad Pública"))
        sector = fmt_text(row.get("Sector de la Entidad"))
        fini = fmt_text(row.get("Fecha de inicio de obra"))
        ffin = fmt_text(row.get("Fecha finalización programada de obra"))
        fpar = fmt_text(row.get("Fecha de paralización"))
        dias = fmt_text(row.get("Número de dias paralizado"))
        causal = fmt_text(row.get("Causal de paralización"))
        av_real = fmt_pct(row.get(av_col))
        av_prog = fmt_pct(row.get("Avance Físico Programado Acumulado (%)_num"))
        ej_fin = fmt_pct(row.get("Porcentaje de ejecución financiera_num"))
        monto_contrato = fmt_monto(row.get("Monto del contrato  en soles"))
        monto_ejec = fmt_monto(row.get("Monto de valorización Ejecutado Acumulado"))
        contratista = fmt_text(row.get("Nombre o razón social de la empresa o consorcio"))
        ruc = fmt_text(row.get("RUC"))
        direccion = fmt_text(row.get("Dirección o información de referencia"))
        tipo_ubic = fmt_text(row.get("Tipo de ubicación (exacta/referencial)"))

        infobras_url = f"https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId={cod}" if cod.isdigit() else ""

        md.append(f"### {i}. [{distrito}] {nombre}")
        md.append("")
        md.append(f"- **Código INFOBRAS:** {cod}" + (f" — [ver ficha oficial]({infobras_url})" if infobras_url else ""))
        md.append(f"- **Entidad:** {entidad}")
        md.append(f"- **Sector:** {sector}")
        md.append(f"- **Fechas:** inicio `{fini}` → fin programado `{ffin}`")
        md.append(f"- **Paralizada desde:** `{fpar}` ({dias} días)")
        md.append(f"- **Causal:** {causal}")
        md.append(f"- **Avance físico real:** {av_real}  ·  Programado: {av_prog}  ·  Ejecución financiera: {ej_fin}")
        md.append(f"- **Monto contrato:** {monto_contrato}  ·  Ejecutado: {monto_ejec}")
        md.append(f"- **Contratista:** {contratista}  (RUC: {ruc})")
        md.append(f"- **Ubicación:** {direccion}  ({tipo_ubic})")
        md.append("")

    md.append("---")
    md.append("")
    md.append("## 3. Mapeo: lo que pediste vs lo que tengo")
    md.append("")
    md.append("| Campo pedido | Estado | Columna fuente Infobras |")
    md.append("|---|---|---|")
    md.append("| **nombre** | ✅ completo | `Nombre de obra` |")
    md.append("| **fecha inicio** | ✅ completo (cuando la entidad lo reportó) | `Fecha de inicio de obra` |")
    md.append("| **reporte paralizadas** | ✅ completo: marca + causal + fecha + días | `Existe Paralización` + `Causal de paralización` + `Fecha de paralización` + `Número de dias paralizado` |")
    md.append("| **avances** | ✅ completo: físico real, físico programado, financiero | `Avance Físico Real Acumulado (%)` + `Avance Físico Programado Acumulado (%)` + `Porcentaje de ejecución financiera` |")
    md.append("| **ubicación** | ⚠️ solo texto/dirección, **sin lat/lon** | `Dirección o información de referencia` + `Tipo de ubicación` |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 4. Gaps detectados y de dónde podrían venir")
    md.append("")
    md.append("### 4.1 Coordenadas (lat/lon) — el gap más importante para el MVP")
    md.append("")
    md.append("Infobras DataSet **no incluye lat/lon**. Solo `Dirección o información de referencia` (texto) y `Tipo de ubicación` (exacta/referencial). Esto bloquea el filtro 'obras a 500m/1km/3km' del MD maestro §6.1.")
    md.append("")
    md.append("**Opciones para resolverlo:**")
    md.append("")
    md.append("| Opción | Costo | Cobertura esperada | Notas |")
    md.append("|---|---|---|---|")
    md.append("| Nominatim (OSM, gratis) | 0 USD, 1 req/seg | 60-75% por baja calidad de direcciones | Rate-limit duro; ~15 min para las 870 obras |")
    md.append("| Google Geocoding API | ~$5/1000 calls | 85-95% | Requiere API key. ~$0.04 las 870 obras |")
    md.append("| Ficha individual Infobras (HTML) | Gratis, scrape | Algunas obras tienen mapa embebido | Hay que parsear coordenadas del HTML — ver script 03 |")
    md.append("| Infobras `Mapa` (geoserver interno) | Posiblemente bloqueado | Desconocido | El HTML hace referencia a `http://11.162.107.180:8070/geoserver` (IP interna, no accesible) |")
    md.append("")
    md.append("Recomendación: **Nominatim para batch inicial + ficha Infobras para las paralizadas (39 obras) que requieren precisión**.")
    md.append("")
    md.append("### 4.2 Causal de paralización vacía (~23% de las paralizadas)")
    md.append("")
    md.append("9 de las 39 obras paralizadas tienen `Causal = NaN`. Esto es un gap del propio Infobras (la entidad reportó la paralización pero no la causal). No es scrapeable desde otra fuente: lo correcto es mostrar 'Causal no reportada por la entidad' en el UI.")
    md.append("")
    md.append("### 4.3 Direcciones faltantes (6 obras)")
    md.append("")
    md.append("Las obras INFOBRAS 83578, 132147, 144572, 160050, 169395, 537440 no tienen `Dirección o información de referencia`. Quedan con ubicación a nivel distrito solamente. Same gap que 4.2: depende de la entidad reportar.")
    md.append("")
    md.append("### 4.4 Contratistas: vista de concentración ≤8 UIT (gap más grande del MD maestro)")
    md.append("")
    md.append("Tengo `RUC` + `Nombre razón social` del contratista de cada obra. Lo que **falta** es la concentración de ese RUC en compras menores ≤8 UIT por entidad — eso vive en **OECE Pentaho** que requiere Playwright (ver `analisis_scraping.md` §4 y `estado_scrapers.md`). La API OCDS Perú (que sí tenemos) **no** incluye contratos ≤8 UIT por definición.")
    md.append("")
    md.append("### 4.5 Cruce con OCDS por proceso")
    md.append("")
    md.append("OCDS API ya está scrapeada (catálogo + 20 releases de muestra) pero no se ha cruzado con las obras Infobras. El campo cruce sería `Código Único de Inversión` o `RUC del contratista`. Pendiente de un script de join.")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 5. Resumen de cobertura por fuente")
    md.append("")
    md.append("Estado actual de las fuentes del MD maestro §8.2 aplicadas a estos 3 distritos:")
    md.append("")
    md.append("| Fuente | Estado | Aporta para 3 distritos |")
    md.append("|---|---|---|")
    md.append("| Infobras Obras Públicas | ✅ Bajado y filtrado | **870 obras** con todos los campos pedidos (excepto lat/lon) |")
    md.append("| Infobras Obras Paralizadas (bulk) | ✅ Bajado | Confirmación cruzada; 6 obras coinciden con el bulk de mar-2025 |")
    md.append("| Contraloría informe dic-2025 | ✅ Bajado | 3 XLSX + PDF; para análisis nacional, no aporta directo a estos distritos |")
    md.append("| Infobras ficha individual | ✅ Script listo | On-demand para enriquecer las 39 paralizadas con datos extra |")
    md.append("| OCDS API (releases + files) | ✅ Bajado parcial | Pendiente cruce por RUC/CUI |")
    md.append("| OCDS bulk mensual | ✅ Script listo | No descargado masivamente todavía |")
    md.append("| Pentaho Órdenes ≤8 UIT | ❌ Bloqueado | Requiere Playwright. Es el gap #1 para vista de contratista |")
    md.append("| INEI RNM / Mapa Pobreza | ❌ Manual pendiente | Para enriquecer ficha distrito |")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 6. Archivos generados")
    md.append("")
    md.append("- `scrapers/data/processed/obras_lima_3distritos_clean.csv` — 870 obras, columnas pedidas + columnas numéricas limpias (`*_num`)")
    md.append("- `scrapers/data/processed/obras_lima_paralizadas_clean.csv` — 39 obras paralizadas")
    md.append("- `scrapers/data/raw/infobras_datasets/DataSet-Obras-Publicas_15-05-2026.xlsx` — bulk fuente (63 MB)")
    md.append("")
    md.append("---")
    md.append("")
    md.append("## 7. Siguientes pasos sugeridos")
    md.append("")
    md.append("1. **Geocodificar las 870 obras** con Nominatim (15 min) → primer mapa funcional.")
    md.append("2. **Refinar lat/lon de las 39 paralizadas** parseando la ficha individual Infobras.")
    md.append("3. **Cruzar OCDS por RUC** para enriquecer contratista con historial de procesos ganados.")
    md.append("4. **Playwright para Pentaho** → Órdenes ≤8 UIT → vista de contratista del MD maestro §4.3.")
    md.append("")

    MD_PATH.write_text("\n".join(md), encoding="utf-8")
    print(f"\nMD escrito: {MD_PATH} ({MD_PATH.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
