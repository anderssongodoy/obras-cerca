"""Obras Cerca API v2.

Backend FastAPI sobre obrascerca_v2.
Diseño: MEF/Invierte.pe es el maestro. Infobras es satélite.
Soporta saldos de obra y cruce de fuentes.

Levantar local:
    cd backend
    pip install -r requirements.txt
    python -m uvicorn app.main:app --reload --port 8000

Docs: http://localhost:8000/docs
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import ALLOWED_ORIGINS, APP_ENV
from .db import close_pool, open_pool
from .routers import admin, chat, contratistas, distritos, health, obras, senales


@asynccontextmanager
async def lifespan(app: FastAPI):
    open_pool()
    yield
    close_pool()


app = FastAPI(
    title="Obras Cerca API",
    version="0.2.0",
    description=(
        "API ciudadana que cruza Invierte.pe (MEF) + Infobras (Contraloría) + "
        "SEACE + Pentaho (compras ≤8 UIT). Diseñada para hack@latam 2026, "
        "track Transparency & Corruption.\n\n"
        "**Ámbito MVP:** Lima Metropolitana + Provincia Constitucional del Callao."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if APP_ENV == "local" else ALLOWED_ORIGINS,
    allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)

app.include_router(health.router)
app.include_router(distritos.router)
app.include_router(obras.router)
app.include_router(contratistas.router)
app.include_router(senales.router)
app.include_router(admin.router)
app.include_router(chat.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "Obras Cerca API v2",
        "version": "0.2.0",
        "docs": "/docs",
        "stack": "FastAPI + PostgreSQL 17 (obrascerca_v2)",
    }
