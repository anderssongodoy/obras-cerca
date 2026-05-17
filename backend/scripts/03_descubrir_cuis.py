"""Por cada entidad con IdUE conocido, lista todos sus CUIs ejecutados en el periodo.

Endpoint: POST GetEjecucion (Postman §2.3)
Pagina con pPageSize=30 hasta agotar.

Output: tabla proyecto_mef llenada con datos básicos del listado (los datos
completos se traen en el script 04).

Uso:
    python 03_descubrir_cuis.py                  # periodo 2026
    python 03_descubrir_cuis.py --periodo 2025
    python 03_descubrir_cuis.py --solo-mvp       # solo entidades con distrito MVP
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import date

import psycopg
from app.clients.mef import MEFClient

from _common import norm

DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")


def cargar_a_proyecto_mef(conn, fila: dict, entidad_id: int, periodo: int) -> int:
    """Inserta o actualiza fila básica en proyecto_mef.

    El listado GetEjecucion devuelve campos crudos como cols['COD_DGPP'],
    ['NOM_INVERSION'], etc. Distintas versiones del endpoint usan claves
    distintas; lo hacemos flexible.
    """
    cui = fila.get("CODIGO_UNICO") or fila.get("COD_DGPP") or fila.get("CUI") or fila.get("CODIGO")
    if not cui:
        # En algunas respuestas viene como string en formato "N° | CUI | ..."
        return 0
    try:
        cui = int(str(cui).strip())
    except (ValueError, TypeError):
        return 0
    nombre = (
        fila.get("NOM_INVERSION") or fila.get("NOMBRE") or fila.get("NOMBRE_INVERSION")
        or fila.get("NOM_PROYECTO") or "(sin nombre)"
    ).strip()
    conn.execute("""
        INSERT INTO proyecto_mef (cui, nombre_inversion, entidad_id, estado)
        VALUES (%s, %s, %s, 'NO_VERIFICADO'::estado_proyecto_mef)
        ON CONFLICT (cui) DO UPDATE SET
            entidad_id = COALESCE(EXCLUDED.entidad_id, proyecto_mef.entidad_id)
    """, (cui, nombre, entidad_id))
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--periodo", type=int, default=date.today().year)
    ap.add_argument("--solo-mvp", action="store_true")
    ap.add_argument("--rate", type=float, default=0.5)
    args = ap.parse_args()

    mef = MEFClient()
    with psycopg.connect(DSN) as conn:
        where = "siaf_idue IS NOT NULL"
        if args.solo_mvp:
            where += " AND distrito_id IS NOT NULL"
        cur = conn.execute(f"SELECT id, siaf_idue, nombre FROM entidad WHERE {where} ORDER BY id")
        entidades = cur.fetchall()
        print(f"Entidades a consultar: {len(entidades)} | periodo: {args.periodo}")

        total_cuis = 0
        for i, (eid, idue, nombre) in enumerate(entidades, 1):
            page = 1
            ent_cuis = 0
            while True:
                rows = mef.get_ejecucion(idue, args.periodo, page=page, page_size=30)
                if not rows:
                    break
                for fila in rows:
                    ent_cuis += cargar_a_proyecto_mef(conn, fila, eid, args.periodo)
                page += 1
                time.sleep(args.rate)
                if len(rows) < 30:
                    break  # última página
            conn.commit()
            total_cuis += ent_cuis
            print(f"  [{i:>4}/{len(entidades)}] IdUE={idue} {nombre[:50]:<50} -> {ent_cuis} CUIs")

        cur = conn.execute("SELECT COUNT(*) FROM proyecto_mef")
        print(f"\nTotal proyectos en BD: {cur.fetchone()[0]} (recién: {total_cuis})")
    return 0


if __name__ == "__main__":
    main()
