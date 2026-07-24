"""
ETL ALBA - Paso 1: Procesar GEIH y generar tablas agregadas
Lee los 52 meses de CSV de GEIH (Ocupados, Fuerza de trabajo, Caracteristicas)
y genera tablas agregadas en data/processed/ para alimentar los 5 modulos de ALBA.

Tablas generadas:
1. geih_desempleo_mensual.csv      - Tasa de desempleo nacional y por depto (52 meses x 33 deptos)
2. geih_empleo_sector_mensual.csv  - Empleo por sector CIIU (52 meses x ~20 sectores)
3. geih_salario_ocupacion.csv      - Salario promedio/mediano por ocupacion (ultima foto)
4. geih_salario_sector_mensual.csv - Salario promedio por sector (52 meses x sectores)
5. geih_informalidad_mensual.csv   - Tasa de informalidad nacional y por depto
6. geih_empleo_depto_sector.csv    - Matriz empleo por depto x sector (mapa de calor)
7. geih_empleo_nivel_educativo.csv - Empleo por nivel educativo (ultima foto)
8. geih_resumen_nacional.csv       - KPIs nacionales mensuales (52 filas)
"""
import pandas as pd
import numpy as np
import os
import time
import warnings

warnings.filterwarnings('ignore')

RAW = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\data\raw\geih'
PROCESSED = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\data\processed'

os.makedirs(PROCESSED, exist_ok=True)


def leer_csv_geih(path, usecols=None):
    """Lee un CSV de GEIH con encoding latin1 y separador ;."""
    try:
        df = pd.read_csv(path, sep=';', encoding='latin1', usecols=usecols, low_memory=False)
        return df
    except Exception as e:
        print(f'  Error leyendo {os.path.basename(path)}: {e}')
        return pd.DataFrame()


