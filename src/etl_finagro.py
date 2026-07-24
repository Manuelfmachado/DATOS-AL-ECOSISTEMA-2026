"""
ETL ALBA - FINAGRO (credito agropecuario).
Genera tablas agregadas para alimentar el modulo Emprende IA cuando el sector
es agricultura, ganaderia o actividades rurales.

Entradas (descargadas por download_finagro.py):
  - data/raw/finagro_colocaciones_detalle.csv
  - data/raw/finagro_colocaciones_resumen.csv

Salidas (data/processed/):
  1. finagro_colocaciones_detalle.csv      - copia limpia (dpto x cadena x ano x tipo)
  2. finagro_resumen_departamento.csv       - totales por departamento (colocacion, ops, cadenas)
  3. finagro_resumen_cadena.csv             - cadenas productivas mas financiadas
  4. finagro_resumen_nacional_anual.csv     - totales anuales nacionales
  5. finagro_top_cadenas_departamento.csv   - top cadenas por departamento (para ranking)

El dataset FINAGRO contiene la linea_de_produccion (cadena productiva: cacao, cafe,
palma, bovinos, arroz, etc.) por cada credito colocado. Para Emprende IA esto permite
responder: "¿cultivar cacao en Cordoba?" con los creditos reales desembolsados alli.
"""
import pandas as pd
import numpy as np
import os
import warnings

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DETALLE = os.path.join(BASE, 'data', 'raw', 'finagro_colocaciones_detalle.csv')
RAW_RESUMEN = os.path.join(BASE, 'data', 'raw', 'finagro_colocaciones_resumen.csv')
PROCESSED = os.path.join(BASE, 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)


def to_num(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)


