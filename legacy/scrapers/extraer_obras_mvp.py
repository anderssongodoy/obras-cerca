"""Extrae TODAS las obras del MVP: Lima Metropolitana (43) + Callao (7).

Filtra el DataSet Obras-Publicas por:
    Departamento IN ('LIMA','CALLAO') AND Provincia IN ('LIMA','CALLAO')

Salida:
    data/processed/obras_mvp_50distritos.csv
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

OBRAS_XLSX = BASE / "DataSet-Obras-Publicas_15-05-2026.xlsx"

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


def limpiar_pct(v):
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


def main() -> int:
    print(f"Leyendo {OBRAS_XLSX.name}...")
    df = pd.read_excel(OBRAS_XLSX, sheet_name=0, header=3)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  {len(df):,} filas total nacional")

    dep = df["Departamento"].astype(str).str.upper().str.strip()
    prov = df["Provincia"].astype(str).str.upper().str.strip()
    # Provincia de Lima (LIMA dep + LIMA prov) o Provincia del Callao (CALLAO dep + CALLAO prov)
    mask = ((dep == "LIMA") & (prov == "LIMA")) | ((dep == "CALLAO") & (prov == "CALLAO"))
    sub = df.loc[mask, [c for c in COLS if c in df.columns]].copy()
    print(f"  {len(sub):,} obras en Lima Metropolitana + Callao")

    print(f"\nPor provincia:")
    print(sub.groupby([dep[mask], prov[mask]]).size().to_string())

    print(f"\nPor distrito (top 20):")
    print(sub["Distrito"].value_counts().head(20).to_string())

    # Limpiar columnas numéricas
    for c in ["Avance Físico Real Acumulado (%)",
              "Avance Físico Programado Acumulado (%)",
              "Porcentaje de ejecución financiera"]:
        if c in sub.columns:
            sub[c + "_num"] = sub[c].apply(limpiar_pct)

    n_paral = (sub["Existe Paralización"].astype(str).str.strip().str.upper() == "SI").sum()
    print(f"\nObras paralizadas en MVP: {n_paral}")

    out_path = OUT / "obras_mvp_50distritos.csv"
    sub.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\nCSV escrito: {out_path} ({out_path.stat().st_size:,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