def procesar_mes(carpeta_mes, ano, mes):
    """Procesa un mes de GEIH y devuelve datos agregados."""
    periodo = f'{ano}-{mes:02d}'
    resultado = {'periodo': periodo, 'ano': ano, 'mes': mes}

    # --- 1. FUERZA DE TRABAJO (desempleo) ---
    ft_path = os.path.join(carpeta_mes, 'Fuerza de trabajo.csv')
    if os.path.exists(ft_path):
        ft = leer_csv_geih(ft_path, usecols=['DPTO', 'P6240', 'FEX_C18'])
        if not ft.empty:
            ft = ft.dropna(subset=['FEX_C18'])
            ft['FEX_C18'] = pd.to_numeric(ft['FEX_C18'], errors='coerce')
            ft = ft.dropna(subset=['FEX_C18'])
            ft['P6240'] = pd.to_numeric(ft['P6240'], errors='coerce')

            # P6240: 1=Trabajando, 2=Buscando trabajo, 3=Estudiando, 4=Oficios del hogar, 5=Incapacitado, 6=Otra
            # Poblacion Economicamente Activa (PEA) = P6240 in [1, 2]
            pea = ft[ft['P6240'].isin([1, 2])]
            desempleados = ft[ft['P6240'] == 2]

            # Nacional
            pea_nacional = pea['FEX_C18'].sum()
            desempleo_nacional = desempleados['FEX_C18'].sum()
            tasa_nacional = (desempleo_nacional / pea_nacional * 100) if pea_nacional > 0 else np.nan
            resultado['pea_nacional'] = pea_nacional
            resultado['desempleados_nacional'] = desempleo_nacional
            resultado['tasa_desempleo_nacional'] = round(tasa_nacional, 2) if not np.isnan(tasa_nacional) else np.nan

            # Por departamento
            deptos = ft.groupby('DPTO').apply(lambda g: {
                'pea': g[g['P6240'].isin([1, 2])]['FEX_C18'].sum(),
                'desempleados': g[g['P6240'] == 2]['FEX_C18'].sum(),
            }).apply(pd.Series)
            deptos['tasa'] = (deptos['desempleados'] / deptos['pea'] * 100).round(2)
            deptos = deptos.reset_index()
            deptos['periodo'] = periodo
            deptos['ano'] = ano
            deptos['mes'] = mes
            resultado['_desempleo_depto'] = deptos[['periodo', 'ano', 'mes', 'DPTO', 'pea', 'desempleados', 'tasa']]

    # --- 2. OCUPADOS (empleo, salario, informalidad, sector) ---
    occ_path = os.path.join(carpeta_mes, 'Ocupados.csv')
    if os.path.exists(occ_path):
        # Leer solo las columnas necesarias
        cols_needed = ['DPTO', 'FEX_C18', 'RAMA2D_R4', 'OFICIO_C8', 'INGLABO', 'OCI', 'P6920', 'P6430', 'P6426', 'P3042', 'P6040', 'P3271']
        # Verificar que columnas existen
        try:
            header_df = pd.read_csv(occ_path, sep=';', encoding='latin1', nrows=0)
            cols_disponibles = [c for c in cols_needed if c in header_df.columns]
        except:
            cols_disponibles = cols_needed

        occ = leer_csv_geih(occ_path, usecols=cols_disponibles)
        if not occ.empty:
            occ = occ.dropna(subset=['FEX_C18'])
            occ['FEX_C18'] = pd.to_numeric(occ['FEX_C18'], errors='coerce')
            occ = occ.dropna(subset=['FEX_C18'])

            # Nacional: empleo total
            resultado['empleo_nacional'] = occ['FEX_C18'].sum()

            # Salario promedio nacional
            if 'INGLABO' in occ.columns:
                occ['INGLABO'] = pd.to_numeric(occ['INGLABO'], errors='coerce')
                occ_valid = occ[occ['INGLABO'] > 0]
                if len(occ_valid) > 0:
                    resultado['salario_promedio_nacional'] = round(
                        (occ_valid['INGLABO'] * occ_valid['FEX_C18']).sum() / occ_valid['FEX_C18'].sum()
                    )
                else:
                    resultado['salario_promedio_nacional'] = np.nan

            # Informalidad nacional: usar P6920 (cotiza a pension) como proxy
            # P6920: 1=cotiza (formal), 2=no cotiza (informal), 3=otro
            if 'P6920' in occ.columns:
                occ['P6920'] = pd.to_numeric(occ['P6920'], errors='coerce')
                informales = occ[occ['P6920'] == 2]  # No cotizan = informales
                resultado['informales_nacional'] = informales['FEX_C18'].sum()
                resultado['tasa_informalidad_nacional'] = round(
                    informales['FEX_C18'].sum() / occ['FEX_C18'].sum() * 100, 2
                )

            # Empleo por sector
            if 'RAMA2D_R4' in occ.columns:
                occ['RAMA2D_R4'] = pd.to_numeric(occ['RAMA2D_R4'], errors='coerce')
                sector_emp = occ.groupby('RAMA2D_R4')['FEX_C18'].sum().reset_index()
                sector_emp.columns = ['rama_ciiu', 'empleo']
                sector_emp['periodo'] = periodo
                sector_emp['ano'] = ano
                sector_emp['mes'] = mes

                # Salario por sector
                if 'INGLABO' in occ.columns:
                    sector_sal = occ_valid.groupby('RAMA2D_R4').apply(
                        lambda g: (g['INGLABO'] * g['FEX_C18']).sum() / g['FEX_C18'].sum()
                        if g['FEX_C18'].sum() > 0 else np.nan
                    ).reset_index()
                    sector_sal.columns = ['rama_ciiu', 'salario_promedio']
                    sector_sal['salario_promedio'] = sector_sal['salario_promedio'].round(0)
                    sector_emp = sector_emp.merge(sector_sal, on='rama_ciiu', how='left')
                else:
                    sector_emp['salario_promedio'] = np.nan

                resultado['_empleo_sector'] = sector_emp

                # Matriz depto x sector
                if 'DPTO' in occ.columns:
                    matriz = occ.groupby(['DPTO', 'RAMA2D_R4'])['FEX_C18'].sum().reset_index()
                    matriz.columns = ['dpto', 'rama_ciiu', 'empleo']
                    matriz['periodo'] = periodo
                    matriz['ano'] = ano
                    matriz['mes'] = mes
                    resultado['_matriz_depto_sector'] = matriz

            # Informalidad por depto: usar P6920 (no cotiza = informal)
            if 'P6920' in occ.columns and 'DPTO' in occ.columns:
                occ['P6920'] = pd.to_numeric(occ['P6920'], errors='coerce')
                info_depto = occ.groupby('DPTO').apply(lambda g: {
                    'empleo': g['FEX_C18'].sum(),
                    'informales': g[g['P6920'] == 2]['FEX_C18'].sum(),
                }).apply(pd.Series).reset_index()
                info_depto['tasa_informalidad'] = (info_depto['informales'] / info_depto['empleo'] * 100).round(2)
                info_depto['periodo'] = periodo
                info_depto['ano'] = ano
                info_depto['mes'] = mes
                resultado['_informalidad_depto'] = info_depto[['periodo', 'ano', 'mes', 'DPTO', 'empleo', 'informales', 'tasa_informalidad']]

            # Salario por ocupacion (acumulando muestra ponderada mes a mes)
            if 'OFICIO_C8' in occ.columns and 'INGLABO' in occ.columns:
                occ['OFICIO_C8'] = pd.to_numeric(occ['OFICIO_C8'], errors='coerce')
                sal_ocup = occ_valid.groupby('OFICIO_C8').apply(
                    lambda g: pd.Series({
                        'sum_ingreso_ponderado': (g['INGLABO'] * g['FEX_C18']).sum(),
                        'sum_fex': g['FEX_C18'].sum(),
                        'mediana_ingreso': g['INGLABO'].median(),
                        'empleo_total': g['FEX_C18'].sum(),
                        'ocupados_muestra': len(g),
                    })
                ).reset_index()
                sal_ocup['periodo'] = periodo
                sal_ocup['ano'] = ano
                sal_ocup['mes'] = mes
                resultado['_salario_ocupacion'] = sal_ocup

            # Empleo por nivel educativo
            if 'P3042' in occ.columns:
                occ['P3042'] = pd.to_numeric(occ['P3042'], errors='coerce')
                nivel_emp = occ.groupby('P3042')['FEX_C18'].sum().reset_index()
                nivel_emp.columns = ['nivel_educativo', 'empleo']
                nivel_emp['periodo'] = periodo
                resultado['_nivel_educativo'] = nivel_emp

    return resultado


