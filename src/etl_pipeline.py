"""
ETL Pipeline inicial para ALBACOLOMBIA (Alineación Laboral Basada en Analítica en Colombia)
Procesa datasets crudos de data/raw/ y genera tablas limpias en data/processed/
"""

import os
import sys
import json
import urllib.request
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Paths - usar directorio de trabajo absoluto
ROOT = Path.cwd()
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# GEIH está en carpeta especial, no en data/raw
GEIH_DIR = ROOT / "Marzo 2026" / "CSV"

print(f"[{datetime.now()}] Iniciando ETL")
print(f"RAW: {RAW}")
print(f"PROCESSED: {PROCESSED}")

# ============================================================================
# Descarga automática de datasets abiertos (Socrata / datos.gov.co)
# ============================================================================
DATASETS = {
    'spe_ape_inscritos_20260704.csv': {
        'url': 'https://www.datos.gov.co/api/views/8pqf-rmzr/rows.csv?accessType=DOWNLOAD',
        'desc': 'SPE proxy - APE SENA inscritos por ocupación'
    },
    'ole_etdh_programas_20260704.csv': {
        'url': 'https://www.datos.gov.co/api/views/2v94-3ypi/rows.csv?accessType=DOWNLOAD',
        'desc': 'OLE proxy - MEN programas ETDH'
    },
    'dnp_medicion_desempeno_municipal_20260704.csv': {
        'url': 'https://www.datos.gov.co/api/views/nkjx-rsq7/rows.csv?accessType=DOWNLOAD',
        'desc': 'DNP - Medición del Desempeño Municipal'
    },
}

def descargar_dataset(nombre, url, descripcion):
    destino = RAW / nombre
    if destino.exists():
        print(f"  [SKIP] {descripcion} ya existe: {destino.name}")
        return
    print(f"  [DOWNLOAD] {descripcion}...")
    try:
        urllib.request.urlretrieve(url, destino)
        print(f"  [OK] {destino.name} ({destino.stat().st_size / 1024:.1f} KB)")
    except Exception as e:
        print(f"  [ERROR] No se pudo descargar {descripcion}: {e}")
        print(f"  Descargalo manualmente de {url} y guardalo como {destino}")

print("\n[0/9] Verificando datasets descargables...")
for nombre, info in DATASETS.items():
    descargar_dataset(nombre, info['url'], info['desc'])

# ============================================================================
# 1. GEIH - Ocupados y No ocupados
# ============================================================================
print("\n[1/9] Procesando GEIH...")

geih_files = {
    'ocupados': GEIH_DIR / "Ocupados.CSV",
    'no_ocupados': GEIH_DIR / "No ocupados.CSV",
}

def leer_geih(path):
    """Lee CSV del GEIH con separador ; y codificación correcta."""
    if not path.exists():
        print(f"  [SKIP] No existe {path}")
        return None
    try:
        df = pd.read_csv(path, sep=';', encoding='utf-8', low_memory=False)
    except Exception as e:
        print(f"  [ERROR utf-8] {e}, probando latin-1")
        df = pd.read_csv(path, sep=';', encoding='latin-1', low_memory=False)
    return df

