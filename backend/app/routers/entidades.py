"""Entidades — autocomplete y filtros."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from ..db import fetch_all

router = APIRouter(prefix="/api/entidades", tags=["entidades"])


@router.get("")
def listar(
    q: Optional[str] = Query(None, min_length=2, description="Autocomplete por nombre"),
    limit: int = Query(20, ge=1, le=100),
) -> list[dict]:
    where = ["TRUE"]
    params: list = []
    if q:
        where.append("e.nombre_norm ILIKE %s")
        params.append(f"%{q.upper()}%")
    return fetch_all(f"""
        SELECT e.id, e.nombre, e.nivel_gobierno, e.sector,
               (SELECT COUNT(*) FROM obra o WHERE o.entidad_id = e.id) AS total_obras,
               (SELECT COUNT(*) FROM obra o WHERE o.entidad_id = e.id AND o.existe_paralizacion) AS obras_paralizadas
        FROM entidad e
        WHERE {' AND '.join(where)}
        ORDER BY total_obras DESC
        LIMIT %s
    """, tuple(params + [limit]))
