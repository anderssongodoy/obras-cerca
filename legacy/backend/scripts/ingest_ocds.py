"""Ingesta de releases OCDS Perú a la tabla procedimiento_seleccion.

Lee scrapers/data/raw/ocds_releases/*.ndjson y carga cada release como
un procedimiento de selección. Cruza por RUC con contratistas y entidades
del MVP cuando es posible.

OCDS Release Package estándar OCP. Cada release tiene tender, awards,
contracts. Aquí extraemos:
    - ocid (canonical)
    - tender (objeto, monto referencial, fechas, num postores)
    - awards (contratista RUC + monto adjudicado + fecha buena pro)
    - parties (entidad procuring + contratista supplier)
"""
from __future__ import annotations

import io
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
NDJSON_DIR = ROOT / "scrapers" / "data" / "raw" / "ocds_releases"
DSN = "host=localhost user=postgres password=123 dbname=obrascerca"


def to_date(s):
    if not s:
        return None
    try:
        if isinstance(s, str):
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except Exception:
        return None
    return None


def parse_release(rel: dict, entidad_map: dict, contratista_map: dict) -> dict | None:
    ocid = rel.get("ocid")
    if not ocid:
        return None
    tender = rel.get("tender") or {}
    awards = rel.get("awards") or []
    parties = rel.get("parties") or []

    entidad_id = None
    contratista_id = None
    contratista_ruc = None

    # Buscar entidad procuring (roles incluye 'procuringEntity' o 'buyer')
    for p in parties:
        roles = p.get("roles") or []
        if "procuringEntity" in roles or "buyer" in roles:
            nombre_norm = (p.get("name") or "").strip().upper()
            if nombre_norm and nombre_norm in entidad_map:
                entidad_id = entidad_map[nombre_norm]
                break

    # Contratista: el supplier del primer award completo
    for a in awards:
        if a.get("status") in (None, "active", "pending"):
            for s in (a.get("suppliers") or []):
                ruc_candidate = (s.get("id") or s.get("identifier", {}).get("id") or "").strip()
                if re.match(r"^\d{8,11}$", ruc_candidate):
                    contratista_ruc = ruc_candidate
                    contratista_id = contratista_map.get(ruc_candidate)
                    break
            if contratista_id:
                break

    monto_referencial = (tender.get("value") or {}).get("amount")
    monto_adjudicado = None
    fecha_buena_pro = None
    for a in awards:
        if (a.get("value") or {}).get("amount"):
            monto_adjudicado = a["value"]["amount"]
        if a.get("date"):
            fecha_buena_pro = to_date(a["date"])
        if monto_adjudicado and fecha_buena_pro:
            break

    return {
        "ocid": ocid,
        "fuente_ocds": (rel.get("source") or rel.get("sourceId") or "").lower() or None,
        "entidad_id": entidad_id,
        "contratista_id": contratista_id,
        "contratista_ruc": contratista_ruc,
        "objeto": (tender.get("title") or "")[:500] or None,
        "descripcion": (tender.get("description") or "")[:2000] or None,
        "monto_referencial": monto_referencial,
        "monto_adjudicado": monto_adjudicado,
        "numero_postores": tender.get("numberOfTenderers"),
        "fecha_convocatoria": to_date((tender.get("tenderPeriod") or {}).get("startDate")),
        "fecha_buena_pro": fecha_buena_pro,
        "fecha_contrato": to_date((tender.get("contractPeriod") or {}).get("startDate")),
        "estado": tender.get("status"),
        "tipo_procedimiento": tender.get("procurementMethodDetails"),
    }


def main() -> int:
    archivos = sorted(NDJSON_DIR.glob("*.ndjson"))
    if not archivos:
        print(f"No hay NDJSON en {NDJSON_DIR}. Corre primero scrapers/05_ocds_releases.py")
        return 1
    print(f"Archivos NDJSON: {len(archivos)}")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, nombre_norm FROM entidad")
            entidad_map = {r[1]: r[0] for r in cur.fetchall()}
            cur.execute("SELECT id, ruc FROM contratista")
            contratista_map = {r[1]: r[0] for r in cur.fetchall()}
            print(f"  Entidades: {len(entidad_map)}, contratistas: {len(contratista_map)}")

            insertados = nuevos_contratistas = 0
            for f in archivos:
                print(f"Procesando {f.name}...")
                with f.open(encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            rel = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        rec = parse_release(rel, entidad_map, contratista_map)
                        if not rec:
                            continue
                        # Si vino con RUC pero no estaba en contratista_map, lo creamos
                        if rec["contratista_ruc"] and not rec["contratista_id"]:
                            # extraer razón social del party
                            razon = None
                            for p in (rel.get("parties") or []):
                                ruc_p = (p.get("id") or p.get("identifier", {}).get("id") or "").strip()
                                if ruc_p == rec["contratista_ruc"]:
                                    razon = (p.get("name") or "").strip()
                                    break
                            if razon:
                                cur.execute(
                                    "INSERT INTO contratista (ruc, razon_social) VALUES (%s, %s) ON CONFLICT (ruc) DO NOTHING RETURNING id",
                                    (rec["contratista_ruc"], razon)
                                )
                                row = cur.fetchone()
                                if row:
                                    contratista_map[rec["contratista_ruc"]] = row[0]
                                    rec["contratista_id"] = row[0]
                                    nuevos_contratistas += 1
                                else:
                                    cur.execute("SELECT id FROM contratista WHERE ruc = %s", (rec["contratista_ruc"],))
                                    rec["contratista_id"] = cur.fetchone()[0]

                        cur.execute("""
                            INSERT INTO procedimiento_seleccion
                                (ocid, fuente_ocds, entidad_id, contratista_id,
                                 objeto, descripcion, monto_referencial, monto_adjudicado,
                                 numero_postores, fecha_convocatoria, fecha_buena_pro,
                                 fecha_contrato, estado, tipo_procedimiento)
                            VALUES (%(ocid)s, %(fuente_ocds)s, %(entidad_id)s, %(contratista_id)s,
                                    %(objeto)s, %(descripcion)s, %(monto_referencial)s, %(monto_adjudicado)s,
                                    %(numero_postores)s, %(fecha_convocatoria)s, %(fecha_buena_pro)s,
                                    %(fecha_contrato)s, %(estado)s, %(tipo_procedimiento)s)
                            ON CONFLICT (ocid) DO UPDATE SET
                                monto_adjudicado = EXCLUDED.monto_adjudicado,
                                fecha_buena_pro = EXCLUDED.fecha_buena_pro,
                                contratista_id = COALESCE(EXCLUDED.contratista_id, procedimiento_seleccion.contratista_id)
                        """, rec)
                        insertados += 1
            conn.commit()

            # Cruzar OCDS con obras Infobras por RUC (heurística)
            cur.execute("""
                UPDATE procedimiento_seleccion p
                SET obra_id = o.id
                FROM obra o
                WHERE p.contratista_id IS NOT NULL
                  AND p.contratista_id = o.contratista_id
                  AND p.obra_id IS NULL
                  AND p.fecha_buena_pro IS NOT NULL
                  AND o.fecha_inicio IS NOT NULL
                  AND p.fecha_buena_pro BETWEEN o.fecha_inicio - INTERVAL '180 days' AND o.fecha_inicio + INTERVAL '90 days'
            """)
            cruzados = cur.rowcount
            conn.commit()

            print(f"\nProcedimientos ingestados: {insertados}")
            print(f"Contratistas nuevos:       {nuevos_contratistas}")
            print(f"Cruces obra↔procedimiento: {cruzados}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
