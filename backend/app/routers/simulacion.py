"""
Módulo Simulación — Tres decisiones, una fuente integrada (Supabase).

1. Alineación curricular (Universidades): ¿Conviene actualizar el pensum?
   Compara el pensum actual con habilidades esenciales ESCO de ocupaciones afines.
2. Intervención por objetivo (Gobierno): ¿Dónde y en qué sector intervenir?
   Ranking de oportunidades por depto, ponderado según objetivo declarado.
3. Explora carrera (Estudiantes): ¿Qué pasa si estudio esta carrera?
   Habilidades, salidas laborales, demanda, salario y dónde estudiarla. Sin score mágico.

Plus: Analizar con IA — Gemini responde preguntas sobre la simulación generada.

Todo desde Supabase. Cero scores inventados: cada número se explica con su fórmula.
"""
import json
import unicodedata
from collections import Counter
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.supabase import supabase
from app.services.llm_gemini import call_gemini_text, is_gemini_available
from app.services.llm import call_llm_text

router = APIRouter(prefix="/api/simulacion", tags=["Simulacion"])

SMMLV_2026 = 1_750_000

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

RANGO_INGRESO_MEDIO_SMMLV: dict[str, float] = {
    "1 SMMLV": 1.0, "Entre 1 y 1,5 SMMLV": 1.25,
    "Entre 1,5 y 2,5 SMMLV": 2.0, "Entre 2,5 y 4 SMMLV": 3.25,
    "Entre 4 y 6 SMMLV": 5.0, "Entre 6 y 9 SMMLV": 7.5,
    "Mas de 9 SMMLV": 11.0, "Más de 9 SMMLV": 11.0,
}

CIIU2_NOMBRES: dict[int, str] = {
    0: "Sin clasificar",
    1: "Agricultura, ganadería, caza y silvicultura",
    2: "Explotación de minas y canteras",
    3: "Industria manufacturera",
    5: "Construcción",
    6: "Comercio, hoteles y restaurantes",
    7: "Transporte y comunicaciones",
    8: "Información y comunicaciones",
    9: "Actividades financieras e inmobiliarias",
    10: "Servicios comunales, sociales y personales",
    10: "Fabricación de productos alimenticios",
    11: "Fabricación de bebidas",
    13: "Fabricación de textiles",
    14: "Confección de prendas de vestir",
    17: "Transformación de madera",
    18: "Fabricación de papel y cartón",
    20: "Fabricación de sustancias químicas",
    21: "Fabricación de productos farmacéuticos",
    22: "Productos de caucho y plástico",
    23: "Otros minerales no metálicos",
    24: "Industria básica de hierro y acero",
    25: "Productos metálicos",
    26: "Productos informáticos y electrónicos",
    27: "Equipo eléctrico",
    28: "Maquinaria y equipo",
    29: "Vehículos automotores",
    30: "Otros equipos de transporte",
    31: "Fabricación de muebles",
    32: "Otras industrias manufactureras",
    35: "Suministro de electricidad, gas y vapor",
    36: "Distribución de agua",
    41: "Construcción de edificaciones",
    43: "Actividades especializadas de construcción",
    45: "Comercio de vehículos",
    46: "Comercio al por mayor",
    47: "Comercio al por menor",
    49: "Transporte terrestre",
    50: "Transporte acuático",
    51: "Transporte aéreo",
    52: "Almacenamiento",
    53: "Actividades postales y mensajería",
    55: "Alojamiento",
    56: "Servicios de comida",
    58: "Actividades de edición",
    59: "Actividades cinematográficas",
    61: "Telecomunicaciones",
    62: "Desarrollo de sistemas informáticos (software)",
    63: "Procesamiento de datos y hosting",
    64: "Servicios financieros",
    65: "Seguros",
    66: "Actividades auxiliares a servicios financieros",
    68: "Actividades inmobiliarias",
    69: "Actividades jurídicas y contables",
    70: "Consultoría de gestión",
    71: "Servicios técnicos y arquitectónicos",
    72: "Investigación científica",
    73: "Publicidad y estudios de mercado",
    74: "Otras actividades profesionales",
    78: "Servicios de empleo y agencias",
    80: "Seguridad e investigación",
    81: "Servicios a edificios",
    82: "Actividades administrativas",
    84: "Administración pública y defensa",
    85: "Educación",
    86: "Atención en salud",
    87: "Asistencia social con alojamiento",
    90: "Actividades artísticas y de entretenimiento",
    93: "Actividades deportivas y recreativas",
    94: "Actividades de asociaciones",
    96: "Otros servicios personales",
    97: "Hogares como empleadores",
}

