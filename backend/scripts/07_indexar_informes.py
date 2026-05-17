"""Indexa los PDFs de informes de Contraloría para el chat RAG.

Por cada informe en `informe_control` con `rag_estado='pendiente'`:
    1. Descarga el PDF desde url_pdf_completo (o url_pdf_resumen como fallback)
    2. Extrae texto con PyMuPDF
    3. Si el PDF no tiene texto extraíble (escaneado) → marca 'pendiente_ocr' y salta
    4. Chunkea ~500 tokens con overlap 50
    5. Genera embedding con sentence-transformers paraphrase-multilingual-MiniLM-L12-v2 (384 dim)
    6. INSERT en documento_chunk + UPDATE informe_control.rag_estado='indexado'

Pre-requisitos:
    pip install -r backend/requirements-rag.txt

Opción A — BD local en tu PC (si la tienes corriendo):
    cd backend
    python scripts/07_indexar_informes.py

Opción B — BD de la EC2 (vía SSH tunnel):
    # En una terminal aparte (déjala abierta):
    ssh -i $HOME/.ssh/my_key_pair.pem -L 5433:127.0.0.1:5432 ubuntu@34.230.30.239

    # En otra terminal:
    set DB_DSN=host=localhost port=5433 user=obrascerca_app password=<el-de-/etc/obras-cerca-db-pass> dbname=obrascerca_v2
    python scripts/07_indexar_informes.py

Idempotente: solo procesa informes con rag_estado='pendiente'.
Reset si quieres re-indexar:
    UPDATE informe_control SET rag_estado='pendiente';
    DELETE FROM documento_chunk;
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg
import requests
from psycopg.rows import dict_row
from tqdm import tqdm

# UTF-8 a stdout (Windows console)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------- Config ----------
DSN = os.getenv("DB_DSN", "host=localhost user=postgres password=123 dbname=obrascerca_v2")
MODEL_NAME = os.getenv("EMBED_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
CHUNK_SIZE = 500   # palabras aprox (no tokens exactos, no hace falta tokenizer del modelo)
CHUNK_OVERLAP = 50
HTTP_TIMEOUT = 60
HTTP_UA = "Mozilla/5.0 ObrasCerca RAG indexer"

# ---------- Helpers ----------

def descargar_pdf(url: str, cache_dir: Path | None = None) -> bytes | None:
    """Descarga el PDF. Cachea localmente para no re-descargar en reintentos."""
    if not url:
        return None

    cache_file = None
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        url_hash = hashlib.sha1(url.encode()).hexdigest()[:16]
        cache_file = cache_dir / f"{url_hash}.pdf"
        if cache_file.exists():
            return cache_file.read_bytes()

    try:
        r = requests.get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": HTTP_UA})
        r.raise_for_status()
        content = r.content
        if cache_file:
            cache_file.write_bytes(content)
        return content
    except Exception as e:
        print(f"  ERROR descarga: {e}")
        return None


def extraer_texto_pdf(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Devuelve lista de (pagina, texto). Si no hay texto extraíble devuelve []."""
    import fitz  # pymupdf
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        print(f"  ERROR abrir PDF: {e}")
        return []

    paginas = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        # Limpieza básica: colapsar espacios múltiples y saltos repetidos
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        if text:
            paginas.append((i, text))
    doc.close()
    return paginas


