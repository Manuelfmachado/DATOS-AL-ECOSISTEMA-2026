"""
Predicción laboral para Colombia con TimesFM 2.5 (zero-shot foundation model) + blend CAGR.

Motor de forecasting: TimesFM 2.5 200M (torch), foundation model de Google Research pre-
entrenado en 100B puntos reales de series temporales (ICML 2024). Reemplaza a Chronos T5
Small por mejor captura de tendencias en horizontes largos.

Fuentes de series temporales:
  - GEIH DANE mensual: 10 macrosectores de empleo, salario/empleo/desempleo/informalidad
    nacional, y ~18 CIIUs 2-dígitos asociados a las profesiones. (~47 pts mensuales)
  - World Bank: sectores (% empleo), desempleo, formalidad, PIB por empleado. (anual, 16 pts,
    referencia macro)
  - WEF Future of Jobs / O*NET / ESCO: badge cualitativo de demanda (alta/media/baja) de
    profesiones y habilidades. No es serie temporal.

BLEND CAGR HISTÓRICO: los foundation models zero-shot (TimesFM incluido) sufren reversión a
la media con series cortas, proyectando decrecimiento donde la tendencia real es creciente.
Para evitar proyecciones absurdas, el CAGR final combina 50% TimesFM + 50% CAGR histórico
real calculado sobre los años completos disponibles, acotado a pisos realistas.

Salida: data/processed/predicciones_mundiales.json

Nota: el archivo se llama prediccion_chronos.py por compatibilidad con AGENTS.md y scripts
de despliegue, pero el motor activo es TimesFM 2.5.
"""
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from timesfm import TimesFM_2p5_200M_torch, ForecastConfig

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

# --- Configuración -------------------------------------------------
MODEL_NAME = "google/timesfm-2.5-200m-pytorch"
TIMESFM_REPO = "google/timesfm-2.5-200m-pytorch"
HORIZONS = {"5a": 5, "10a": 10}
# TimesFM 2.5 exige series multiplos de p=32 (patch length).
TIMESFM_PATCH = 32
# Blend: peso del CAGR histórico real vs TimesFM. 0.5 = 50/50.
BLEND_HIST_WEIGHT = 0.5
# Acotamientos realistas para Colombia (crecimiento anual).
# Antes CAGR_CAP=0.12 permitía acumular +120% en 10 años para sectores en rebote
# post-pandemia (ej: CIIU 27 Aparatos eléctricos). +8% anual es ya optimista para
# Colombia (PIB crece ~3-4%); con esto el máximo 10y es (1.08)^10 - 1 ≈ +116%.
CAGR_FLOOR = -0.05   # -5% (caída severa)
CAGR_CAP = 0.08      # +8% (boom sostenido, conservador)

SECTORES_WB = {
    "SL.AGR.EMPL.ZS": "Agricultura",
    "SL.IND.EMPL.ZS": "Industria",
    "SL.SRV.EMPL.ZS": "Servicios",
}

OTROS_WB = {
    "SL.UEM.TOTL.ZS": "Desempleo",
    "SL.EMP.WORK.ZS": "Asalariados formales",
    "SL.EMP.SELF.ZS": "Cuenta propia",
    "SL.GDP.PCAP.EM.KD": "PIB por empleado",
}

# 10 macrosectores colombianos (mismo bucketing que el endpoint todos-los-sectores).
def _macrosector_name(code: int) -> str:
    if code < 10: return "Agricultura y recursos"
    if code < 20: return "Alimentos y manufactura"
    if code < 30: return "Industria y tecnologia"
    if code < 40: return "Energia y agua"
    if code < 48: return "Construccion y comercio"
    if code < 54: return "Transporte y logistica"
    if code < 57: return "Alojamiento y comida"
    if code < 67: return "Informacion y finanzas"
    if code < 83: return "Servicios empresariales"
    return "Servicios publicos y sociales"


# Perfiles profesionales con demanda base (alta/media/baja) ajustada a Colombia.
# Salarios base distintos por profesión, anclados a rangos reales del mercado laboral
# colombiano (GEIH-DANE, PILA, ofertas laborales y encuestas sectoriales).
# No se usa el promedio genérico del sector: cada perfil tiene su propio salario base.
PROFESIONES = [
    # Alta demanda (tecnología, datos, sostenibilidad, salud)
    {"nombre": "Desarrollador de software", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 5_800_000, "ciiu": 62},
    {"nombre": "Científico de datos / IA", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 6_500_000, "ciiu": 62},
    {"nombre": "Especialista en ciberseguridad", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 6_200_000, "ciiu": 62},
    {"nombre": "Ingeniero de nube / DevOps", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 6_000_000, "ciiu": 61},
    {"nombre": "Diseñador UX / UI", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 3_200_000, "ciiu": 73},
    {"nombre": "Enfermero(a) profesional", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 3_000_000, "ciiu": 86},
    {"nombre": "Técnico en energías renovables", "sector": "Industria", "demanda_base": "alta", "salario_mensual_cop": 2_600_000, "ciiu": 27},
    {"nombre": "Ingeniero(a) eléctrico(a)", "sector": "Industria", "demanda_base": "alta", "salario_mensual_cop": 4_200_000, "ciiu": 27},
    {"nombre": "Analista financiero", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 4_000_000, "ciiu": 64},
    {"nombre": "Especialista en marketing digital", "sector": "Servicios", "demanda_base": "alta", "salario_mensual_cop": 3_000_000, "ciiu": 73},

    # Demanda media (estables, con crecimiento moderado)
    {"nombre": "Técnico logístico / cadena de suministro", "sector": "Industria", "demanda_base": "media", "salario_mensual_cop": 2_000_000, "ciiu": 49},
    {"nombre": "Gestor(a) de proyectos", "sector": "Servicios", "demanda_base": "media", "salario_mensual_cop": 4_800_000, "ciiu": 70},
    {"nombre": "Técnico agropecuario sostenible", "sector": "Agricultura", "demanda_base": "media", "salario_mensual_cop": 1_400_000, "ciiu": 1},
    {"nombre": "Contador(a) / auditor(a)", "sector": "Servicios", "demanda_base": "media", "salario_mensual_cop": 3_500_000, "ciiu": 69},
    {"nombre": "Profesor(a) de educación técnica", "sector": "Servicios", "demanda_base": "media", "salario_mensual_cop": 3_200_000, "ciiu": 85},
    {"nombre": "Profesional en recursos humanos", "sector": "Servicios", "demanda_base": "media", "salario_mensual_cop": 2_800_000, "ciiu": 78},

    # Demanda baja o en declive (automatización, menor crecimiento)
    {"nombre": "Operario(a) de manufactura tradicional", "sector": "Industria", "demanda_base": "baja", "salario_mensual_cop": 1_700_000, "ciiu": 25},
    {"nombre": "Agricultor(a) tradicional", "sector": "Agricultura", "demanda_base": "baja", "salario_mensual_cop": 900_000, "ciiu": 1},
    {"nombre": "Empleado(a) administrativo(a) tradicional", "sector": "Servicios", "demanda_base": "baja", "salario_mensual_cop": 1_800_000, "ciiu": 82},
    {"nombre": "Cajero(a) / atención al cliente básica", "sector": "Servicios", "demanda_base": "baja", "salario_mensual_cop": 1_300_000, "ciiu": 47},
    {"nombre": "Conductor(a) de vehículos (sin automatización)", "sector": "Servicios", "demanda_base": "baja", "salario_mensual_cop": 1_500_000, "ciiu": 49},
]

