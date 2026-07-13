-- Schema inicial para ENIL en Supabase
-- Ejecutar en SQL Editor de Supabase

-- Activar extensión para embeddings vectoriales
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- DATOS PROCESADOS DEL ETL
-- ============================================================================

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

CREATE TABLE IF NOT EXISTS geih_desempleo_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    no_ocupados INTEGER,
    mujeres_pct NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pila_resumen_sector (
    id SERIAL PRIMARY KEY,
    actividad_economica TEXT,
    total_cotizantes NUMERIC,
    total_cotizaciones NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS pila_resumen_tipo (
    id SERIAL PRIMARY KEY,
    tipo_cotizante TEXT,
    total_cotizantes NUMERIC,
    total_cotizaciones NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rues_resumen_camara_ciiu (
    id SERIAL PRIMARY KEY,
    camara_comercio TEXT,
    ciiu2 TEXT,
    empresas_activas INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rues_top_sectores_nacional (
    id SERIAL PRIMARY KEY,
    ciiu2 TEXT,
    empresas_activas INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rues_empresas_nuevas (
    id SERIAL PRIMARY KEY,
    anio_matricula INTEGER,
    ciiu2 TEXT,
    empresas_nuevas INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS snies_programas_matriculados (
    id SERIAL PRIMARY KEY,
    institucion TEXT,
    programa TEXT,
    departamento TEXT,
    nucleo_conocimiento TEXT,
    matriculados NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snies_programa_departamento 
ON snies_programas_matriculados(departamento);

CREATE INDEX IF NOT EXISTS idx_snies_programa_institucion 
ON snies_programas_matriculados(institucion);

CREATE TABLE IF NOT EXISTS snies_matriculados_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    matriculados NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sena_programas_activos (
    id SERIAL PRIMARY KEY,
    programa TEXT,
    departamento TEXT,
    area_desempeno TEXT,
    tipo_certificado TEXT,
    escolaridad TEXT,
    costo NUMERIC,
    duracion_horas NUMERIC,
    institucion TEXT,
    estado_programa TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sena_area 
ON sena_programas_activos(area_desempeno);

CREATE TABLE IF NOT EXISTS saberpro_resumen_programas (
    id SERIAL PRIMARY KEY,
    institucion TEXT,
    programa TEXT,
    departamento TEXT,
    puntaje_razona_cuantitat NUMERIC,
    puntaje_comunica_escrita NUMERIC,
    puntaje_lectura_critica NUMERIC,
    puntaje_ingles NUMERIC,
    puntaje_competencia_ciudada NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- NUEVOS DATASETS: SPE, OLE, DNP
-- ============================================================================

CREATE TABLE IF NOT EXISTS spe_ape_inscritos_ocupacion (
    id SERIAL PRIMARY KEY,
    id_ocupacion INTEGER,
    ocupacion TEXT,
    nivel TEXT,
    inscritos_2019 NUMERIC,
    inscritos_2020 NUMERIC,
    participacion_2019 NUMERIC,
    participacion_2020 NUMERIC,
    variacion_pct NUMERIC,
    contribucion_variacion NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spe_ocupacion_nivel 
ON spe_ape_inscritos_ocupacion(nivel);

CREATE TABLE IF NOT EXISTS spe_ape_inscritos_nivel (
    id SERIAL PRIMARY KEY,
    nivel TEXT,
    total_inscritos_2019 NUMERIC,
    total_inscritos_2020 NUMERIC,
    ocupaciones INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ole_etdh_programas_activos (
    id SERIAL PRIMARY KEY,
    programa TEXT,
    institucion TEXT,
    departamento TEXT,
    municipio TEXT,
    area_desempeno TEXT,
    tipo_certificado TEXT,
    escolaridad TEXT,
    costo NUMERIC,
    duracion_horas NUMERIC,
    estado_programa TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ole_area 
ON ole_etdh_programas_activos(area_desempeno);

CREATE INDEX IF NOT EXISTS idx_ole_departamento 
ON ole_etdh_programas_activos(departamento);

CREATE TABLE IF NOT EXISTS ole_etdh_resumen_departamento_area (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    area_desempeno TEXT,
    programas INTEGER,
    duracion_promedio_horas NUMERIC,
    costo_promedio NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dnp_medicion_desempeno_municipal (
    id SERIAL PRIMARY KEY,
    codigo_unico TEXT,
    indicador TEXT,
    codigo_categoria TEXT,
    codigo_subcategoria TEXT,
    codigo_variable TEXT,
    codigo_departamento TEXT,
    departamento TEXT,
    codigo_entidad TEXT,
    entidad TEXT,
    dato NUMERIC,
    etiqueta TEXT,
    anio INTEGER,
    mes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dnp_desempeno_indicador 
ON dnp_medicion_desempeno_municipal(indicador);

CREATE INDEX IF NOT EXISTS idx_dnp_desempeno_entidad 
ON dnp_medicion_desempeno_municipal(entidad);

CREATE TABLE IF NOT EXISTS dnp_medicion_desempeno_ultimo (
    id SERIAL PRIMARY KEY,
    codigo_unico TEXT,
    indicador TEXT,
    codigo_categoria TEXT,
    codigo_subcategoria TEXT,
    codigo_variable TEXT,
    codigo_departamento TEXT,
    departamento TEXT,
    codigo_entidad TEXT,
    entidad TEXT,
    dato NUMERIC,
    etiqueta TEXT,
    anio INTEGER,
    mes INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dnp_desempeno_departamento (
    id SERIAL PRIMARY KEY,
    departamento TEXT,
    promedio_desempeno NUMERIC,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- EMBEDDINGS VECTORIALES (para función 3, 4, 5)
-- ============================================================================

CREATE TABLE IF NOT EXISTS embeddings_skills (
    id SERIAL PRIMARY KEY,
    texto TEXT,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_skills 
ON embeddings_skills USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS embeddings_programas (
    id SERIAL PRIMARY KEY,
    texto TEXT,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_programas 
ON embeddings_programas USING ivfflat (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS embeddings_guias (
    id SERIAL PRIMARY KEY,
    texto TEXT,
    embedding VECTOR(768),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_guias 
ON embeddings_guias USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- DATOS DE LA APLICACIÓN
-- ============================================================================

CREATE TABLE IF NOT EXISTS perfiles_usuarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    tipo_usuario TEXT CHECK (tipo_usuario IN ('estudiante', 'profesional', 'academia', 'empresa')),
    datos JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS simulaciones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES perfiles_usuarios(id),
    carrera TEXT,
    departamento TEXT,
    resultados JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS entrevistas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES perfiles_usuarios(id),
    vacante_texto TEXT,
    preguntas_respuestas JSONB,
    score NUMERIC,
    feedback TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chat_sesiones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID REFERENCES perfiles_usuarios(id),
    mensajes JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Políticas RLS básicas (deshabilitadas para desarrollo inicial)
ALTER TABLE perfiles_usuarios DISABLE ROW LEVEL SECURITY;
ALTER TABLE simulaciones DISABLE ROW LEVEL SECURITY;
ALTER TABLE entrevistas DISABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sesiones DISABLE ROW LEVEL SECURITY;

-- ============================================================================
-- FUNCIONES PARA BUSQUEDA POR SIMILITUD (RAG)
-- ============================================================================

-- Busca chunks similares en cualquiera de las tablas de embeddings.
-- Uso: SELECT * FROM buscar_embeddings('texto consulta', 'embeddings_guias', 5);
CREATE OR REPLACE FUNCTION buscar_embeddings(
    consulta_texto TEXT,
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
    consulta_embedding VECTOR(768);
BEGIN
    -- La consulta se ejecuta desde Python; aqui recibimos el embedding ya calculado.
    -- Esta funcion es un helper para filtrar por categoria y ordenar por similitud.
    RAISE EXCEPTION 'Funcion deprecada: calcular embedding desde Python y usar operator <=> o <#> directamente.';
END;
$$;

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