# Procesar ocupados
df_ocu = leer_geih(geih_files['ocupados'])
if df_ocu is not None:
    print(f"  Ocupados: {len(df_ocu):,} filas")
    # Mapeo básico de columnas comunes del GEIH
    cols = df_ocu.columns.tolist()
    
    # Extraer departamento
    dpto_col = 'DPTO' if 'DPTO' in cols else None
    if dpto_col:
        # DPTO en GEIH es numérico, mapear a nombres
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
        df_ocu['departamento'] = df_ocu[dpto_col].map(dpto_map)
    
    # Ingreso laboral - INGLABO
    if 'INGLABO' in cols:
        df_ocu['ingreso_laboral'] = pd.to_numeric(df_ocu['INGLABO'], errors='coerce')
    
    # Formalidad - P6460 (cotiza a pensión?) o P6460S1
    if 'P6460' in cols:
        df_ocu['cotiza_pension'] = pd.to_numeric(df_ocu['P6460'], errors='coerce')
        df_ocu['formal'] = df_ocu['cotiza_pension'].map({1: 1, 2: 0}).fillna(0)
    elif 'P6460S1' in cols:
        df_ocu['cotiza_pension'] = pd.to_numeric(df_ocu['P6460S1'], errors='coerce')
        df_ocu['formal'] = df_ocu['cotiza_pension'].map({1: 1, 2: 0}).fillna(0)
    else:
        df_ocu['formal'] = np.nan
    
    # Sexo - P6020 o similar
    sexo_col = next((c for c in cols if 'SEXO' in c.upper() or c == 'P6020'), None)
    if sexo_col:
        df_ocu['sexo'] = df_ocu[sexo_col]
    
    # Edad - P6040
    edad_col = next((c for c in cols if c == 'P6040'), None)
    if edad_col:
        df_ocu['edad'] = pd.to_numeric(df_ocu[edad_col], errors='coerce')
    
    # Nivel educativo - P6210 o similar
    edu_col = next((c for c in cols if 'NIVEL' in c.upper() or c == 'P6210' or c == 'P6210S1'), None)
    if edu_col:
        df_ocu['nivel_educativo'] = df_ocu[edu_col]
    
    # Rama de actividad - RAMA2D_R4
    rama_col = next((c for c in cols if 'RAMA2D' in c.upper() or c == 'RAMA4D_R4'), None)
    if rama_col:
        df_ocu['rama_actividad'] = df_ocu[rama_col]
    
    # Oficio - OFICIO_C8
    oficio_col = next((c for c in cols if 'OFICIO' in c.upper()), None)
    if oficio_col:
        df_ocu['oficio'] = df_ocu[oficio_col]
    
    # Factor de expansion (FEX_C18): cada fila representa FEX personas en la poblacion
    fex_col = next((c for c in cols if c.upper() in ['FEX_C18', 'FEX_C_2011']), None)
    if fex_col:
        df_ocu['fex'] = pd.to_numeric(df_ocu[fex_col], errors='coerce').fillna(1)
        print(f"  Factor de expansion detectado: {fex_col}")
    else:
        print("  [WARN] No se encontro factor de expansion (FEX_C18). Usando 1.")
        df_ocu['fex'] = 1
    
    # Agregar por departamento usando factor de expansion
    def weighted_mean(x, values='ingreso_laboral', weights='fex'):
        v = x[values]
        w = x[weights]
        mask = pd.notna(v) & pd.notna(w) & (v > 0)
        if mask.sum() == 0:
            return np.nan
        return (v[mask] * w[mask]).sum() / w[mask].sum()
    
    def weighted_mean_binary(x, col='formal'):
        v = pd.to_numeric(x[col], errors='coerce')
        w = x['fex']
        mask = pd.notna(v) & pd.notna(w)
        if mask.sum() == 0:
            return np.nan
        return (v[mask] * w[mask]).sum() / w[mask].sum()
    
    agregado = df_ocu.groupby('departamento').apply(
        lambda g: pd.Series({
            'ocupados': g['fex'].sum(),
            'ingreso_promedio': weighted_mean(g, 'ingreso_laboral', 'fex'),
            'ingreso_mediano': np.nan,  # mediana ponderada no trivial, se calcula aproximada abajo si aplica
            'tasa_formalidad': weighted_mean_binary(g, 'formal') if 'formal' in g.columns and g['formal'].notna().any() else np.nan,
            'mujeres_pct': weighted_mean_binary(g, 'sexo') if 'sexo' in g.columns and g['sexo'].notna().any() else np.nan,
        })
    ).reset_index()
    
    # Mediana ponderada aproximada usando percentil 50 de muestra expandida
    if 'ingreso_laboral' in df_ocu.columns:
        for i, row in agregado.iterrows():
            dpto = row['departamento']
            g = df_ocu[(df_ocu['departamento'] == dpto) & (df_ocu['ingreso_laboral'] > 0)]
            if len(g) > 0:
                sorted_g = g.sort_values('ingreso_laboral')
                cumsum = sorted_g['fex'].cumsum()
                total = sorted_g['fex'].sum()
                median_row = sorted_g[cumsum >= total / 2].iloc[0]
                agregado.at[i, 'ingreso_mediano'] = median_row['ingreso_laboral']
    
    agregado.to_csv(PROCESSED / 'geih_resumen_departamento.csv', index=False)
    print(f"  [OK] geih_resumen_departamento.csv: {len(agregado)} departamentos")
    print(f"  Ocupados expandidos nacionales: {agregado['ocupados'].sum():,.0f}")

