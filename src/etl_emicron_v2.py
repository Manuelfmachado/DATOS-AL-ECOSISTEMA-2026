"""
ETL ALBA - EMICRON v2 (Encuesta de Micronegocios DANE).
Corrige el bug del ETL v1: usa GRUPOS12 (13 sectores) del modulo Identificacion
en lugar de P1633 (que era una pregunta binaria con solo 2 valores).

Agrega 3 modulos nuevos no usados antes:
- Costos_Gastos: costo mensual de operacion por sector
- Sitio_Ubicacion: tipo de local (casa, local fijo, ambulante, vehiculo...)
- Personal_Propietario: perfil del emprendedor (sexo, edad, educacion)

Anios con GRUPOS12: 2022, 2023, 2024 (2021 no tiene GRUPOS12).

Tablas generadas (data/processed/):
1. emicron_por_sector_v2.csv        - micronegocios, ingreso, % credito, % internet por GRUPOS12 x ano
2. emicron_costos_sector.csv        - costo mediano de operacion por sector x ano
3. emicron_ubicacion_sector.csv     - distribucion de tipos de local por sector x ano
4. emicron_perfil_propietario.csv   - perfil del emprendedor por sector (sexo, educacion)
5. emicron_resumen_nacional_v2.csv  - KPIs nacionales con sector real
6. emicron_por_departamento_v2.csv  - micronegocios por depto (conserva 2021 sin sector)

Sirve a 4 modulos:
- Observatorio: estructura del empleo informal por sector
- Prediccion: tendencia de creacion de microempresas
- Emprende IA: costos, tipos de local, perfil del emprendedor
- Simulacion: empleo informal en el ranking de oportunidades (complementa PILA)
"""
import pandas as pd
import numpy as np
import zipfile
import io
import os
import warnings

warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMICRON_DIR = os.path.join(BASE, 'EMICRON_DANE')
PROCESSED = os.path.join(BASE, 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)

# GRUPOS12 solo existe 2022-2024 (2021 no tiene el campo)
ANOS_CON_SECTOR = [2022, 2023, 2024]
ANOS_TODOS = [2021, 2022, 2023, 2024]

GRUPOS12_NOMBRES = {
    1: "Agricultura, ganaderia, caza y silvicultura",
    2: "Explotacion de minas y canteras",
    3: "Industria manufacturera",
    4: "Suministro de electricidad, gas y agua",
    5: "Construccion",
    6: "Comercio al por mayor",
    7: "Comercio al por menor",
    8: "Transporte y almacenamiento",
    9: "Alojamiento y servicios de comida",
    10: "Informacion y comunicaciones",
    11: "Actividades financieras y de seguros",
    12: "Actividades profesionales y servicios",
    13: "Otros servicios",
}

P3053_TIPO_LOCAL = {
    1: "Local fijo independiente",
    2: "Local en centro comercial",
    3: "Dentro de la vivienda",
    4: "Vivienda con adaptacion",
    5: "Kiosko o puesto movil",
    6: "Vehiculo",
    7: "Sin local fijo (ambulante)",
    8: "Otro",
}