def main():
    print('ETL GEIH - Procesando 52 meses...')
    print('=' * 70)

    # Listar todas las carpetas de meses
    carpetas = []
    for ano_dir in sorted(os.listdir(RAW)):
        ano_path = os.path.join(RAW, ano_dir)
        if not os.path.isdir(ano_path):
            continue
        for mes_dir in sorted(os.listdir(ano_path)):
            mes_path = os.path.join(ano_path, mes_dir)
            if os.path.isdir(mes_path):
                # Parsear ano y mes del nombre (formato: 2023-01)
                parts = mes_dir.split('-')
                if len(parts) == 2:
                    ano = int(parts[0])
                    mes = int(parts[1])
                    carpetas.append((mes_path, ano, mes))

    print(f'Carpetas encontradas: {len(carpetas)}')

    # Procesar cada mes
    resumen_nacional = []
    desempleo_depto = []
    empleo_sector = []
    salario_ocupacion = []
    informalidad_depto = []
    matriz_depto_sector = []
    nivel_educativo = []

    t0 = time.time()

    for i, (carpeta, ano, mes) in enumerate(carpetas, 1):
        t1 = time.time()
        try:
            res = procesar_mes(carpeta, ano, mes)
            resumen_nacional.append({k: v for k, v in res.items() if not k.startswith('_')})
            if '_desempleo_depto' in res:
                desempleo_depto.append(res['_desempleo_depto'])
            if '_empleo_sector' in res:
                empleo_sector.append(res['_empleo_sector'])
            if '_salario_ocupacion' in res:
                salario_ocupacion.append(res['_salario_ocupacion'])
            if '_informalidad_depto' in res:
                informalidad_depto.append(res['_informalidad_depto'])
            if '_matriz_depto_sector' in res:
                matriz_depto_sector.append(res['_matriz_depto_sector'])
            if '_nivel_educativo' in res:
                nivel_educativo.append(res['_nivel_educativo'])
            elapsed = time.time() - t1
            tasa = res.get('tasa_desempleo_nacional', '?')
            print(f'[{i:2d}/{len(carpetas)}] {ano}-{mes:02d} OK ({elapsed:.1f}s) tasa_des={tasa}%')
        except Exception as e:
            print(f'[{i:2d}/{len(carpetas)}] {ano}-{mes:02d} ERROR: {e}')

    print('=' * 70)

    # Guardar tablas
    def guardar(df_list, name, sort_cols=None):
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            if sort_cols:
                df = df.sort_values(sort_cols)
            path = os.path.join(PROCESSED, name)
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f'[OK] {name}: {len(df)} filas, {os.path.getsize(path)/1024:.0f} KB')
            return df
        else:
            print(f'[FAIL] {name}: sin datos')
            return None

    print('\nGuardando tablas agregadas...')

    # Resumen nacional: convertir lista de dicts a DataFrame
    if resumen_nacional:
        df_resumen = pd.DataFrame(resumen_nacional)
        df_resumen = df_resumen.sort_values(['ano', 'mes'])
        path = os.path.join(PROCESSED, 'geih_resumen_nacional.csv')
        df_resumen.to_csv(path, index=False, encoding='utf-8-sig')
        print(f'[OK] geih_resumen_nacional.csv: {len(df_resumen)} filas, {os.path.getsize(path)/1024:.0f} KB')
    else:
        print('[FAIL] geih_resumen_nacional.csv: sin datos')

    def guardar_df(df_list, name, sort_cols=None):
        if df_list:
            df = pd.concat(df_list, ignore_index=True)
            if sort_cols:
                df = df.sort_values(sort_cols)
            path = os.path.join(PROCESSED, name)
            df.to_csv(path, index=False, encoding='utf-8-sig')
            print(f'[OK] {name}: {len(df)} filas, {os.path.getsize(path)/1024:.0f} KB')
            return df
        else:
            print(f'[FAIL] {name}: sin datos')
            return None

    guardar_df(desempleo_depto, 'geih_desempleo_mensual.csv', ['ano', 'mes', 'DPTO'])
    guardar_df(empleo_sector, 'geih_empleo_sector_mensual.csv', ['ano', 'mes', 'rama_ciiu'])
    guardar_df(informalidad_depto, 'geih_informalidad_mensual.csv', ['ano', 'mes', 'DPTO'])
    guardar_df(matriz_depto_sector, 'geih_empleo_depto_sector.csv', ['ano', 'mes', 'dpto', 'rama_ciiu'])

    # Salario por ocupacion: promedio movil 12 meses + confianza
    if salario_ocupacion:
        df_sal = pd.concat(salario_ocupacion, ignore_index=True)
        # Ordenar y asignar ranking de periodos (meses consecutivos)
        df_sal['periodo_dt'] = pd.to_datetime(df_sal['periodo'], format='%Y-%m', errors='coerce')
        df_sal = df_sal.dropna(subset=['periodo_dt']).sort_values(['OFICIO_C8', 'periodo_dt'])
        df_sal['mes_idx'] = df_sal.groupby('OFICIO_C8').cumcount() + 1
        n_periodos = df_sal['periodo_dt'].dt.to_period('M').nunique()
        ventana = min(12, max(1, n_periodos - 1))

        # Calcular sumas acumuladas por ocupacion
        g = df_sal.groupby('OFICIO_C8')
        df_sal['sum_ingreso_acum'] = g['sum_ingreso_ponderado'].cumsum()
        df_sal['sum_fex_acum'] = g['sum_fex'].cumsum()
        df_sal['muestra_acum'] = g['ocupados_muestra'].cumsum()

        # Tomar el ultimo periodo de cada ocupacion y restar la ventana anterior
        ultimos = df_sal.groupby('OFICIO_C8').last().reset_index()
        anteriores = df_sal[df_sal['mes_idx'] == df_sal['mes_idx'] - ventana]
        anteriores = anteriores.set_index('OFICIO_C8')[['sum_ingreso_acum', 'sum_fex_acum', 'muestra_acum']].rename(
            columns=lambda c: c + '_prev')
        ultimos = ultimos.set_index('OFICIO_C8')
        ultimos = ultimos.join(anteriores, how='left')

        ultimos['sum_ingreso_ventana'] = ultimos['sum_ingreso_acum'] - ultimos['sum_ingreso_acum_prev'].fillna(0)
        ultimos['sum_fex_ventana'] = ultimos['sum_fex_acum'] - ultimos['sum_fex_acum_prev'].fillna(0)
        ultimos['muestra_ventana'] = (ultimos['muestra_acum'] - ultimos['muestra_acum_prev'].fillna(0)).astype(int)

        ultimos['salario_promedio'] = (ultimos['sum_ingreso_ventana'] / ultimos['sum_fex_ventana'].replace(0, np.nan)).round(0)
        ultimos['salario_mediano'] = df_sal.groupby('OFICIO_C8')['mediana_ingreso'].median().round(0)
        ultimos['empleo_total'] = ultimos['sum_fex_ventana'].round(0).astype('Int64')

        # Confianza segun tamano de muestra real y empleo estimado
        def _confianza(row):
            muestra = int(row['muestra_ventana'] or 0)
            empleo = float(row['empleo_total'] or 0)
            if muestra < 30 or empleo < 5000:
                return "baja"
            if muestra < 100 or empleo < 20000:
                return "media"
            return "alta"
        ultimos['confianza'] = ultimos.apply(_confianza, axis=1)

        df_sal_reciente = ultimos.reset_index()[[
            'OFICIO_C8', 'salario_promedio', 'salario_mediano', 'empleo_total',
            'ocupados_muestra', 'muestra_ventana', 'confianza', 'periodo'
        ]].copy()
        df_sal_reciente['ocupados_muestra'] = df_sal_reciente['ocupados_muestra'].fillna(0).astype(int)
        df_sal_reciente['muestra_ventana'] = df_sal_reciente['muestra_ventana'].fillna(0).astype(int)
        df_sal_reciente = df_sal_reciente[df_sal_reciente['OFICIO_C8'].notna() & (df_sal_reciente['OFICIO_C8'] != 0)]
        df_sal_reciente.to_csv(os.path.join(PROCESSED, 'geih_salario_ocupacion.csv'), index=False, encoding='utf-8-sig')
        print(f'[OK] geih_salario_ocupacion.csv: {len(df_sal_reciente)} filas (promedio movil {ventana} meses, foto: {ultimos["periodo"].iloc[0] if not ultimos.empty else "n/a"})')

    guardar_df(nivel_educativo, 'geih_empleo_nivel_educativo.csv', ['periodo', 'nivel_educativo'])

    elapsed_total = time.time() - t0
    print(f'\nTiempo total: {elapsed_total:.1f}s ({elapsed_total/60:.1f} min)')


if __name__ == '__main__':
    main()