# Procesar no ocupados
df_nocu = leer_geih(geih_files['no_ocupados'])
if df_nocu is not None:
    print(f"  No ocupados: {len(df_nocu):,} filas")
    # Filtrar SOLO desocupados (DSI == 1). 'No ocupados' tambien incluye inactivos.
    df_nocu = df_nocu[df_nocu['DSI'] == 1].copy()
    print(f"  Desocupados (DSI=1): {len(df_nocu):,} filas")
    
    cols = df_nocu.columns.tolist()
    dpto_col = 'DPTO' if 'DPTO' in cols else None
    if dpto_col:
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
        df_nocu['departamento'] = df_nocu[dpto_col].map(dpto_map)
    
    # Sexo
    sexo_col = next((c for c in cols if 'SEXO' in c.upper() or c == 'P6020'), None)
    if sexo_col:
        df_nocu['sexo'] = df_nocu[sexo_col]
    
    # Edad
    edad_col = next((c for c in cols if c == 'P6040'), None)
    if edad_col:
        df_nocu['edad'] = pd.to_numeric(df_nocu[edad_col], errors='coerce')
    
    # Factor de expansion para no ocupados
    fex_col_n = next((c for c in cols if c.upper() in ['FEX_C18', 'FEX_C_2011']), None)
    if fex_col_n:
        df_nocu['fex'] = pd.to_numeric(df_nocu[fex_col_n], errors='coerce').fillna(1)
    else:
        df_nocu['fex'] = 1
    
    # Desempleo por departamento con expansion
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
    
    desempleo.to_csv(PROCESSED / 'geih_desempleo_departamento.csv', index=False)
    print(f"  [OK] geih_desempleo_departamento.csv: {len(desempleo)} departamentos")
    print(f"  No ocupados expandidos nacionales: {desempleo['no_ocupados'].sum():,.0f}")

# ============================================================================
# 2. PILA
# ============================================================================
print("\n[2/9] Procesando PILA...")

pila_path = RAW / "pila_20260608.csv"
if pila_path.exists():
    df_pila = pd.read_csv(pila_path, encoding='utf-8', low_memory=False)
    print(f"  PILA: {len(df_pila):,} filas")
    
    # Agregar por actividad económica
    resumen_pila = df_pila.groupby('ActividadEconomicaDesc').agg(
        total_cotizantes=('NumeroCotizantes', 'sum'),
        total_cotizaciones=('NumeroCotizaciones', 'sum')
    ).reset_index().sort_values('total_cotizantes', ascending=False)
    
    resumen_pila.to_csv(PROCESSED / 'pila_resumen_sector.csv', index=False)
    print(f"  [OK] pila_resumen_sector.csv: {len(resumen_pila)} sectores")
    
    # También por tipo de cotizante
    resumen_tipo = df_pila.groupby('TipoCotizantePilaDesc').agg(
        total_cotizantes=('NumeroCotizantes', 'sum'),
        total_cotizaciones=('NumeroCotizaciones', 'sum')
    ).reset_index()
    
    resumen_tipo.to_csv(PROCESSED / 'pila_resumen_tipo.csv', index=False)
    print(f"  [OK] pila_resumen_tipo.csv")

# ============================================================================
# 3. SNIES
# ============================================================================
print("\n[3/9] Procesando SNIES...")

