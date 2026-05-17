"""Genera señales 'concentracion_menores' desde orden_compra_servicio.

Regla operativa: un RUC genera señal si en los últimos 12 meses
recibe ≥ N órdenes de la misma entidad Y eso representa ≥ X% del monto
total de compras menores de esa entidad.

Umbral: ≥30% del monto y al menos 5 órdenes, sobre entidades con
≥20 órdenes totales. (Configurable abajo.)
"""
from __future__ import annotations

import io
import json
import sys

import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

PCT_MIN = 20.0
ORDENES_MIN = 5
ENTIDAD_MIN_ORD = 20


def main() -> int:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            # Desactivar señales previas de este tipo
            cur.execute(
                "UPDATE senal_revision SET activa = FALSE WHERE tipo = 'concentracion_menores'"
            )
            print(f"Señales previas desactivadas: {cur.rowcount}")

            cur.execute("""
                WITH por_entidad AS (
                    SELECT entidad_id, COUNT(*)::int AS total_ent,
                           SUM(monto_soles) AS monto_ent
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                    GROUP BY entidad_id
                ),
                por_ruc_ent AS (
                    SELECT entidad_id, contratista_id,
                           COUNT(*)::int AS n_ruc, SUM(monto_soles) AS monto_ruc
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                      AND contratista_id IS NOT NULL
                    GROUP BY entidad_id, contratista_id
                )
                SELECT r.contratista_id, r.entidad_id, c.ruc, c.razon_social,
                       e.nombre AS entidad,
                       r.n_ruc, r.monto_ruc, pe.total_ent, pe.monto_ent,
                       ROUND(100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0), 2) AS pct_monto,
                       ROUND(100.0 * r.n_ruc / NULLIF(pe.total_ent, 0), 2) AS pct_ord
                FROM por_ruc_ent r
                JOIN por_entidad pe ON pe.entidad_id = r.entidad_id
                JOIN contratista c ON c.id = r.contratista_id
                JOIN entidad e ON e.id = r.entidad_id
                WHERE pe.total_ent >= %s
                  AND r.n_ruc >= %s
                  AND (100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0)) >= %s
                ORDER BY pct_monto DESC NULLS LAST
            """, (ENTIDAD_MIN_ORD, ORDENES_MIN, PCT_MIN))
            casos = cur.fetchall()
            print(f"Casos detectados (pct_monto >= {PCT_MIN}%, n_ord >= {ORDENES_MIN}, ent ≥{ENTIDAD_MIN_ORD}): {len(casos)}")

            insertadas = 0
            for cid, eid, ruc, razon, entidad, n_ruc, m_ruc, n_ent, m_ent, pct_m, pct_o in casos:
                titulo = f"{razon} concentra {pct_m}% de compras menores de {entidad[:60]}"
                explicacion = (
                    f"En los últimos 12 meses, el RUC {ruc} ({razon}) recibió "
                    f"{n_ruc} órdenes de servicio o compra ≤8 UIT de {entidad}, "
                    f"por S/ {float(m_ruc or 0):,.0f}. Eso representa {pct_m}% del monto "
                    f"total de compras menores de la entidad ({n_ent} órdenes "
                    f"por S/ {float(m_ent or 0):,.0f}). Vale revisar."
                )
                formula = (
                    f"pct_monto = 100 * Σmonto(RUC,entidad,12m) / Σmonto(entidad,12m) "
                    f"= 100 * {float(m_ruc or 0):.2f} / {float(m_ent or 0):.2f} "
                    f"= {pct_m}% — umbral señal: ≥ {PCT_MIN}%"
                )
                evidencia = {
                    "ruc": ruc,
                    "razon_social": razon,
                    "entidad_id": eid,
                    "entidad": entidad,
                    "ventana_dias": 365,
                    "ordenes_ruc_entidad": n_ruc,
                    "ordenes_totales_entidad": n_ent,
                    "monto_ruc_entidad_soles": float(m_ruc or 0),
                    "monto_total_entidad_soles": float(m_ent or 0),
                    "pct_monto": float(pct_m),
                    "pct_ordenes": float(pct_o),
                    "umbral_pct_monto": PCT_MIN,
                    "fuente": "pentaho_conosce_2026-02_2026-03",
                }
                cur.execute("""
                    INSERT INTO senal_revision
                        (tipo, contratista_id, entidad_id, titulo, explicacion,
                         score, formula, evidencia, activa)
                    VALUES ('concentracion_menores', %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (cid, eid, titulo, explicacion, float(pct_m or 0), formula, json.dumps(evidencia)))
                insertadas += 1
            conn.commit()

            print(f"\nSeñales 'concentracion_menores' insertadas: {insertadas}")
            cur.execute("SELECT tipo::text, COUNT(*) FROM senal_revision WHERE activa GROUP BY tipo ORDER BY 2 DESC")
            print("\nSeñales activas por tipo:")
            for r in cur.fetchall():
                print(f"  {r[0]:<25} {r[1]:>5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
