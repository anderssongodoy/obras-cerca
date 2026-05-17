"""Endpoint del chat RAG sobre informes de Contraloría — POST /api/obras/{id}/preguntar.

Flujo:
  1. Cache hit por hash(pregunta_normalizada, obra_id) → respuesta cacheada
  2. Cache miss → embed la pregunta → vector search top-5 chunks → LLM → cache + devuelve

GET /api/obras/{id}/preguntar/health — info sobre disponibilidad del chat para la obra
(cuántos chunks/informes están indexados). Útil para el frontend para mostrar/ocultar el chat.
"""
from __future__ import annotations

import hashlib
import json
import logging

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from ..db import fetch_all, fetch_one, get_conn
from ..rag import chat_rag, embed_text, embed_to_pgvector

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/obras", tags=["chat"])


class PreguntaIn(BaseModel):
    pregunta: str = Field(..., min_length=3, max_length=500)


def _hash_pregunta(p: str) -> str:
    """Normaliza la pregunta y la hashea para usar como cache key."""
    p_norm = " ".join(p.lower().strip().split())
    return hashlib.sha256(p_norm.encode("utf-8")).hexdigest()


@router.post("/{obra_id}/preguntar")
def preguntar(body: PreguntaIn, obra_id: int = Path(..., gt=0)) -> dict:
    """Responde una pregunta del periodista sobre una obra específica usando RAG."""
    pregunta = body.pregunta.strip()
    pregunta_hash = _hash_pregunta(pregunta)

    # 1. Cache hit?
    cached = fetch_one(
        "SELECT respuesta, fuentes, creado_en "
        "FROM chat_qa_cache "
        "WHERE obra_id = %s AND pregunta_hash = %s",
        (obra_id, pregunta_hash),
    )
    if cached:
        return {
            "respuesta": cached["respuesta"],
            "fuentes": cached["fuentes"] or [],
            "cache": True,
        }

    # 2. Validar que la obra existe
    obra = fetch_one("SELECT id FROM obra WHERE id = %s", (obra_id,))
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    # 3. Embed la pregunta
    try:
        q_emb = embed_text(pregunta)
    except Exception as e:
        log.exception("Error generando embedding")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar embedding: {type(e).__name__}",
        )

    q_emb_str = embed_to_pgvector(q_emb)

    # 4. Vector search — top 5 chunks de la obra
    chunks = fetch_all(
        """
        SELECT
            dc.texto,
            dc.informe_id,
            dc.pagina,
            dc.chunk_idx,
            ic.nro_informe,
            ic.titulo,
            ic.url_pdf_completo
        FROM documento_chunk dc
        JOIN informe_control ic ON ic.id = dc.informe_id
        WHERE dc.obra_id = %s AND dc.embedding IS NOT NULL
        ORDER BY dc.embedding <=> %s::vector
        LIMIT 5
        """,
        (obra_id, q_emb_str),
    )

    # 5. LLM con el contexto recuperado
    resp = chat_rag(pregunta, chunks)

    # 6. Armar fuentes citables
    fuentes = [
        {
            "informe_id": c["informe_id"],
            "nro_informe": c["nro_informe"],
            "titulo": c["titulo"],
            "pagina": c["pagina"],
            "url_pdf": c["url_pdf_completo"],
        }
        for c in chunks
    ]

    # 7. Guardar en cache (ON CONFLICT por si dos requests simultáneos)
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO chat_qa_cache
                (obra_id, pregunta_hash, pregunta, respuesta, fuentes, tokens_total)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (obra_id, pregunta_hash) DO NOTHING
            """,
            (
                obra_id,
                pregunta_hash,
                pregunta,
                resp["respuesta"],
                json.dumps(fuentes, ensure_ascii=False),
                resp.get("tokens_input", 0) + resp.get("tokens_output", 0),
            ),
        )

    return {
        "respuesta": resp["respuesta"],
        "fuentes": fuentes,
        "cache": False,
        "provider": resp["provider"],
        "modelo": resp["modelo"],
    }


@router.get("/{obra_id}/preguntar/health")
def health_chat(obra_id: int = Path(..., gt=0)) -> dict:
    """Informa al frontend si esta obra tiene RAG disponible (chunks indexados)."""
    obra = fetch_one("SELECT id FROM obra WHERE id = %s", (obra_id,))
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    counts = fetch_one(
        """
        SELECT
            COUNT(*)::int AS chunks,
            COUNT(DISTINCT informe_id)::int AS informes_indexados
        FROM documento_chunk
        WHERE obra_id = %s AND embedding IS NOT NULL
        """,
        (obra_id,),
    )

    n_chunks = (counts or {}).get("chunks") or 0
    n_informes = (counts or {}).get("informes_indexados") or 0

    return {
        "obra_id": obra_id,
        "chunks_indexados": n_chunks,
        "informes_indexados": n_informes,
        "puede_preguntar": n_chunks > 0,
    }


@router.get("/{obra_id}/preguntar/sugerencias")
def sugerencias(obra_id: int = Path(..., gt=0)) -> dict:
    """Devuelve 4 preguntas sugeridas para el chat. Son fijas, pero dependen de qué
    info tenga la obra (señales activas, paralización, etc) para mostrar las más
    relevantes."""
    obra = fetch_one(
        """
        SELECT
            o.id,
            o.estado_obra_wfs,
            o.existe_informe_control,
            (o.obra_padre_id IS NOT NULL) AS es_saldo_obra,
            COALESCE(p.estado::text, '') AS estado_proyecto_mef,
            EXISTS (SELECT 1 FROM senal_revision s WHERE s.obra_id = o.id AND s.activa) AS tiene_senal,
            EXISTS (SELECT 1 FROM documento_chunk dc WHERE dc.obra_id = o.id) AS tiene_chunks
        FROM obra o
        LEFT JOIN proyecto_mef p ON p.cui = o.cui
        WHERE o.id = %s
        """,
        (obra_id,),
    )
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    sugeridas: list[str] = []

    # Pregunta universal — siempre la primera
    sugeridas.append("¿Qué dicen los informes de Contraloría sobre esta obra?")

    # Pregunta sobre estado
    if obra.get("estado_obra_wfs") == "Paralizada":
        sugeridas.append("¿Por qué está paralizada esta obra?")
    elif "DESACTIVA" in (obra.get("estado_proyecto_mef") or ""):
        sugeridas.append("¿Por qué el MEF desactivó este proyecto?")
    else:
        sugeridas.append("¿Cuál es el estado real de avance de esta obra?")

    # Pregunta sobre contratista / responsabilidades
    sugeridas.append("¿Qué hallazgos identifica Contraloría sobre el contratista?")

    # Pregunta sobre saldos / continuidad
    if obra.get("es_saldo_obra"):
        sugeridas.append("¿Por qué esta obra es un saldo? ¿Qué pasó con el contrato original?")
    else:
        sugeridas.append("¿Hay riesgos o irregularidades observados en los informes?")

    return {
        "obra_id": obra_id,
        "puede_preguntar": obra.get("tiene_chunks") or False,
        "sugerencias": sugeridas,
    }
