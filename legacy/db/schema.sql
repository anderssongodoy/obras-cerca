-- =============================================================
-- Obras Cerca — Schema completo MVP
-- Diseñado para el MD maestro §6 (fichas) + §8 (fuentes)
-- Ámbito MVP: Lima Metropolitana (43) + Provincia Constitucional del Callao (7)
-- =============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- =============================================================
-- 1. CATÁLOGOS
-- =============================================================

CREATE TABLE IF NOT EXISTS distrito (
    id           SERIAL PRIMARY KEY,
    ubigeo       VARCHAR(6) UNIQUE NOT NULL,
    departamento TEXT NOT NULL,
    provincia    TEXT NOT NULL,
    distrito     TEXT NOT NULL,
    ambito_mvp   BOOLEAN NOT NULL DEFAULT FALSE,
    geom         geometry(MultiPolygon, 4326),  -- contornos (carga futura desde INEI shapefile)
    centroide    geometry(Point, 4326)          -- fallback para centrar el mapa
);
CREATE INDEX IF NOT EXISTS distrito_geom_idx     ON distrito USING GIST(geom);
CREATE INDEX IF NOT EXISTS distrito_centroide_idx ON distrito USING GIST(centroide);
CREATE INDEX IF NOT EXISTS distrito_ambito_idx    ON distrito(ambito_mvp) WHERE ambito_mvp;

CREATE TABLE IF NOT EXISTS entidad (
    id              SERIAL PRIMARY KEY,
    codigo_entidad  TEXT,                       -- código Infobras (entidad ejecutora)
    nombre          TEXT NOT NULL,
    nombre_norm     TEXT NOT NULL,              -- uppercase trim para dedupe
    nivel_gobierno  TEXT,                       -- nacional/regional/local
    sector          TEXT,
    UNIQUE (nombre_norm)
);
CREATE INDEX IF NOT EXISTS entidad_codigo_idx ON entidad(codigo_entidad);