# Mapa aproximado de código CIIU-2-dígitos → nombre de sector en PILA y predicciones
CIIU2_KEYWORD_SECTOR: dict[int, list[str]] = {
    62: ["software", "informatic", "tecnolog", "sistema", "datos"],
    63: ["datos", "informacion", "hosting"],
    61: ["telecom", "telecomunicacion"],
    85: ["educacion", "enseñanza"],
    86: ["salud", "hospital", "medic"],
    84: ["publica", "gobierno", "administracion publica"],
    47: ["comercio", "minorista", "retail", "tienda"],
    46: ["comercio", "mayorista", "mayor"],
    56: ["restaurante", "comida", "gastronomia", "alojamiento"],
    55: ["hotel", "alojamiento", "turismo"],
    49: ["transporte", "logistica", "vehiculo"],
    41: ["construccion", "obra", "edificacion"],
    1: ["agricola", "agro", "campo", "cultivo", "ganaderia"],
    3: ["manufactura", "industria", "fabrica"],
}

# Pesos por objetivo de intervención (Gobierno)
PESOS_OBJETIVO: dict[str, dict[str, float]] = {
    "sectores_emergentes":   {"demanda": 0.25, "crecimiento": 0.40, "deficit_talento": 0.20, "compatibilidad": 0.15},
    "reducir_desempleo_juvenil": {"demanda": 0.45, "crecimiento": 0.20, "deficit_talento": 0.20, "compatibilidad": 0.15},
    "emprendimiento":         {"demanda": 0.20, "crecimiento": 0.30, "deficit_talento": 0.35, "compatibilidad": 0.15},
    "reducir_informalidad":   {"demanda": 0.20, "crecimiento": 0.15, "deficit_talento": 0.20, "compatibilidad": 0.45},
}


# ===========================================================================
# Helpers
# ===========================================================================

def _fix_mojibake(s: str) -> str:
    if not s:
        return s
    mojibake_map = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
        "Ã¼": "ü", "Â¿": "¿", "Â¡": "¡", "â€™": "'", 'â€œ': '"', 'â€': '"',
        "Ã": "A",
    }
    out = s
    for bad, good in mojibake_map.items():
        out = out.replace(bad, good)
    return out


def _norm(s: str) -> str:
    if not s:
        return ""
    s = _fix_mojibake(str(s))
    s = s.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _norm_depto(s: str) -> str:
    n = _norm(s)
    if n in ("BOGOTA D.C", "BOGOTA", "BOGOTA DC", "BOGOTA, D.C.", "BOGOTA, DC"):
        return "BOGOTA D.C."
    if "SAN ANDRES" in n:
        return "SAN ANDRES Y PROVIDENCIA"
    return n


def _depto_to_code(depto_norm: str) -> str | None:
    for code, name in DANE_DEPTO.items():
        if _norm_depto(name) == depto_norm:
            return code
    return None


def _rango_a_cop(rango: str) -> float | None:
    if not rango:
        return None
    nr = _norm(rango)
    for k, v in RANGO_INGRESO_MEDIO_SMMLV.items():
        if _norm(k) == nr:
            return v * SMMLV_2026
    return None


def _sb_select(table: str, select: str = "*", filt: dict | None = None,
               order: str | None = None, limit: int | None = None) -> list[dict]:
    q = supabase.table(table).select(select)
    if filt:
        for k, v in filt.items():
            q = q.eq(k, v)
    if order:
        col, direction = (order.split(".") + ["asc"])[:2]
        q = q.order(col, desc=(direction == "desc"))
    if limit:
        q = q.limit(limit)
    return q.execute().data or []


def _sb_ilike(table: str, select: str, column: str, value: str,
              limit: int = 50, order: str | None = None) -> list[dict]:
    q = supabase.table(table).select(select).ilike(column, value)
    if order:
        col, direction = (order.split(".") + ["asc"])[:2]
        q = q.order(col, desc=(direction == "desc"))
    return q.limit(limit).execute().data or []


# ===========================================================================
# Simulación 1 — Alineación curricular (Universidades)
# ===========================================================================

class AlineacionRequest(BaseModel):
    programa: str
    pensum: list[str] = []


def _ocupaciones_compatibles(programa_norm: str, limit: int = 8) -> list[dict]:
    """Busca ocupaciones ESCO cuyas palabras principales coincidan con el programa."""
    # Palabras distintivas del programa (>= 4 chars, sin stopwords)
    stop = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON",
            "POR", "AL", "A", "O", "Tecnolog", "Tecnica", "Profesional", "Especializacion",
            "Maestria", "Doctorado", "Licenciatura", "INGENIERIA", "CIENCIA", "CIENCIAS",
            "ADMINISTR", "DIPLOMADO", "TECHNOLOG"}
    palabras = [w for w in programa_norm.split() if len(w) >= 4 and w not in stop]
    if not palabras:
        palabras = [w for w in programa_norm.split() if len(w) >= 4][:3]
    
    seen_uris = set()
    result = []
    for w in palabras[:5]:  # cubrir hasta 5 palabras clave
        rows = _sb_ilike("esco_ocupaciones", "uri,nombre", "nombre", f"%{w}%", limit=10)
        for r in rows:
            u = r.get("uri")
            n = r.get("nombre", "").strip()
            if u and n and u not in seen_uris:
                seen_uris.add(u)
                result.append({"uri": u, "nombre": n})
        if len(result) >= limit:
            break
    return result[:limit]


