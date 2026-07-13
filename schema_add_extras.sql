-- Agregar columnas de mujeres cabeza de hogar y nivel educativo
-- a la tabla geih_resumen_departamento

ALTER TABLE geih_resumen_departamento 
  ADD COLUMN IF NOT EXISTS mujeres_cabeza_hogar_pct DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS nivel_educativo_prom DOUBLE PRECISION;