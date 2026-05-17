from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/contratistas", tags=["contratistas"])


@router.get("")
def listar(q: Optional[str] = None, limit: int = Query(50, ge=1, le=500)) -> list[dict]:
    where = ["TRUE"]; params: list = []
    if q:
        where.append("(razon_social_norm ILIKE %s OR ruc = %s)")
        params += [f"%{q.upper()}%", q]
    return fetch_all(f"""
        SELECT c.id, c.ruc, c.razon_social, c.tiene_sancion_oece,
               (SELECT COUNT(*) FROM obra o WHERE o.contratista_id = c.id) AS obras,
               (SELECT COUNT(*) FROM procedimiento_seleccion p WHERE p.contratista_id = c.id) AS procedimientos
        FROM contratista c
        WHERE {' AND '.join(where)}
        ORDER BY obras DESC
        LIMIT %s
    """, tuple(params + [limit]))


@router.get("/{ruc}")
def ficha(ruc: str) -> dict:
    c = fetch_one("SELECT * FROM contratista WHERE ruc = %s", (ruc,))
    if not c:
        raise HTTPException(404, "contratista no encontrado")
    c["obras"] = fetch_all("""
        SELECT id, nobr_id, descripcion AS nombre, avance_fisico_infobras, estado_obra_wfs,
               (SELECT distrito FROM distrito d JOIN proyecto_mef p ON p.distrito_id = d.id WHERE p.cui = obra.cui) AS distrito
        FROM obra WHERE contratista_id = %s ORDER BY id DESC LIMIT 50
    """, (c["id"],))
    c["procedimientos"] = fetch_all("""
        SELECT nomenclatura, fecha_buena_pro, monto_contratado, estado, url_contrato_pdf
        FROM procedimiento_seleccion WHERE contratista_id = %s
        ORDER BY fecha_buena_pro DESC NULLS LAST LIMIT 50
    """, (c["id"],))
    return c


@router.get("/sospechosos/top")
def sospechosos(min_pct: float = Query(20.0, ge=0, le=100), limit: int = Query(30, ge=1, le=200)) -> list[dict]:
    return fetch_all("""
        SELECT contratista_id, evidencia ->> 'ruc' AS ruc,
               evidencia ->> 'razon_social' AS razon_social,
               evidencia ->> 'entidad' AS entidad,
               (evidencia ->> 'pct_monto')::numeric AS pct_monto,
               (evidencia ->> 'n_ordenes_ruc')::int AS n_ordenes,
               (evidencia ->> 'monto_ruc')::numeric AS monto_ruc
        FROM senal_revision
        WHERE tipo = 'concentracion_menores' AND activa
        ORDER BY score DESC
        LIMIT %s
    """, (limit,))
