"""Mini-ingesta para tener data en la demo sin esperar el pipeline completo.

Insertar manualmente unos CUIs verificados y correr el flujo MEF + Infobras
sobre ellos. Cada CUI trae sus NOBR_IDs, contratos, paralizaciones,
e incluso PDFs de Contraloría.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg
import time

from app.clients.mef import MEFClient
from app.clients.infobras import InfobrasClient
import sys as _s
_s.path.insert(0, str(Path(__file__).resolve().parent))
# Importar las funciones de enriquecimiento y verificación
import importlib.util
spec = importlib.util.spec_from_file_location("e", str(Path(__file__).parent / "04_enriquecer_cui.py"))
mod_e = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod_e)
spec = importlib.util.spec_from_file_location("v", str(Path(__file__).parent / "05_verificar_nobr.py"))
mod_v = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod_v)

DSN = "host=localhost user=postgres password=123 dbname=obrascerca_v2"

# CUIs de obras conocidas en Lima Metro
CUIS_DEMO = [
    2171549,  # JNJ — Mejoramiento (paralizada con saldos 553414 y 553656)
    2412541,  # JNJ — Expediente Judicial Electrónico
    2403507,  # SEDAPAL Colector Chorrillos (DESACTIVADO PERMANENTE)
    2325535,  # San Isidro — Seguridad Ciudadana (caso del compañero, NOBR 545958)
    2673653,  # SJL — Pasos a desnivel (caso 536317)
]


def main() -> int:
    mef = MEFClient()
    inf = InfobrasClient()

    with psycopg.connect(DSN) as conn:
        # 1. Insertar CUIs como proyecto_mef shell
        for cui in CUIS_DEMO:
            conn.execute("""
                INSERT INTO proyecto_mef (cui, nombre_inversion, estado)
                VALUES (%s, '(pendiente)', 'NO_VERIFICADO'::estado_proyecto_mef)
                ON CONFLICT (cui) DO NOTHING
            """, (cui,))
        conn.commit()
        print(f"Insertados {len(CUIS_DEMO)} CUIs en proyecto_mef")

        # 2. Para cada CUI, llamar a los 4 endpoints MEF
        for i, cui in enumerate(CUIS_DEMO, 1):
            print(f"\n[{i}/{len(CUIS_DEMO)}] Enriqueciendo CUI {cui}...")
            det = mef.trae_det_inv_ssi(cui)
            if det:
                mod_e.upsert_proyecto(conn, cui, det)
                print(f"  ESTADO MEF: {det.get('ESTADO')} | {det.get('NOMBRE_INVERSION', '')[:60]}")
            else:
                print("  (sin datos MEF)")
            obras = mef.ver_info_obras2(cui)
            n_o = mod_e.upsert_obras(conn, cui, obras)
            print(f"  Obras (NOBR_IDs): {n_o}")
            contratos = mef.trae_contrato_seace_dwh(cui)
            n_c = mod_e.upsert_contratos(conn, cui, contratos)
            print(f"  Contratos SEACE: {n_c}")
            paral = mef.trae_lista_paraliza_publico(cui)
            n_p = mod_e.upsert_paralizaciones(conn, cui, paral)
            print(f"  Paralizaciones MEF: {n_p}")
            conn.commit()
            time.sleep(0.5)

        # 3. Para cada NOBR_ID, verificar contra Infobras (WFS + ficha + InformeControl)
        cur = conn.execute("SELECT id, nobr_id FROM obra WHERE verificado_wfs_en IS NULL")
        obras_a_verificar = cur.fetchall()
        print(f"\nVerificando {len(obras_a_verificar)} NOBR_IDs contra Infobras...")
        for i, (oid, nobr) in enumerate(obras_a_verificar, 1):
            wfs = inf.wfs_obra(nobr)
            ficha = inf.ficha_obra(nobr)
            informes = inf.informes_control(nobr)

            if wfs and wfs.get("lat"):
                conn.execute("""
                    UPDATE obra SET latitud=%s, longitud=%s, geom_fuente='wfs_infobras',
                        estado_obra_wfs=%s, verificado_wfs_en=NOW()
                    WHERE id=%s
                """, (wfs["lat"], wfs["lon"], wfs.get("estado"), oid))
            else:
                conn.execute("UPDATE obra SET verificado_wfs_en=NOW() WHERE id=%s", (oid,))

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
                    WHERE id=%s
                """, (
                    ficha.get("ESTADO DE OBRA"),
                    mod_v.parse_pct(ficha.get("PORCENTAJE DE AVANCE FÍSICO")),
                    mod_v.parse_fecha_es(ficha.get("FECHA DEL ULTIMO AVANCE")),
                    mod_v.parse_fecha_es(ficha.get("FECHA DE INICIO")),
                    mod_v.parse_fecha_es(ficha.get("FECHA DE FIN")),
                    ficha.get("CONTRATO"),
                    mod_v.parse_fecha_es(ficha.get("FECHA DE CONTRATO")),
                    mod_v.parse_monto(ficha.get("MONTO DE APROBACIÓN")),
                    oid,
                ))

            for inf_data in informes:
                cres = None
                if inf_data.get("RutaPublicacion"):
                    import re
                    m = re.search(r"CRES_CODIGO=([^&]+)", inf_data["RutaPublicacion"])
                    if m: cres = m.group(1)
                from app.clients.mef import _dotnet_date
                conn.execute("""
                    INSERT INTO informe_control
                        (obra_id, anio, nro_informe, titulo, tipo_servicio, modalidad,
                         fecha_emision, fecha_publicacion, url_pdf_resumen, url_pdf_completo, cres_codigo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cres_codigo) DO NOTHING
                """, (
                    oid, int(inf_data.get("Anio") or 0) or None,
                    inf_data.get("NroInforme"), inf_data.get("TituloInforme"),
                    inf_data.get("TipoServicio"), inf_data.get("Modalidad"),
                    _dotnet_date(inf_data.get("FechaEmision")),
                    _dotnet_date(inf_data.get("FechaPublicacion")),
                    inf_data.get("RutaPublicacion"), inf_data.get("RutaInforme"), cres,
                ))
            if informes:
                conn.execute("UPDATE obra SET existe_informe_control=TRUE WHERE id=%s", (oid,))
            conn.commit()
            wfs_e = (wfs or {}).get("estado", "?")
            print(f"  [{i}/{len(obras_a_verificar)}] NOBR={nobr}  wfs={wfs_e}  informes={len(informes)}")
            time.sleep(0.5)

        # 4. Vincular proyectos con entidad existente
        conn.execute("""
            UPDATE proyecto_mef p
            SET entidad_id = e.id
            FROM entidad e
            WHERE p.entidad_id IS NULL AND e.nombre_norm = (
                SELECT UPPER(REGEXP_REPLACE(
                    UPPER(p2.nombre_inversion), '^.*ENTIDAD[^A-Z]*([A-Z ]+).*$', '\\1'))
                FROM proyecto_mef p2 WHERE p2.cui = p.cui
            )
        """)

        # 5. Asignar distrito_id en base a los datos WFS
        conn.execute("""
            UPDATE proyecto_mef p
            SET distrito_id = d.id
            FROM obra o
            JOIN distrito d ON UPPER(d.distrito) = UPPER((
                SELECT cdp1_distrito FROM (SELECT 'X' AS x) z WHERE FALSE
            ))
            WHERE o.cui = p.cui
        """)

        # mejor: sacar el distrito del WFS guardado en obra (latitud/longitud + nombre del distrito)
        # como ya tenemos lat/lon en obra, asignar distrito por proximidad
        conn.execute("""
            UPDATE proyecto_mef p SET distrito_id = (
                SELECT d.id FROM obra o
                JOIN distrito d ON d.ambito_mvp = TRUE
                WHERE o.cui = p.cui AND o.latitud IS NOT NULL
                ORDER BY (
                  power(o.latitud  - d.centroide_lat, 2) +
                  power(o.longitud - d.centroide_lon, 2)
                ) ASC
                LIMIT 1
            ) WHERE p.distrito_id IS NULL
        """)
        conn.commit()

        # Reporte
        cur = conn.execute("SELECT COUNT(*) FROM proyecto_mef WHERE verificado_mef_en IS NOT NULL")
        print(f"\nProyectos MEF verificados: {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM obra")
        print(f"Obras totales: {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM obra WHERE estado_obra_wfs = 'Paralizada'")
        print(f"Obras paralizadas (WFS): {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM informe_control")
        print(f"Informes de control: {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM procedimiento_seleccion")
        print(f"Procedimientos SEACE: {cur.fetchone()[0]}")
        cur = conn.execute("SELECT COUNT(*) FROM paralizacion_oficial")
        print(f"Paralizaciones MEF: {cur.fetchone()[0]}")
    return 0


if __name__ == "__main__":
    main()
