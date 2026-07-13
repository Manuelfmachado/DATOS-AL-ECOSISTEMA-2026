"""
Router del modulo Simulacion (Modulo #6).
Cinco simulaciones interactivas basadas en datos reales:

1. Trayectoria Profesional — programa academico + depto -> proyeccion salarial a 10 anos
2. Migracion Territorial — depto origen vs destino -> delta salarial, formalidad, desempleo
3. Reskilling / Transicion — ocupacion actual vs deseada -> brecha de habilidades + SENA
4. Demanda Sectorial — sliders de escenario -> proyeccion de empleo sectorial
5. Estudiar vs Trabajar vs Emprender — comparacion de 3 trayectorias a 10 anos
"""
import json
import math
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/simulacion", tags=["Simulacion"])

DATA = Path(__file__).resolve().parents[3] / "data" / "processed"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _clean_text(s: str) -> str:
    """Limpia texto con mojibake para mostrar. Devuelve mayúsculas sin acentos."""
    if not s:
        return s
    s = s.strip().upper()
    # Eliminar marcas diacríticas
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    # Remover artefactos comunes de mojibake
    for bad in ["\u00c2", "\u00bf", "\ufffd", "?"]:
        s = s.replace(bad, "")
    # Limpiar espacios múltiples
    while "  " in s:
        s = s.replace("  ", " ")
    return s.strip()


def _load_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Dataset {name} no disponible")
    return pd.read_csv(path)


def _load_json(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"Dataset {name} no disponible")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# Rangos salariales OLE -> valor medio en SMMLV (2026 = 1,750,000)
SMMLV_2026 = 1_750_000

RANGO_INGRESO_MEDIO_SMMLV: dict[str, float] = {
    "1 SMMLV": 1.0,
    "Entre 1 y 1,5 SMMLV": 1.25,
    "Entre 1,5 y 2,5 SMMLV": 2.0,
    "Entre 2,5 y 4 SMMLV": 3.25,
    "Entre 4 y 6 SMMLV": 5.0,
    "Entre 6 y 9 SMMLV": 7.5,
    "Mas de 9 SMMLV": 11.0,
    "Más de 9 SMMLV": 11.0,
}


def _rango_a_cop(rango: str) -> float:
    """Convierte un rango de ingreso OLE a COP promedio."""
    val = RANGO_INGRESO_MEDIO_SMMLV.get(rango.strip())
    if val is None:
        val = RANGO_INGRESO_MEDIO_SMMLV.get(_norm(rango), 2.0)
    return val * SMMLV_2026


# Mapeo CIIU2 -> nombre legible (subset principal)
CIIU2_NOMBRES: dict[str, str] = {
    "01": "Agricultura, ganadería",
    "10": "Alimentos",
    "11": "Bebidas",
    "13": "Textiles",
    "14": "Prendas de vestir",
    "20": "Productos químicos",
    "21": "Productos farmacéuticos",
    "23": "Minerales no metálicos",
    "24": "Metalurgia",
    "25": "Productos metálicos",
    "26": "Informática y electrónica",
    "27": "Material eléctrico",
    "28": "Maquinaria y equipo",
    "29": "Vehículos automotores",
    "35": "Electricidad y gas",
    "41": "Construcción de edificios",
    "42": "Obras de ingeniería civil",
    "43": "Construcción especializada",
    "45": "Comercio de vehículos",
    "46": "Comercio al por mayor",
    "47": "Comercio al por menor",
    "49": "Transporte terrestre",
    "50": "Transporte por agua",
    "51": "Transporte aéreo",
    "52": "Almacenamiento",
    "53": "Correo y mensajería",
    "55": "Alojamiento",
    "56": "Restaurantes y bebidas",
    "58": "Edición",
    "61": "Telecomunicaciones",
    "62": "Programación y consultoría",
    "63": "Servicios de información",
    "64": "Servicios financieros",
    "65": "Seguros",
    "66": "Actividades auxiliares financieras",
    "68": "Actividades inmobiliarias",
    "69": "Actividades jurídicas y contabilidad",
    "70": "Administración empresarial",
    "71": "Arquitectura e ingeniería",
    "72": "Investigación científica",
    "73": "Publicidad",
    "74": "Otras actividades profesionales",
    "75": "Veterinaria",
    "81": "Servicios a edificios",
    "82": "Servicios administrativos de oficina",
    "84": "Administración pública",
    "85": "Educación",
    "86": "Servicios de salud",
    "87": "Servicios de atención social",
    "90": "Artes creativas",
    "91": "Bibliotecas y museos",
    "93": "Actividades deportivas",
    "94": "Asociaciones",
    "95": "Reparación de equipos",
    "96": "Otros servicios personales",
    "97": "Actividades de los hogares",
    "99": "Organizaciones extraterritoriales",
}

# Mapeo de nombres de departamento con mojibake -> nombre limpio
DEPTO_FIX: dict[str, str] = {
    "AMAZONAS": "Amazonas",
    "ANTIOQUIA": "Antioquia",
    "ARAUCA": "Arauca",
    "ARCHIPI\u00c9LAGO DE SAN ANDR\u00c9S": "Archipiélago de San Andrés",
    "ATL\u00c1NTICO": "Atlántico",
    "BOGOT\u00c1": "Bogotá D.C.",
    "BOL\u00cdVAR": "Bolívar",
    "BOYAC\u00c1": "Boyacá",
    "CALDAS": "Caldas",
    "CAQUET\u00c1": "Caquetá",
    "CASANARE": "Casanare",
    "CAUCA": "Cauca",
    "CESAR": "Cesar",
    "CHOC\u00d3": "Chocó",
    "CUNDINAMARCA": "Cundinamarca",
    "C\u00d3RDOBA": "Córdoba",
    "GUAIN\u00cdA": "Guainía",
    "GUAVIARE": "Guaviare",
    "HUILA": "Huila",
    "LA GUAJIRA": "La Guajira",
    "MAGDALENA": "Magdalena",
    "META": "Meta",
    "NARI\u00d1O": "Nariño",
    "NORTE DE SANTANDER": "Norte de Santander",
    "PUTUMAYO": "Putumayo",
    "QUIND\u00cdO": "Quindío",
    "RISARALDA": "Risaralda",
    "SANTANDER": "Santander",
    "SUCRE": "Sucre",
    "TOLIMA": "Tolima",
    "VALLE DEL CAUCA": "Valle del Cauca",
    "VAUP\u00c9S": "Vaupés",
    "VICHADA": "Vichada",
}


def _fix_depto_name(raw: str) -> str:
    """Convierte un nombre de departamento con mojibake a su forma limpia."""
    if not raw:
        return raw
    upper = raw.upper().strip()
    return DEPTO_FIX.get(upper, raw.title())


# ── Mapeo de crecimiento por ocupación (SPE + Chronos) ─────────────────

_SPE_GROWTH_CACHE: dict[str, float] | None = None


def _build_spe_growth_map() -> dict[str, float]:
    """Construye un diccionario de palabra clave → tasa de crecimiento
    a partir de las 567 ocupaciones del SPE/APE con demanda real + keywords extra."""
    global _SPE_GROWTH_CACHE
    if _SPE_GROWTH_CACHE is not None:
        return _SPE_GROWTH_CACHE

    try:
        spe = pd.read_csv(DATA / "spe_ape_inscritos_ocupacion.csv")
    except Exception:
        _SPE_GROWTH_CACHE = {}
        return _SPE_GROWTH_CACHE

    spe = spe.dropna(subset=["variacion_pct", "ocupacion"])
    spe["ocupacion_norm"] = spe["ocupacion"].apply(_clean_text).apply(_norm)

    vari = spe["variacion_pct"]
    p25, p50, p75, p90 = vari.quantile(0.25), vari.quantile(0.50), vari.quantile(0.75), vari.quantile(0.90)

    def _growth_from_variacion(v: float) -> float:
        if v >= p90:
            return 0.060
        elif v >= p75:
            return 0.050
        elif v >= p50:
            return 0.042
        elif v >= p25:
            return 0.035
        else:
            return 0.025

    growth_map: dict[str, float] = {}
    for _, row in spe.iterrows():
        oc_norm = row["ocupacion_norm"]
        growth = _growth_from_variacion(float(row["variacion_pct"]))
        palabras = [w for w in oc_norm.split() if len(w) > 3]
        for kw in palabras:
            if kw not in growth_map or growth > growth_map[kw]:
                growth_map[kw] = growth

    extra = {
        "INGENIERIA": 0.048, "PROGRAMACION": 0.052, "DESARROLLO": 0.050,
        "MEDICINA": 0.045, "ENFERMERIA": 0.044, "DERECHO": 0.038,
        "ARQUITECTURA": 0.040, "DISEÑO": 0.042, "PSICOLOGIA": 0.038,
        "ECONOMIA": 0.042, "ADMINISTRACION": 0.040, "CONTADURIA": 0.035,
        "MERCADEO": 0.045, "COMUNICACION": 0.040, "BIOLOGIA": 0.038,
        "QUIMICA": 0.036, "FISICA": 0.037, "MATEMATICA": 0.040,
        "ESTADISTICA": 0.045, "AGRONOMIA": 0.035, "VETERINARIA": 0.040,
        "ODONTOLOGIA": 0.042, "NUTRICION": 0.042, "FARMACIA": 0.043,
        "TRABAJO SOCIAL": 0.038, "ANTROPOLOGIA": 0.035, "SOCIOLOGIA": 0.036,
        "FILOSOFIA": 0.033, "HISTORIA": 0.033, "LITERATURA": 0.033,
        "ARTES": 0.035, "MUSICA": 0.036, "DEPORTE": 0.040,
        "TURISMO": 0.042, "HOTELERIA": 0.040, "GASTRONOMIA": 0.043,
        "CONSTRUCCION": 0.038, "MINAS": 0.036, "PETROLEO": 0.040,
        "AMBIENTAL": 0.042, "SISTEMAS": 0.050, "INFORMATICA": 0.050,
        "SOFTWARE": 0.052, "REDES": 0.048, "TELECOMUNICACIONES": 0.046,
        "FINANZAS": 0.045, "FINANCIERA": 0.044, "BANCA": 0.042,
        "LOGISTICA": 0.043, "RECURSOS HUMANOS": 0.040, "TALENTO HUMANO": 0.040,
        "EDUCACION": 0.040, "PEDAGOGIA": 0.038, "DOCENCIA": 0.037,
        "ENERGIA": 0.045, "RENOVABLE": 0.046, "SOSTENIBLE": 0.044,
    }
    for kw, growth in extra.items():
        if kw not in growth_map or growth > growth_map[kw]:
            growth_map[kw] = growth

    _SPE_GROWTH_CACHE = growth_map
    return _SPE_GROWTH_CACHE


