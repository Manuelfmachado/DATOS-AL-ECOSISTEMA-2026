"""
ETL ALBA - Registro Nacional de Turismo (RNT - MinCIT).
Genera tablas agregadas para alimentar el modulo Emprende IA cuando el sector
es alojamiento, comidas, agencias de viajes u otros servicios turisticos.

Entrada: data/raw/rnt_establecimientos.csv (descargado por download_turismo_rnt.py)
Salidas (data/processed/):
  1. rnt_establecimientos.csv            - copia limpia y normalizada
  2. rnt_resumen_departamento_categoria.csv - establecimientos, camas, hab, empledos
                                                por departamento x categoria (ano mas reciente)
  3. rnt_resumen_municipio_categoria.csv - idem por municipio x categoria (top municipios)
  4. rnt_resumen_nacional_categoria.csv  - totales nacionales por categoria y sub_categoria

Categorias del RNT (segun diccionario MinCIT):
- ESTABLECIMIENTOS DE ALOJAMIENTO TURISTICO (hoteles, apartahoteles, hostales, etc.)
- AGENCIAS DE VIAJES
- GUIAS DE TURISMO
- OFICINAS DE REPRESENTACION TURISTICA
- ESTABLECIMIENTOS DE GASTRONOMIA (si aplica)
- OTROS
"""
import pandas as pd
import numpy as np
import os
import glob
import warnings

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, 'data', 'raw')

# Buscar el CSV descargado manualmente del portal de datos.gov.co (nombre con fecha)
# o el descargado por download_turismo_rnt.py
RNT_CANDIDATOS = sorted(glob.glob(os.path.join(RAW_DIR, 'Registro_Nacional_de_Turismo_RNT_*.csv')))
RNT_CANDIDATOS += [os.path.join(RAW_DIR, 'rnt_establecimientos.csv')]
RAW = RNT_CANDIDATOS[0] if RNT_CANDIDATOS else None

PROCESSED = os.path.join(BASE, 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)


def to_num(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)