# Mapeo profesión -> CIIU 2-dígitos (sector donde se desempeña la profesión).
# TimesFM+blend se corre sobre la serie mensual de empleo de ese CIIU en GEIH, y el
# CAGR proyectado se usa como crecimiento de demanda de la profesión. Como el CIIU
# mide empleo del SECTOR completo (no solo de la profesión), se etiqueta en la UI
# como "crecimiento sectorial TimesFM+blend". La demanda_base (alta/media/baja) se
# conserva solo como badge visual y referencia cualitativa O*NET/ESCO/WEF, no para el cálculo.
PROF_CIIU = {
    "Desarrollador de software": 62,
    "Científico de datos / IA": 62,  # data science en Colombia vive en software/finanzas, no en CIIU 72 (investigación pura, en declive)
    "Especialista en ciberseguridad": 62,
    "Ingeniero de nube / DevOps": 61,
    "Diseñador UX / UI": 73,
    "Enfermero(a) profesional": 86,
    "Técnico en energías renovables": 35,
    "Ingeniero(a) eléctrico(a)": 27,
    "Analista financiero": 64,
    "Especialista en marketing digital": 73,
    "Técnico logístico / cadena de suministro": 52,
    "Gestor(a) de proyectos": 70,
    "Técnico agropecuario sostenible": 1,
    "Contador(a) / auditor(a)": 69,
    "Profesor(a) de educación técnica": 85,
    "Profesional en recursos humanos": 78,
    "Operario(a) de manufactura tradicional": 25,
    "Agricultor(a) tradicional": 1,
    "Empleado(a) administrativo(a) tradicional": 82,
    "Cajero(a) / atención al cliente básica": 47,
    "Conductor(a) de vehículos (sin automatización)": 49,
}

# Habilidades del WEF Future of Jobs, adaptadas al contexto colombiano.
HABILIDADES = [
    {"habilidad": "Pensamiento analítico e innovación", "demanda": 95},
    {"habilidad": "Aprendizaje activo y adaptabilidad", "demanda": 94},
    {"habilidad": "Programación y automatización", "demanda": 93},
    {"habilidad": "Inteligencia artificial generativa", "demanda": 92},
    {"habilidad": "Gestión de datos y BI", "demanda": 90},
    {"habilidad": "Resolución de problemas complejos", "demanda": 89},
    {"habilidad": "Ciberseguridad básica", "demanda": 87},
    {"habilidad": "Pensamiento crítico", "demanda": 85},
    {"habilidad": "Creatividad y diseño centrado en humanos", "demanda": 82},
    {"habilidad": "Gestión de proyectos ágiles", "demanda": 80},
    {"habilidad": "Colaboración remota / trabajo híbrido", "demanda": 78},
    {"habilidad": "Comunicación digital efectiva", "demanda": 76},
    {"habilidad": "Automatización de procesos (RPA)", "demanda": 74},
    {"habilidad": "Sostenibilidad y economía circular", "demanda": 72},
    {"habilidad": "Emprendimiento e intraemprendimiento", "demanda": 70},
    {"habilidad": "Electrónica e IoT básico", "demanda": 68},
    {"habilidad": "Gestión del cambio", "demanda": 65},
    {"habilidad": "Negociación y persuasión digital", "demanda": 62},
    {"habilidad": "Liderazgo distribuido", "demanda": 60},
    {"habilidad": "Atención al cliente experiencial", "demanda": 55},
]


# ============================================================================
# Helpers TimesFM 2.5 + blend CAGR histórico
# ============================================================================

def _pad_to_patch(values: np.ndarray, patch: int = TIMESFM_PATCH) -> np.ndarray:
    """Pad la serie al inicio con el primer valor para que sea múltiplo de `patch`."""
    n = len(values)
    pad_n = (patch - (n % patch)) % patch
    if pad_n == 0:
        return values
    return np.concatenate([np.full(pad_n, values[0], dtype=values.dtype), values])


def forecast_series(values: np.ndarray, horizon: int, model: TimesFM_2p5_200M_torch):
    """Predice `horizon` pasos con TimesFM 2.5. Devuelve medianas y bandas 10-90.

    TimesFM devuelve (point_forecast, quantile_forecast) donde quantile_forecast tiene
    shape (batch, horizon, n_quantiles). Las cuantiles por defecto son 10 niveles
    espaciados; mapeamos las posiciones para p10 y p90.
    """
    arr = np.asarray(values, dtype=np.float32)
    arr_padded = _pad_to_patch(arr)
    point_forecast, quantile_forecast = model.forecast(horizon=horizon, inputs=[arr_padded])
    median = point_forecast[0].astype(float)
    q = quantile_forecast[0]  # shape (horizon, n_quantiles)
    n_q = q.shape[-1]
    # Mapear a p10/p90 asumiendo cuantiles equiespaciados [0.1..0.9] o similar
    idx_p10 = max(0, int(round(0.10 * (n_q - 1))))
    idx_p90 = min(n_q - 1, int(round(0.90 * (n_q - 1))))
    p10 = q[:, idx_p10].astype(float)
    p90 = q[:, idx_p90].astype(float)
    return median.tolist(), p10.tolist(), p90.tolist()


def cagr(val_inicial: float, val_final: float, años: int) -> float:
    if val_inicial <= 0 or años <= 0:
        return 0.0
    return (val_final / val_inicial) ** (1 / años) - 1


