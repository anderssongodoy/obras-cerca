"""Para cada NOBR_ID en BD, valida contra Infobras (WFS + ficha + informes de control).

WFS te da:
    - lat/lon real (más preciso que centroide)
    - estado oficial Contraloría ('En Ejecución'/'Paralizada'/'Finalizada')

Ficha pública te da:
    - estado visible al ciudadano (puede diferir del bulk)
    - último avance, contratista, montos

InformeControl te da:
    - PDFs de auditorías (Control Concurrente, Orientación de Oficio, etc)

Uso:
    python 05_verificar_nobr.py             # todos los pendientes
    python 05_verificar_nobr.py --nobr 42593
    python 05_verificar_nobr.py --limit 100
"""
from __future__ import annotations

import argparse
import os
import time
from datetime import datetime

import psycopg
from app.clients.infobras import InfobrasClient
from app.clients.mef import _dotnet_date

from _common import norm

DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")


def parse_pct(s: str | None) -> float | None:
    if not s:
        return None
    try:
        return float(s.replace("%", "").replace(",", ".").strip())
    except ValueError:
        return None


def parse_monto(s: str | None) -> float | None:
    if not s:
        return None
    import re
    m = re.search(r"[\d,]+(?:\.\d+)?", s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_fecha_es(s: str | None):
    if not s:
        return None
    import re
    # "MAR 2026" -> aprox mes/año
    m = re.match(r"^([A-ZÁÉÍÓÚ]+)\s+(\d{4})$", s.strip().upper())
    if m:
        meses = {"ENE":1,"FEB":2,"MAR":3,"ABR":4,"MAY":5,"JUN":6,
                 "JUL":7,"AGO":8,"SEP":9,"SET":9,"OCT":10,"NOV":11,"DIC":12}
        mes_n = meses.get(m.group(1)[:3])
        if mes_n:
            from datetime import date
            try:
                return date(int(m.group(2)), mes_n, 1)
            except ValueError:
                return None
    return _dotnet_date(s)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--nobr", type=int)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--rate", type=float, default=0.5)
    args = ap.parse_args()

    ibras = InfobrasClient()
    with psycopg.connect(DSN) as conn:
        if args.nobr:
            cur = conn.execute(
                "SELECT id, nobr_id FROM obra WHERE nobr_id = %s", (args.nobr,)
            )
        else:
            sql = "SELECT id, nobr_id FROM obra WHERE verificado_wfs_en IS NULL ORDER BY id"
            if args.limit:
                sql += f" LIMIT {int(args.limit)}"
            cur = conn.execute(sql)
        obras = cur.fetchall()
        print(f"Obras a verificar: {len(obras)}")

        for i, (oid, nobr) in enumerate(obras, 1):
            wfs = ibras.wfs_obra(nobr)
            ficha = ibras.ficha_obra(nobr)
            informes = ibras.informes_control(nobr)

            # Actualizar obra con WFS + ficha
            if wfs and wfs.get("lat") and wfs.get("lon"):
                conn.execute("""
                    UPDATE obra SET
                        latitud = %s, longitud = %s, geom_fuente = 'wfs_infobras',
                        estado_obra_wfs = %s,
                        verificado_wfs_en = NOW()
                    WHERE id = %s
                """, (wfs["lat"], wfs["lon"], wfs.get("estado"), oid))
            else:
                # Marcar como verificado WFS aunque no tenga features (para no reintentar infinito)
                conn.execute("UPDATE obra SET verificado_wfs_en = NOW() WHERE id = %s", (oid,))

            if ficha:
                conn.execute("""
                    UPDATE obra SET
                        estado_obra_ficha = COALESCE(%s, estado_obra_ficha),
                        avance_fisico_infobras = COALESCE(%s, avance_fisico_infobras),
                        fecha_ult_avance = COALESCE(%s, fecha_ult_avance),
                        fecha_inicio = COALESCE(%s, fecha_inicio),
                        fecha_fin_programada = COALESCE(%s, fecha_fin_programada),
                        numero_contrato = COALESCE(%s, numero_contrato),
                        fecha_contrato = COALESCE(%s, fecha_contrato),
                        monto_aprobacion = COALESCE(%s, monto_aprobacion),
                        verificado_ficha_en = NOW()
                    WHERE id = %s
                """, (
                    ficha.get("ESTADO DE OBRA"),
                    parse_pct(ficha.get("PORCENTAJE DE AVANCE FÍSICO")),
                    parse_fecha_es(ficha.get("FECHA DEL ULTIMO AVANCE")),
                    _dotnet_date(ficha.get("FECHA DE INICIO")),
                    _dotnet_date(ficha.get("FECHA DE FIN")),
                    ficha.get("CONTRATO"),
                    _dotnet_date(ficha.get("FECHA DE CONTRATO")),
                    parse_monto(ficha.get("MONTO DE APROBACIÓN")),
                    oid,
                ))

            # Informes de control
            n_inf = 0
            for inf in informes:
                cres = None
                if inf.get("RutaPublicacion"):
                    import re
                    m = re.search(r"CRES_CODIGO=([^&]+)", inf["RutaPublicacion"])
                    if m: cres = m.group(1)
                conn.execute("""
                    INSERT INTO informe_control
                        (obra_id, anio, nro_informe, titulo, tipo_servicio, modalidad,
                         fecha_emision, fecha_publicacion, url_pdf_resumen, url_pdf_completo, cres_codigo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cres_codigo) DO NOTHING
                """, (
                    oid,
                    int(inf.get("Anio") or 0) or None,
                    inf.get("NroInforme"),
                    inf.get("TituloInforme"),
                    inf.get("TipoServicio"),
                    inf.get("Modalidad"),
                    _dotnet_date(inf.get("FechaEmision")),
                    _dotnet_date(inf.get("FechaPublicacion")),
                    inf.get("RutaPublicacion"),
                    inf.get("RutaInforme"),
                    cres,
                ))
                n_inf += 1
            if n_inf:
                conn.execute("UPDATE obra SET existe_informe_control = TRUE WHERE id = %s", (oid,))
            conn.commit()

            wfs_estado = (wfs or {}).get("estado", "?")
            print(f"  [{i:>4}/{len(obras)}] NOBR={nobr}  wfs={wfs_estado:<14}  informes={n_inf}")
            time.sleep(args.rate)
    return 0


if __name__ == "__main__":
    main()
