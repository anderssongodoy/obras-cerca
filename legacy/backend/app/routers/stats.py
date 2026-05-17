"""KPIs para la landing y el header del MVP."""
from __future__ import annotations

from fastapi import APIRouter

from ..db import fetch_one, fetch_all

router = APIRouter(tags=["stats"])


@router.get("/api/stats")
def stats() -> dict:
    """Resumen agregado del ámbito MVP."""
    totales = fetch_one("""
        SELECT
            COUNT(*) AS obras,
            COUNT(*) FILTER (WHERE existe_paralizacion) AS paralizadas,
            COUNT(*) FILTER (WHERE clasificacion_paralizacion = 'vigente') AS paralizadas_vigentes,
            COUNT(*) FILTER (WHERE clasificacion_paralizacion = 'dudosa') AS paralizadas_dudosas,
            COUNT(*) FILTER (WHERE clasificacion_paralizacion = 'zombie') AS paralizadas_zombies,
            COUNT(*) FILTER (WHERE confirmada_contraloria_2025) AS confirmadas_contraloria,
            COALESCE(SUM(monto_contrato), 0)::bigint AS monto_total_contrato,
            COALESCE(SUM(monto_contrato) FILTER (WHERE existe_paralizacion), 0)::bigint AS monto_paralizado
        FROM obra
    """)
    catalogos = fetch_one("""
        SELECT
            (SELECT COUNT(*) FROM distrito WHERE ambito_mvp) AS distritos_mvp,
            (SELECT COUNT(*) FROM entidad) AS entidades,
            (SELECT COUNT(*) FROM contratista) AS contratistas,
            (SELECT COUNT(*) FROM senal_revision WHERE activa) AS senales_activas
    """)
    top_paralizadas = fetch_all("""
        SELECT d.distrito, d.ubigeo,
               COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS vigentes,
               COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025 AND o.existe_paralizacion) AS confirmadas
        FROM distrito d
        LEFT JOIN obra o ON o.distrito_id = d.id
        WHERE d.ambito_mvp
        GROUP BY d.id
        ORDER BY vigentes DESC, confirmadas DESC
        LIMIT 8
    """)
    return {
        "totales": totales,
        "catalogos": catalogos,
        "top_distritos_paralizacion_vigente": top_paralizadas,
    }