def cagr_historico_real(promedios_anuales: list, anios_completos: list) -> float:
    """CAGR real entre el primer y último año completo disponible."""
    if len(promedios_anuales) < 2 or len(anios_completos) < 2:
        return 0.0
    first = float(promedios_anuales[0])
    last = float(promedios_anuales[-1])
    years = int(anios_completos[-1]) - int(anios_completos[0])
    if first <= 0 or years <= 0:
        return 0.0
    return (last / first) ** (1 / years) - 1


def blend_cagr(cagr_timesfm: float, cagr_hist: float) -> float:
    """Combina 50% TimesFM + 50% CAGR histórico real, acotado a pisos realistas.

    Esto mitiga la reversión-a-la-media de los foundation models zero-shot en series
    cortas: si TimesFM proyecta -1.6% pero la tendencia real es +6.1%, el blend da
    ~+2.25% (realista y anclado a la evidencia)."""
    blended = BLEND_HIST_WEIGHT * cagr_timesfm + (1 - BLEND_HIST_WEIGHT) * cagr_hist
    # Acotar a pisos realistas para Colombia
    blended = max(CAGR_FLOOR, min(CAGR_CAP, blended))
    return blended


def proyectar_indicador(start_year: int, values: list, horizon: int, model: TimesFM_2p5_200M_torch):
    """Proyección anual directa (para series WB anuales). Aplica blend con CAGR histórico."""
    median, p10, p90 = forecast_series(np.array(values), horizon, model)
    # Blend: ajustar la mediana al CAGR blended en lugar del CAGR TimesFM puro
    cagr_tfm = cagr(values[-1], median[-1], horizon) if len(median) == horizon else 0.0
    cagr_hist = cagr(values[0], values[-1], len(values) - 1) if len(values) > 1 else 0.0
    cagr_final = blend_cagr(cagr_tfm, cagr_hist)
    # Reconstruir mediana blended con crecimiento compuesto desde el último valor real
    median_blended = [values[-1] * ((1 + cagr_final) ** (i + 1)) for i in range(horizon)]
    years = list(range(start_year, start_year + horizon))
    return {
        "historico": {"años": [int(y) for y in range(start_year - len(values), start_year)], "valores": values},
        "prediccion": {"años": years, "mediana": median_blended, "bajo_10": p10, "alto_90": p90},
        "cagr_timesfm_pct": round(cagr_tfm * 100, 2),
        "cagr_historico_pct": round(cagr_hist * 100, 2),
        "cagr_blend_pct": round(cagr_final * 100, 2),
    }


def forecast_mensual_a_anual(
    valores_mensuales: list,
    ultimo_ano_completo: int,
    primer_ano_hist: int,
    model: TimesFM_2p5_200M_torch,
    horizonte_anios: int = 10,
    no_negativo: bool = True,
    promedios_anuales_hist: list = None,
    anios_completos_hist: list = None,
):
    """Toma una serie mensual, la proyecta con TimesFM (horizon = anios*12) y
    anualiza promediando bloques de 12 meses. Aplica blend con el CAGR histórico real
    si se proveen promedios_anuales_hist y anios_completos_hist."""
    horizon = horizonte_anios * 12
    median, p10, p90 = forecast_series(np.array(valores_mensuales), horizon, model)

    if no_negativo:
        median = [max(0.0, v) for v in median]
        p10 = [max(0.0, v) for v in p10]
        p90 = [max(0.0, v) for v in p90]

    # CAGR TimesFM sobre la proyección mensual anualizada
    last_base = float(valores_mensuales[-1])
    val_5_tfm = float(np.mean(median[HORIZONS["5a"] * 12 - 12:HORIZONS["5a"] * 12])) if len(median) >= HORIZONS["5a"] * 12 else last_base
    val_10_tfm = float(np.mean(median[HORIZONS["10a"] * 12 - 12:HORIZONS["10a"] * 12])) if len(median) >= HORIZONS["10a"] * 12 else last_base
    cagr_tfm_5 = cagr(last_base, val_5_tfm, HORIZONS["5a"])
    cagr_tfm_10 = cagr(last_base, val_10_tfm, HORIZONS["10a"])

    # CAGR histórico real
    cagr_hist = cagr_historico_real(promedios_anuales_hist or [], anios_completos_hist or [])

    # Blend
    cagr_blend_5 = blend_cagr(cagr_tfm_5, cagr_hist)
    cagr_blend_10 = blend_cagr(cagr_tfm_10, cagr_hist)

    # Reconstruir serie anual blended con CAGR blended (más estable que el raw de TimesFM)
    pred_anos = []
    pred_med = []
    pred_p10 = []
    pred_p90 = []
    for i in range(horizonte_anios):
        pred_anos.append(ultimo_ano_completo + 1 + i)
        # Mediana blended: crecimiento compuesto desde last_base
        pred_med.append(last_base * ((1 + cagr_blend_10) ** (i + 1)))
        # Bandas: mantener la dispersión relativa de TimesFM alrededor de su mediana
        if len(median) > i * 12:
            med_tfm_block = float(np.mean(median[i * 12:(i + 1) * 12]))
            p10_tfm_block = float(np.mean(p10[i * 12:(i + 1) * 12]))
            p90_tfm_block = float(np.mean(p90[i * 12:(i + 1) * 12]))
            spread_low = (med_tfm_block - p10_tfm_block) if med_tfm_block > 0 else 0
            spread_high = (p90_tfm_block - med_tfm_block) if med_tfm_block > 0 else 0
            pred_p10.append(max(0.0, pred_med[-1] - spread_low))
            pred_p90.append(max(0.0, pred_med[-1] + spread_high))
        else:
            pred_p10.append(pred_med[-1])
            pred_p90.append(pred_med[-1])

    return {
        "pred_anos": pred_anos,
        "pred_mediana": pred_med,
        "pred_bajo_10": pred_p10,
        "pred_alto_90": pred_p90,
        "serie_mensual_pred": median,
        "cagr_timesfm_5a_pct": round(cagr_tfm_5 * 100, 2),
        "cagr_timesfm_10a_pct": round(cagr_tfm_10 * 100, 2),
        "cagr_historico_pct": round(cagr_hist * 100, 2),
        "cagr_blend_5a_pct": round(cagr_blend_5 * 100, 2),
        "cagr_blend_10a_pct": round(cagr_blend_10 * 100, 2),
    }


# ============================================================================
# GEIH: 10 macrosectores con TimesFM + blend
# ============================================================================

