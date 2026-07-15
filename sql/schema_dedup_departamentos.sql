-- ============================================================================
-- Limpieza de filas duplicadas en tablas departamentales.
--
-- Las tablas se cargaron multiples veces con INSERT (sin TRUNCATE ni upsert),
-- acumulando ~6 copias de cada uno de los 33 departamentos (198 filas).
-- Este script:
--   1. Elimina duplicados conservando la fila con menor id (mas antigua).
--   2. Anade restricciones UNIQUE sobre la columna "departamento" para que
--      futuras cargas no puedan reintroducir duplicados.
--
-- Ejecutar en Supabase SQL Editor.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. geih_resumen_departamento
-- ----------------------------------------------------------------------------
DELETE FROM geih_resumen_departamento
WHERE id NOT IN (
    SELECT MIN(id)
    FROM geih_resumen_departamento
    GROUP BY departamento
);

-- Limpieza de cualquier fila con departamento NULL
DELETE FROM geih_resumen_departamento WHERE departamento IS NULL;

-- Restriccion UNIQUE (idempotente)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_geih_resumen_departamento'
    ) THEN
        ALTER TABLE geih_resumen_departamento
        ADD CONSTRAINT uq_geih_resumen_departamento UNIQUE (departamento);
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 2. geih_desempleo_departamento
-- ----------------------------------------------------------------------------
DELETE FROM geih_desempleo_departamento
WHERE id NOT IN (
    SELECT MIN(id)
    FROM geih_desempleo_departamento
    GROUP BY departamento
);

DELETE FROM geih_desempleo_departamento WHERE departamento IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_geih_desempleo_departamento'
    ) THEN
        ALTER TABLE geih_desempleo_departamento
        ADD CONSTRAINT uq_geih_desempleo_departamento UNIQUE (departamento);
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 3. snies_matriculados_departamento
-- ----------------------------------------------------------------------------
DELETE FROM snies_matriculados_departamento
WHERE id NOT IN (
    SELECT MIN(id)
    FROM snies_matriculados_departamento
    GROUP BY departamento
);

DELETE FROM snies_matriculados_departamento WHERE departamento IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_snies_matriculados_departamento'
    ) THEN
        ALTER TABLE snies_matriculados_departamento
        ADD CONSTRAINT uq_snies_matriculados_departamento UNIQUE (departamento);
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- 4. dnp_desempeno_departamento
-- ----------------------------------------------------------------------------
DELETE FROM dnp_desempeno_departamento
WHERE id NOT IN (
    SELECT MIN(id)
    FROM dnp_desempeno_departamento
    GROUP BY departamento
);

DELETE FROM dnp_desempeno_departamento WHERE departamento IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_dnp_desempeno_departamento'
    ) THEN
        ALTER TABLE dnp_desempeno_departamento
        ADD CONSTRAINT uq_dnp_desempeno_departamento UNIQUE (departamento);
    END IF;
END $$;

-- ----------------------------------------------------------------------------
-- Verificacion: cada tabla debe quedar con exactamente 33 departamentos.
-- ----------------------------------------------------------------------------
SELECT 'geih_resumen_departamento' AS tabla,
       COUNT(*) AS filas,
       COUNT(DISTINCT departamento) AS unicos
FROM geih_resumen_departamento
UNION ALL
SELECT 'geih_desempleo_departamento', COUNT(*), COUNT(DISTINCT departamento)
FROM geih_desempleo_departamento
UNION ALL
SELECT 'snies_matriculados_departamento', COUNT(*), COUNT(DISTINCT departamento)
FROM snies_matriculados_departamento
UNION ALL
SELECT 'dnp_desempeno_departamento', COUNT(*), COUNT(DISTINCT departamento)
FROM dnp_desempeno_departamento;