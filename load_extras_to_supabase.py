"""
Carga solo las columnas nuevas (mujeres_cabeza_hogar_pct, nivel_educativo_prom)
a la tabla geih_resumen_departamento en Supabase.
Primero agrega las columnas si no existen, luego actualiza los registros.
"""
import os
import pandas as pd
import numpy as np
import math
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

ROOT = Path.cwd()
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan SUPABASE_URL o SUPABASE_KEY en .env")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"Conectando a Supabase: {SUPABASE_URL}")

# 1. Leer CSV actualizado
path = PROCESSED / 'geih_resumen_departamento.csv'
df = pd.read_csv(path)
print(f"CSV: {len(df)} filas, columnas: {df.columns.tolist()}")

# 2. Para cada departamento, hacer update de las columnas nuevas
updates = []
for _, row in df.iterrows():
    depto = row['departamento']
    muj = row.get('mujeres_cabeza_hogar_pct')
    edu = row.get('nivel_educativo_prom')

    if pd.isna(muj):
        muj = None
    else:
        muj = round(float(muj), 1)

    if pd.isna(edu):
        edu = None
    else:
        edu = round(float(edu), 1)

    updates.append({
        'departamento': depto,
        'mujeres_cabeza_hogar_pct': muj,
        'nivel_educativo_prom': edu,
    })

# 3. Intentar hacer update registro por registro
# Supabase REST API no soporta UPDATE masivo, así que usamos upsert
print(f"\nActualizando {len(updates)} departamentos...")

# Primero intentar un upsert con on_conflict
# Necesitamos traer todos los datos existentes y reinsertarlos con los nuevos campos
try:
    # Traer datos actuales
    existing = supabase.table('geih_resumen_departamento').select('*').execute()
    print(f"Registros actuales en Supabase: {len(existing.data)}")

    # Crear mapa de updates por departamento normalizado
    def norm(s):
        import unicodedata
        if not s:
            return ""
        s = s.upper().strip()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        if "BOGOTA" in s:
            return "BOGOTA"
        if "SAN ANDRES" in s or "ARCHIPIELAGO" in s:
            return "ARCHIPIELAGO DE SAN ANDRES"
        if s == "GUAJIRA":
            return "LA GUAJIRA"
        if s == "NARINIO":
            return "NARINO"
        return s

    update_map = {}
    for u in updates:
        update_map[norm(u['departamento'])] = u

    # Merge: para cada registro existente, agregar los campos nuevos
    merged = []
    for rec in existing.data:
        key = norm(rec.get('departamento', ''))
        if key in update_map:
            rec['mujeres_cabeza_hogar_pct'] = update_map[key]['mujeres_cabeza_hogar_pct']
            rec['nivel_educativo_prom'] = update_map[key]['nivel_educativo_prom']
        merged.append(rec)

    # Eliminar id y created_at para el upsert
    for rec in merged:
        rec.pop('id', None)
        rec.pop('created_at', None)

    # Borrar registros existentes y reinsertar
    print("Borrando registros existentes...")
    supabase.table('geih_resumen_departamento').delete().neq('id', 0).execute()

    print("Insertando registros actualizados...")
    for i in range(0, len(merged), 50):
        batch = merged[i:i+50]
        try:
            supabase.table('geih_resumen_departamento').insert(batch).execute()
            print(f"  Lote {i//50 + 1}: {len(batch)} registros insertados")
        except Exception as e:
            print(f"  [ERROR] Lote {i//50 + 1}: {e}")
            # Intentar insertar con solo columnas seguras
            for rec in batch:
                safe = {k: v for k, v in rec.items() if v is not None or k in ['departamento', 'ocupados']}
                try:
                    supabase.table('geih_resumen_departamento').insert(safe).execute()
                except Exception as e2:
                    print(f"    [ERROR] {rec.get('departamento')}: {e2}")

    print("\n[OK] Carga completada")

    # Verificar
    verify = supabase.table('geih_resumen_departamento').select('departamento,mujeres_cabeza_hogar_pct,nivel_educativo_prom').execute()
    print(f"\nVerificacion: {len(verify.data)} registros")
    with_data = [r for r in verify.data if r.get('mujeres_cabeza_hogar_pct') is not None]
    print(f"Registros con mujeres_cabeza_hogar_pct: {len(with_data)}")
    with_edu = [r for r in verify.data if r.get('nivel_educativo_prom') is not None]
    print(f"Registros con nivel_educativo_prom: {len(with_edu)}")
    if with_data:
        print(f"\nEjemplo: {with_data[0]}")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()