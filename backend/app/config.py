"""Configuración leída desde .env (con defaults locales)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=False)
load_dotenv(BACKEND_DIR / ".env.example", override=False)

DB_DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")
ALLOWED_ORIGINS = [o.strip() for o in os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:4200,http://localhost:5173,http://localhost:3000"
).split(",") if o.strip()]
APP_ENV = os.getenv("APP_ENV", "local")

LLM_PROVIDER     = os.getenv("LLM_PROVIDER", "stub").lower()
MINIMAX_API_KEY  = os.getenv("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io/v1")
MINIMAX_MODEL    = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL   = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

HTTP_UA = os.getenv(
    "HTTP_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)

# Token compartido entre la Lambda de EventBridge y el endpoint /api/admin/ingesta-diaria.
# Si está vacío, el endpoint admin rechaza todo (modo seguro por default).
INGESTA_TOKEN = os.getenv("INGESTA_TOKEN", "")
SCRIPTS_DIR = BACKEND_DIR / "scripts"

# RAG / embeddings.
# EMBED_PROVIDER:
#   - 'auto'      (default): usa sentence-transformers si está disponible, sino HF API
#   - 'local'     : fuerza sentence-transformers (requiere pip install -r requirements-rag.txt)
#   - 'hf_api'    : fuerza HuggingFace Inference API (necesita HF_TOKEN para evitar rate limit)
EMBED_PROVIDER = os.getenv("EMBED_PROVIDER", "auto").lower()
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_API_URL = os.getenv(
    "HF_API_URL",
    "https://router.huggingface.co/hf-inference/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/pipeline/feature-extraction",
)
