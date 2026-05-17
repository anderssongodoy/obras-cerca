"""Clasifica cada obra paralizada como 'vigente' / 'dudosa' / 'zombie'.

Regla operativa (hoy = CURRENT_DATE):
    - vigente: paralización ≤ 2 años AND último avance dentro de [paralización, +180 días)
               (es decir, paralizada recientemente y sin reactivación posterior)
    - dudosa:  paralización > 2 años PERO último avance hace < 1 año
               (entidad sigue tocando el registro: probablemente reactivada con flag pegado)
               O paralización ≤ 2 años PERO último avance posterior a paralización + 180 días
    - zombie:  paralización > 2 años AND último avance > 2 años (o NULL)
               (cementerio de Infobras: nadie ha tocado el registro)

También calcula:
    - dias_paralizada_real  = today - fecha_paralizacion (lo que tiene sentido para vecinos)
    - dias_sin_avance       = today - fecha_ultimo_avance
"""
from __future__ import annotations

import io
import sys

import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

CLASIFICAR_SQL = """
WITH calc AS (
    SELECT
        o.id AS obra_id,
        op.fecha_paralizacion,
        o.fecha_ultimo_avance,
        (CURRENT_DATE - op.fecha_paralizacion)::int AS dias_paralizada_real,
        CASE
            WHEN o.fecha_ultimo_avance IS NULL THEN NULL
            ELSE (CURRENT_DATE - o.fecha_ultimo_avance)::int
        END AS dias_sin_avance,
        CASE
            WHEN op.fecha_paralizacion IS NULL THEN NULL
            -- vigente: paralización <= 2 años y último avance no muy posterior
            WHEN op.fecha_paralizacion >= CURRENT_DATE - INTERVAL '730 days'
                 AND (o.fecha_ultimo_avance IS NULL
                      OR o.fecha_ultimo_avance <= op.fecha_paralizacion + INTERVAL '180 days')
            THEN 'vigente'::clasif_paralizacion
            -- dudosa: actividad reciente o reactivación posterior
            WHEN o.fecha_ultimo_avance >= CURRENT_DATE - INTERVAL '365 days'
            THEN 'dudosa'::clasif_paralizacion
            WHEN op.fecha_paralizacion >= CURRENT_DATE - INTERVAL '730 days'
                 AND o.fecha_ultimo_avance > op.fecha_paralizacion + INTERVAL '180 days'
            THEN 'dudosa'::clasif_paralizacion
            -- zombie: ambos viejos
            ELSE 'zombie'::clasif_paralizacion
        END AS clas
    FROM obra o
    JOIN obra_paralizacion op ON op.obra_id = o.id
    WHERE o.existe_paralizacion
)
UPDATE obra
SET
    clasificacion_paralizacion = calc.clas,
    dias_paralizada_real       = calc.dias_paralizada_real,
    dias_sin_avance            = calc.dias_sin_avance
FROM calc
WHERE obra.id = calc.obra_id;
"""

RESET_NO_PARALIZADAS_SQL = """
UPDATE obra SET clasificacion_paralizacion = NULL, dias_paralizada_real = NULL
WHERE NOT existe_paralizacion;
"""


def main() -> int:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            print("Aplicando reglas de clasificación...")
            cur.execute(CLASIFICAR_SQL)
            print(f"  {cur.rowcount} obras clasificadas")
            cur.execute(RESET_NO_PARALIZADAS_SQL)
            conn.commit()

            print("\n=== Distribución por clasificación ===")
            cur.execute("""
                SELECT clasificacion_paralizacion::text, COUNT(*),
                       COUNT(*) FILTER (WHERE confirmada_contraloria_2025) AS confirmadas_contraloria
                FROM obra
                WHERE existe_paralizacion
                GROUP BY clasificacion_paralizacion
                ORDER BY 1
            """)
            for r in cur.fetchall():
                print(f"  {r[0] or '(null)':<10} total: {r[1]:>4}   confirmadas Contraloría: {r[2]:>4}")

            print("\n=== Por distrito MVP: paralizadas vigentes vs zombies ===")
            cur.execute("""
                SELECT d.distrito,
                       COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS vigente,
                       COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'dudosa')  AS dudosa,
                       COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'zombie')  AS zombie,
                       COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025 AND o.existe_paralizacion) AS confirmadas
                FROM distrito d
                LEFT JOIN obra o ON o.distrito_id = d.id AND o.existe_paralizacion
                WHERE d.ambito_mvp
                GROUP BY d.distrito
                HAVING SUM(CASE WHEN o.existe_paralizacion THEN 1 ELSE 0 END) > 0
                ORDER BY vigente DESC
            """)
            print(f"  {'distrito':<28} {'vigente':>8} {'dudosa':>7} {'zombie':>7} {'conf.contr':>11}")
            for r in cur.fetchall():
                print(f"  {(r[0] or ''):<28} {r[1]:>8} {r[2]:>7} {r[3]:>7} {r[4]:>11}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
