-- Tablas faltantes en Supabase
-- Ejecutar en SQL Editor de Supabase

-- GEIH extras por departamento
CREATE TABLE IF NOT EXISTS geih_extras_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    indicador TEXT,
    dato NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE geih_extras_departamento DISABLE ROW LEVEL SECURITY;

-- World Bank Colombia
CREATE TABLE IF NOT EXISTS worldbank_colombia (
    id SERIAL PRIMARY KEY,
    indicador TEXT,
    anio INTEGER,
    valor NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE worldbank_colombia DISABLE ROW LEVEL SECURITY;

-- Corregir tipo de columna en geih_salario_ocupacion si es necesario
-- El CSV tiene valores como "2.0" que no pueden ser integer
DO $$ 
BEGIN
    -- Verificar si la columna oficio_c8 es integer y cambiarla a numeric si es necesario
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'geih_salario_ocupacion' 
        AND column_name = 'oficio_c8' 
        AND data_type = 'integer'
    ) THEN
        ALTER TABLE geih_salario_ocupacion ALTER COLUMN oficio_c8 TYPE NUMERIC;
    END IF;
    
    -- Verificar si la columna ocupados_muestra es integer y cambiarla a numeric si es necesario
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'geih_salario_ocupacion' 
        AND column_name = 'ocupados_muestra' 
        AND data_type = 'integer'
    ) THEN
        ALTER TABLE geih_salario_ocupacion ALTER COLUMN ocupados_muestra TYPE NUMERIC;
    END IF;
END $$;

-- Verificar y crear geih_resumen_departamento si no existe con todas las columnas
CREATE TABLE IF NOT EXISTS geih_resumen_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    ocupados INTEGER,
    ingreso_promedio NUMERIC,
    ingreso_mediano NUMERIC,
    tasa_formalidad NUMERIC,
    mujeres_pct NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

ALTER TABLE geih_resumen_departamento DISABLE ROW LEVEL SECURITY;
