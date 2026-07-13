"""
Script de corrección urgente: recalcular GEIH desempleo usando solo DSI=1 (desocupados).
Actualiza data/processed/geih_desempleo_departamento.csv y recarga a Supabase.
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path.cwd().parent if Path.cwd().name == 'backend' else Path.cwd()
GEIH_DIR = ROOT / "Marzo 2026" / "CSV"
PROCESSED = ROOT / "data" / "processed"

def leer_geih(path):
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, sep=';', encoding='utf-8', low_memory=False)
    except Exception:
        df = pd.read_csv(path, sep=';', encoding='latin-1', low_memory=False)
    return df

dpto_map = {
    5: 'ANTIOQUIA', 8: 'ATLÁNTICO', 11: 'BOGOTÁ', 13: 'BOLÍVAR',
    15: 'BOYACÁ', 17: 'CALDAS', 18: 'CAQUETÁ', 19: 'CAUCA',
    20: 'CESAR', 23: 'CÓRDOBA', 25: 'CUNDINAMARCA', 27: 'CHOCÓ',
    41: 'HUILA', 44: 'LA GUAJIRA', 47: 'MAGDALENA', 50: 'META',
    52: 'NARIÑO', 54: 'NORTE DE SANTANDER', 63: 'QUINDÍO', 66: 'RISARALDA',
    68: 'SANTANDER', 70: 'SUCRE', 73: 'TOLIMA', 76: 'VALLE DEL CAUCA',
    81: 'ARAUCA', 85: 'CASANARE', 86: 'PUTUMAYO', 88: 'ARCHIPIÉLAGO DE SAN ANDRÉS',
    91: 'AMAZONAS', 94: 'GUAINÍA', 95: 'GUAVIARE', 97: 'VAUPÉS', 99: 'VICHADA'
}

# Recalcular desempleo correcto
df_nocu = leer_geih(GEIH_DIR / "No ocupados.CSV")
assert df_nocu is not None, "No se encontró No ocupados.CSV"

# Antes del filtro
print(f"Total 'no ocupados' crudo: {len(df_nocu):,}")
print(f"DSI == 1 (desocupados): {(df_nocu['DSI'] == 1).sum():,}")

df_nocu = df_nocu[df_nocu['DSI'] == 1].copy()
df_nocu['departamento'] = df_nocu['DPTO'].map(dpto_map)

sexo_col = next((c for c in df_nocu.columns if 'SEXO' in c.upper() or c == 'P6020'), None)
if sexo_col:
    df_nocu['sexo'] = df_nocu[sexo_col]

fex_col_n = next((c for c in df_nocu.columns if c.upper() in ['FEX_C18', 'FEX_C_2011']), None)
if fex_col_n:
    df_nocu['fex'] = pd.to_numeric(df_nocu[fex_col_n], errors='coerce').fillna(1)
else:
    df_nocu['fex'] = 1

def weighted_mean_binary_n(g, col='sexo'):
    v = pd.to_numeric(g[col], errors='coerce')
    w = g['fex']
    mask = pd.notna(v) & pd.notna(w)
    if mask.sum() == 0:
        return np.nan
    return (v[mask] * w[mask]).sum() / w[mask].sum()

desempleo = df_nocu.groupby('departamento').apply(
    lambda g: pd.Series({
        'no_ocupados': g['fex'].sum(),
        'mujeres_pct': weighted_mean_binary_n(g, 'sexo') if 'sexo' in g.columns and g['sexo'].notna().any() else np.nan,
    })
).reset_index()

desempleo['no_ocupados'] = desempleo['no_ocupados'].round(0).astype(int)

desempleo.to_csv(PROCESSED / 'geih_desempleo_departamento.csv', index=False)
print(f"\n[OK] geih_desempleo_departamento.csv actualizado: {len(desempleo)} departamentos")
print(f"Desocupados expandidos nacionales (corregido): {desempleo['no_ocupados'].sum():,.0f}")

# Validar contra ocupados
res = pd.read_csv(PROCESSED / 'geih_resumen_departamento.csv')
print(f"Ocupados expandidos nacionales: {res['ocupados'].sum():,.0f}")
print(f"Tasa de desempleo corregida: {desempleo['no_ocupados'].sum() / (res['ocupados'].sum() + desempleo['no_ocupados'].sum()) * 100:.2f}%")
print(f"Tasa de ocupacion: {res['ocupados'].sum() / (res['ocupados'].sum() + desempleo['no_ocupados'].sum()) * 100:.2f}%")

# Cargar a Supabase
print("\nCargando a Supabase...")
from app.db.supabase import supabase

csv_path = PROCESSED / 'geih_desempleo_departamento.csv'
df_load = pd.read_csv(csv_path)
# Reemplazar NaN/inf por None para JSON
import numpy as np
df_load = df_load.replace([np.nan, np.inf, -np.inf], None)
data = df_load.to_dict('records')

supabase.table('geih_desempleo_departamento').delete().neq('id', 0).execute()
result = supabase.table('geih_desempleo_departamento').insert(data).execute()
print(f"[OK] {len(result.data)} filas cargadas en geih_desempleo_departamento")
