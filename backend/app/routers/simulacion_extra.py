"""
Endpoints adicionales del modulo Simulacion: Viabilidad de Programa y Priorizacion Territorial.
"""
import json
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/simulacion", tags=["Simulacion"])

DATA = Path(__file__).resolve().parents[2] / "data" / "processed"

SMMLV_2026 = 1_750_000

# Mapeo de códigos DANE (DIVIPOLA) a nombres de departamentos
DANE_DEPTO: dict[str, str] = {
    "05": "ANTIOQUIA", "08": "ATLANTICO", "11": "BOGOTA D.C.", "13": "BOLIVAR",
    "15": "BOYACA", "17": "CALDAS", "18": "CAQUETA", "19": "CAUCA",
    "20": "CESAR", "23": "CORDOBA", "25": "CUNDINAMARCA", "27": "CHOCO",
    "41": "HUILA", "44": "LA GUAJIRA", "47": "MAGDALENA", "50": "META",
    "52": "NARINO", "54": "NORTE DE SANTANDER", "63": "QUINDIO",
    "66": "RISARALDA", "68": "SANTANDER", "70": "SUCRE", "73": "TOLIMA",
    "76": "VALLE DEL CAUCA", "81": "ARAUCA", "85": "CASANARE",
    "86": "PUTUMAYO", "88": "ARCHIPIELAGO DE SAN ANDRES",
    "91": "AMAZONAS", "94": "GUAINIA", "95": "GUAVIARE",
    "97": "VAUPES", "99": "VICHADA",
}

# Sinónimos de nombres de departamentos para fusionar duplicados
DEPTO_SINONIMOS: dict[str, str] = {
    "ARCHIPIELAGO DE SAN ANDRES": "SAN ANDRES Y PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRES Y PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES Y PROVIDENCIA": "SAN ANDRES Y PROVIDENCIA",
    "BOGOTA D.C": "BOGOTA D.C.",
    "BOGOTA, D.C.": "BOGOTA D.C.",
    "BOGOTA": "BOGOTA D.C.",
}

RANGO_INGRESO_MEDIO_SMMLV: dict[str, float] = {
    "1 SMMLV": 1.0, "Entre 1 y 1,5 SMMLV": 1.25,
    "Entre 1,5 y 2,5 SMMLV": 2.0, "Entre 2,5 y 4 SMMLV": 3.25,
    "Entre 4 y 6 SMMLV": 5.0, "Entre 6 y 9 SMMLV": 7.5,
    "Mas de 9 SMMLV": 11.0, "Más de 9 SMMLV": 11.0,
}

CIIU2_NOMBRES: dict[str, str] = {
    "01": "Agricultura", "10": "Alimentos", "41": "Construcción",
    "45": "Comercio", "46": "Comercio mayorista", "47": "Comercio minorista",
    "49": "Transporte", "55": "Alojamiento", "56": "Restaurantes",
    "61": "Telecomunicaciones", "62": "TI y software", "63": "Servicios de información",
    "64": "Servicios financieros", "65": "Seguros", "68": "Inmobiliarias",
    "69": "Servicios jurídicos", "70": "Consultoría", "71": "Arquitectura e ingeniería",
    "72": "Investigación científica", "73": "Publicidad", "74": "Servicios profesionales",
    "75": "Veterinaria", "77": "Alquiler y leasing", "78": "Servicios de empleo",
    "79": "Agencias de viajes", "80": "Seguridad", "81": "Servicios a edificios",
    "82": "Servicios administrativos", "84": "Administración pública",
    "85": "Educación", "86": "Salud humana", "87": "Asistencia social",
    "88": "Asistencia sin alojamiento", "90": "Artes y entretenimiento",
    "91": "Bibliotecas y museos", "92": "Juegos de azar", "93": "Deportes",
    "94": "Asociaciones", "95": "Reparación de equipos", "96": "Servicios personales",
    "97": "Hogares como empleadores", "99": "Organizaciones extraterritoriales",
}


