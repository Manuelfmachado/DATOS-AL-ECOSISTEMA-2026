"""
ETL para extraer variables adicionales del GEIH que requieren join con
'Características generales, seguridad social en salud y educación.CSV':
  - Mujeres cabeza de hogar (%): P6050==1 (jefe) + P3271==2 (mujer), por DPTO
  - Nivel educativo promedio (años): P3042 + P3042S1, por DPTO

Ambos archivos comparten DIRECTORIO + SECUENCIA_P + ORDEN.
"""
import pandas as pd
import numpy as np
from pathlib import Path

ROOT = Path.cwd()
GEIH_DIR = ROOT / "Marzo 2026" / "CSV"
PROCESSED = ROOT / "data" / "processed"

DPTO_MAP = {
    5: 'ANTIOQUIA', 8: 'ATLÁNTICO', 11: 'BOGOTÁ', 13: 'BOLÍVAR',
    15: 'BOYACÁ', 17: 'CALDAS', 18: 'CAQUETÁ', 19: 'CAUCA',
    20: 'CESAR', 23: 'CÓRDOBA', 25: 'CUNDINAMARCA', 27: 'CHOCÓ',
    41: 'HUILA', 44: 'LA GUAJIRA', 47: 'MAGDALENA', 50: 'META',
    52: 'NARIÑO', 54: 'NORTE DE SANTANDER', 63: 'QUINDÍO', 66: 'RISARALDA',
    68: 'SANTANDER', 70: 'SUCRE', 73: 'TOLIMA', 76: 'VALLE DEL CAUCA',
    81: 'ARAUCA', 85: 'CASANARE', 86: 'PUTUMAYO', 88: 'ARCHIPIÉLAGO DE SAN ANDRÉS',
    91: 'AMAZONAS', 94: 'GUAINÍA', 95: 'GUAVIARE', 97: 'VAUPÉS', 99: 'VICHADA'
}

# Mapeo de P3042 (nivel educativo) a etiqueta legible
NIVEL_EDUC_ETIQUETA = {
    1: 'Sin educación',
    2: 'Preescolar',
    3: 'Primaria',
    4: 'Secundaria',
    5: 'Bachiller',
    6: 'Postgrado',
    7: 'Especialización',
    8: 'Técnico',
    9: 'Tecnólogo',
    10: 'Universitario',
    11: 'Especialización',
    12: 'Maestría',
    13: 'Doctorado',
    99: 'Sin info',
}

# Marca si un nivel educativo corresponde a educacion superior
NIVEL_ES_SUPERIOR = {
    1: False, 2: False, 3: False, 4: False, 5: False,
    6: True, 7: True, 8: True, 9: True, 10: True,
    11: True, 12: True, 13: True, 99: False,
}

# Marca si un nivel corresponde a bachillerato completo o menos
NIVEL_ES_BASICA = {
    1: True, 2: True, 3: True, 4: True, 5: True,
    6: False, 7: False, 8: False, 9: False, 10: False,
    11: False, 12: False, 13: False, 99: True,
}


def leer_csv(path):
    if not path.exists():
        print(f"  [SKIP] No existe {path}")
        return None
    try:
        return pd.read_csv(path, sep=';', encoding='utf-8', low_memory=False)
    except Exception:
        return pd.read_csv(path, sep=';', encoding='latin-1', low_memory=False)