def construir_sectores_geih(model: TimesFM_2p5_200M_torch) -> dict:
    """Proyecta los 10 macrosectores de empleo con TimesFM + blend CAGR sobre GEIH."""
    path = PROCESSED / "geih_empleo_sector_mensual.csv"
    if not path.exists():
        print("[GEIH sectores] CSV no encontrado, se omite")
        return {"sectores": [], "periodo_historico": "", "anio_base_proyeccion": None,
                "ultimo_periodo": "", "anio_actual_incompleto": None, "metodologia": ""}

    df = pd.read_csv(path)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["rama_ciiu"] = df["rama_ciiu"].fillna(0).astype(int)
    df["macrosector"] = df["rama_ciiu"].apply(_macrosector_name)

    # CORRECCIÓN DE COHERENCIA GEIH (igual que en construir_geih_nacional y que
    # el Observatorio): el CSV de empleo sectorial suma más que la PEA nacional
    # por inconsistencias en las tabulaciones del DANE. Prorrateamos la corrección
    # por periodo usando (pea - desempleados) de geih_resumen_nacional como total
    # correcto, para que la suma de los 10 macrosectores cuadre con el empleo
    # nacional mostrado en Dashboard/Observatorio (~20.7M, no 24.3M).
    path_nacional = PROCESSED / "geih_resumen_nacional.csv"
    if path_nacional.exists():
        df_nac = pd.read_csv(path_nacional)
        df_nac["ano"] = df_nac["ano"].astype(int)
        df_nac["mes"] = df_nac["mes"].astype(int)
        # Empleo correcto por periodo = pea - desempleados
        df_nac["empleo_correcto"] = df_nac["pea_nacional"] - df_nac["desempleados_nacional"]
        # Factor de corrección por periodo
        for _, row_nac in df_nac.iterrows():
            a, m = int(row_nac["ano"]), int(row_nac["mes"])
            suma_sectorial = df[(df["ano"] == a) & (df["mes"] == m)]["empleo"].sum()
            if suma_sectorial > 0 and row_nac["empleo_correcto"] > 0:
                factor = row_nac["empleo_correcto"] / suma_sectorial
                if 0.5 < factor < 1.5:  # solo si el factor es razonable
                    df.loc[(df["ano"] == a) & (df["mes"] == m), "empleo"] *= factor

    # Meses por año y años completos
    meses_por_ano = df.groupby("ano")["mes"].nunique().to_dict()
    anios_completos = sorted([a for a, m in meses_por_ano.items() if m >= 12])
    if not anios_completos:
        return {"sectores": [], "periodo_historico": "", "anio_base_proyeccion": None,
                "ultimo_periodo": "", "anio_actual_incompleto": None, "metodologia": ""}
    ultimo_ano_completo = max(anios_completos)
    ultimo_ano_crudo = int(df["ano"].max())
    primer_ano = int(df["ano"].min())

    # Último periodo real disponible
    ultimo_periodo_row = df.sort_values(["ano", "mes"]).iloc[-1]
    ultimo_periodo_str = f"{int(ultimo_periodo_row['ano']):04d}-{int(ultimo_periodo_row['mes']):02d}"

    # IMPORTANTE: usar TODA la serie mensual disponible (incluido el año en curso
    # parcial como 2026 con 4 meses) para alimentar el forecast. Descartar el año
    # en curso por "incompleto" ignoraba datos REALES que ya muestran saltos
    # importantes (ej: salario subió de $1.9M en 2025 a $2.2M en 2026).
    # El blend histórico sigue usando solo años completos (metodológicamente correcto).
    mensual = (
        df.groupby(["ano", "mes", "periodo", "macrosector"])["empleo"]
        .sum()
        .reset_index()
    )

    # Promedio anual por macrosector (años completos) para histórico display y blend
    anual = df[df["ano"].isin(anios_completos)].groupby(["ano", "macrosector"]).agg(
        empleo=("empleo", "sum"), meses=("mes", "nunique")
    ).reset_index()
    anual["empleo_prom"] = anual["empleo"] / anual["meses"]

    sectores = []
    for sec in sorted(anual["macrosector"].unique()):
        # Serie mensual ordenada para este macrosector (TODOS los meses disponibles)
        sm = mensual[mensual["macrosector"] == sec].sort_values(["ano", "mes"])
        valores_mensuales = sm["empleo"].tolist()
        if len(valores_mensuales) < 6:
            continue

        # Histórico anual display: incluye años completos + año en curso (parcial)
        # con el promedio de los meses disponibles. Esto conecta el último histórico con
        # el forecast (que arranca en ultimo_ano_crudo + 1) sin gap visual.
        hist_sec = anual[anual["macrosector"] == sec].sort_values("ano")
        serie_historica = [
            {"ano": int(r["ano"]), "empleo": int(round(r["empleo_prom"]))}
            for _, r in hist_sec.iterrows() if int(r["ano"]) in anios_completos
        ]
        # Agregar año en curso (parcial) con el promedio de los meses disponibles
        if ultimo_ano_crudo not in anios_completos:
            sm_anio_crudo = sm[sm["ano"] == ultimo_ano_crudo]
            if len(sm_anio_crudo) > 0:
                promedio_crudo = float(sm_anio_crudo["empleo"].mean())
                serie_historica.append({
                    "ano": int(ultimo_ano_crudo),
                    "empleo": int(round(promedio_crudo)),
                    "parcial": True,
                })

        # Promedios anuales históricos para el blend
        hist_completo = hist_sec[hist_sec["ano"].isin(anios_completos)].sort_values("ano")
        promedios_anuales_hist = [float(r["empleo_prom"]) for _, r in hist_completo.iterrows()]
        anios_hist_blend = [int(r["ano"]) for _, r in hist_completo.iterrows()]

        # BASE de proyección: último valor MENSUAL real disponible.
        # Antes se usaba promedio del último año completo, lo que ignoraba el año en curso.
        last_base = float(valores_mensuales[-1])

        # CAGR histórico real
        cagr_hist_val = cagr_historico_real(promedios_anuales_hist, anios_hist_blend)

        # Proyectar con TimesFM + blend (mensual -> anual).
        # primer_ano_hist se pasa solo para referencia; forecast usa la serie completa.
        res = forecast_mensual_a_anual(
            valores_mensuales, ultimo_ano_crudo, primer_ano, model,
            horizonte_anios=HORIZONS["10a"], no_negativo=True,
            promedios_anuales_hist=promedios_anuales_hist,
            anios_completos_hist=anios_hist_blend,
        )

        # Crecimiento: usar el CAGR BLENDED directamente (no recalcular desde last_base,
        # eso mezcla bases y genera inconsistencias).
        crec_5_dec = res["cagr_blend_5a_pct"] / 100.0
        crec_10_dec = res["cagr_blend_10a_pct"] / 100.0
        # Reconstruir empleo 5y/10y con crecimiento compuesto desde last_base real.
        empleo_5y = last_base * (1 + crec_5_dec) ** HORIZONS["5a"]
        empleo_10y = last_base * (1 + crec_10_dec) ** HORIZONS["10a"]
        var_5y = ((empleo_5y / last_base) - 1) * 100 if last_base > 0 else 0
        var_10y = ((empleo_10y / last_base) - 1) * 100 if last_base > 0 else 0

        # Serie completa: histórico anual + predicción anual blended.
        # Para la predicción anual, reconstruimos con el CAGR blended desde last_base
        # (consistente con crec_5/crec_10 declarados, en vez del raw de TimesFM).
        pred_anos_blended = []
        for i, y in enumerate(res["pred_anos"]):
            pred_anos_blended.append(last_base * (1 + crec_10_dec) ** (i + 1))
        serie = list(serie_historica)
        for y, med in zip(res["pred_anos"], pred_anos_blended):
            serie.append({"ano": int(y), "empleo": int(round(med)), "proyectado": True})

        sectores.append({
            "sector": str(sec),
            "empleo_actual": int(round(last_base)),
            "cagr_historico_pct": round(float(cagr_hist_val) * 100, 1),
            "crec_timesfm_5a_pct": res["cagr_timesfm_5a_pct"],
            "crec_timesfm_10a_pct": res["cagr_timesfm_10a_pct"],
            "crec_blend_5a_pct": res["cagr_blend_5a_pct"],
            "crec_blend_10a_pct": res["cagr_blend_10a_pct"],
            "empleo_5y": int(round(empleo_5y)),
            "empleo_10y": int(round(empleo_10y)),
            "variacion_5y_pct": round(float(var_5y), 1),
            "variacion_10y_pct": round(float(var_10y), 1),
            "serie": serie,
        })

    sectores.sort(key=lambda s: -s["empleo_actual"])

    return {
        "sectores": sectores,
        "periodo_historico": f"{min(anios_completos)}-{max(anios_completos)}",
        "anio_base_proyeccion": ultimo_ano_completo,
        "ultimo_periodo": ultimo_periodo_str,
        "anio_actual_incompleto": ultimo_ano_crudo if ultimo_ano_crudo != ultimo_ano_completo else None,
        "metodologia": "TimesFM 2.5 200M (Google Research, ICML 2024) sobre serie mensual GEIH (DANE). Blend 50/50 con CAGR histórico real. Bandas p10-p90 de TimesFM. Acotado a -5%/+12% anual.",
        "motor_prediccion": "timesfm_2p5_blend",
    }


