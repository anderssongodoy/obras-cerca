"""Distritos del ámbito MVP + resumen por distrito."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/distritos", tags=["distritos"])


@router.get("")
def listar() -> list[dict]:
    """Lista los 50 distritos del ámbito MVP con centroides para el mapa."""
    return fetch_all("""
        SELECT id, ubigeo, departamento, provincia, distrito,
               centroide_lat AS lat, centroide_lon AS lon
        FROM distrito
        WHERE ambito_mvp
        ORDER BY provincia, distrito
    """)


@router.get("/resumen")
def resumen_general() -> list[dict]:
    """Resumen de obras + paralizadas por distrito (para sidebar/mapa)."""
    return fetch_all("""
        SELECT d.id, d.ubigeo, d.distrito, d.provincia,
               d.centroide_lat AS lat, d.centroide_lon AS lon,
               COUNT(o.id) AS total_obras,
               COUNT(*) FILTER (WHERE o.existe_paralizacion) AS paralizadas,
               COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS paralizadas_vigentes,
               COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025 AND o.existe_paralizacion) AS confirmadas_contraloria,
               COUNT(*) FILTER (WHERE o.estado_ejecucion ILIKE '%%ejecuc%%') AS en_ejecucion,
               COUNT(*) FILTER (WHERE o.avance_fisico_real >= 100) AS terminadas,
               COALESCE(SUM(o.monto_contrato), 0)::bigint AS monto_total,
               COALESCE(SUM(o.monto_contrato) FILTER (WHERE o.existe_paralizacion), 0)::bigint AS monto_paralizado
        FROM distrito d
        LEFT JOIN obra o ON o.distrito_id = d.id
        WHERE d.ambito_mvp
        GROUP BY d.id
        ORDER BY paralizadas_vigentes DESC, total_obras DESC
    """)


@router.get("/{ubigeo}")
def detalle(ubigeo: str) -> dict:
    d = fetch_one("""
        SELECT id, ubigeo, departamento, provincia, distrito,
               centroide_lat AS lat, centroide_lon AS lon, ambito_mvp
        FROM distrito WHERE ubigeo = %s
    """, (ubigeo,))
    if not d:
        raise HTTPException(404, "Distrito no encontrado")

    agg = fetch_one("""
        SELECT
            COUNT(*) AS total_obras,
            COUNT(*) FILTER (WHERE existe_paralizacion) AS paralizadas,
            COUNT(*) FILTER (WHERE clasificacion_paralizacion = 'vigente') AS paralizadas_vigentes,
            COUNT(*) FILTER (WHERE confirmada_contraloria_2025 AND existe_paralizacion) AS confirmadas_contraloria,
            COALESCE(SUM(monto_contrato), 0)::bigint AS monto_total,
            COALESCE(SUM(monto_contrato) FILTER (WHERE existe_paralizacion), 0)::bigint AS monto_paralizado,
            ROUND(AVG(avance_fisico_real)::numeric, 1) AS avance_promedio
        FROM obra WHERE distrito_id = %s
    """, (d["id"],))
    return {**d, "resumen": agg}
