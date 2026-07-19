"""
Módulo Simulación — "El viaje de una decisión"
Endpoint transversal que integra Radiografía territorial (Gobierno),
Programas con hueco regional (Universidad) y Salario proyectado (Estudiante)
en una sola respuesta, demostrando que los mismos datos sirven para 3 públicos.

Datos 100% reales, sin scores inventados. Todo desde Supabase.
"""
import unicodedata
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.supabase import supabase

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

DEPTO_SINONIMOS: dict[str, str] = {
    "ARCHIPIELAGO DE SAN ANDRES": "SAN ANDRES Y PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES, PROVIDENCIA Y SANTA CATALINA": "SAN ANDRES Y PROVIDENCIA",
    "ARCHIPIELAGO DE SAN ANDRES Y PROVIDENCIA": "SAN ANDRES Y PROVIDENCIA",
    "BOGOTA D.C": "BOGOTA D.C.", "BOGOTA, D.C.": "BOGOTA D.C.", "BOGOTA": "BOGOTA D.C.",
    "SAN ANDRES Y PROVIDENCIA": "SAN ANDRES Y PROVIDENCIA",
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
    4: "Suministro de electricidad, gas y agua",
    5: "Construcción",
    6: "Comercio, hoteles y restaurantes (sección F antigua)",
    7: "Transporte, almacenamiento y comunicaciones",
    8: "Información y comunicaciones",
    9: "Actividades financieras e inmobiliarias",
    10: "Servicios comunales, sociales y personales",
    11: "Actividades no bien especificadas",
    # Códigos CIIU Rev. 4 a 2 dígitos (los que realmente aparecen en GEIH)
    10: "Fabricación de productos alimenticios",
    11: "Fabricación de bebidas",
    12: "Fabricación de productos del tabaco",
    13: "Fabricación de textiles",
    14: "Confección de prendas de vestir",
    15: "Curtido y acabado de cueros",
    16: "Transformación de madera y productos de madera",
    17: "Fabricación de papel y cartón",
    18: "Actividades de impresión y reproducción",
    19: "Coquización y refinación de petróleo",
    20: "Fabricación de sustancias químicas",
    21: "Fabricación de productos farmacéuticos",
    22: "Fabricación de productos de caucho y plástico",
    23: "Fabricación de otros minerales no metálicos",
    24: "Industria básica de hierro y acero",
    25: "Fabricación de productos metálicos",
    26: "Fabricación de productos informáticos y electrónicos",
    27: "Fabricación de equipo eléctrico",
    28: "Fabricación de maquinaria y equipo",
    29: "Fabricación de vehículos automotores",
    30: "Fabricación de otros equipos de transporte",
    31: "Fabricación de muebles",
    32: "Otras industrias manufactureras",
    33: "Reparación e instalación de maquinaria",
    35: "Suministro de electricidad, gas y vapor",
    36: "Captación, tratamiento y distribución de agua",
    37: "Gestión de aguas residuales",
    38: "Recolección y tratamiento de desechos",
    39: "Actividades de descontaminación",
    41: "Construcción de edificaciones",
    42: "Construcción de obras de ingeniería civil",
    43: "Actividades especializadas de construcción",
    45: "Comercio de vehículos automotores",
    46: "Comercio al por mayor",
    47: "Comercio al por menor",
    49: "Transporte terrestre",
    50: "Transporte acuático",
    51: "Transporte aéreo",
    52: "Almacenamiento y actividades de transporte complementarias",
    53: "Actividades postales y de mensajería",
    55: "Alojamiento",
    56: "Servicios de comida",
    58: "Actividades de edición",
    59: "Actividades cinematográficas y de sonido",
    60: "Actividades de programación y transmisión",
    61: "Telecomunicaciones",
    62: "Desarrollo de sistemas informáticos (software)",
    63: "Actividades de procesamiento de datos y hosting",
    64: "Actividades de servicios financieros",
    65: "Seguros y reaseguros",
    66: "Actividades auxiliares a los servicios financieros",
    68: "Actividades inmobiliarias",
    69: "Actividades jurídicas y contables",
    70: "Actividades de oficinas principales y consultoría",
    71: "Servicios técnicos y arquitectónicos",
    72: "Investigación científica y desarrollo",
    73: "Publicidad y estudios de mercado",
    74: "Otras actividades profesionales y científicas",
    75: "Actividades veterinarias",
    77: "Actividades de alquiler y arrendamiento",
    78: "Actividades de empleo y agencias de personal",
    79: "Actividades de agencias de viajes y operadores turísticos",
    80: "Actividades de seguridad e investigación",
    81: "Servicios a edificios y paisajismo",
    82: "Actividades administrativas de oficina",
    84: "Administración pública y defensa",
    85: "Educación",
    86: "Actividades de atención humana en salud",
    87: "Actividades de atención en instituciones de cuidado",
    88: "Actividades de asistencia social sin alojamiento",
    90: "Actividades creativas, artísticas y de entretenimiento",
    91: "Actividades de bibliotecas, archivos y museos",
    92: "Actividades de lotería y apuestas",
    93: "Actividades deportivas y recreativas",
    94: "Actividades de asociaciones",
    95: "Reparación de computadores y equipos de comunicación",
    96: "Otras actividades de servicios personales",
    97: "Actividades de los hogares como empleadores",
    99: "Organizaciones y órganos extraterritoriales",
}


