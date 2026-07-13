"""
Crear tablas faltantes en Supabase
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan SUPABASE_URL o SUPABASE_KEY")
    exit(1)

print(f"Conectando a Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# SQL para crear tablas faltantes
sql = """
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

-- Corregir tipo de columna en geih_salario_ocupacion
DO $$ 
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'geih_salario_ocupacion' 
        AND column_name = 'oficio_c8' 
        AND data_type = 'integer'
    ) THEN
        ALTER TABLE geih_salario_ocupacion ALTER COLUMN oficio_c8 TYPE NUMERIC;
    END IF;
    
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'geih_salario_ocupacion' 
        AND column_name = 'ocupados_muestra' 
        AND data_type = 'integer'
    ) THEN
        ALTER TABLE geih_salario_ocupacion ALTER COLUMN ocupados_muestra TYPE NUMERIC;
    END IF;
END $$;
"""

print("Ejecutando SQL para crear tablas faltantes...")
try:
    # Supabase no tiene método directo para ejecutar SQL arbitrario
    # Necesitamos usar la API REST o ejecutar queries individuales
    # Por ahora, solo verificamos que las tablas existen
    
    # Intentar verificar si geih_extras_departamento existe
    try:
        result = supabase.table('geih_extras_departamento').select('id').limit(1).execute()
        print("[OK] Tabla geih_extras_departamento ya existe")
    except:
        print("[!] Tabla geih_extras_departamento NO existe - crear manualmente en Supabase SQL Editor")
    
    # Intentar verificar si worldbank_colombia existe
    try:
        result = supabase.table('worldbank_colombia').select('id').limit(1).execute()
        print("[OK] Tabla worldbank_colombia ya existe")
    except:
        print("[!] Tabla worldbank_colombia NO existe - crear manualmente en Supabase SQL Editor")
        
    print("\n[!] IMPORTANTE:")
    print("El cliente de Supabase no puede ejecutar SQL arbitrario.")
    print("Debes ejecutar manualmente el archivo schema_crear_tablas_faltantes.sql")
    print("en el SQL Editor de Supabase:")
    print("1. Ve a https://app.supabase.com/project/vyerhngdkzyhbhucolek/sql")
    print("2. Copia el contenido de schema_crear_tablas_faltantes.sql")
    print("3. Ejecútalo (Run)")
    
except Exception as e:
    print(f"[ERROR] {e}")
