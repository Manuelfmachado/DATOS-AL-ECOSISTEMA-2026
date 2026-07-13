"""
ETL ALBA - EMICRON: Encuesta de Micronegocios (DANE)
Procesa 4 anos (2021-2024) de EMICRON y genera tablas agregadas para Emprende IA.

Tablas generadas:
1. emicron_resumen_nacional.csv      - KPIs nacionales por ano (micronegocios, ingresos, empleo)
2. emicron_por_sector.csv            - Caracteristicas por sector CIIU (ingresos, empleo, TIC)
3. emicron_emprendimiento.csv        - Motivos de emprendimiento, financiamiento, antiguedad
4. emicron_por_departamento.csv      - Micronegocios por departamento
5. emicron_inclusion_financiera.csv  - Acceso a credito, cuentas, ahorro por sector

Columnas clave por modulo (decifradas del diccionario DANE):
- Emprendimiento: P3050 (motivo), P3051 (fuente financiamiento), P639 (primera empresa), P3052 (tiempo funcionamiento)
- Caracteristicas: P1633 (actividad CIIU), P986 (tipo de local), P640 (sector), P4000 (registro RUT)
- Ventas: INGRESO_MIXTO, VALOR_AGREGADO, VENTAS_MES_ANTERIOR
- Personal Ocupado: P3077 (sexo), P3079 (edad), P3080 (tipo contrato)
- TIC: P4001 (usa internet), P977 (tiene computador), P1087 (usa redes sociales)
- Inclusion Financiera: P1764 (tiene cuenta), P1567 (tiene credito), P1572 (ahorro)
- Factores: FEX_C (factor de expansion)
"""
import pandas as pd
import numpy as np
import zipfile
import io
import os
import time
import warnings

warnings.filterwarnings('ignore')

BASE = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026'
EMICRON_DIR = os.path.join(BASE, 'EMICRON_DANE')
PROCESSED = os.path.join(BASE, 'data', 'processed')
os.makedirs(PROCESSED, exist_ok=True)

ANOS = [2021, 2022, 2023, 2024]


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


def leer_factores(ano):
    """Lee el factor de expansion departamental."""
    fname = f'{ano}_Factores_Departamental.zip'
    path = os.path.join(EMICRON_DIR, fname)
    if not os.path.exists(path):
        return pd.DataFrame()
    with zipfile.ZipFile(path, 'r') as zf:
        csv_name = [f for f in zf.namelist() if f.endswith('.csv')][0]
        with zf.open(csv_name) as f:
            df = pd.read_csv(io.BytesIO(f.read()), encoding='latin1', low_memory=False)
    return df


def to_num(s):
    return pd.to_numeric(s, errors='coerce')


