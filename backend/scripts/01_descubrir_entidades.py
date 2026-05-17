"""Descubre todas las entidades públicas relevantes para el MVP desde el PTE.

Tipos cubiertos:
    - Tipo_Pod=5 (Gobiernos Locales) → 1,279 munis del Perú; filtramos 50 MVP
    - Tipo_Pod=None (Ejecutivo)      → ~348 ministerios y organismos centrales
    - Tipo_Pod=4 (Autónomos)         → JNJ, JNE, ONPE, Defensoría, etc
    - Tipo_Pod=2 (Judicial)          → Poder Judicial
    - Tipo_Pod=1 (Legislativo)       → Congreso
    - Tipo_Pod=7 (Regionales)        → Gobierno Regional de Lima (no aplica Callao Provincial Constitucional)

Inserta en tabla `entidad` con clasificación por `tipo` + `tipo_pod_pte`.
Marca como `distrito_id` aquellas munis que están en el ámbito MVP.

Uso:
    python 01_descubrir_entidades.py
"""
from __future__ import annotations

import os

from _common import norm

import psycopg
from app.clients.pte import PTEClient

DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")


# Mapeo Tipo_Pod -> (tipo_entidad enum, nivel_gobierno)
TIPO_POD_MAP = {
    5:    ("municipalidad_distrital",  "local"),     # se afina por nombre abajo
    None: ("ministerio",                "nacional"),
    4:    ("organismo_autonomo",       "nacional"),
    2:    ("organismo_autonomo",       "nacional"),
    1:    ("organismo_autonomo",       "nacional"),
    7:    ("gobierno_regional",        "regional"),
}


def clasificar_local(nombre: str) -> str:
    """Refina el tipo según el nombre."""
    n = norm(nombre)
    if "PROVINCIAL" in n:
        return "municipalidad_provincial"
    if "MUNICIPALIDAD" in n:
        return "municipalidad_distrital"
    if "EMPRESA" in n:
        return "empresa_estatal"
    if "UNIVERSIDAD" in n:
        return "universidad_nacional"
    return "otro"


def main() -> int:
    pte = PTEClient()
    tipos_pod = [5, None, 4, 7, 2, 1]
    todas: dict[int, dict] = {}
    for tp in tipos_pod:
        ents = pte.listar_entidades(tipo_pod=tp)
        print(f"Tipo_Pod={tp}: {len(ents)} entidades")
        tipo_default, nivel = TIPO_POD_MAP.get(tp, ("otro", None))
        for e in ents:
            id_ent = e["id_entidad"]
            if id_ent in todas:
                continue
            tipo = clasificar_local(e["nombre"]) if tp == 5 else tipo_default
            todas[id_ent] = {
                **e,
                "tipo": tipo,
                "tipo_pod": tp,
                "nivel_gobierno": nivel,
                "nombre_norm": norm(e["nombre"]),
            }
    print(f"\nTotal entidades únicas: {len(todas)}")

    # Mapear entidades munis MVP al distrito_id correspondiente
    with psycopg.connect(DSN) as conn:
        cur = conn.execute(
            "SELECT id, distrito FROM distrito WHERE ambito_mvp"
        )
        distrito_por_nombre = {norm(r[1]): r[0] for r in cur.fetchall()}
        # Algunos alias del PTE → ubigeo del distrito
        alias = {
            norm("LURIGANCHO-CHOSICA"): distrito_por_nombre.get(norm("LURIGANCHO")),
            norm("CARMEN DE LA LEGUA REYNOSO"): distrito_por_nombre.get(norm("CARMEN DE LA LEGUA REYNOSO")),
            norm("MAGDALENA VIEJA"): distrito_por_nombre.get(norm("PUEBLO LIBRE")),
        }
        distrito_por_nombre.update({k: v for k, v in alias.items() if v})

        ins = 0
        for e in todas.values():
            distrito_id = None
            if e["tipo"] in ("municipalidad_distrital", "municipalidad_provincial"):
                # Heurística: buscar substring del distrito al final del nombre
                for dnorm, did in distrito_por_nombre.items():
                    if dnorm and dnorm in e["nombre_norm"]:
                        # evitar matches parciales (SAN JUAN dentro de SAN JUAN DE LURIGANCHO)
                        # exigir que el match sea palabra completa
                        if (" " + dnorm + " ") in (" " + e["nombre_norm"] + " ") or \
                           e["nombre_norm"].endswith(dnorm):
                            distrito_id = did
                            break
            conn.execute(
                """
                INSERT INTO entidad
                    (pte_id_entidad, nombre, nombre_norm, sigla, tipo, tipo_pod_pte,
                     nivel_gobierno, distrito_id)
                VALUES (%s, %s, %s, %s, %s::tipo_entidad, %s, %s, %s)
                ON CONFLICT (nombre_norm) DO UPDATE SET
                    pte_id_entidad = EXCLUDED.pte_id_entidad,
                    sigla = EXCLUDED.sigla,
                    tipo = EXCLUDED.tipo,
                    tipo_pod_pte = EXCLUDED.tipo_pod_pte,
                    nivel_gobierno = EXCLUDED.nivel_gobierno,
                    distrito_id = COALESCE(EXCLUDED.distrito_id, entidad.distrito_id)
                """,
                (e["id_entidad"], e["nombre"], e["nombre_norm"], e["sigla"],
                 e["tipo"], e["tipo_pod"], e["nivel_gobierno"], distrito_id),
            )
            ins += 1
        conn.commit()

        # Reporte
        cur = conn.execute("""
            SELECT tipo::text, COUNT(*) FROM entidad
            GROUP BY tipo ORDER BY COUNT(*) DESC
        """)
        print("\nPor tipo:")
        for r in cur.fetchall():
            print(f"  {r[0]:<28} {r[1]:>5}")
        cur = conn.execute("""
            SELECT COUNT(*) FROM entidad WHERE distrito_id IS NOT NULL
        """)
        print(f"\nEntidades vinculadas a distrito MVP: {cur.fetchone()[0]}")
    return 0


if __name__ == "__main__":
    main()
