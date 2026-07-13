"""
Ejecuta schema_nuevas_tablas.sql en Supabase y carga todas las tablas.
Usa la service_role key para bypass RLS.
"""
import os
import json
import math
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

ROOT = Path(__file__).parent
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL")
ANON_KEY = os.getenv("SUPABASE_KEY")
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5ZXJobmdka3p5aGJodWNvbGVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTY2NjE2MywiZXhwIjoyMDk3MjQyMTYzfQ.nVXWWm1IuQNRrdb20NMcUHQ6RSBuO-GgHr_ZTE-8g6Q"

print(f"Supabase URL: {SUPABASE_URL}")

# Crear cliente con service_role key
supabase: Client = create_client(SUPABASE_URL, SERVICE_KEY)

# ============================================================================
# PASO 1: Crear tablas via PostgREST RPC
# ============================================================================

def ejecutar_sql_via_rpc(sql):
    """Intenta ejecutar SQL via PostgREST RPC."""
    headers = {
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
        'Content-Type': 'application/json',
    }
    # Probar varios nombres de funcion RPC que puedan ejecutar SQL
    for fn_name in ['pg_query', 'exec_sql', 'run_sql', 'pg_exec']:
        try:
            resp = requests.post(
                f'{SUPABASE_URL}/rest/v1/rpc/{fn_name}',
                headers=headers,
                json={'query': sql} if fn_name == 'pg_query' else {'sql': sql},
                timeout=30
            )
            if resp.status_code == 200:
                print(f"  [OK] SQL ejecutado via RPC {fn_name}")
                return True
        except Exception:
            pass
    return False


def ejecutar_sql_via_pg_endpoint(sql):
    """Intenta ejecutar SQL via el endpoint /pg de Supabase."""
    headers = {
        'apikey': SERVICE_KEY,
        'Authorization': f'Bearer {SERVICE_KEY}',
        'Content-Type': 'application/json',
    }
    try:
        resp = requests.post(
            f'{SUPABASE_URL}/pg/query',
            headers=headers,
            json={'query': sql},
            timeout=30
        )
        if resp.status_code == 200:
            print(f"  [OK] SQL ejecutado via /pg/query")
            return True
    except Exception:
        pass
    return False


def crear_tablas():
    """Crea las tablas nuevas en Supabase."""
    sql_path = ROOT / "schema_nuevas_tablas.sql"
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Dividir en statements individuales
    statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
    print(f"Statements SQL a ejecutar: {len(statements)}")

    # Intentar via RPC
    if ejecutar_sql_via_rpc(sql):
        return True

    # Intentar via /pg/query
    if ejecutar_sql_via_pg_endpoint(sql):
        return True

    print("  [FAIL] No se pudo ejecutar DDL via API REST")
    return False


# ============================================================================
# PASO 2: Cargar datos
# ============================================================================

def csv_to_records(path):
    """Lee CSV y devuelve lista de diccionarios limpios."""
    if not path.exists():
        return []
    df = pd.read_csv(path, encoding='utf-8-sig')
    df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
    df = df.where(pd.notna(df), None)
    df = df.replace([np.inf, -np.inf], None)
    records = df.to_dict('records')
    for rec in records:
        rec.pop('created_at', None)
        for k, v in rec.items():
            if isinstance(v, float):
                rec[k] = None if math.isnan(v) or math.isinf(v) else v
            elif isinstance(v, np.integer):
                rec[k] = int(v)
            elif isinstance(v, np.floating):
                rec[k] = float(v) if not math.isnan(v) else None
    return records


def upload_table(table_name, records, batch_size=500):
    """Sube registros a Supabase."""
    if not records:
        print(f"  [SKIP] {table_name}: sin datos")
        return
    print(f"[>] {table_name}: {len(records)} registros...", end=' ')
    total_ok = 0
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            supabase.table(table_name).insert(batch).execute()
            total_ok += len(batch)
        except Exception as e:
            for j in range(0, len(batch), 50):
                try:
                    supabase.table(table_name).insert(batch[j:j+50]).execute()
                    total_ok += len(batch[j:j+50])
                except Exception:
                    break
    print(f"{total_ok}/{len(records)} OK")