def leer_modulo(modulo, ano):
    """Lee el CSV de un modulo de EMICRON desde el ZIP."""
    fname = f'{ano}_{modulo}.zip'
    path = os.path.join(EMICRON_DIR, fname)
    if not os.path.exists(path):
        return pd.DataFrame()
    with zipfile.ZipFile(path, 'r') as zf:
        csv_name = [f for f in zf.namelist() if f.endswith('.csv')][0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(io.BytesIO(f.read()), encoding='latin1', low_memory=False)
    df['ANO'] = ano
    return df


def to_num(s):
    if isinstance(s, (int, float)):
        return s
    return pd.to_numeric(s, errors='coerce').fillna(0)


def mediana_ponderada(valores, pesos):
    """Mediana ponderada: el valor donde se acumula el 50% del peso."""
    if len(valores) == 0:
        return np.nan
    orden = np.argsort(valores)
    v = valores[orden]
    p = pesos[orden]
    cum = np.cumsum(p)
    total = cum[-1]
    idx = np.searchsorted(cum, total / 2)
    return v[min(idx, len(v) - 1)]


def guardar(df_list, name):
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
        path = os.path.join(PROCESSED, name)
        df.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  [OK] {name}: {len(df)} filas, {os.path.getsize(path)/1024:.0f} KB')
    else:
        print(f'  [SKIP] {name}: sin datos')


def main():
    print('ETL EMICRON v2 - Corregido con GRUPOS12 + modulos nuevos')
    print('=' * 70)

    resumen_nacional = []
    por_sector = []
    costos_sector = []
    ubicacion_sector = []
    perfil_propietario = []
    por_departamento = []

    for ano in ANOS_TODOS:
        print(f'\n--- Procesando {ano} ---')

        # === Modulo Identificacion (tiene GRUPOS12 y F_EXP) ===
        ident = leer_modulo('Identificacion', ano)
        if ident.empty:
            print(f'  [SKIP] Sin Identificacion')
            continue
        if 'F_EXP' not in ident.columns:
            ident['F_EXP'] = 1.0
        else:
            ident['F_EXP'] = pd.to_numeric(ident['F_EXP'], errors='coerce').fillna(1)
        if 'COD_DEPTO' not in ident.columns:
            ident['COD_DEPTO'] = 0
        else:
            ident['COD_DEPTO'] = pd.to_numeric(ident['COD_DEPTO'], errors='coerce').fillna(0)
        tiene_grupos12 = 'GRUPOS12' in ident.columns
        print(f'  Identificacion: {len(ident)} filas, GRUPOS12={tiene_grupos12}')

        # Merge keys
        merge_keys = [c for c in ['DIRECTORIO', 'SECUENCIA_P', 'SECUENCIA_ENCUESTA']
                      if c in ident.columns]
        total_mn = ident['F_EXP'].sum()
        print(f'  Total micronegocios (expandidos): {total_mn/1e6:.2f}M')

        # Resumen nacional
        resumen = {'ano': ano, 'total_micronegocios': int(total_mn)}

        # Por departamento (todos los anos, sin necesitar GRUPOS12)
        depto_agg = ident.groupby('COD_DEPTO')['F_EXP'].sum().reset_index()
        depto_agg.columns = ['dpto', 'micronegocios']
        depto_agg['ano'] = ano
        por_departamento.append(depto_agg)

        # === Solo procesar sector si hay GRUPOS12 ===
        if not tiene_grupos12:
            print(f'  [SKIP] Sin GRUPOS12 en {ano}, omitiendo sectorial')
            resumen_nacional.append(resumen)
            continue

        ident['GRUPOS12'] = to_num(ident['GRUPOS12'])

        # Por sector (GRUPOS12)
        sec_agg = ident.groupby('GRUPOS12')['F_EXP'].sum().reset_index()
        sec_agg.columns = ['grupos12', 'micronegocios']
        sec_agg['ano'] = ano
        sec_agg['sector'] = sec_agg['grupos12'].map(GRUPOS12_NOMBRES)
        por_sector.append(sec_agg)

        # === Modulo Ventas/Ingresos (ingreso promedio por sector) ===
        ventas = leer_modulo('Ventas_Ingresos', ano)
        if not ventas.empty and 'INGRESO_MIXTO' in ventas.columns:
            ventas['F_EXP'] = to_num(ventas.get('F_EXP', 1))
            ventas['INGRESO_MIXTO'] = to_num(ventas['INGRESO_MIXTO'])
            if merge_keys:
                merged = ventas.merge(ident[merge_keys + ['GRUPOS12']], on=merge_keys, how='left')
                valid = merged[(merged['INGRESO_MIXTO'] > 0) & (merged['GRUPOS12'] > 0)]
                if len(valid) > 0:
                    # Ingreso promedio ponderado por sector
                    ing_sec = valid.groupby('GRUPOS12').apply(
                        lambda g: (g['INGRESO_MIXTO'] * g['F_EXP']).sum() / g['F_EXP'].sum()
                        if g['F_EXP'].sum() > 0 else np.nan
                    ).reset_index()
                    ing_sec.columns = ['grupos12', 'ingreso_promedio']
                    ing_sec['ingreso_promedio'] = ing_sec['ingreso_promedio'].round(0)
                    ing_sec['ano'] = ano
                    sec_agg = sec_agg.merge(ing_sec[['grupos12', 'ingreso_promedio', 'ano']],
                                             on=['grupos12', 'ano'], how='left')
                    # Ingreso promedio nacional
                    ing_nac = (valid['INGRESO_MIXTO'] * valid['F_EXP']).sum() / valid['F_EXP'].sum()
                    resumen['ingreso_promedio_mensual'] = int(ing_nac)
                    print(f'  Ingreso promedio nacional: ${ing_nac:,.0f}')

        # === Modulo TIC (% usa internet) ===
        tic = leer_modulo('TIC', ano)
        if not tic.empty:
            tic['F_EXP'] = to_num(tic.get('F_EXP', 1))
            tic['P4001'] = to_num(tic.get('P4001', np.nan))
            usa_internet = tic[tic['P4001'] == 1]['F_EXP'].sum()
            total_tic = tic['F_EXP'].sum()
            pct_internet = (usa_internet / total_tic * 100) if total_tic > 0 else np.nan
            resumen['pct_usa_internet'] = round(pct_internet, 1)
            print(f'  % usa internet: {pct_internet:.1f}%')
            # Por sector
            if merge_keys:
                merged_tic = tic.merge(ident[merge_keys + ['GRUPOS12']], on=merge_keys, how='left')
                valid_tic = merged_tic[merged_tic['GRUPOS12'] > 0]
                if len(valid_tic) > 0:
                    tic_sec = valid_tic.groupby('GRUPOS12').apply(
                        lambda g: (g[g['P4001'] == 1]['F_EXP'].sum() / g['F_EXP'].sum() * 100)
                        if g['F_EXP'].sum() > 0 else np.nan
                    ).reset_index()
                    tic_sec.columns = ['grupos12', 'pct_usa_internet']
                    tic_sec['pct_usa_internet'] = tic_sec['pct_usa_internet'].round(1)
                    tic_sec['ano'] = ano
                    sec_agg = sec_agg.merge(tic_sec[['grupos12', 'pct_usa_internet', 'ano']],
                                             on=['grupos12', 'ano'], how='left')

        # === Modulo Inclusion Financiera (% tiene credito por sector) ===
        fin = leer_modulo('Inclusion_Financiera', ano)
        if not fin.empty:
            fin['F_EXP'] = to_num(fin.get('F_EXP', 1))
            fin['P1567'] = to_num(fin.get('P1567', np.nan))
            tiene_credito = fin[fin['P1567'] == 1]['F_EXP'].sum()
            total_fin = fin['F_EXP'].sum()
            pct_credito = (tiene_credito / total_fin * 100) if total_fin > 0 else np.nan
            resumen['pct_tiene_credito'] = round(pct_credito, 1)
            print(f'  % tiene credito: {pct_credito:.1f}%')
            # Por sector
            if merge_keys:
                merged_fin = fin.merge(ident[merge_keys + ['GRUPOS12']], on=merge_keys, how='left')
                valid_fin = merged_fin[merged_fin['GRUPOS12'] > 0]
                if len(valid_fin) > 0:
                    fin_sec = valid_fin.groupby('GRUPOS12').apply(
                        lambda g: (g[g['P1567'] == 1]['F_EXP'].sum() / g['F_EXP'].sum() * 100)
                        if g['F_EXP'].sum() > 0 else np.nan
                    ).reset_index()
                    fin_sec.columns = ['grupos12', 'pct_tiene_credito']
                    fin_sec['pct_tiene_credito'] = fin_sec['pct_tiene_credito'].round(1)
                    fin_sec['ano'] = ano
                    sec_agg = sec_agg.merge(fin_sec[['grupos12', 'pct_tiene_credito', 'ano']],
                                             on=['grupos12', 'ano'], how='left')

        # === NUEVO: Modulo Costos_Gastos ===
        costos = leer_modulo('Costos_Gastos', ano)
        if not costos.empty and 'COSTOS_MES_ANTERIOR' in costos.columns and merge_keys:
            costos['F_EXP'] = to_num(costos.get('F_EXP', 1))
            costos['COSTOS_MES_ANTERIOR'] = to_num(costos['COSTOS_MES_ANTERIOR'])
            costos['CONSUMO_INTERMEDIO'] = to_num(costos.get('CONSUMO_INTERMEDIO', 0))
            merged_cos = costos.merge(ident[merge_keys + ['GRUPOS12']], on=merge_keys, how='left')
            valid_cos = merged_cos[(merged_cos['COSTOS_MES_ANTERIOR'] > 0) & (merged_cos['GRUPOS12'] > 0)]
            if len(valid_cos) > 0:
                cost_sec = valid_cos.groupby('GRUPOS12').apply(
                    lambda g: mediana_ponderada(
                        g['COSTOS_MES_ANTERIOR'].values,
                        g['F_EXP'].values
                    )
                ).reset_index()
                cost_sec.columns = ['grupos12', 'costo_mediano_mensual']
                cost_sec['costo_mediano_mensual'] = cost_sec['costo_mediano_mensual'].round(0)
                cost_sec['ano'] = ano
                # Consumo intermedio (materia prima)
                ci_sec = valid_cos.groupby('GRUPOS12').apply(
                    lambda g: mediana_ponderada(
                        g['CONSUMO_INTERMEDIO'].values,
                        g['F_EXP'].values
                    ) if g['CONSUMO_INTERMEDIO'].sum() > 0 else np.nan
                ).reset_index()
                ci_sec.columns = ['grupos12', 'consumo_intermedio_mediano']
                ci_sec['consumo_intermedio_mediano'] = ci_sec['consumo_intermedio_mediano'].round(0)
                ci_sec['ano'] = ano
                cost_sec = cost_sec.merge(ci_sec, on=['grupos12', 'ano'], how='left')
                cost_sec['sector'] = cost_sec['grupos12'].map(GRUPOS12_NOMBRES)
                costos_sector.append(cost_sec)
                print(f'  Costos: {len(cost_sec)} sectores, costo mediano nacional '
                      f'${mediana_ponderada(valid_cos["COSTOS_MES_ANTERIOR"].values, valid_cos["F_EXP"].values):,.0f}')

        # === NUEVO: Modulo Sitio_Ubicacion (tipo de local) ===
        sitio = leer_modulo('Sitio_Ubicacion', ano)
        if not sitio.empty and 'P3053' in sitio.columns and merge_keys:
            sitio['F_EXP'] = to_num(sitio.get('F_EXP', 1))
            sitio['P3053'] = to_num(sitio['P3053'])
            merged_sit = sitio.merge(ident[merge_keys + ['GRUPOS12']], on=merge_keys, how='left')
            valid_sit = merged_sit[merged_sit['GRUPOS12'] > 0]
            if len(valid_sit) > 0:
                # Distribucion de tipos de local por sector
                cross = valid_sit.groupby(['GRUPOS12', 'P3053'])['F_EXP'].sum().reset_index()
                total_por_sector = cross.groupby('GRUPOS12')['F_EXP'].sum()
                cross['pct'] = cross.apply(
                    lambda r: round(r['F_EXP'] / total_por_sector[r['GRUPOS12']] * 100, 1)
                    if total_por_sector[r['GRUPOS12']] > 0 else 0, axis=1
                )
                cross['tipo_local'] = cross['P3053'].astype(int).map(P3053_TIPO_LOCAL)
                cross['sector'] = cross['GRUPOS12'].map(GRUPOS12_NOMBRES)
                cross['ano'] = ano
                cross = cross.rename(columns={'GRUPOS12': 'grupos12'})
                ubicacion_sector.append(cross[['grupos12', 'sector', 'P3053', 'tipo_local',
                                               'F_EXP', 'pct', 'ano']])
                print(f'  Ubicacion: {len(cross)} combinaciones sector x tipo_local')

        # === NUEVO: Modulo Personal_Propietario (perfil del emprendedor) ===
        # NOTA: P3088 no es sexo (89% valor=2 es sospechoso) y P3091 tiene 15 valores
        # (no 5 como se asumio). El diccionario DANE 2024 difiere del v1.
        # Se omite hasta mapear correctamente los campos con el diccionario oficial.
        # prop = leer_modulo('Personal_Propietario', ano)

        # === Modulo Personal Ocupado (empleo generado) ===
        personal = leer_modulo('Personal_Ocupado', ano)
        if not personal.empty:
            personal['F_EXP'] = to_num(personal.get('F_EXP', 1))
            empleo_total = personal['F_EXP'].sum()
            resumen['empleo_generado'] = int(empleo_total)
            print(f'  Empleo generado: {empleo_total/1e6:.1f}M')

        # === Modulo Emprendimiento (motivos) - se conserva del v1 ===
        # Ya procesado por etl_emicron.py v1, no duplicar

        # Actualizar por_sector con los enriquecimientos
        # Reemplazar la entrada anterior de por_sector con la enriquecida
        if por_sector and por_sector[-1]['ano'].iloc[0] == ano:
            por_sector[-1] = sec_agg
        else:
            por_sector.append(sec_agg)

        resumen_nacional.append(resumen)

    # === Guardar tablas ===
    print('\n' + '=' * 70)
    print('Guardando tablas...')

    # 1. Resumen nacional
    if resumen_nacional:
        df_res = pd.DataFrame(resumen_nacional)
        path = os.path.join(PROCESSED, 'emicron_resumen_nacional_v2.csv')
        df_res.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  [OK] emicron_resumen_nacional_v2.csv: {len(df_res)} filas')
        print(f'       {df_res.to_string()}')

    # 2. Por sector (GRUPOS12) - la tabla corregida
    guardar(por_sector, 'emicron_por_sector_v2.csv')

    # 3. Costos por sector
    guardar(costos_sector, 'emicron_costos_sector.csv')

    # 4. Ubicacion por sector
    guardar(ubicacion_sector, 'emicron_ubicacion_sector.csv')

    # 5. Perfil del propietario
    guardar(perfil_propietario, 'emicron_perfil_propietario.csv')

    # 6. Por departamento (conserva 2021 sin sector)
    guardar(por_departamento, 'emicron_por_departamento_v2.csv')

    print('\nETL EMICRON v2 completado.')


if __name__ == '__main__':
    main()