def chunkear(texto: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Chunkea por palabras (más simple que tokens). Suficiente para 384-dim."""
    palabras = texto.split()
    if len(palabras) <= size:
        return [texto] if palabras else []

    chunks = []
    step = size - overlap
    for i in range(0, len(palabras), step):
        chunk_palabras = palabras[i:i + size]
        if len(chunk_palabras) < 20:  # ignorar fragmentos diminutos
            break
        chunks.append(" ".join(chunk_palabras))
    return chunks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=None, help="Procesar solo N informes")
    ap.add_argument("--reset", action="store_true", help="Borrar embeddings existentes y reindexar TODO")
    ap.add_argument("--informe-id", type=int, default=None, help="Solo indexar un informe específico (para debug)")
    args = ap.parse_args()

    print(f"\nConexión BD: {DSN.split('password=')[0]}password=***\n")
    print(f"Modelo embeddings: {MODEL_NAME}")
    print(f"Chunk size: {CHUNK_SIZE} palabras (overlap {CHUNK_OVERLAP})\n")

    # ---------- Cargar modelo (toma 5-15 seg primera vez) ----------
    print("Cargando modelo de embeddings (primera vez descarga ~500 MB)...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    dim = model.get_sentence_embedding_dimension()
    print(f"Modelo cargado. Dimensión: {dim}\n")

    if dim != 384:
        print(f"⚠ ADVERTENCIA: modelo devuelve {dim} dims pero la tabla está en 384")
        print(f"  Si cambiaste el modelo, ajusta también db/migrations/001_pgvector_rag.sql")
        return 1

    # ---------- Conexión BD ----------
    with psycopg.connect(DSN, autocommit=False) as conn:
        conn.row_factory = dict_row

        if args.reset:
            print("⚠ RESET: borrando embeddings existentes...")
            conn.execute("DELETE FROM documento_chunk")
            conn.execute("UPDATE informe_control SET rag_estado='pendiente', rag_chunks_count=0, rag_indexed_at=NULL")
            conn.commit()

        # ---------- Listar informes pendientes ----------
        where = "rag_estado = 'pendiente'"
        params: list = []
        if args.informe_id:
            where += " AND id = %s"
            params.append(args.informe_id)
        limit_clause = f"LIMIT {args.limit}" if args.limit else ""

        informes = conn.execute(f"""
            SELECT id, nro_informe, titulo, url_pdf_completo, url_pdf_resumen, obra_id
            FROM informe_control
            WHERE {where}
            ORDER BY id
            {limit_clause}
        """, params).fetchall()

        if not informes:
            print("Sin informes pendientes. Todos indexados.")
            return 0

        print(f"Informes a indexar: {len(informes)}\n")

        cache_dir = Path("backend/data/pdf_cache")
        total_chunks = 0
        ok, sin_texto, fallidos = 0, 0, 0

        for inf in tqdm(informes, desc="Indexando"):
            pdf_url = inf["url_pdf_completo"] or inf["url_pdf_resumen"]
            if not pdf_url:
                conn.execute(
                    "UPDATE informe_control SET rag_estado='descarga_fallida' WHERE id=%s",
                    (inf["id"],),
                )
                conn.commit()
                fallidos += 1
                continue

            pdf_bytes = descargar_pdf(pdf_url, cache_dir=cache_dir)
            if not pdf_bytes:
                conn.execute(
                    "UPDATE informe_control SET rag_estado='descarga_fallida' WHERE id=%s",
                    (inf["id"],),
                )
                conn.commit()
                fallidos += 1
                continue

            paginas = extraer_texto_pdf(pdf_bytes)
            texto_total = "\n\n".join(t for _, t in paginas)

            if not texto_total or len(texto_total.split()) < 50:
                # PDF escaneado, sin texto extraíble
                conn.execute(
                    "UPDATE informe_control SET rag_estado='pendiente_ocr' WHERE id=%s",
                    (inf["id"],),
                )
                conn.commit()
                sin_texto += 1
                continue

            # Chunkear todo el documento (con tracking de página por chunk)
            chunks_con_pagina: list[tuple[int, str]] = []
            for pagina, texto_pag in paginas:
                pieces = chunkear(texto_pag)
                for piece in pieces:
                    chunks_con_pagina.append((pagina, piece))

            if not chunks_con_pagina:
                conn.execute(
                    "UPDATE informe_control SET rag_estado='no_indexable' WHERE id=%s",
                    (inf["id"],),
                )
                conn.commit()
                sin_texto += 1
                continue

            # Generar embeddings en batch (más rápido que uno por uno)
            textos = [t for _, t in chunks_con_pagina]
            embeddings = model.encode(textos, show_progress_bar=False, convert_to_numpy=True)

            # INSERT chunks
            for idx, ((pagina, texto), emb) in enumerate(zip(chunks_con_pagina, embeddings)):
                # pgvector espera string formato '[v1,v2,...]'
                vec_str = "[" + ",".join(f"{x:.6f}" for x in emb) + "]"
                tokens_aprox = len(texto.split())
                conn.execute("""
                    INSERT INTO documento_chunk
                        (informe_id, obra_id, pagina, chunk_idx, texto, embedding, tokens)
                    VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                    ON CONFLICT (informe_id, chunk_idx) DO NOTHING
                """, (inf["id"], inf["obra_id"], pagina, idx, texto, vec_str, tokens_aprox))

            # Marcar informe como indexado
            conn.execute("""
                UPDATE informe_control
                SET rag_estado='indexado', rag_chunks_count=%s, rag_indexed_at=%s
                WHERE id=%s
            """, (len(chunks_con_pagina), datetime.now(timezone.utc), inf["id"]))
            conn.commit()
            total_chunks += len(chunks_con_pagina)
            ok += 1

        print(f"\n=== Resumen ===")
        print(f"  Indexados:     {ok}")
        print(f"  Sin texto/OCR: {sin_texto}")
        print(f"  Fallidos:      {fallidos}")
        print(f"  Total chunks:  {total_chunks}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
