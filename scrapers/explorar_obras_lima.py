"""Filtra el DataSet de Obras Publicas Infobras por 3 distritos:
Lima Cercado, San Isidro, Miraflores.

Extrae los campos pedidos por el usuario:
    - nombre, fecha inicio, paralizada (sí/no/causal), avances, ubicación

Salida:
    - data/processed/obras_lima_3distritos.csv  (todo + extras útiles)
    - data/processed/obras_lima_paralizadas.csv (solo las paralizadas, foco)
    - imprime resumen en stdout
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd

# Stdout UTF-8 para no romper en cp1252 de Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path("data/raw/infobras_datasets")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

OBRAS_XLSX = BASE / "DataSet-Obras-Publicas_15-05-2026.xlsx"

DISTRITOS = {"LIMA", "SAN ISIDRO", "MIRAFLORES"}

# Columnas que queremos (exactas tal como vienen en el XLSX)
COLS_REQUEST = [
    "Código INFOBRAS",
    "Departamento",
    "Provincia",
    "Distrito",
    "Nombre de obra",
    "Entidad Pública",
    "Nivel de gobierno",
    "Sector de la Entidad",
    "Naturaleza de la obra",
    "Tipo de obra - Clasificador Nivel 1",
    "Estado de ejecución",
    "Fecha de inicio de obra",
    "Fecha finalización programada de obra",
    "Plazo de ejecución (en dias)",
    "Avance Físico Real Acumulado (%)",
    "Avance Físico Programado Acumulado (%)",
    "Porcentaje de ejecución financiera",
    "Monto de valorización Ejecutado Acumulado",
    "Monto del contrato  en soles",
    "Nombre o razón social de la empresa o consorcio",
    "RUC",
    "Existe Paralización",
    "Causal de paralización",
    "Fecha de paralización",
    "Número de dias paralizado",
    "Fecha de registro de avance",
    "Dirección o información de referencia",
    "Tipo de ubicación (exacta/referencial)",
]


def main() -> int:
    print(f"Leyendo {OBRAS_XLSX.name} ({OBRAS_XLSX.stat().st_size:,} B)...")
    obras = pd.read_excel(OBRAS_XLSX, sheet_name=0, header=3)
    obras.columns = [str(c).strip() for c in obras.columns]
    print(f"  {len(obras):,} filas x {len(obras.columns)} columnas")

    # Validar que tenemos todas las columnas pedidas
    faltan = [c for c in COLS_REQUEST if c not in obras.columns]
    if faltan:
        print(f"AVISO: faltan {len(faltan)} columnas esperadas:")
        for c in faltan:
            print(f"  - {c}")

    # Filtrar por departamento + provincia + distrito
    dep = obras["Departamento"].astype(str).str.upper().str.strip()
    prov = obras["Provincia"].astype(str).str.upper().str.strip()
    dist = obras["Distrito"].astype(str).str.upper().str.strip()
    mask = (dep == "LIMA") & (prov == "LIMA") & (dist.isin(DISTRITOS))
    sub = obras.loc[mask, [c for c in COLS_REQUEST if c in obras.columns]].copy()
    print(f"\nObras en los 3 distritos: {len(sub):,}")

    print("\nPor distrito:")
    print(sub["Distrito"].value_counts().to_string())

    # Existe Paralización: marca directa del propio dataset
    paral_col = "Existe Paralización"
    if paral_col in sub.columns:
        sub["_paralizada_norm"] = sub[paral_col].astype(str).str.strip().str.upper()
        n_paral = (sub["_paralizada_norm"] == "SI").sum()
        print(f"\nMarcadas 'Existe Paralización = SI': {n_paral}")

    csv_full = OUT / "obras_lima_3distritos.csv"
    sub.drop(columns=["_paralizada_norm"], errors="ignore").to_csv(
        csv_full, index=False, encoding="utf-8-sig"
    )
    print(f"\nCSV completo: {csv_full} ({csv_full.stat().st_size:,} B)")

    # Subset solo paralizadas
    if paral_col in sub.columns:
        par = sub[sub["_paralizada_norm"] == "SI"].drop(columns=["_paralizada_norm"])
        if len(par):
            csv_par = OUT / "obras_lima_paralizadas.csv"
            par.to_csv(csv_par, index=False, encoding="utf-8-sig")
            print(f"CSV paralizadas: {csv_par} ({csv_par.stat().st_size:,} B)")

            print("\n=== Obras PARALIZADAS en los 3 distritos ===")
            for _, row in par.iterrows():
                print(f"\n  • {row.get('Distrito')} | INFOBRAS {row.get('Código INFOBRAS')}")
                print(f"    {row.get('Nombre de obra')}")
                print(f"    Entidad: {row.get('Entidad Pública')}")
                print(f"    Inicio: {row.get('Fecha de inicio de obra')}  |  Fin prog: {row.get('Fecha finalización programada de obra')}")
                print(f"    Avance fisico real: {row.get('Avance Físico Real Acumulado (%)')}%  |  Ejecucion financiera: {row.get('Porcentaje de ejecución financiera')}%")
                print(f"    Causal: {row.get('Causal de paralización')}")
                print(f"    Paralizada desde: {row.get('Fecha de paralización')} ({row.get('Número de dias paralizado')} dias)")
                print(f"    Ubicacion: {row.get('Dirección o información de referencia')}")

    # Resumen avance por distrito
    av_real = "Avance Físico Real Acumulado (%)"
    if av_real in sub.columns:
        print("\n=== Avance fisico real (%) por distrito ===")
        sub_n = sub.copy()
        sub_n[av_real] = pd.to_numeric(sub_n[av_real], errors="coerce")
        agg = sub_n.groupby("Distrito")[av_real].agg(["count", "mean", "median"]).round(1)
        print(agg.to_string())

        print("\n=== Distribución de avance (real) por bucket ===")
        buckets = pd.cut(sub_n[av_real],
                         bins=[-0.1, 0, 25, 50, 75, 99.9, 100.1],
                         labels=["0% (no iniciada)", "1-25%", "26-50%", "51-75%", "76-99%", "100% (terminada)"])
        print(pd.crosstab(buckets, sub_n["Distrito"]).to_string())

    return 0


if __name__ == "__main__":
    sys.exit(main())
