-- =====================================================================
-- Obras Cerca — Schema v2 (BD obrascerca_v2)
-- Diseño: MEF/Invierte.pe es el MAESTRO. Infobras es satélite.
-- Cruce determinístico de fuentes. Soporta saldos de obra. Trazabilidad.
-- =====================================================================

-- =====================================================================
-- ENUMS
-- =====================================================================

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_entidad') THEN
        CREATE TYPE tipo_entidad AS ENUM (
            'municipalidad_distrital',
            'municipalidad_provincial',
            'gobierno_regional',
            'ministerio',
            'organismo_autonomo',
            'empresa_estatal',
            'universidad_nacional',
            'otro'
        );
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'estado_proyecto_mef') THEN
        CREATE TYPE estado_proyecto_mef AS ENUM (
            'ACTIVO',
            'DESACTIVADO_TEMPORAL',
            'DESACTIVADO_PERMANENTE',
            'CERRADO',
            'NO_VERIFICADO'
        );
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'tipo_senal') THEN
        CREATE TYPE tipo_senal AS ENUM (
            'sobrecosto',
            'discrepancia_avance',
            'paralizacion_real',
            'paralizada_zombie',
            'inactiva_mef',
            'saldos_pendientes',
            'concentracion_menores',
            'sancion_oece'
        );
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'fuente_dato_tipo') THEN
        CREATE TYPE fuente_dato_tipo AS ENUM (
            'mef_ssi',
            'mef_siaf',
            'infobras_bulk',
            'infobras_ficha_live',
            'infobras_wfs',
            'contraloria_informe_control',
            'contraloria_anexo_paralizadas',
            'pte_listado_entidades',
            'pte_mapeo_idue',
            'seace_pentaho_conosce',
            'seace_ocds_oece',
            'sunat_padron_ruc',
            'oece_sanciones'
        );
    END IF;
END $$;

-- =====================================================================
-- CATÁLOGOS
-- =====================================================================

-- 50 distritos del ámbito MVP: Lima Metropolitana + Provincia Constitucional del Callao
CREATE TABLE IF NOT EXISTS distrito (
    id              SERIAL PRIMARY KEY,
    ubigeo          VARCHAR(6) UNIQUE NOT NULL,
    departamento    TEXT NOT NULL,
    provincia       TEXT NOT NULL,
    distrito        TEXT NOT NULL,
    ambito_mvp      BOOLEAN NOT NULL DEFAULT FALSE,
    centroide_lat   NUMERIC(10, 7),
    centroide_lon   NUMERIC(10, 7),
    poblacion_inei  INTEGER,
    pobreza_pct     NUMERIC(5, 2)
);
CREATE INDEX IF NOT EXISTS distrito_ambito_idx ON distrito(ambito_mvp) WHERE ambito_mvp;
CREATE INDEX IF NOT EXISTS distrito_latlon_idx ON distrito(centroide_lat, centroide_lon);