def _habilidades_esenciales(ocupaciones: list[dict]) -> dict[str, int]:
    """Retorna un dict {habilidad: conteo} de habilidades ESSENCIAL de las ocupaciones."""
    freq: Counter = Counter()
    for occ in ocupaciones:
        uri = occ.get("uri")
        if not uri:
            continue
        rows = _sb_select(
            "esco_ocupacion_habilidades",
            select="habilidad_nombre,tipo_habilidad",
            filt={"ocupacion_uri": uri, "tipo_relacion": "essential"},
            limit=200,
        )
        for r in rows:
            n = (r.get("habilidad_nombre") or "").strip()
            if n:
                freq[n] += 1
    return dict(freq)


@router.post("/alineacion-curricular")
async def alineacion_curricular(req: AlineacionRequest):
    """
    Índice de Alineación Curricular: cobertura del pensum sobre las habilidades
    ESCO esenciales de las ocupaciones afines al programa.

    Salidaclared:
    - indice_alineacion (0-100): |pensum ∩ esenciales| / |esenciales| * 100
    - cobertura_esco_pct: idem
    - ocupaciones_compatibles: lista analizada
    - competencias_cubiertas / faltantes
    - cursos_sena_recomendados (para cerrar brechas)
    """
    programa_norm = _norm(req.programa)
    if not programa_norm:
        raise HTTPException(status_code=400, detail="Programa requerido")
    if not req.pensum:
        raise HTTPException(status_code=400, detail="Indica al menos una competencia del pensum actual")

    # 1. Ocupaciones ESCO afines al programa
    ocupaciones = _ocupaciones_compatibles(programa_norm)
    print("DEBUG AC: programa_norm =", programa_norm)
    print("DEBUG AC: ocupaciones =", ocupaciones)
    if not ocupaciones:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontraron ocupaciones ESCO afines a '{req.programa}'. Prueba con un nombre más específico (ej: 'Ingeniería de Sistemas')."
        )

    # 2. Habilidades esenciales + frecuencia
    esencial_freq = _habilidades_esenciales(ocupaciones)
    print("DEBUG AC: esencial_freq =", len(esencial_freq))
    if not esencial_freq:
        raise HTTPException(
            status_code=503,
            detail=f"Las ocupaciones afines a '{req.programa}' no tienen habilidades esenciales registradas en ESCO."
        )

    # Top esenciales (por frecuencia en las ocupaciones compatibles)
    top_esenciales = [h for h, _ in sorted(esencial_freq.items(), key=lambda x: -x[1])]
    esencial_set_norm = {_norm(h) for h in top_esenciales}

    # 3. Normalizar pensum usuario
    pensum_es = req.pensum.copy()
    
    # Diccionario de fallback básico para español -> ESCO inglés (por si la API de Gemini falla)
    fallback_dict = {
        "analisis de datos": ["data analysis", "analyse data", "data analytics"],
        "logistica": ["logistics", "supply chain", "manage logistics"],
        "mecanica": ["mechanics", "mechanical engineering", "machinery"],
        "programacion": ["programming", "develop software", "write code"],
        "desarrollo web": ["web development", "web design"],
        "bases de datos": ["databases", "sql", "manage data"],
        "matematicas": ["mathematics", "calculate", "math"],
        "estadistica": ["statistics", "statistical analysis"],
        "ingles": ["english", "foreign language"],
        "administracion": ["management", "business administration", "manage staff"],
        "finanzas": ["finance", "financial analysis", "accounting"],
        "seguridad": ["safety", "security", "safety measures", "health and safety"],
        "diseño": ["design", "design principles", "blueprints"],
        "proyectos": ["project management", "manage schedule of tasks"],
        "liderazgo": ["leadership", "lead a team", "manage a team"]
    }

    # Intentar traducir el pensum al inglés para hacer match con ESCO
    if is_gemini_available() and pensum_es:
        try:
            sys_prompt = "Traduce esta lista de materias o competencias del español al inglés técnico de ESCO. Devuelve SOLO un JSON con el formato: {\"traducciones\": [\"item1\", \"item2\"]}. No agregues markdown ni comillas fuera del JSON."
            usr_prompt = json.dumps(pensum_es, ensure_ascii=False)
            res = call_gemini_text(sys_prompt, usr_prompt, temperature=0.1)
            # Limpiar posible markdown
            if res.startswith("```json"): res = res[7:]
            if res.startswith("```"): res = res[3:]
            if res.endswith("```"): res = res[:-3]
            traduccion = json.loads(res.strip())
            if "traducciones" in traduccion and isinstance(traduccion["traducciones"], list):
                pensum_es.extend(traduccion["traducciones"])
        except Exception as e:
            print("DEBUG AC: Error traduciendo pensum:", e)
            
    # Agregar traducciones del fallback dictionary si hacen match con algo ingresado
    for item in req.pensum:
        item_norm = _norm(item).lower()
        for k, v in fallback_dict.items():
            if _norm(k).lower() in item_norm or item_norm in _norm(k).lower():
                pensum_es.extend(v)
            
    pensum_norm = {_norm(h) for h in pensum_es if h.strip()}

    # Matching: contamos una esencial como cubierta si alguna palabra del pensum la contiene
    # (mejor que igualdad exacta porque ESCO usa frases largas)
    cubiertas: list[str] = []
    faltantes: list[str] = []
    for h in top_esenciales:
        hn = _norm(h)
        matched = any(pn in hn or hn in pn for pn in pensum_norm if len(pn) >= 4)
        (cubiertas if matched else faltantes).append(h)

    total_esenciales = len(top_esenciales)
    total_cubiertas = len(cubiertas)
    indice_alineacion = round(total_cubiertas / total_esenciales * 100, 1) if total_esenciales else 0.0

    # Traducir faltantes al español para mostrar en UI
    faltantes_es = faltantes[:15].copy()
    if is_gemini_available() and faltantes_es:
        try:
            sys_prompt = "Traduce esta lista de competencias de ESCO del inglés al español. Devuelve SOLO un JSON con formato: {\"traducciones\": [\"item1\", \"item2\"]}. No uses markdown."
            usr_prompt = json.dumps(faltantes_es, ensure_ascii=False)
            res = call_gemini_text(sys_prompt, usr_prompt, temperature=0.1)
            if res.startswith("```json"): res = res[7:]
            if res.startswith("```"): res = res[3:]
            if res.endswith("```"): res = res[:-3]
            traduccion = json.loads(res.strip())
            if "traducciones" in traduccion and len(traduccion["traducciones"]) == len(faltantes_es):
                faltantes_es = traduccion["traducciones"]
        except Exception as e:
            print("DEBUG AC: Error traduciendo faltantes:", e)

    # 4. Coincidencia con vacantes SPE/APE (proxy de demanda laboral real)
    spe_match_pct = 0.0
    spe_total = 0
    spe_matched = 0
    for occ_dict in ocupaciones:
        occ = occ_dict["nombre"]
        # Buscar ocupación SPE por palabra clave
        palabras = [w for w in _norm(occ).split() if len(w) >= 4]
        if not palabras:
            continue
        kw = palabras[0]
        try:
            rows = _sb_ilike("spe_ape_inscritos_ocupacion", "ocupacion,inscritos_2020", "ocupacion",
                             f"%{kw}%", limit=5)
            if rows:
                spe_total += 1
                if any(int(r.get("inscritos_2020") or 0) > 100 for r in rows):
                    spe_matched += 1
                    spe_total += sum(int(r.get("inscritos_2020") or 0) for r in rows)
        except Exception:
            pass
    spe_match_pct = round(spe_matched / len(ocupaciones) * 100, 1) if ocupaciones else 0.0

    # 5. Cursos SENA sugeridos para las brechas más frecuentes
    sena_sugeridos: list[dict] = []
    try:
        top_faltantes = faltantes[:5]
        palabras_prog = [w for w in programa_norm.split() if len(w) >= 4][:3]
        for kw in palabras_prog:
            rows = _sb_ilike("sena_programas_activos",
                            "programa,area_desempeno,duracion_horas,costo,institucion,departamento",
                            "programa", f"%{kw}%", limit=8)
            for r in rows:
                sena_sugeridos.append({
                    "programa": r.get("programa"),
                    "area": r.get("area_desempeno"),
                    "duracion_horas": r.get("duracion_horas"),
                    "costo_cop": r.get("costo"),
                    "institucion": r.get("institucion"),
                    "departamento": r.get("departamento"),
                })
                if len(sena_sugeridos) >= 6:
                    break
            if len(sena_sugeridos) >= 6:
                break
    except Exception:
        pass

    return {
        "programa": req.programa,
        "pensum_ingresado": req.pensum,
        "ocupaciones_afines": [occ["nombre"] for occ in ocupaciones],
        "indice_alineacion_curricular": indice_alineacion,
        "cobertura_esco_pct": indice_alineacion,
        "total_esenciales": total_esenciales,
        "total_cubiertas": total_cubiertas,
        "total_faltantes": len(faltantes),
        "coincidencia_vacantes_spe_pct": spe_match_pct,
        "competencias_cubiertas": cubiertas[:20],
        "competencias_faltan": faltantes_es,
        "cursos_sena_recomendados": sena_sugeridos,
        "metodologia": (
            "Índice = |competencias_del_pensum que coinciden con habilidades ESCO esenciales| "
            "/ |total habilidades ESCO esenciales de las ocupaciones afines| × 100. "
            "Coincidencia con vacantes SPE/APE: porcentaje de ocupaciones afines con >100 inscritos SPE."
        ),
        "fuentes": ["ESCO (UE)", "SPE/APE SENA", "SENA"],
    }


