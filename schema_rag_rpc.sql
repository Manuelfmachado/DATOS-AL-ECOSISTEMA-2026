-- schema_rag_rpc.sql
-- Funciones PostgreSQL para busqueda por similitud con embeddings Gemma 300 (768d).
-- Ejecutar en SQL Editor de Supabase si ya tienes las tablas de embeddings creadas.

-- Version con embedding pre-calculado: devuelve resultados ordenados por cosine similarity
-- categoria_filter: pasar NULL o string vacio para no filtrar; pasar un valor para filtrar
CREATE OR REPLACE FUNCTION buscar_embeddings_vector(
    consulta_embedding VECTOR(768),
    nombre_tabla TEXT,
    limite_resultados INTEGER DEFAULT 5,
    categoria_filter TEXT DEFAULT NULL
)
RETURNS TABLE(
    id INTEGER,
    texto TEXT,
    metadata JSONB,
    similitud NUMERIC
) LANGUAGE plpgsql AS $$
DECLARE
    cat_filter TEXT := NULLIF(categoria_filter, '');
BEGIN
    IF nombre_tabla = 'embeddings_skills' THEN
        RETURN QUERY
        SELECT e.id, e.texto, e.metadata,
               (1 - (e.embedding <=> consulta_embedding))::NUMERIC AS similitud
        FROM embeddings_skills e
        WHERE cat_filter IS NULL OR e.metadata->>'category' = cat_filter
        ORDER BY e.embedding <=> consulta_embedding
        LIMIT limite_resultados;
    ELSIF nombre_tabla = 'embeddings_programas' THEN
        RETURN QUERY
        SELECT e.id, e.texto, e.metadata,
               (1 - (e.embedding <=> consulta_embedding))::NUMERIC AS similitud
        FROM embeddings_programas e
        WHERE cat_filter IS NULL OR e.metadata->>'category' = cat_filter
        ORDER BY e.embedding <=> consulta_embedding
        LIMIT limite_resultados;
    ELSIF nombre_tabla = 'embeddings_guias' THEN
        RETURN QUERY
        SELECT e.id, e.texto, e.metadata,
               (1 - (e.embedding <=> consulta_embedding))::NUMERIC AS similitud
        FROM embeddings_guias e
        WHERE cat_filter IS NULL OR e.metadata->>'category' = cat_filter
        ORDER BY e.embedding <=> consulta_embedding
        LIMIT limite_resultados;
    ELSE
        RAISE EXCEPTION 'Tabla no soportada: %', nombre_tabla;
    END IF;
END;
$$;
