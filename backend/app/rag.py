"""Capa RAG — chat sobre informes de Contraloría.

Embeddings: 2 proveedores, decidido por EMBED_PROVIDER:
  - 'local'  : sentence-transformers en proceso (necesita ~400 MB RAM + disco)
              Usado en LOCAL al indexar PDFs (script 07).
  - 'hf_api' : HuggingFace Inference API (cero deps, free tier ~1000 req/día)
              Usado en EC2 donde el disco/RAM están justos.
  - 'auto'   : usa local si está instalado, sino hf_api.

Ambos devuelven el MISMO vector porque ambos usan el modelo
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (384 dim).

Si todo falla, fallback determinístico para no dejar muda la UI.
"""
from __future__ import annotations

import logging
import re
from threading import Lock
from typing import Any

import requests

from .config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    EMBED_MODEL, EMBED_PROVIDER, HF_API_URL, HF_TOKEN,
    LLM_PROVIDER,
    MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL,
)

log = logging.getLogger(__name__)

_local_model = None
_local_model_lock = Lock()
_local_unavailable = False


def _get_local_model():
    """Lazy load del modelo sentence-transformers. Devuelve None si no está instalado."""
    global _local_model, _local_unavailable
    if _local_unavailable:
        return None
    if _local_model is None:
        with _local_model_lock:
            if _local_model is None and not _local_unavailable:
                try:
                    log.info("Cargando modelo embeddings local (toma 10-30s)...")
                    from sentence_transformers import SentenceTransformer
                    _local_model = SentenceTransformer(EMBED_MODEL.split("/")[-1])
                    log.info("Modelo local cargado. Dim: %s", _local_model.get_sentence_embedding_dimension())
                except ImportError:
                    log.info("sentence-transformers no instalado, usando HF Inference API")
                    _local_unavailable = True
                    return None
                except Exception as e:
                    log.exception("Error cargando modelo local")
                    _local_unavailable = True
                    return None
    return _local_model


def _embed_local(text: str) -> list[float] | None:
    """Embedding con modelo local. Devuelve None si no disponible."""
    model = _get_local_model()
    if model is None:
        return None
    vec = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
    return vec.tolist()