# ── Matching de programa → profesión Chronos (21 profesiones pre-calculadas) ─

_CHRONOS_PROFS_CACHE: list[dict] | None = None


def _load_chronos_professions() -> list[dict]:
    """Carga las 21 profesiones con su crecimiento desde predicciones_mundiales.json."""
    global _CHRONOS_PROFS_CACHE
    if _CHRONOS_PROFS_CACHE is not None:
        return _CHRONOS_PROFS_CACHE
    try:
        pred = _load_json("predicciones_mundiales.json")
        _CHRONOS_PROFS_CACHE = pred.get("profesiones", [])
    except Exception:
        _CHRONOS_PROFS_CACHE = []
    return _CHRONOS_PROFS_CACHE


def _chronos_rate(profesion_nombre: str) -> float | None:
    """Busca la tasa de crecimiento de una profesión Chronos por nombre."""
    for p in _load_chronos_professions():
        if _norm(p.get("profesion", "")) == _norm(profesion_nombre):
            return p.get("crecimiento_anual_pct", None)
    return None


# Mapa ordenado de keyword(s) → nombre de profesión Chronos.
# Ordenado por especificidad (frases multi-palabra primero). Primer match gana.
# Las tasas se leen del JSON (Chronos), no van hardcodeadas aquí.
_CHRONOS_KW_MAP: list[tuple[str, str]] = [
    # ── Frases específicas (alta especificidad) ──
    ("CIENCIA DE DATOS", "Científico de datos / IA"),
    ("CIENCIA DE LA INFORMACION", "Científico de datos / IA"),
    ("INTELIGENCIA ARTIFICIAL", "Científico de datos / IA"),
    ("MACHINE LEARNING", "Científico de datos / IA"),
    ("ANALITICA DE DATOS", "Científico de datos / IA"),
    ("BIG DATA", "Científico de datos / IA"),
    ("MARKETING DIGITAL", "Especialista en marketing digital"),
    ("MERCADEO DIGITAL", "Especialista en marketing digital"),
    ("DIGITAL MARKETING", "Especialista en marketing digital"),
    ("CIBERSEGURIDAD", "Especialista en ciberseguridad"),
    ("SEGURIDAD INFORMATICA", "Especialista en ciberseguridad"),
    ("SEGURIDAD DE LA INFORMACION", "Especialista en ciberseguridad"),
    ("ENERGIAS RENOVABLES", "Técnico en energías renovables"),
    ("ENERGIA RENOVABLE", "Técnico en energías renovables"),
    ("ENERGIAS LIMPIAS", "Técnico en energías renovables"),
    ("CADENA DE SUMINISTRO", "Técnico logístico / cadena de suministro"),
    ("LOGISTICA INTEGRAL", "Técnico logístico / cadena de suministro"),
    ("RECURSOS HUMANOS", "Profesional en recursos humanos"),
    ("GESTION HUMANA", "Profesional en recursos humanos"),
    ("TALENTO HUMANO", "Profesional en recursos humanos"),
    ("GESTION DE PROYECTOS", "Gestor(a) de proyectos"),
    ("GERENCIA DE PROYECTOS", "Gestor(a) de proyectos"),
    ("PROJECT MANAGEMENT", "Gestor(a) de proyectos"),
    ("DIRECCION DE PROYECTOS", "Gestor(a) de proyectos"),
    ("DESARROLLO DE SOFTWARE", "Desarrollador de software"),
    ("INGENIERIA DE SOFTWARE", "Desarrollador de software"),
    ("INGENIERIA DE SISTEMAS", "Desarrollador de software"),
    ("INGENIERIA DE SISTEMAS E INFORMATICA", "Desarrollador de software"),
    ("INGENIERIA INFORMATICA", "Desarrollador de software"),
    ("TECNOLOGIAS DE LA INFORMACION", "Desarrollador de software"),
    ("TECNOLOGIAS DE INFORMACION", "Desarrollador de software"),
    ("SISTEMAS DE INFORMACION", "Desarrollador de software"),
    ("INGENIERIA DE DATOS", "Científico de datos / IA"),
    ("INTELIGENCIA DE NEGOCIOS", "Científico de datos / IA"),
    ("COMPUTACION EN LA NUBE", "Ingeniero de nube / DevOps"),
    ("INGENIERIA DE NUBE", "Ingeniero de nube / DevOps"),
    ("ARQUITECTURA DE NUBE", "Ingeniero de nube / DevOps"),
    ("DISENO UX", "Diseñador UX / UI"),
    ("DISENO UI", "Diseñador UX / UI"),
    ("INTERACCION HUMANO COMPUTADOR", "Diseñador UX / UI"),
    ("DISENO GRAFICO", "Diseñador UX / UI"),
    ("DISENO DIGITAL", "Diseñador UX / UI"),
    ("EDUCACION TECNICA", "Profesor(a) de educación técnica"),
    ("EDUCACION TECNOLOGICA", "Profesor(a) de educación técnica"),
    ("PEDAGOGIA", "Profesor(a) de educación técnica"),
    ("DOCENCIA", "Profesor(a) de educación técnica"),
    ("AGROPECUARIO", "Técnico agropecuario sostenible"),
    ("AGROINDUSTRIA", "Técnico agropecuario sostenible"),
    ("DESARROLLO AGROPECUARIO", "Técnico agropecuario sostenible"),
    # ── Palabras clave simples (baja especificidad, >=4 chars) ──
    ("SOFTWARE", "Desarrollador de software"),
    ("PROGRAMACION", "Desarrollador de software"),
    ("INFORMATICA", "Desarrollador de software"),
    ("COMPUTACION", "Desarrollador de software"),
    ("SISTEMAS", "Desarrollador de software"),
    ("ELECTRICA", "Ingeniero(a) eléctrico(a)"),
    ("ELECTRONICA", "Ingeniero(a) eléctrico(a)"),
    ("ENFERMERIA", "Enfermero(a) profesional"),
    ("CONTADURIA", "Contador(a) / auditor(a)"),
    ("CONTABILIDAD", "Contador(a) / auditor(a)"),
    ("AUDITORIA", "Contador(a) / auditor(a)"),
    ("LOGISTICA", "Técnico logístico / cadena de suministro"),
    ("AGRONOMIA", "Técnico agropecuario sostenible"),
    ("AGRICOLA", "Técnico agropecuario sostenible"),
    ("MARKETING", "Especialista en marketing digital"),
    ("MERCADEO", "Especialista en marketing digital"),
    ("PUBLICIDAD", "Especialista en marketing digital"),
    ("FINANZAS", "Analista financiero"),
    ("FINANCIERA", "Analista financiero"),
    ("DATOS", "Científico de datos / IA"),
    ("ANALITICA", "Científico de datos / IA"),
    ("LICENCIATURA", "Profesor(a) de educación técnica"),
    ("EDUCACION", "Profesor(a) de educación técnica"),
    # Negativas (declinantes) — solo si el programa es claramente oficio tradicional
    ("CONDUCCION", "Conductor(a) de vehículos (sin automatización)"),
    ("AGRICULTURA TRADICIONAL", "Agricultor(a) tradicional"),
    ("MANUFACTURA", "Operario(a) de manufactura tradicional"),
    ("CAJERO", "Cajero(a) / atención al cliente básica"),
    ("ATENCION AL CLIENTE", "Cajero(a) / atención al cliente básica"),
]


