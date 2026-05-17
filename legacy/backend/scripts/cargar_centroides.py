"""Carga centroides (lat, lon) de los 50 distritos del MVP y los aplica
como ubicación-fallback a todas las obras sin geocoding propio.

Coordenadas WGS84 aproximadas (centroide político del distrito).
"""
from __future__ import annotations

import io
import sys

import psycopg

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DSN = "host=localhost user=postgres password=123 dbname=obrascerca"

# {ubigeo: (lat, lon)}  — centroides aproximados Lima Metro + Callao
CENTROIDES: dict[str, tuple[float, float]] = {
    # Lima Metro
    "150101": (-12.0464, -77.0428),  # LIMA (Cercado)
    "150102": (-11.7708, -77.1772),  # ANCON
    "150103": (-12.0264, -76.9170),  # ATE
    "150104": (-12.1449, -77.0211),  # BARRANCO
    "150105": (-12.0606, -77.0497),  # BREÑA
    "150106": (-11.8500, -77.0408),  # CARABAYLLO
    "150107": (-11.9750, -76.7700),  # CHACLACAYO
    "150108": (-12.1700, -77.0257),  # CHORRILLOS
    "150109": (-12.1208, -76.8203),  # CIENEGUILLA
    "150110": (-11.9355, -77.0578),  # COMAS
    "150111": (-12.0408, -76.9989),  # EL AGUSTINO
    "150112": (-11.9866, -77.0436),  # INDEPENDENCIA
    "150113": (-12.0732, -77.0492),  # JESUS MARIA
    "150114": (-12.0867, -76.9474),  # LA MOLINA
    "150115": (-12.0667, -77.0167),  # LA VICTORIA
    "150116": (-12.0843, -77.0334),  # LINCE
    "150117": (-11.9658, -77.0742),  # LOS OLIVOS
    "150118": (-11.9444, -76.7000),  # LURIGANCHO (Chosica)
    "150119": (-12.2769, -76.8731),  # LURIN
    "150120": (-12.0900, -77.0728),  # MAGDALENA DEL MAR
    "150121": (-12.0775, -77.0631),  # PUEBLO LIBRE
    "150122": (-12.1196, -77.0289),  # MIRAFLORES
    "150123": (-12.2197, -76.8506),  # PACHACAMAC
    "150124": (-12.4839, -76.7989),  # PUCUSANA
    "150125": (-11.8631, -77.0742),  # PUENTE PIEDRA
    "150126": (-12.3361, -76.8208),  # PUNTA HERMOSA
    "150127": (-12.3692, -76.7886),  # PUNTA NEGRA
    "150128": (-12.0289, -77.0344),  # RIMAC
    "150129": (-12.3897, -76.7794),  # SAN BARTOLO
    "150130": (-12.1090, -77.0030),  # SAN BORJA
    "150131": (-12.0959, -77.0364),  # SAN ISIDRO
    "150132": (-11.9819, -76.9989),  # SAN JUAN DE LURIGANCHO
    "150133": (-12.1592, -76.9706),  # SAN JUAN DE MIRAFLORES
    "150134": (-12.0769, -76.9978),  # SAN LUIS
    "150135": (-12.0033, -77.0808),  # SAN MARTIN DE PORRES
    "150136": (-12.0775, -77.0931),  # SAN MIGUEL
    "150137": (-12.0464, -76.9742),  # SANTA ANITA
    "150138": (-12.4131, -76.7747),  # SANTA MARIA DEL MAR
    "150139": (-11.7944, -77.1486),  # SANTA ROSA
    "150140": (-12.1481, -76.9914),  # SANTIAGO DE SURCO
    "150141": (-12.1133, -77.0179),  # SURQUILLO
    "150142": (-12.2125, -76.9389),  # VILLA EL SALVADOR
    "150143": (-12.1631, -76.9347),  # VILLA MARIA DEL TRIUNFO
    # Callao
    "070101": (-12.0566, -77.1181),  # CALLAO
    "070102": (-12.0606, -77.1209),  # BELLAVISTA
    "070103": (-12.0511, -77.1083),  # CARMEN DE LA LEGUA REYNOSO
    "070104": (-12.0703, -77.1170),  # LA PERLA
    "070105": (-12.0700, -77.1647),  # LA PUNTA
    "070106": (-11.8617, -77.1175),  # VENTANILLA
    "070107": (-11.8595, -77.1308),  # MI PERU
}


def main() -> int:
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            print(f"Cargando centroides para {len(CENTROIDES)} distritos...")
            for ubigeo, (lat, lon) in CENTROIDES.items():
                cur.execute(
                    "UPDATE distrito SET centroide_lat = %s, centroide_lon = %s WHERE ubigeo = %s",
                    (lat, lon, ubigeo)
                )
            conn.commit()
            cur.execute("SELECT COUNT(*) AS n FROM distrito WHERE centroide_lat IS NOT NULL")
            print(f"  distritos con centroide: {cur.fetchone()[0]}")

            print("\nAsignando lat/lon a obras como fallback = centroide distrito...")
            cur.execute("""
                UPDATE obra o
                SET latitud = d.centroide_lat,
                    longitud = d.centroide_lon,
                    geom_fuente = COALESCE(o.geom_fuente, 'centroide_distrito')
                FROM distrito d
                WHERE o.distrito_id = d.id
                  AND o.latitud IS NULL
                  AND d.centroide_lat IS NOT NULL
            """)
            n = cur.rowcount
            conn.commit()
            print(f"  obras actualizadas con lat/lon fallback: {n}")

            cur.execute("""
                SELECT geom_fuente, COUNT(*) FROM obra
                WHERE latitud IS NOT NULL GROUP BY geom_fuente ORDER BY 2 DESC
            """)
            print("\nDistribución geom_fuente:")
            for r in cur.fetchall():
                print(f"  {r[0] or '(null)':<25}: {r[1]:>6}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
