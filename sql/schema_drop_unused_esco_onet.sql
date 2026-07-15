-- ============================================================================
-- Reclamar espacio fisico tras vaciar tablas ESCO/O*NET no usadas.
--
-- Las tablas ya fueron vaciadas via REST (DELETE), pero Postgres NO libera
-- espacio en disco automaticamente tras un DELETE; solo marca los bloques como
-- reutilizables. Para reducir el Disk Size en Supabase hay que:
--   1. DROP las tablas vacias (libera espacio de tabla + indices).
--   2. VACUUM FULL para reclamar espacio fisico.
--
-- Ejecutar en Supabase SQL Editor.
-- ============================================================================

-- 1. Eliminar las 4 tablas vacias (no las usa ningun endpoint del backend).
--    DROP TABLE es DDL: libera el espacio fisico INMEDIATAMENTE (no necesita VACUUM).
DROP TABLE IF EXISTS esco_occupation_skills;
DROP TABLE IF EXISTS onet_occupation_skills;
DROP TABLE IF EXISTS esco_skill_relations;
DROP TABLE IF EXISTS esco_habilidades;

-- 2. Verificar el resultado
SELECT
    schemaname AS esquema,
    relname   AS tabla,
    pg_size_pretty(pg_total_relation_size(relid)) AS tamano_total
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 15;

-- Tamano total de la base de datos
SELECT pg_size_pretty(pg_database_size(current_database())) AS tamano_bd;