def _match_chronos(programa_norm: str) -> tuple[str, float] | None:
    """Matchea un programa normalizado a una profesión Chronos.
    Devuelve (nombre_profesion, tasa_crecimiento) o None."""
    for keyword, prof_name in _CHRONOS_KW_MAP:
        if keyword in programa_norm:
            rate = _chronos_rate(prof_name)
            if rate is not None:
                return (prof_name, rate / 100.0)
    return None


# ---------------------------------------------------------------------------
# 1. TRAYECTORIA PROFESIONAL
# ---------------------------------------------------------------------------

class TrayectoriaRequest(BaseModel):
    programa: str
    departamento: str = "Bogotá D.C."
    nivel_educativo: str | None = None  # Si no se envía, se infiere del nombre del programa


class TrayectoriaResponse(BaseModel):
    programa: str
    departamento: str
    nivel_detectado: str
    salario_base_ole_cop: float
    salario_inicial_cop: float
    salario_inicial_rango: str
    calidad_saberpro: float | None = None
    ajuste_territorial: float
    profesion_chronos: str = ""
    fuente_crecimiento: str = ""
    anos: list[int]
    mediana: list[float]
    p10: list[float]
    p90: list[float]
    crecimiento_anual_pct: float
    salario_5a_cop: float
    salario_10a_cop: float
    recomendacion: str
    desglose: str


@router.post("/trayectoria", response_model=TrayectoriaResponse)
async def sim_trayectoria(req: TrayectoriaRequest):
    """Simula la trayectoria salarial a 10 años de un egresado de un programa académico."""
    programa_norm = _norm(req.programa)
    depto_norm = _norm(req.departamento)

    # Inferir nivel educativo del nombre del programa si no se envía
    nivel = req.nivel_educativo
    if not nivel:
        pn = programa_norm
        if "DOCTORADO" in pn:
            nivel = "Doctorado"
        elif "MAESTRIA" in pn or "MAESTRÍA" in pn:
            nivel = "Maestria"
        elif "ESPECIALIZACION" in pn or "ESPECIALIZACIÓN" in pn:
            nivel = "Especializacion"
        elif "TECNOLOGIA" in pn or "TECNOL" in pn:
            nivel = "Tecnologo"
        elif "TECNICO" in pn or "TÉCNICO" in pn:
            nivel = "Tecnico"
        else:
            nivel = "Universitario"

    # 1. Salario inicial desde OLE (rango más frecuente)
    ole = _load_csv("ole_ingresos_por_programa.csv")
    ole["programa"] = ole["programa"].astype(str).str.strip().apply(_clean_text)
    ole["_prog_norm"] = ole["programa"].apply(_norm)
    prog_rows = ole[ole["_prog_norm"].str.contains(programa_norm, na=False)]
    if prog_rows.empty:
        # fallback: usar OLE por nivel
        ole_nivel = _load_csv("ole_ingresos_por_nivel.csv")
        nivel_map = {
            "Tecnico": "Formación Técnica Profesional",
            "Tecnologo": "Formación Tecnológica",
            "Universitario": "Universitaria",
            "Especializacion": "Especialización",
            "Maestria": "Maestría",
            "Doctorado": "Doctorado",
        }
        nivel_buscar = nivel_map.get(req.nivel_educativo, "Universitaria")
        nivel_rows = ole_nivel[ole_nivel["nivel_formacion"].apply(_norm) == _norm(nivel_buscar)]
        if nivel_rows.empty:
            salario_inicial = 2.0 * SMMLV_2026
            rango_label = "Estimado (~2 SMMLV)"
        else:
            top = nivel_rows.sort_values("graduados", ascending=False).iloc[0]
            salario_inicial = _rango_a_cop(top["rango_ingreso"])
            rango_label = top["rango_ingreso"]
    else:
        # rango más común (mayor nº de graduados)
        top = prog_rows.sort_values("graduados", ascending=False).iloc[0]
        salario_inicial = _rango_a_cop(top["rango_ingreso"])
        rango_label = top["rango_ingreso"]

    # 2. Factor de calidad desde SaberPro
    calidad = None
    try:
        saber = _load_csv("saberpro_resumen_programas.csv")
        saber["_prog_norm"] = saber["programa"].apply(_norm)
        sp_rows = saber[saber["_prog_norm"].str.contains(programa_norm, na=False)]
        if not sp_rows.empty:
            cols_notas = [c for c in sp_rows.columns if c.startswith("MOD_") and c.endswith("_PUNT")]
            if cols_notas:
                calidad = float(sp_rows[cols_notas].mean(axis=1).mean())
    except Exception:
        pass

    # Ajuste por calidad SaberPro: promedio nacional ~150, rango 0-300
    factor_calidad = 1.0
    if calidad is not None:
        factor_calidad = 0.90 + (calidad / 300) * 0.20  # 0.90 - 1.10

    # 3. Ajuste territorial desde GEIH (cap más conservador: 0.8 - 1.2)
    geih_depto = _load_csv("geih_resumen_departamento.csv")
    geih_depto["_depto_norm"] = geih_depto["departamento"].apply(lambda d: _norm(_fix_depto_name(d)))
    depto_row = geih_depto[geih_depto["_depto_norm"] == depto_norm]
    if depto_row.empty:
        for raw_name in geih_depto["departamento"]:
            if _norm(_fix_depto_name(raw_name)) == depto_norm:
                depto_row = geih_depto[geih_depto["departamento"] == raw_name]
                break
    if depto_row.empty:
        ajuste_territorial = 1.0
    else:
        ingreso_depto = float(depto_row.iloc[0]["ingreso_promedio"])
        ingreso_nacional = float(geih_depto["ingreso_promedio"].mean())
        ajuste_territorial = max(0.80, min(1.20, ingreso_depto / ingreso_nacional))

    salario_ole = salario_inicial
    salario_base = salario_ole * factor_calidad * ajuste_territorial

    # 4. Crecimiento: Chronos T5 (21 profesiones) → SPE/APE (567 ocupaciones) → baseline 3.5%
    pred = _load_json("predicciones_mundiales.json")
    crec_base = pred.get("salarios", {}).get("crecimiento_anual_pct", 3.5) / 100  # 3.5% baseline Chronos

    crec_chronos = crec_base
    profesion_chronos = "Baseline general"
    fuente_crec = "Chronos T5 (baseline general)"

    # 4a. Chronos: match programa → una de las 21 profesiones pre-calculadas
    match_chronos = _match_chronos(programa_norm)
    if match_chronos is not None:
        profesion_chronos, crec_chronos = match_chronos
        fuente_crec = f"Chronos T5 (profesión: {profesion_chronos})"
    else:
        # 4b. SPE/APE: si no hay match Chronos, usar mapa de demanda por ocupación
        spe_map = _build_spe_growth_map()
        programa_palabras = [w for w in programa_norm.split() if len(w) > 3]
        for palabra in programa_palabras:
            if palabra in spe_map:
                crec_chronos = spe_map[palabra]
                fuente_crec = f"SPE/APE (demanda por ocupación: {palabra})"
                break

    # Ajuste por nivel educativo (+/- 0.5% por nivel respecto a universitario)
    ajuste_nivel = {
        "Tecnico": -0.010,
        "Tecnologo": -0.005,
        "Universitario": 0.0,
        "Especializacion": 0.005,
        "Maestria": 0.010,
        "Doctorado": 0.015,
    }
    crec_anual = crec_chronos + ajuste_nivel.get(nivel, 0.0)

    # 5. Monte Carlo: 1000 trayectorias con volatilidad
    rng = np.random.default_rng(42)
    n_sim = 1000
    anos = list(range(0, 11))
    volatilidad = 0.035  # desviación del crecimiento anual

    trayectorias = np.zeros((n_sim, 11))
    trayectorias[:, 0] = salario_base
    for s in range(n_sim):
        for y in range(1, 11):
            shock = rng.normal(0, volatilidad)
            crec_real = max(-0.02, crec_anual + shock)
            trayectorias[s, y] = trayectorias[s, y - 1] * (1 + crec_real)

    mediana = np.median(trayectorias, axis=0).tolist()
    p10 = np.percentile(trayectorias, 10, axis=0).tolist()
    p90 = np.percentile(trayectorias, 90, axis=0).tolist()

    salario_5a = mediana[5]
    salario_10a = mediana[10]
    crec_pct = crec_anual * 100

    # Recomendación simple y concreta
    recomendacion = (
        f"Estudiando {req.programa} en {req.departamento}, es probable que empieces ganando "
        f"{format(round(salario_base), ',').replace(',', '.')} COP al mes. "
        f"En 10 años, tu salario podría llegar a aproximadamente "
        f"{format(round(salario_10a), ',').replace(',', '.')} COP "
        f"con un crecimiento estimado del {crec_anual*100:.1f}% anual "
        f"({fuente_crec})."
    )

    # Desglose (no crítico, se ignora si falla)
    try:
        desglose = (
            f"Salario OLE: {int(salario_ole or 0):,} COP ({rango_label}). "
            f"SaberPro {factor_calidad:.2f} x Ajuste territorial {ajuste_territorial:.2f}. "
            f"Crecimiento: {crec_anual*100:.1f}% — {fuente_crec} (nivel {nivel})."
        )
    except Exception:
        desglose = "No disponible"

    return TrayectoriaResponse(
        programa=req.programa,
        departamento=req.departamento,
        nivel_detectado=nivel,
        salario_base_ole_cop=round(salario_ole or 0),
        salario_inicial_cop=round(salario_base or 0),
        salario_inicial_rango=rango_label or "Estimado",
        calidad_saberpro=round(calidad, 1) if calidad else None,
        ajuste_territorial=round(ajuste_territorial, 2),
        profesion_chronos=profesion_chronos,
        fuente_crecimiento=fuente_crec,
        anos=anos,
        mediana=[round(v) for v in mediana],
        p10=[round(v) for v in p10],
        p90=[round(v) for v in p90],
        crecimiento_anual_pct=round(crec_anual * 100, 1),
        salario_5a_cop=round(salario_5a),
        salario_10a_cop=round(salario_10a),
        recomendacion=recomendacion,
        desglose=desglose,
    )