CREATE TABLE IF NOT EXISTS contratista (
    id             SERIAL PRIMARY KEY,
    ruc            VARCHAR(11) UNIQUE NOT NULL,
    razon_social   TEXT NOT NULL,
    estado_ruc     TEXT,                        -- ACTIVO/SUSPENDIDO/BAJA — futuro consulta SUNAT
    tiene_sancion  BOOLEAN NOT NULL DEFAULT FALSE,
    fuente_sancion TEXT,                        -- OECE inhabilitados, etc.
    actualizado_en TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS fuente_dato (
    id                    SERIAL PRIMARY KEY,
    nombre                TEXT UNIQUE NOT NULL, -- 'infobras_obras_publicas', 'ocds_releases', etc.
    descripcion           TEXT,
    url                   TEXT,
    ultima_ingestion      TIMESTAMPTZ,
    filas_ingestadas      BIGINT,
    notas                 TEXT
);

-- =============================================================
-- 2. NÚCLEO — OBRA
-- =============================================================

CREATE TABLE IF NOT EXISTS obra (
    id                                  BIGSERIAL PRIMARY KEY,
    codigo_infobras                     BIGINT UNIQUE,                  -- ObraId Infobras
    codigo_unico_inversion              TEXT,                           -- CUI / Invierte.pe
    codigo_snip                         TEXT,
    nombre                              TEXT NOT NULL,
    entidad_id                          INT REFERENCES entidad(id),
    contratista_id                      INT REFERENCES contratista(id),
    supervisor_id                       INT REFERENCES contratista(id), -- la supervisora también es un RUC
    distrito_id                         INT REFERENCES distrito(id),
    direccion                           TEXT,
    tipo_ubicacion                      TEXT,                           -- exacta / referencial
    geom                                geometry(Point, 4326),          -- lat/lon (geocoding pendiente)
    geom_fuente                         TEXT,                           -- nominatim / google / infobras / inferred-distrito

    naturaleza                          TEXT,                           -- Construcción, Mejoramiento, ...
    tipo_obra_nivel1                    TEXT,
    tipo_obra_nivel2                    TEXT,
    tipo_obra_nivel3                    TEXT,
    modalidad_ejecucion                 TEXT,                           -- Contrata / Administración directa
    sector                              TEXT,
    estado_ejecucion                    TEXT,

    -- Fechas
    fecha_inicio                        DATE,
    fecha_fin_programada                DATE,
    fecha_fin_reprogramada              DATE,
    fecha_fin_real                      DATE,
    fecha_ultimo_avance                 DATE,

    -- Montos (en soles)
    monto_contrato                      NUMERIC(18, 2),
    monto_aprobado                      NUMERIC(18, 2),
    monto_ejecutado                     NUMERIC(18, 2),
    moneda                              VARCHAR(8) DEFAULT 'PEN',

    -- Avances
    avance_fisico_real                  NUMERIC(6, 2),                  -- % 0-100
    avance_fisico_programado            NUMERIC(6, 2),
    porcentaje_ejecucion_financiera     NUMERIC(6, 2),

    -- Flags
    existe_paralizacion                 BOOLEAN NOT NULL DEFAULT FALSE,
    marca_reconstruccion                BOOLEAN NOT NULL DEFAULT FALSE,
    marca_reactivacion_economica        BOOLEAN NOT NULL DEFAULT FALSE,
    es_reservada                        BOOLEAN NOT NULL DEFAULT FALSE,

    -- Trazabilidad
    fuente                              TEXT NOT NULL,                  -- p.ej. 'infobras_obras_publicas_2026-05-15'
    ingestado_en                        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS obra_geom_idx                ON obra USING GIST(geom);
CREATE INDEX IF NOT EXISTS obra_distrito_idx            ON obra(distrito_id);
CREATE INDEX IF NOT EXISTS obra_contratista_idx         ON obra(contratista_id);
CREATE INDEX IF NOT EXISTS obra_entidad_idx             ON obra(entidad_id);
CREATE INDEX IF NOT EXISTS obra_existe_paralizacion_idx ON obra(existe_paralizacion) WHERE existe_paralizacion;
CREATE INDEX IF NOT EXISTS obra_codigo_infobras_idx     ON obra(codigo_infobras);
CREATE INDEX IF NOT EXISTS obra_cui_idx                 ON obra(codigo_unico_inversion);

-- =============================================================
-- 3. PARALIZACIÓN — detalle (1 row por obra paralizada, futura puede haber histórico)
-- =============================================================

CREATE TABLE IF NOT EXISTS obra_paralizacion (
    id                   BIGSERIAL PRIMARY KEY,
    obra_id              BIGINT NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    fecha_paralizacion   DATE,
    dias_paralizado      INT,
    causal               TEXT,
    comentarios          TEXT,
    avance_fisico_al_par NUMERIC(6, 2),
    avance_fin_al_par    NUMERIC(6, 2),
    fuente               TEXT NOT NULL,
    ingestado_en         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (obra_id, fecha_paralizacion)
);
CREATE INDEX IF NOT EXISTS paralizacion_obra_idx ON obra_paralizacion(obra_id);
CREATE INDEX IF NOT EXISTS paralizacion_dias_idx ON obra_paralizacion(dias_paralizado);

-- =============================================================
-- 4. AVANCES — histórico (futuro; Infobras solo trae el último)
-- =============================================================

CREATE TABLE IF NOT EXISTS obra_avance (
    id                       BIGSERIAL PRIMARY KEY,
    obra_id                  BIGINT NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    anio                     INT,
    mes                      INT,
    fecha_registro           DATE,
    avance_fisico_real       NUMERIC(6, 2),
    avance_fisico_programado NUMERIC(6, 2),
    monto_ejecutado          NUMERIC(18, 2),
    monto_programado         NUMERIC(18, 2),
    UNIQUE (obra_id, anio, mes)
);
CREATE INDEX IF NOT EXISTS avance_obra_idx ON obra_avance(obra_id);

-- =============================================================
-- 5. OCDS — PROCEDIMIENTOS DE SELECCIÓN
-- =============================================================

CREATE TABLE IF NOT EXISTS procedimiento_seleccion (
    id                  BIGSERIAL PRIMARY KEY,
    ocid                TEXT UNIQUE,                       -- OCDS canonical id
    fuente_ocds         TEXT,                              -- seace_v1/v2/v3
    nomenclatura        TEXT,                              -- nomenclatura SEACE
    entidad_id          INT REFERENCES entidad(id),
    contratista_id      INT REFERENCES contratista(id),
    objeto              TEXT,
    descripcion         TEXT,
    monto_referencial   NUMERIC(18, 2),
    monto_adjudicado    NUMERIC(18, 2),
    moneda              VARCHAR(8) DEFAULT 'PEN',
    numero_postores     INT,
    fecha_convocatoria  DATE,
    fecha_buena_pro     DATE,
    fecha_contrato      DATE,
    estado              TEXT,
    tipo_procedimiento  TEXT,
    obra_id             BIGINT REFERENCES obra(id),        -- cruce con Infobras por CUI/RUC
    ingestado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS proc_contratista_idx ON procedimiento_seleccion(contratista_id);
CREATE INDEX IF NOT EXISTS proc_entidad_idx     ON procedimiento_seleccion(entidad_id);
CREATE INDEX IF NOT EXISTS proc_obra_idx        ON procedimiento_seleccion(obra_id);

-- =============================================================
-- 6. ÓRDENES ≤ 8 UIT (futuro Pentaho/CONOSCE)
-- =============================================================

CREATE TABLE IF NOT EXISTS orden_compra_servicio (
    id              BIGSERIAL PRIMARY KEY,
    numero_orden    TEXT,
    tipo            TEXT,                                  -- 'compra' / 'servicio'
    entidad_id      INT REFERENCES entidad(id),
    contratista_id  INT REFERENCES contratista(id),
    monto_soles     NUMERIC(18, 2),
    fecha_emision   DATE,
    descripcion     TEXT,
    url_documento   TEXT,
    fuente          TEXT NOT NULL,                         -- 'pentaho/conosce/2024'
    ingestado_en    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS orden_entidad_idx     ON orden_compra_servicio(entidad_id);
CREATE INDEX IF NOT EXISTS orden_contratista_idx ON orden_compra_servicio(contratista_id);
CREATE INDEX IF NOT EXISTS orden_fecha_idx       ON orden_compra_servicio(fecha_emision);

-- =============================================================
-- 7. SEÑALES DE REVISIÓN — el corazón del producto
-- =============================================================

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_senal') THEN
        CREATE TYPE tipo_senal AS ENUM (
            'paralizacion',
            'paralizacion_prolongada',
            'concentracion_menores',
            'monto_atipico',
            'sanciones_oece',
            'avance_fisico_estancado'
        );
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS senal_revision (
    id              BIGSERIAL PRIMARY KEY,
    tipo            tipo_senal NOT NULL,
    obra_id         BIGINT REFERENCES obra(id),
    contratista_id  INT REFERENCES contratista(id),
    entidad_id      INT REFERENCES entidad(id),
    titulo          TEXT NOT NULL,
    explicacion     TEXT,                                  -- lenguaje ciudadano (puede ser generado por IA)
    score           NUMERIC,                               -- prioridad numérica
    formula         TEXT,                                  -- fórmula auditable (string explicativo)
    evidencia       JSONB,                                 -- filas que justifican la señal (para exportar CSV)
    detectada_en    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activa          BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS senal_obra_idx        ON senal_revision(obra_id);
CREATE INDEX IF NOT EXISTS senal_contratista_idx ON senal_revision(contratista_id);
CREATE INDEX IF NOT EXISTS senal_tipo_idx        ON senal_revision(tipo, activa);

-- =============================================================
-- 8. INEI — enriquecimiento distrital (futuro)
-- =============================================================

CREATE TABLE IF NOT EXISTS inei_pobreza_distrito (
    distrito_id          INT PRIMARY KEY REFERENCES distrito(id),
    pobreza_monetaria    NUMERIC(5, 2),
    pobreza_extrema      NUMERIC(5, 2),
    poblacion_estimada   INT,
    anio_referencia      INT,
    fuente               TEXT
);

-- =============================================================
-- 9. VISTAS para la API
-- =============================================================

-- Ficha resumida de obra (lo que se devuelve al hacer click en un punto del mapa)
CREATE OR REPLACE VIEW v_obra_ficha AS
SELECT
    o.id,
    o.codigo_infobras,
    o.codigo_unico_inversion,
    o.nombre,
    o.estado_ejecucion,
    o.naturaleza,
    o.tipo_obra_nivel1,
    o.sector,
    e.nombre        AS entidad_nombre,
    e.nivel_gobierno,
    c.ruc           AS contratista_ruc,
    c.razon_social  AS contratista_nombre,
    d.distrito      AS distrito_nombre,
    d.provincia,
    d.departamento,
    o.direccion,
    o.tipo_ubicacion,
    ST_AsGeoJSON(o.geom) :: jsonb AS geom_geojson,
    o.fecha_inicio,
    o.fecha_fin_programada,
    o.fecha_ultimo_avance,
    o.monto_contrato,
    o.monto_ejecutado,
    o.avance_fisico_real,
    o.avance_fisico_programado,
    o.porcentaje_ejecucion_financiera,
    o.existe_paralizacion,
    o.fuente,
    CASE
        WHEN o.codigo_infobras IS NOT NULL
        THEN 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.codigo_infobras
    END AS infobras_url
FROM obra o
LEFT JOIN entidad     e ON e.id = o.entidad_id
LEFT JOIN contratista c ON c.id = o.contratista_id
LEFT JOIN distrito    d ON d.id = o.distrito_id;

-- Obras del MVP solamente (Lima Metro + Callao)
CREATE OR REPLACE VIEW v_obra_mvp AS
SELECT o.*
FROM obra o
JOIN distrito d ON d.id = o.distrito_id
WHERE d.ambito_mvp;

-- Resumen por distrito MVP (para sidebar/agregados)
CREATE OR REPLACE VIEW v_resumen_distrito AS
SELECT
    d.id          AS distrito_id,
    d.ubigeo,
    d.distrito,
    d.provincia,
    d.departamento,
    COUNT(o.id)                                                                  AS total_obras,
    COUNT(*) FILTER (WHERE o.existe_paralizacion)                                AS paralizadas,
    COUNT(*) FILTER (WHERE o.estado_ejecucion ILIKE '%ejecuc%')                  AS en_ejecucion,
    COUNT(*) FILTER (WHERE o.avance_fisico_real >= 100)                          AS terminadas,
    ROUND(AVG(o.avance_fisico_real) :: numeric, 1)                               AS avance_promedio,
    SUM(o.monto_contrato) FILTER (WHERE o.existe_paralizacion)                   AS monto_paralizado
FROM distrito o_d
LEFT JOIN distrito d ON d.id = o_d.id
LEFT JOIN obra o ON o.distrito_id = d.id
WHERE d.ambito_mvp
GROUP BY d.id, d.ubigeo, d.distrito, d.provincia, d.departamento;