def _fix_mojibake(s: str) -> str:
    """Reconstruye texto UTF-8 que fue malinterpretado como Latin-1.
    Maneja 'CaquetÃ¡' (UTF-8 de 'Caquetá' codificado como latin-1) y reverso.
    Idempotente: si el string ya es UTF-8 correcto, lo deja igual."""
    if not s:
        return s
    # Caso 1: mojibake UTF-8 como latin-1 (común cuando axios/envío mezcla encodings)
    # Patrón: secuencias como "Ã¡", "Ã©", "Ã³", "Ã±", "Ã­", "Ãº", "Ã" sola
    mojibake_map = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú", "Ã±": "ñ",
        "Ã¼": "ü", "Â¿": "¿", "Â¡": "¡", "â€™": "'", 'â€œ': '"', 'â€': '"',
        "Ã": "Á", "Ã‰": "É", "Ã": "Í", "Ã" "Â³": "ó",
    }
    out = s
    for bad, good in mojibake_map.items():
        out = out.replace(bad, good)
    # Si quedó una "Ã" suelta (mayúscula A con tilde, U+00C3), reintentar como latin-1→utf-8
    if "Ã" in out:
        try:
            # Out tiene el byte U+00C3 que en latin-1 es 0xC3; combinado con el siguiente char...
            # Estrategia general: si todavía hay Ã, intenta encodear como latin-1 y decodear utf-8
            candidate = out.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if candidate and "Ã" not in candidate and len(candidate) <= len(out) + 5:
                out = candidate
        except Exception:
            pass
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
    return DEPTO_SINONIMOS.get(n, n)


def _rango_a_cop(rango: str) -> float | None:
    if not rango:
        return None
    for k, v in RANGO_INGRESO_MEDIO_SMMLV.items():
        if _norm(k) == _norm(rango):
            return v * SMMLV_2026
    return None


def _depto_to_code(depto_norm: str) -> str | None:
    for code, name in DANE_DEPTO.items():
        if _norm_depto(name) == depto_norm:
            return code
    return None


def _depto_search_keywords(depto_norm: str) -> list[str]:
    """Genera keywords de búsqueda para filtrar SNIES por departamento.
    Cubre sinónimos, mojibake y variantes (BOGOTA D.C. vs BOGOTA)."""
    kws: list[str] = []
    # Variante principal sin "D.C." ni "DEPARTAMENTO"
    base = depto_norm.replace(" D.C.", "").replace(" D.C", "").strip()
    kws.append(base)
    if base != depto_norm:
        kws.append(depto_norm)
    # Palabra distintiva (la más larga, evita "DE", "LA")
    stopwords = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON", "POR", "AL", "A", "O", "D.C.", "D.C"}
    palabras = [w for w in depto_norm.split() if w not in stopwords and len(w) > 2]
    if palabras:
        # palabra más larga como keyword distintivo
        kws.append(max(palabras, key=len))
    # Sinónimos manuales para casos especiales
    if "SAN ANDRES" in depto_norm:
        kws.extend(["ANDRES", "ARCHIPIELAGO"])
    if "BOGOTA" in depto_norm:
        kws.append("BOGOTA")
    # Deduplicar preservando orden
    seen = set()
    return [k for k in kws if not (k in seen or seen.add(k))]