@router.get("/trayectoria/programas")
async def listar_programas(q: str = "", limit: int = 50, incluir_posgrado: bool = True):
    """Lista programas académicos ordenados por relevancia y popularidad.

    Ordenamiento:
      1. Empiezan con la query y son más populares (graduados)
      2. Contienen la query y son más populares
      3. Doctorados/maestrías/especializaciones quedan al final a menos que
         empiecen directamente con la query.
    """
    ole = _load_csv("ole_ingresos_por_programa.csv")
    ole["programa_raw"] = ole["programa"].astype(str).str.strip()
    ole["programa"] = ole["programa_raw"].apply(_clean_text)
    ole["_prog_norm"] = ole["programa"].apply(_norm)

    # Popularidad por programa limpio
    popularidad = ole.groupby("programa")["graduados"].sum()

    programas = ole["programa"].dropna().unique().tolist()
    q_norm = _norm(q)

    def _score(p: str) -> float:
        pn = _norm(p)
        if q and q_norm not in pn:
            return -1.0
        score = 0.0
        # Empieza exactamente con la query: muy relevante
        if pn.startswith(q_norm):
            score += 1_000_000
        # Contiene la query como palabra completa
        elif f" {q_norm}" in pn or f"-{q_norm}" in pn:
            score += 500_000
        # Penalizar posgrado si no se pide explícitamente (pero menos si es match al inicio)
        posgrado_keywords = ("DOCTORADO", "MAESTRIA", "ESPECIALIZACION", "ESPECIALIZACIÓN", "DOCTORATE", "MASTER")
        if any(k in pn for k in posgrado_keywords):
            if not incluir_posgrado and not pn.startswith(q_norm):
                return -1.0
            if not pn.startswith(q_norm):
                score -= 200_000
        # Popularidad: más graduados = mejor
        score += float(popularidad.get(p, 0)) / 100.0
        return score

    scored = [(p, _score(p)) for p in programas if _score(p) >= 0]
    scored.sort(key=lambda x: -x[1])

    resultado = [p for p, _ in scored]
    return {"programas": resultado[:limit], "total": len(resultado)}


@router.get("/trayectoria/programas-populares")
async def programas_populares(limit: int = 24):
    """Programas más populares por número de graduados (OLE)."""
    ole = _load_csv("ole_ingresos_por_programa.csv")
    ole["programa"] = ole["programa"].astype(str).str.strip().apply(_clean_text)
    agg = ole.groupby("programa")["graduados"].sum().sort_values(ascending=False).head(limit)
    resultado = [{"programa": p, "graduados": int(v)} for p, v in agg.items()]
    return {"programas": resultado}


@router.get("/trayectoria/departamentos")
async def listar_departamentos():
    """Lista departamentos disponibles."""
    geih = _load_csv("geih_resumen_departamento.csv")
    deptos_raw = geih["departamento"].dropna().unique().tolist()
    deptos = sorted([_fix_depto_name(d) for d in deptos_raw])
    return {"departamentos": deptos}


# ---------------------------------------------------------------------------
# 2. MIGRACION TERRITORIAL
# ---------------------------------------------------------------------------

class MigracionRequest(BaseModel):
    departamento_origen: str
    departamento_destino: str


@router.post("/migracion")
async def sim_migracion(req: MigracionRequest):
    """Compara indicadores laborales entre dos departamentos."""
    geih = _load_csv("geih_resumen_departamento.csv")
    geih["_depto_norm"] = geih["departamento"].apply(lambda d: _norm(_fix_depto_name(d)))

    orig_norm = _norm(req.departamento_origen)
    dest_norm = _norm(req.departamento_destino)

    row_orig = geih[geih["_depto_norm"] == orig_norm]
    row_dest = geih[geih["_depto_norm"] == dest_norm]

    if row_orig.empty or row_dest.empty:
        raise HTTPException(status_code=404, detail="Departamento no encontrado. Usa GET /simulacion/trayectoria/departamentos para ver los disponibles.")

    o = row_orig.iloc[0]
    d = row_dest.iloc[0]

    # Usar nombre limpio en la respuesta
    o_nombre = _fix_depto_name(str(o["departamento"]))
    d_nombre = _fix_depto_name(str(d["departamento"]))

    # Desempleo por departamento
    desempleo = _load_csv("geih_desempleo_departamento.csv")
    desempleo["_depto_norm"] = desempleo["DPTO"].astype(str)
    # Buscar último periodo por departamento
    desempleo_ult = desempleo.sort_values("periodo", ascending=False).drop_duplicates("_depto_norm", keep="first")

    def _tasa_desempleo(depto_norm: str) -> float | None:
        # GEIH resumen no tiene tasa directa; usar aproximación desde desempleo depto
        # DPTO es código numérico, no nombre. Como fallback, estimar.
        return None

    delta_salario = float(d["ingreso_promedio"]) - float(o["ingreso_promedio"])
    delta_salario_pct = (delta_salario / float(o["ingreso_promedio"])) * 100 if float(o["ingreso_promedio"]) > 0 else 0
    delta_formalidad = (float(d["tasa_formalidad"]) - float(o["tasa_formalidad"])) * 100
    delta_educacion = float(d["pct_educacion_superior"]) - float(o["pct_educacion_superior"])

    # Score de atractivo 0-100
    score = 50
    score += delta_salario_pct * 0.5
    score += delta_formalidad * 0.8
    score += delta_educacion * 0.3
    score = max(0, min(100, score))

    if score >= 65:
        veredicto = "Mudarse es favorable: mejores condiciones laborales en el destino."
    elif score >= 45:
        veredicto = "Mudanza neutral: condiciones similares. Considera costo de vida."
    else:
        veredicto = "Mudanza desfavorable: el origen tiene mejores condiciones laborales."

    return {
        "origen": {
            "departamento": o_nombre,
            "ingreso_promedio": round(float(o["ingreso_promedio"])),
            "ingreso_mediano": round(float(o["ingreso_mediano"])),
            "tasa_formalidad_pct": round(float(o["tasa_formalidad"]) * 100, 1),
            "pct_educacion_superior": round(float(o["pct_educacion_superior"]), 1),
            "ocupados": int(float(o["ocupados"])),
            "nivel_educativo": o.get("nivel_educativo_etiqueta", "N/D"),
        },
        "destino": {
            "departamento": d_nombre,
            "ingreso_promedio": round(float(d["ingreso_promedio"])),
            "ingreso_mediano": round(float(d["ingreso_mediano"])),
            "tasa_formalidad_pct": round(float(d["tasa_formalidad"]) * 100, 1),
            "pct_educacion_superior": round(float(d["pct_educacion_superior"]), 1),
            "ocupados": int(float(d["ocupados"])),
            "nivel_educativo": d.get("nivel_educativo_etiqueta", "N/D"),
        },
        "delta": {
            "salario_cop": round(delta_salario),
            "salario_pct": round(delta_salario_pct, 1),
            "formalidad_pct": round(delta_formalidad, 1),
            "educacion_pct": round(delta_educacion, 1),
        },
        "score_atractivo": round(score, 1),
        "veredicto": veredicto,
    }


# ---------------------------------------------------------------------------
# 3. RESKILLING / TRANSICION LABORAL
# ---------------------------------------------------------------------------

class ReskillingRequest(BaseModel):
    ocupacion_actual: str
    ocupacion_deseada: str


