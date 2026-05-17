"""Endpoints administrativos disparados por Lambda + EventBridge.

Protegidos por un token compartido (env var INGESTA_TOKEN). La Lambda envía el token
en el header X-Admin-Token; si no coincide, devolvemos 401 sin más detalle.

El endpoint /ingesta-diaria arranca la ingesta en background y devuelve 202 inmediatamente
para que la Lambda no espere los minutos que demora el scraping completo.
"""
from __future__ import annotations

import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException

from ..config import INGESTA_TOKEN, SCRIPTS_DIR

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Orden de ejecución del pipeline diario.
# Cada uno es un script idempotente que solo procesa lo nuevo del día.
PIPELINE = [
    "02_mapear_idue.py",
    "03_descubrir_cuis.py",
    "04_enriquecer_cui.py",
    "05_verificar_nobr.py",
    "06_generar_senales.py",
]


def _check_token(token: str | None) -> None:
    if not INGESTA_TOKEN:
        raise HTTPException(status_code=503, detail="admin disabled (INGESTA_TOKEN not set)")
    if token != INGESTA_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")


def _run_pipeline() -> None:
    """Corre los scripts en serie. Logs en /var/log/obras-cerca/ o stderr."""
    log_dir = Path("/var/log/obras-cerca")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{datetime.utcnow():%Y-%m-%d}.log"

    with log_file.open("a", encoding="utf-8") as out:
        out.write(f"\n=== ingesta diaria {datetime.utcnow().isoformat()} ===\n")
        for script in PIPELINE:
            path = SCRIPTS_DIR / script
            if not path.exists():
                out.write(f"[skip] {script} no existe\n")
                continue
            out.write(f"[run] {script}\n")
            out.flush()
            try:
                result = subprocess.run(
                    ["python", str(path)],
                    cwd=SCRIPTS_DIR.parent,
                    stdout=out,
                    stderr=subprocess.STDOUT,
                    timeout=900,  # 15 min por script
                )
                out.write(f"[done] {script} exit={result.returncode}\n")
            except subprocess.TimeoutExpired:
                out.write(f"[timeout] {script} pasó 15 min\n")
            except Exception as e:
                out.write(f"[error] {script}: {e}\n")
            out.flush()


@router.post("/ingesta-diaria", status_code=202)
def ingesta_diaria(
    bg: BackgroundTasks,
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> dict:
    """Arranca el pipeline 02..06 en background. Lambda recibe 202 al instante."""
    _check_token(x_admin_token)
    bg.add_task(_run_pipeline)
    return {
        "status": "queued",
        "pipeline": PIPELINE,
        "started_at": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/health-auth")
def health_auth(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> dict:
    """Endpoint para que Lambda verifique conectividad + token antes del cron real."""
    _check_token(x_admin_token)
    return {"ok": True, "ts": datetime.utcnow().isoformat() + "Z"}
