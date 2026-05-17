"""Endpoints específicos para alimentar el mapa del frontend."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..db import fetch_all

router = APIRouter(prefix="/api/mapa", tags=["mapa"])


@router.get("/heatmap")
def heatmap() -> list[dict]:
    """Datos agregados por distrito MVP — peso = obras paralizadas vigentes + confirmadas."""
    return fetch_all("""
        SELECT
            d.ubigeo, d.distrito, d.provincia,
            d.centroide_lat AS lat, d.centroide_lon AS lon,
            COUNT(o.id) AS total_obras,
            COUNT(*) FILTER (WHERE o.existe_paralizacion) AS paralizadas,
            COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS paral_vigente,
            COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025 AND o.existe_paralizacion) AS confirmadas,
            COALESCE(SUM(o.monto_contrato) FILTER (WHERE o.existe_paralizacion), 0)::bigint AS monto_paralizado
        FROM distrito d
        LEFT JOIN obra o ON o.distrito_id = d.id
        WHERE d.ambito_mvp
        GROUP BY d.id
        ORDER BY paral_vigente DESC, confirmadas DESC
    """)


@router.get("/bounds")
def obras_en_bounds(
    nw_lat: float = Query(..., description="Esquina noroeste — latitud"),
    nw_lon: float = Query(..., description="Esquina noroeste — longitud"),
    se_lat: float = Query(..., description="Esquina sureste — latitud"),
    se_lon: float = Query(..., description="Esquina sureste — longitud"),
    solo_paralizadas: bool = Query(False),
    solo_vigentes: bool = Query(False),
    limit: int = Query(2000, ge=10, le=10000),
) -> dict:
    """Obras dentro del bounding box visible del mapa.

    El mapa pasa las esquinas tras un pan/zoom y recibe solo lo visible.
    """
    where = ["d.ambito_mvp",
             "o.latitud BETWEEN %s AND %s",
             "o.longitud BETWEEN %s AND %s"]
    params: list = [se_lat, nw_lat, nw_lon, se_lon]
    if solo_paralizadas:
        where.append("o.existe_paralizacion")
    if solo_vigentes:
        where.append("o.clasificacion_paralizacion = 'vigente'")

    sql = f"""
        SELECT o.id, o.codigo_infobras, o.nombre,
               o.latitud, o.longitud,
               o.existe_paralizacion,
               o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
               o.confirmada_contraloria_2025,
               o.avance_fisico_real, o.monto_contrato,
               d.distrito, d.ubigeo AS distrito_ubigeo
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        WHERE {' AND '.join(where)}
        ORDER BY o.existe_paralizacion DESC, o.id
        LIMIT %s
    """
    rows = fetch_all(sql, tuple(params + [limit]))
    return {"count": len(rows), "items": rows}
