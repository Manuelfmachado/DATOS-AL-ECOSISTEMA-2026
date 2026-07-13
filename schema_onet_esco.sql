-- schema_onet_esco.sql
-- Tablas para O*NET y ESCO en ALBA

-- ============================================================================
-- O*NET
-- ============================================================================

CREATE TABLE IF NOT EXISTS onet_occupations (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_onet_occupations_code ON onet_occupations(onet_soc_code);

CREATE TABLE IF NOT EXISTS onet_skill_definitions (
    id SERIAL PRIMARY KEY,
    element_id TEXT UNIQUE NOT NULL,
    element_name TEXT NOT NULL,
    domain TEXT NOT NULL,  -- skill, knowledge, ability, software
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_onet_skill_element_id ON onet_skill_definitions(element_id);

CREATE TABLE IF NOT EXISTS onet_occupation_skills (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    element_id TEXT NOT NULL,
    element_name TEXT NOT NULL,
    domain TEXT NOT NULL,
    scale_id TEXT,
    data_value NUMERIC,
    is_essential BOOLEAN DEFAULT FALSE,
    is_software BOOLEAN DEFAULT FALSE,
    hot_technology TEXT,
    in_demand TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(onet_soc_code, element_id, domain, scale_id)
);

CREATE INDEX IF NOT EXISTS idx_onet_occ_skills_code ON onet_occupation_skills(onet_soc_code);
CREATE INDEX IF NOT EXISTS idx_onet_occ_skills_domain ON onet_occupation_skills(domain);

CREATE TABLE IF NOT EXISTS onet_related_occupations (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    related_onet_soc_code TEXT NOT NULL,
    relatedness_tier TEXT,
    related_index INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(onet_soc_code, related_onet_soc_code)
);

CREATE INDEX IF NOT EXISTS idx_onet_related_code ON onet_related_occupations(onet_soc_code);

CREATE TABLE IF NOT EXISTS onet_job_titles (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    job_title TEXT NOT NULL,
    short_title TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_onet_job_titles_code ON onet_job_titles(onet_soc_code);

CREATE TABLE IF NOT EXISTS onet_education (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    element_id TEXT NOT NULL,
    element_name TEXT NOT NULL,
    category INTEGER,
    data_value NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(onet_soc_code, element_id, category)
);

CREATE INDEX IF NOT EXISTS idx_onet_education_code ON onet_education(onet_soc_code);

-- ============================================================================
-- ESCO
-- ============================================================================

CREATE TABLE IF NOT EXISTS esco_occupations (
    id SERIAL PRIMARY KEY,
    uri TEXT UNIQUE NOT NULL,
    code TEXT,
    title TEXT NOT NULL,
    title_es TEXT,
    description TEXT,
    preferred_label JSONB,
    alternative_label JSONB,
    broader_isco_group TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esco_occupations_uri ON esco_occupations(uri);
CREATE INDEX IF NOT EXISTS idx_esco_occupations_code ON esco_occupations(code);

CREATE TABLE IF NOT EXISTS esco_skills (
    id SERIAL PRIMARY KEY,
    uri TEXT UNIQUE NOT NULL,
    skill_type TEXT,  -- skillCompetence, knowledgeSkill, languageSkill, etc.
    title TEXT NOT NULL,
    title_es TEXT,
    description TEXT,
    preferred_label JSONB,
    alternative_label JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_esco_skills_uri ON esco_skills(uri);

CREATE TABLE IF NOT EXISTS esco_occupation_skills (
    id SERIAL PRIMARY KEY,
    esco_uri TEXT NOT NULL REFERENCES esco_occupations(uri) ON DELETE CASCADE,
    esco_skill_uri TEXT NOT NULL REFERENCES esco_skills(uri) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,  -- essential, optional
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(esco_uri, esco_skill_uri, relation_type)
);

CREATE INDEX IF NOT EXISTS idx_esco_occ_skills_uri ON esco_occupation_skills(esco_uri);
CREATE INDEX IF NOT EXISTS idx_esco_occ_skills_skill ON esco_occupation_skills(esco_skill_uri);

-- Mapeo de ocupaciones O*NET a ocupaciones SPE SENA (Colombia)
CREATE TABLE IF NOT EXISTS onet_spe_mapping (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    spe_ocupacion TEXT NOT NULL,
    similarity_score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(onet_soc_code, spe_ocupacion)
);

CREATE INDEX IF NOT EXISTS idx_onet_spe_mapping_code ON onet_spe_mapping(onet_soc_code);
CREATE INDEX IF NOT EXISTS idx_onet_spe_mapping_occ ON onet_spe_mapping(spe_ocupacion);

-- Mapeo de ocupaciones ESCO a ocupaciones SPE SENA (Colombia)
CREATE TABLE IF NOT EXISTS esco_spe_mapping (
    id SERIAL PRIMARY KEY,
    esco_uri TEXT NOT NULL REFERENCES esco_occupations(uri) ON DELETE CASCADE,
    spe_ocupacion TEXT NOT NULL,
    similarity_score NUMERIC,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(esco_uri, spe_ocupacion)
);

CREATE INDEX IF NOT EXISTS idx_esco_spe_mapping_uri ON esco_spe_mapping(esco_uri);
CREATE INDEX IF NOT EXISTS idx_esco_spe_mapping_occ ON esco_spe_mapping(spe_ocupacion);

-- ============================================================================
-- Embeddings para RAG
-- ============================================================================

CREATE TABLE IF NOT EXISTS embeddings_onet_occupations (
    id SERIAL PRIMARY KEY,
    onet_soc_code TEXT NOT NULL REFERENCES onet_occupations(onet_soc_code) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(onet_soc_code)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_onet_code ON embeddings_onet_occupations(onet_soc_code);

CREATE TABLE IF NOT EXISTS embeddings_esco_occupations (
    id SERIAL PRIMARY KEY,
    esco_uri TEXT NOT NULL REFERENCES esco_occupations(uri) ON DELETE CASCADE,
    texto TEXT NOT NULL,
    embedding VECTOR(768),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(esco_uri)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_esco_uri ON embeddings_esco_occupations(esco_uri);
