"""Obras Cerca — API FastAPI.

Levantar local:
    cd backend
    uvicorn app.main:app --reload --port 8000

Docs interactivas: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS, APP_ENV
from .db import close_pool, open_pool
from .routers import contratistas, distritos, entidades, explicacion, health, info, mapa, obras, senales, sospechosos, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(
    title="Obras Cerca API",
    version="0.1.0",
    description=(
        "API ciudadana que integra Infobras, OECE OCDS, Contraloría e INEI para "
        "que cualquier persona en el Perú pueda revisar las obras públicas cerca "
        "de su ubicación.\n\n"
        "Ámbito MVP: Lima Metropolitana + Provincia Constitucional del Callao (50 distritos)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if APP_ENV != "local" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(stats.router)
app.include_router(distritos.router)
# sospechosos ANTES de contratistas: define /api/contratistas/sospechosos antes
# de que /api/contratistas/{ruc} lo capture
app.include_router(sospechosos.router)
app.include_router(obras.router)
app.include_router(contratistas.router)
app.include_router(senales.router)
app.include_router(entidades.router)
app.include_router(explicacion.router)
app.include_router(mapa.router)
app.include_router(info.router)


@app.get("/", tags=["root"])
def root() -> dict:
    return {
        "name": "Obras Cerca API",
        "version": "0.1.0",
        "docs": "/docs",
        "ambito": "Lima Metropolitana + Provincia Constitucional del Callao",
    }