def main():
    if not RAW or not os.path.exists(RAW):
        print(f'[FAIL] No se encontro CSV del RNT en {RAW_DIR}.')
        print('       Descarga el CSV desde https://www.datos.gov.co/d/thwd-ivmp')
        print('       y guardalo en data/raw/Registro_Nacional_de_Turismo_RNT_YYYYMMDD.csv')
        return

    print(f'ETL RNT - Registro Nacional de Turismo (MinCIT)')
    print(f'Archivo: {os.path.basename(RAW)}')
    print('=' * 70)

    df = pd.read_csv(RAW, encoding='utf-8-sig', low_memory=False)
    print(f'Leidos: {len(df):,} establecimientos-anio, {len(df.columns)} columnas')

    # Normalizar columnas a minusculas
    df.columns = [c.strip().lower() for c in df.columns]

    # Mapeo de columnas del CSV oficial a nombres internos
    rename_map = {
        'codigo_rnt': 'codigo_rnt',
        'estado_rnt': 'estado_rnt',
        'razon_social_establecimiento': 'razon_social_establecimiento',
        'departamento': 'departamento',
        'codigo_departamento': 'cod_dpto',
        'cod_dpto': 'cod_dpto',
        'municipio': 'municipio',
        'codigo_municipio': 'cod_mun',
        'cod_mun': 'cod_mun',
        'nit': 'nit',
        'categoria': 'categoria',
        'sub_categoria': 'sub_categoria',
        'numero_de_habitaciones': 'habitaciones',
        'habitaciones': 'habitaciones',
        'numero_de_camas': 'camas',
        'camas': 'camas',
        'numero_de_empleados': 'empleados',
        'num_emp1': 'empleados',
        'año': 'ano',
        'ano': 'ano',
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Normalizar texto. Los acentos del CSV oficial (TURÍSTICA, GASTRONOMÍA)
    # se preservan correctamente en UTF-8; solo aplicamos strip+upper.
    for col in ['estado_rnt', 'departamento', 'municipio', 'categoria', 'sub_categoria',
                'razon_social_establecimiento']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    # Numericos
    for col in ['habitaciones', 'camas', 'empleados', 'ano', 'cod_dpto', 'cod_mun']:
        if col in df.columns:
            df[col] = to_num(df[col])

    # Normalizar Bogota (variantes en el dataset)
    df['departamento'] = df['departamento'].replace({
        'BOGOTÁ, D.C.': 'BOGOTA D.C.',
        'BOGOTA D.E.': 'BOGOTA D.C.',
        'BOGOTÁ D.C.': 'BOGOTA D.C.',
        'BOGOTA, D.C.': 'BOGOTA D.C.',
    })
    df['municipio'] = df['municipio'].replace({
        'BOGOTA D.C.': 'BOGOTA D.C.',
        'BOGOTÁ D.C.': 'BOGOTA D.C.',
    })

    print(f'  Anios disponibles: {sorted(df["ano"].unique().tolist())}')
    print(f'  Estados: {df["estado_rnt"].value_counts().head(3).to_dict()}')

    # Solo estados ACTIVOS
    if 'estado_rnt' in df.columns:
        df_activos = df[df['estado_rnt'].str.contains('ACTIVO', na=False)].copy()
        print(f'  Activos: {len(df_activos):,} / {len(df):,} total')
    else:
        df_activos = df.copy()

    # Tomar el ano mas reciente disponible por establecimiento (codigo_rnt)
    if 'ano' in df_activos.columns and 'codigo_rnt' in df_activos.columns:
        df_activos = df_activos.sort_values(['codigo_rnt', 'ano']).drop_duplicates(
            'codigo_rnt', keep='last'
        )
        print(f'  Unico por codigo_rnt (ano mas reciente): {len(df_activos):,}')

    # === Tabla 1: copia limpia ===
    cols_out = [c for c in ['codigo_rnt', 'estado_rnt', 'razon_social_establecimiento',
                           'departamento', 'cod_dpto', 'municipio', 'cod_mun', 'nit',
                           'categoria', 'sub_categoria', 'habitaciones', 'camas',
                           'empleados', 'ano'] if c in df_activos.columns]
    df_clean = df_activos[cols_out].copy()
    out1 = os.path.join(PROCESSED, 'rnt_establecimientos.csv')
    df_clean.to_csv(out1, index=False, encoding='utf-8-sig')
    print(f'\n[OK] rnt_establecimientos.csv: {len(df_clean):,} filas, '
          f'{os.path.getsize(out1)/1024:.0f} KB')

    # === Tabla 2: resumen por departamento x categoria ===
    group_cols_dpto = [c for c in ['departamento', 'categoria'] if c in df_activos.columns]
    if group_cols_dpto and len(group_cols_dpto) == 2:
        agg_dpto = df_activos.groupby(group_cols_dpto).agg(
            establecimientos=('codigo_rnt', 'count'),
            habitaciones=('habitaciones', 'sum'),
            camas=('camas', 'sum'),
            empleados=('empleados', 'sum'),
        ).reset_index()
        out2 = os.path.join(PROCESSED, 'rnt_resumen_departamento_categoria.csv')
        agg_dpto.to_csv(out2, index=False, encoding='utf-8-sig')
        print(f'[OK] rnt_resumen_departamento_categoria.csv: {len(agg_dpto):,} filas, '
              f'{os.path.getsize(out2)/1024:.0f} KB')
        print(f'     Departamentos: {agg_dpto["departamento"].nunique()}, '
              f'Categorias: {agg_dpto["categoria"].nunique()}')

    # === Tabla 3: resumen por municipio x categoria ===
    group_cols_mun = [c for c in ['departamento', 'municipio', 'categoria']
                      if c in df_activos.columns]
    if len(group_cols_mun) == 3:
        agg_mun = df_activos.groupby(group_cols_mun).agg(
            establecimientos=('codigo_rnt', 'count'),
            habitaciones=('habitaciones', 'sum'),
            camas=('camas', 'sum'),
            empleados=('empleados', 'sum'),
        ).reset_index()
        out3 = os.path.join(PROCESSED, 'rnt_resumen_municipio_categoria.csv')
        agg_mun.to_csv(out3, index=False, encoding='utf-8-sig')
        print(f'[OK] rnt_resumen_municipio_categoria.csv: {len(agg_mun):,} filas, '
              f'{os.path.getsize(out3)/1024:.0f} KB')
        print(f'     Municipios: {agg_mun["municipio"].nunique()}')

    # === Tabla 4: resumen nacional por categoria x sub_categoria ===
    group_cols_nac = [c for c in ['categoria', 'sub_categoria'] if c in df_activos.columns]
    if len(group_cols_nac) == 2:
        agg_nac = df_activos.groupby(group_cols_nac).agg(
            establecimientos=('codigo_rnt', 'count'),
            habitaciones=('habitaciones', 'sum'),
            camas=('camas', 'sum'),
            empleados=('empleados', 'sum'),
        ).reset_index().sort_values('establecimientos', ascending=False)
        out4 = os.path.join(PROCESSED, 'rnt_resumen_nacional_categoria.csv')
        agg_nac.to_csv(out4, index=False, encoding='utf-8-sig')
        print(f'[OK] rnt_resumen_nacional_categoria.csv: {len(agg_nac):,} filas, '
              f'{os.path.getsize(out4)/1024:.0f} KB')
        print('\nTop categorias (establecimientos):')
        for _, r in agg_nac.head(15).iterrows():
            print(f'  {int(r["establecimientos"]):>5,}  {r["categoria"][:40]:<40} '
                  f'/ {str(r["sub_categoria"])[:25]}')

    print('\nETL RNT completado.')


if __name__ == '__main__':
    main()