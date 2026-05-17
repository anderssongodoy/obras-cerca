"""Ingesta Órdenes de Compra y Servicios ≤8 UIT desde Pentaho/CONOSCE.

Lee scrapers/data/raw/pentaho_ordenes/CONOSCE_ORDENESCOMPRA*.xlsx,
filtra por departamento_entidad IN ('LIMA','CALLAO') y tipodecontratacion
'hasta 8 UIT', y carga a orden_compra_servicio.

Si no encuentra la entidad o el contratista, los crea on-the-fly.

Esto alimenta la vista de concentración en /api/contratistas/{ruc}
(la query ya está en el endpoint).
"""
from __future__ import annotations

import io
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
ORDENES_DIR = ROOT / "scrapers" / "data" / "raw" / "pentaho_ordenes"
DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

DEPARTAMENTOS_MVP = {"LIMA", "CALLAO"}


def to_date(v):
    if v is None or pd.isna(v):
        return None
    if isinstance(v, datetime):
        return v.date()
    try:
        return pd.to_datetime(v, errors="coerce").date()
    except Exception:
        return None


def to_num(v):
    if v is None or pd.isna(v):
        return None
    try:
        return float(v)
    except Exception:
        return None


def to_text(v):
    if v is None or pd.isna(v):
        return None
    s = str(v).strip()
    return s or None