def main():
    print('ETL EMICRON - Procesando 4 anos (2021-2024)...')
    print('=' * 70)

    resumen_nacional = []
    por_sector = []
    emprendimiento_data = []
    por_departamento = []
    inclusion_financiera = []

    for ano in ANOS:
        print(f'\n--- Procesando {ano} ---')

        # Leer factores de expansion
        factores = leer_factores(ano)
        if factores.empty:
            print(f'  [SKIP] Sin factores de expansion')
            continue
        print(f'  Factores: {len(factores)} filas')

        # Leer modulo emprendimiento
        emp = leer_modulo('Emprendimiento', ano)
        if not emp.empty:
            emp['F_EXP'] = to_num(emp.get('F_EXP', 1))
            emp['COD_DEPTO'] = to_num(emp.get('COD_DEPTO', 0))
            emp['P3050'] = to_num(emp.get('P3050', np.nan))
            emp['P3051'] = to_num(emp.get('P3051', np.nan))
            emp['P639'] = to_num(emp.get('P639', np.nan))
            emp['P3052'] = to_num(emp.get('P3052', np.nan))
            total_mn = emp['F_EXP'].sum()
            print(f'  Emprendimiento: {len(emp)} filas, {total_mn/1e3:.0f}K micronegocios (expandidos)')

            # Resumen nacional
            resumen_nacional.append({
                'ano': ano,
                'total_micronegocios': int(total_mn),
            })

            # Motivo de emprendimiento (P3050)
            # 1=Perdida o cierre de empleo anterior, 2=Oportunidad de negocio, 3=Dificultad para conseguir empleo, 4=Tradicion familiar, 9=Otro
            motivos = emp.groupby('P3050')['F_EXP'].sum().reset_index()
            motivos.columns = ['codigo_motivo', 'micronegocios']
            motivos['ano'] = ano
            emprendimiento_data.append(motivos)

        # Leer modulo caracteristicas
        carac = leer_modulo('Caracteristicas', ano)
        if not carac.empty:
            carac['F_EXP'] = to_num(carac.get('F_EXP', 1))
            carac['COD_DEPTO'] = to_num(carac.get('COD_DEPTO', 0))
            carac['P1633'] = to_num(carac.get('P1633', np.nan))  # Actividad CIIU
            carac['P640'] = to_num(carac.get('P640', np.nan))  # Sector

            # Llaves de merge disponibles
            merge_keys = [c for c in ['DIRECTORIO', 'SECUENCIA_P', 'SECUENCIA_ENCUESTA'] if c in carac.columns]

            # Por sector CIIU (P1633 = codigo de 4 digitos)
            if 'P1633' in carac.columns:
                sector_agg = carac.groupby('P1633').agg({
                    'F_EXP': 'sum',
                }).reset_index()
                sector_agg.columns = ['ciiu', 'micronegocios']
                sector_agg['ano'] = ano

                # Por departamento
                depto_agg = carac.groupby('COD_DEPTO')['F_EXP'].sum().reset_index()
                depto_agg.columns = ['dpto', 'micronegocios']
                depto_agg['ano'] = ano
                por_departamento.append(depto_agg)

        # Leer modulo ventas/ingresos
        ventas = leer_modulo('Ventas_Ingresos', ano)
        if not ventas.empty and 'INGRESO_MIXTO' in ventas.columns:
            ventas['F_EXP'] = to_num(ventas.get('F_EXP', 1))
            ventas['INGRESO_MIXTO'] = to_num(ventas['INGRESO_MIXTO'])
            ventas['COD_DEPTO'] = to_num(ventas.get('COD_DEPTO', 0))
            # Ingreso promedio nacional ponderado
            valid = ventas[ventas['INGRESO_MIXTO'] > 0]
            if len(valid) > 0:
                ingreso_prom = (valid['INGRESO_MIXTO'] * valid['F_EXP']).sum() / valid['F_EXP'].sum()
                if resumen_nacional and resumen_nacional[-1]['ano'] == ano:
                    resumen_nacional[-1]['ingreso_promedio_mensual'] = int(ingreso_prom)
                print(f'  Ingreso mixto promedio: ${ingreso_prom:,.0f}')

            # Por sector
            if not carac.empty and 'P1633' in carac.columns and merge_keys:
                merged = ventas.merge(carac[merge_keys + ['P1633']], on=merge_keys, how='left')
                merged = merged[merged['INGRESO_MIXTO'] > 0]
                if len(merged) > 0:
                    sector_ing = merged.groupby('P1633').apply(
                        lambda g: (g['INGRESO_MIXTO'] * g['F_EXP']).sum() / g['F_EXP'].sum()
                        if g['F_EXP'].sum() > 0 else np.nan
                    ).reset_index()
                    sector_ing.columns = ['ciiu', 'ingreso_promedio']
                    sector_ing['ingreso_promedio'] = sector_ing['ingreso_promedio'].round(0)
                    sector_agg = sector_agg.merge(sector_ing, on='ciiu', how='left')
            por_sector.append(sector_agg)

        # Leer modulo TIC
        tic = leer_modulo('TIC', ano)
        if not tic.empty:
            tic['F_EXP'] = to_num(tic.get('F_EXP', 1))
            tic['P4001'] = to_num(tic.get('P4001', np.nan))  # Usa internet
            # % que usa internet (1=Si)
            usa_internet = tic[tic['P4001'] == 1]['F_EXP'].sum()
            total_tic = tic['F_EXP'].sum()
            pct_internet = (usa_internet / total_tic * 100) if total_tic > 0 else np.nan
            if resumen_nacional and resumen_nacional[-1]['ano'] == ano:
                resumen_nacional[-1]['pct_usa_internet'] = round(pct_internet, 1)
            print(f'  % usa internet: {pct_internet:.1f}%')

        # Leer modulo inclusion financiera
        fin = leer_modulo('Inclusion_Financiera', ano)
        if not fin.empty:
            fin['F_EXP'] = to_num(fin.get('F_EXP', 1))
            fin['P1567'] = to_num(fin.get('P1567', np.nan))  # Tiene credito
            fin['P1764_1'] = to_num(fin.get('P1764_1', np.nan))  # Tiene cuenta corriente
            fin['P1764_2'] = to_num(fin.get('P1764_2', np.nan))  # Tiene cuenta ahorros
            tiene_credito = fin[fin['P1567'] == 1]['F_EXP'].sum()
            total_fin = fin['F_EXP'].sum()
            pct_credito = (tiene_credito / total_fin * 100) if total_fin > 0 else np.nan
            if resumen_nacional and resumen_nacional[-1]['ano'] == ano:
                resumen_nacional[-1]['pct_tiene_credito'] = round(pct_credito, 1)
            print(f'  % tiene credito: {pct_credito:.1f}%')

            # Por sector (merge con caracteristicas)
            if not carac.empty and 'P1633' in carac.columns and merge_keys:
                merged_fin = fin.merge(carac[merge_keys + ['P1633']], on=merge_keys, how='left')
                merged_fin['P1567'] = to_num(merged_fin.get('P1567', np.nan))
                fin_sector = merged_fin.groupby('P1633').apply(
                    lambda g: (g[g['P1567'] == 1]['F_EXP'].sum() / g['F_EXP'].sum() * 100)
                    if g['F_EXP'].sum() > 0 else np.nan
                ).reset_index()
                fin_sector.columns = ['ciiu', 'pct_credito']
                fin_sector['pct_credito'] = fin_sector['pct_credito'].round(1)
                fin_sector['ano'] = ano
                inclusion_financiera.append(fin_sector)

        # Leer modulo personal ocupado
        personal = leer_modulo('Personal_Ocupado', ano)
        if not personal.empty:
            personal['F_EXP'] = to_num(personal.get('F_EXP', 1))
            # Empleo total generado por micronegocios
            empleo_total = personal['F_EXP'].sum()
            if resumen_nacional and resumen_nacional[-1]['ano'] == ano:
                resumen_nacional[-1]['empleo_generado'] = int(empleo_total)
            print(f'  Empleo generado: {empleo_total/1e6:.1f}M')

    # Guardar tablas
    print('\n' + '=' * 70)
    print('Guardando tablas...')

    def guardar(df_list, name):
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            path = os.path.join(PROCESSED, name)
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f'  [OK] {name}: {len(df)} filas, {os.path.getsize(path)/1024:.0f} KB')
        else:
            print(f'  [FAIL] {name}: sin datos')

    if resumen_nacional:
        df_resumen = pd.DataFrame(resumen_nacional)
        path = os.path.join(PROCESSED, 'emicron_resumen_nacional.csv')
        df_resumen.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'  [OK] emicron_resumen_nacional.csv: {len(df_resumen)} filas')
        print(f'       {df_resumen.to_string()}')

    guardar(por_sector, 'emicron_por_sector.csv')
    guardar(emprendimiento_data, 'emicron_emprendimiento.csv')
    guardar(por_departamento, 'emicron_por_departamento.csv')
    guardar(inclusion_financiera, 'emicron_inclusion_financiera.csv')

    print('\nETL EMICRON completado.')


if __name__ == '__main__':
    main()