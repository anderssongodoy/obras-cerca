"""Endpoints de obras: listado, ficha con cruce de fuentes, verificación live, explicación IA, exportar."""
from __future__ import annotations

import csv, io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..db import fetch_all, fetch_one, get_conn
from ..clients.mef import MEFClient
from ..clients.infobras import InfobrasClient
from ..llm import generar_obra

router = APIRouter(prefix="/api/obras", tags=["obras"])


HAVERSINE = (
    "(2 * 6371000 * asin(sqrt("
    "power(sin(radians((latitud - %s)/2)), 2) + "
    "cos(radians(%s)) * cos(radians(latitud)) * "
    "power(sin(radians((longitud - %s)/2)), 2))))"
)


@router.get("")
def listar(
    ubigeo: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radio_m: int = Query(2000, ge=100, le=20000),
    paralizadas_wfs: Optional[bool] = None,
    inactivas_mef: Optional[bool] = None,
    con_saldos: Optional[bool] = None,
    contratista_ruc: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
) -> dict:
    where = ["TRUE"]
    params: list = []
    if ubigeo:
        where.append("distrito_ubigeo = %s")
        params.append(ubigeo)
    if paralizadas_wfs:
        where.append("estado_obra_wfs = 'Paralizada'")
    if inactivas_mef:
        where.append("estado_proyecto_mef = 'DESACTIVADO_PERMANENTE'")
    if con_saldos:
        where.append("es_saldo_obra")
    if contratista_ruc:
        where.append("contratista_ruc = %s")
        params.append(contratista_ruc)
    if q:
        where.append("(nombre_obra ILIKE %s OR nombre_inversion ILIKE %s)")
        params += [f"%{q}%", f"%{q}%"]

    geo = lat is not None and lon is not None
    if geo:
        where.append("latitud IS NOT NULL AND longitud IS NOT NULL")
        where.append(f"{HAVERSINE} <= %s")
        params_geo_where = [lat, lat, lon, radio_m]
    else:
        params_geo_where = []

    where_sql = " AND ".join(where)
    distancia_sql = f"{HAVERSINE} AS distancia_m" if geo else "NULL::float AS distancia_m"
    params_select = [lat, lat, lon] if geo else []
    order = ("distancia_m ASC, " if geo else "") + "id DESC"

    sql = f"""
        SELECT *, {distancia_sql}
        FROM v_obra_mvp
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT %s OFFSET %s
    """
    total = fetch_one(
        f"SELECT COUNT(*) AS t FROM v_obra_mvp WHERE {where_sql}",
        tuple(params + params_geo_where),
    )["t"]
    rows = fetch_all(sql, tuple(params_select + params + params_geo_where + [limit, offset]))
    return {"total": total, "limit": limit, "offset": offset, "items": rows}


@router.get("/{obra_id}")
def ficha(obra_id: int) -> dict:
    row = fetch_one("SELECT * FROM v_obra_ficha WHERE id = %s", (obra_id,))
    if not row:
        raise HTTPException(404, "obra no encontrada")

    row["saldos_hijos"] = fetch_all("""
        SELECT id, nobr_id, descripcion, avance_fisico_infobras, estado_obra_wfs,
               numero_contrato, monto_contrato
        FROM obra WHERE obra_padre_id = %s
    """, (obra_id,))

    row["procedimientos"] = fetch_all("""
        SELECT ps.id, ps.nomenclatura, ps.objeto_contractual,
               ps.fecha_buena_pro, ps.fecha_suscripcion,
               ps.valor_referencial, ps.monto_contratado, ps.estado, ps.url_contrato_pdf,
               c.ruc AS contratista_ruc, c.razon_social AS contratista
        FROM procedimiento_seleccion ps
        LEFT JOIN contratista c ON c.id = ps.contratista_id
        WHERE ps.cui = %s
        ORDER BY ps.fecha_buena_pro DESC NULLS LAST
    """, (row["cui"],))

    row["paralizaciones"] = fetch_all("""
        SELECT fecha_paralizacion, fecha_reinicio, dias_paralizado, causal, estado
        FROM paralizacion_oficial WHERE cui = %s
        ORDER BY fecha_paralizacion DESC NULLS LAST
    """, (row["cui"],))

    row["informes_control"] = fetch_all("""
        SELECT anio, nro_informe, titulo, tipo_servicio, modalidad,
               fecha_publicacion, url_pdf_resumen, url_pdf_completo
        FROM informe_control WHERE obra_id = %s
        ORDER BY fecha_publicacion DESC NULLS LAST
    """, (obra_id,))

    row["senales"] = fetch_all("""
        SELECT tipo::text, titulo, resumen, score, formula, evidencia
        FROM senal_revision
        WHERE activa AND (obra_id = %s OR cui = %s)
        ORDER BY score DESC NULLS LAST
    """, (obra_id, row["cui"]))

    return row