@router.post("/reskilling")
async def sim_reskilling(req: ReskillingRequest):
    """Compara habilidades entre dos ocupaciones (ESCO) y recomienda programas SENA."""
    esc = _load_csv("esco_ocupacion_habilidades.csv")
    esc["_ocup_norm"] = esc["ocupacion_nombre"].apply(_norm)

    act_norm = _norm(req.ocupacion_actual)
    des_norm = _norm(req.ocupacion_deseada)

    act_rows = esc[esc["_ocup_norm"].str.contains(act_norm, na=False)]
    des_rows = esc[esc["_ocup_norm"].str.contains(des_norm, na=False)]

    if act_rows.empty or des_rows.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Ocupacion no encontrada en ESCO. Usa GET /simulacion/reskilling/ocupaciones para ver disponibles.",
        )

    act_habs = set(act_rows["habilidad_nombre"].dropna().unique())
    des_habs = set(des_rows["habilidad_nombre"].dropna().unique())

    coinciden = act_habs & des_habs
    faltan = des_habs - act_habs
    sobran = act_habs - des_habs

    overlap_pct = (len(coinciden) / len(des_habs) * 100) if des_habs else 0

    # Buscar programas SENA que cubran las habilidades faltantes
    sena = _load_csv("sena_programas_activos.csv")
    sena["_prog_norm"] = sena["programa"].apply(_norm)
    recomendaciones = []
    for hab in list(faltan)[:5]:
        hab_words = [w for w in _norm(hab).split() if len(w) > 3]
        if not hab_words:
            continue
        mask = sena["_prog_norm"].apply(lambda p: any(w in str(p).upper() for w in hab_words))
        matches = sena[mask].head(3)
        for _, row in matches.iterrows():
            recomendaciones.append({
                "habilidad_faltante": hab,
                "programa_sena": row["programa"],
                "departamento": row.get("departamento", "N/D"),
                "duracion_horas": float(row.get("duracion_horas", 0) or 0),
                "costo": float(row.get("costo", 0) or 0),
            })

    # Habilidades del WEF que son críticas
    pred = _load_json("predicciones_mundiales.json")
    habs_wef = {h["habilidad"]: h["demanda"] for h in pred.get("habilidades", [])}
    faltan_criticas = [(h, habs_wef[h]) for h in faltan if h in habs_wef]
    faltan_criticas.sort(key=lambda x: -x[1])

    # Veredicto
    if overlap_pct >= 70:
        veredicto = f"Transición fácil: ya tienes {overlap_pct:.0f}% de las habilidades necesarias."
    elif overlap_pct >= 40:
        veredicto = f"Transición moderada: tienes {overlap_pct:.0f}%. Necesitas desarrollar {len(faltan)} habilidades."
    else:
        veredicto = f"Transición retadora: solo tienes {overlap_pct:.0f}%. Requieres capacitación significativa en {len(faltan)} habilidades."

    return {
        "ocupacion_actual": req.ocupacion_actual,
        "ocupacion_deseada": req.ocupacion_deseada,
        "habilidades_actuales": len(act_habs),
        "habilidades_deseadas": len(des_habs),
        "habilidades_coinciden": sorted(list(coinciden))[:20],
        "habilidades_faltan": sorted(list(faltan))[:20],
        "habilidades_sobran": sorted(list(sobran))[:10],
        "overlap_pct": round(overlap_pct, 1),
        "faltan_criticas_wef": [{"habilidad": h, "demanda_wef": d} for h, d in faltan_criticas[:5]],
        "programas_sena_recomendados": recomendaciones[:10],
        "veredicto": veredicto,
    }


@router.get("/reskilling/ocupaciones")
async def listar_ocupaciones(q: str = "", limit: int = 50):
    """Lista ocupaciones disponibles en ESCO para el simulador."""
    esc = _load_csv("esco_ocupacion_habilidades.csv")
    ocupaciones = esc["ocupacion_nombre"].dropna().unique().tolist()
    if q:
        q_norm = _norm(q)
        ocupaciones = [o for o in ocupaciones if q_norm in _norm(o)]
    ocupaciones.sort()
    return {"ocupaciones": ocupaciones[:limit], "total": len(ocupaciones)}


# ---------------------------------------------------------------------------
# 4. DEMANDA SECTORIAL (escenarios)
# ---------------------------------------------------------------------------

class EscenarioRequest(BaseModel):
    sector_ciiu: str = "47"  # CIIU2
    crecimiento_pib_pct: float = 3.0  # -5 a 10
    inflacion_pct: float = 5.0
    inversion_pct: float = 0.0  # -20 a 20, shock de inversión


@router.post("/demanda-sectorial")
async def sim_demanda_sectorial(req: EscenarioRequest):
    """Simula el impacto de un escenario macroeconómico en el empleo sectorial."""
    geih_sector = _load_csv("geih_empleo_sector_mensual.csv")
    sector_rows = geih_sector[geih_sector["rama_ciiu"].astype(str) == req.sector_ciiu].sort_values("periodo")

    if sector_rows.empty:
        raise HTTPException(status_code=404, detail=f"Sector CIIU {req.sector_ciiu} no tiene datos. Disponibles: 1, 47, 56, 49, 41")

    # Último valor de empleo
    empleo_actual = float(sector_rows.iloc[-1]["empleo"])
    salario_actual = float(sector_rows.iloc[-1].get("salario_promedio", 0) or 0)

    # Cargar predicción GEIH del sector
    pred_geih = _load_json("predicciones_geih.json")
    sector_key = str(int(float(req.sector_ciiu)))
    sector_pred = pred_geih.get("sectores", {}).get(sector_key, {})

    # Sensibilidad: cada 1% de PIB -> 0.4% empleo; cada 1% inflación -> -0.15% empleo
    factor_pib = req.crecimiento_pib_pct * 0.004
    factor_inflacion = req.inflacion_pct * -0.0015
    factor_inversion = req.inversion_pct * 0.002

    ajuste = 1 + factor_pib + factor_inflacion + factor_inversion

    # Proyectar 12 meses con el ajuste del escenario
    meses = list(range(1, 13))
    pred_base = sector_pred.get("prediccion_1ano", [])
    proyeccion_base = [p.get("mediana", empleo_actual) for p in pred_base]
    proyeccion_escenario = [v * ajuste for v in proyeccion_base]
    if len(proyeccion_escenario) < 12:
        # fallback: crecimiento lineal
        crec_mensual = (ajuste - 1) / 12
        proyeccion_escenario = [empleo_actual * (1 + crec_mensual * m) for m in meses]

    empleo_final = proyeccion_escenario[-1]
    delta_pct = ((empleo_final - empleo_actual) / empleo_actual) * 100 if empleo_actual > 0 else 0

    # Salario proyectado (crece con inflación + productividad)
    salario_final = salario_actual * (1 + req.inflacion_pct / 100 * 0.8 + req.crecimiento_pib_pct / 100 * 0.2)

    nombre_sector = CIIU2_NOMBRES.get(sector_key, f"Sector CIIU {sector_key}")

    if delta_pct > 5:
        veredicto = f"Escenario favorable para {nombre_sector}: el empleo crecería {delta_pct:+.1f}%."
    elif delta_pct > -2:
        veredicto = f"Escenario neutral para {nombre_sector}: el empleo se mantendría estable ({delta_pct:+.1f}%)."
    else:
        veredicto = f"Escenario adverso para {nombre_sector}: el empleo caería {delta_pct:+.1f}%."

    return {
        "sector_ciiu": sector_key,
        "sector_nombre": nombre_sector,
        "empleo_actual": round(empleo_actual),
        "empleo_proyectado_12m": round(empleo_final),
        "delta_empleo_pct": round(delta_pct, 1),
        "salario_actual": round(salario_actual),
        "salario_proyectado_12m": round(salario_final),
        "delta_salario_pct": round(((salario_final / salario_actual - 1) * 100) if salario_actual > 0 else 0, 1),
        "meses": meses,
        "proyeccion_base": [round(v) for v in proyeccion_base[:12]],
        "proyeccion_escenario": [round(v) for v in proyeccion_escenario[:12]],
        "parametros": {
            "crecimiento_pib_pct": req.crecimiento_pib_pct,
            "inflacion_pct": req.inflacion_pct,
            "inversion_pct": req.inversion_pct,
        },
        "veredicto": veredicto,
    }


@router.get("/demanda-sectorial/sectores")
async def listar_sectores_ciiu():
    """Lista sectores CIIU disponibles para el simulador."""
    geih = _load_csv("geih_empleo_sector_mensual.csv")
    codigos = geih["rama_ciiu"].dropna().unique().tolist()
    codigos_str = [str(int(float(c))) for c in codigos]
    sectores = [{"codigo": c, "nombre": CIIU2_NOMBRES.get(c, f"CIIU {c}")} for c in sorted(set(codigos_str))]
    return {"sectores": sectores}


