"""
Cargar solo las 4 tablas que fallaron en la carga anterior.
EJECUTAR DESPUÉS de correr schema_correcciones.sql en Supabase SQL Editor.
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
    # Solo las 4 tablas que fallaron
    tables = {
        'geih_resumen_departamento.csv': ('geih_resumen_departamento', [
            'departamento', 'ocupados', 'ingreso_promedio', 'ingreso_mediano',
            'tasa_formalidad', 'mujeres_pct', 'mujeres_cabeza_hogar_pct',
            'pct_educacion_superior', 'nivel_educativo_etiqueta'
        ]),
        'geih_salario_ocupacion.csv': ('geih_salario_ocupacion', [
            'oficio_c8', 'salario_promedio', 'salario_mediano',
            'empleo_total', 'ocupados_muestra', 'periodo'
        ]),
        'geih_extras_departamento.csv': ('geih_extras_departamento', [
            'departamento', 'mujeres_cabeza_hogar_pct', 'total_jefes_hogar',
            'pct_educacion_superior', 'nivel_educativo_categoria', 'nivel_educativo_etiqueta'
        ]),
        'worldbank_colombia.csv': ('worldbank_colombia', [
            'indicator_code', 'indicator_name', 'year', 'value', 'country'
        ]),
    }
    
    print("=" * 70)
    print("CARGA DE TABLAS FALLIDAS")
    print("=" * 70)
    print("\n[!] IMPORTANTE:")
    print("Antes de ejecutar este script, debes:")
    print("1. Ir a https://app.supabase.com/project/vyerhngdkzyhbhucolek/sql")
    print("2. Copiar el contenido de schema_correcciones.sql")
    print("3. Ejecutarlo (Run)")
    print()
    
    for csv_file, (table_name, allowed_cols) in tables.items():
        path = PROCESSED / csv_file
        records = csv_to_records(path, allowed_cols)
        upload_table(table_name, records)
    
    print("\n" + "=" * 70)
    print("CARGA FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
