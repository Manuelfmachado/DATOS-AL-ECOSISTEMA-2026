-- ============================================================================
-- CORRECCIÓN DE ESQUEMAS Y CREACIÓN DE TABLAS FALTANTES
-- Ejecutar en SQL Editor de Supabase
-- ============================================================================

-- 1. CORREGIR geih_salario_ocupacion (cambiar INTEGER a NUMERIC)
ALTER TABLE geih_salario_ocupacion ALTER COLUMN oficio_c8 TYPE NUMERIC;
ALTER TABLE geih_salario_ocupacion ALTER COLUMN ocupados_muestra TYPE NUMERIC;

-- 2. AGREGAR COLUMNAS FALTANTES a geih_resumen_departamento
ALTER TABLE geih_resumen_departamento ADD COLUMN IF NOT EXISTS mujeres_cabeza_hogar_pct NUMERIC;
ALTER TABLE geih_resumen_departamento ADD COLUMN IF NOT EXISTS pct_educacion_superior NUMERIC;
ALTER TABLE geih_resumen_departamento ADD COLUMN IF NOT EXISTS nivel_educativo_etiqueta TEXT;

-- 3. CREAR geih_extras_departamento
CREATE TABLE IF NOT EXISTS geih_extras_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    mujeres_cabeza_hogar_pct NUMERIC,
    total_jefes_hogar NUMERIC,
    pct_educacion_superior NUMERIC,
    nivel_educativo_categoria TEXT,
    nivel_educativo_etiqueta TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE geih_extras_departamento DISABLE ROW LEVEL SECURITY;

-- 4. CREAR worldbank_colombia
CREATE TABLE IF NOT EXISTS worldbank_colombia (
    id SERIAL PRIMARY KEY,
    indicator_code TEXT,
    indicator_name TEXT,
    year INTEGER,
    value NUMERIC,
    country TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE worldbank_colombia DISABLE ROW LEVEL SECURITY;

-- 5. VACIAR tablas que tuvieron errores para poder recargarlas
TRUNCATE TABLE geih_salario_ocupacion RESTART IDENTITY;
TRUNCATE TABLE geih_resumen_departamento RESTART IDENTITY;