snies_path = RAW / "snies_matricula_20260608.csv"
if snies_path.exists():
    # El CSV original está en latin1; usamos fallback para evitar errores de encoding
    try:
        df_snies = pd.read_csv(snies_path, encoding='utf-8', low_memory=False)
    except UnicodeDecodeError:
        df_snies = pd.read_csv(snies_path, encoding='latin1', low_memory=False)
    print(f"  SNIES: {len(df_snies):,} filas")

    # Renombrar columnas con nombres más limpios
    df_snies.columns = [c.strip() for c in df_snies.columns]

    # Detectar columnas relevantes con flexibilidad de nombre
    mat_cols = [c for c in df_snies.columns if 'MATRI' in c.upper() or 'INSCRIP' in c.upper()]
    year_cols = [c for c in df_snies.columns if c.upper() in ('AÑO', 'ANO', 'A�O')]
    sem_cols = [c for c in df_snies.columns if 'SEMESTRE' in c.upper()]
    dpto_cols = [c for c in df_snies.columns if 'DEPARTAMENTO' in c.upper() and 'OFERTA' in c.upper()]
    print(f"  Columnas de matrícula detectadas: {mat_cols[:5]}")

    if mat_cols and dpto_cols:
        mat_col = mat_cols[0]
        dpto_col = dpto_cols[0]
        df_snies[mat_col] = pd.to_numeric(df_snies[mat_col], errors='coerce').fillna(0)

        # Tomar solo el año/semestre más reciente para evitar acumulados inflados
        if year_cols and sem_cols:
            year_col = year_cols[0]
            sem_col = sem_cols[0]
            latest_year = int(df_snies[year_col].max())
            latest_sem = int(df_snies[df_snies[year_col] == latest_year][sem_col].max())
            df_snies = df_snies[(df_snies[year_col] == latest_year) & (df_snies[sem_col] == latest_sem)].copy()
            print(f"  Filtrado a año/semestre más reciente: {latest_year}-{latest_sem} ({len(df_snies):,} filas)")

        # Normalizar nombres de departamento
        def _norm_depto_snies(name):
            import unicodedata
            if not isinstance(name, str):
                return name
            s = "".join(
                c for c in unicodedata.normalize("NFD", name.upper().strip())
                if unicodedata.category(c) != "Mn"
            )
            if "BOGOTA" in s or s == "BOGOTA":
                return "Bogotá"
            if (
                "SAN ANDRES" in s
                or "ARCHIPIELAGO" in s
                or "PROVIDENCIA" in s
                or "SANTA CATALINA" in s
            ):
                return "Archipiélago de San Andrés"
            if s == "GUAJIRA":
                return "La Guajira"
            if s == "NARINIO":
                return "Nariño"
            if s == "VALLE DEL CAUCA":
                return "Valle del Cauca"
            return name.strip().title()

        df_snies[dpto_col] = df_snies[dpto_col].apply(_norm_depto_snies)

        # Agregar por programa (último periodo)
        ies_col = next((c for c in df_snies.columns if 'IES' in c.upper() and 'INSTITUCIÓN' in c.upper()), None)
        prog_col = next((c for c in df_snies.columns if 'PROGRAMA' in c.upper()), None)
        nbc_col = next((c for c in df_snies.columns if 'NÚCLEO' in c.upper() or 'NUCLEO' in c.upper()), None)
        if ies_col and prog_col and nbc_col:
            resumen_programas = df_snies.groupby([ies_col, prog_col, dpto_col, nbc_col], as_index=False)[mat_col].sum()
            resumen_programas.columns = ['institucion', 'programa', 'departamento', 'nucleo_conocimiento', 'matriculados']
            resumen_programas.to_csv(PROCESSED / 'snies_programas_matriculados.csv', index=False)
            print(f"  [OK] snies_programas_matriculados.csv: {len(resumen_programas)} programas")

        # Resumen por departamento
        resumen_dpto = df_snies.groupby(dpto_col, as_index=False)[mat_col].sum()
        resumen_dpto.columns = ['departamento', 'matriculados']
        resumen_dpto.to_csv(PROCESSED / 'snies_matriculados_departamento.csv', index=False)
        print(f"  [OK] snies_matriculados_departamento.csv: {len(resumen_dpto)} departamentos")

