"""Setup completo de la BD obrascerca_v2.

1) Crea la BD obrascerca_v2 si no existe (la vieja obrascerca queda intacta).
2) Aplica schema.sql.
3) Aplica seed_distritos.sql (50 distritos MVP + 13 fuentes de datos catálogo).

Uso:
    cd db
    python setup.py
"""
from __future__ import annotations

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


def crear_bd() -> None:
    with psycopg.connect(DSN_ADMIN, autocommit=True) as conn:
        cur = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if cur.fetchone():
            print(f"BD '{DB_NAME}' ya existe — no se recrea")
            return
        conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(DB_NAME)))
        print(f"BD '{DB_NAME}' creada")


def aplicar_sql(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    print(f"Aplicando {path.name} ({len(text):,} chars)...")
    with psycopg.connect(DSN_APP, autocommit=True) as conn:
        conn.execute(text)
    print("  OK")


def resumen() -> None:
    with psycopg.connect(DSN_APP) as conn:
        tables = [r[0] for r in conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' AND table_type='BASE TABLE'
            ORDER BY table_name
        """).fetchall()]
        views = [r[0] for r in conn.execute("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema='public' ORDER BY table_name
        """).fetchall()]
        distritos = conn.execute("SELECT COUNT(*) FROM distrito WHERE ambito_mvp").fetchone()[0]
        fuentes = conn.execute("SELECT COUNT(*) FROM fuente_dato").fetchone()[0]
    print(f"\nTablas: {len(tables)} -> {', '.join(tables)}")
    print(f"Vistas: {len(views)} -> {', '.join(views)}")
    print(f"Distritos MVP cargados: {distritos}")
    print(f"Fuentes de dato catalogadas: {fuentes}")


def main() -> int:
    crear_bd()
    aplicar_sql(ROOT / "schema.sql")
    aplicar_sql(ROOT / "seed_distritos.sql")
    resumen()
    return 0


if __name__ == "__main__":
    sys.exit(main())
