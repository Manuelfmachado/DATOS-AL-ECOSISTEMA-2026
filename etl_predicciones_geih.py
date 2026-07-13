"""
ETL ALBA - Paso 4: Predicciones Chronos T5 sobre series mensuales de GEIH
Genera predicciones mensuales de desempleo nacional usando Chronos T5 Small
sobre los 51 puntos mensuales de GEIH (2022-02 a 2026-04).

Genera: data/processed/predicciones_geih.json
"""
import json
import os
import numpy as np
import pandas as pd

BASE = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026'
PROCESSED = os.path.join(BASE, 'data', 'processed')


def predecir_con_chronos(serie, horizonte, n_samples=50):
    """Genera prediccion con Chronos T5 Small."""
    try:
        from chronos import ChronosPipeline
        import torch
        pipe = ChronosPipeline.from_pretrained(
            "amazon/chronos-t5-small",
            device_map="cpu",
            torch_dtype=torch.float32,
        )
        context = torch.tensor(serie)
        forecast = pipe.predict(context, prediction_length=horizonte, num_samples=n_samples)
        # forecast shape: (batch, num_samples, prediction_length) -> squeeze batch
        forecast_np = forecast.squeeze(0).numpy()  # (num_samples, prediction_length)
        mediana = np.median(forecast_np, axis=0)  # (prediction_length,)
        p10 = np.percentile(forecast_np, 10, axis=0)
        p90 = np.percentile(forecast_np, 90, axis=0)
        return mediana.tolist(), p10.tolist(), p90.tolist()
    except Exception as e:
        print(f'  Chronos no disponible, usando tendencia lineal: {e}')
        return None, None, None


def predecir_tendencia_lineal(serie, horizonte):
    """Fallback: prediccion por tendencia lineal simple."""
    x = np.arange(len(serie))
    y = np.array(serie)
    # Regresion lineal
    coef = np.polyfit(x, y, 1)
    polinomio = np.poly1d(coef)
    futuro = np.arange(len(serie), len(serie) + horizonte)
    prediccion = polinomio(futuro)
    # No permitir valores negativos
    prediccion = np.maximum(prediccion, 0)
    # Intervalo de confianza simple: +- 20%
    p10 = prediccion * 0.8
    p90 = prediccion * 1.2
    return prediccion.tolist(), p10.tolist(), p90.tolist()