# ============================================================================
# 4. SENA
# ============================================================================
print("\n[4/9] Procesando SENA...")

sena_path = RAW / "sena_programas_20260617.csv"
if sena_path.exists():
    df_sena = pd.read_csv(sena_path, encoding='utf-8', low_memory=False)
    print(f"  SENA: {len(df_sena):,} filas")
    
    # Limpiar columnas
    df_sena.columns = [c.strip() for c in df_sena.columns]
    
    # Seleccionar columnas útiles
    cols_sena = {
        'Nombre Programa': 'programa',
        'Departamento': 'departamento',
        'Área Desempeño': 'area_desempeno',
        'Tipo Certificado': 'tipo_certificado',
        'Escolaridad': 'escolaridad',
        'Costo': 'costo',
        'Duración Horas': 'duracion_horas',
        'Estado Programa': 'estado_programa',
        'Año Corte': 'anio_corte',
        'Nombre Institución': 'institucion'
    }
    
    # Mapear columnas existentes
    cols_existentes = {k: v for k, v in cols_sena.items() if k in df_sena.columns}
    df_sena_clean = df_sena[list(cols_existentes.keys())].rename(columns=cols_existentes)
    
    # Limpiar costo
    if 'costo' in df_sena_clean.columns:
        df_sena_clean['costo'] = df_sena_clean['costo'].astype(str).str.replace('.', '').str.replace(',', '.')
        df_sena_clean['costo'] = pd.to_numeric(df_sena_clean['costo'], errors='coerce')
    
    # Filtrar programas activos
    if 'estado_programa' in df_sena_clean.columns:
        activos = df_sena_clean[df_sena_clean['estado_programa'].str.contains('ACTIVO|REN|VIGENTE', case=False, na=False)]
    else:
        activos = df_sena_clean
    
    activos.to_csv(PROCESSED / 'sena_programas_activos.csv', index=False)
    print(f"  [OK] sena_programas_activos.csv: {len(activos)} programas activos")

# ============================================================================
# 5. Saber Pro
# ============================================================================
print("\n[5/9] Procesando Saber Pro...")

saber_path = RAW / "saberpro_20260608.csv"
if saber_path.exists():
    df_saber = pd.read_csv(saber_path, encoding='utf-8', low_memory=False)
    print(f"  Saber Pro: {len(df_saber):,} filas")
    
    df_saber.columns = [c.strip() for c in df_saber.columns]
    
    # Detectar columnas de puntaje
    puntaje_cols = [c for c in df_saber.columns if 'PUNT' in c.upper() or 'GLOBAL' in c.upper()]
    print(f"  Columnas de puntaje: {puntaje_cols[:10]}")
    
    if puntaje_cols:
        # Promedio por programa
        grupo_cols = ['INST_NOMBRE_INSTITUCION', 'ESTU_PRGM_ACADEMICO', 'ESTU_INST_DEPARTAMENTO']
        cols_disponibles = [c for c in grupo_cols if c in df_saber.columns]
        
        if cols_disponibles:
            for col in puntaje_cols:
                df_saber[col] = pd.to_numeric(df_saber[col], errors='coerce')
            
            agg_dict = {col: 'mean' for col in puntaje_cols}
            resumen_saber = df_saber.groupby(cols_disponibles, as_index=False).agg(agg_dict)
            resumen_saber.columns = ['institucion' if c == 'INST_NOMBRE_INSTITUCION' else 
                                     'programa' if c == 'ESTU_PRGM_ACADEMICO' else 
                                     'departamento' if c == 'ESTU_INST_DEPARTAMENTO' else c 
                                     for c in resumen_saber.columns]
            
            resumen_saber.to_csv(PROCESSED / 'saberpro_resumen_programas.csv', index=False)
            print(f"  [OK] saberpro_resumen_programas.csv: {len(resumen_saber)} programas")