def main():
    if not os.path.exists(RAW_DETALLE):
        print(f'[FAIL] No existe {RAW_DETALLE}. Ejecuta primero download_finagro.py')
        return

    print('ETL FINAGRO - Colocaciones de Credito Agropecuario')
    print('=' * 70)

    df = pd.read_csv(RAW_DETALLE, encoding='utf-8-sig', low_memory=False)
    print(f'Leidos: {len(df):,} filas agregadas (dpto x cadena x ano x tipo)')

    # Normalizar columnas
    df.columns = [c.strip().lower() for c in df.columns]

    # Renombrar columna ano si vino como 'a_o'
    if 'a_o' in df.columns and 'ano' not in df.columns:
        df = df.rename(columns={'a_o': 'ano'})

    # Limpiar texto
    for col in ['departamento_inversion', 'destino_de_credito']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()
            df[col] = df[col].replace({'NAN': np.nan, '': np.nan})

    # Numericos
    for col in ['ano', 'total_colocacion', 'total_inversion', 'num_operaciones']:
        if col in df.columns:
            df[col] = to_num(df[col])

    df['ano'] = df['ano'].astype(int)

    print(f'  Anios: {sorted(df["ano"].unique())}')
    print(f'  Departamentos: {df["departamento_inversion"].nunique()}')
    print(f'  Destinos de credito (cultivos/actividades): {df["destino_de_credito"].nunique()}')

    # Normalizar Bogota (hay variantes: "BOGOTA, D.C." / "BOGOTA D.E.")
    df['departamento_inversion'] = df['departamento_inversion'].replace({
        'BOGOTÁ, D.C.': 'BOGOTA D.C.',
        'BOGOTA D.E.': 'BOGOTA D.C.',
        'BOGOTÁ D.C.': 'BOGOTA D.C.',
        'BOGOTA, D.C.': 'BOGOTA D.C.',
    })

    # Extraer el cultivo/actividad del destino_de_credito (formato "132310 Sostenimiento cafe")
    # quitando el codigo numerico inicial
    def extraer_cultivo(destino):
        if not destino or destino == 'NAN':
            return None
        partes = destino.split(' ', 1)
        return partes[1] if len(partes) > 1 else destino
    df['cultivo'] = df['destino_de_credito'].apply(extraer_cultivo)

    # === Tabla 1: copia limpia detalle ===
    out1 = os.path.join(PROCESSED, 'finagro_colocaciones_detalle.csv')
    df.to_csv(out1, index=False, encoding='utf-8-sig')
    print(f'\n[OK] finagro_colocaciones_detalle.csv: {len(df):,} filas, '
          f'{os.path.getsize(out1)/1024:.0f} KB')

    # === Tabla 2: resumen por departamento (todos los anos) ===
    agg_dpto = df.groupby('departamento_inversion').agg(
        total_colocacion=('total_colocacion', 'sum'),
        total_inversion=('total_inversion', 'sum'),
        num_operaciones=('num_operaciones', 'sum'),
        cultivos_distintos=('cultivo', 'nunique'),
    ).reset_index().sort_values('total_colocacion', ascending=False)
    agg_dpto['total_colocacion'] = agg_dpto['total_colocacion'].round(0)
    agg_dpto['total_inversion'] = agg_dpto['total_inversion'].round(0)
    out2 = os.path.join(PROCESSED, 'finagro_resumen_departamento.csv')
    agg_dpto.to_csv(out2, index=False, encoding='utf-8-sig')
    print(f'[OK] finagro_resumen_departamento.csv: {len(agg_dpto)} filas, '
          f'{os.path.getsize(out2)/1024:.0f} KB')
    print('\nTop 10 departamentos por colocacion (2020-2024):')
    for _, r in agg_dpto.head(10).iterrows():
        print(f'  ${r["total_colocacion"]/1e9:>6.1f}B  {r["departamento_inversion"]:<15} '
              f'({int(r["num_operaciones"]):>6,} ops, {int(r["cultivos_distintos"]):>2,} cultivos)')

    # === Tabla 3: resumen por cultivo (todos los anos) ===
    agg_cad = df.groupby('cultivo').agg(
        total_colocacion=('total_colocacion', 'sum'),
        num_operaciones=('num_operaciones', 'sum'),
        departamentos=('departamento_inversion', 'nunique'),
    ).reset_index().sort_values('total_colocacion', ascending=False)
    agg_cad['total_colocacion'] = agg_cad['total_colocacion'].round(0)
    out3 = os.path.join(PROCESSED, 'finagro_colocaciones_cadena.csv')
    agg_cad.to_csv(out3, index=False, encoding='utf-8-sig')
    print(f'\n[OK] finagro_colocaciones_cadena.csv: {len(agg_cad)} cultivos, '
          f'{os.path.getsize(out3)/1024:.0f} KB')
    print('\nTop 15 cultivos/actividades:')
    for _, r in agg_cad.head(15).iterrows():
        print(f'  ${r["total_colocacion"]/1e9:>5.1f}B  {str(r["cultivo"])[:40]:<40} '
              f'({int(r["departamentos"]):>2} dptos)')

    # === Tabla 4: resumen nacional anual ===
    agg_ano = df.groupby('ano').agg(
        total_colocacion=('total_colocacion', 'sum'),
        total_inversion=('total_inversion', 'sum'),
        num_operaciones=('num_operaciones', 'sum'),
        departamentos_atendidos=('departamento_inversion', 'nunique'),
        cultivos_atendidos=('cultivo', 'nunique'),
    ).reset_index().sort_values('ano')
    agg_ano['total_colocacion'] = agg_ano['total_colocacion'].round(0)
    agg_ano['total_inversion'] = agg_ano['total_inversion'].round(0)
    out4 = os.path.join(PROCESSED, 'finagro_resumen_nacional_anual.csv')
    agg_ano.to_csv(out4, index=False, encoding='utf-8-sig')
    print(f'\n[OK] finagro_resumen_nacional_anual.csv: {len(agg_ano)} anos')
    for _, r in agg_ano.iterrows():
        print(f'  {int(r["ano"])}: ${r["total_colocacion"]/1e9:>5.1f}B colocados, '
              f'{int(r["num_operaciones"]):>6,} ops, {int(r["cultivos_atendidos"]):>2} cultivos')

    # === Tabla 5: top cultivos por departamento (para ranking de oportunidades) ===
    agg_dpto_cad = df.groupby(['departamento_inversion', 'cultivo']).agg(
        total_colocacion=('total_colocacion', 'sum'),
        num_operaciones=('num_operaciones', 'sum'),
    ).reset_index()
    # Rank por departamento
    agg_dpto_cad['rank'] = agg_dpto_cad.groupby('departamento_inversion')['total_colocacion'] \
        .rank(method='dense', ascending=False).astype(int)
    agg_dpto_cad = agg_dpto_cad.sort_values(['departamento_inversion', 'rank'])
    agg_dpto_cad['total_colocacion'] = agg_dpto_cad['total_colocacion'].round(0)
    out5 = os.path.join(PROCESSED, 'finagro_top_cadenas_departamento.csv')
    agg_dpto_cad.to_csv(out5, index=False, encoding='utf-8-sig')
    print(f'\n[OK] finagro_top_cadenas_departamento.csv: {len(agg_dpto_cad):,} filas, '
          f'{os.path.getsize(out5)/1024:.0f} KB')

    print('\nETL FINAGRO completado.')


if __name__ == '__main__':
    main()