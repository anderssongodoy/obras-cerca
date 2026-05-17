"""Capa RAG — chat sobre informes de Contraloría.

Carga lazy el modelo sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2, 384 dim).
El modelo NO se carga en startup para que uvicorn arranque rápido — se carga la primera
vez que se hace una pregunta. Después queda en memoria del proceso.

Si Minimax falla, fallback determinístico para no dejar muda la UI.
"""
from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from .config import (
    ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
    LLM_PROVIDER,
    MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL,
)

log = logging.getLogger(__name__)

_model = None
_model_lock = Lock()


def get_embed_model():
    """Lazy load del modelo sentence-transformers (singleton thread-safe)."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                log.info("Cargando modelo embeddings (toma 10-30 seg la primera vez)...")
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
                log.info("Modelo cargado. Dim: %s", _model.get_sentence_embedding_dimension())
    return _model


def embed_text(text: str) -> list[float]:
    """Genera embedding 384-dim para un texto."""
    model = get_embed_model()
    vec = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
    return vec.tolist()


def embed_to_pgvector(vec: list[float]) -> str:
    """Convierte lista de floats al formato textual que acepta pgvector: '[v1,v2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


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
    """Arma el user prompt con el contexto recuperado."""
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
    """Respuesta degradada determinística cuando el LLM no está disponible."""
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
        f"Por favor consulta los PDFs originales listados en las fuentes para más detalle. "
        f"\n\nDatos cruzados de MEF/Invierte.pe + Infobras/Contraloría."
    )


def chat_rag(pregunta: str, chunks: list[dict]) -> dict[str, Any]:
    """Llama al LLM con el contexto. Fallback determinístico si falla.

    Devuelve dict: provider, modelo, respuesta, tokens_input, tokens_output.
    """
    provider = LLM_PROVIDER

    if provider == "minimax" and MINIMAX_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=MINIMAX_API_KEY, base_url=MINIMAX_BASE_URL)
            prompt = build_rag_prompt(pregunta, chunks)
            resp = client.messages.create(
                model=MINIMAX_MODEL,
                max_tokens=600,
                system=SYSTEM_RAG,
                messages=[{"role": "user", "content": prompt}],
            )
            texto = "".join(
                b.text for b in resp.content if getattr(b, "type", None) == "text"
            ).strip()
            usage = getattr(resp, "usage", None)
            return {
                "provider": "minimax",
                "modelo": MINIMAX_MODEL,
                "respuesta": texto,
                "tokens_input": (getattr(usage, "input_tokens", 0) or 0) if usage else 0,
                "tokens_output": (getattr(usage, "output_tokens", 0) or 0) if usage else 0,
            }
        except Exception as e:
            log.exception("Minimax falló, usando stub")
            return {
                "provider": "fallback",
                "modelo": f"error:{type(e).__name__}",
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
