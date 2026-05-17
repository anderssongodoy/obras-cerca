"""Por cada CUI en BD sin datos completos, llama a los 4 endpoints MEF
y guarda toda la data cruzada.

Endpoints:
    1) traeDetInvSSI       -> datos generales Invierte.pe (1 row proyecto_mef)
    2) verInfObras2        -> NOBR_IDs vinculados (1..N rows obra, con obra_padre_id para saldos)
    3) traeContratoSeaceDWH -> contratos SEACE (N rows procedimiento_seleccion)
    4) traeListaParalizaPublico -> paralizaciones (N rows paralizacion_oficial)

Uso:
    python 04_enriquecer_cui.py                # todos los pendientes
    python 04_enriquecer_cui.py --limit 50     # primeros 50
    python 04_enriquecer_cui.py --cui 2171549  # uno específico (debug)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import date

import psycopg
from app.clients.mef import MEFClient, _dotnet_date

from _common import norm

DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")


ESTADO_MAP = {
    "ACTIVO":                  "ACTIVO",
    "DESACTIVADO PERMANENTE":  "DESACTIVADO_PERMANENTE",
    "DESACTIVADO TEMPORAL":    "DESACTIVADO_TEMPORAL",
    "CERRADO":                 "CERRADO",
}


def _to_num(v):
    if v is None or v == "":
        return None
    try:
        f = float(v)
        return f if f != 0 else None
    except (TypeError, ValueError):
        return None


def _enum_estado(s: str | None) -> str:
    if not s:
        return "NO_VERIFICADO"
    return ESTADO_MAP.get(s.strip().upper(), "NO_VERIFICADO")


def upsert_proyecto(conn, cui: int, det: dict) -> None:
    """Llena proyecto_mef con datos de traeDetInvSSI."""
    conn.execute("""
        UPDATE proyecto_mef SET
            cod_snip          = COALESCE(%s, cod_snip),
            nombre_inversion  = COALESCE(NULLIF(%s, ''), nombre_inversion),
            sector            = COALESCE(%s, sector),
            funcion           = COALESCE(%s, funcion),
            nivel_gobierno    = COALESCE(%s, nivel_gobierno),
            estado            = %s::estado_proyecto_mef,
            situacion         = COALESCE(%s, situacion),
            marco             = COALESCE(%s, marco),
            mto_viable        = COALESCE(%s, mto_viable),
            costo_actualizado = COALESCE(%s, costo_actualizado),
            dev_acumulado     = COALESCE(%s, dev_acumulado),
            pim_ano_vigente   = COALESCE(%s, pim_ano_vigente),
            dev_ano_vigente   = COALESCE(%s, dev_ano_vigente),
            fec_viable        = COALESCE(%s, fec_viable),
            fec_ini_ejec      = COALESCE(%s, fec_ini_ejec),
            fec_fin_ejec      = COALESCE(%s, fec_fin_ejec),
            avance_fisico_mef = COALESCE(%s, avance_fisico_mef),
            modal_ejec        = COALESCE(%s, modal_ejec),
            beneficiarios     = COALESCE(%s, beneficiarios),
            verificado_mef_en = NOW()
        WHERE cui = %s
    """, (
        det.get("COD_SNIP"),
        det.get("NOMBRE_INVERSION") or det.get("DES_INVERSION"),
        det.get("SECTOR"), det.get("FUNCION"), det.get("NIVEL"),
        _enum_estado(det.get("ESTADO")),
        det.get("SITUACION"), det.get("MARCO"),
        _to_num(det.get("MTO_VIABLE")),
        _to_num(det.get("COSTO_ACTUALIZADO")),
        _to_num(det.get("DEV_ACUMULADO")),
        _to_num(det.get("PIM_ANO_VIGENTE")),
        _to_num(det.get("DEV_ANO_VIGENTE")),
        _dotnet_date(det.get("FEC_VIABLE")),
        _dotnet_date(det.get("FEC_INI_EJ") or det.get("FEC_INI_EJEC")),
        _dotnet_date(det.get("FEC_FIN_EJ") or det.get("FEC_FIN_EJEC")),
        _to_num(det.get("AVAN_FISICO")) if _to_num(det.get("AVAN_FISICO")) and _to_num(det.get("AVAN_FISICO")) >= 0 else None,
        det.get("MODAL_EJEC"),
        int(det.get("BENEFICIARIO") or 0) or None,
        cui,
    ))


def upsert_obras(conn, cui: int, obras: list[dict]) -> int:
    """Llena/actualiza tabla obra desde verInfObras2."""
    if not obras:
        return 0
    insertadas = 0
    # primero la obra "principal" (la que tenga avance, o la primera)
    for o in obras:
        nobr = o.get("NOBR_ID") or o.get("CDP1_CODIGO")
        if not nobr:
            continue
        try:
            nobr = int(nobr)
        except (ValueError, TypeError):
            continue
        conn.execute("""
            INSERT INTO obra
                (nobr_id, cui, descripcion, direccion, modalidad_ejecucion,
                 estado_obra_bulk, avance_fisico_infobras, fuente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'mef_ssi'::fuente_dato_tipo)
            ON CONFLICT (nobr_id) DO UPDATE SET
                cui = EXCLUDED.cui,
                descripcion = COALESCE(EXCLUDED.descripcion, obra.descripcion),
                direccion = COALESCE(EXCLUDED.direccion, obra.direccion),
                modalidad_ejecucion = COALESCE(EXCLUDED.modalidad_ejecucion, obra.modalidad_ejecucion),
                avance_fisico_infobras = COALESCE(EXCLUDED.avance_fisico_infobras, obra.avance_fisico_infobras)
        """, (
            nobr, cui,
            (o.get("COBR_DESCRI") or "")[:500] or None,
            (o.get("COBR_DIRECCION") or "")[:300] or None,
            o.get("COPA_DESCRI"),
            o.get("ESTADO_OBRA") or o.get("cdp1_estadoobra"),
            _to_num(o.get("AVANCEFISICO_REAL") or o.get("AVAN_FISICO_REAL")),
        ))
        insertadas += 1

    # Marcar saldos: si hay >1 obra, las que tengan descripción con "saldo"
    # o "partidas no ejecutadas" se vinculan al original (la de mayor avance)
    if len(obras) > 1:
        conn.execute("""
            WITH ordered AS (
                SELECT id, nobr_id, descripcion, avance_fisico_infobras,
                       ROW_NUMBER() OVER (
                           ORDER BY avance_fisico_infobras DESC NULLS LAST, nobr_id ASC
                       ) AS rn
                FROM obra WHERE cui = %s
            ),
            padre AS (SELECT id FROM ordered WHERE rn = 1)
            UPDATE obra SET obra_padre_id = (SELECT id FROM padre)
            WHERE cui = %s
              AND id <> (SELECT id FROM padre)
              AND (descripcion ILIKE '%%saldo%%' OR descripcion ILIKE '%%no ejecutad%%' OR descripcion ILIKE '%%deficient%%')
        """, (cui, cui))
    return insertadas


def upsert_contratos(conn, cui: int, contratos: list[dict]) -> int:
    n = 0
    for c in contratos:
        ruc = (c.get("RUC") or c.get("CONTRATISTA_RUC") or "").strip()
        razon = (c.get("CONTRATISTA") or c.get("RAZON_SOCIAL") or "").strip()
        contratista_id = None
        if ruc and re.match(r"^\d{8,11}$", ruc):
            r = conn.execute("""
                INSERT INTO contratista (ruc, razon_social, razon_social_norm)
                VALUES (%s, %s, %s)
                ON CONFLICT (ruc) DO UPDATE SET razon_social = EXCLUDED.razon_social
                RETURNING id
            """, (ruc, razon or f"(sin nombre, RUC {ruc})", norm(razon))).fetchone()
            contratista_id = r[0]
        conn.execute("""
            INSERT INTO procedimiento_seleccion
                (cui, contratista_id, nomenclatura, objeto_contractual,
                 numero_contrato, fecha_convocatoria, fecha_buena_pro, fecha_suscripcion,
                 valor_referencial, monto_contratado, url_contrato_pdf, fuente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'seace_ocds_oece'::fuente_dato_tipo)
        """, (
            cui, contratista_id,
            c.get("PROCESO") or c.get("NOMENCLATURA"),
            (c.get("OBJETO") or c.get("DESCRIPCION") or "")[:500] or None,
            c.get("NUM_CONTRATO") or c.get("NUMERO_CONTRATO"),
            _dotnet_date(c.get("FECHA_CONVOCATORIA")),
            _dotnet_date(c.get("FECHA_BUENA_PRO")),
            _dotnet_date(c.get("FECHA_SUSCRIPCION") or c.get("FECHA_CONTRATO")),
            _to_num(c.get("VALOR_REFERENCIAL")),
            _to_num(c.get("MONTO_CONTRATADO") or c.get("MONTO")),
            c.get("URL_CONTRATO") or c.get("RUTA_CONTRATO"),
        ))
        n += 1
    return n


def upsert_paralizaciones(conn, cui: int, paral: list[dict]) -> int:
    if not paral:
        return 0
    for p in paral:
        conn.execute("""
            INSERT INTO paralizacion_oficial
                (cui, fecha_paralizacion, fecha_reinicio, dias_paralizado, causal, estado, detalle, fuente)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'mef_ssi'::fuente_dato_tipo)
        """, (
            cui,
            _dotnet_date(p.get("FECHA_PARALIZACION") or p.get("FEC_PARALIZACION")),
            _dotnet_date(p.get("FECHA_REINICIO")),
            int(p.get("DIAS") or p.get("DIAS_PARALIZADO") or 0) or None,
            p.get("CAUSAL") or p.get("MOTIVO"),
            p.get("ESTADO"),
            json.dumps(p, default=str),
        ))
    return len(paral)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cui", type=int, help="Procesar un único CUI (debug)")
    ap.add_argument("--limit", type=int, default=0, help="Máximo de CUIs a procesar (0 = todos)")
    ap.add_argument("--rate", type=float, default=0.5)
    args = ap.parse_args()

    mef = MEFClient()
    with psycopg.connect(DSN) as conn:
        if args.cui:
            cuis = [args.cui]
        else:
            cur = conn.execute(
                "SELECT cui FROM proyecto_mef WHERE verificado_mef_en IS NULL ORDER BY cui"
                + (f" LIMIT {int(args.limit)}" if args.limit else "")
            )
            cuis = [r[0] for r in cur.fetchall()]
        print(f"CUIs a enriquecer: {len(cuis)}")

        ok = fail = 0
        for i, cui in enumerate(cuis, 1):
            det = mef.trae_det_inv_ssi(cui)
            if det:
                upsert_proyecto(conn, cui, det)
            obras = mef.ver_info_obras2(cui)
            n_obras = upsert_obras(conn, cui, obras)
            contratos = mef.trae_contrato_seace_dwh(cui)
            n_cont = upsert_contratos(conn, cui, contratos)
            paral = mef.trae_lista_paraliza_publico(cui)
            n_par = upsert_paralizaciones(conn, cui, paral)
            conn.commit()

            estado = (det or {}).get("ESTADO", "(?)")
            ok_flag = 1 if det else 0
            ok += ok_flag
            fail += (1 - ok_flag)
            print(f"  [{i:>4}/{len(cuis)}] CUI {cui}  estado={estado[:20]:<20}  obras={n_obras} contratos={n_cont} paraliz={n_par}")
            time.sleep(args.rate)

        print(f"\nOK: {ok}  FAIL: {fail}")
    return 0


if __name__ == "__main__":
    main()
