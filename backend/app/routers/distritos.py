from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ..db import fetch_all, fetch_one

router = APIRouter(prefix="/api/distritos", tags=["distritos"])


@router.get("")
def listar() -> list[dict]:
    return fetch_all("""
        SELECT id, ubigeo, departamento, provincia, distrito,
               centroide_lat AS lat, centroide_lon AS lon, ambito_mvp
        FROM distrito WHERE ambito_mvp
        ORDER BY provincia, distrito
    """)


@router.get("/resumen")
def resumen() -> list[dict]:
    return fetch_all("SELECT * FROM v_resumen_distrito ORDER BY paralizadas_wfs DESC NULLS LAST, total_obras DESC")


@router.get("/{ubigeo}")
def detalle(ubigeo: str) -> dict:
    d = fetch_one("SELECT * FROM distrito WHERE ubigeo = %s", (ubigeo,))
    if not d:
        raise HTTPException(404, "distrito no encontrado")
    return d