@router.get("/{obra_id}/verificar")
def verificar_live(obra_id: int) -> dict:
    """Cruce LIVE en tiempo real: pregunta a MEF + WFS + ficha pública AHORA mismo.

    Útil para mostrar al jurado "miren, no es data vieja — estos números vienen de la API
    oficial en este instante". No actualiza la BD, solo devuelve lo que ven los oficiales.
    """
    row = fetch_one("SELECT id, nobr_id, cui FROM obra WHERE id = %s", (obra_id,))
    if not row:
        raise HTTPException(404, "obra no encontrada")

    mef = MEFClient()
    inf = InfobrasClient()

    det = mef.trae_det_inv_ssi(row["cui"])
    nobrs = mef.ver_info_obras2(row["cui"])
    paral = mef.trae_lista_paraliza_publico(row["cui"])
    contratos = mef.trae_contrato_seace_dwh(row["cui"])

    wfs = inf.wfs_obra(row["nobr_id"])
    ficha_inf = inf.ficha_obra(row["nobr_id"])
    informes = inf.informes_control(row["nobr_id"])

    return {
        "obra_id": obra_id, "nobr_id": row["nobr_id"], "cui": row["cui"],
        "fuentes": {
            "mef_invierte_pe":  det,
            "mef_nobr_vinculados": [{"nobr": x.get("NOBR_ID") or x.get("CDP1_CODIGO"),
                                       "modal": x.get("COPA_DESCRI"),
                                       "descripcion": x.get("COBR_DESCRI")} for x in nobrs],
            "mef_paralizaciones": paral,
            "seace_contratos": contratos,
            "infobras_wfs": wfs,
            "infobras_ficha_publica": ficha_inf,
            "contraloria_informes": informes,
        },
        "urls": {
            "mef_ssi": f"https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo={row['cui']}",
            "infobras_ficha": f"https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId={row['nobr_id']}",
            "infobras_informes": f"https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/InformeControl?obraId={row['nobr_id']}",
        },
    }


@router.get("/{obra_id}/explicacion")
def explicacion(obra_id: int, refresh: bool = Query(False)) -> dict:
    if not refresh:
        cached = fetch_one("""
            SELECT provider, modelo, texto, tokens_input, tokens_output, generado_en
            FROM explicacion_ia WHERE entidad_tipo='obra' AND entidad_id=%s AND audiencia='ciudadano'
        """, (obra_id,))
        if cached:
            return {"cached": True, **cached}

    base = fetch_one("SELECT * FROM v_obra_ficha WHERE id = %s", (obra_id,))
    if not base:
        raise HTTPException(404, "obra no encontrada")

    saldos = fetch_one("SELECT COUNT(*) AS n FROM obra WHERE obra_padre_id = %s", (obra_id,))["n"]
    n_inf = fetch_one("SELECT COUNT(*) AS n FROM informe_control WHERE obra_id = %s", (obra_id,))["n"]

    hechos = {
        "nombre": base.get("nombre_obra") or base.get("nombre_inversion"),
        "distrito": base.get("distrito_nombre"),
        "entidad": base.get("entidad_nombre"),
        "estado_mef": (base.get("estado_proyecto_mef") or "").upper() if base.get("estado_proyecto_mef") else None,
        "estado_wfs": base.get("estado_obra_wfs"),
        "avance_mef": float(base["avance_fisico_mef"]) if base.get("avance_fisico_mef") is not None else None,
        "avance_infobras": float(base["avance_fisico_infobras"]) if base.get("avance_fisico_infobras") is not None else None,
        "sobrecosto_pct": float(base["sobrecosto_pct"]) if base.get("sobrecosto_pct") is not None else None,
        "monto_viable": float(base["mto_viable"]) if base.get("mto_viable") else None,
        "costo_actualizado": float(base["costo_actualizado"]) if base.get("costo_actualizado") else None,
        "saldos_hijos": saldos,
        "informes_control": n_inf,
    }

    gen = generar_obra(hechos)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO explicacion_ia
                (entidad_tipo, entidad_id, audiencia, provider, modelo, texto, tokens_input, tokens_output)
            VALUES ('obra', %s, 'ciudadano', %s, %s, %s, %s, %s)
            ON CONFLICT (entidad_tipo, entidad_id, audiencia) DO UPDATE SET
                provider=EXCLUDED.provider, modelo=EXCLUDED.modelo, texto=EXCLUDED.texto,
                tokens_input=EXCLUDED.tokens_input, tokens_output=EXCLUDED.tokens_output,
                generado_en=NOW()
        """, (obra_id, gen["provider"], gen["modelo"], gen["texto"], gen["tokens_input"], gen["tokens_output"]))
    return {"cached": False, **gen, "hechos_usados": hechos}


@router.get("/{obra_id}/exportar")
def exportar_csv(obra_id: int):
    obra = fetch_one("SELECT * FROM v_obra_ficha WHERE id = %s", (obra_id,))
    if not obra:
        raise HTTPException(404, "obra no encontrada")

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(list(obra.keys())); w.writerow(list(obra.values()))
    w.writerow([])
    w.writerow(["--- saldos hijos ---"])
    saldos = fetch_all("SELECT * FROM obra WHERE obra_padre_id = %s", (obra_id,))
    if saldos:
        w.writerow(list(saldos[0].keys()))
        for s in saldos: w.writerow(list(s.values()))
    w.writerow([])
    w.writerow(["--- informes de control ---"])
    inf = fetch_all("SELECT * FROM informe_control WHERE obra_id = %s", (obra_id,))
    if inf:
        w.writerow(list(inf[0].keys()))
        for i in inf: w.writerow(list(i.values()))
    buf.seek(0)
    fname = f"obra_{obra.get('nobr_id', obra_id)}_evidencia.csv"
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="{fname}"'})
