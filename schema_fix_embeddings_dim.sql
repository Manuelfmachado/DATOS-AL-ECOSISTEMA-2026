-- schema_fix_embeddings_dim.sql
-- Actualiza las tablas de embeddings de 384 a 768 dimensiones para usar Gemma 300 via DeepInfra.
-- Ejecutar en SQL Editor de Supabase si ya creaste las tablas con VECTOR(384).
-- ADVERTENCIA: trunca los datos existentes porque los embeddings 384d no son compatibles con 768d.

TRUNCATE TABLE embeddings_skills;
TRUNCATE TABLE embeddings_programas;
TRUNCATE TABLE embeddings_guias;

ALTER TABLE embeddings_skills ALTER COLUMN embedding TYPE VECTOR(768);
ALTER TABLE embeddings_programas ALTER COLUMN embedding TYPE VECTOR(768);
ALTER TABLE embeddings_guias ALTER COLUMN embedding TYPE VECTOR(768);

-- Recrear indices ivfflat (recomendado tras cambiar tipo de vector)
DROP INDEX IF EXISTS idx_embeddings_skills;
DROP INDEX IF EXISTS idx_embeddings_programas;
DROP INDEX IF EXISTS idx_embeddings_guias;

CREATE INDEX IF NOT EXISTS idx_embeddings_skills 
ON embeddings_skills USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_embeddings_programas 
ON embeddings_programas USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_embeddings_guias 
ON embeddings_guias USING ivfflat (embedding vector_cosine_ops);