# ============================================================================
# GEIH nacional: salario, empleo, desempleo, informalidad con TimesFM + blend
# ============================================================================

def construir_geih_nacional(model: TimesFM_2p5_200M_torch) -> dict:
    """Proyecta indicadores nacionales GEIH con TimesFM + blend sobre serie mensual."""
    path = PROCESSED / "geih_resumen_nacional.csv"
    if not path.exists():
        print("[GEIH nacional] CSV no encontrado, se omite")
        return {}

    df = pd.read_csv(path)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df = df.sort_values(["ano", "mes"])

    # CORRECCIÓN DE COHERENCIA GEIH: el CSV crudo a veces trae empleo_nacional
    # inconsistente (mayor que la PEA), probablemente por inconsistencias en las
    # tabulaciones del DANE. El Observatorio aplica la misma corrección: si
    # empleo > PEA, recalcular como pea - desempleados (consistente con la tasa
    # de desempleo reportada). Sin esto, Dashboard muestra 20.7M y Predicción 24.3M.
    if "empleo_nacional" in df.columns and "pea_nacional" in df.columns and "desempleados_nacional" in df.columns:
        mascara_inc = df["empleo_nacional"] > df["pea_nacional"]
        if mascara_inc.any():
            df.loc[mascara_inc, "empleo_nacional"] = df.loc[mascara_inc, "pea_nacional"] - df.loc[mascara_inc, "desempleados_nacional"]

    meses_por_ano = df.groupby("ano")["mes"].nunique().to_dict()
    anios_completos = sorted([a for a, m in meses_por_ano.items() if m >= 12])
    if not anios_completos:
        return {}
    ultimo_ano_completo = max(anios_completos)
    ultimo_ano_crudo = int(df["ano"].max())
    primer_ano = int(df["ano"].min())

    indicadores = {
        "salario_promedio_nacional": {"nombre": "salario_nacional", "no_neg": True},
        "empleo_nacional": {"nombre": "empleo_nacional", "no_neg": True},
        "tasa_desempleo_nacional": {"nombre": "desempleo_nacional", "no_neg": True},
        "tasa_informalidad_nacional": {"nombre": "informalidad_nacional", "no_neg": True},
    }

    out = {}
    for col, cfg in indicadores.items():
        if col not in df.columns:
            continue
        # Serie mensual completa (incluido el año en curso parcial): datos REALES.
        serie = df.dropna(subset=[col])
        valores = serie[col].tolist()
        if len(valores) < 6:
            continue

        # Histórico anual para display: incluye el año en curso (parcial) con el
        # promedio de los meses disponibles, para que no haya gap visual entre el
        # último año completo y el inicio del forecast.
        hist_anos_display = []
        hist_valores_display = []
        for a in sorted(df["ano"].unique()):
            sub = df[df["ano"] == a][col].dropna()
            if len(sub) > 0:
                hist_anos_display.append(int(a))
                hist_valores_display.append(float(sub.mean()))

        # Histórico anual solo con años completos -> entrada del blend (metodológicamente correcto).
        hist_anos = []
        hist_valores = []
        for a in anios_completos:
            sub = df[df["ano"] == a][col].dropna()
            if len(sub) > 0:
                hist_anos.append(int(a))
                hist_valores.append(float(sub.mean()))

        res = forecast_mensual_a_anual(
            valores, ultimo_ano_crudo, primer_ano, model,
            horizonte_anios=HORIZONS["10a"], no_negativo=cfg["no_neg"],
            promedios_anuales_hist=hist_valores,
            anios_completos_hist=hist_anos,
        )

        # BASE: último valor MENSUAL real disponible (no promedio del último año completo).
        # Antes se usaba hist_valores[-1] (promedio 2025), ignorando que 2026 ya
        # mostraba saltos importantes en los meses disponibles.
        last_base = float(valores[-1])

        # Crecimiento: usar el CAGR BLENDED directo. Reconstruir val_5y/val_10y
        # con crecimiento compuesto desde last_base (consistente con el blend declarado).
        crec_5_dec = res["cagr_blend_5a_pct"] / 100.0
        crec_10_dec = res["cagr_blend_10a_pct"] / 100.0
        val_5 = last_base * (1 + crec_5_dec) ** HORIZONS["5a"]
        val_10 = last_base * (1 + crec_10_dec) ** HORIZONS["10a"]

        # Reconstruir la mediana de la predicción con el blend (consistente con val_5/val_10)
        mediana_blended = [last_base * (1 + crec_10_dec) ** (i + 1) for i in range(len(res["pred_anos"]))]

        out[cfg["nombre"]] = {
            "historico": {"años": hist_anos_display, "valores": [round(v, 2) for v in hist_valores_display]},
            "prediccion": {
                "años": res["pred_anos"],
                "mediana": [round(v, 2) for v in mediana_blended],
                "bajo_10": [round(v, 2) for v in res["pred_bajo_10"]],
                "alto_90": [round(v, 2) for v in res["pred_alto_90"]],
            },
            "valor_actual": round(last_base, 2),
            "valor_5y": round(val_5, 2),
            "valor_10y": round(val_10, 2),
            "crec_anual_5a_pct": round(crec_5_dec * 100, 2),
            "crec_anual_10a_pct": round(crec_10_dec * 100, 2),
            "crec_timesfm_5a_pct": res["cagr_timesfm_5a_pct"],
            "crec_timesfm_10a_pct": res["cagr_timesfm_10a_pct"],
            "crec_historico_pct": res["cagr_historico_pct"],
            "crec_blend_5a_pct": res["cagr_blend_5a_pct"],
            "crec_blend_10a_pct": res["cagr_blend_10a_pct"],
        }
        print(f"[GEIH nacional] {cfg['nombre']}: {len(valores)} pts mensuales, "
              f"actual={round(last_base)} -> 10y={round(val_10)} "
              f"(blend10a={res['cagr_blend_10a_pct']}%, hist={res['cagr_historico_pct']}%)")

    return out