-- Entidades públicas. Catálogo desde PTE de transparencia.gob.pe.
-- Cubre los 7 tipos de poder/sector (Tipo_Pod 1..7).
CREATE TABLE IF NOT EXISTS entidad (
    id                  SERIAL PRIMARY KEY,
    pte_id_entidad      INTEGER UNIQUE,                  -- clave para PTE + scraping IdUE
    siaf_idue           INTEGER,                         -- clave para todos los endpoints MEF
    ruc                 VARCHAR(11),
    nombre              TEXT NOT NULL,
    nombre_norm         TEXT UNIQUE NOT NULL,            -- uppercase sin tildes para dedupe
    sigla               TEXT,
    tipo                tipo_entidad NOT NULL DEFAULT 'otro',
    tipo_pod_pte        SMALLINT,                        -- 1..7 según PTE
    sector              TEXT,
    nivel_gobierno      TEXT,                            -- nacional/regional/local
    distrito_id         INTEGER REFERENCES distrito(id), -- sede física si aplica
    descubierto_en      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS entidad_pte_idx     ON entidad(pte_id_entidad);
CREATE INDEX IF NOT EXISTS entidad_idue_idx    ON entidad(siaf_idue);
CREATE INDEX IF NOT EXISTS entidad_ruc_idx     ON entidad(ruc);
CREATE INDEX IF NOT EXISTS entidad_tipo_idx    ON entidad(tipo);


-- Contratistas (RUC + razón social). Se llenan al descubrir contratos.
CREATE TABLE IF NOT EXISTS contratista (
    id                  SERIAL PRIMARY KEY,
    ruc                 VARCHAR(11) UNIQUE NOT NULL,
    razon_social        TEXT NOT NULL,
    razon_social_norm   TEXT NOT NULL,                   -- uppercase sin tildes
    tipo_contribuyente  TEXT,                            -- futuro: consultar SUNAT
    estado_ruc          TEXT,
    tiene_sancion_oece  BOOLEAN NOT NULL DEFAULT FALSE,
    fuente_sancion      TEXT,
    descubierto_en      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actualizado_en      TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS contratista_razon_norm_idx ON contratista(razon_social_norm);


-- Catálogo de fuentes usadas y cuándo se descargó cada cosa.
-- Auditabilidad: para cada fila importante de obra/proyecto sabremos
-- qué fuente la alimentó y cuándo.
CREATE TABLE IF NOT EXISTS fuente_dato (
    id                SERIAL PRIMARY KEY,
    tipo              fuente_dato_tipo UNIQUE NOT NULL,
    descripcion       TEXT,
    url_base          TEXT,
    ultima_ingestion  TIMESTAMPTZ,
    filas_ingestadas  BIGINT,
    notas             TEXT
);


-- =====================================================================
-- NÚCLEO — proyecto_mef es el MAESTRO
-- =====================================================================

-- Proyecto de inversión pública (Invierte.pe / SNIP).
-- Es el nivel canónico. Cada CUI tiene una sola fila aquí.
-- Una obra física en Infobras se modela como hija de un proyecto_mef.
CREATE TABLE IF NOT EXISTS proyecto_mef (
    cui                       BIGINT PRIMARY KEY,
    cod_snip                  TEXT,                              -- código viejo SNIP (anterior a Invierte.pe)
    nombre_inversion          TEXT NOT NULL,
    entidad_id                INTEGER REFERENCES entidad(id),
    sector                    TEXT,
    funcion                   TEXT,
    nivel_gobierno            TEXT,
    distrito_id               INTEGER REFERENCES distrito(id),

    -- Estado oficial MEF
    estado                    estado_proyecto_mef NOT NULL DEFAULT 'NO_VERIFICADO',
    situacion                 TEXT,                              -- VIABLE / EN FORMULACION / etc
    marco                     TEXT,                              -- SNIP / INVIERTE.PE

    -- Montos (S/)
    mto_viable                NUMERIC(18, 2),
    costo_actualizado         NUMERIC(18, 2),
    dev_acumulado             NUMERIC(18, 2),
    pim_ano_vigente           NUMERIC(18, 2),
    dev_ano_vigente           NUMERIC(18, 2),

    -- Fechas
    fec_viable                DATE,
    fec_ini_ejec              DATE,
    fec_fin_ejec              DATE,                              -- a veces 5-15 años después

    -- Avance reportado por MEF
    avance_fisico_mef         NUMERIC(6, 2),
    modal_ejec                TEXT,
    beneficiarios             INTEGER,

    -- Trazabilidad
    fuente                    fuente_dato_tipo NOT NULL DEFAULT 'mef_ssi',
    ingestado_en              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verificado_mef_en         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS proyecto_entidad_idx  ON proyecto_mef(entidad_id);
CREATE INDEX IF NOT EXISTS proyecto_distrito_idx ON proyecto_mef(distrito_id);
CREATE INDEX IF NOT EXISTS proyecto_estado_idx   ON proyecto_mef(estado);
CREATE INDEX IF NOT EXISTS proyecto_cod_snip_idx ON proyecto_mef(cod_snip);


-- Obra física registrada en Infobras (NOBR_ID).
-- Un proyecto_mef puede tener 1..N obras. Si hay saldos, la "hija"
-- apunta a la "padre" via obra_padre_id.
CREATE TABLE IF NOT EXISTS obra (
    id                          BIGSERIAL PRIMARY KEY,
    nobr_id                     BIGINT UNIQUE NOT NULL,          -- Código INFOBRAS
    cui                         BIGINT NOT NULL REFERENCES proyecto_mef(cui) ON DELETE CASCADE,
    obra_padre_id               BIGINT REFERENCES obra(id),       -- para saldos de obra
    descripcion                 TEXT,                            -- el "COBR_DESCRI" de Infobras
    direccion                   TEXT,
    tipo_ubicacion              TEXT,                            -- exacta / referencial

    -- Geolocalización (fuente preferida: WFS Infobras)
    latitud                     NUMERIC(10, 7),
    longitud                    NUMERIC(10, 7),
    geom_fuente                 TEXT,                            -- 'wfs_infobras' / 'centroide_distrito'

    -- Datos del registro Infobras
    modalidad_ejecucion         TEXT,                            -- Contrata / Administración Directa
    estado_obra_wfs             TEXT,                            -- 'En Ejecución' / 'Paralizada' / 'Finalizada' (WFS Contraloría)
    estado_obra_ficha           TEXT,                            -- estado visible en la ficha pública
    estado_obra_bulk            TEXT,                            -- estado del bulk XLSX (referencial)

    -- Avance y fechas Infobras
    avance_fisico_infobras      NUMERIC(6, 2),
    fecha_ult_avance            DATE,
    fecha_inicio                DATE,
    fecha_fin_programada        DATE,
    fecha_fin_real              DATE,

    -- Contrato
    contratista_id              INTEGER REFERENCES contratista(id),
    supervisor_id               INTEGER REFERENCES contratista(id),
    numero_contrato             TEXT,
    fecha_contrato              DATE,
    monto_contrato              NUMERIC(18, 2),
    monto_aprobacion            NUMERIC(18, 2),

    -- Flags derivados
    existe_paralizacion_mef     BOOLEAN NOT NULL DEFAULT FALSE,  -- de traeListaParalizaPublico
    existe_informe_control      BOOLEAN NOT NULL DEFAULT FALSE,

    -- Trazabilidad y verificación
    fuente                      fuente_dato_tipo NOT NULL,
    ingestado_en                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    verificado_wfs_en           TIMESTAMPTZ,
    verificado_ficha_en         TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS obra_cui_idx        ON obra(cui);
CREATE INDEX IF NOT EXISTS obra_padre_idx      ON obra(obra_padre_id);
CREATE INDEX IF NOT EXISTS obra_contratista_idx ON obra(contratista_id);
CREATE INDEX IF NOT EXISTS obra_geo_idx        ON obra(latitud, longitud) WHERE latitud IS NOT NULL;
CREATE INDEX IF NOT EXISTS obra_estado_wfs_idx ON obra(estado_obra_wfs);


-- Avance mensual (devengado SIAF + avance físico cuando se reporta).
-- Una fila por (cui, año, mes).
CREATE TABLE IF NOT EXISTS proyecto_avance_mensual (
    id                       BIGSERIAL PRIMARY KEY,
    cui                      BIGINT NOT NULL REFERENCES proyecto_mef(cui) ON DELETE CASCADE,
    anio                     SMALLINT NOT NULL,
    mes                      SMALLINT NOT NULL,
    devengado_mes            NUMERIC(18, 2),
    devengado_acumulado      NUMERIC(18, 2),
    avance_fisico            NUMERIC(6, 2),
    fuente                   fuente_dato_tipo NOT NULL DEFAULT 'mef_siaf',
    UNIQUE (cui, anio, mes)
);


-- Paralizaciones declaradas en MEF (traeListaParalizaPublico).
CREATE TABLE IF NOT EXISTS paralizacion_oficial (
    id                  BIGSERIAL PRIMARY KEY,
    cui                 BIGINT NOT NULL REFERENCES proyecto_mef(cui) ON DELETE CASCADE,
    obra_id             BIGINT REFERENCES obra(id),
    fecha_paralizacion  DATE,
    fecha_reinicio      DATE,
    dias_paralizado     INTEGER,
    causal              TEXT,
    estado              TEXT,                            -- vigente / superada / etc
    detalle             JSONB,
    fuente              fuente_dato_tipo NOT NULL DEFAULT 'mef_ssi',
    ingestado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS paral_cui_idx ON paralizacion_oficial(cui);


-- Procedimientos de selección SEACE (vía traeContratoSeaceDWH de MEF).
CREATE TABLE IF NOT EXISTS procedimiento_seleccion (
    id                       BIGSERIAL PRIMARY KEY,
    cui                      BIGINT REFERENCES proyecto_mef(cui),
    obra_id                  BIGINT REFERENCES obra(id),
    nomenclatura             TEXT,
    objeto_contractual       TEXT,
    contratista_id           INTEGER REFERENCES contratista(id),
    numero_contrato          TEXT,
    fecha_convocatoria       DATE,
    fecha_buena_pro          DATE,
    fecha_suscripcion        DATE,
    valor_referencial        NUMERIC(18, 2),
    monto_contratado         NUMERIC(18, 2),
    moneda                   VARCHAR(8) DEFAULT 'PEN',
    numero_postores          INTEGER,
    estado                   TEXT,
    url_contrato_pdf         TEXT,
    fuente                   fuente_dato_tipo NOT NULL,
    ingestado_en             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS proc_cui_idx          ON procedimiento_seleccion(cui);
CREATE INDEX IF NOT EXISTS proc_contratista_idx  ON procedimiento_seleccion(contratista_id);


-- Informes de control de Contraloría (Orientación de Oficio, Control Concurrente, etc).
CREATE TABLE IF NOT EXISTS informe_control (
    id                  BIGSERIAL PRIMARY KEY,
    obra_id             BIGINT NOT NULL REFERENCES obra(id) ON DELETE CASCADE,
    anio                SMALLINT,
    nro_informe         TEXT,
    titulo              TEXT,
    tipo_servicio       TEXT,                            -- Control Simultáneo / Posterior
    modalidad           TEXT,                            -- ORIENTACION DE OFICIO / CONTROL CONCURRENTE / ...
    fecha_emision       DATE,
    fecha_publicacion   DATE,
    url_pdf_resumen     TEXT,
    url_pdf_completo    TEXT,
    cres_codigo         TEXT UNIQUE,                     -- para deduplicar
    ingestado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS informe_obra_idx ON informe_control(obra_id);


-- Órdenes de compra/servicio ≤ 8 UIT (Pentaho CONOSCE).
-- Independiente del flujo CUI. Se cruza con contratista por RUC.
CREATE TABLE IF NOT EXISTS orden_compra_servicio (
    id                  BIGSERIAL PRIMARY KEY,
    entidad_id          INTEGER REFERENCES entidad(id),
    contratista_id      INTEGER REFERENCES contratista(id),
    numero_orden        TEXT,
    tipo                TEXT,                            -- compra / servicio
    objeto_contractual  TEXT,                            -- BIENES / SERVICIOS
    descripcion         TEXT,
    monto_soles         NUMERIC(18, 2),
    moneda              VARCHAR(8) DEFAULT 'PEN',
    fecha_emision       DATE,
    fecha_registro      DATE,
    estado_contratacion TEXT,                            -- Emitida / Comprometida / Devengada
    tipo_contratacion   TEXT,                            -- 'hasta 8 UIT' / 'Proceso de selección' / etc
    fuente              fuente_dato_tipo NOT NULL DEFAULT 'seace_pentaho_conosce',
    ingestado_en        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS orden_entidad_idx    ON orden_compra_servicio(entidad_id);
CREATE INDEX IF NOT EXISTS orden_contratista_idx ON orden_compra_servicio(contratista_id);
CREATE INDEX IF NOT EXISTS orden_fecha_idx       ON orden_compra_servicio(fecha_emision);


-- Señales de revisión (calculadas con SQL determinístico al final del flujo).
CREATE TABLE IF NOT EXISTS senal_revision (
    id              BIGSERIAL PRIMARY KEY,
    tipo            tipo_senal NOT NULL,
    cui             BIGINT REFERENCES proyecto_mef(cui),
    obra_id         BIGINT REFERENCES obra(id),
    entidad_id      INTEGER REFERENCES entidad(id),
    contratista_id  INTEGER REFERENCES contratista(id),
    titulo          TEXT NOT NULL,
    resumen         TEXT,                                -- frase para el ciudadano
    score           NUMERIC,                             -- prioridad
    formula         TEXT,                                -- regla SQL en lenguaje natural
    evidencia       JSONB,                               -- datos crudos auditables
    detectada_en    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    activa          BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS senal_tipo_idx       ON senal_revision(tipo) WHERE activa;
CREATE INDEX IF NOT EXISTS senal_cui_idx        ON senal_revision(cui);
CREATE INDEX IF NOT EXISTS senal_obra_idx       ON senal_revision(obra_id);
CREATE INDEX IF NOT EXISTS senal_contratista_idx ON senal_revision(contratista_id);


-- Cache de explicaciones generadas por IA (no se regeneran cada request).
CREATE TABLE IF NOT EXISTS explicacion_ia (
    entidad_tipo    TEXT NOT NULL,                       -- 'obra' / 'contratista' / 'senal'
    entidad_id      BIGINT NOT NULL,
    audiencia       TEXT NOT NULL DEFAULT 'ciudadano',   -- 'ciudadano' / 'periodista'
    provider        TEXT NOT NULL,
    modelo          TEXT,
    texto           TEXT NOT NULL,
    tokens_input    INTEGER,
    tokens_output   INTEGER,
    generado_en     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (entidad_tipo, entidad_id, audiencia)
);


-- =====================================================================
-- VISTAS — usadas por la API
-- =====================================================================

-- Ficha rica de obra con cruce de fuentes ya resuelto.
CREATE OR REPLACE VIEW v_obra_ficha AS
SELECT
    o.id,
    o.nobr_id,
    o.cui,
    p.cod_snip,
    p.nombre_inversion,
    o.descripcion AS nombre_obra,
    e.nombre AS entidad_nombre,
    e.tipo AS entidad_tipo,
    e.sector AS entidad_sector,
    c.ruc AS contratista_ruc,
    c.razon_social AS contratista_nombre,
    d.distrito AS distrito_nombre,
    d.ubigeo AS distrito_ubigeo,
    o.direccion,
    o.latitud,
    o.longitud,
    o.geom_fuente,
    -- 3 niveles de "estado de obra"
    o.estado_obra_wfs,        -- la verdad oficial Contraloría
    o.estado_obra_ficha,      -- lo que muestra la ficha pública
    p.estado AS estado_proyecto_mef,  -- ACTIVO / DESACTIVADO_PERMANENTE / ...
    -- Avances (cruzados)
    o.avance_fisico_infobras,
    p.avance_fisico_mef,
    p.dev_acumulado AS devengado_siaf,
    o.fecha_ult_avance,
    p.fec_ini_ejec AS fecha_inicio_mef,
    p.fec_fin_ejec AS fecha_fin_mef,
    -- Montos
    p.mto_viable,
    p.costo_actualizado,
    o.monto_contrato,
    -- Sobrecosto calculado
    CASE WHEN p.mto_viable > 0
         THEN ROUND(100.0 * (p.costo_actualizado - p.mto_viable) / p.mto_viable, 2)
    END AS sobrecosto_pct,
    -- Flags
    o.existe_paralizacion_mef,
    o.existe_informe_control,
    (o.obra_padre_id IS NOT NULL) AS es_saldo_obra,
    -- URLs para verificación humana
    'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=' || o.nobr_id AS url_infobras_ficha,
    'https://ofi5.mef.gob.pe/ssi/Ssi/Index?tipo=2&codigo=' || o.cui AS url_mef_ssi,
    'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/InformeControl?obraId=' || o.nobr_id AS url_infobras_informes
FROM obra o
JOIN proyecto_mef p ON p.cui = o.cui
LEFT JOIN entidad     e ON e.id = p.entidad_id
LEFT JOIN contratista c ON c.id = o.contratista_id
LEFT JOIN distrito    d ON d.id = COALESCE(p.distrito_id, e.distrito_id);


-- Vista del ámbito MVP (Lima Metro + Callao) solamente.
CREATE OR REPLACE VIEW v_obra_mvp AS
SELECT v.* FROM v_obra_ficha v
JOIN distrito d ON d.ubigeo = v.distrito_ubigeo
WHERE d.ambito_mvp;


-- Resumen por distrito MVP.
CREATE OR REPLACE VIEW v_resumen_distrito AS
SELECT
    d.id            AS distrito_id,
    d.ubigeo,
    d.distrito,
    d.provincia,
    d.centroide_lat AS lat,
    d.centroide_lon AS lon,
    COUNT(DISTINCT p.cui)                                                        AS total_proyectos,
    COUNT(DISTINCT o.id)                                                         AS total_obras,
    COUNT(DISTINCT o.id) FILTER (WHERE o.estado_obra_wfs = 'Paralizada')         AS paralizadas_wfs,
    COUNT(DISTINCT o.id) FILTER (WHERE p.estado = 'DESACTIVADO_PERMANENTE')      AS inactivas_mef,
    COUNT(DISTINCT o.id) FILTER (WHERE o.obra_padre_id IS NOT NULL)              AS saldos_obra,
    COUNT(DISTINCT o.id) FILTER (WHERE o.existe_informe_control)                 AS con_informe_control,
    COALESCE(SUM(p.costo_actualizado), 0)::bigint                                AS monto_total
FROM distrito d
LEFT JOIN proyecto_mef p ON p.distrito_id = d.id
LEFT JOIN obra o ON o.cui = p.cui
WHERE d.ambito_mvp
GROUP BY d.id;
