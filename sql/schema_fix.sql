-- schema_fix.sql — Corrige tablas con nombres de columna incorrectos

-- 1. PILA
DROP TABLE IF EXISTS pila_resumen_sector CASCADE;
CREATE TABLE pila_resumen_sector (
    id SERIAL PRIMARY KEY,
    actividadeconomicadesc TEXT,
    total_cotizantes NUMERIC,
    total_cotizaciones NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

DROP TABLE IF EXISTS pila_resumen_tipo CASCADE;
CREATE TABLE pila_resumen_tipo (
    id SERIAL PRIMARY KEY,
    tipocotizantepiladesc TEXT,
    total_cotizantes NUMERIC,
    total_cotizaciones NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 2. RUES empresas nuevas (anio_matricula acepta FLOAT)
DROP TABLE IF EXISTS rues_empresas_nuevas CASCADE;
CREATE TABLE rues_empresas_nuevas (
    id SERIAL PRIMARY KEY,
    anio_matricula NUMERIC,
    ciiu2 TEXT,
    empresas_nuevas NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. SENA
DROP TABLE IF EXISTS sena_programas_activos CASCADE;
CREATE TABLE sena_programas_activos (
    id SERIAL PRIMARY KEY,
    programa TEXT,
    departamento TEXT,
    area_desempeno TEXT,
    tipo_certificado TEXT,
    escolaridad TEXT,
    costo NUMERIC,
    duracion_horas NUMERIC,
    estado_programa TEXT,
    institucion TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 4. Saber Pro
DROP TABLE IF EXISTS saberpro_resumen_programas CASCADE;
CREATE TABLE saberpro_resumen_programas (
    id SERIAL PRIMARY KEY,
    institucion TEXT,
    programa TEXT,
    departamento TEXT,
    mod_razona_cuantitat_punt NUMERIC,
    mod_comuni_escrita_punt NUMERIC,
    mod_lectura_critica_punt NUMERIC,
    mod_ingles_punt NUMERIC,
    mod_competen_ciudada_punt NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);