# ============================================================================
# CIIU por profesión: TimesFM + blend sobre series mensuales GEIH
# ============================================================================

CIIU2_NAMES = {
    1: "Agricultura, ganadería y caza", 2: "Silvicultura y madera",
    3: "Pesca y acuicultura", 5: "Extracción de carbón",
    6: "Extracción de petróleo y gas", 7: "Minería de metales",
    8: "Otras minas y canteras", 9: "Actividades de apoyo a la minería",
    10: "Elaboración de alimentos", 11: "Elaboración de bebidas",
    25: "Productos metálicos", 27: "Aparatos eléctricos",
    35: "Electricidad, gas y vapor", 41: "Construcción de edificios",
    47: "Comercio al por menor", 49: "Transporte terrestre y por tuberías",
    52: "Almacenamiento y transporte complementario",
    61: "Telecomunicaciones", 62: "Desarrollo de software",
    64: "Servicios financieros", 69: "Actividades jurídicas y contabilidad",
    70: "Consultoría y gestión", 72: "Investigación científica",
    73: "Publicidad y estudios de mercado", 78: "Actividades de empleo",
    82: "Actividades administrativas de oficina", 85: "Educación",
    86: "Servicios de salud humana",
}


def construir_ciiu_proyecciones(model: TimesFM_2p5_200M_torch, ciius: list[int]) -> dict:
    """Proyecta el empleo mensual de cada CIIU 2-dígitos con TimesFM + blend y devuelve
    un dict {ciiu: {crec_anual_5a, crec_anual_10a, valor_actual, valor_5y, valor_10y, ...}}."""
    path = PROCESSED / "geih_empleo_sector_mensual.csv"
    if not path.exists():
        print("[CIIU] CSV no encontrado, se omite")
        return {}

    df = pd.read_csv(path)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    df["rama_ciiu"] = df["rama_ciiu"].fillna(0).astype(int)

    meses_por_ano = df.groupby("ano")["mes"].nunique().to_dict()
    anios_completos = sorted([a for a, m in meses_por_ano.items() if m >= 12])
    if not anios_completos:
        return {}
    ultimo_ano_completo = max(anios_completos)
    ultimo_ano_crudo = int(df["ano"].max())
    primer_ano = int(df["ano"].min())

    # IMPORTANTE: NO filtrar por df["ano"] <= ultimo_ano_completo; eso descarta el
    # año en curso (2026 con 4 meses) que tiene datos REALES. El forecast usa toda
    # la serie disponible; el blend histórico sigue usando solo años completos.
    out = {}
    for ciiu in sorted(set(ciius)):
        sm = df[df["rama_ciiu"] == ciiu].sort_values(["ano", "mes"])
        valores = sm["empleo"].tolist()
        if len(valores) < 6:
            print(f"[CIIU {ciiu:02d}] serie muy corta ({len(valores)} pts), se omite")
            continue

        # Promedio anual histórico por año completo (para el blend)
        hist_anos_ciiu: list[int] = []
        hist_vals_ciiu: list[float] = []
        for a in anios_completos:
            sub = sm[sm["ano"] == a]["empleo"].dropna()
            if len(sub) > 0:
                hist_anos_ciiu.append(int(a))
                hist_vals_ciiu.append(float(sub.mean()))

        res = forecast_mensual_a_anual(
            valores, ultimo_ano_crudo, primer_ano, model,
            horizonte_anios=HORIZONS["10a"], no_negativo=True,
            promedios_anuales_hist=hist_vals_ciiu,
            anios_completos_hist=hist_anos_ciiu,
        )
        # BASE: último valor MENSUAL real disponible (no promedio del último año completo).
        # Antes se usaba el promedio de 2025, ignorando los meses de 2026 que ya muestran
        # el valor real actualizado del empleo del sector.
        last_base = float(valores[-1])

        # Crecimiento: usar el CAGR BLENDED directamente (TimesFM + histórico real).
        # NO recalcular con cagr(last_base, val_10) — eso mezcla bases (last_base es
        # promedio anual, val_10 viene de serie mensual anualizada) y genera
        # inconsistencias donde crec_anual_10a != crec_blend_10a_pct.
        crec_5 = res["cagr_blend_5a_pct"] / 100.0
        crec_10 = res["cagr_blend_10a_pct"] / 100.0

        # Reconstruir valores 5y/10y con crecimiento compuesto desde last_base
        # (consistente con el CAGR blended declarado).
        val_5 = last_base * (1 + crec_5) ** HORIZONS["5a"]
        val_10 = last_base * (1 + crec_10) ** HORIZONS["10a"]

        nombre = CIIU2_NAMES.get(ciiu, f"CIIU {ciiu:02d}")
        out[ciiu] = {
            "ciiu": ciiu,
            "nombre_sector": nombre,
            "valor_actual": int(round(last_base)),
            "valor_5y": int(round(val_5)),
            "valor_10y": int(round(val_10)),
            "crec_anual_5a": round(float(crec_5), 4),
            "crec_anual_10a": round(float(crec_10), 4),
            "crec_anual_5a_pct": round(float(crec_5) * 100, 2),
            "crec_anual_10a_pct": round(float(crec_10) * 100, 2),
            "crec_blend_5a_pct": res["cagr_blend_5a_pct"],
            "crec_blend_10a_pct": res["cagr_blend_10a_pct"],
            "crec_timesfm_5a_pct": res["cagr_timesfm_5a_pct"],
            "crec_timesfm_10a_pct": res["cagr_timesfm_10a_pct"],
            "crec_historico_pct": res["cagr_historico_pct"],
            "prediccion": {
                "años": res["pred_anos"],
                "mediana": [round(v, 2) for v in res["pred_mediana"]],
                "bajo_10": [round(v, 2) for v in res["pred_bajo_10"]],
                "alto_90": [round(v, 2) for v in res["pred_alto_90"]],
            },
        }
        print(f"[CIIU {ciiu:02d}] {nombre}: {len(valores)} pts, "
              f"actual={round(last_base)} -> 10y={round(val_10)} "
              f"(blend10a={res['cagr_blend_10a_pct']}%, hist={res['cagr_historico_pct']}%)")

    return out


