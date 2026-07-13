-- schema_new_tables_spe_ole_dnp.sql
-- Tablas nuevas para SPE, OLE y DNP (datos.gov.co)
-- Ejecutar en SQL Editor de Supabase para crear las tablas antes de correr load_to_supabase.py

-- ============================================================================
-- SPE - Servicio Público de Empleo (proxy: APE SENA)
-- ============================================================================

CREATE TABLE IF NOT EXISTS spe_ape_inscritos_ocupacion (
    id SERIAL PRIMARY KEY,
    id_ocupacion INTEGER,
    ocupacion TEXT,
    nivel TEXT,
    inscritos_2019 NUMERIC,
    inscritos_2020 NUMERIC,
    participacion_2019 NUMERIC,
    participacion_2020 NUMERIC,
    variacion_pct NUMERIC,
    contribucion_variacion NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spe_ocupacion_nivel 
ON spe_ape_inscritos_ocupacion(nivel);

CREATE TABLE IF NOT EXISTS spe_ape_inscritos_nivel (
    id SERIAL PRIMARY KEY,
    nivel TEXT,
    total_inscritos_2019 NUMERIC,
    total_inscritos_2020 NUMERIC,
    ocupaciones INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- OLE - Observatorio Laboral para la Educación (proxy: MEN ETDH)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ole_etdh_programas_activos (
    id SERIAL PRIMARY KEY,
    programa TEXT,
    institucion TEXT,
    departamento TEXT,
    municipio TEXT,
    area_desempeno TEXT,
    tipo_certificado TEXT,
    escolaridad TEXT,
    costo NUMERIC,
    duracion_horas NUMERIC,
    estado_programa TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ole_area 
ON ole_etdh_programas_activos(area_desempeno);

CREATE INDEX IF NOT EXISTS idx_ole_departamento 
ON ole_etdh_programas_activos(departamento);

CREATE TABLE IF NOT EXISTS ole_etdh_resumen_departamento_area (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    area_desempeno TEXT,
    programas INTEGER,
    duracion_promedio_horas NUMERIC,
    costo_promedio NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- DNP - Medición del Desempeño Municipal
-- ============================================================================

CREATE TABLE IF NOT EXISTS dnp_medicion_desempeno_municipal (
    id SERIAL PRIMARY KEY,
    codigo_unico TEXT,
    indicador TEXT,
    codigo_categoria TEXT,
    codigo_subcategoria TEXT,
    codigo_variable TEXT,
    codigo_departamento TEXT,
    departamento TEXT,
    codigo_entidad TEXT,
    entidad TEXT,
    dato NUMERIC,
    etiqueta TEXT,
    anio INTEGER,
    mes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dnp_desempeno_indicador 
ON dnp_medicion_desempeno_municipal(indicador);

CREATE INDEX IF NOT EXISTS idx_dnp_desempeno_entidad 
ON dnp_medicion_desempeno_municipal(entidad);

CREATE TABLE IF NOT EXISTS dnp_medicion_desempeno_ultimo (
    id SERIAL PRIMARY KEY,
    codigo_unico TEXT,
    indicador TEXT,
    codigo_categoria TEXT,
    codigo_subcategoria TEXT,
    codigo_variable TEXT,
    codigo_departamento TEXT,
    departamento TEXT,
    codigo_entidad TEXT,
    entidad TEXT,
    dato NUMERIC,
    etiqueta TEXT,
    anio INTEGER,
    mes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dnp_desempeno_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    promedio_desempeno NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
