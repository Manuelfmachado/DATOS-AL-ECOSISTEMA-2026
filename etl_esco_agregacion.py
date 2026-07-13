"""
ETL ALBA - Paso 3: Procesar ESCO (18 archivos CSV) y generar tablas limpias
Lee los 18 CSV de ESCO y genera tablas optimizadas para los modulos de ALBA.

Tablas generadas:
1. esco_ocupaciones.csv              - Catalogo de ocupaciones (19.289 filas)
2. esco_habilidades.csv              - Catalogo de habilidades (45.503 filas)
3. esco_ocupacion_habilidades.csv    - Relacion ocupacion->habilidad (126.051 filas)
4. esco_skill_relations.csv          - Grafo de habilidades relacionadas (5.818 filas)
5. esco_habilidades_verdes.csv       - Habilidades verdes (844 filas)
6. esco_habilidades_digitales.csv    - Habilidades digitales (1.520 filas)
7. esco_green_share_ocupaciones.csv  - Indice de verdor por ocupacion (3.590 filas)
"""
import pandas as pd
import os
import time
import warnings

warnings.filterwarnings('ignore')

BASE = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\ESCO dataset - v1.2.1 - classification - es - csv'
PROCESSED = os.path.join(r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026', 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)


def leer_csv(path, nrows=None):
    """Lee un CSV de ESCO."""
    try:
        return pd.read_csv(path, encoding='utf-8', nrows=nrows, low_memory=False)
    except Exception as e:
        print(f'  Error leyendo {os.path.basename(path)}: {e}')
        return pd.DataFrame()


def guardar(df, name):
    """Guarda un DataFrame a CSV en data/processed."""
    path = os.path.join(PROCESSED, name)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    print(f'  [OK] {name}: {len(df):,} filas, {os.path.getsize(path)/1024:.0f} KB')


def main():
    print('ETL ESCO - Procesando 18 archivos CSV...')
    print('=' * 70)

    # --- 1. OCUPACIONES ---
    print('\n[1/7] Ocupaciones...')
    occ = leer_csv(os.path.join(BASE, 'occupations_es.csv'))
    if not occ.empty:
        # Seleccionar columnas utiles
        cols_occ = [c for c in ['conceptUri', 'preferredLabel', 'altLabels', 'hiddenLabels',
                                'iscoGroup', 'naceCode', 'definition', 'regulatedProfessionNote',
                                'scopeNote', 'inScheme'] if c in occ.columns]
        occ_clean = occ[cols_occ].copy()
        occ_clean.columns = ['uri', 'nombre', 'nombres_alternativos', 'nombres_ocultos',
                             'codigo_isco', 'codigo_nace', 'definicion',
                             'nota_profesion_regulada', 'nota_alcance', 'esquema']
        guardar(occ_clean, 'esco_ocupaciones.csv')

    # --- 2. HABILIDADES ---
    print('[2/7] Habilidades...')
    skills = leer_csv(os.path.join(BASE, 'skills_es.csv'))
    if not skills.empty:
        cols_skills = [c for c in ['conceptUri', 'preferredLabel', 'altLabels', 'hiddenLabels',
                                    'skillType', 'reuseLevel', 'definition', 'scopeNote',
                                    'inScheme'] if c in skills.columns]
        skills_clean = skills[cols_skills].copy()
        skills_clean.columns = ['uri', 'nombre', 'nombres_alternativos', 'nombres_ocultos',
                                'tipo_habilidad', 'nivel_reutilizacion', 'definicion',
                                'nota_alcance', 'esquema']
        guardar(skills_clean, 'esco_habilidades.csv')

    # --- 3. RELACION OCUPACION -> HABILIDAD ---
    print('[3/7] Relacion ocupacion-habilidad...')
    rel = leer_csv(os.path.join(BASE, 'occupationSkillRelations_es.csv'))
    if not rel.empty:
        cols_rel = [c for c in ['occupationUri', 'occupationLabel', 'relationType',
                                'skillType', 'skillUri', 'skillLabel'] if c in rel.columns]
        rel_clean = rel[cols_rel].copy()
        rel_clean.columns = ['ocupacion_uri', 'ocupacion_nombre', 'tipo_relacion',
                             'tipo_habilidad', 'habilidad_uri', 'habilidad_nombre']
        guardar(rel_clean, 'esco_ocupacion_habilidades.csv')

    # --- 4. GRAFO DE HABILIDADES RELACIONADAS ---
    print('[4/7] Grafo de habilidades relacionadas...')
    ssr = leer_csv(os.path.join(BASE, 'skillSkillRelations_es.csv'))
    if not ssr.empty:
        cols_ssr = [c for c in ['originalSkillUri', 'originalSkillType', 'relationType',
                                'relatedSkillType', 'relatedSkillUri'] if c in ssr.columns]
        ssr_clean = ssr[cols_ssr].copy()
        ssr_clean.columns = ['habilidad_origen_uri', 'tipo_origen', 'tipo_relacion',
                             'tipo_relacionada', 'habilidad_relacionada_uri']
        guardar(ssr_clean, 'esco_skill_relations.csv')

    # --- 5. HABILIDADES VERDES ---
    print('[5/7] Habilidades verdes...')
    green = leer_csv(os.path.join(BASE, 'greenSkillsCollection_es.csv'))
    if not green.empty:
        cols_green = [c for c in ['conceptUri', 'preferredLabel', 'description', 'skillType', 'reuseLevel'] if c in green.columns]
        green_clean = green[cols_green].copy()
        green_clean.columns = ['uri', 'nombre', 'definicion', 'tipo_habilidad', 'nivel_reutilizacion'] if len(cols_green) == 5 else green_clean.columns
        guardar(green_clean, 'esco_habilidades_verdes.csv')

    # --- 6. HABILIDADES DIGITALES ---
    print('[6/7] Habilidades digitales...')
    digital = leer_csv(os.path.join(BASE, 'digitalSkillsCollection_es.csv'))
    if not digital.empty:
        cols_dig = [c for c in ['conceptUri', 'preferredLabel', 'description', 'skillType', 'reuseLevel'] if c in digital.columns]
        digital_clean = digital[cols_dig].copy()
        digital_clean.columns = ['uri', 'nombre', 'definicion', 'tipo_habilidad', 'nivel_reutilizacion'] if len(cols_dig) == 5 else digital_clean.columns
        guardar(digital_clean, 'esco_habilidades_digitales.csv')

    # --- 7. INDICE DE VERDOR POR OCUPACION ---
    print('[7/7] Indice de verdor por ocupacion...')
    green_occ = leer_csv(os.path.join(BASE, 'greenShareOcc_es.csv'))
    if not green_occ.empty:
        cols_go = [c for c in ['conceptUri', 'code', 'preferredLabel', 'greenShare'] if c in green_occ.columns]
        green_occ_clean = green_occ[cols_go].copy()
        green_occ_clean.columns = ['uri', 'codigo', 'nombre', 'indice_verdor']
        guardar(green_occ_clean, 'esco_green_share_ocupaciones.csv')

    print('\n' + '=' * 70)
    print('ETL ESCO completado.')


if __name__ == '__main__':
    main()