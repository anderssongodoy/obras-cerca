"""Señales de revisión — feed de cosas que merecen mirada."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..db import fetch_all

router = APIRouter(prefix="/api/senales", tags=["senales"])


@router.get("")
def listar(
    tipo: Optional[str] = Query(None, description="paralizacion / paralizacion_prolongada / concentracion_menores / ..."),
    ubigeo: Optional[str] = Query(None, description="Filtrar por distrito"),
    solo_confirmadas: bool = Query(False, description="Solo señales con sello Contraloría dic-2025"),
    solo_vigentes: bool = Query(True, description="Excluir 'zombies' (paralizaciones viejas sin actualizar)"),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    where = ["s.activa"]
    params: list = []
    if tipo:
        where.append("s.tipo = %s::tipo_senal")
        params.append(tipo)
    if ubigeo:
        where.append("d.ubigeo = %s")
        params.append(ubigeo)
    if solo_confirmadas:
        where.append("o.confirmada_contraloria_2025")
    if solo_vigentes:
        where.append("(o.clasificacion_paralizacion IS NULL OR o.clasificacion_paralizacion <> 'zombie')")
    sql = f"""
        SELECT
            s.id, s.tipo::text AS tipo, s.titulo, s.explicacion, s.score, s.formula, s.evidencia,
            s.detectada_en,
            o.id AS obra_id, o.codigo_infobras, o.nombre AS obra_nombre,
            o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
            o.confirmada_contraloria_2025,
            o.dias_paralizada_real,
            d.distrito, d.ubigeo AS distrito_ubigeo,
            c.ruc AS contratista_ruc, c.razon_social AS contratista_nombre,
            e.nombre AS entidad_nombre
        FROM senal_revision s
        LEFT JOIN obra o ON o.id = s.obra_id
        LEFT JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN contratista c ON c.id = COALESCE(s.contratista_id, o.contratista_id)
        LEFT JOIN entidad e ON e.id = COALESCE(s.entidad_id, o.entidad_id)
        WHERE {' AND '.join(where)}
        ORDER BY o.confirmada_contraloria_2025 DESC,
                 (o.clasificacion_paralizacion = 'vigente') DESC,
                 s.score DESC NULLS LAST
        LIMIT %s
    """
    return fetch_all(sql, tuple(params + [limit]))