# ---------------------------------------------------------------------------
# 5. ESTUDIAR vs TRABAJAR vs EMPRENDER
# ---------------------------------------------------------------------------

class DecisionRequest(BaseModel):
    edad: int = 20
    nivel_educativo_actual: str = "Bachiller"  # Bachiller, Tecnico, Tecnologo, Universitario
    departamento: str = "BOGOTÁ"
    sector_interes: str = "Servicios"  # Agricultura, Industria, Servicios
    capital_disponible_cop: float = 0


@router.post("/decision")
async def sim_decision(req: DecisionRequest):
    """Compara 3 trayectorias a 10 años: estudiar, trabajar o emprender."""
    geih = _load_csv("geih_resumen_departamento.csv")
    geih["_depto_norm"] = geih["departamento"].apply(lambda d: _norm(_fix_depto_name(d)))
    depto_row = geih[geih["_depto_norm"] == _norm(req.departamento)]
    ingreso_depto = float(depto_row.iloc[0]["ingreso_promedio"]) if not depto_row.empty else 1_800_000
    formalidad_depto = float(depto_row.iloc[0]["tasa_formalidad"]) if not depto_row.empty else 0.3

    # Crecimiento salarial por nivel
    nivel_crec = {
        "Bachiller": 0.015,
        "Tecnico": 0.025,
        "Tecnologo": 0.030,
        "Universitario": 0.035,
    }

    # Salario inicial por nivel (ajustado al depto)
    nivel_salario_base = {
        "Bachiller": 1.0,
        "Tecnico": 1.3,
        "Tecnologo": 1.6,
        "Universitario": 2.2,
    }
    salario_actual = nivel_salario_base.get(req.nivel_educativo_actual, 1.0) * SMMLV_2026

    anos = list(range(0, 11))

    # --- Trayectoria 1: Estudiar (invierte 2-5 años, luego gana más) ---
    anos_estudio = 5 if req.nivel_educativo_actual == "Bachiller" else 2
    salario_estudio_base = nivel_salario_base.get(req.nivel_educativo_actual, 1.0) * SMMLV_2026
    # Durante el estudio: ingreso bajo (medio tiempo)
    tray_estudiar = []
    for y in anos:
        if y < anos_estudio:
            tray_estudiar.append(salario_estudio_base * 0.3)  # medio tiempo
        else:
            nivel_final = "Universitario" if req.nivel_educativo_actual in ("Bachiller", "Tecnico") else "Especializacion"
            sal_final = nivel_salario_base.get(nivel_final, 2.2) * SMMLV_2026 * (1 + 0.035) ** (y - anos_estudio)
            tray_estudiar.append(sal_final)

    # --- Trayectoria 2: Trabajar directamente ---
    crec_trabajo = nivel_crec.get(req.nivel_educativo_actual, 0.020)
    tray_trabajar = [salario_actual * (1 + crec_trabajo) ** y for y in anos]

    # --- Trayectoria 3: Emprender ---
    rues = _load_csv("rues_empresas_nuevas.csv")
    rues["_ciiu_norm"] = rues["ciiu2"].astype(str)
    # Buscar dinamismo del sector
    pred = _load_json("predicciones_mundiales.json")
    sector_cagr = pred.get("sectores_cagr_5a", {}).get(req.sector_interes, 0.5)

    # Emprendimiento: alto riesgo, alta recompensa
    rng = np.random.default_rng(42)
    n_sim = 500
    trays_emp = np.zeros((n_sim, 11))
    for s in range(n_sim):
        # 60% fracasan (ingreso bajo), 40% tienen éxito variable
        exito = rng.random() < 0.4
        if exito:
            crec_base = 0.05 + abs(sector_cagr) / 100
            for y in range(11):
                if y == 0:
                    trays_emp[s, y] = req.capital_disponible_cop * 0.1 if req.capital_disponible_cop > 0 else salario_actual * 0.5
                else:
                    shock = rng.normal(0, 0.08)
                    trays_emp[s, y] = trays_emp[s, y - 1] * (1 + crec_base + shock)
        else:
            # Negocio que no despega
            for y in range(11):
                trays_emp[s, y] = salario_actual * (0.5 + rng.uniform(-0.2, 0.2))

    tray_emprender_mediana = np.median(trays_emp, axis=0).tolist()
    tray_emprender_p10 = np.percentile(trays_emp, 10, axis=0).tolist()
    tray_emprender_p90 = np.percentile(trays_emp, 90, axis=0).tolist()

    # Ingreso acumulado a 10 años
    acum_estudiar = sum(tray_estudiar)
    acum_trabajar = sum(tray_trabajar)
    acum_emprender = sum(tray_emprender_mediana)

    # Veredicto
    trayectorias = {
        "estudiar": acum_estudiar,
        "trabajar": acum_trabajar,
        "emprender": acum_emprender,
    }
    mejor = max(trayectorias, key=trayectorias.get)

    veredictos = {
        "estudiar": f"Estudiar genera el mayor ingreso acumulado a 10 años ({acum_estudiar/1_000_000:.0f}M COP). La inversión en educación se recupera tras los primeros años.",
        "trabajar": f"Trabajar directamente genera el mayor ingreso acumulado a 10 años ({acum_trabajar/1_000_000:.0f}M COP). Entrar al mercado pronto compensa el menor salario inicial.",
        "emprender": f"Emprender tiene el mayor potencial acumulado ({acum_emprender/1_000_000:.0f}M COP), pero con alta volatilidad. Solo recomendable si tienes red de apoyo y capital.",
    }

    return {
        "anos": anos,
        "estudiar": {
            "trayectoria": [round(v) for v in tray_estudiar],
            "ingreso_acumulado_10a": round(acum_estudiar),
            "anos_inversion": anos_estudio,
            "descripcion": "Ingresos bajos durante estudios, salto al graduarse",
        },
        "trabajar": {
            "trayectoria": [round(v) for v in tray_trabajar],
            "ingreso_acumulado_10a": round(acum_trabajar),
            "crecimiento_anual_pct": round(crec_trabajo * 100, 1),
            "descripcion": "Ingreso estable desde el inicio, crecimiento gradual",
        },
        "emprender": {
            "mediana": [round(v) for v in tray_emprender_mediana],
            "p10": [round(v) for v in tray_emprender_p10],
            "p90": [round(v) for v in tray_emprender_p90],
            "ingreso_acumulado_10a": round(acum_emprender),
            "prob_exito_pct": 40,
            "descripcion": "Alto riesgo y alta recompensa. Mediana de 500 simulaciones Monte Carlo",
        },
        "mejor_opcion": mejor,
        "veredicto": veredictos[mejor],
        "parametros": {
            "edad": req.edad,
            "nivel_educativo_actual": req.nivel_educativo_actual,
            "departamento": req.departamento,
            "sector_interes": req.sector_interes,
            "capital_disponible_cop": req.capital_disponible_cop,
        },
    }


# ---------------------------------------------------------------------------
# 6. SIMULADOR UNIFICADO "¿Y SI...?" (múltiples escenarios en un gráfico)
# ---------------------------------------------------------------------------

# Cache de DataFrames pesados para no recargar en cada escenario
_OLE_DF: pd.DataFrame | None = None
_SABER_DF: pd.DataFrame | None = None
_GEIH_DEPTO_DF: pd.DataFrame | None = None


def _get_ole() -> pd.DataFrame:
    global _OLE_DF
    if _OLE_DF is None:
        df = _load_csv("ole_ingresos_por_programa.csv")
        df["programa"] = df["programa"].astype(str).str.strip().apply(_clean_text)
        df["_prog_norm"] = df["programa"].apply(_norm)
        _OLE_DF = df
    return _OLE_DF


def _get_saber() -> pd.DataFrame | None:
    global _SABER_DF
    if _SABER_DF is None:
        try:
            _SABER_DF = _load_csv("saberpro_resumen_programas.csv")
            _SABER_DF["_prog_norm"] = _SABER_DF["programa"].apply(_norm)
        except Exception:
            _SABER_DF = pd.DataFrame()
    return _SABER_DF


def _get_geih_depto() -> pd.DataFrame:
    global _GEIH_DEPTO_DF
    if _GEIH_DEPTO_DF is None:
        df = _load_csv("geih_resumen_departamento.csv")
        df["_depto_norm"] = df["departamento"].apply(lambda d: _norm(_fix_depto_name(d)))
        _GEIH_DEPTO_DF = df
    return _GEIH_DEPTO_DF


def _inferir_nivel(programa_norm: str) -> str:
    if "DOCTORADO" in programa_norm:
        return "Doctorado"
    if "MAESTRIA" in programa_norm or "MAESTRIA" in programa_norm:
        return "Maestria"
    if "ESPECIALIZACION" in programa_norm:
        return "Especializacion"
    if "TECNOLOGIA" in programa_norm or "TECNOL" in programa_norm:
        return "Tecnologo"
    if "TECNICO" in programa_norm:
        return "Tecnico"
    return "Universitario"


