"""Para cada entidad sin IdUE en BD, hace scrape del PTE y guarda el IdUE SIAF.

Endpoint: pte_transparencia_pro_inv.aspx?id_entidad=X&id_tema=26&ver=1
Regex: IdUE=(\\d+) en el HTML.

Por defecto solo procesa entidades del MVP (relacionadas a Lima/Callao) o
ministerios/autónomos (que ejecutan obras en todo el país).

Uso:
    python 02_mapear_idue.py                  # solo entidades clave (recomendado)
    python 02_mapear_idue.py --todas          # las 1,600+ entidades del catálogo
    python 02_mapear_idue.py --rate 0.5       # 1 request cada 0.5s (default)
"""
from __future__ import annotations

import argparse
import time

from _common import norm

import psycopg
from app.clients.mef import MEFClient

DSN = "host=localhost user=postgres password=123 dbname=obrascerca_v2"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--todas", action="store_true", help="Procesar todas, no solo las clave")
    ap.add_argument("--rate", type=float, default=0.5, help="Segundos entre requests")
    args = ap.parse_args()

    mef = MEFClient()
    with psycopg.connect(DSN) as conn:
        where = (
            "siaf_idue IS NULL AND pte_id_entidad IS NOT NULL"
            if args.todas else
            "siaf_idue IS NULL AND pte_id_entidad IS NOT NULL AND "
            "(distrito_id IS NOT NULL OR tipo IN "
            "('ministerio','organismo_autonomo','empresa_estatal','universidad_nacional'))"
        )
        cur = conn.execute(f"SELECT id, pte_id_entidad, nombre FROM entidad WHERE {where} ORDER BY id")
        pendientes = cur.fetchall()
        print(f"Pendientes de mapear IdUE: {len(pendientes)}")

        ok = fail = 0
        for i, (eid, pte_id, nombre) in enumerate(pendientes, 1):
            idue = mef.scrape_idue_de_pte(pte_id)
            if idue:
                conn.execute("UPDATE entidad SET siaf_idue = %s WHERE id = %s", (idue, eid))
                ok += 1
                if i % 20 == 0 or i == len(pendientes):
                    conn.commit()
                print(f"  [{i:>4}/{len(pendientes)}] OK   id_entidad={pte_id} IdUE={idue} {nombre[:60]}")
            else:
                fail += 1
                print(f"  [{i:>4}/{len(pendientes)}] FAIL id_entidad={pte_id} {nombre[:60]}")
            time.sleep(args.rate)
        conn.commit()

        print(f"\nOK: {ok} · FAIL: {fail}")
    return 0


if __name__ == "__main__":
    main()