def main() -> int:
    archivos = sorted(ORDENES_DIR.glob("CONOSCE_ORDENESCOMPRA*.xlsx"))
    if not archivos:
        print(f"No hay archivos en {ORDENES_DIR}")
        return 1
    print(f"Archivos: {len(archivos)}")
    for a in archivos:
        print(f"  - {a.name} ({a.stat().st_size:,} B)")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre_norm FROM entidad")
            entidad_map = {r[1]: r[0] for r in cur.fetchall()}
            cur.execute("SELECT id, ruc FROM contratista")
            contratista_map = {r[1]: r[0] for r in cur.fetchall()}
            print(f"  BD inicial: {len(entidad_map)} entidades, {len(contratista_map)} contratistas")

            total_ins = total_entidades_nuevas = total_contr_nuevos = 0

            for archivo in archivos:
                fuente = archivo.stem  # ej. CONOSCE_ORDENESCOMPRAMARZO2026_0
                print(f"\nProcesando {archivo.name}...")
                df = pd.read_excel(archivo, sheet_name=0)
                df.columns = [str(c).strip() for c in df.columns]
                print(f"  filas crudas: {len(df):,}")

                # Filtrar
                dep = df.get("departamento_entidad", pd.Series(dtype=str)).astype(str).str.upper().str.strip()
                tipo = df.get("tipodecontratacion", pd.Series(dtype=str)).astype(str).str.lower()
                mask = dep.isin(DEPARTAMENTOS_MVP) & tipo.str.contains("hasta 8 uit", na=False)
                sub = df[mask]
                print(f"  ≤8 UIT + Lima/Callao: {len(sub):,}")

                if len(sub) == 0:
                    continue

                rows_to_insert = []
                for _, row in sub.iterrows():
                    ent_nombre = to_text(row.get("entidad"))
                    if not ent_nombre:
                        continue
                    ent_norm = ent_nombre.upper()
                    ent_id = entidad_map.get(ent_norm)
                    if not ent_id:
                        # Crear entidad nueva
                        cur.execute("""
                            INSERT INTO entidad (nombre, nombre_norm, nivel_gobierno)
                            VALUES (%s, %s, NULL)
                            ON CONFLICT (nombre_norm) DO UPDATE SET nombre = EXCLUDED.nombre
                            RETURNING id
                        """, (ent_nombre, ent_norm))
                        ent_id = cur.fetchone()[0]
                        entidad_map[ent_norm] = ent_id
                        total_entidades_nuevas += 1

                    ruc_raw = to_text(row.get("ruc_contratista"))
                    cont_id = None
                    if ruc_raw:
                        ruc = re.sub(r"\.0$", "", ruc_raw).strip()
                        if re.match(r"^\d{8,11}$", ruc):
                            cont_id = contratista_map.get(ruc)
                            if not cont_id:
                                razon = to_text(row.get("nombre_razon_contratista")) or f"(sin nombre, RUC {ruc})"
                                cur.execute("""
                                    INSERT INTO contratista (ruc, razon_social) VALUES (%s, %s)
                                    ON CONFLICT (ruc) DO UPDATE SET razon_social = EXCLUDED.razon_social
                                    RETURNING id
                                """, (ruc, razon))
                                cont_id = cur.fetchone()[0]
                                contratista_map[ruc] = cont_id
                                total_contr_nuevos += 1

                    tipo_orden = (to_text(row.get("tipoorden")) or "").lower()
                    tipo_canon = "compra" if "compra" in tipo_orden else ("servicio" if "servicio" in tipo_orden else None)

                    rows_to_insert.append((
                        to_text(row.get("nro_de_orden")) or to_text(row.get("orden")),
                        tipo_canon,
                        ent_id,
                        cont_id,
                        to_num(row.get("monto_total_orden_original")),
                        to_date(row.get("fecha_de_emision")) or to_date(row.get("fecha_registro")),
                        to_text(row.get("descripcion_orden")),
                        None,  # url_documento — no viene en el XLSX
                        fuente,
                    ))

                # Insert batch
                with cur.copy("""
                    COPY orden_compra_servicio
                        (numero_orden, tipo, entidad_id, contratista_id,
                         monto_soles, fecha_emision, descripcion, url_documento, fuente)
                    FROM STDIN
                """) as copy:
                    for r in rows_to_insert:
                        copy.write_row(r)
                conn.commit()
                total_ins += len(rows_to_insert)
                print(f"  insertadas: {len(rows_to_insert):,}")

            cur.execute("SELECT COUNT(*) FROM orden_compra_servicio")
            total_bd = cur.fetchone()[0]

            print(f"\nTotal insertadas en esta corrida: {total_ins:,}")
            print(f"Entidades nuevas:                  {total_entidades_nuevas}")
            print(f"Contratistas nuevos:               {total_contr_nuevos}")
            print(f"Total en orden_compra_servicio:    {total_bd:,}")

            # Top 10 contratistas con más concentración por entidad (últimos 12m, ≤8 UIT)
            print("\n=== Top 10 RUCs por concentración en compras menores (12m) ===")
            cur.execute("""
                WITH por_entidad AS (
                    SELECT entidad_id, COUNT(*)::int AS total_ent, SUM(monto_soles) AS monto_ent
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                    GROUP BY entidad_id
                ),
                por_ruc_ent AS (
                    SELECT entidad_id, contratista_id, COUNT(*)::int AS n_ruc, SUM(monto_soles) AS monto_ruc
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                      AND contratista_id IS NOT NULL
                    GROUP BY entidad_id, contratista_id
                )
                SELECT c.ruc, c.razon_social, e.nombre AS entidad,
                       r.n_ruc, r.monto_ruc::bigint, pe.total_ent, pe.monto_ent::bigint,
                       ROUND(100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0), 2) AS pct_monto
                FROM por_ruc_ent r
                JOIN por_entidad pe ON pe.entidad_id = r.entidad_id
                JOIN contratista c ON c.id = r.contratista_id
                JOIN entidad e ON e.id = r.entidad_id
                WHERE pe.total_ent >= 5
                ORDER BY pct_monto DESC NULLS LAST
                LIMIT 10
            """)
            for r in cur.fetchall():
                ruc, razon, ent, n, m_ruc, n_ent, m_ent, pct = r
                ent_short = ent[:50]
                razon_short = (razon or "")[:40]
                print(f"  {pct or 0:>5}%  RUC {ruc}  {razon_short:<40}  {n_ruc} ord = S/{m_ruc or 0:,}  ({ent_short})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
