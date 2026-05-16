"""Vista de contratista: RUC + obras + procedimientos + compras menores."""
from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/contratistas", tags=["contratistas"])


@router.get("")
def listar(
    q: Optional[str] = Query(None, description="Búsqueda por razón social"),
    con_paralizadas: bool = Query(False, description="Solo contratistas con al menos 1 obra paralizada"),
    limit: int = Query(50, ge=1, le=500),
) -> list[dict]:
    where = ["TRUE"]
    params: list = []
    if q:
        where.append("(c.razon_social ILIKE %s OR c.ruc = %s)")
        params += [f"%{q}%", q]
    if con_paralizadas:
        where.append("EXISTS (SELECT 1 FROM obra o WHERE o.contratista_id = c.id AND o.existe_paralizacion)")
    return fetch_all(f"""
        SELECT c.id, c.ruc, c.razon_social, c.estado_ruc, c.tiene_sancion,
               (SELECT COUNT(*) FROM obra o WHERE o.contratista_id = c.id) AS total_obras,
               (SELECT COUNT(*) FROM obra o WHERE o.contratista_id = c.id AND o.existe_paralizacion) AS obras_paralizadas,
               (SELECT COALESCE(SUM(o.monto_contrato), 0)::bigint FROM obra o WHERE o.contratista_id = c.id) AS monto_total
        FROM contratista c
        WHERE {' AND '.join(where)}
        ORDER BY obras_paralizadas DESC, total_obras DESC
        LIMIT %s
    """, tuple(params + [limit]))


@router.get("/{ruc}")
def ficha(ruc: str) -> dict:
    c = fetch_one(
        "SELECT id, ruc, razon_social, estado_ruc, tiene_sancion, fuente_sancion FROM contratista WHERE ruc = %s",
        (ruc,)
    )
    if not c:
        raise HTTPException(404, "Contratista no encontrado")

    obras = fetch_all("""
        SELECT o.id, o.codigo_infobras, o.nombre, o.estado_ejecucion,
               o.fecha_inicio, o.fecha_fin_programada, o.avance_fisico_real,
               o.monto_contrato, o.existe_paralizacion,
               o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
               o.confirmada_contraloria_2025,
               d.distrito, d.ubigeo AS distrito_ubigeo,
               e.nombre AS entidad
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN entidad e ON e.id = o.entidad_id
        WHERE o.contratista_id = %s
        ORDER BY o.fecha_inicio DESC NULLS LAST
    """, (c["id"],))

    # Concentración en compras menores ≤8 UIT (pendiente Pentaho, ya está la tabla)
    concentracion = fetch_all("""
        WITH ordenes_entidad AS (
            SELECT entidad_id, COUNT(*) AS total_ordenes_entidad,
                   COALESCE(SUM(monto_soles), 0)::bigint AS monto_total_entidad
            FROM orden_compra_servicio
            WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY entidad_id
        ),
        ordenes_ruc_entidad AS (
            SELECT entidad_id, COUNT(*) AS n_ordenes,
                   COALESCE(SUM(monto_soles), 0)::bigint AS monto_ruc
            FROM orden_compra_servicio
            WHERE contratista_id = %s
              AND fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY entidad_id
        )
        SELECT e.id AS entidad_id, e.nombre AS entidad,
               r.n_ordenes, r.monto_ruc,
               oe.total_ordenes_entidad, oe.monto_total_entidad,
               ROUND(100.0 * r.n_ordenes / NULLIF(oe.total_ordenes_entidad, 0), 2) AS pct_ordenes,
               ROUND(100.0 * r.monto_ruc / NULLIF(oe.monto_total_entidad, 0), 2) AS pct_monto
        FROM ordenes_ruc_entidad r
        JOIN ordenes_entidad oe ON oe.entidad_id = r.entidad_id
        JOIN entidad e ON e.id = r.entidad_id
        WHERE r.n_ordenes > 0
        ORDER BY pct_monto DESC NULLS LAST
    """, (c["id"],))

    procedimientos = fetch_all("""
        SELECT id, ocid, fuente_ocds, objeto, monto_referencial, monto_adjudicado,
               fecha_buena_pro, fecha_contrato, numero_postores, estado
        FROM procedimiento_seleccion
        WHERE contratista_id = %s
        ORDER BY fecha_buena_pro DESC NULLS LAST
        LIMIT 100
    """, (c["id"],))

    return {
        **c,
        "obras": obras,
        "concentracion_compras_menores_12m": concentracion,
        "procedimientos_seleccion": procedimientos,
    }


@router.get("/{ruc}/exportar")
def exportar(ruc: str):
    c = fetch_one("SELECT id, ruc, razon_social FROM contratista WHERE ruc = %s", (ruc,))
    if not c:
        raise HTTPException(404, "Contratista no encontrado")

    obras = fetch_all("""
        SELECT o.codigo_infobras, o.nombre, o.estado_ejecucion, o.fecha_inicio,
               o.fecha_fin_programada, o.avance_fisico_real, o.monto_contrato,
               o.existe_paralizacion, o.clasificacion_paralizacion::text AS clasificacion,
               o.confirmada_contraloria_2025,
               d.distrito, e.nombre AS entidad,
               CASE WHEN o.codigo_infobras IS NOT NULL
                    THEN 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.codigo_infobras
               END AS infobras_url
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN entidad e ON e.id = o.entidad_id
        WHERE o.contratista_id = %s
        ORDER BY o.fecha_inicio DESC NULLS LAST
    """, (c["id"],))

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["RUC", c["ruc"], "razon_social", c["razon_social"]])
    writer.writerow([])
    if obras:
        writer.writerow(list(obras[0].keys()))
        for o in obras:
            writer.writerow(list(o.values()))
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="contratista_{ruc}.csv"'},
    )