# ============================================================================
# Profesiones: crecimiento de demanda desde TimesFM+blend sobre el CIIU del sector
# ============================================================================

def calcular_crecimiento_profesion(
    prof: dict,
    crecimiento_salarial_anual: float,
    ciiu_proyecciones: dict,
) -> dict:
    """Crecimiento de demanda proviene de TimesFM+blend sobre el CIIU 2-dígitos del sector
    donde se desempeña la profesión. La proyección salarial usa el crecimiento salarial
    nacional (TimesFM+blend sobre GEIH) con un ajuste por demanda cualitativa:
    alta demanda crece ~+1.5 p.p. sobre el promedio, baja demanda crece ~-1.0 p.p.,
    demanda media usa el promedio. Así cada profesión tiene un salario base distinto
    y una trayectoria salarial propia."""
    base = prof["demanda_base"]
    ciiu = PROF_CIIU.get(prof["nombre"])

    # 1. Crecimiento de la DEMANDA (empleo) = CAGR del CIIU del sector
    if ciiu and ciiu in ciiu_proyecciones:
        crec_demanda_anual = ciiu_proyecciones[ciiu]["crec_anual_10a"]
        fuente_crec = "timesfm_blend_ciiu"
        nombre_sector_ciiu = ciiu_proyecciones[ciiu]["nombre_sector"]
    else:
        # Fallback: heurística conservadora si el CIIU no tiene serie
        low, high = {"alta": (0.04, 0.065), "media": (0.02, 0.04), "baja": (-0.015, 0.015)}[base]
        crec_demanda_anual = float(np.random.uniform(low, high))
        fuente_crec = "heuristica_onet"
        nombre_sector_ciiu = None

    crec_demanda_5 = (1 + crec_demanda_anual) ** 5 - 1
    crec_demanda_10 = (1 + crec_demanda_anual) ** 10 - 1

    # 2. Crecimiento SALARIAL por profesión = crecimiento nacional + ajuste por demanda
    ajuste_demanda = {"alta": 0.015, "media": 0.0, "baja": -0.010}[base]
    crec_salarial_prof = crecimiento_salarial_anual + ajuste_demanda
    # Acotar a rango realista para Colombia (-1% a +8% anual)
    crec_salarial_prof = max(-0.01, min(0.08, crec_salarial_prof))

    crec_salarial_5 = (1 + crec_salarial_prof) ** 5 - 1
    crec_salarial_10 = (1 + crec_salarial_prof) ** 10 - 1

    # 3. Proyección salarial propia de cada profesión
    salario_5 = prof["salario_mensual_cop"] * (1 + crec_salarial_prof) ** 5
    salario_10 = prof["salario_mensual_cop"] * (1 + crec_salarial_prof) ** 10

    return {
        "profesion": prof["nombre"],
        "sector": prof["sector"],
        "demanda": base,
        "ciiu_sector": ciiu,
        "nombre_sector_ciiu": nombre_sector_ciiu,
        "fuente_crecimiento": fuente_crec,
        "salario_mensual_cop": prof["salario_mensual_cop"],
        "salario_5a_cop": round(salario_5, -3),
        "salario_10a_cop": round(salario_10, -3),
        # Crecimiento de la demanda (empleo) del sector/profesión
        "crecimiento_anual_pct": round(crec_demanda_anual * 100, 1),
        "crecimiento_5a_pct": round(crec_demanda_5 * 100, 1),
        "crecimiento_10a_pct": round(crec_demanda_10 * 100, 1),
        # Crecimiento salarial propio de la profesión
        "crecimiento_salarial_anual_pct": round(crec_salarial_prof * 100, 2),
        "crecimiento_salarial_5a_pct": round(crec_salarial_5 * 100, 1),
        "crecimiento_salarial_10a_pct": round(crec_salarial_10 * 100, 1),
    }


# ============================================================================
# Main
# ============================================================================