# ============================================================================
# 6. RUES (por chunks, archivo grande)
# ============================================================================
print("\n[6/9] Procesando RUES (archivo grande, puede tardar)...")

rues_path = RAW / "rues_20260617.csv"
if rues_path.exists():
    print(f"  RUES: {rues_path.stat().st_size / 1024**3:.2f} GB")
    
    # Columnas que necesitamos
    usecols = [
        'codigo_camara', 'camara_comercio', 'cod_ciiu_act_econ_pri',
        'cod_ciiu_act_econ_sec', 'fecha_matricula', 'fecha_renovacion',
        'ultimo_ano_renovado', 'fecha_cancelacion', 'tipo_sociedad',
        'organizacion_juridica', 'estado_matricula', 'fecha_actualizacion'
    ]
    
    # Leer en chunks y filtrar activas
    chunk_size = 200_000
    chunks_filtrados = []
    total = 0
    activas = 0
    
    for i, chunk in enumerate(pd.read_csv(rues_path, encoding='latin-1', chunksize=chunk_size, low_memory=False)):
        total += len(chunk)
        # Filtrar activas: estado_matricula que no contenga CANCELADA ni DISUELTA ni LIQUIDADA
        mask = ~chunk['estado_matricula'].str.contains('CANCELADA|DISUELTA|LIQUIDADA|INACTIVA', case=False, na=False)
        activas_chunk = chunk[mask].copy()
        activas += len(activas_chunk)
        
        # Seleccionar solo columnas útiles
        cols_disp = [c for c in usecols if c in activas_chunk.columns]
        chunks_filtrados.append(activas_chunk[cols_disp])
        
        if (i + 1) % 5 == 0:
            print(f"    Procesados {(i+1)*chunk_size:,} registros. Activas acumuladas: {activas:,}")
    
    print(f"  Total registros: {total:,}. Activas: {activas:,}")
    
    # Concatenar y agregar
    df_rues = pd.concat(chunks_filtrados, ignore_index=True)
    
    # Convertir fechas
    df_rues['fecha_matricula'] = pd.to_datetime(df_rues['fecha_matricula'], errors='coerce', format='%Y%m%d')
    df_rues['anio_matricula'] = df_rues['fecha_matricula'].dt.year
    
    # Agregar por departamento (cámara = proxy de departamento) y CIIU
    df_rues['ciiu2'] = df_rues['cod_ciiu_act_econ_pri'].astype(str).str[:2]
    
    resumen_rues = df_rues.groupby(['camara_comercio', 'ciiu2']).size().reset_index(name='empresas_activas')
    resumen_rues.to_csv(PROCESSED / 'rues_resumen_camara_ciiu.csv', index=False)
    print(f"  [OK] rues_resumen_camara_ciiu.csv: {len(resumen_rues)} combinaciones")
    
    # Top sectores nacionales
    top_ciiu = df_rues.groupby('ciiu2').size().reset_index(name='empresas_activas').sort_values('empresas_activas', ascending=False)
    top_ciiu.to_csv(PROCESSED / 'rues_top_sectores_nacional.csv', index=False)
    print(f"  [OK] rues_top_sectores_nacional.csv")
    
    # Empresas nuevas por año
    nuevas = df_rues[df_rues['anio_matricula'] >= 2020].groupby(['anio_matricula', 'ciiu2']).size().reset_index(name='empresas_nuevas')
    nuevas.to_csv(PROCESSED / 'rues_empresas_nuevas.csv', index=False)
    print(f"  [OK] rues_empresas_nuevas.csv")

# ============================================================================
# 7. SPE - Servicio Público de Empleo (proxy: Agencia Pública de Empleo SENA)
# ============================================================================
print("\n[7/9] Procesando SPE (proxy: APE SENA)...")

