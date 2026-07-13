"""
ETL ALBA - Paso 2: Procesar OLE-IBC (4 archivos Excel) y generar tablas agregadas
Lee los 4 archivos Excel del OLE (2020-2023) con encoding reparado
y genera tablas agregadas para los modulos de ALBA.

Tablas generadas:
1. ole_ingresos_por_programa.csv    - Distribucion de ingresos por programa academico
2. ole_ingresos_por_area.csv        - Distribucion de ingresos por area de conocimiento
3. ole_ingresos_por_nivel.csv       - Distribucion de ingresos por nivel de formacion
4. ole_ingresos_por_ies.csv         - Ranking de IES por ingresos de graduados
5. ole_graduados_por_anio.csv       - Total graduados por ano y programa
"""
import pandas as pd
import numpy as np
import os
import time
import warnings

warnings.filterwarnings('ignore')

BASE = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026'
PROCESSED = os.path.join(BASE, 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)

# Los 4 archivos Excel del OLE (cada uno contiene datos 2001-ano_corte)
ARCHIVOS = [
    # Usar solo el archivo mas reciente (corte 2023, datos 2001-2022)
    # Es el mas completo y actualizado, evita duplicados entre cortes
    (os.path.join(BASE, 'articles-425926_recurso_1.xlsx'), 2023, 8),
]

# Nombres de columnas normalizados
COLUMNAS = [
    'CODIGO_IES', 'IES', 'ID_SECTOR', 'SECTOR', 'CODIGO_SNIES', 'PROGRAMA',
    'ID_NIVEL_ACAD', 'NIVEL_ACAD', 'ID_NIVEL_FORM', 'NIVEL_FORM',
    'ID_AREA', 'AREA', 'SEXO', 'ANO_GRADO', 'INGRESO', 'GRADUADOS'
]


