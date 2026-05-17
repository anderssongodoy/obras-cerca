"""Endpoints de listas priorizadas — sospechosos, sectores, series."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..db import fetch_all

router = APIRouter(prefix="/api", tags=["sospechosos"])


@router.get("/contratistas/sospechosos")
def sospechosos(
    min_pct: float = Query(15.0, ge=0, le=100, description="Umbral mínimo de % monto"),
    min_ordenes: int = Query(5, ge=1, description="Mín. órdenes del RUC en la entidad"),
    min_total_entidad: int = Query(20, ge=1, description="Mín. órdenes totales de la entidad para que el % tenga sentido"),
    limit: int = Query(30, ge=1, le=200),
) -> list[dict]:
    """Top contratistas con concentración anormal en compras ≤8 UIT (últimos 12 meses).

    Esto materializa el patrón del MD maestro §4.3:
    'cuando un contratista concentra una proporción anormal de las compras
    menores de una misma entidad, se muestra una señal de revisión'.
    """
    return fetch_all("""
        WITH por_entidad AS (
            SELECT entidad_id, COUNT(*)::int AS total_ent, SUM(monto_soles) AS monto_ent
            FROM orden_compra_servicio
            WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY entidad_id
        ),
        por_ruc_ent AS (
            SELECT entidad_id, contratista_id,
                   COUNT(*)::int AS n_ruc, SUM(monto_soles) AS monto_ruc
            FROM orden_compra_servicio
            WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
              AND contratista_id IS NOT NULL
            GROUP BY entidad_id, contratista_id
        )
        SELECT c.ruc, c.razon_social, e.id AS entidad_id, e.nombre AS entidad,
               r.n_ruc, r.monto_ruc::bigint,
               pe.total_ent, pe.monto_ent::bigint,
               ROUND(100.0 * r.n_ruc / NULLIF(pe.total_ent, 0), 2) AS pct_ordenes,
               ROUND(100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0), 2) AS pct_monto
        FROM por_ruc_ent r
        JOIN por_entidad pe ON pe.entidad_id = r.entidad_id
        JOIN contratista c ON c.id = r.contratista_id
        JOIN entidad e ON e.id = r.entidad_id
        WHERE pe.total_ent >= %s
          AND r.n_ruc >= %s
          AND (100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0)) >= %s
        ORDER BY pct_monto DESC NULLS LAST
        LIMIT %s
    """, (min_total_entidad, min_ordenes, min_pct, limit))


@router.get("/sectores")
def sectores() -> list[dict]:
    """Agregado por sector en el ámbito MVP."""
    return fetch_all("""
        SELECT
            COALESCE(o.sector, '(sin sector)') AS sector,
            COUNT(*) AS total_obras,
            COUNT(*) FILTER (WHERE o.existe_paralizacion) AS paralizadas,
            COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS paral_vigente,
            COALESCE(SUM(o.monto_contrato), 0)::bigint AS monto_total,
            COALESCE(SUM(o.monto_contrato) FILTER (WHERE o.existe_paralizacion), 0)::bigint AS monto_paralizado,
            ROUND(AVG(o.avance_fisico_real)::numeric, 1) AS avance_promedio
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        WHERE d.ambito_mvp
        GROUP BY 1
        ORDER BY paral_vigente DESC, total_obras DESC
    """)


@router.get("/stats/series-paralizadas")
def series_paralizadas() -> list[dict]:
    """Serie temporal de paralizaciones por año (cuándo se reportó).

    Útil para gráfico de tendencia. Solo considera obras con
    clasificación no-zombie para no inflar con el cementerio.
    """
    return fetch_all("""
        SELECT
            EXTRACT(YEAR FROM op.fecha_paralizacion)::int AS anio,
            COUNT(*) AS paralizaciones,
            COUNT(*) FILTER (WHERE o.clasificacion_paralizacion = 'vigente') AS vigentes,
            COUNT(*) FILTER (WHERE o.confirmada_contraloria_2025) AS confirmadas
        FROM obra_paralizacion op
        JOIN obra o ON o.id = op.obra_id
        JOIN distrito d ON d.id = o.distrito_id
        WHERE d.ambito_mvp AND op.fecha_paralizacion IS NOT NULL
        GROUP BY anio
        ORDER BY anio
    """)


@router.get("/search")
def search(
    q: str = Query(..., min_length=3, description="Texto libre — busca obras, contratistas, entidades"),
    limit: int = Query(15, ge=1, le=50),
) -> dict:
    """Búsqueda transversal por texto — obras + contratistas + entidades."""
    obras = fetch_all("""
        SELECT 'obra' AS tipo, o.id, o.codigo_infobras, o.nombre AS texto,
               d.distrito, o.existe_paralizacion,
               o.clasificacion_paralizacion::text AS clasificacion
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        WHERE d.ambito_mvp AND o.nombre ILIKE %s
        ORDER BY o.existe_paralizacion DESC, o.id DESC
        LIMIT %s
    """, (f"%{q}%", limit))
    contratistas = fetch_all("""
        SELECT 'contratista' AS tipo, id, ruc, razon_social AS texto
        FROM contratista
        WHERE razon_social ILIKE %s OR ruc = %s
        LIMIT %s
    """, (f"%{q}%", q, limit))
    entidades = fetch_all("""
        SELECT 'entidad' AS tipo, id, nombre AS texto
        FROM entidad
        WHERE nombre_norm ILIKE %s
        LIMIT %s
    """, (f"%{q.upper()}%", limit))
    return {"obras": obras, "contratistas": contratistas, "entidades": entidades}
