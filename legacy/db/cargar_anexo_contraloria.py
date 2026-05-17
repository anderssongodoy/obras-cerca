"""Marca obras como confirmadas por Contraloría dic-2025.

Lee el Anexo N°02 del informe oficial y para cada Código INFOBRAS:
    UPDATE obra SET confirmada_contraloria_2025 = TRUE
    UPDATE obra_paralizacion SET confirmada_contraloria_2025 = TRUE

Esto da el "sello oficial" que confirma que la obra realmente está paralizada
según la auditoría de Contraloría (≥6 meses sin avance al corte de dic-2025).
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ANEXO_PATH = (
    ROOT / "scrapers" / "data" / "raw" / "contraloria_paralizadas"
    / "7715417-informe-de-obras-paralizadas-en-el-territorio-nacional-a-diciembre-2025"
    / "7715417-anexo-n-02-reporte-obras-paralizadas-diciembre-2025-vf.XLSX"
)
DSN = "host=localhost user=postgres password=123 dbname=obrascerca"


def main() -> int:
    if not ANEXO_PATH.exists():
        print(f"ERROR: no encuentro {ANEXO_PATH}")
        return 1

    print(f"Leyendo {ANEXO_PATH.name} ({ANEXO_PATH.stat().st_size:,} B)...")

    # Detectar header — los anexos suelen tener metadata en filas 0-3
    raw = pd.read_excel(ANEXO_PATH, sheet_name=0, header=None, nrows=10)
    print("Primeras filas:")
    for i in range(len(raw)):
        cells = raw.iloc[i].dropna().astype(str).tolist()[:6]
        print(f"  fila {i}: {' | '.join(cells)[:160]}")

    # Heurística: encontrar la fila que tiene 'INFOBRAS' o 'Código' como header
    header_row = 0
    for i in range(len(raw)):
        s = " ".join(raw.iloc[i].dropna().astype(str).tolist()).upper()
        if "INFOBRAS" in s or "CÓDIGO" in s or "CODIGO" in s:
            header_row = i
            break
    print(f"\nHeader detectado en fila {header_row}")

    df = pd.read_excel(ANEXO_PATH, sheet_name=0, header=header_row)
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  {len(df):,} filas x {len(df.columns)} columnas")
    print(f"  Columnas: {list(df.columns)[:15]}")

    # Buscar columna que contenga el código INFOBRAS
    col_inf = None
    for c in df.columns:
        cu = str(c).upper()
        if "INFOBRAS" in cu and ("CÓD" in cu or "COD" in cu):
            col_inf = c
            break
    if not col_inf:
        # Fallback: cualquier columna que se llame solo "Código"
        for c in df.columns:
            if str(c).strip().upper() in ("CÓDIGO", "CODIGO", "CODIGO INFOBRAS", "CÓDIGO INFOBRAS"):
                col_inf = c
                break
    if not col_inf:
        print("ERROR: no encuentro columna de Código INFOBRAS en el Anexo 02")
        return 1
    print(f"  Columna INFOBRAS: '{col_inf}'")

    codigos = (
        pd.to_numeric(df[col_inf], errors="coerce")
        .dropna()
        .astype("int64")
        .unique()
        .tolist()
    )
    print(f"  Códigos únicos en Anexo 02: {len(codigos):,}")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # Reset previo
            cur.execute("UPDATE obra SET confirmada_contraloria_2025 = FALSE")
            cur.execute("UPDATE obra_paralizacion SET confirmada_contraloria_2025 = FALSE")

            # Marcar coincidencias
            cur.execute(
                "UPDATE obra SET confirmada_contraloria_2025 = TRUE WHERE codigo_infobras = ANY(%s)",
                (codigos,)
            )
            n_obra = cur.rowcount
            cur.execute(
                """
                UPDATE obra_paralizacion p
                SET confirmada_contraloria_2025 = TRUE
                FROM obra o
                WHERE p.obra_id = o.id AND o.codigo_infobras = ANY(%s)
                """,
                (codigos,)
            )
            n_par = cur.rowcount
            conn.commit()
            print(f"\nObras del MVP confirmadas por Contraloría: {n_obra}")
            print(f"Paralizaciones confirmadas por Contraloría: {n_par}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