def fix_encoding(s):
    """Repara mojibake del Excel OLE. Intenta varios decodings hasta que el texto sea legible."""
    if pd.isna(s):
        return s
    s = str(s)
    # Si ya tiene tildes validas, no necesita fix
    if any(c in s for c in ['á', 'é', 'í', 'ó', 'ú', 'ñ', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ñ']):
        return s
    # Intentar utf-8 -> latin1 (caso comun del mojibake)
    try:
        result = s.encode('utf-8').decode('latin1')
        if any(c in result for c in ['á', 'é', 'í', 'ó', 'ú', 'ñ']):
            return result
    except Exception:
        pass
    # Intentar latin1 -> utf-8
    try:
        result = s.encode('latin1').decode('utf-8')
        if any(c in result for c in ['á', 'é', 'í', 'ó', 'ú', 'ñ']):
            return result
    except Exception:
        pass
    return s


def leer_archivo_ole(path, skiprows, ano_corte):
    """Lee un archivo Excel del OLE con skiprows correcto y repara encoding."""
    print(f'  Leyendo {os.path.basename(path)} (corte {ano_corte}, skiprows={skiprows})...')
    df = pd.read_excel(path, sheet_name=0, skiprows=skiprows, dtype=str)
    if len(df.columns) == 16:
        df.columns = COLUMNAS
    else:
        print(f'    WARNING: {len(df.columns)} columnas (esperadas 16)')
        return pd.DataFrame()
    # Reparar encoding en columnas de texto
    for col in ['IES', 'PROGRAMA', 'SECTOR', 'NIVEL_ACAD', 'NIVEL_FORM', 'AREA', 'SEXO']:
        if col in df.columns:
            df[col] = df[col].apply(fix_encoding)
    # Convertir numericos
    df['GRADUADOS'] = pd.to_numeric(df['GRADUADOS'], errors='coerce').fillna(0).astype(int)
    df['ANO_GRADO'] = pd.to_numeric(df['ANO_GRADO'], errors='coerce')
    df['CODIGO_SNIES'] = pd.to_numeric(df['CODIGO_SNIES'], errors='coerce')
    print(f'    {len(df)} filas leidas')
    return df


def main():
    print('ETL OLE-IBC - Procesando 4 archivos Excel...')
    print('=' * 70)

    # Usar solo el archivo mas reciente (2023, corte mas completo)
    # pero tambien cargar 2020-2022 para comparar
    dfs = []
    for path, ano_corte, skiprows in ARCHIVOS:
        if not os.path.exists(path):
            print(f'  [SKIP] {os.path.basename(path)} no existe')
            continue
        df = leer_archivo_ole(path, skiprows, ano_corte)
        if not df.empty:
            df['ANO_CORTE'] = ano_corte
            dfs.append(df)

    if not dfs:
        print('ERROR: No se pudieron leer los archivos OLE')
        return

    # Combinar todos los archivos
    print('\nCombinando archivos...')
    df_all = pd.concat(dfs, ignore_index=True)
    print(f'Total filas combinadas: {len(df_all):,}')

    # Eliminar la deduplicacion compleja que era lenta; con un solo archivo no hay duplicados entre cortes

    # Agrupar INGRESO en categorias limpias
    def normalizar_ingreso(val):
        if pd.isna(val):
            return 'No reporta'
        val = str(val).strip()
        # Normalizar variantes
        val_lower = val.lower()
        if 'no reporta' in val_lower or 'no_reporta' in val_lower or val == '' or val == 'nan':
            return 'No reporta'
        return val

    df_all['INGRESO_NORM'] = df_all['INGRESO'].apply(normalizar_ingreso)

    # --- TABLA 1: Ingresos por programa academico ---
    print('\nGenerando ole_ingresos_por_programa.csv...')
    prog = df_all.groupby(['PROGRAMA', 'INGRESO_NORM'])['GRADUADOS'].sum().reset_index()
    prog.columns = ['programa', 'rango_ingreso', 'graduados']
    # Calcular total por programa para porcentajes
    totales_prog = prog.groupby('programa')['graduados'].transform('sum')
    prog['porcentaje'] = (prog['graduados'] / totales_prog * 100).round(2)
    prog = prog[prog['graduados'] > 0]
    prog = prog.sort_values(['programa', 'graduados'], ascending=[True, False])
    path1 = os.path.join(PROCESSED, 'ole_ingresos_por_programa.csv')
    prog.to_csv(path1, index=False, encoding='utf-8-sig')
    print(f'  [OK] {len(prog):,} filas, {os.path.getsize(path1)/1024:.0f} KB')

    # --- TABLA 2: Ingresos por area de conocimiento ---
    print('Generando ole_ingresos_por_area.csv...')
    area = df_all.groupby(['AREA', 'INGRESO_NORM'])['GRADUADOS'].sum().reset_index()
    area.columns = ['area', 'rango_ingreso', 'graduados']
    totales_area = area.groupby('area')['graduados'].transform('sum')
    area['porcentaje'] = (area['graduados'] / totales_area * 100).round(2)
    area = area.sort_values(['area', 'graduados'], ascending=[True, False])
    path2 = os.path.join(PROCESSED, 'ole_ingresos_por_area.csv')
    area.to_csv(path2, index=False, encoding='utf-8-sig')
    print(f'  [OK] {len(area):,} filas, {os.path.getsize(path2)/1024:.0f} KB')

    # --- TABLA 3: Ingresos por nivel de formacion ---
    print('Generando ole_ingresos_por_nivel.csv...')
    nivel = df_all.groupby(['NIVEL_FORM', 'INGRESO_NORM'])['GRADUADOS'].sum().reset_index()
    nivel.columns = ['nivel_formacion', 'rango_ingreso', 'graduados']
    totales_nivel = nivel.groupby('nivel_formacion')['graduados'].transform('sum')
    nivel['porcentaje'] = (nivel['graduados'] / totales_nivel * 100).round(2)
    nivel = nivel.sort_values(['nivel_formacion', 'graduados'], ascending=[True, False])
    path3 = os.path.join(PROCESSED, 'ole_ingresos_por_nivel.csv')
    nivel.to_csv(path3, index=False, encoding='utf-8-sig')
    print(f'  [OK] {len(nivel):,} filas, {os.path.getsize(path3)/1024:.0f} KB')

    # --- TABLA 4: Ranking de IES por ingresos de graduados ---
    print('Generando ole_ingresos_por_ies.csv...')
    # Para cada IES, calcular el rango modal de ingreso (el mas comun)
    ies_data = df_all.groupby(['IES', 'INGRESO_NORM'])['GRADUADOS'].sum().reset_index()
    ies_data.columns = ['ies', 'rango_ingreso', 'graduados']
    # El rango modal es el que tiene mas graduados
    ies_modal = ies_data.sort_values('graduados', ascending=False).drop_duplicates('ies', keep='first')
    ies_modal.columns = ['ies', 'rango_modal', 'graduados_rango_modal']
    # Total graduados por IES
    ies_total = df_all.groupby('IES')['GRADUADOS'].sum().reset_index()
    ies_total.columns = ['ies', 'total_graduados']
    ies_ranking = ies_modal.merge(ies_total, on='ies')
    ies_ranking = ies_ranking.sort_values('total_graduados', ascending=False)
    path4 = os.path.join(PROCESSED, 'ole_ingresos_por_ies.csv')
    ies_ranking.to_csv(path4, index=False, encoding='utf-8-sig')
    print(f'  [OK] {len(ies_ranking):,} filas, {os.path.getsize(path4)/1024:.0f} KB')

    # --- TABLA 5: Graduados por ano y programa ---
    print('Generando ole_graduados_por_anio.csv...')
    grad_anio = df_all.groupby(['ANO_GRADO', 'AREA'])['GRADUADOS'].sum().reset_index()
    grad_anio.columns = ['ano_grado', 'area', 'graduados']
    grad_anio = grad_anio[grad_anio['ano_grado'] >= 2001]
    grad_anio = grad_anio.sort_values(['ano_grado', 'graduados'], ascending=[True, False])
    path5 = os.path.join(PROCESSED, 'ole_graduados_por_anio.csv')
    grad_anio.to_csv(path5, index=False, encoding='utf-8-sig')
    print(f'  [OK] {len(grad_anio):,} filas, {os.path.getsize(path5)/1024:.0f} KB')

    # Resumen
    print('\n' + '=' * 70)
    print('Resumen OLE-IBC:')
    print(f'  Total filas procesadas: {len(df_all):,}')
    print(f'  Programas unicos: {df_all["PROGRAMA"].nunique():,}')
    print(f'  IES unicas: {df_all["IES"].nunique():,}')
    print(f'  Anios de grado: {sorted(df_all["ANO_GRADO"].dropna().unique())}')
    print(f'  Total graduados: {df_all["GRADUADOS"].sum():,}')
    print(f'  Areas: {sorted(df_all["AREA"].dropna().unique())}')
    print(f'  Rangos de ingreso: {sorted(df_all["INGRESO_NORM"].dropna().unique())}')


if __name__ == '__main__':
    main()