spe_path = RAW / "spe_ape_inscritos_20260704.csv"
if spe_path.exists():
    df_spe = pd.read_csv(spe_path, encoding='utf-8', low_memory=False)
    print(f"  SPE/APE: {len(df_spe):,} ocupaciones")
    
    # Renombrar columnas a nombres limpios
    df_spe.columns = [c.strip() for c in df_spe.columns]
    df_spe_clean = df_spe.rename(columns={
        'ID': 'id_ocupacion',
        'Nombre de la ocupación': 'ocupacion',
        'Nivel': 'nivel',
        'Número de Inscritos 2019': 'inscritos_2019',
        'Número de Inscritos 2020': 'inscritos_2020',
        'Participacion (%)  2019': 'participacion_2019',
        'Participacion (%)  2020': 'participacion_2020',
        '% Variacion    2020  vs  2019': 'variacion_pct',
        'Contribución a la variación': 'contribucion_variacion'
    })
    
    # Convertir numéricas
    num_cols = ['inscritos_2019', 'inscritos_2020', 'participacion_2019',
                'participacion_2020', 'variacion_pct', 'contribucion_variacion']
    for col in num_cols:
        if col in df_spe_clean.columns:
            df_spe_clean[col] = pd.to_numeric(df_spe_clean[col], errors='coerce')
    
    df_spe_clean.to_csv(PROCESSED / 'spe_ape_inscritos_ocupacion.csv', index=False)
    print(f"  [OK] spe_ape_inscritos_ocupacion.csv")
    
    # Agregar por nivel
    resumen_nivel = df_spe_clean.groupby('nivel', as_index=False).agg(
        total_inscritos_2019=('inscritos_2019', 'sum'),
        total_inscritos_2020=('inscritos_2020', 'sum'),
        ocupaciones=('ocupacion', 'count')
    ).sort_values('total_inscritos_2020', ascending=False)
    
    resumen_nivel.to_csv(PROCESSED / 'spe_ape_inscritos_nivel.csv', index=False)
    print(f"  [OK] spe_ape_inscritos_nivel.csv")

# ============================================================================
# 8. OLE - Observatorio Laboral para la Educación (proxy: MEN ETDH)
# ============================================================================
print("\n[8/9] Procesando OLE (proxy: MEN Educación para el Trabajo)...")

ole_path = RAW / "ole_etdh_programas_20260704.csv"
if ole_path.exists():
    df_ole = pd.read_csv(ole_path, encoding='utf-8', low_memory=False)
    print(f"  OLE/ETDH: {len(df_ole):,} programas")
    
    df_ole.columns = [c.strip() for c in df_ole.columns]
    
    # Mapear columnas útiles
    cols_ole = {
        'Nombre Programa': 'programa',
        'Nombre Institución': 'institucion',
        'Departamento': 'departamento',
        'Municipio': 'municipio',
        'Área Desempeño': 'area_desempeno',
        'Tipo Certificado': 'tipo_certificado',
        'Escolaridad': 'escolaridad',
        'Costo': 'costo',
        'Duración Horas': 'duracion_horas',
        'Estado Programa': 'estado_programa',
    }
    
    cols_existentes = {k: v for k, v in cols_ole.items() if k in df_ole.columns}
    df_ole_clean = df_ole[list(cols_existentes.keys())].rename(columns=cols_existentes)
    
    # Limpiar costo
    if 'costo' in df_ole_clean.columns:
        df_ole_clean['costo'] = df_ole_clean['costo'].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        df_ole_clean['costo'] = pd.to_numeric(df_ole_clean['costo'], errors='coerce')
    
    # Limpiar duración
    if 'duracion_horas' in df_ole_clean.columns:
        df_ole_clean['duracion_horas'] = pd.to_numeric(df_ole_clean['duracion_horas'], errors='coerce')
    
    # Filtrar programas activos: en ETDH los registros son válidos si están en cualquiera de los estados oficiales
    estados_validos = ['REGISTRO POR PRIMERA VEZ', 'REGISTRO RENOVADO', 'REGISTRO MODIFICADO']
    if 'estado_programa' in df_ole_clean.columns:
        activos_ole = df_ole_clean[df_ole_clean['estado_programa'].isin(estados_validos)]
    else:
        activos_ole = df_ole_clean
    
    activos_ole.to_csv(PROCESSED / 'ole_etdh_programas_activos.csv', index=False)
    print(f"  [OK] ole_etdh_programas_activos.csv: {len(activos_ole)} programas")
    
    # Resumen por departamento y área
    if 'departamento' in activos_ole.columns and 'area_desempeno' in activos_ole.columns:
        resumen_ole = activos_ole.groupby(['departamento', 'area_desempeno'], as_index=False).agg(
            programas=('programa', 'count'),
            duracion_promedio_horas=('duracion_horas', 'mean'),
            costo_promedio=('costo', 'mean')
        ).sort_values('programas', ascending=False)
        
        resumen_ole.to_csv(PROCESSED / 'ole_etdh_resumen_departamento_area.csv', index=False)
        print(f"  [OK] ole_etdh_resumen_departamento_area.csv")

