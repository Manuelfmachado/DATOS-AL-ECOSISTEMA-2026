"""
Carga los datos procesados del ETL a Supabase.
Requiere archivo .env con SUPABASE_URL y SUPABASE_KEY.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

ROOT = Path.cwd()
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan SUPABASE_URL o SUPABASE_KEY en archivo .env")
    print("1. Copiá .env.example a .env")
    print("2. Completá con tus credenciales de Supabase (Project Settings → API → anon public)")
    exit(1)

print(f"Conectando a Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def csv_to_records(path: Path, allowed_columns=None):
    """Lee CSV y devuelve lista de diccionarios, limpiando NaN/Inf."""
    if not path.exists():
        print(f"  [SKIP] No existe {path}")
        return []
    df = pd.read_csv(path, encoding='utf-8')
    
    # Reemplazar columnas problemáticas
    df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
    
    # Filtrar solo columnas permitidas si se especifican
    if allowed_columns:
        cols_to_keep = [c for c in df.columns if c in allowed_columns]
        df = df[cols_to_keep]
    
    # Limpiar NaN, Inf, -Inf → None (agresivo)
    df = df.where(pd.notna(df), None)
    df = df.replace([np.inf, -np.inf], None)
    
    records = df.to_dict('records')
    
    # Post-procesar: reemplazar float('nan') y float('inf') con None
    import math
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    rec[k] = None
    
    print(f"  [OK] {len(records)} registros listos")
    return records


def upload_table(table_name: str, records: list, batch_size=500):
    """Sube registros a Supabase en lotes."""
    if not records:
        return
    
    print(f"\n[>] Subiendo {table_name}...")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            response = supabase.table(table_name).insert(batch).execute()
            print(f"  [OK] Lote {i//batch_size + 1}: {len(batch)} registros")
        except Exception as e:
            print(f"  [ERROR] Lote {i//batch_size + 1}: {e}")
            print(f"  Intentando con lote más pequeño...")
            # Fallback: subir de a 50
            for j in range(0, len(batch), 50):
                try:
                    supabase.table(table_name).insert(batch[j:j+50]).execute()
                except Exception as e2:
                    print(f"    [ERROR FATAL] {e2}")
                    break


def main():
    # Mapeo archivo CSV → tabla Supabase + columnas permitidas
    tables = {
        'geih_resumen_departamento.csv': ('geih_resumen_departamento', None),
        'geih_desempleo_departamento.csv': ('geih_desempleo_departamento', None),
        'pila_resumen_sector.csv': ('pila_resumen_sector', None),
        'pila_resumen_tipo.csv': ('pila_resumen_tipo', None),
        'rues_resumen_camara_ciiu.csv': ('rues_resumen_camara_ciiu', None),
        'rues_top_sectores_nacional.csv': ('rues_top_sectores_nacional', None),
        'rues_empresas_nuevas.csv': ('rues_empresas_nuevas', None),
        'snies_programas_matriculados.csv': ('snies_programas_matriculados', None),
        'snies_matriculados_departamento.csv': ('snies_matriculados_departamento', None),
        'sena_programas_activos.csv': ('sena_programas_activos', [
            'programa', 'departamento', 'area_desempeno', 'tipo_certificado',
            'escolaridad', 'costo', 'duracion_horas', 'estado_programa', 'institucion'
        ]),
        'saberpro_resumen_programas.csv': ('saberpro_resumen_programas', [
            'institucion', 'programa', 'departamento',
            'mod_razona_cuantitat_punt', 'mod_comuni_escrita_punt',
            'mod_lectura_critica_punt', 'mod_ingles_punt', 'mod_competen_ciudada_punt'
        ]),
        'spe_ape_inscritos_ocupacion.csv': ('spe_ape_inscritos_ocupacion', None),
        'spe_ape_inscritos_nivel.csv': ('spe_ape_inscritos_nivel', None),
        'ole_etdh_programas_activos.csv': ('ole_etdh_programas_activos', [
            'programa', 'institucion', 'departamento', 'municipio',
            'area_desempeno', 'tipo_certificado', 'escolaridad',
            'costo', 'duracion_horas', 'estado_programa'
        ]),
        'ole_etdh_resumen_departamento_area.csv': ('ole_etdh_resumen_departamento_area', None),
        'dnp_medicion_desempeno_municipal.csv': ('dnp_medicion_desempeno_municipal', None),
        'dnp_medicion_desempeno_ultimo.csv': ('dnp_medicion_desempeno_ultimo', None),
        'dnp_desempeno_departamento.csv': ('dnp_desempeno_departamento', None),
    }
    
    print("=" * 70)
    print("CARGA DE DATOS A SUPABASE")
    print("=" * 70)
    
    # Verificar conexión y tablas
    print("\n[!] IMPORTANTE:")
    print("Las tablas deben estar creadas en Supabase antes de cargar datos.")
    print("Si no las creaste todavía:")
    print("1. Andá al SQL Editor de Supabase")
    print("2. Copiá el contenido de schema_supabase.sql")
    print("3. Ejecutalo (Run)")
    print("4. Luego ejecutá de nuevo este script")
    print()
    
    # Chequear primera tabla
    try:
        response = supabase.table('geih_resumen_departamento').select('id', count='exact').limit(1).execute()
        print(f"[OK] Conexión a Supabase verificada. Tablas existen.")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar o las tablas no existen: {e}")
        print("[ERROR] Creá las tablas con schema_supabase.sql primero.")
        return
    
    for csv_file, (table_name, allowed_cols) in tables.items():
        path = PROCESSED / csv_file
        records = csv_to_records(path, allowed_cols)
        upload_table(table_name, records)
    
    print("\n" + "=" * 70)
    print("CARGA FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