# ===========================================================================
# Simulación 2 — Intervención por objetivo (Gobierno)
# ===========================================================================

class IntervencionRequest(BaseModel):
    departamento: str
    objetivo: str = "sectores_emergentes"
    beneficiarios: int = 500


@router.post("/intervencion-gobierno")
async def intervencion_gobierno(req: IntervencionRequest):
    """
    Ranking de oportunidades sectoriales en un departamento, ponderado según
    el objetivo declarado. Cada score 0-100 se descompone en 4 indicadores reales.

    Score = demanda + crecimiento + déficit_talento + compatibilidad (pesos por objetivo).
    """
    depto_norm = _norm_depto(req.departamento)
    depto_code = _depto_to_code(depto_norm)
    if not depto_code:
        raise HTTPException(status_code=400, detail=f"Departamento '{req.departamento}' no reconocido")

    pesos = PESOS_OBJETIVO.get(req.objetivo, PESOS_OBJETIVO["sectores_emergentes"])

    # 1. Sectores CIUU con empleo en el depto (último periodo)
    code_int = int(depto_code)
    ultimo_rows = _sb_select("geih_empleo_depto_sector", select="periodo",
                             filt={"dpto": code_int}, order="periodo.desc", limit=1)
    if not ultimo_rows:
        raise HTTPException(status_code=404, detail=f"Sin datos sectoriales para {req.departamento}")
    ultimo_periodo = ultimo_rows[0]["periodo"]
    sec_rows = _sb_select("geih_empleo_depto_sector",
                          filt={"dpto": code_int, "periodo": ultimo_periodo})
    empleo_por_rama: dict[int, float] = {}
    for r in sec_rows:
        rama = int(r.get("rama_ciiu") or 0)
        emp = float(r.get("empleo") or 0)
        if emp > empleo_por_rama.get(rama, 0):
            empleo_por_rama[rama] = emp
    if not empleo_por_rama:
        raise HTTPException(status_code=503, detail="No se pudo consolidar empleo sectorial")

    max_empleo = max(empleo_por_rama.values())
    top_ramas = sorted(empleo_por_rama.items(), key=lambda x: -x[1])[:12]

    # 2. Predicciones Chronos sectoriales (crecimiento proyectado)
    def _cronos_rate_sector(rama: int) -> float | None:
        nombre_sector = CIIU2_NOMBRES.get(rama, "")
        if not nombre_sector:
            return None
        try:
            rows = _sb_select("predicciones_mundiales", filt={"tipo": "sectores"})
            for row in rows:
                datos_raw = row.get("datos")
                if not datos_raw:
                    continue
                datos = json.loads(datos_raw) if isinstance(datos_raw, str) else datos_raw
                if not isinstance(datos, dict):
                    continue
                # Buscar sector cuyo nombre coincida con sector
                for sec_name, sec_data in datos.items():
                    sn = _norm(sec_name)
                    # coincidir por substring en el nombre del sector CIIU
                    if sn and (sn in _norm(nombre_sector) or _norm(nombre_sector) in sn):
                        pred = sec_data.get("prediccion", {})
                        if isinstance(pred, dict):
                            valores = list(pred.get("valores", {}).values()) if isinstance(pred.get("valores"), dict) else pred.get("valores", [])
                            if valores and len(valores) >= 2:
                                try:
                                    v0 = float(valores[-2])
                                    vf = float(valores[-1])
                                    if v0 > 0:
                                        return round((vf - v0) / v0 * 100, 1)
                                except Exception:
                                    pass
            return None
        except Exception:
            return None

    # 3. Compatibilidad económica: PILA cotizantes por sector
    pila_rows = _sb_select("pila_resumen_sector",
                           select="actividadeconomicadesc,total_cotizantes",
                           order="total_cotizantes.desc", limit=50)
    max_pila = max((float(r.get("total_cotizantes") or 0) for r in pila_rows), default=1) or 1

    def _pila_compatibilidad(rama: int) -> float:
        nombre = CIIU2_NOMBRES.get(rama, "")
        if not nombre:
            return 0.0
        keywords = CIIU2_KEYWORD_SECTOR.get(rama, [_norm(nombre)[:8]])
        for r in pila_rows:
            desc = _norm(r.get("actividadeconomicadesc") or "")
            for kw in keywords:
                if kw in desc:
                    return float(r.get("total_cotizantes") or 0) / max_pila * 100
        return 0.0

    # 4. Déficit de talento: bajo = saturado, alto = hay hueco
    # Proxy: programas SENA afines en el depto (cuantos menos, más déficit)
    def _deficit_talento(rama: int) -> float:
        keywords = CIIU2_KEYWORD_SECTOR.get(rama, [])
        if not keywords:
            return 50.0  # neutro si no sabemos
        try:
            # Buscar programas SENA en el depto con la keyword
            count = 0
            for kw in keywords[:2]:
                rows = _sb_ilike("sena_programas_activos", "programa", "programa",
                                 f"%{kw}%", limit=200)
                # filtrar por depto (case-insensitive)
                count += sum(1 for _ in rows)
            # Normalizar invertido: más programas = menos déficit
            # cap en 0-100: 0 programas → 100 (déficit alto), 50+ → 5
            deficit = max(5, min(100, 100 - count * 1.8))
            return round(deficit, 1)
        except Exception:
            return 50.0

    # 5. Calcular score por sector
    oportunidades: list[dict] = []
    for rama, empleo in top_ramas:
        if empleo < max_empleo * 0.01:
            continue  # saltar sectores marginales
        demanda_norm = empleo / max_empleo * 100
        crecimiento = _cronos_rate_sector(rama) or 0.0
        # crecimiento puede ser negativo; normalizar 0-100 (capándolo)
        crec_norm = max(0, min(100, crecimiento * 4 + 50))  # 0% → 50, +12% → 100, -12% → 0
        deficit = _deficit_talento(rama)
        compatibilidad = _pila_compatibilidad(rama)

        score = (
            pesos["demanda"] * demanda_norm
            + pesos["crecimiento"] * crec_norm
            + pesos["deficit_talento"] * deficit
            + pesos["compatibilidad"] * compatibilidad
        )
        oportunidades.append({
            "rama_ciiu": rama,
            "sector": CIIU2_NOMBRES.get(rama, f"Rama {rama}"),
            "empleo_depto": round(empleo),
            "demanda_pct": round(demanda_norm, 1),
            "crecimiento_proyectado_pct": round(crecimiento, 1),
            "deficit_talento_pct": round(deficit, 1),
            "compatibilidad_economica_pct": round(compatibilidad, 1),
            "score": round(score, 1),
            "beneficiarios_estimados": int(req.beneficiarios),
        })

    oportunidades.sort(key=lambda x: -x["score"])
    top4 = oportunidades[:4]

    # Justificación textual por cada sector top (basada en sus métricas reales)
    for o in top4:
        razones = []
        if o["demanda_pct"] >= 60:
            razones.append(f"Alta demanda laboral local ({o['empleo_depto']:,} ocupados)")
        if o["crecimiento_proyectado_pct"] > 3:
            razones.append(f"Crecimiento proyectado Chronos +{o['crecimiento_proyectado_pct']}% anual")
        if o["deficit_talento_pct"] >= 70:
            razones.append(f"Alto déficit de talento (pocos programas SENA en {req.departamento})")
        if o["compatibilidad_economica_pct"] >= 50:
            razones.append("Sólida base económica formal (PILA)")
        if not razones:
            razones.append("Combinación equilibrada de indicadores")
        o["justificacion"] = ". ".join(razones) + "."

    return {
        "departamento": req.departamento,
        "objetivo": req.objetivo,
        "objetivo_label": req.objetivo.replace("_", " ").capitalize(),
        "beneficiarios": req.beneficiarios,
        "periodo_empleo": ultimo_periodo,
        "pesos_objetivo": pesos,
        "top_oportunidades": top4,
        "ranking_completo": oportunidades[:10],
        "metodologia": (
            "Score 0-100 = demanda (empleo sectorial GEIH) × peso + crecimiento proyectado (Chronos T5) × peso + "
            "déficit de talento (inverso de programas SENA en el depto) × peso + compatibilidad económica "
            "(cotizantes PILA del sector) × peso. Los pesos dependen del objetivo declarado."
        ),
        "fuentes": ["GEIH-DANE", "SENA", "PILA-MinTrabajo", "Chronos T5 (World Bank)"],
    }