def _embed_hf_api(text: str) -> list[float] | None:
    """Embedding via HuggingFace Inference API. Devuelve None si falla."""
    headers = {"Content-Type": "application/json"}
    if HF_TOKEN:
        headers["Authorization"] = f"Bearer {HF_TOKEN}"
    try:
        r = requests.post(
            HF_API_URL,
            json={"inputs": text},
            headers=headers,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        # La API devuelve directamente el vector como lista de floats (para feature-extraction).
        # Algunos modelos devuelven lista de listas (uno por token) — promediar.
        if isinstance(data, list):
            if data and isinstance(data[0], list):
                # token-level → mean pooling
                import statistics
                dim = len(data[0])
                return [statistics.fmean(row[i] for row in data) for i in range(dim)]
            elif data and isinstance(data[0], (int, float)):
                return [float(x) for x in data]
        log.warning("HF API respondió formato inesperado: %s", str(data)[:200])
        return None
    except Exception as e:
        log.exception("HF Inference API falló: %s", e)
        return None


def embed_text(text: str) -> list[float]:
    """Genera embedding 384-dim. Decide provider según EMBED_PROVIDER."""
    provider = EMBED_PROVIDER

    if provider in ("local", "auto"):
        vec = _embed_local(text)
        if vec is not None:
            return vec
        if provider == "local":
            raise RuntimeError("EMBED_PROVIDER=local pero sentence-transformers no está disponible")
        # auto → falla local, sigue al fallback

    if provider in ("hf_api", "auto"):
        vec = _embed_hf_api(text)
        if vec is not None:
            return vec

    raise RuntimeError(f"No se pudo generar embedding (provider={provider}, HF_TOKEN set: {bool(HF_TOKEN)})")


def embed_to_pgvector(vec: list[float]) -> str:
    """Convierte lista de floats al formato textual que acepta pgvector: '[v1,v2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


# ---------------------------------------------------------------------------
# Chat RAG con Minimax (o fallback determinístico)
# ---------------------------------------------------------------------------

SYSTEM_RAG = (
    "Eres un asistente para periodistas de investigación cívica en Perú. "
    "Tu rol: responder preguntas sobre UNA obra pública específica usando "
    "EXCLUSIVAMENTE los fragmentos de informes de Contraloría que te paso como contexto.\n\n"
    "REGLAS ESTRICTAS:\n"
    "1. NO inventes datos. Si el contexto no responde la pregunta, di textualmente: "
    "'No hay información suficiente en los informes registrados para responder eso.'\n"
    "2. Cita las fuentes inline al hacer afirmaciones, formato: [Informe NRO, página N].\n"
    "3. Voz neutral periodística. NO acuses de corrupción ni uses términos peyorativos. "
    "Presenta solo hechos verificables.\n"
    "4. Responde en español peruano neutro. Máximo 200 palabras.\n"
    "5. Si la pregunta es ambigua o demasiado abierta, pide que la concrete.\n"
    "6. NO repitas literalmente fragmentos largos del contexto. Sintetiza."
)


def build_rag_prompt(pregunta: str, chunks: list[dict]) -> str:
    if not chunks:
        return (
            f"No hay informes de Contraloría indexados sobre esta obra.\n\n"
            f"Pregunta del periodista: {pregunta}"
        )

    bloques = []
    for c in chunks:
        marca = f"[Informe {c.get('nro_informe') or c['informe_id']}"
        if c.get("pagina"):
            marca += f", página {c['pagina']}"
        marca += "]"
        bloques.append(f"{marca}\n{c['texto']}")

    contexto = "\n\n---\n\n".join(bloques)
    return (
        f"Contexto: fragmentos de informes de Contraloría sobre esta obra.\n\n"
        f"{contexto}\n\n---\n\n"
        f"Pregunta del periodista: {pregunta}\n\n"
        f"Responde basándote SOLO en los fragmentos anteriores. Cita las fuentes."
    )


def _stub_rag(pregunta: str, chunks: list[dict]) -> str:
    if not chunks:
        return (
            "No tengo informes de Contraloría indexados sobre esta obra. "
            "Para verificar el estado y avance, consulta las fuentes oficiales:\n"
            "- MEF/Invierte.pe (banco de inversiones)\n"
            "- Infobras de Contraloría"
        )
    nro = len({c['informe_id'] for c in chunks})
    return (
        f"Encontré contenido relevante en {nro} informe(s) de Contraloría. "
        f"El servicio de respuesta automática está temporalmente degradado. "
        f"Por favor consulta los PDFs originales listados en las fuentes para más detalle."
    )


def chat_rag(pregunta: str, chunks: list[dict]) -> dict[str, Any]:
    provider = LLM_PROVIDER

    if provider == "minimax" and MINIMAX_API_KEY:
        try:
            # Minimax expone una API compatible con OpenAI (no con Anthropic).
            # Endpoint estándar: POST {base_url}/chat/completions
            from openai import OpenAI
            client = OpenAI(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
            prompt = build_rag_prompt(pregunta, chunks)
            resp = client.chat.completions.create(
                model=MINIMAX_MODEL,
                max_tokens=600,
                messages=[
                    {"role": "system", "content": SYSTEM_RAG},
                    {"role": "user", "content": prompt},
                ],
            )
            texto = (resp.choices[0].message.content or "").strip()
            # Minimax M2.7 es un modelo de razonamiento — devuelve <think>...</think>
            # antes de la respuesta final. Lo quitamos para que el usuario no lo vea.
            texto = re.sub(r"<think>.*?</think>\s*", "", texto, flags=re.DOTALL).strip()
            # Quitar headings markdown sueltos tipo "## Respuesta" que el modelo agrega
            texto = re.sub(r"^#+\s*Respuesta\s*\n+", "", texto, flags=re.IGNORECASE).strip()
            usage = getattr(resp, "usage", None)
            return {
                "provider": "minimax",
                "modelo": MINIMAX_MODEL,
                "respuesta": texto,
                "tokens_input": (getattr(usage, "prompt_tokens", 0) or 0) if usage else 0,
                "tokens_output": (getattr(usage, "completion_tokens", 0) or 0) if usage else 0,
            }
        except Exception as e:
            log.exception("Minimax falló, usando stub")
            return {
                "provider": "fallback",
                "modelo": f"error:{type(e).__name__}:{str(e)[:80]}",
                "respuesta": _stub_rag(pregunta, chunks),
                "tokens_input": 0, "tokens_output": 0,
            }

    if provider == "anthropic" and ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            prompt = build_rag_prompt(pregunta, chunks)
            resp = client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=600,
                system=SYSTEM_RAG,
                messages=[{"role": "user", "content": prompt}],
            )
            texto = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            ).strip()
            usage = getattr(resp, "usage", None)
            return {
                "provider": "anthropic",
                "modelo": ANTHROPIC_MODEL,
                "respuesta": texto,
                "tokens_input": (getattr(usage, "input_tokens", 0) or 0) if usage else 0,
                "tokens_output": (getattr(usage, "output_tokens", 0) or 0) if usage else 0,
            }
        except Exception as e:
            log.exception("Anthropic falló, usando stub")
            return {
                "provider": "fallback",
                "modelo": f"error:{type(e).__name__}",
                "respuesta": _stub_rag(pregunta, chunks),
                "tokens_input": 0, "tokens_output": 0,
            }

    return {
        "provider": "stub",
        "modelo": "deterministic_v1",
        "respuesta": _stub_rag(pregunta, chunks),
        "tokens_input": 0, "tokens_output": 0,
    }