TABLES = [
    ('geih_resumen_nacional.csv', 'geih_resumen_nacional'),
    ('geih_desempleo_mensual.csv', 'geih_desempleo_mensual'),
    ('geih_empleo_sector_mensual.csv', 'geih_empleo_sector_mensual'),
    ('geih_informalidad_mensual.csv', 'geih_informalidad_mensual'),
    ('geih_empleo_depto_sector.csv', 'geih_empleo_depto_sector'),
    ('geih_salario_ocupacion.csv', 'geih_salario_ocupacion'),
    ('ole_ingresos_por_programa.csv', 'ole_ingresos_por_programa'),
    ('ole_ingresos_por_area.csv', 'ole_ingresos_por_area'),
    ('ole_ingresos_por_nivel.csv', 'ole_ingresos_por_nivel'),
    ('ole_ingresos_por_ies.csv', 'ole_ingresos_por_ies'),
    ('ole_graduados_por_anio.csv', 'ole_graduados_por_anio'),
    ('esco_ocupaciones.csv', 'esco_ocupaciones'),
    ('esco_habilidades.csv', 'esco_habilidades'),
    ('esco_ocupacion_habilidades.csv', 'esco_ocupacion_habilidades'),
    ('esco_skill_relations.csv', 'esco_skill_relations'),
    ('esco_habilidades_verdes.csv', 'esco_habilidades_verdes'),
    ('esco_habilidades_digitales.csv', 'esco_habilidades_digitales'),
    ('esco_green_share_ocupaciones.csv', 'esco_green_share_ocupaciones'),
    ('emicron_resumen_nacional.csv', 'emicron_resumen_nacional'),
    ('emicron_por_sector.csv', 'emicron_por_sector'),
    ('emicron_emprendimiento.csv', 'emicron_emprendimiento'),
    ('emicron_por_departamento.csv', 'emicron_por_departamento'),
    ('emicron_inclusion_financiera.csv', 'emicron_inclusion_financiera'),
]


def main():
    print("=" * 70)
    print("ALBA - Crear tablas + cargar datos a Supabase")
    print("=" * 70)

    # PASO 1: Crear tablas
    print("\n[1/2] Creando tablas...")
    tablas_creadas = crear_tablas()

    if not tablas_creadas:
        print("\n  No se pudo crear tablas via API REST.")
        print("  Necesitas ejecutar schema_nuevas_tablas.sql manualmente:")
        print("  1. Ve a Supabase Dashboard > SQL Editor")
        print("  2. Copia y pega el contenido de schema_nuevas_tablas.sql")
        print("  3. Click Run")
        print("  4. Vuelve a ejecutar este script")
        return

    # PASO 2: Cargar datos
    print("\n[2/2] Cargando datos...")

    for csv_file, table_name in TABLES:
        path = PROCESSED / csv_file
        records = csv_to_records(path)
        upload_table(table_name, records)

    # Predicciones JSON
    print("\n[>] Cargando predicciones...")

    # predicciones_geih.json
    pred_path = PROCESSED / 'predicciones_geih.json'
    if pred_path.exists():
        with open(pred_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = []
        for h_key in ['prediccion_1ano', 'prediccion_5anos']:
            if h_key in data.get('desempleo_nacional', {}):
                for p in data['desempleo_nacional'][h_key]:
                    records.append({
                        'tipo': 'desempleo_nacional',
                        'periodo': p['periodo'],
                        'mediana': p['mediana'],
                        'p10': p['p10'],
                        'p90': p['p90'],
                        'horizonte': h_key,
                    })
        for sector, sdata in data.get('sectores', {}).items():
            for h_key in ['prediccion_1ano', 'prediccion_5anos']:
                if h_key in sdata:
                    for p in sdata[h_key]:
                        records.append({
                            'tipo': f'sector_{sector}',
                            'periodo': p['periodo'],
                            'mediana': p['mediana'],
                            'p10': p['p10'],
                            'p90': p['p90'],
                            'horizonte': h_key,
                        })
        upload_table('predicciones_geih', records, batch_size=1000)

    # predicciones_mundiales.json
    mund_path = PROCESSED / 'predicciones_mundiales.json'
    if mund_path.exists():
        with open(mund_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        records = []
        for key in ['sectores', 'profesiones', 'habilidades', 'salarios']:
            if key in data:
                records.append({
                    'tipo': key,
                    'categoria': key,
                    'datos': json.dumps(data[key], ensure_ascii=False),
                })
        upload_table('predicciones_mundiales', records, batch_size=100)

    print("\n" + "=" * 70)
    print("CARGA COMPLETADA")
    print("=" * 70)


if __name__ == '__main__':
    main()