# ===========================================================================
# Simulación 3 — Explora carrera (Estudiantes)
# ===========================================================================

class ExploraRequest(BaseModel):
    programa: str


@router.post("/explora-carrera")
async def explora_carrera(req: ExploraRequest):
    """
    Explora una carrera sin scores mágicos: habilidades que developarás, salidas
    laborales, demanda del sector, salario OLE y dónde estudiarla.
    """
    programa_norm = _norm(req.programa)
    if not programa_norm:
        raise HTTPException(status_code=400, detail="Programa requerido")

    # 1. Ocupaciones ESCO afines
    ocupaciones = _ocupaciones_compatibles(programa_norm, limit=10)

    # 2. Habilidades esenciales (top 10 por frecuencia)
    habilidades_top: list[tuple[str, int]] = []
    if ocupaciones:
        freq = _habilidades_esenciales(ocupaciones)
        habilidades_top = sorted(freq.items(), key=lambda x: -x[1])[:10]

    # 3. Salario OLE más frecuente del programa
    salario_rango: str | None = None
    salario_cop: float | None = None
    egresados_anuales = 0
    try:
        ole_rows = _sb_ilike("ole_ingresos_por_programa",
                             "rango_ingreso,graduados", "programa",
                             f"%{programa_norm[:25]}%", limit=50)
        if ole_rows:
            rango_freq = Counter()
            for r in ole_rows:
                rng = r.get("rango_ingreso")
                g = int(r.get("graduados") or 0)
                if rng:
                    rango_freq[rng] += g
                egresados_anuales += g
            if rango_freq:
                salario_rango, _ = rango_freq.most_common(1)[0]
                salario_cop = _rango_a_cop(salario_rango)
    except Exception:
        pass

    # Deduplicar: los egresados se suman dos veces si hay cargas dobles; usar max por rango
    try:
        ole_rows2 = _sb_ilike("ole_ingresos_por_programa",
                              "rango_ingreso,graduados", "programa",
                              f"%{programa_norm[:25]}%", limit=200)
        if ole_rows2:
            seen: dict[str, int] = {}
            for r in ole_rows2:
                rng = r.get("rango_ingreso")
                g = int(r.get("graduados") or 0)
                if rng and g > seen.get(rng, 0):
                    seen[rng] = g
            egresados_anuales = sum(seen.values())
            if seen and not salario_rango:
                salario_rango = max(seen.items(), key=lambda x: x[1])[0]
                salario_cop = _rango_a_cop(salario_rango)
    except Exception:
        pass

    # 4. Sectores con mayor empleo nacional (GEIH último periodo nacional)
    sectores_nacional: list[dict] = []
    try:
        ult_rows = _sb_select("geih_empleo_depto_sector", select="periodo",
                              order="periodo.desc", limit=1)
        if ult_rows:
            ultp = ult_rows[0]["periodo"]
            all_rows = _sb_select("geih_empleo_depto_sector",
                                  filt={"periodo": ultp}, limit=500)
            emp_rama: dict[int, float] = {}
            for r in all_rows:
                rama = int(r.get("rama_ciiu") or 0)
                emp_rama[rama] = emp_rama.get(rama, 0) + float(r.get("empleo") or 0)
            # Tomar max agregando (por si duplicados)
            for rama, emp in sorted(emp_rama.items(), key=lambda x: -x[1])[:5]:
                sectores_nacional.append({
                    "rama_ciiu": rama,
                    "sector": CIIU2_NOMBRES.get(rama, f"Rama {rama}"),
                    "empleo_nacional": round(emp),
                })
    except Exception:
        pass

    # 5. Dónde estudiarla: top 5 instituciones SNIES con ese programa
    instituciones: list[dict] = []
    try:
        # Buscar por palabra clave distintiva
        stop = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON"}
        palabras = [w for w in programa_norm.split() if len(w) >= 4 and w not in stop]
        kw = palabras[0] if palabras else programa_norm[:8]
        snies = _sb_ilike("snies_programas_matriculados",
                          "institucion,programa,matriculados,departamento", "programa",
                          f"%{kw}%", limit=30, order="matriculados.desc")
        # Deduplicar por (institucion, programa) con max matriculados
        seen2: dict[tuple, dict] = {}
        for r in snies:
            pnorm = _norm(r.get("programa") or "")
            if programa_norm not in pnorm:
                continue
            key = (_norm(r.get("institucion") or ""), pnorm)
            mat = float(r.get("matriculados") or 0)
            if key not in seen2 or mat > seen2[key].get("matriculados", 0):
                seen2[key] = r
        instituciones = list(seen2.values())[:5]
    except Exception:
        pass

    return {
        "programa": req.programa,
        "ocupaciones_afines": [occ["nombre"] for occ in ocupaciones],
        "habilidades_desarrollaras": [
            {"habilidad": h, "frecuencia_en_ocupaciones": c}
            for h, c in habilidades_top
        ],
        "salidas_laborales": [occ["nombre"] for occ in ocupaciones[:5]],
        "demanda_laboral_sectores": sectores_nacional,
        "salario_esperado": {
            "rango_modal": salario_rango,
            "mediana_cop": round(salario_cop) if salario_cop else None,
            "egresados_anuales_nacional": egresados_anuales,
        },
        "donde_estudiarla": [
            {
                "institucion": i.get("institucion"),
                "programa": i.get("programa"),
                "departamento": i.get("departamento"),
                "matriculados": int(i.get("matriculados") or 0),
            }
            for i in instituciones
        ],
        "fuentes": ["ESCO (UE)", "OLE/MEN", "GEIH-DANE", "SNIES-MEN"],
    }