def _salario_ole(programa_norm: str) -> tuple[float, str]:
    """Devuelve (salario_cop, rango_label) desde OLE para un programa."""
    ole = _get_ole()
    prog_rows = ole[ole["_prog_norm"].str.contains(programa_norm, na=False)]
    if prog_rows.empty:
        return 2.0 * SMMLV_2026, "Estimado (~2 SMMLV)"
    top = prog_rows.sort_values("graduados", ascending=False).iloc[0]
    return _rango_a_cop(top["rango_ingreso"]), top["rango_ingreso"]


def _factor_calidad(programa_norm: str) -> tuple[float, float | None]:
    """Devuelve (factor_calidad, puntaje_raw) desde SaberPro."""
    saber = _get_saber()
    if saber is None or saber.empty:
        return 1.0, None
    sp_rows = saber[saber["_prog_norm"].str.contains(programa_norm, na=False)]
    if sp_rows.empty:
        return 1.0, None
    cols_notas = [c for c in sp_rows.columns if c.startswith("MOD_") and c.endswith("_PUNT")]
    if not cols_notas:
        return 1.0, None
    calidad = float(sp_rows[cols_notas].mean(axis=1).mean())
    return 0.90 + (calidad / 300) * 0.20, calidad


def _ajuste_territorial(depto_norm: str) -> float:
    geih = _get_geih_depto()
    row = geih[geih["_depto_norm"] == depto_norm]
    if row.empty:
        return 1.0
    ing_depto = float(row.iloc[0]["ingreso_promedio"])
    ing_nacional = float(geih["ingreso_promedio"].mean())
    return max(0.80, min(1.20, ing_depto / ing_nacional))


def _tasa_chronos(programa_norm: str) -> tuple[float, str, str]:
    """Devuelve (crecimiento_decimal, profesion_chronos, fuente). Cadena Chronos → SPE → baseline."""
    pred = _load_json("predicciones_mundiales.json")
    crec_base = pred.get("salarios", {}).get("crecimiento_anual_pct", 3.5) / 100
    match = _match_chronos(programa_norm)
    if match is not None:
        prof, rate = match
        return rate, prof, f"Chronos T5 ({prof})"
    spe_map = _build_spe_growth_map()
    for palabra in [w for w in programa_norm.split() if len(w) > 3]:
        if palabra in spe_map:
            return spe_map[palabra], "Baseline", f"SPE/APE ({palabra})"
    return crec_base, "Baseline general", "Chronos T5 (baseline)"


_AJUSTE_NIVEL = {
    "Tecnico": -0.010, "Tecnologo": -0.005, "Universitario": 0.0,
    "Especializacion": 0.005, "Maestria": 0.010, "Doctorado": 0.015,
}

# Salario base por nivel para el escenario "trabajar sin estudiar" (en SMMLV)
_SALARIO_NIVEL_SMMLV = {
    "Bachiller": 1.0, "Tecnico": 1.3, "Tecnologo": 1.6, "Universitario": 2.0,
}

# Bono salarial por nivel de posgrado sobre el salario base universitario
_BONO_POSGRADO = {
    "Especializacion": 1.15, "Maestria": 1.25, "Doctorado": 1.40,
}

# Años de estudio por posgrado
_ANOS_POSGRADO = {"Especializacion": 1, "Maestria": 2, "Doctorado": 4}


def _trayectoria_mc(
    salario_post: float,
    crec_anual: float,
    anos_inversion: int = 0,
    factor_inversion: float = 0.3,
    vol: float = 0.035,
) -> dict:
    """Monte Carlo de 1000 trayectorias a 10 años.
    Durante los años de inversión: salario_post × factor_inversion.
    Después: crecimiento compuesto con shocks."""
    rng = np.random.default_rng(42)
    n_sim = 1000
    anos = list(range(0, 11))
    tr = np.zeros((n_sim, 11))
    for s in range(n_sim):
        for y in range(11):
            if anos_inversion > 0 and y <= anos_inversion:
                tr[s, y] = salario_post * factor_inversion
            elif y == 0 or (anos_inversion > 0 and y == anos_inversion + 1):
                tr[s, y] = salario_post
            else:
                shock = rng.normal(0, vol)
                crec_real = max(-0.02, crec_anual + shock)
                tr[s, y] = tr[s, y - 1] * (1 + crec_real)
    mediana = np.median(tr, axis=0).tolist()
    p10 = np.percentile(tr, 10, axis=0).tolist()
    p90 = np.percentile(tr, 90, axis=0).tolist()
    acum = float(np.median(tr, axis=0).sum())
    return {"anos": anos, "mediana": mediana, "p10": p10, "p90": p90, "acumulado": acum}


def _trayectoria_emprender(
    salario_ref: float, sector_cagr: float, capital: float
) -> dict:
    """Monte Carlo de emprendimiento: 40% éxito, 60% fracaso."""
    rng = np.random.default_rng(42)
    n_sim = 500
    tr = np.zeros((n_sim, 11))
    crec_base = 0.05 + abs(sector_cagr) / 100
    base_ini = capital * 0.1 if capital > 0 else salario_ref * 0.5
    for s in range(n_sim):
        exito = rng.random() < 0.4
        if exito:
            for y in range(11):
                if y == 0:
                    tr[s, y] = base_ini
                else:
                    shock = rng.normal(0, 0.08)
                    tr[s, y] = tr[s, y - 1] * (1 + crec_base + shock)
        else:
            for y in range(11):
                tr[s, y] = salario_ref * (0.5 + rng.uniform(-0.2, 0.2))
    mediana = np.median(tr, axis=0).tolist()
    p10 = np.percentile(tr, 10, axis=0).tolist()
    p90 = np.percentile(tr, 90, axis=0).tolist()
    acum = float(np.median(tr, axis=0).sum())
    return {"anos": list(range(11)), "mediana": mediana, "p10": p10, "p90": p90, "acumulado": acum}


class EscenarioItem(BaseModel):
    tipo: str  # base | migracion | posgrado | reskilling | emprender | trabajar
    departamento_destino: str | None = None
    nivel: str | None = None  # posgrado
    ocupacion_destino: str | None = None  # reskilling
    sector_interes: str | None = None  # emprender
    capital_disponible_cop: float = 0
    nivel_actual: str | None = None  # trabajar


class QuePasaSiRequest(BaseModel):
    programa: str
    departamento: str = "Bogotá D.C."
    edad: int = 22
    escenarios: list[EscenarioItem]


class EscenarioResult(BaseModel):
    tipo: str
    label: str
    color: str
    salario_inicial_cop: float
    crecimiento_anual_pct: float
    anos_inversion: int
    anos: list[int]
    mediana: list[float]
    p10: list[float]
    p90: list[float]
    ingreso_acumulado_10a: float
    delta_vs_base_cop: float
    descripcion: str
    profesion_chronos: str = ""


class QuePasaSiResponse(BaseModel):
    programa: str
    departamento: str
    edad: int
    nivel_detectado: str
    escenarios: list[EscenarioResult]
    mejor_opcion: str
    veredicto: str


_COLORES = {
    "base": "#d4af37",
    "migracion": "#3b82f6",
    "posgrado": "#22c55e",
    "reskilling": "#a855f7",
    "emprender": "#f97316",
    "trabajar": "#94a3b8",
}


