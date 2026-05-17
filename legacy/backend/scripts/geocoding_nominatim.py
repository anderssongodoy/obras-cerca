"""Geocoding batch con Nominatim (OSM, gratis, 1 req/seg).

Prioriza las obras paralizadas vigentes + confirmadas Contraloría
(las que el ciudadano va a mirar primero).

Política Nominatim:
    - User-Agent identificable obligatorio
    - 1 req/seg como máximo
    - Cache local en data/processed/geocache.json para no repetir
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

import psycopg
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent.parent
CACHE_PATH = ROOT / "scrapers" / "data" / "processed" / "geocache.json"
DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

NOMINATIM = "https://nominatim.openstreetmap.org/search"
UA = "ObrasCerca-Hackathon/0.1 (hack@latam 2026; anderssongodoygarcia@gmail.com)"


def cargar_cache() -> dict[str, dict]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def guardar_cache(cache: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def consultar_nominatim(direccion: str, distrito: str) -> dict | None:
    q = f"{direccion}, {distrito}, Lima, Peru"
    params = {"q": q, "format": "json", "limit": 1, "countrycodes": "pe"}
    try:
        r = requests.get(NOMINATIM, params=params, headers={"User-Agent": UA}, timeout=20)
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"]),
                "display_name": data[0].get("display_name"), "q": q}
    except Exception as e:
        print(f"  ERROR geocoding '{q}': {e}")
        return None


def main() -> int:
    cache = cargar_cache()
    print(f"Cache previa: {len(cache)} entradas")

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT o.id, o.codigo_infobras, o.direccion, d.distrito,
                       o.clasificacion_paralizacion::text, o.confirmada_contraloria_2025
                FROM obra o
                JOIN distrito d ON d.id = o.distrito_id
                WHERE o.existe_paralizacion
                  AND o.direccion IS NOT NULL
                  AND LENGTH(TRIM(o.direccion)) > 5
                  AND (o.geom_fuente IS NULL OR o.geom_fuente IN ('centroide_distrito'))
                ORDER BY
                    o.confirmada_contraloria_2025 DESC,
                    (o.clasificacion_paralizacion = 'vigente') DESC,
                    (o.clasificacion_paralizacion = 'dudosa') DESC
            """)
            obras = cur.fetchall()
            print(f"Obras paralizadas con dirección útil a geocodificar: {len(obras)}")

            geocoded = skipped_cache = failed = 0
            for i, (obra_id, cod_inf, direccion, distrito, clas, conf) in enumerate(obras, 1):
                key = f"{distrito}::{direccion.strip()[:160]}"
                if key in cache:
                    result = cache[key]
                    skipped_cache += 1
                else:
                    result = consultar_nominatim(direccion.strip(), distrito)
                    cache[key] = result or {"_failed": True}
                    if (i % 25) == 0:
                        guardar_cache(cache)
                    time.sleep(1.1)  # rate-limit Nominatim
                if not result or result.get("_failed"):
                    failed += 1
                    continue
                cur.execute(
                    """
                    UPDATE obra SET
                        latitud = %s, longitud = %s,
                        geom_fuente = 'nominatim'
                    WHERE id = %s
                    """,
                    (result["lat"], result["lon"], obra_id)
                )
                geocoded += 1
                print(f"  [{i}/{len(obras)}] {clas or '-':<7} {'C' if conf else ' '} "
                      f"INFOBRAS {cod_inf} → ({result['lat']:.5f}, {result['lon']:.5f})")
            conn.commit()
            guardar_cache(cache)

            print(f"\nGeocoded:     {geocoded}")
            print(f"Cache hits:   {skipped_cache}")
            print(f"Failed:       {failed}")

            cur.execute("SELECT geom_fuente, COUNT(*) FROM obra GROUP BY geom_fuente ORDER BY 2 DESC")
            print("\nDistribución geom_fuente tras geocoding:")
            for r in cur.fetchall():
                print(f"  {(r[0] or '(null)'):<25}: {r[1]:>6}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