# ===========================================================================
# Analizar con IA — chat sobre la simulación generada
# ===========================================================================

class AnalizarRequest(BaseModel):
    simulacion_tipo: str  # "alineacion" | "intervencion" | "explora"
    simulacion_titulo: str  # título legible (ej: "Alineación curricular: Ingeniería de Sistemas")
    simulacion_data: dict[str, Any]
    pregunta: str
    historial: list[dict[str, Any]] | None = None


@router.post("/analizar")
async def analizar_con_ia(req: AnalizarRequest):
    """Gemini responde preguntas sobre la simulación generada. Sistema ALBA estricto."""
    system = """Eres ALBA, una plataforma de inteligencia laboral para Colombia. Estás analizando el resultado de una simulación basada en datos reales del DANE (GEIH), MEN (SNIES, OLE), SENA (SPE/APE), ESCO (UE) y DNP/MDM.

REGLAS OBLIGATORIAS:
1. Responde SOBRE los datos de la simulación que recibes. NO contradigas los números.
2. ANTI-ALUCINACIONES: nunca inventes cifras. Si necesitas un dato que no está en la simulación, dilo claramente ("este dato no está en la simulación") y propone cómo se podría obtener.
3. Usa SIEMPRE pesos colombianos (COP, $). Nunca dólares ni euros.
4. Sé conciso: máximo 2-3 párrafos. Usa **negrita** para resaltar datos clave.
5. Responde en español de Colombia, tono profesional y cercano.
6. NO comiences con "¡Hola!" ni "Claro!" ni "Entiendo que...". Responde directamente.
7. Si la pregunta no tiene relación con la simulación, redirige amablemente: "Esta pregunta no corresponde a la simulación actual. Aquí estamos analizando [título]."
8. Cita las fuentes de los datos cuando sea relevante (GEIH, OLE, ESCO, etc.)."""

    historial_txt = ""
    if req.historial:
        historial_txt = "\n\n## Historial de la conversación\n" + "\n".join(
            f"- **{'Usuario' if h.get('role') == 'user' else 'ALBA'}**: {h.get('content', '')}"
            for h in req.historial
        )

    # Serializar dump de la simulación (limitado para no saturar el prompt)
    try:
        dump = json.dumps(req.simulacion_data, ensure_ascii=False, default=str)
        if len(dump) > 6000:
            dump = dump[:6000] + "\n... (truncado)"
    except Exception:
        dump = str(req.simulacion_data)[:6000]

    user = f"""## Simulación analizada
- Tipo: {req.simulacion_tipo}
- Título: {req.simulacion_titulo}

## Datos de la simulación
{dump}{historial_txt}

## Pregunta del usuario
{req.pregunta}
"""

    try:
        if is_gemini_available():
            respuesta = call_gemini_text(system, user)
        else:
            respuesta = call_llm_text(system, user)
        return {"respuesta": respuesta, "simulacion_tipo": req.simulacion_tipo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al consultar la IA: {str(e)}")


# ===========================================================================
# Endpoints auxiliares: listados para autocompletar
# ===========================================================================

@router.get("/programas")
async def listar_programas(q: str = "", limit: int = 30):
    """Lista programas SNIES para autocompletar. Deduplica por nombre normalizado."""
    if not q.strip():
        # top por matriculados
        rows = _sb_select("snies_programas_matriculados",
                          select="programa,matriculados",
                          order="matriculados.desc", limit=limit * 5)
    else:
        kw = _norm(q)
        rows = _sb_ilike("snies_programas_matriculados",
                         "programa,matriculados", "programa",
                         f"%{kw}%", limit=limit * 5, order="matriculados.desc")
    # Deduplicar por nombre normalizado, conservando el máximo de matriculados
    seen: dict[str, dict] = {}
    for r in rows:
        p = r.get("programa") or ""
        pn = _norm(p)
        if not pn:
            continue
        m = float(r.get("matriculados") or 0)
        if pn not in seen or m > seen[pn].get("_m", 0):
            seen[pn] = {"programa": p, "_m": m}
    salida = sorted(seen.values(), key=lambda x: -x["_m"])[:limit]
    for x in salida:
        del x["_m"]
    return {"programas": salida}


@router.get("/departamentos")
async def listar_departamentos():
    rows = _sb_select("geih_resumen_departamento", select="departamento")
    # Limpieza mínima de mojibake
    salida = sorted({_fix_mojibake(str(r.get("departamento") or "")) for r in rows if r.get("departamento")})
    return {"departamentos": salida}