@router.post("/que-pasa-si", response_model=QuePasaSiResponse)
async def sim_que_pasa_si(req: QuePasaSiRequest):
    """Simulador unificado: calcula múltiples escenarios de vida y los compara en un solo gráfico."""
    programa_norm = _norm(req.programa)
    depto_norm = _norm(req.departamento)
    nivel = _inferir_nivel(programa_norm)

    # --- Base salary + growth del programa ---
    sal_ole, rango = _salario_ole(programa_norm)
    f_calidad, calidad_raw = _factor_calidad(programa_norm)
    crec_chronos, prof_chronos, fuente = _tasa_chronos(programa_norm)

    pred = _load_json("predicciones_mundiales.json")
    sector_cagr_map = pred.get("sectores_cagr_5a", {})

    # Asegurar que "base" esté siempre primero
    escenarios_req = list(req.escenarios)
    if not any(e.tipo == "base" for e in escenarios_req):
        escenarios_req.insert(0, EscenarioItem(tipo="base"))

    resultados: list[EscenarioResult] = []
    base_acum = 0.0

    for i, esc in enumerate(escenarios_req):
        color = _COLORES.get(esc.tipo, "#d4af37")
        delta_base = 0.0

        if esc.tipo == "base":
            ajuste_t = _ajuste_territorial(depto_norm)
            sal_base = sal_ole * f_calidad * ajuste_t
            crec = crec_chronos + _AJUSTE_NIVEL.get(nivel, 0.0)
            tray = _trayectoria_mc(sal_base, crec)
            label = f"Base: {req.departamento}"
            desc = f"Salario inicial {format(round(sal_base), ',').replace(',', '.')} COP, crece {crec*100:.1f}% anual ({fuente})."
            base_acum = tray["acumulado"]

        elif esc.tipo == "migracion":
            dest = esc.departamento_destino or "Bogotá D.C."
            ajuste_t = _ajuste_territorial(_norm(dest))
            sal_base = sal_ole * f_calidad * ajuste_t
            crec = crec_chronos + _AJUSTE_NIVEL.get(nivel, 0.0)
            tray = _trayectoria_mc(sal_base, crec)
            label = f"Mudanza a {dest}"
            ajuste_origen = _ajuste_territorial(depto_norm)
            delta_pct = (ajuste_t / ajuste_origen - 1) * 100 if ajuste_origen > 0 else 0
            signo = "+" if delta_pct >= 0 else ""
            desc = f"Salario inicial {signo}{delta_pct:.0f}% vs base por costo/ingreso territorial. Total: {format(round(sal_base), ',').replace(',', '.')} COP."

        elif esc.tipo == "posgrado":
            niv = esc.nivel or "Maestria"
            bono = _BONO_POSGRADO.get(niv, 1.25)
            anos_est = _ANOS_POSGRADO.get(niv, 2)
            ajuste_t = _ajuste_territorial(depto_norm)
            sal_post = sal_ole * f_calidad * ajuste_t * bono
            crec = crec_chronos + _AJUSTE_NIVEL.get(niv, 0.01)
            tray = _trayectoria_mc(sal_post, crec, anos_inversion=anos_est, factor_inversion=0.3)
            label = f"Estudiar {niv}"
            desc = f"Inversión de {anos_est} año(s). Tras graduarte: {format(round(sal_post), ',').replace(',', '.')} COP (+{(bono-1)*100:.0f}% vs base), crece {crec*100:.1f}% anual."

        elif esc.tipo == "reskilling":
            ocup = esc.ocupacion_destino or ""
            ocup_norm = _norm(ocup)
            # Match Chronos para la nueva ocupación
            match = _match_chronos(ocup_norm)
            if match:
                prof_n, crec_n = match
                sal_info = _chronos_salario(prof_n)
                sal_post = sal_info if sal_info else sal_ole * 1.05
            else:
                prof_n = "Estimado"
                spe_map = _build_spe_growth_map()
                crec_n = crec_chronos
                for p in [w for w in ocup_norm.split() if len(w) > 3]:
                    if p in spe_map:
                        crec_n = spe_map[p]
                        break
                sal_post = sal_ole * 1.05
            ajuste_t = _ajuste_territorial(depto_norm)
            sal_post *= ajuste_t * f_calidad
            tray = _trayectoria_mc(sal_post, crec_n, anos_inversion=1, factor_inversion=0.5)
            label = f"Reskilling a {ocup}" if ocup else "Reskilling"
            desc = f"1 año de transición. Nueva ocupación: {prof_n}. Salario objetivo: {format(round(sal_post), ',').replace(',', '.')} COP."

        elif esc.tipo == "emprender":
            sector = esc.sector_interes or "Servicios"
            cagr = sector_cagr_map.get(sector, 0.5)
            sal_ref = sal_ole * f_calidad * _ajuste_territorial(depto_norm)
            tray = _trayectoria_emprender(sal_ref, cagr, esc.capital_disponible_cop)
            label = "Emprender"
            desc = f"Monte Carlo (500 sims): 40% prob. de éxito. Sector {sector} (CAGR {cagr:+.1f}%). Alta volatilidad."

        elif esc.tipo == "trabajar":
            niv_act = esc.nivel_actual or "Bachiller"
            sal_base = _SALARIO_NIVEL_SMMLV.get(niv_act, 1.0) * SMMLV_2026
            crec = 0.020 + _AJUSTE_NIVEL.get(niv_act, -0.010) + 0.010
            ajuste_t = _ajuste_territorial(depto_norm)
            sal_base *= ajuste_t
            tray = _trayectoria_mc(sal_base, crec)
            label = f"Trabajar ya ({niv_act})"
            desc = f"Ingreso inmediato sin estudiar el programa. Salario: {format(round(sal_base), ',').replace(',', '.')} COP, crece {crec*100:.1f}% anual."

        else:
            continue

        delta_base = tray["acumulado"] - base_acum
        # Crecimiento efectivo: desde el fin de la inversión (o año 0) hasta año 10
        inv = _ANOS_POSGRADO.get(esc.nivel, 0) if esc.tipo == "posgrado" else (1 if esc.tipo == "reskilling" else 0)
        start_idx = inv + 1 if inv > 0 else 0
        end_val = tray["mediana"][-1]
        start_val = tray["mediana"][start_idx] if start_idx < 10 else end_val
        years_grow = 10 - start_idx
        crec_disp = ((end_val / start_val) ** (1 / years_grow) - 1) * 100 if start_val > 0 and years_grow > 0 else 0
        resultados.append(EscenarioResult(
            tipo=esc.tipo,
            label=label,
            color=color,
            salario_inicial_cop=round(tray["mediana"][0]),
            crecimiento_anual_pct=round(crec_disp, 1),
            anos_inversion=inv,
            anos=tray["anos"],
            mediana=[round(v) for v in tray["mediana"]],
            p10=[round(v) for v in tray["p10"]],
            p90=[round(v) for v in tray["p90"]],
            ingreso_acumulado_10a=round(tray["acumulado"]),
            delta_vs_base_cop=round(delta_base),
            descripcion=desc,
            profesion_chronos=prof_chronos if esc.tipo in ("base", "migracion", "posgrado") else "",
        ))

    # Veredicto: mejor opción por ingreso acumulado
    mejor = max(resultados, key=lambda r: r.ingreso_acumulado_10a)
    base_r = next((r for r in resultados if r.tipo == "base"), resultados[0])
    if mejor.tipo == "base":
        veredicto = f"Seguir tu plan actual es la mejor opción: ingreso acumulado a 10 años de {format(round(base_r.ingreso_acumulado_10a), ',').replace(',', '.')} COP."
    else:
        delta = mejor.ingreso_acumulado_10a - base_r.ingreso_acumulado_10a
        signo = "+" if delta >= 0 else ""
        veredicto = (
            f"Tu mejor opción es {mejor.label.lower()}: ingreso acumulado de "
            f"{format(round(mejor.ingreso_acumulado_10a), ',').replace(',', '.')} COP "
            f"({signo}{format(round(abs(delta)), ',').replace(',', '.')} COP vs base)."
        )

    return QuePasaSiResponse(
        programa=req.programa,
        departamento=req.departamento,
        edad=req.edad,
        nivel_detectado=nivel,
        escenarios=resultados,
        mejor_opcion=mejor.tipo,
        veredicto=veredicto,
    )


def _chronos_salario(profesion_nombre: str) -> float | None:
    """Busca el salario mensual COP de una profesión Chronos por nombre."""
    for p in _load_chronos_professions():
        if _norm(p.get("profesion", "")) == _norm(profesion_nombre):
            return p.get("salario_mensual_cop")
    return None


# ---------------------------------------------------------------------------
# Endpoint de resumen
# ---------------------------------------------------------------------------

@router.get("/resumen")
async def resumen():
    """Metadatos del módulo de simulación."""
    return {
        "modulo": "Simulación",
        "simulaciones": [
            {
                "id": "trayectoria",
                "nombre": "Trayectoria Profesional",
                "descripcion": "Proyecta tu salario a 10 años según programa académico y departamento",
                "endpoint": "/api/simulacion/trayectoria",
                "fuentes": ["OLE/MEN", "Saber Pro", "GEIH", "Chronos T5"],
            },
            {
                "id": "migracion",
                "nombre": "Migración Territorial",
                "descripcion": "Compara condiciones laborales entre departamentos",
                "endpoint": "/api/simulacion/migracion",
                "fuentes": ["GEIH", "DNP/MDM"],
            },
            {
                "id": "reskilling",
                "nombre": "Reskilling / Transición",
                "descripcion": "Calcula la brecha de habilidades entre ocupaciones y recomienda formación SENA",
                "endpoint": "/api/simulacion/reskilling",
                "fuentes": ["ESCO", "SENA", "WEF Future of Jobs"],
            },
            {
                "id": "demanda-sectorial",
                "nombre": "Demanda Sectorial",
                "descripcion": "Simula el impacto de escenarios macroeconómicos en el empleo sectorial",
                "endpoint": "/api/simulacion/demanda-sectorial",
                "fuentes": ["GEIH mensual", "Chronos T5", "RUES"],
            },
            {
                "id": "decision",
                "nombre": "Estudiar vs Trabajar vs Emprender",
                "descripcion": "Compara 3 trayectorias a 10 años según tu perfil",
                "endpoint": "/api/simulacion/decision",
                "fuentes": ["GEIH", "RUES", "Chronos T5", "OLE/MEN"],
            },
        ],
    }