# ============================================================================
# 9. DNP - Medición del Desempeño Municipal
# ============================================================================
print("\n[9/9] Procesando DNP (Medición del Desempeño Municipal)...")

dnp_path = RAW / "dnp_medicion_desempeno_municipal_20260704.csv"
if dnp_path.exists():
    df_dnp = pd.read_csv(dnp_path, encoding='utf-8', low_memory=False)
    print(f"  DNP/MDM: {len(df_dnp):,} registros")
    
    df_dnp.columns = [c.strip() for c in df_dnp.columns]
    
    # Renombrar a nombres limpios
    df_dnp_clean = df_dnp.rename(columns={
        'Codigo_Unico': 'codigo_unico',
        'Indicador': 'indicador',
        'Codigo_Categoria': 'codigo_categoria',
        'Codigo_SubCategoria': 'codigo_subcategoria',
        'Codigo_Variable': 'codigo_variable',
        'Codigo_Departamento': 'codigo_departamento',
        'Departamento': 'departamento',
        'Codigo_Entidad': 'codigo_entidad',
        'Entidad': 'entidad',
        'Dato': 'dato',
        'Etiqueta': 'etiqueta',
        'Anio': 'anio',
        'Mes': 'mes'
    })
    
    # Convertir dato a numérico
    df_dnp_clean['dato'] = pd.to_numeric(df_dnp_clean['dato'], errors='coerce')
    
    # Guardar tabla limpia
    df_dnp_clean.to_csv(PROCESSED / 'dnp_medicion_desempeno_municipal.csv', index=False)
    print(f"  [OK] dnp_medicion_desempeno_municipal.csv")
    
    # Último dato por indicador y municipio
    ultimos = df_dnp_clean.sort_values(['codigo_unico', 'indicador', 'anio', 'mes']).drop_duplicates(
        subset=['codigo_unico', 'indicador'], keep='last'
    )
    ultimos.to_csv(PROCESSED / 'dnp_medicion_desempeno_ultimo.csv', index=False)
    print(f"  [OK] dnp_medicion_desempeno_ultimo.csv")
    
    # Ranking por departamento (promedio de indicadores numéricos)
    if 'departamento' in df_dnp_clean.columns:
        resumen_dpto = df_dnp_clean.groupby('departamento', as_index=False)['dato'].mean().rename(
            columns={'dato': 'promedio_desempeno'}
        ).sort_values('promedio_desempeno', ascending=False)
        
        resumen_dpto.to_csv(PROCESSED / 'dnp_desempeno_departamento.csv', index=False)
        print(f"  [OK] dnp_desempeno_departamento.csv")

print(f"\n[{datetime.now()}] ETL finalizado")
print(f"Archivos generados en {PROCESSED}:")
for f in sorted(PROCESSED.iterdir()):
    if f.is_file():
        print(f"  - {f.name} ({f.stat().st_size / 1024:.1f} KB)")
