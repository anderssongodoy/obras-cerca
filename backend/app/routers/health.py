from __future__ import annotations
from fastapi import APIRouter
from ..db import fetch_one

router = APIRouter(tags=["meta"])


@router.get("/api/health")
def health() -> dict:
    row = fetch_one("SELECT current_database() AS db, version() AS pg")
    return {"ok": True, "db": row["db"], "pg": row["pg"].split(" on ")[0] if row else None}


@router.get("/api/stats")
def stats() -> dict:
    return {
        "totales": fetch_one("""
            SELECT
              (SELECT COUNT(*) FROM distrito WHERE ambito_mvp)        AS distritos_mvp,
              (SELECT COUNT(*) FROM entidad)                          AS entidades,
              (SELECT COUNT(*) FROM contratista)                      AS contratistas,
              (SELECT COUNT(*) FROM proyecto_mef)                     AS proyectos,
              (SELECT COUNT(*) FROM obra)                             AS obras,
              (SELECT COUNT(*) FROM proyecto_mef
                  WHERE estado = 'DESACTIVADO_PERMANENTE')            AS proyectos_desactivados,
              (SELECT COUNT(*) FROM obra
                  WHERE estado_obra_wfs = 'Paralizada')               AS obras_paralizadas_wfs,
              (SELECT COUNT(*) FROM obra WHERE obra_padre_id IS NOT NULL)
                                                                       AS saldos_obra,
              (SELECT COUNT(*) FROM informe_control)                  AS informes_control,
              (SELECT COUNT(*) FROM orden_compra_servicio)            AS ordenes_menores,
              (SELECT COUNT(*) FROM senal_revision WHERE activa)      AS senales_activas
        """)
    }
