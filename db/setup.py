"""Setup completo de la BD obrascerca.

1. Crea la BD obrascerca si no existe.
2. Habilita PostGIS (con fallback si no está disponible).
3. Aplica schema.sql y seed_distritos.sql.

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
DSN_APP   = "host=localhost user=postgres password=123 dbname=obrascerca"
DB_NAME = "obrascerca"

ROOT = Path(__file__).resolve().parent


def crear_bd() -> None:
    with psycopg.connect(DSN_ADMIN, autocommit=True) as conn:
        cur = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
        if cur.fetchone():
            print(f"BD '{DB_NAME}' ya existe")
            return
        conn.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8'").format(sql.Identifier(DB_NAME)))
        print(f"BD '{DB_NAME}' creada")


def verificar_postgis() -> bool:
    with psycopg.connect(DSN_APP, autocommit=True) as conn:
        cur = conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'postgis'")
        return cur.fetchone() is not None


def aplicar_sql(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    print(f"Aplicando {path.name} ({len(text):,} chars)...")
    with psycopg.connect(DSN_APP, autocommit=True) as conn:
        conn.execute(text)
    print(f"  OK")


def aplicar_schema_sin_postgis() -> None:
    """Fallback: aplica schema cambiando geometry → numeric lat/lon."""
    text = (ROOT / "schema.sql").read_text(encoding="utf-8")
    # Reemplazos puntuales para correr sin PostGIS
    text = text.replace("CREATE EXTENSION IF NOT EXISTS postgis;", "-- postgis no disponible, fallback a lat/lon NUMERIC")
    text = text.replace("geom         geometry(MultiPolygon, 4326),", "geom_wkt     TEXT,")
    text = text.replace("centroide    geometry(Point, 4326)", "centroide_lat NUMERIC(10,7), centroide_lon NUMERIC(10,7)")
    text = text.replace("geom                                geometry(Point, 4326),", "latitud  NUMERIC(10,7),\n    longitud NUMERIC(10,7),")
    text = text.replace("CREATE INDEX IF NOT EXISTS obra_geom_idx                ON obra USING GIST(geom);", "CREATE INDEX IF NOT EXISTS obra_latlon_idx ON obra(latitud, longitud);")
    text = text.replace("CREATE INDEX IF NOT EXISTS distrito_geom_idx     ON distrito USING GIST(geom);", "")
    text = text.replace("CREATE INDEX IF NOT EXISTS distrito_centroide_idx ON distrito USING GIST(centroide);", "")
    text = text.replace("ST_AsGeoJSON(o.geom) :: jsonb AS geom_geojson,",
                        "jsonb_build_object('type', 'Point', 'coordinates', ARRAY[o.longitud, o.latitud]) AS geom_geojson,")
    print("Aplicando schema sin PostGIS (fallback)...")
    with psycopg.connect(DSN_APP, autocommit=True) as conn:
        conn.execute(text)
    print("  OK")


def main() -> int:
    crear_bd()
    if verificar_postgis():
        print("PostGIS disponible — aplicando schema completo")
        aplicar_sql(ROOT / "schema.sql")
    else:
        print("PostGIS NO disponible — aplicando schema fallback con lat/lon NUMERIC")
        aplicar_schema_sin_postgis()
    aplicar_sql(ROOT / "seed_distritos.sql")

    # Resumen
    with psycopg.connect(DSN_APP) as conn:
        cur = conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
        cur = conn.execute("""
            SELECT table_name FROM information_schema.views
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        views = [r[0] for r in cur.fetchall()]
        cur = conn.execute("SELECT COUNT(*) FROM distrito WHERE ambito_mvp")
        mvp = cur.fetchone()[0]

    print(f"\nTablas creadas ({len(tables)}): {', '.join(tables)}")
    print(f"Vistas creadas ({len(views)}): {', '.join(views)}")
    print(f"Distritos en ámbito MVP: {mvp}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
