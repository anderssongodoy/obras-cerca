"""Restore de la BD demo desde cero — para que el equipo tenga la MISMA data.

1) Borra obrascerca_v2 si existe.
2) Crea obrascerca_v2 vacía.
3) Aplica schema.sql (estructura).
4) Aplica seed_distritos.sql (50 distritos MVP + 13 fuentes catalogadas).
5) Aplica seeds/demo_snapshot.sql (entidades + obras + informes + señales del demo).

Tras correr esto cada miembro del equipo tiene los MISMOS datos que vi al hacer la demo,
sin depender de que MEF/Infobras estén respondiendo igual hoy que el día del snapshot.

Uso:
    cd db
    python restore_demo.py
    python restore_demo.py --drop      # borra y recrea (default si existe)
    python restore_demo.py --no-drop   # falla si la BD ya existe (modo seguro)
"""
from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import psycopg
from psycopg import sql

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DSN_ADMIN = "host=localhost user=postgres password=123 dbname=postgres"
DB_NAME = "obrascerca_v2"
DSN_APP = f"host=localhost user=postgres password=123 dbname={DB_NAME}"

ROOT = Path(__file__).resolve().parent
SCHEMA = ROOT / "schema.sql"
SEED_DISTRITOS = ROOT / "seed_distritos.sql"
DEMO_SNAPSHOT = ROOT / "seeds" / "demo_snapshot.sql"


def bd_existe() -> bool:
    with psycopg.connect(DSN_ADMIN, autocommit=True) as conn:
        cur = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        return cur.fetchone() is not None


def drop_bd() -> None:
    with psycopg.connect(DSN_ADMIN, autocommit=True) as conn:
        # Forzar cierre de conexiones activas a esta BD (necesario en Windows)
        conn.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (DB_NAME,)
        )
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(DB_NAME)))
        print(f"BD '{DB_NAME}' eliminada")


def crear_bd() -> None:
    with psycopg.connect(DSN_ADMIN, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(DB_NAME)))
        print(f"BD '{DB_NAME}' creada")


def _limpiar_dump(text: str) -> str:
    """Quita meta-comandos de psql (\\restrict, \\unrestrict, \\connect, etc.)
    que psycopg no entiende. Los \\restrict aparecen en pg_dump >= 17.
    """
    lineas = []
    for ln in text.splitlines():
        s = ln.lstrip()
        if s.startswith("\\"):
            continue
        lineas.append(ln)
    return "\n".join(lineas)


def aplicar(path: Path, *, defer_fk: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".sql" and path.name == "demo_snapshot.sql":
        text = _limpiar_dump(text)
    print(f"Aplicando {path.name} ({len(text):,} chars)...")
    with psycopg.connect(DSN_APP, autocommit=True) as conn:
        if defer_fk:
            # Desactiva triggers/FK durante la carga del snapshot (por self-FK de obra.obra_padre_id)
            conn.execute("SET session_replication_role = replica")
        conn.execute(text)
        if defer_fk:
            conn.execute("SET session_replication_role = origin")
    print("  OK")


def resumen() -> None:
    with psycopg.connect(DSN_APP) as conn:
        kpis = conn.execute("""
            SELECT
              (SELECT COUNT(*) FROM distrito WHERE ambito_mvp)             AS distritos_mvp,
              (SELECT COUNT(*) FROM entidad)                               AS entidades,
              (SELECT COUNT(*) FROM proyecto_mef)                          AS proyectos,
              (SELECT COUNT(*) FROM obra)                                  AS obras,
              (SELECT COUNT(*) FROM obra WHERE estado_obra_wfs='Paralizada') AS paralizadas_wfs,
              (SELECT COUNT(*) FROM obra WHERE obra_padre_id IS NOT NULL)  AS saldos,
              (SELECT COUNT(*) FROM informe_control)                       AS informes,
              (SELECT COUNT(*) FROM procedimiento_seleccion)               AS contratos,
              (SELECT COUNT(*) FROM senal_revision WHERE activa)           AS senales
        """).fetchone()
    print("\nResumen tras restore:")
    for k, v in kpis.items() if hasattr(kpis, "items") else zip(
        ['distritos_mvp','entidades','proyectos','obras','paralizadas_wfs','saldos','informes','contratos','senales'],
        kpis
    ):
        print(f"  {k:<20} {v:>6}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-drop", action="store_true", help="Fallar si la BD ya existe (modo seguro)")
    args = ap.parse_args()

    for f in (SCHEMA, SEED_DISTRITOS, DEMO_SNAPSHOT):
        if not f.exists():
            print(f"ERROR: falta {f}")
            return 1

    if bd_existe():
        if args.no_drop:
            print(f"ERROR: BD '{DB_NAME}' ya existe. Quita --no-drop para sobreescribir.")
            return 1
        drop_bd()
    crear_bd()
    aplicar(SCHEMA)
    aplicar(SEED_DISTRITOS)
    aplicar(DEMO_SNAPSHOT, defer_fk=True)
    resumen()
    print("\nListo. Levanta el backend con:  cd ../backend && uvicorn app.main:app --reload --port 8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