class ViajeResponse(BaseModel):
    departamento: str
    radiografia: dict[str, Any]
    sectores_top: list[dict[str, Any]]
    programas_con_hueco: list[dict[str, Any]]
    metodologia_salario: dict[str, Any]
    fuentes: list[str]


def _fetch_all(table: str, select: str = "*", filt: dict | None = None,
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


def _find_by_norm(rows: list[dict], field: str, target_norm: str) -> dict | None:
    target = _norm_depto(target_norm)
    for r in rows:
        if _norm_depto(str(r.get(field, ""))) == target:
            return r
    return None


@router.get("/viaje", response_model=ViajeResponse)
async def viaje(departamento: str):
    """
    El viaje de una decisión: una sola llamada integra 3 públicos.

    Entrada: nombre de departamento (flexible, normaliza acentos y sinónimos).
    Salida:
      - radiografia: indicadores reales del territorio (Gobierno).
      - sectores_top: 5 sectores CIUU con más empleo en el depto (Gobierno + Universidad).
      - programas_con_hueco: programas con alta demanda nacional y sin oferta local (Universidad),
        con salario proyectado ajustado al territorio (Estudiante).
      - metodologia_salario: transparencia sobre cómo se calcula el salario.
    """
    depto_norm = _norm_depto(departamento)
    if not depto_norm:
        raise HTTPException(status_code=400, detail="Departamento requerido")

    depto_code = _depto_to_code(depto_norm)

    # ─────────────────────────────────────────────────────────────────────
    # 1. RADIOGRAFÍA TERRITORIAL (GEIH + DNP)
    # ─────────────────────────────────────────────────────────────────────
    geih_rows = _fetch_all("geih_resumen_departamento")
    target = _find_by_norm(geih_rows, "departamento", depto_norm)
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"Departamento '{departamento}' no encontrado en GEIH"
        )

    ingreso_depto = float(target.get("ingreso_promedio") or 0)
    ingreso_nacional = sum(float(r.get("ingreso_promedio") or 0) for r in geih_rows) / max(len(geih_rows), 1)
    ajuste_territorial = max(0.80, min(1.20, ingreso_depto / ingreso_nacional)) if ingreso_nacional > 0 else 1.0
    formalidad_pct = round(float(target.get("tasa_formalidad") or 0) * 100, 1)
    ocupados = int(float(target.get("ocupados") or 0))

    # Desempleo: no_ocupados / (ocupados + no_ocupados)
    des_rows = _fetch_all("geih_desempleo_departamento")
    des_row = _find_by_norm(des_rows, "departamento", depto_norm)
    no_ocupados = float(des_row.get("no_ocupados", 0)) if des_row else 0
    denom = ocupados + no_ocupados
    desempleo_pct = round(no_ocupados / denom * 100, 1) if denom > 0 else 0.0

    # Informalidad: promedio últimos 12 meses del depto
    informalidad_pct = None
    if depto_code:
        try:
            code_int = int(depto_code)
            inf_rows = _fetch_all(
                "geih_informalidad_mensual",
                filt={"dpto": code_int},
                order="periodo.desc",
                limit=12,
            )
            if inf_rows:
                vals = [float(r.get("tasa_informalidad") or 0) for r in inf_rows]
                informalidad_pct = round(sum(vals) / len(vals), 1)
        except Exception:
            pass

    # DNP desempeño departamental
    dnp_val = None
    try:
        dnp_rows = _fetch_all("dnp_desempeno_departamento")
        dnp_row = _find_by_norm(dnp_rows, "departamento", depto_norm)
        if dnp_row:
            dnp_val = round(float(dnp_row.get("promedio_desempeno") or 0), 1)
    except Exception:
        pass

    # Acción recomendada: regla declarada sobre el indicador dominante
    if informalidad_pct is not None and informalidad_pct >= 75:
        accion = "Formalización y simplificación de trámites empresariales"
    elif desempleo_pct >= 15:
        accion = "Formación laboral + intermediación SENA/APE"
    elif dnp_val is not None and dnp_val < 50:
        accion = "Fortalecimiento institucional y capacidad municipal"
    else:
        accion = "Empleo juvenil y emprendimiento (ver módulo Emprende IA)"

    radiografia = {
        "desempleo_pct": desempleo_pct,
        "informalidad_pct": informalidad_pct,
        "formalidad_pct": formalidad_pct,
        "ingreso_promedio_cop": round(ingreso_depto),
        "ingreso_nacional_cop": round(ingreso_nacional),
        "ajuste_territorial": round(ajuste_territorial, 3),
        "ocupados": ocupados,
        "dnp_desempeno": dnp_val,
        "accion_recomendada": accion,
    }

    # ─────────────────────────────────────────────────────────────────────
    # 2. SECTORES TOP DEL DEPARTAMENTO (GEIH empleo_depto_sector)
    # ─────────────────────────────────────────────────────────────────────
    sectores_top: list[dict[str, Any]] = []
    if depto_code:
        try:
            code_int = int(depto_code)
            last_p_rows = _fetch_all(
                "geih_empleo_depto_sector",
                select="periodo",
                filt={"dpto": code_int},
                order="periodo.desc",
                limit=1,
            )
            if last_p_rows:
                ultimo_periodo = last_p_rows[0]["periodo"]
                sec_rows = _fetch_all(
                    "geih_empleo_depto_sector",
                    filt={"dpto": code_int, "periodo": ultimo_periodo},
                )
                # Agrupar por rama_ciiu tomando el máximo empleo (deduplica cargas repetidas idénticas)
                empleo_por_rama: dict[int, float] = {}
                for r in sec_rows:
                    rama = int(r.get("rama_ciiu") or 0)
                    emp = float(r.get("empleo") or 0)
                    if emp > empleo_por_rama.get(rama, 0):
                        empleo_por_rama[rama] = emp
                total_empleo = sum(empleo_por_rama.values()) or 1
                sec_sorted = sorted(empleo_por_rama.items(), key=lambda x: x[1], reverse=True)
                for rama, empleo in sec_sorted[:5]:
                    sectores_top.append({
                        "rama_ciiu": rama,
                        "nombre": CIIU2_NOMBRES.get(rama, f"Rama {rama}"),
                        "empleo": round(empleo),
                        "participacion_pct": round(empleo / total_empleo * 100, 1),
                    })
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────
    # 3. PROGRAMAS CON HUECO REGIONAL (SNIES oferta vs OLE demanda nacional)
    # ─────────────────────────────────────────────────────────────────────
    # SNIES: programas locales del depto (deduplicar por programa normalizado)
    # Filtro por keyword del depto para no traer las 600k filas; cubre sinónimos y mojibake.
    snies_dedup: dict[tuple[str, str], float] = {}
    try:
        keywords = _depto_search_keywords(depto_norm)
        for kw in keywords:
            rows = supabase.table("snies_programas_matriculados") \
                .select("programa,matriculados,departamento,institucion") \
                .ilike("departamento", f"%{kw}%") \
                .limit(5000).execute().data or []
            for r in rows:
                dep = _norm_depto(str(r.get("departamento") or ""))
                if dep != depto_norm:
                    continue
                pnorm = _norm(str(r.get("programa") or ""))
                if not pnorm:
                    continue
                inst = _norm(str(r.get("institucion") or ""))
                key = (pnorm, inst)
                mat = float(r.get("matriculados") or 0)
                if mat > snies_dedup.get(key, 0):
                    snies_dedup[key] = mat
    except Exception:
        pass

    # Agregar por programa normalizado (consolidar instituciones)
    programas_locales: dict[str, dict] = {}
    for (pnorm, _inst), mat in snies_dedup.items():
        entry = programas_locales.setdefault(pnorm, {"nombre": pnorm, "matriculados": 0, "count": 0})
        entry["matriculados"] += mat
        entry["count"] += 1

    # OLE: agrupar por programa normalizado (deduplica cargas múltiples)
    ole_rows = _fetch_all("ole_ingresos_por_programa", limit=5000)
    por_programa: dict[str, dict] = {}
    for r in ole_rows:
        pnorm = _norm(str(r.get("programa") or ""))
        if not pnorm:
            continue
        entry = por_programa.setdefault(pnorm, {"nombre": r.get("programa"), "rangos": []})
        entry["rangos"].append((r.get("rango_ingreso"), float(r.get("graduados") or 0)))

    programas_nacional: list[dict[str, Any]] = []
    for pnorm, info in por_programa.items():
        if not info["rangos"]:
            continue
        total_grad = sum(g for _, g in info["rangos"])
        rango_modal, _ = max(info["rangos"], key=lambda x: x[1])
        programas_nacional.append({
            "norm": pnorm,
            "nombre": info["nombre"],
            "egresados_anuales": int(total_grad),
            "rango_modal": rango_modal,
        })

    programas_nacional.sort(key=lambda x: x["egresados_anuales"], reverse=True)
    candidatos = programas_nacional[:40]

    # Palabras clave principal de cada programa local (para matching flexible)
    _stopwords_prog = {"DE", "DEL", "LA", "LAS", "LOS", "EL", "EN", "Y", "E", "PARA", "CON", "POR", "AL", "A", "O", "EN"}
    locales_keywords: list[str] = []
    for pnorm in programas_locales:
        for w in pnorm.split():
            if w not in _stopwords_prog and len(w) >= 4:
                locales_keywords.append(w)

    def _tiene_oferta_local(cand_norm: str) -> tuple[int, float]:
        """Devuelve (n_programas_locales, matriculados_locales) usando matching flexible."""
        # 1. Match exacto
        loc = programas_locales.get(cand_norm)
        if loc:
            return (loc["count"], loc["matriculados"])
        # 2. Match por palabra clave principal (>= 5 chars) del candidato
        cand_words = [w for w in cand_norm.split() if w not in _stopwords_prog and len(w) >= 5]
        if not cand_words:
            return (0, 0)
        cand_kw = max(cand_words, key=len)
        count = 0
        matr = 0.0
        for pnorm, info in programas_locales.items():
            if cand_kw in pnorm.split():
                count += info["count"]
                matr += info["matriculados"]
        return (count, matr)

    programas_con_hueco: list[dict[str, Any]] = []
    for p in candidatos:
        prog_locales_count, matriculados_locales = _tiene_oferta_local(p["norm"])

        # "Hueco": sin oferta local Y con egresados nacionales considerables
        if prog_locales_count == 0 and p["egresados_anuales"] >= 200:
            salario_rango = _rango_a_cop(p["rango_modal"]) or SMMLV_2026 * 2.0
            salario_ajustado = salario_rango * ajuste_territorial
            programas_con_hueco.append({
                "programa": p["nombre"],
                "programas_locales": prog_locales_count,
                "matriculados_locales": int(matriculados_locales),
                "egresados_anuales_nacional": p["egresados_anuales"],
                "rango_modal": p["rango_modal"],
                "salario_mediano_cop": round(salario_rango),
                "salario_ajustado_cop": round(salario_ajustado),
                "veredicto": "Hueco detectado",
            })

    # Top 8 por salario ajustado (más atractivo para demo)
    programas_con_hueco.sort(key=lambda x: x["salario_ajustado_cop"], reverse=True)
    programas_con_hueco = programas_con_hueco[:8]

    metodologia_salario = {
        "formula": "salario_OLE × (ingreso_promedio_depto / ingreso_promedio_nacional)",
        "ingreso_depto_cop": round(ingreso_depto),
        "ingreso_nacional_cop": round(ingreso_nacional),
        "ajuste_territorial": round(ajuste_territorial, 3),
        "nota": "El rango OLE más frecuente se convierte a COP usando el SMMLV 2026 ($1.750.000). El ajuste territorial usa el ratio real del ingreso promedio del depto vs el promedio nacional (cap 0.80-1.20). Sin Monte Carlo, sin proyección inventada.",
    }

    return ViajeResponse(
        departamento=target.get("departamento", departamento),
        radiografia=radiografia,
        sectores_top=sectores_top,
        programas_con_hueco=programas_con_hueco,
        metodologia_salario=metodologia_salario,
        fuentes=["GEIH-DANE", "OLE-MEN", "SNIES-MEN", "DNP/MDM"],
    )


@router.get("/viaje/departamentos")
async def listar_departamentos():
    """Lista los 33 departamentos disponibles para el viaje."""
    rows = _fetch_all("geih_resumen_departamento", select="departamento")
    return {"departamentos": sorted({r["departamento"] for r in rows if r.get("departamento")})}
