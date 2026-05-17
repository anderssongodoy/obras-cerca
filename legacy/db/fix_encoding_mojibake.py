"""Repara mojibake (doble encode UTF-8 → cp1252) en campos de texto.

El ingest de Infobras leyó XLSX con bytes que ya estaban en UTF-8 pero
fueron interpretados como Latin-1, produciendo cosas como:
    'EducaciÃ"N' (mojibake) ← original 'EDUCACIÓN'
    'Ejecución' (mojibake) ← original 'Ejecución'

Fix: para cada string, intentar `s.encode('latin-1').decode('utf-8')`.
Si decodifica y mejora (saca bytes raros), se aplica. Si no, se deja.
"""
from __future__ import annotations

import io
import re
import sys

import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

MOJIBAKE_RX = re.compile(r"Ã[-¿]|Ã[-ÿ]")


def fix(s: str | None) -> str | None:
    if s is None:
        return None
    if not MOJIBAKE_RX.search(s):
        return s
    try:
        fixed = s.encode("latin-1").decode("utf-8")
        # Validar: el fixed no debe tener bytes raros nuevos
        return fixed
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


TARGETS = [
    ("obra", "id", ["nombre", "naturaleza", "tipo_obra_nivel1", "tipo_obra_nivel2",
                     "tipo_obra_nivel3", "sector", "estado_ejecucion", "direccion"]),
    ("entidad", "id", ["nombre", "nombre_norm", "sector"]),
    ("contratista", "id", ["razon_social"]),
    ("obra_paralizacion", "id", ["causal", "comentarios"]),
    ("orden_compra_servicio", "id", ["descripcion"]),
]


def main() -> int:
    total_filas = 0
    total_cols = 0
    with psycopg.connect(DSN) as conn:
        for tabla, pk, cols in TARGETS:
            print(f"\nTabla {tabla} ({len(cols)} cols)...")
            with conn.cursor() as cur:
                col_sql = ", ".join(cols)
                cur.execute(f"SELECT {pk}, {col_sql} FROM {tabla}")
                rows = cur.fetchall()
                print(f"  {len(rows):,} filas leídas")
                cambios = 0
                batch_changes = []
                for row in rows:
                    pk_val = row[0]
                    valores_orig = row[1:]
                    valores_new = [fix(v) for v in valores_orig]
                    if valores_new != list(valores_orig):
                        batch_changes.append((pk_val, valores_new))
                        cambios += 1
                if cambios:
                    set_sql = ", ".join(f"{c} = %s" for c in cols)
                    update_sql = f"UPDATE {tabla} SET {set_sql} WHERE {pk} = %s"
                    for pk_val, valores_new in batch_changes:
                        cur.execute(update_sql, (*valores_new, pk_val))
                    conn.commit()
                print(f"  filas modificadas: {cambios:,}")
                total_filas += cambios
                total_cols += len(cols)
    print(f"\nTotal filas con fix: {total_filas:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
