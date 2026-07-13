-- ============================================================================
-- SCHEMA NUEVAS TABLAS ALBA - Datos procesados ETL (GEIH, OLE, ESCO, EMICRON)
-- Ejecutar en SQL Editor de Supabase
-- ============================================================================

-- ============================================================================
-- GEIH - 52 meses (2022-2026)
-- ============================================================================

CREATE TABLE IF NOT EXISTS geih_resumen_nacional (
    id SERIAL PRIMARY KEY,
    periodo TEXT,
    ano INTEGER,
    mes INTEGER,
    pea_nacional NUMERIC,
    desempleados_nacional NUMERIC,
    tasa_desempleo_nacional NUMERIC,
    empleo_nacional NUMERIC,
    salario_promedio_nacional NUMERIC,
    informales_nacional NUMERIC,
    tasa_informalidad_nacional NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_resumen_periodo ON geih_resumen_nacional(periodo);

CREATE TABLE IF NOT EXISTS geih_desempleo_mensual (
    id SERIAL PRIMARY KEY,
    periodo TEXT,
    ano INTEGER,
    mes INTEGER,
    dpto INTEGER,
    pea NUMERIC,
    desempleados NUMERIC,
    tasa NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_desempleo_periodo ON geih_desempleo_mensual(periodo);
CREATE INDEX IF NOT EXISTS idx_geih_desempleo_dpto ON geih_desempleo_mensual(dpto);

CREATE TABLE IF NOT EXISTS geih_empleo_sector_mensual (
    id SERIAL PRIMARY KEY,
    periodo TEXT,
    ano INTEGER,
    mes INTEGER,
    rama_ciiu NUMERIC,
    empleo NUMERIC,
    salario_promedio NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_sector_periodo ON geih_empleo_sector_mensual(periodo);
CREATE INDEX IF NOT EXISTS idx_geih_sector_rama ON geih_empleo_sector_mensual(rama_ciiu);

CREATE TABLE IF NOT EXISTS geih_informalidad_mensual (
    id SERIAL PRIMARY KEY,
    periodo TEXT,
    ano INTEGER,
    mes INTEGER,
    dpto INTEGER,
    empleo NUMERIC,
    informales NUMERIC,
    tasa_informalidad NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_info_periodo ON geih_informalidad_mensual(periodo);

CREATE TABLE IF NOT EXISTS geih_empleo_depto_sector (
    id SERIAL PRIMARY KEY,
    periodo TEXT,
    ano INTEGER,
    mes INTEGER,
    dpto INTEGER,
    rama_ciiu NUMERIC,
    empleo NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_depto_sector_periodo ON geih_empleo_depto_sector(periodo);
CREATE INDEX IF NOT EXISTS idx_geih_depto_sector_dpto ON geih_empleo_depto_sector(dpto);

CREATE TABLE IF NOT EXISTS geih_salario_ocupacion (
    id SERIAL PRIMARY KEY,
    oficio_c8 NUMERIC,
    salario_promedio NUMERIC,
    salario_mediano NUMERIC,
    empleo_total NUMERIC,
    ocupados_muestra INTEGER,
    periodo TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_geih_salario_oficio ON geih_salario_ocupacion(oficio_c8);

-- ============================================================================
-- OLE - Ingresos por carrera (2001-2022)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ole_ingresos_por_programa (
    id SERIAL PRIMARY KEY,
    programa TEXT,
    rango_ingreso TEXT,
    graduados INTEGER,
    porcentaje NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ole_prog_programa ON ole_ingresos_por_programa(programa);

CREATE TABLE IF NOT EXISTS ole_ingresos_por_area (
    id SERIAL PRIMARY KEY,
    area TEXT,
    rango_ingreso TEXT,
    graduados INTEGER,
    porcentaje NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ole_ingresos_por_nivel (
    id SERIAL PRIMARY KEY,
    nivel_formacion TEXT,
    rango_ingreso TEXT,
    graduados INTEGER,
    porcentaje NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ole_ingresos_por_ies (
    id SERIAL PRIMARY KEY,
    ies TEXT,
    rango_modal TEXT,
    graduados_rango_modal INTEGER,
    total_graduados INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ole_graduados_por_anio (
    id SERIAL PRIMARY KEY,
    ano_grado INTEGER,
    area TEXT,
    graduados INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- ESCO - Ocupaciones y habilidades
-- ============================================================================

CREATE TABLE IF NOT EXISTS esco_ocupaciones (
    id SERIAL PRIMARY KEY,
    uri TEXT,
    nombre TEXT,
    nombres_alternativos TEXT,
    nombres_ocultos TEXT,
    codigo_isco TEXT,
    codigo_nace TEXT,
    definicion TEXT,
    nota_profesion_regulada TEXT,
    nota_alcance TEXT,
    esquema TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esco_occ_nombre ON esco_ocupaciones(nombre);
CREATE INDEX IF NOT EXISTS idx_esco_occ_isco ON esco_ocupaciones(codigo_isco);

CREATE TABLE IF NOT EXISTS esco_habilidades (
    id SERIAL PRIMARY KEY,
    uri TEXT,
    nombre TEXT,
    nombres_alternativos TEXT,
    nombres_ocultos TEXT,
    tipo_habilidad TEXT,
    nivel_reutilizacion TEXT,
    definicion TEXT,
    nota_alcance TEXT,
    esquema TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esco_skill_nombre ON esco_habilidades(nombre);

CREATE TABLE IF NOT EXISTS esco_ocupacion_habilidades (
    id SERIAL PRIMARY KEY,
    ocupacion_uri TEXT,
    ocupacion_nombre TEXT,
    tipo_relacion TEXT,
    tipo_habilidad TEXT,
    habilidad_uri TEXT,
    habilidad_nombre TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esco_rel_occ ON esco_ocupacion_habilidades(ocupacion_nombre);
CREATE INDEX IF NOT EXISTS idx_esco_rel_skill ON esco_ocupacion_habilidades(habilidad_nombre);

CREATE TABLE IF NOT EXISTS esco_skill_relations (
    id SERIAL PRIMARY KEY,
    habilidad_origen_uri TEXT,
    tipo_origen TEXT,
    tipo_relacion TEXT,
    tipo_relacionada TEXT,
    habilidad_relacionada_uri TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS esco_habilidades_verdes (
    id SERIAL PRIMARY KEY,
    uri TEXT,
    nombre TEXT,
    definicion TEXT,
    tipo_habilidad TEXT,
    nivel_reutilizacion TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS esco_habilidades_digitales (
    id SERIAL PRIMARY KEY,
    uri TEXT,
    nombre TEXT,
    definicion TEXT,
    tipo_habilidad TEXT,
    nivel_reutilizacion TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS esco_green_share_ocupaciones (
    id SERIAL PRIMARY KEY,
    uri TEXT,
    codigo TEXT,
    nombre TEXT,
    indice_verdor NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EMICRON - Micronegocios (2021-2024)
-- ============================================================================

CREATE TABLE IF NOT EXISTS emicron_resumen_nacional (
    id SERIAL PRIMARY KEY,
    ano INTEGER,
    total_micronegocios INTEGER,
    pct_usa_internet NUMERIC,
    pct_tiene_credito NUMERIC,
    empleo_generado INTEGER,
    ingreso_promedio_mensual NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emicron_por_sector (
    id SERIAL PRIMARY KEY,
    ciiu NUMERIC,
    micronegocios NUMERIC,
    ano INTEGER,
    ingreso_promedio NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emicron_emprendimiento (
    id SERIAL PRIMARY KEY,
    codigo_motivo NUMERIC,
    micronegocios NUMERIC,
    ano INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emicron_por_departamento (
    id SERIAL PRIMARY KEY,
    dpto INTEGER,
    micronegocios NUMERIC,
    ano INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emicron_inclusion_financiera (
    id SERIAL PRIMARY KEY,
    ciiu NUMERIC,
    pct_credito NUMERIC,
    ano INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- PREDICCIONES - Chronos T5 (JSON)
-- ============================================================================

CREATE TABLE IF NOT EXISTS predicciones_geih (
    id SERIAL PRIMARY KEY,
    tipo TEXT,
    periodo TEXT,
    mediana NUMERIC,
    p10 NUMERIC,
    p90 NUMERIC,
    horizonte TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predicciones_mundiales (
    id SERIAL PRIMARY KEY,
    tipo TEXT,
    categoria TEXT,
    datos JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deshabilitar RLS para desarrollo
ALTER TABLE geih_resumen_nacional DISABLE ROW LEVEL SECURITY;
ALTER TABLE geih_desempleo_mensual DISABLE ROW LEVEL SECURITY;
ALTER TABLE geih_empleo_sector_mensual DISABLE ROW LEVEL SECURITY;
ALTER TABLE geih_informalidad_mensual DISABLE ROW LEVEL SECURITY;
ALTER TABLE geih_empleo_depto_sector DISABLE ROW LEVEL SECURITY;
ALTER TABLE geih_salario_ocupacion DISABLE ROW LEVEL SECURITY;
ALTER TABLE ole_ingresos_por_programa DISABLE ROW LEVEL SECURITY;
ALTER TABLE ole_ingresos_por_area DISABLE ROW LEVEL SECURITY;
ALTER TABLE ole_ingresos_por_nivel DISABLE ROW LEVEL SECURITY;
ALTER TABLE ole_ingresos_por_ies DISABLE ROW LEVEL SECURITY;
ALTER TABLE ole_graduados_por_anio DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_ocupaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_habilidades DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_ocupacion_habilidades DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_skill_relations DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_habilidades_verdes DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_habilidades_digitales DISABLE ROW LEVEL SECURITY;
ALTER TABLE esco_green_share_ocupaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE emicron_resumen_nacional DISABLE ROW LEVEL SECURITY;
ALTER TABLE emicron_por_sector DISABLE ROW LEVEL SECURITY;
ALTER TABLE emicron_emprendimiento DISABLE ROW LEVEL SECURITY;
ALTER TABLE emicron_por_departamento DISABLE ROW LEVEL SECURITY;
ALTER TABLE emicron_inclusion_financiera DISABLE ROW LEVEL SECURITY;
ALTER TABLE predicciones_geih DISABLE ROW LEVEL SECURITY;
ALTER TABLE predicciones_mundiales DISABLE ROW LEVEL SECURITY;