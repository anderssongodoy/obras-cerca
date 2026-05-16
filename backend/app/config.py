"""Configuración de la app — lee de variables de entorno con defaults locales."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env.example", override=False)

DB_DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:4200,http://localhost:5173,http://localhost:3000"
).split(",") if o.strip()]
APP_ENV = os.getenv("APP_ENV", "local")

# Capa IA — explicación ciudadana (MD §6.5: la IA SOLO redacta, no decide)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "stub").lower()
MINIMAX_API_KEY = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
