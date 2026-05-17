"""Obras: listado con filtros geográficos + ficha + exportar caso CSV."""
from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/obras", tags=["obras"])

# Haversine en SQL puro (radio_tierra = 6371000 m)
HAVERSINE_SQL = (
    "(2 * 6371000 * asin(sqrt("
    "power(sin(radians((o.latitud - %s)/2)), 2) + "
    "cos(radians(%s)) * cos(radians(o.latitud)) * "
    "power(sin(radians((o.longitud - %s)/2)), 2)"
    ")))"
)


@router.get("")
def listar(
    ubigeo: Optional[str] = Query(None, description="Filtro por distrito (ubigeo)"),
    lat: Optional[float] = Query(None, description="Latitud para 'obras cerca de mí'"),
    lon: Optional[float] = Query(None, description="Longitud para 'obras cerca de mí'"),
    radio_m: int = Query(1000, ge=100, le=20000, description="Radio en metros (default 1km)"),
    paralizadas: Optional[bool] = Query(None, description="Solo paralizadas (true) o no paralizadas (false)"),
    clasificacion: Optional[str] = Query(None, description="vigente/dudosa/zombie"),
    contratista_ruc: Optional[str] = Query(None),
    entidad_id: Optional[int] = Query(None),
    sector: Optional[str] = Query(None),
    estado: Optional[str] = Query(None, description="Filtro por estado_ejecucion (LIKE)"),
    q: Optional[str] = Query(None, description="Búsqueda libre por nombre de obra"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> dict:
    """Listado de obras con filtros combinables.

    Para 'obras cerca de mí': pasa `lat` + `lon` + `radio_m` (Haversine en SQL).
    """
    where: list[str] = ["d.ambito_mvp"]
    where_params: list = []

    if ubigeo:
        where.append("d.ubigeo = %s")
        where_params.append(ubigeo)
    if paralizadas is True:
        where.append("o.existe_paralizacion")
    elif paralizadas is False:
        where.append("NOT o.existe_paralizacion")
    if clasificacion:
        where.append("o.clasificacion_paralizacion = %s::clasif_paralizacion")
        where_params.append(clasificacion)
    if contratista_ruc:
        where.append("c.ruc = %s")
        where_params.append(contratista_ruc)
    if entidad_id:
        where.append("o.entidad_id = %s")
        where_params.append(entidad_id)
    if sector:
        where.append("o.sector ILIKE %s")
        where_params.append(f"%{sector}%")
    if estado:
        where.append("o.estado_ejecucion ILIKE %s")
        where_params.append(f"%{estado}%")
    if q:
        where.append("o.nombre ILIKE %s")
        where_params.append(f"%{q}%")

    geo_enabled = lat is not None and lon is not None
    if geo_enabled:
        where.append("o.latitud IS NOT NULL AND o.longitud IS NOT NULL")
        where.append(f"{HAVERSINE_SQL} <= %s")
        where_params += [lat, lat, lon, radio_m]

    where_sql = " AND ".join(where) if where else "TRUE"

    select_distancia = f"{HAVERSINE_SQL} AS distancia_m" if geo_enabled else "NULL::float AS distancia_m"
    select_params: list = [lat, lat, lon] if geo_enabled else []

    order = (
        "distancia_m ASC NULLS LAST, o.existe_paralizacion DESC, o.id DESC"
        if geo_enabled
        else "o.existe_paralizacion DESC, o.codigo_infobras DESC"
    )

    sql = f"""
        SELECT
            o.id, o.codigo_infobras, o.nombre, o.estado_ejecucion,
            o.naturaleza, o.sector, o.fecha_inicio, o.fecha_fin_programada,
            o.fecha_ultimo_avance,
            o.avance_fisico_real, o.avance_fisico_programado,
            o.porcentaje_ejecucion_financiera,
            o.monto_contrato, o.monto_ejecutado,
            o.existe_paralizacion, o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
            o.confirmada_contraloria_2025,
            o.dias_paralizada_real, o.dias_sin_avance,
            o.latitud, o.longitud, o.direccion, o.tipo_ubicacion,
            e.nombre AS entidad_nombre,
            c.ruc AS contratista_ruc, c.razon_social AS contratista_nombre,
            d.distrito AS distrito_nombre, d.provincia, d.ubigeo AS distrito_ubigeo,
            {select_distancia}
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN entidad e ON e.id = o.entidad_id
        LEFT JOIN contratista c ON c.id = o.contratista_id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT %s OFFSET %s
    """
    sql_params = tuple(select_params + where_params + [limit, offset])

    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN contratista c ON c.id = o.contratista_id
        WHERE {where_sql}
    """
    total = fetch_one(count_sql, tuple(where_params))["total"]
    rows = fetch_all(sql, sql_params)
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


@router.get("/{obra_id}")
def ficha(obra_id: int) -> dict:
    """Ficha completa de una obra (lo que se abre al click)."""
    row = fetch_one("""
        SELECT
            o.*, o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
            e.nombre AS entidad_nombre, e.nivel_gobierno, e.sector AS entidad_sector,
            c.ruc AS contratista_ruc, c.razon_social AS contratista_nombre,
            sup.ruc AS supervisor_ruc, sup.razon_social AS supervisor_nombre,
            d.distrito AS distrito_nombre, d.provincia, d.departamento, d.ubigeo AS distrito_ubigeo,
            CASE WHEN o.codigo_infobras IS NOT NULL
                 THEN 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.codigo_infobras
            END AS infobras_url
        FROM obra o
        LEFT JOIN entidad e ON e.id = o.entidad_id
        LEFT JOIN contratista c ON c.id = o.contratista_id
        LEFT JOIN contratista sup ON sup.id = o.supervisor_id
        JOIN distrito d ON d.id = o.distrito_id
        WHERE o.id = %s
    """, (obra_id,))
    if not row:
        raise HTTPException(404, "Obra no encontrada")

    paralizacion = fetch_one("""
        SELECT fecha_paralizacion, dias_paralizado, dias_paralizada_real,
               causal, comentarios, avance_fisico_al_par, avance_fin_al_par,
               confirmada_contraloria_2025
        FROM obra_paralizacion
        WHERE obra_id = %s
        ORDER BY fecha_paralizacion DESC NULLS LAST
        LIMIT 1
    """, (obra_id,))
    row["paralizacion"] = paralizacion

    senales = fetch_all("""
        SELECT id, tipo::text, titulo, explicacion, score, formula, evidencia, detectada_en
        FROM senal_revision
        WHERE obra_id = %s AND activa
        ORDER BY score DESC NULLS LAST
    """, (obra_id,))
    row["senales"] = senales

    return row


@router.get("/{obra_id}/exportar")
def exportar_caso(obra_id: int):
    """Descarga CSV con la evidencia auditable de la obra y sus señales."""
    obra = fetch_one("""
        SELECT o.id, o.codigo_infobras, o.nombre, o.estado_ejecucion, o.naturaleza,
               o.sector, o.fecha_inicio, o.fecha_fin_programada, o.fecha_ultimo_avance,
               o.avance_fisico_real, o.avance_fisico_programado, o.porcentaje_ejecucion_financiera,
               o.monto_contrato, o.monto_ejecutado,
               o.existe_paralizacion, o.clasificacion_paralizacion::text AS clasificacion_paralizacion,
               o.confirmada_contraloria_2025, o.dias_paralizada_real, o.dias_sin_avance,
               o.latitud, o.longitud, o.direccion,
               e.nombre AS entidad,
               c.ruc AS contratista_ruc, c.razon_social AS contratista,
               d.distrito, d.provincia, d.departamento,
               CASE WHEN o.codigo_infobras IS NOT NULL
                    THEN 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.codigo_infobras
               END AS fuente_oficial_infobras
        FROM obra o
        LEFT JOIN entidad e ON e.id = o.entidad_id
        LEFT JOIN contratista c ON c.id = o.contratista_id
        JOIN distrito d ON d.id = o.distrito_id
        WHERE o.id = %s
    """, (obra_id,))
    if not obra:
        raise HTTPException(404, "Obra no encontrada")

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(list(obra.keys()))
    writer.writerow(list(obra.values()))
    buf.write("\n")
    writer.writerow(["--- senales activas ---"])
    senales = fetch_all("""
        SELECT tipo::text, titulo, explicacion, score, formula, evidencia, detectada_en
        FROM senal_revision WHERE obra_id = %s AND activa
        ORDER BY score DESC
    """, (obra_id,))
    if senales:
        writer.writerow(list(senales[0].keys()))
        for s in senales:
            writer.writerow(list(s.values()))

    buf.seek(0)
    fname = f"obra_{obra['codigo_infobras'] or obra_id}_evidencia.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
