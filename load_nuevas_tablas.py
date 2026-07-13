"""
Carga las 30 tablas + 2 JSON a Supabase usando la service_role key.
"""
import os
import json
import math
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

ROOT = Path(__file__).parent
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://vyerhngdkzyhbhucolek.supabase.co")
SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ5ZXJobmdka3p5aGJodWNvbGVrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MTY2NjE2MywiZXhwIjoyMDk3MjQyMTYzfQ.nVXWWm1IuQNRrdb20NMcUHQ6RSBuO-GgHr_ZTE-8g6Q"

supabase = create_client(SUPABASE_URL, SERVICE_KEY)


def csv_to_records(path):
    if not path.exists():
        print(f"  [SKIP] {path.name} no existe")
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
    if not records:
        print(f"  [SKIP] {table_name}: sin datos")
        return 0
    total_ok = 0
    errors = 0
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
                except Exception as e2:
                    if errors == 0:
                        print(f"    [ERROR] {e2}")
                    errors += 1
                    if errors > 5:
                        break
    print(f"  {table_name:45s} {total_ok:>7,} / {len(records):>7,} OK")
    return total_ok


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

print("=" * 70)
print("CARGA DE DATOS A SUPABASE")
print("=" * 70)

total_rows = 0
for csv_file, table_name in TABLES:
    path = PROCESSED / csv_file
    records = csv_to_records(path)
    total_rows += upload_table(table_name, records)

# Predicciones GEIH
print("\n  Cargando predicciones_geih...")
pred_path = PROCESSED / 'predicciones_geih.json'
if pred_path.exists():
    with open(pred_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = []
    for h_key in ['prediccion_1ano', 'prediccion_5anos']:
        if h_key in data.get('desempleo_nacional', {}):
            for p in data['desempleo_nacional'][h_key]:
                records.append({
                    'tipo': 'desempleo_nacional', 'periodo': p['periodo'],
                    'mediana': p['mediana'], 'p10': p['p10'], 'p90': p['p90'],
                    'horizonte': h_key,
                })
    for sector, sdata in data.get('sectores', {}).items():
        for h_key in ['prediccion_1ano', 'prediccion_5anos']:
            if h_key in sdata:
                for p in sdata[h_key]:
                    records.append({
                        'tipo': f'sector_{sector}', 'periodo': p['periodo'],
                        'mediana': p['mediana'], 'p10': p['p10'], 'p90': p['p90'],
                        'horizonte': h_key,
                    })
    total_rows += upload_table('predicciones_geih', records, batch_size=1000)

# Predicciones mundiales
print("  Cargando predicciones_mundiales...")
mund_path = PROCESSED / 'predicciones_mundiales.json'
if mund_path.exists():
    with open(mund_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    records = []
    for key in ['sectores', 'profesiones', 'habilidades', 'salarios']:
        if key in data:
            records.append({
                'tipo': key, 'categoria': key,
                'datos': json.dumps(data[key], ensure_ascii=False),
            })
    total_rows += upload_table('predicciones_mundiales', records, batch_size=100)

print(f"\n{'='*70}")
print(f"CARGA COMPLETADA: {total_rows:,} filas totales")
print(f"{'='*70}")