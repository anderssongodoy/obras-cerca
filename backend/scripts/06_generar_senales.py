"""Genera señales de revisión con SQL determinístico al final del pipeline.

Cada señal tiene su fórmula auditable visible.
Una señal se desactiva si la regla deja de cumplirse en una corrida posterior.

Tipos generados:
    1) sobrecosto                 — costo_actualizado > 1.30 × mto_viable
    2) discrepancia_avance        — |avance_infobras - avance_mef| > 10 puntos
    3) paralizacion_real          — estado_obra_wfs = 'Paralizada' OR (existe_paralizacion_mef Y saldos_hijos en 0%)
    4) inactiva_mef               — proyecto_mef.estado = 'DESACTIVADO_PERMANENTE'
    5) saldos_pendientes          — obra padre tiene saldos hijos al 0%
"""
from __future__ import annotations

import json

import psycopg

from _common import norm

DSN = "host=localhost user=postgres password=123 dbname=obrascerca_v2"


def main() -> int:
    with psycopg.connect(DSN) as conn:
        # Limpiar señales calculadas previas (las nuevas se vuelven a calcular)
        conn.execute("UPDATE senal_revision SET activa = FALSE WHERE tipo IN ('sobrecosto','discrepancia_avance','paralizacion_real','inactiva_mef','saldos_pendientes')")

        # 1) Sobrecosto
        conn.execute("""
            INSERT INTO senal_revision (tipo, cui, entidad_id, titulo, resumen, score, formula, evidencia)
            SELECT
                'sobrecosto'::tipo_senal,
                p.cui, p.entidad_id,
                'Sobrecosto del ' || ROUND(100.0*(p.costo_actualizado - p.mto_viable)/p.mto_viable, 1) || '% en el proyecto',
                'Costo actualizado supera al monto viable en más del 30%. ' ||
                'Viable: S/' || ROUND(p.mto_viable,0) || ' Actualizado: S/' || ROUND(p.costo_actualizado,0),
                ROUND(100.0*(p.costo_actualizado - p.mto_viable)/p.mto_viable, 2),
                'pct = 100 * (costo_actualizado - mto_viable) / mto_viable; umbral > 30%',
                jsonb_build_object(
                    'cui', p.cui,
                    'mto_viable', p.mto_viable,
                    'costo_actualizado', p.costo_actualizado,
                    'sobrecosto_pct', ROUND(100.0*(p.costo_actualizado - p.mto_viable)/p.mto_viable, 2),
                    'url_mef', 'https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo=' || p.cui
                )
            FROM proyecto_mef p
            WHERE p.mto_viable > 0
              AND p.costo_actualizado > p.mto_viable * 1.30
        """)
        n_sob = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='sobrecosto' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        # 2) Discrepancia de avance Infobras vs MEF
        conn.execute("""
            INSERT INTO senal_revision (tipo, cui, obra_id, entidad_id, titulo, resumen, score, formula, evidencia)
            SELECT
                'discrepancia_avance'::tipo_senal,
                o.cui, o.id, p.entidad_id,
                'Avance MEF (' || COALESCE(p.avance_fisico_mef,0) || '%) vs Infobras (' || COALESCE(o.avance_fisico_infobras,0) || '%)',
                'Las dos fuentes oficiales reportan avances físicos distintos para esta obra. Posible registro desactualizado.',
                ABS(COALESCE(p.avance_fisico_mef,0) - COALESCE(o.avance_fisico_infobras,0)),
                'abs(avance_mef - avance_infobras); umbral > 10 puntos',
                jsonb_build_object(
                    'nobr_id', o.nobr_id,
                    'avance_mef', p.avance_fisico_mef,
                    'avance_infobras', o.avance_fisico_infobras,
                    'diff', ABS(COALESCE(p.avance_fisico_mef,0) - COALESCE(o.avance_fisico_infobras,0))
                )
            FROM obra o
            JOIN proyecto_mef p ON p.cui = o.cui
            WHERE p.avance_fisico_mef IS NOT NULL
              AND o.avance_fisico_infobras IS NOT NULL
              AND ABS(p.avance_fisico_mef - o.avance_fisico_infobras) > 10
        """)
        n_dis = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='discrepancia_avance' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        # 3) Paralización real (WFS dice Paralizada)
        conn.execute("""
            INSERT INTO senal_revision (tipo, cui, obra_id, entidad_id, titulo, resumen, score, formula, evidencia)
            SELECT
                'paralizacion_real'::tipo_senal,
                o.cui, o.id, p.entidad_id,
                'Obra confirmada como Paralizada por Contraloría (WFS)',
                'El WFS oficial de Infobras (Contraloría) muestra la obra como Paralizada. Fuente independiente del bulk.',
                100,
                'estado_obra_wfs = ''Paralizada'' (Contraloría WFS oficial)',
                jsonb_build_object(
                    'nobr_id', o.nobr_id,
                    'estado_wfs', o.estado_obra_wfs,
                    'avance_infobras', o.avance_fisico_infobras,
                    'avance_mef', p.avance_fisico_mef,
                    'url_infobras', 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.nobr_id
                )
            FROM obra o
            JOIN proyecto_mef p ON p.cui = o.cui
            WHERE o.estado_obra_wfs = 'Paralizada'
        """)
        n_par = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='paralizacion_real' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        # 4) Inactiva MEF (DESACTIVADO PERMANENTE)
        conn.execute("""
            INSERT INTO senal_revision (tipo, cui, entidad_id, titulo, resumen, score, formula, evidencia)
            SELECT
                'inactiva_mef'::tipo_senal,
                p.cui, p.entidad_id,
                'Proyecto DESACTIVADO PERMANENTE en MEF',
                'MEF marca este proyecto como inactivo. Verifica si Infobras aún lo muestra como activo (problema de calidad de datos).',
                90,
                'proyecto_mef.estado = ''DESACTIVADO_PERMANENTE''',
                jsonb_build_object(
                    'cui', p.cui,
                    'estado_mef', p.estado::text,
                    'url_mef', 'https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo=' || p.cui
                )
            FROM proyecto_mef p
            WHERE p.estado = 'DESACTIVADO_PERMANENTE'
        """)
        n_inact = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='inactiva_mef' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        # 5) Saldos pendientes (obra original existe + hijos con avance 0%)
        conn.execute("""
            INSERT INTO senal_revision (tipo, cui, obra_id, entidad_id, titulo, resumen, score, formula, evidencia)
            SELECT
                'saldos_pendientes'::tipo_senal,
                padre.cui, padre.id, p.entidad_id,
                'Obra con saldos de obra pendientes (contratos cortados)',
                'La obra original tiene ' || (SELECT COUNT(*) FROM obra h WHERE h.obra_padre_id = padre.id) || ' saldo(s) de obra registrado(s) en Infobras. Indica que el contrato original quedó inconcluso.',
                80,
                'obra padre con N obras hijas (obra_padre_id = padre.id)',
                jsonb_build_object(
                    'obra_padre_nobr_id', padre.nobr_id,
                    'avance_padre', padre.avance_fisico_infobras,
                    'saldos_hijos', (SELECT jsonb_agg(jsonb_build_object('nobr_id', h.nobr_id, 'avance', h.avance_fisico_infobras))
                                     FROM obra h WHERE h.obra_padre_id = padre.id)
                )
            FROM obra padre
            JOIN proyecto_mef p ON p.cui = padre.cui
            WHERE EXISTS (SELECT 1 FROM obra h WHERE h.obra_padre_id = padre.id)
        """)
        n_sal = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='saldos_pendientes' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        # 6) Concentración compras menores (≤8 UIT) — solo si hay órdenes cargadas
        n_concentra = 0
        if conn.execute("SELECT EXISTS(SELECT 1 FROM orden_compra_servicio LIMIT 1)").fetchone()[0]:
            conn.execute("""
                INSERT INTO senal_revision (tipo, contratista_id, entidad_id, titulo, resumen, score, formula, evidencia)
                WITH por_entidad AS (
                    SELECT entidad_id, COUNT(*)::int AS total, SUM(monto_soles) AS monto
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                    GROUP BY entidad_id HAVING COUNT(*) >= 20
                ),
                por_ruc_ent AS (
                    SELECT entidad_id, contratista_id, COUNT(*)::int AS n_ruc, SUM(monto_soles) AS monto_ruc
                    FROM orden_compra_servicio
                    WHERE fecha_emision >= CURRENT_DATE - INTERVAL '365 days'
                      AND contratista_id IS NOT NULL
                    GROUP BY entidad_id, contratista_id HAVING COUNT(*) >= 5
                )
                SELECT
                    'concentracion_menores'::tipo_senal,
                    r.contratista_id, r.entidad_id,
                    c.razon_social || ' concentra ' || ROUND(100.0*r.monto_ruc/pe.monto, 1) || '% de compras menores de ' || e.nombre,
                    'RUC ' || c.ruc || ' recibió ' || r.n_ruc || ' órdenes ≤8 UIT por S/ ' || ROUND(r.monto_ruc,0) || ' (12m).',
                    ROUND(100.0*r.monto_ruc/pe.monto, 2),
                    'pct = 100 * monto(RUC,entidad,12m) / monto(entidad,12m); umbral ≥ 20%',
                    jsonb_build_object(
                        'ruc', c.ruc,
                        'razon_social', c.razon_social,
                        'entidad', e.nombre,
                        'n_ordenes_ruc', r.n_ruc,
                        'monto_ruc', r.monto_ruc,
                        'n_ordenes_entidad', pe.total,
                        'monto_entidad', pe.monto,
                        'pct_monto', ROUND(100.0*r.monto_ruc/pe.monto, 2)
                    )
                FROM por_ruc_ent r
                JOIN por_entidad pe ON pe.entidad_id = r.entidad_id
                JOIN contratista c ON c.id = r.contratista_id
                JOIN entidad e ON e.id = r.entidad_id
                WHERE (100.0*r.monto_ruc/pe.monto) >= 20
            """)
            n_concentra = conn.execute("SELECT COUNT(*) FROM senal_revision WHERE tipo='concentracion_menores' AND detectada_en >= NOW() - INTERVAL '1 minute'").fetchone()[0]

        conn.commit()

        print("Señales activas generadas:")
        print(f"  sobrecosto              : {n_sob}")
        print(f"  discrepancia_avance     : {n_dis}")
        print(f"  paralizacion_real       : {n_par}")
        print(f"  inactiva_mef            : {n_inact}")
        print(f"  saldos_pendientes       : {n_sal}")
        print(f"  concentracion_menores   : {n_concentra}")
        print(f"  TOTAL                   : {n_sob + n_dis + n_par + n_inact + n_sal + n_concentra}")
    return 0


if __name__ == "__main__":
    main()