def main():
    print("Cargando datos mundiales (World Bank)...")
    wb = pd.read_csv(PROCESSED / "worldbank_colombia.csv")

    print(f"Cargando modelo TimesFM 2.5 200M ({TIMESFM_REPO})...")
    # TimesFM 2.5 (torch) se carga vía from_pretrained; no usa device_map ni torch_dtype.
    # Corre en CPU (~1.5 GB RAM según el model card).
    model = TimesFM_2p5_200M_torch.from_pretrained(TIMESFM_REPO)
    # TimesFM 2.5 exige llamar compile() con un ForecastConfig antes de forecast().
    # max_context: nuestra serie más larga es GEIH mensual (~47 pts, padded a ~64); 1024 es holgado.
    # max_horizon: proyectamos 10 años mensual = 120 pts; 256 cubre con margen.
    model.compile(ForecastConfig(max_context=1024, max_horizon=256))

    last_year = int(wb["year"].max())
    print(f"Último año histórico World Bank: {last_year}")

    # --- 1. Sectores WB (3 macrosectores, anual, TimesFM+blend) -----------
    sectores = {}
    sectores_cagr = {}
    for code, name in SECTORES_WB.items():
        serie = wb[wb["indicator_code"] == code].sort_values("year")
        values = serie["value"].tolist()
        if len(values) < 5:
            continue
        sectores[name] = proyectar_indicador(last_year + 1, values, HORIZONS["10a"], model)
        # Usar el CAGR blended a 5 años (más estable que el TimesFM puro)
        sectores_cagr[name] = sectores[name]["cagr_blend_pct"] / 100
        print(f"[WB] {name}: histórico {len(values)} años, CAGR blend 5a "
              f"{sectores_cagr[name]*100:.1f}% (tfm={sectores[name]['cagr_timesfm_pct']}%)")

    # --- 2. Otros indicadores WB (anual, TimesFM+blend) -------------------
    otros = {}
    for code, name in OTROS_WB.items():
        serie = wb[wb["indicator_code"] == code].sort_values("year")
        values = serie["value"].tolist()
        if len(values) < 5:
            continue
        otros[name] = proyectar_indicador(last_year + 1, values, HORIZONS["10a"], model)

    # --- 3. Sectores GEIH (10 macrosectores, mensual->anual, TimesFM+blend)
    print("Proyectando 10 macrosectores GEIH con TimesFM + blend...")
    sectores_geih = construir_sectores_geih(model)
    print(f"[GEIH sectores] {len(sectores_geih.get('sectores', []))} macrosectores proyectados")

    # --- 4. GEIH nacional (salario, empleo, desempleo, informalidad) ------
    print("Proyectando indicadores nacionales GEIH con TimesFM + blend...")
    geih_nacional = construir_geih_nacional(model)

    # --- 5. CIIU por profesión (TimesFM+blend sobre series mensuales GEIH) -
    ciius_profesiones = sorted(set(PROF_CIIU.values()))
    print(f"Proyectando {len(ciius_profesiones)} CIIUs de profesiones con TimesFM + blend...")
    ciiu_proyecciones = construir_ciiu_proyecciones(model, ciius_profesiones)
    print(f"[CIIU profesiones] {len(ciiu_proyecciones)} CIIUs proyectados")

    # --- 6. Crecimiento salarial (TimesFM+blend sobre GEIH nacional) ------
    sal_nac = geih_nacional.get("salario_nacional", {})
    crec_salarial = (sal_nac.get("crec_blend_10a_pct", sal_nac.get("crec_anual_10a_pct", 3.5)) or 3.5) / 100
    # Fallback de seguridad: acotar a un rango realista para Colombia
    crec_salarial = max(0.01, min(0.08, crec_salarial))
    print(f"[Salarios] Crecimiento salarial anual (TimesFM+blend): {crec_salarial*100:.2f}%")

    # --- 7. Profesiones (crecimiento blend del CIIU + salario blend) ------
    np.random.seed(42)
    profesiones_resultado = [
        calcular_crecimiento_profesion(p, crec_salarial, ciiu_proyecciones)
        for p in PROFESIONES
    ]
    profesiones_resultado.sort(key=lambda x: x["crecimiento_10a_pct"], reverse=True)

    # --- 8. Habilidades (WEF, no serie temporal) --------------------------
    habilidades_resultado = HABILIDADES

    # --- 9. Salarios (crecimiento TimesFM+blend, no fijo) -----------------
    salario_minimo_2026 = 1_750_000
    salarios = {
        "metrica": "Crecimiento salarial anual proyectado (TimesFM 2.5 + blend sobre GEIH)",
        "fuente": "TimesFM 2.5 200M (Google Research) sobre salario promedio mensual GEIH (DANE). Blend 50/50 con CAGR histórico.",
        "crecimiento_anual_pct": round(crec_salarial * 100, 2),
        "observacion": f"Crecimiento real anual proyectado por TimesFM + blend sobre el salario promedio GEIH. "
                       f"Base {sectores_geih.get('anio_base_proyeccion')} -> 10 anios.",
        "salario_minimo_2026_cop": salario_minimo_2026,
        "salario_minimo_2030_cop": round(salario_minimo_2026 * (1 + crec_salarial) ** 5, -3),
        "salario_minimo_2035_cop": round(salario_minimo_2026 * (1 + crec_salarial) ** 10, -3),
        "serie_salario_nacional": sal_nac,
    }

    # --- 10. Insights automáticos -----------------------------------------
    def _limpiar_nombre_insight(p: dict) -> str:
        """Quita paréntesis de género y la coletilla 'tradicional' para los insights
        (donde el espacio es limitado y la concisión importa más que la formalidad)."""
        n = p["profesion"]
        n = n.replace("(a)", "").replace("a)", "").replace("a/a", "").strip()
        # Quitar coletilla 'tradicional' para compactar
        n = n.replace("tradicional", "").strip()
        # Quitar dobles espacios
        n = " ".join(n.split())
        return n

    sectores_ordenados = sorted(
        [(name, sectores_cagr[name]) for name in sectores_cagr],
        key=lambda x: x[1],
        reverse=True,
    )
    insights = {
        "sectores": {
            "principal_empleador": "Servicios",
            "mas_estable": sectores_ordenados[0][0] if sectores_ordenados else "Servicios",
            "mensaje": "Servicios seguirá siendo el principal empleador en Colombia (~65% del empleo). "
                       "Agricultura e industria mantendrán una participación estable con pequeños cambios relativos.",
        },
        "profesiones": {
            "top_1": _limpiar_nombre_insight(profesiones_resultado[0]),
            "top_3": [_limpiar_nombre_insight(p) for p in profesiones_resultado[:3]],
            "mensaje": "Las profesiones con mejor perspectiva son tecnología, datos, ciberseguridad e ingeniería.",
        },
        "salarios": salarios,
    }

    resultado = {
        "modelo": MODEL_NAME,
        "motor_prediccion": "timesfm_2p5_blend",
        "pais": "Colombia",
        "fuente": "GEIH DANE (mensual, principal) + World Bank (macro referencia) + WEF/O*NET/ESCO (badge demanda)",
        "ultimo_año_historico": last_year,
        "horizontes": HORIZONS,
        "sectores": sectores,
        "sectores_cagr_5a": {k: round(v * 100, 1) for k, v in sectores_cagr.items()},
        "otros_indicadores": otros,
        "sectores_geih": sectores_geih,
        "geih_nacional": geih_nacional,
        "ciiu_proyecciones": ciiu_proyecciones,
        "profesiones": profesiones_resultado,
        "habilidades": habilidades_resultado,
        "salarios": salarios,
        "insights": insights,
    }

    out_path = PROCESSED / "predicciones_mundiales.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print(f"Guardado: {out_path}")


if __name__ == "__main__":
    main()