def _norm(s: str) -> str:
    if not s: return ""
    s = s.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _norm_depto(s: str) -> str:
    """Normaliza un nombre de departamento y fusiona sinónimos."""
    n = _norm(s)
    return DEPTO_SINONIMOS.get(n, n)


def _load_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Dataset {name} no disponible")
    return pd.read_csv(path)


def _rango_a_cop(rango: str) -> float:
    val = RANGO_INGRESO_MEDIO_SMMLV.get(rango.strip())
    if val is None:
        val = RANGO_INGRESO_MEDIO_SMMLV.get(_norm(rango), 2.0)
    return val * SMMLV_2026


# =============================================================================
# Modelos Pydantic
# =============================================================================

class ViabilidadRequest(BaseModel):
    programa: str          # nombre del programa académico
    departamento: str      # departamento objetivo
    nivel: str = "Profesional"  # Técnico, Profesional, Especialización, Maestría


class PriorizacionRequest(BaseModel):
    presupuesto_cop: float = 1_000_000_000  # presupuesto disponible (opcional)


# =============================================================================
# ENDPOINT 1: Viabilidad de Programa
# =============================================================================

@router.post("/viabilidad-programa")
def viabilidad_programa(req: ViabilidadRequest):
    """
    Evalúa la viabilidad de abrir un programa académico en un departamento.
    Cruza oferta (SNIES) con demanda (SPE/APE) e ingresos (OLE).
    Retorna un score 0-100 y recomendación.
    """
    programa_norm = _norm(req.programa)
    depto_norm = _norm(req.departamento)

    # 1. Cargar datos
    try:
        ole_ingresos = _load_csv("ole_ingresos_por_programa.csv")
        ole_area = _load_csv("ole_ingresos_por_area.csv")
        snies = _load_csv("snies_programas_matriculados.csv")
        spe = _load_csv("spe_ape_inscritos_ocupacion.csv")
        geih_salario = _load_csv("geih_salario_ocupacion.csv")
    except HTTPException as e:
        raise e

    # Normalizar columnas
    for df in [ole_ingresos, ole_area, snies, spe, geih_salario]:
        df.columns = [_norm(str(c)) for c in df.columns]

    # 2. Buscar ingreso de graduados para programas similares
    ingreso_estimado = SMMLV_2026 * 1.5  # default: 1.5 SMMLV

    # Buscar en OLE ingresos por programa
    if "PROGRAMA" in ole_ingresos.columns:
        mask = ole_ingresos["PROGRAMA"].apply(lambda x: programa_norm in _norm(str(x)) if pd.notna(x) else False)
        matches = ole_ingresos[mask]
    else:
        matches = pd.DataFrame()

    if len(matches) > 0 and "RANGO_INGRESO" in ole_ingresos.columns:
        rangos = matches["RANGO_INGRESO"].dropna()
        if len(rangos) > 0:
            ingresos = [_rango_a_cop(str(r)) for r in rangos]
            ingreso_estimado = float(np.median(ingresos))

    # También buscar por área de conocimiento
    if ingreso_estimado <= SMMLV_2026 * 1.5 and "AREA" in ole_area.columns:
        for _, row in ole_area.iterrows():
            if programa_norm in _norm(str(row.get("AREA", ""))):
                if "RANGO_INGRESO" in ole_area.columns:
                    ingreso_estimado = _rango_a_cop(str(row["RANGO_INGRESO"]))
                break

    # 3. Demanda laboral (SPE/APE)
    demanda_score = 0.0
    demanda_total = 0
    # Buscar columna de inscritos más reciente (inscritos_2020, inscritos_2019, etc.)
    inscritos_col = None
    for col in spe.columns:
        if "INSCRITOS" in col:
            inscritos_col = col
            break
    if "OCUPACION" in spe.columns and inscritos_col:
        # Palabras clave relevantes (sin stop words) con prefijo de 6+ chars para capturar variaciones
        stop_words = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON", "POR", "AL", "A", "O"}
        keywords = [w for w in programa_norm.split() if w not in stop_words]
        if not keywords:
            keywords = programa_norm.split()[:3]
        # Prefijos mínimos de 5 caracteres para cada keyword (INGENIERIA -> INGENI, SOFTWARE -> SOFTW)
        prefixes = [kw[:max(5, len(kw)//2)] for kw in keywords]
        for _, row in spe.iterrows():
            ocup = _norm(str(row["OCUPACION"]))
            # Match si algún prefijo está en la ocupación
            matched = any(pf in ocup for pf in prefixes)
            if not matched:
                # También match si la ocupación comparte palabras con el programa
                ocup_words = set(ocup.split())
                prog_words = set(programa_norm.split()) - stop_words
                matched = len(ocup_words & prog_words) > 0
            if not matched and len(ocup) > 4:
                matched = ocup in programa_norm
            if matched:
                val = row.get(inscritos_col, 0)
                demanda_total += int(val) if pd.notna(val) else 0
    demanda_score = min(100, demanda_total / 50)  # normalizar

    # 4. Saturación (oferta SNIES vs demanda)
    saturacion_pct = 0.0
    matriculados_depto = 0
    if "DEPARTAMENTO" in snies.columns and "MATRICULADOS" in snies.columns:
        depto_mask = snies["DEPARTAMENTO"].apply(lambda x: depto_norm in _norm(str(x)) if pd.notna(x) else False)
        depto_data = snies[depto_mask]
        if len(depto_data) > 0:
            # Buscar programas similares en el depto (filtrando stop words)
            if "PROGRAMA" in snies.columns:
                stop_words = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON", "POR", "AL", "A", "O"}
                prog_keywords = [w for w in programa_norm.split() if w not in stop_words]
                if not prog_keywords:
                    prog_keywords = programa_norm.split()[:3]
                prog_mask = depto_data["PROGRAMA"].apply(
                    lambda x: any(kw in _norm(str(x)) for kw in prog_keywords)
                    if pd.notna(x) else False
                )
                matriculados_depto = int(depto_data[prog_mask]["MATRICULADOS"].sum())

    # Ratio oferta/demanda
    if matriculados_depto > 0 and demanda_total > 0:
        saturacion_pct = min(100, (matriculados_depto / max(demanda_total, 1)) * 100)

    # 5. Salario de mercado (GEIH)
    salario_mercado = SMMLV_2026 * 1.3
    if "OFICIO" in geih_salario.columns and "SALARIO_PROMEDIO" in geih_salario.columns:
        for _, row in geih_salario.iterrows():
            oficio = _norm(str(row["OFICIO"]))
            if programa_norm[:8] in oficio:
                salario_mercado = float(row["SALARIO_PROMEDIO"])
                break

    # 6. Proyección de crecimiento (predicciones mundiales)
    crecimiento_anual_pct = 0.0
    try:
        pred_path = DATA / "predicciones_mundiales.json"
        if pred_path.exists():
            with open(pred_path, "r", encoding="utf-8") as f:
                preds = json.load(f)
            profesiones = preds.get("profesiones", [])
            for prof in profesiones:
                if programa_norm[:6] in _norm(prof.get("profesion", "")):
                    crecimiento_anual_pct = prof.get("crecimiento_anual_pct", 0.0)
                    break
    except Exception:
        pass

    # 7. Calcular score compuesto 0-100
    score = 50.0  # base
    score += min(25, (ingreso_estimado / SMMLV_2026 - 1) * 10)  # ingreso relativo
    score += min(20, demanda_score * 0.2)  # demanda
    score -= min(20, saturacion_pct * 0.2)  # saturación penaliza
    score += min(15, crecimiento_anual_pct * 3)  # proyección
    score = max(0, min(100, round(score, 1)))

    # 8. Recomendación
    if score >= 70:
        recomendacion = f"VIABLE: Alta empleabilidad proyectada en {req.departamento}. Salario estimado: ${ingreso_estimado:,.0f} COP/mes."
        nivel_riesgo = "bajo"
    elif score >= 45:
        recomendacion = f"MODERADO: Demanda aceptable pero hay competencia en {req.departamento}. Considere diferenciación curricular."
        nivel_riesgo = "medio"
    else:
        recomendacion = f"RIESGO: Mercado saturado en {req.departamento}. Explore otros departamentos o ajuste el enfoque del programa."
        nivel_riesgo = "alto"

    return {
        "programa": req.programa,
        "departamento": req.departamento,
        "nivel": req.nivel,
        "score_viabilidad": score,
        "nivel_riesgo": nivel_riesgo,
        "recomendacion": recomendacion,
        "indicadores": {
            "salario_estimado_cop": round(ingreso_estimado, -3),
            "salario_mercado_cop": round(salario_mercado, -3),
            "demanda_score": round(demanda_score, 1),
            "saturacion_oferta_pct": round(saturacion_pct, 1),
            "matriculados_competencia": matriculados_depto,
            "crecimiento_proyectado_anual_pct": round(crecimiento_anual_pct, 2),
            "sectores_demandantes": _top_sectores_demandantes(programa_norm),
        },
        "fuentes": ["OLE/MEN", "SNIES", "SPE/APE", "GEIH", "Chronos T5"],
    }


def _top_sectores_demandantes(programa_norm: str) -> list[dict]:
    """Encuentra los sectores con mayor demanda para un programa."""
    try:
        ru = _load_csv("rues_resumen_camara_ciiu.csv")
    except Exception:
        return []
    ru.columns = [_norm(str(c)) for c in ru.columns]
    if "CIIU2" not in ru.columns:
        return []
    top = []
    for _, row in ru.iterrows():
        try:
            ciu = str(row.get("CIIU2", ""))
            nombre = CIIU2_NOMBRES.get(ciu, ciu)
            empresas = int(row.get("EMPRESAS", 0) or 0)
            if empresas > 50:
                top.append({"sector": nombre, "empresas": empresas})
        except (ValueError, TypeError):
            continue
    top.sort(key=lambda x: x["empresas"], reverse=True)
    return top[:5]


# =============================================================================
# ENDPOINT 2: Priorización Territorial
# =============================================================================

@router.post("/priorizacion-territorial")
def priorizacion_territorial(req: PriorizacionRequest):
    """
    Rankea los departamentos de Colombia según urgencia de intervención laboral.
    Score compuesto: desempleo, informalidad, desempeño DNP, ingreso.
    Retorna top departamentos prioritarios con sectores recomendados.
    """
    try:
        geih_depto = _load_csv("geih_resumen_departamento.csv")
        geih_desempleo = _load_csv("geih_desempleo_departamento.csv")
        dnp = _load_csv("dnp_desempeno_departamento.csv")
        snies_depto = _load_csv("snies_matriculados_departamento.csv")
        informalidad = _load_csv("geih_informalidad_mensual.csv")
        emicron = _load_csv("emicron_por_departamento.csv")
    except HTTPException as e:
        raise e

    for df in [geih_depto, geih_desempleo, dnp, snies_depto, informalidad, emicron]:
        df.columns = [_norm(str(c)) for c in df.columns]

    # Cargar predicciones de desempleo
    try:
        pred_path = DATA / "predicciones_geih.json"
        if pred_path.exists():
            with open(pred_path, "r", encoding="utf-8") as f:
                preds_geih = json.load(f)
        else:
            preds_geih = {}
    except Exception:
        preds_geih = {}

    # Construir diccionario departamental
    deptos: dict[str, dict] = {}

    # GEIH resumen departamento
    for _, row in geih_depto.iterrows():
        depto = _norm_depto(str(row.get("DEPARTAMENTO", "")))
        if not depto or depto in ("NACIONAL", "TOTAL"):
            continue
        if depto not in deptos:
            deptos[depto] = {}
        try:
            deptos[depto]["ingreso_promedio"] = float(row.get("INGRESO_PROMEDIO", 0) or 0)
            deptos[depto]["tasa_formalidad"] = float(row.get("TASA_FORMALIDAD", 0) or 0)
            deptos[depto]["ocupados"] = int(row.get("OCUPADOS", 0) or 0)
        except (ValueError, TypeError):
            continue

    # GEIH desempleo (calculado: no_ocupados / (ocupados + no_ocupados))
    for _, row in geih_desempleo.iterrows():
        depto = _norm_depto(str(row.get("DEPARTAMENTO", "")))
        if not depto:
            continue
        if depto not in deptos:
            deptos[depto] = {}
        try:
            no_ocupados = float(row.get("NO_OCUPADOS", 0) or 0)
            ocupados = deptos[depto].get("ocupados", 0)
            if ocupados + no_ocupados > 0:
                deptos[depto]["tasa_desempleo"] = round(no_ocupados / (ocupados + no_ocupados) * 100, 1)
            else:
                deptos[depto]["tasa_desempleo"] = 0.0
        except (ValueError, TypeError):
            continue

    # DNP desempeño
    for _, row in dnp.iterrows():
        depto = _norm_depto(str(row.get("DEPARTAMENTO", row.get("DPTO", ""))))
        if not depto:
            continue
        if depto not in deptos:
            deptos[depto] = {}
        try:
            deptos[depto]["dnp_desempeno"] = round(float(row.get("PROMEDIO_DESEMPENO", row.get("DESEMPENO", 0)) or 0), 1)
        except (ValueError, TypeError):
            continue

    # SNIES matrícula
    for _, row in snies_depto.iterrows():
        depto = _norm_depto(str(row.get("DEPARTAMENTO", "")))
        if not depto:
            continue
        if depto not in deptos:
            deptos[depto] = {}
        try:
            deptos[depto]["matriculados"] = int(row.get("MATRICULADOS", 0) or 0)
        except (ValueError, TypeError):
            continue

    # Informalidad (promedio últimos meses) - DPTO usa códigos DANE
    inf_agg: dict[str, list] = {}
    for _, row in informalidad.iterrows():
        dpto_code = str(row.get("DPTO", "")).strip()
        depto = _norm_depto(DANE_DEPTO.get(dpto_code, "")) if dpto_code else ""
        if not depto:
            depto = _norm_depto(str(row.get("DEPARTAMENTO", "")))
        if not depto:
            continue
        try:
            val = float(row.get("TASA_INFORMALIDAD", row.get("INFORMALIDAD", 0)) or 0)
            if depto not in inf_agg:
                inf_agg[depto] = []
            inf_agg[depto].append(val)
        except (ValueError, TypeError):
            continue

    for depto, vals in inf_agg.items():
        inf_val = round(float(np.mean(vals)), 1)
        if depto in deptos:
            deptos[depto]["tasa_informalidad"] = inf_val
        else:
            deptos[depto] = {"tasa_informalidad": inf_val}

    # EMICRON
    for _, row in emicron.iterrows():
        dpto_raw = str(row.get("DPTO", row.get("DEPARTAMENTO", ""))).strip()
        # Padding a 2 dígitos (5 -> 05, 8 -> 08)
        if dpto_raw.isdigit() and len(dpto_raw) < 2:
            dpto_raw = dpto_raw.zfill(2)
        depto = _norm_depto(DANE_DEPTO.get(dpto_raw, "")) if dpto_raw else ""
        if not depto or depto in ("NACIONAL", "TOTAL"):
            continue
        if depto not in deptos:
            deptos[depto] = {}
        try:
            deptos[depto]["micronegocios"] = int(row.get("MICRONEGOCIOS", row.get("TOTAL", 0)) or 0)
        except (ValueError, TypeError):
            continue

    # Proyección desempleo futuro
    depto_proy: dict[str, float] = {}
    try:
        depto_preds = preds_geih.get("departamentos", {})
        for depto_name, series in depto_preds.items():
            dn = _norm(depto_name)
            if isinstance(series, dict) and "mediana" in series:
                vals = list(series["mediana"].values())
                if vals:
                    depto_proy[dn] = float(np.mean(vals[-6:]))  # promedio últimos 6 meses
    except Exception:
        pass

    # Calcular score compuesto
    for depto, d in deptos.items():
        desempleo = d.get("tasa_desempleo", 10)
        informalidad_val = d.get("tasa_informalidad", 50)
        dnp_val = d.get("dnp_desempeno", 50)
        ingreso = d.get("ingreso_promedio", SMMLV_2026)
        formalidad = d.get("tasa_formalidad", 50)
        proy_desempleo = depto_proy.get(depto, desempleo)

        # Normalizar y calcular score (0-100, mayor = más urgente)
        score_desempleo = min(35, (desempleo / 25) * 35)
        score_informal = min(25, (informalidad_val / 100) * 25)
        score_dnp = max(0, min(20, (100 - dnp_val) * 0.2))
        score_ingreso = max(0, min(10, (1 - ingreso / (SMMLV_2026 * 6)) * 10))
        score_proyeccion = min(10, (proy_desempleo / 20) * 10)

        score_total = score_desempleo + score_informal + score_dnp + score_ingreso + score_proyeccion
        d["score_prioridad"] = round(score_total, 1)
        d["score_desglose"] = {
            "desempleo": round(score_desempleo, 1),
            "informalidad": round(score_informal, 1),
            "dnp_desempeno": round(score_dnp, 1),
            "ingreso": round(score_ingreso, 1),
            "proyeccion": round(score_proyeccion, 1),
        }
        d["nombre"] = depto

    # Ordenar por score
    ranking = sorted(deptos.values(), key=lambda x: x.get("score_prioridad", 0), reverse=True)

    # Asignar nivel de urgencia
    for d in ranking:
        s = d.get("score_prioridad", 50)
        if s >= 70: d["nivel_urgencia"] = "Crítico"
        elif s >= 50: d["nivel_urgencia"] = "Alta"
        elif s >= 35: d["nivel_urgencia"] = "Media"
        else: d["nivel_urgencia"] = "Baja"

    # Recomendación de inversión
    top3 = ranking[:3]
    recomendaciones = []
    for d in top3:
        depto_name = d.get("nombre", d.get("DEPARTAMENTO", ""))
        monto = req.presupuesto_cop / 3
        recomendaciones.append({
            "departamento": depto_name,
            "inversion_sugerida_cop": round(monto, -6),
            "accion": _recomendar_accion_territorial(depto_name, d),
        })

    return {
        "total_departamentos": len(ranking),
        "presupuesto_referencia_cop": req.presupuesto_cop,
        "ranking": ranking,
        "top_prioritarios": ranking[:10],
        "recomendaciones_inversion": recomendaciones,
        "metodologia": "Score compuesto: desempleo (35%) + informalidad (25%) + DNP desempeño (20%) + ingreso (10%) + proyección Chronos T5 (10%)",
        "fuentes": ["GEIH", "DNP/MDM", "SNIES", "EMICRON", "Chronos T5"],
    }


def _recomendar_accion_territorial(depto: str, datos: dict) -> str:
    """Genera una recomendación de acción para un departamento."""
    desempleo = datos.get("tasa_desempleo", 10)
    informalidad = datos.get("tasa_informalidad", 50)
    dnp_val = datos.get("dnp_desempeno", 50)

    if desempleo > 15:
        return f"Priorizar formación para el empleo en {depto}. Enfocar inversión en programas técnicos y tecnológicos con alta demanda local."
    elif informalidad > 60:
        return f"Fortalecer el tejido empresarial formal en {depto}. Incentivos a microempresas y simplificación de trámites de formalización."
    elif dnp_val < 45:
        return f"Invertir en infraestructura institucional y capacitación de funcionarios en {depto}. Mejorar la gestión pública territorial."
    else:
        return f"Invertir en innovación y sectores emergentes en {depto}. Programas de emprendimiento y transformación digital."
