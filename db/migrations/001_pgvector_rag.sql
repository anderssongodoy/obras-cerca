-- Migración 001 — Tabla documento_chunk para RAG sobre informes de Contraloría.
--
-- Aplicar:
--   PSQL local:
--     psql -h localhost -U postgres -d obrascerca_v2 -f db/migrations/001_pgvector_rag.sql
--
--   En la EC2:
--     ssh ... 'sudo -u postgres psql -d obrascerca_v2 -f /opt/obras-cerca/db/migrations/001_pgvector_rag.sql'

-- Extensión pgvector (idempotente)
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de chunks de PDFs indexados.
-- Dimensión del vector según provider:
--   sentence-transformers paraphrase-multilingual-MiniLM-L12-v2 → 384  (default)
--   OpenAI text-embedding-3-small                                → 1536
--   Voyage / Cohere multilingual                                 → 1024
-- Si cambias provider: DROP TABLE documento_chunk; y aplicar migración con la dim correcta.
CREATE TABLE IF NOT EXISTS documento_chunk (
    id            SERIAL PRIMARY KEY,
    informe_id    INT NOT NULL REFERENCES informe_control(id) ON DELETE CASCADE,
    obra_id       INT REFERENCES obra(id) ON DELETE CASCADE,       -- denormalizado para filtros rápidos
    pagina        INT,                                              -- 1-indexed o NULL si no aplica
    chunk_idx     INT NOT NULL,                                     -- 0-indexed dentro del documento
    texto         TEXT NOT NULL,
    embedding     vector(384),                                      -- NULL si aún no embeddings (degradado)
    tokens        INT,                                              -- conteo aproximado para auditoría de costo
    indexed_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE (informe_id, chunk_idx)
);

-- Índice IVFFlat para búsqueda por similitud coseno.
-- lists=100 es razonable para hasta ~10k chunks. Ajustar a sqrt(n) si crece.
CREATE INDEX IF NOT EXISTS documento_chunk_embedding_idx
    ON documento_chunk USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS documento_chunk_obra_id_idx ON documento_chunk(obra_id);
CREATE INDEX IF NOT EXISTS documento_chunk_informe_id_idx ON documento_chunk(informe_id);

-- Marcador de estado por informe (para no reintentar PDFs que ya fallaron).
ALTER TABLE informe_control
    ADD COLUMN IF NOT EXISTS rag_estado TEXT DEFAULT 'pendiente',
    -- valores: 'pendiente', 'indexado', 'pendiente_ocr', 'descarga_fallida', 'no_indexable'
    ADD COLUMN IF NOT EXISTS rag_chunks_count INT DEFAULT 0,
    ADD COLUMN IF NOT EXISTS rag_indexed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS informe_control_rag_estado_idx ON informe_control(rag_estado);

-- Tabla de Q&A cache: misma pregunta sobre la misma obra → devolver respuesta cacheada
-- (ahorra tokens + latencia para preguntas frecuentes en demo).
CREATE TABLE IF NOT EXISTS chat_qa_cache (
    id            SERIAL PRIMARY KEY,
    obra_id       INT NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    pregunta_hash CHAR(64) NOT NULL,                  -- sha256 de pregunta normalizada
    pregunta      TEXT NOT NULL,
    respuesta     TEXT NOT NULL,
    fuentes       JSONB,                              -- [{informe_id, pagina, chunk_idx}, ...]
    tokens_total  INT,                                -- conteo aproximado
    creado_en     TIMESTAMPTZ DEFAULT now(),
    UNIQUE (obra_id, pregunta_hash)
);

CREATE INDEX IF NOT EXISTS chat_qa_cache_obra_idx ON chat_qa_cache(obra_id);

COMMENT ON TABLE documento_chunk IS 'Chunks de PDFs de informes de Contraloría con embeddings. Base del chat RAG.';
COMMENT ON COLUMN documento_chunk.embedding IS 'Vector de 384 dim — paraphrase-multilingual-MiniLM-L12-v2 (sentence-transformers local).';
COMMENT ON TABLE chat_qa_cache IS 'Cache de Q&A para no quemar tokens en preguntas repetidas durante la demo.';

-- Si la migración se corre como superuser (postgres), las tablas quedan con owner postgres.
-- Garantizamos que el user de la app sea owner para que pueda INSERT/UPDATE/DELETE.
-- (No-op si ya es el owner.)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'obrascerca_app') THEN
        EXECUTE 'ALTER TABLE documento_chunk OWNER TO obrascerca_app';
        EXECUTE 'ALTER TABLE chat_qa_cache OWNER TO obrascerca_app';
        EXECUTE 'ALTER SEQUENCE documento_chunk_id_seq OWNER TO obrascerca_app';
        EXECUTE 'ALTER SEQUENCE chat_qa_cache_id_seq OWNER TO obrascerca_app';
    END IF;
END $$;
