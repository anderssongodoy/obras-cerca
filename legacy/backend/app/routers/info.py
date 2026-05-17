"""Meta-información sobre el estado de los datos.

Útil para que el frontend muestre "Datos actualizados al ..."
y un footer de transparencia con las fuentes.
"""
from __future__ import annotations

from fastapi import APIRouter

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/info", tags=["info"])


@router.get("/data-freshness")
def data_freshness() -> dict:
    fuentes = fetch_all("""
        SELECT nombre, descripcion, url, ultima_ingestion, filas_ingestadas, notas
        FROM fuente_dato ORDER BY ultima_ingestion DESC NULLS LAST
    """)
    pentaho = fetch_one("""
        SELECT MIN(fecha_emision) AS desde, MAX(fecha_emision) AS hasta, COUNT(*) AS filas
        FROM orden_compra_servicio
    """)
    geo = fetch_one("""
        SELECT
            COUNT(*) FILTER (WHERE geom_fuente = 'nominatim') AS geocodificadas,
            COUNT(*) FILTER (WHERE geom_fuente = 'centroide_distrito') AS con_centroide,
            COUNT(*) FILTER (WHERE geom_fuente IS NULL) AS sin_geom
        FROM obra
    """)
    return {
        "fuentes": fuentes,
        "pentaho_ordenes_cobertura": pentaho,
        "geocoding": geo,
    }


@router.get("/senales/resumen")
def senales_resumen() -> dict:
    """Resumen rápido del estado de las señales — útil para el header del feed."""
    por_tipo = fetch_all("""
        SELECT tipo::text, COUNT(*) AS total,
               COUNT(*) FILTER (WHERE evidencia ? 'codigo_infobras') AS con_obra,
               MAX(detectada_en) AS ultima
        FROM senal_revision WHERE activa
        GROUP BY tipo ORDER BY total DESC
    """)
    por_distrito = fetch_all("""
        SELECT d.distrito, d.ubigeo,
               COUNT(*) AS senales,
               COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS vigentes,
               COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025) AS confirmadas
        FROM senal_revision s
        LEFT JOIN obra o ON o.id = s.obra_id
        LEFT JOIN distrito d ON d.id = o.distrito_id
        WHERE s.activa AND d.ambito_mvp
        GROUP BY d.id, d.distrito, d.ubigeo
        ORDER BY vigentes DESC, senales DESC
        LIMIT 10
    """)
    return {"por_tipo": por_tipo, "top_distritos": por_distrito}
