"""Capa de explicación ciudadana (IA solo redacta — MD §6.5).

Cacheada en explicacion_obra / explicacion_contratista para no quemar tokens.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..db import fetch_all, fetch_one, get_conn
from ..llm import generar_contratista, generar_obra

router = APIRouter(tags=["explicacion"])


def _hechos_obra(obra_id: int) -> dict | None:
    row = fetch_one("""
        SELECT o.id, o.codigo_infobras, o.nombre, o.naturaleza, o.sector,
               o.fecha_inicio, o.fecha_fin_programada,
               o.avance_fisico_real, o.porcentaje_ejecucion_financiera,
               o.monto_contrato, o.monto_ejecutado,
               o.existe_paralizacion,
               o.clasificacion_paralizacion::text AS clasificacion,
               o.dias_paralizada_real, o.confirmada_contraloria_2025 AS confirmada_contraloria,
               d.distrito, e.nombre AS entidad
        FROM obra o
        JOIN distrito d ON d.id = o.distrito_id
        LEFT JOIN entidad e ON e.id = o.entidad_id
        WHERE o.id = %s
    """, (obra_id,))
    if not row:
        return None
    par = fetch_one("""
        SELECT causal, fecha_paralizacion FROM obra_paralizacion
        WHERE obra_id = %s ORDER BY fecha_paralizacion DESC NULLS LAST LIMIT 1
    """, (obra_id,))
    if par:
        row["causal"] = par["causal"]
        row["fecha_paralizacion"] = par["fecha_paralizacion"]
    for k, v in list(row.items()):
        if v is None:
            row.pop(k)
    return row


def _hechos_contratista(ruc: str) -> dict | None:
    c = fetch_one("""
        SELECT c.id, c.ruc, c.razon_social,
               (SELECT COUNT(*) FROM obra o WHERE o.contratista_id = c.id) AS total_obras,
               (SELECT COUNT(*) FROM obra o WHERE o.contratista_id = c.id AND o.existe_paralizacion) AS obras_paralizadas
        FROM contratista c WHERE c.ruc = %s
    """, (ruc,))
    if not c:
        return None
    top = fetch_one("""
        WITH por_entidad AS (
            SELECT entidad_id, SUM(monto_soles) AS monto_ent
            FROM orden_compra_servicio
            WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY entidad_id
        ),
        por_ruc AS (
            SELECT entidad_id, COUNT(*) AS n_ord, SUM(monto_soles) AS monto_ruc
            FROM orden_compra_servicio
            WHERE contratista_id = %s
              AND fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
            GROUP BY entidad_id
        )
        SELECT e.nombre AS entidad, r.n_ord AS n_ordenes,
               ROUND(100.0 * r.monto_ruc / NULLIF(pe.monto_ent, 0), 2) AS pct_monto
        FROM por_ruc r
        JOIN por_entidad pe ON pe.entidad_id = r.entidad_id
        JOIN entidad e ON e.id = r.entidad_id
        ORDER BY pct_monto DESC NULLS LAST
        LIMIT 1
    """, (c["id"],))
    if top:
        c["top_concentracion"] = top
    return c


@router.get("/api/obras/{obra_id}/explicacion")
def obra_explicacion(obra_id: int, refresh: bool = Query(False, description="Ignora cache y regenera")):
    if not refresh:
        cached = fetch_one(
            "SELECT provider, modelo, texto, tokens_input, tokens_output, generado_en "
            "FROM explicacion_obra WHERE obra_id = %s AND tipo = 'ficha'",
            (obra_id,)
        )
        if cached:
            return {"cached": True, **cached}

    hechos = _hechos_obra(obra_id)
    if not hechos:
        raise HTTPException(404, "Obra no encontrada")

    gen = generar_obra(hechos)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO explicacion_obra (obra_id, tipo, provider, modelo, texto, tokens_input, tokens_output)
            VALUES (%s, 'ficha', %s, %s, %s, %s, %s)
            ON CONFLICT (obra_id, tipo) DO UPDATE SET
                provider = EXCLUDED.provider,
                modelo = EXCLUDED.modelo,
                texto = EXCLUDED.texto,
                tokens_input = EXCLUDED.tokens_input,
                tokens_output = EXCLUDED.tokens_output,
                generado_en = NOW()
        """, (obra_id, gen["provider"], gen["modelo"], gen["texto"],
              gen["tokens_input"], gen["tokens_output"]))
    return {"cached": False, **gen, "hechos_usados": hechos}


@router.get("/api/contratistas/{ruc}/explicacion")
def contratista_explicacion(ruc: str, refresh: bool = Query(False)):
    hechos = _hechos_contratista(ruc)
    if not hechos:
        raise HTTPException(404, "Contratista no encontrado")
    cid = hechos["id"]

    if not refresh:
        cached = fetch_one(
            "SELECT provider, modelo, texto, tokens_input, tokens_output, generado_en "
            "FROM explicacion_contratista WHERE contratista_id = %s AND tipo = 'ficha'",
            (cid,)
        )
        if cached:
            return {"cached": True, **cached}

    gen = generar_contratista(hechos)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO explicacion_contratista (contratista_id, tipo, provider, modelo, texto, tokens_input, tokens_output)
            VALUES (%s, 'ficha', %s, %s, %s, %s, %s)
            ON CONFLICT (contratista_id, tipo) DO UPDATE SET
                provider = EXCLUDED.provider, modelo = EXCLUDED.modelo,
                texto = EXCLUDED.texto, tokens_input = EXCLUDED.tokens_input,
                tokens_output = EXCLUDED.tokens_output, generado_en = NOW()
        """, (cid, gen["provider"], gen["modelo"], gen["texto"],
              gen["tokens_input"], gen["tokens_output"]))
    return {"cached": False, **gen, "hechos_usados": hechos}