def main():
    print('Predicciones GEIH - Chronos T5 / Tendencia lineal')
    print('=' * 70)

    # Leer serie de desempleo nacional
    df = pd.read_csv(os.path.join(PROCESSED, 'geih_resumen_nacional.csv'))
    df = df.dropna(subset=['tasa_desempleo_nacional']).sort_values(['ano', 'mes']).reset_index(drop=True)
    serie_desempleo = df['tasa_desempleo_nacional'].tolist()
    periodos = df['periodo'].tolist()
    print(f'Serie de desempleo: {len(serie_desempleo)} puntos ({periodos[0]} a {periodos[-1]})')
    print(f'  Min: {min(serie_desempleo):.1f}% | Max: {max(serie_desempleo):.1f}% | Prom: {np.mean(serie_desempleo):.1f}%')

    # Leer serie de empleo por sector (top 5 sectores)
    df_sec = pd.read_csv(os.path.join(PROCESSED, 'geih_empleo_sector_mensual.csv'))
    df_sec = df_sec.dropna(subset=['empleo']).sort_values(['ano', 'mes'])
    # Top 5 sectores por empleo promedio
    top_sectores = df_sec.groupby('rama_ciiu')['empleo'].mean().sort_values(ascending=False).head(5).index.tolist()
    print(f'Top 5 sectores para predecir: {top_sectores}')

    # Leer serie de informalidad
    serie_informalidad = df.dropna(subset=['tasa_informalidad_nacional'])['tasa_informalidad_nacional'].tolist()
    print(f'Serie de informalidad: {len(serie_informalidad)} puntos')

    # Leer serie de salario promedio
    serie_salario = df.dropna(subset=['salario_promedio_nacional'])['salario_promedio_nacional'].tolist()
    print(f'Serie de salario: {len(serie_salario)} puntos')

    # Horizontes: 12 meses (1 ano) y 60 meses (5 anos)
    horizontes = {'1ano': 12, '5anos': 60}

    resultado = {
        'modelo': 'Chronos T5 Small (o tendencia lineal como fallback)',
        'fuente': 'GEIH mensual DANE (52 meses, 2022-02 a 2026-04)',
        'ultimo_periodo_historico': periodos[-1],
        'horizontes': list(horizontes.keys()),
        'desempleo_nacional': {
            'historico': [{'periodo': p, 'valor': v} for p, v in zip(periodos, serie_desempleo)],
        },
        'informalidad_nacional': {
            'historico': [{'periodo': p, 'valor': v} for p, v in zip(periodos, serie_informalidad)] if len(serie_informalidad) == len(periodos) else [],
        },
        'salario_promedio_nacional': {
            'historico': [{'periodo': p, 'valor': int(v)} for p, v in zip(periodos, serie_salario)] if len(serie_salario) == len(periodos) else [],
        },
        'sectores': {},
    }

    # Predecir desempleo nacional
    print('\n[1/3] Prediciendo desempleo nacional...')
    for h_name, h_val in horizontes.items():
        print(f'  Horizonte {h_name} ({h_val} meses)...')
        mediana, p10, p90 = predecir_con_chronos(serie_desempleo, h_val)
        if mediana is None:
            mediana, p10, p90 = predecir_tendencia_lineal(serie_desempleo, h_val)
        # Generar periodos futuros
        ult_ano = int(periodos[-1].split('-')[0])
        ult_mes = int(periodos[-1].split('-')[1])
        periodos_futuros = []
        ano, mes = ult_ano, ult_mes
        for i in range(h_val):
            mes += 1
            if mes > 12:
                mes = 1
                ano += 1
            periodos_futuros.append(f'{ano}-{mes:02d}')
        resultado['desempleo_nacional'][f'prediccion_{h_name}'] = [
            {'periodo': p, 'mediana': round(m, 2), 'p10': round(lo, 2), 'p90': round(hi, 2)}
            for p, m, lo, hi in zip(periodos_futuros, mediana, p10, p90)
        ]

    # Predecir informalidad
    print('[2/3] Prediciendo informalidad nacional...')
    for h_name, h_val in horizontes.items():
        if len(serie_informalidad) > 10:
            mediana, p10, p90 = predecir_con_chronos(serie_informalidad, h_val)
            if mediana is None:
                mediana, p10, p90 = predecir_tendencia_lineal(serie_informalidad, h_val)
            ult_ano = int(periodos[-1].split('-')[0])
            ult_mes = int(periodos[-1].split('-')[1])
            periodos_futuros = []
            ano, mes = ult_ano, ult_mes
            for i in range(h_val):
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
                periodos_futuros.append(f'{ano}-{mes:02d}')
            resultado['informalidad_nacional'][f'prediccion_{h_name}'] = [
                {'periodo': p, 'mediana': round(m, 2), 'p10': round(lo, 2), 'p90': round(hi, 2)}
                for p, m, lo, hi in zip(periodos_futuros, mediana, p10, p90)
            ]

    # Predecir empleo por sector (top 5)
    print('[3/3] Prediciendo empleo por sector (top 5)...')
    for sector in top_sectores:
        df_s = df_sec[df_sec['rama_ciiu'] == sector].sort_values(['ano', 'mes'])
        serie_sec = df_s['empleo'].tolist()
        periodos_sec = df_s['periodo'].tolist()
        if len(serie_sec) < 10:
            continue
        resultado['sectores'][str(int(sector))] = {
            'historico': [{'periodo': p, 'valor': int(v)} for p, v in zip(periodos_sec, serie_sec)],
        }
        for h_name, h_val in horizontes.items():
            mediana, p10, p90 = predecir_con_chronos(serie_sec, h_val)
            if mediana is None:
                mediana, p10, p90 = predecir_tendencia_lineal(serie_sec, h_val)
            ult_ano = int(periodos_sec[-1].split('-')[0])
            ult_mes = int(periodos_sec[-1].split('-')[1])
            periodos_futuros = []
            ano, mes = ult_ano, ult_mes
            for i in range(h_val):
                mes += 1
                if mes > 12:
                    mes = 1
                    ano += 1
                periodos_futuros.append(f'{ano}-{mes:02d}')
            resultado['sectores'][str(int(sector))][f'prediccion_{h_name}'] = [
                {'periodo': p, 'mediana': int(m), 'p10': int(lo), 'p90': int(hi)}
                for p, m, lo, hi in zip(periodos_futuros, mediana, p10, p90)
            ]

    # Guardar
    path_out = os.path.join(PROCESSED, 'predicciones_geih.json')
    with open(path_out, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f'\n[OK] predicciones_geih.json: {os.path.getsize(path_out)/1024:.0f} KB')
    print(f'  Desempleo: {len(serie_desempleo)} puntos historicos + 12+60 prediccion')
    print(f'  Sectores: {len(resultado["sectores"])} sectores con prediccion')


if __name__ == '__main__':
    main()