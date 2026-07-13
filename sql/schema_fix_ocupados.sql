-- Corregir geih_resumen_departamento: cambiar INTEGER a NUMERIC
ALTER TABLE geih_resumen_departamento ALTER COLUMN ocupados TYPE NUMERIC;

-- Vaciar para recargar
TRUNCATE TABLE geih_resumen_departamento RESTART IDENTITY;
