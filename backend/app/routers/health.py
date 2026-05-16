"""Healthcheck y diagnóstico."""
from __future__ import annotations

from fastapi import APIRouter

from ..db import fetch_one

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health() -> dict:
    row = fetch_one("SELECT 1 AS ok, current_database() AS db, version() AS pg")
    return {
        "ok": True,
        "db": row["db"],
        "pg_version": row["pg"].split(" on ")[0] if row else None,
    }
