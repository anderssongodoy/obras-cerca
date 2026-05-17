from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Query
from ..db import fetch_all

router = APIRouter(prefix="/api/senales", tags=["senales"])


@router.get("")
def listar(
    tipo: Optional[str] = None,
    ubigeo: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
) -> list[dict]:
    where = ["s.activa"]; params: list = []
    if tipo:
        where.append("s.tipo = %s::tipo_senal")
        params.append(tipo)
    if ubigeo:
        where.append("d.ubigeo = %s")
        params.append(ubigeo)
    return fetch_all(f"""
        SELECT s.id, s.tipo::text AS tipo, s.titulo, s.resumen, s.score, s.formula, s.evidencia,
               s.detectada_en, s.obra_id, s.cui,
               o.nobr_id, d.distrito, d.ubigeo,
               e.nombre AS entidad, c.razon_social AS contratista
        FROM senal_revision s
        LEFT JOIN obra o     ON o.id = s.obra_id
        LEFT JOIN proyecto_mef p ON p.cui = COALESCE(s.cui, o.cui)
        LEFT JOIN distrito d   ON d.id = p.distrito_id
        LEFT JOIN entidad e    ON e.id = COALESCE(s.entidad_id, p.entidad_id)
        LEFT JOIN contratista c ON c.id = s.contratista_id
        WHERE {' AND '.join(where)}
        ORDER BY s.score DESC NULLS LAST
        LIMIT %s
    """, tuple(params + [limit]))