def main():
    print("=== ETL Extras GEIH: Mujeres cabeza de hogar + Nivel educativo ===\n")

    # 1. Leer Características generales
    path_cg = GEIH_DIR / "Características generales, seguridad social en salud y educación.CSV"
    df_cg = leer_csv(path_cg)
    if df_cg is None:
        print("[ERROR] No se pudo leer Características generales")
        return

    print(f"  Características generales: {len(df_cg):,} filas, {len(df_cg.columns)} columnas")

    # 2. Filtrar columnas necesarias
    cols_needed = ['DIRECTORIO', 'SECUENCIA_P', 'ORDEN', 'FEX_C18', 'DPTO', 'P3271', 'P6050', 'P3042', 'P3042S1']
    cols_present = [c for c in cols_needed if c in df_cg.columns]
    df_cg = df_cg[cols_present].copy()
    print(f"  Columnas presentes: {cols_present}")

    # 3. Mapear departamento
    df_cg['DPTO'] = pd.to_numeric(df_cg['DPTO'], errors='coerce')
    df_cg['departamento'] = df_cg['DPTO'].map(DPTO_MAP)
    df_cg = df_cg[df_cg['departamento'].notna()].copy()

    # 4. Factor de expansión
    df_cg['FEX_C18'] = pd.to_numeric(df_cg['FEX_C18'], errors='coerce').fillna(1)

    # 5. Normalizar variables
    df_cg['P3271'] = pd.to_numeric(df_cg['P3271'], errors='coerce')  # 1=Hombre, 2=Mujer
    df_cg['P6050'] = pd.to_numeric(df_cg['P6050'], errors='coerce')  # 1=Jefe hogar
    df_cg['P3042'] = pd.to_numeric(df_cg['P3042'], errors='coerce')  # Nivel educativo
    df_cg['P3042S1'] = pd.to_numeric(df_cg['P3042S1'], errors='coerce')  # Año/grado

    # ============================================================================
    # A. Mujeres cabeza de hogar (%)
    # ============================================================================
    print("\n[A] Calculando % mujeres cabeza de hogar por departamento...")

    # Filtrar solo jefes de hogar (P6050 == 1)
    jefes = df_cg[df_cg['P6050'] == 1].copy()
    jefes['es_mujer'] = (jefes['P3271'] == 2).astype(int)

    mujeres_hogar = jefes.groupby('departamento').apply(
        lambda g: pd.Series({
            'mujeres_cabeza_hogar_pct': (
                (g['es_mujer'] * g['FEX_C18']).sum() / g['FEX_C18'].sum() * 100
            ) if g['FEX_C18'].sum() > 0 else np.nan,
            'total_jefes_hogar': g['FEX_C18'].sum(),
        })
    ).reset_index()

    print(f"  [OK] {len(mujeres_hogar)} departamentos")
    print(f"  Rango: {mujeres_hogar['mujeres_cabeza_hogar_pct'].min():.1f}% - {mujeres_hogar['mujeres_cabeza_hogar_pct'].max():.1f}%")
    print(f"  Promedio nacional: {mujeres_hogar['mujeres_cabeza_hogar_pct'].mean():.1f}%")

    # ============================================================================
    # B. Nivel educativo: % con educacion superior + nivel dominante
    # ============================================================================
    print("\n[B] Calculando nivel educativo por departamento...")

    df_cg['es_superior'] = df_cg['P3042'].map(NIVEL_ES_SUPERIOR).fillna(False).astype(int)
    df_cg['es_basica'] = df_cg['P3042'].map(NIVEL_ES_BASICA).fillna(True).astype(int)

    # Para la etiqueta, agrupar en 3 categorias: Basica, Bachiller, Superior
    def etiqueta_nivel(nivel):
        if pd.isna(nivel) or nivel in (1, 2, 99):
            return 'Básica'
        elif nivel in (3, 4, 5):
            return 'Bachiller'
        elif nivel in (8, 9):
            return 'Técnico/Tecnólogo'
        elif nivel == 10:
            return 'Universitario'
        else:
            return 'Postgrado'

    df_cg['etiqueta_educ'] = df_cg['P3042'].apply(etiqueta_nivel)

    nivel_educ = df_cg.groupby('departamento').apply(
        lambda g: pd.Series({
            'pct_educacion_superior': (
                (g['es_superior'] * g['FEX_C18']).sum() / g['FEX_C18'].sum() * 100
            ) if g['FEX_C18'].sum() > 0 else 0,
            'nivel_educativo_categoria': (
                g.assign(w=g['FEX_C18'])
                 .groupby('etiqueta_educ')['w']
                 .sum()
                 .idxmax()
            ) if g['FEX_C18'].sum() > 0 else 'Básica',
        })
    ).reset_index()

    # Etiqueta cualitativa segun el % de educacion superior
    def etiqueta_pct(pct):
        if pct >= 35:
            return 'Alto nivel educativo'
        elif pct >= 20:
            return 'Nivel medio'
        elif pct >= 10:
            return 'Básico predominante'
        else:
            return 'Baja formación'

    nivel_educ['nivel_educativo_etiqueta'] = nivel_educ['pct_educacion_superior'].apply(etiqueta_pct)

    print(f"  [OK] {len(nivel_educ)} departamentos")
    print(f"  % con educacion superior:")
    print(f"    Rango: {nivel_educ['pct_educacion_superior'].min():.1f}% - {nivel_educ['pct_educacion_superior'].max():.1f}%")
    print(f"    Promedio nacional: {nivel_educ['pct_educacion_superior'].mean():.1f}%")
    print(f"  Nivel dominante por departamento:")
    print(nivel_educ['nivel_educativo_categoria'].value_counts().to_string())

    # ============================================================================
    # C. Merge y guardar
    # ============================================================================
    print("\n[C] Guardando resultados...")

    # Merge mujeres + nivel educativo
    extras = mujeres_hogar.merge(nivel_educ, on='departamento', how='outer')

    # Cargar archivo existente de resumen departamento y hacer merge
    path_resumen = PROCESSED / 'geih_resumen_departamento.csv'
    if path_resumen.exists():
        df_resumen = pd.read_csv(path_resumen)
        # Quitar columnas viejas si existen
        for col in ['nivel_educativo_prom', 'nivel_educativo_categoria', 'pct_educacion_superior', 'nivel_educativo_etiqueta']:
            if col in df_resumen.columns:
                df_resumen = df_resumen.drop(columns=[col])
        # Quitar columnas duplicadas de mujeres si existen
        for col in ['mujeres_cabeza_hogar_pct_x', 'mujeres_cabeza_hogar_pct_y']:
            if col in df_resumen.columns:
                df_resumen = df_resumen.drop(columns=[col])
        if 'mujeres_cabeza_hogar_pct' in df_resumen.columns:
            df_resumen = df_resumen.drop(columns=['mujeres_cabeza_hogar_pct'])
        # Merge manteniendo columnas existentes + nuevas
        df_resumen = df_resumen.merge(
            extras[['departamento', 'mujeres_cabeza_hogar_pct', 'pct_educacion_superior', 'nivel_educativo_etiqueta']],
            on='departamento',
            how='left'
        )
        df_resumen.to_csv(path_resumen, index=False)
        print(f"  [OK] {path_resumen.name} actualizado con nuevas columnas")
        print(f"  Columnas finales: {df_resumen.columns.tolist()}")
    else:
        print(f"  [WARN] {path_resumen.name} no existe, guardando solo extras")
        extras.to_csv(path_resumen, index=False)

    # También guardar archivo standalone
    extras.to_csv(PROCESSED / 'geih_extras_departamento.csv', index=False)
    print(f"  [OK] geih_extras_departamento.csv guardado ({len(extras)} filas)")

    # Mostrar muestra
    print("\n  Muestra de resultados:")
    muestra = extras[['departamento', 'mujeres_cabeza_hogar_pct', 'pct_educacion_superior', 'nivel_educativo_etiqueta']].head(10)
    print(muestra.to_string(index=False))

    print("\n=== ETL Extras completado ===")


if __name__ == '__main__':
    main()