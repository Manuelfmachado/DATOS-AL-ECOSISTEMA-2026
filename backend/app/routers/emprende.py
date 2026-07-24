"""
Router de Emprende IA (Función #4).
Calcula el Índice de Oportunidad para negocios en municipios/departamentos
colombianos usando RUES, PILA y GEIH. También evalúa ideas de negocio con LLM.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase import supabase
from app.services.llm import evaluar_idea_negocio as deepinfra_evaluar_idea
from app.services.llm_gemini import evaluar_idea_negocio as gemini_evaluar_idea, is_gemini_available
from app.data.ciiu_nombres import CIIU_NOMBRES, obtener_nombre_ciiu
import pandas as pd

router = APIRouter(prefix="/api/emprende", tags=["emprende"])


class OportunidadRequest(BaseModel):
    municipio: str | None = None
    departamento: str = "BOGOTÁ"
    sector: str | None = None  # CIIU2 o palabra clave


class EvaluarIdeaRequest(BaseModel):
    idea: str
    departamento: str = "Bogotá"
    inversion: str = "no especificada"


def _normalizar(texto: str) -> str:
    return texto.strip().upper()


# Mapeo CIIU2 a sectores para presentación (se puede reemplazar por tabla real)
CIIU2_DESCRIPCIONES = {
    "01": "Agricultura, ganadería, caza, silvicultura",
    "02": "Explotación forestal",
    "03": "Pesca y acuicultura",
    "05": "Extracción de carbón de piedra y lignito",
    "06": "Extracción de petróleo crudo y gas natural",
    "07": "Extracción de minerales metalíferos",
    "08": "Otras actividades de explotación de minas y canteras",
    "09": "Actividades de apoyo a la explotación de minas y canteras",
    "10": "Elaboración de productos alimenticios",
    "11": "Elaboración de bebidas",
    "12": "Elaboración de productos de tabaco",
    "13": "Fabricación de productos textiles",
    "14": "Fabricación de prendas de vestir",
    "15": "Fabricación de artículos de cuero y calzado",
    "16": "Transformación de la madera y fabricación de productos de corcho",
    "17": "Fabricación de papel y productos de papel",
    "18": "Actividades de impresión y reproducción de grabaciones",
    "19": "Coquización, fabricación de productos de la refinación del petróleo",
    "20": "Fabricación de sustancias y productos químicos",
    "21": "Fabricación de productos farmacéuticos",
    "22": "Fabricación de productos de caucho y plástico",
    "23": "Fabricación de otros productos minerales no metálicos",
    "24": "Metalurgia",
    "25": "Fabricación de productos metálicos",
    "26": "Fabricación de productos informáticos, electrónicos y ópticos",
    "27": "Fabricación de material y equipo eléctrico",
    "28": "Fabricación de maquinaria y equipo n.c.p.",
    "29": "Fabricación de vehículos automotores, remolques y semirremolques",
    "30": "Fabricación de otros tipos de transporte",
    "31": "Fabricación de muebles, colchones y somieres",
    "32": "Otras industrias manufactureras",
    "33": "Reparación, instalación y mantenimiento de maquinaria y equipo",
    "35": "Suministro de electricidad, gas, vapor y aire acondicionado",
    "36": "Captación, tratamiento y distribución de agua",
    "37": "Evacuación y tratamiento de aguas residuales",
    "38": "Recolección, tratamiento y disposición de residuos",
    "39": "Actividades de saneamiento",
    "41": "Construcción de edificios",
    "42": "Obras de ingeniería civil",
    "43": "Actividades especializadas de construcción",
    "45": "Comercio y reparación de vehículos automotores",
    "46": "Comercio al por mayor",
    "47": "Comercio al por menor",
    "49": "Transporte terrestre",
    "50": "Transporte por agua",
    "51": "Transporte aéreo",
    "52": "Almacenamiento y actividades complementarias al transporte",
    "53": "Actividades de correo y mensajería",
    "55": "Alojamiento",
    "56": "Actividades de servicios de comidas y bebidas",
    "58": "Actividades de edición",
    "59": "Actividades de producción cinematográfica, video y TV",
    "60": "Actividades de programación y transmisión",
    "61": "Telecomunicaciones",
    "62": "Programación informática y actividades conexas",
    "63": "Actividades de servicios de información",
    "64": "Actividades de servicios financieros",
    "65": "Seguros y fondos de pensiones",
    "66": "Actividades auxiliares de los servicios financieros",
    "68": "Actividades inmobiliarias",
    "69": "Actividades jurídicas y de contabilidad",
    "70": "Actividades de oficinas centrales y consultoría de gestión",
    "71": "Actividades de arquitectura e ingeniería",
    "72": "Investigación científica y desarrollo",
    "73": "Publicidad y estudios de mercado",
    "74": "Otras actividades profesionales, científicas y técnicas",
    "75": "Actividades veterinarias",
    "77": "Actividades de alquiler",
    "78": "Actividades de empleo",
    "79": "Agencias de viajes y operadores turísticos",
    "80": "Actividades de seguridad e investigación",
    "81": "Servicios a edificios y actividades de jardinería",
    "82": "Actividades administrativas y de apoyo",
    "84": "Administración pública y defensa",
    "85": "Educación",
    "86": "Actividades de atención de la salud humana",
    "87": "Actividades de atención en residencias",
    "88": "Actividades de apoyo social sin alojamiento",
    "90": "Actividades creativas, artísticas y de entretenimiento",
    "91": "Actividades de bibliotecas, archivos, museos",
    "92": "Actividades de juegos de azar y apuestas",
    "93": "Actividades deportivas, de esparcimiento y recreativas",
    "94": "Actividades de asociaciones",
    "95": "Reparación de computadores y artículos personales",
    "96": "Otras actividades de servicios personales",
    "97": "Actividades de los hogares como empleadores",
    "99": "Actividades de organizaciones y órganos extraterritoriales",
    "00": "No especificado / Otros",
}


# Mapeo GRUPOS12 (EMICRON) -> CIIU2 (para filtrar RUES/PILA por sector real)
_GRUPOS12_TO_CIIU2 = {
    1: ["01", "02", "03"],          # Agricultura
    3: ["10", "11", "13", "14", "15", "16", "17", "18", "20", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32"],  # Industria
    5: ["41", "42", "43"],          # Construcción
    6: ["45", "46"],                # Comercio al por mayor
    7: ["47"],                      # Comercio al por menor
    8: ["49", "50", "51", "52", "53"],  # Transporte
    9: ["55", "56"],                # Alojamiento y comida
    11: ["64", "65", "66"],         # Financiero
    12: ["62", "63", "69", "70", "71", "72", "73", "74"],  # Servicios profesionales/tech
}


def _rues_por_sector_depto(depto: str, ciiu2_codes: list[str]) -> dict:
    """Empresas activas y nuevas de RUES para un departamento + sector CIIU2.

    Usa rues_resumen_camara_ciiu (agrupado por cámara y CIIU2) para sumar
    empresas activas del sector en el departamento. Como respaldo, también
    suma empresas nuevas del sector en todo el país (RUES no desagrega nuevas
    por departamento en nuestra tabla actual).
    """
    out = {"empresas_activas_sector_depto": 0, "empresas_nuevas_sector_nacional": 0, "anio_nuevas": None}
    if not ciiu2_codes:
        return out
    try:
        r = supabase.table("rues_resumen_camara_ciiu").select("*").execute()
        df = pd.DataFrame(r.data or [])
        if not df.empty and "ciiu2" in df.columns:
            df["ciiu2"] = df["ciiu2"].astype(str).str.zfill(2)
            df["departamento_norm"] = df.get("departamento", "").astype(str).str.upper().str.strip().apply(lambda x: x.replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N"))
            depto_norm = depto.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N")
            mask = df["ciiu2"].isin(ciiu2_codes) & (df["departamento_norm"] == depto_norm)
            out["empresas_activas_sector_depto"] = int(df.loc[mask, "empresas_activas"].sum()) if not df.loc[mask].empty else 0
    except Exception as e:
        print(f"[Emprende] RUES activas por sector/depto error: {e}")

    try:
        r_n = supabase.table("rues_empresas_nuevas").select("*").execute()
        df_n = pd.DataFrame(r_n.data or [])
        if not df_n.empty and "ciiu2" in df_n.columns:
            df_n["ciiu2"] = df_n["ciiu2"].astype(str).str.zfill(2)
            df_n = df_n[df_n["ciiu2"].isin(ciiu2_codes) & df_n["anio_matricula"].between(2000, 2026)]
            if not df_n.empty:
                ultimo = int(df_n["anio_matricula"].max())
                out["empresas_nuevas_sector_nacional"] = int(df_n[df_n["anio_matricula"] == ultimo]["empresas_nuevas"].sum())
                out["anio_nuevas"] = ultimo
    except Exception as e:
        print(f"[Emprende] RUES nuevas sector error: {e}")
    return out


def _contexto_mercado(departamento: str, sector: str | None = None) -> dict:
    """Obtiene indicadores de mercado para enriquecer la evaluación con LLM.

    El parámetro `sector` puede ser:
    - Un código CIIU2 directo (ej: "47", "56")
    - El texto de la idea (se detecta el sector via _detectar_grupos12)
    Si no se puede determinar el sector, devuelve totales del departamento.
    """
    depto = _normalizar(departamento)

    ocu = supabase.table("geih_resumen_departamento").select("*").eq("departamento", depto).execute()
    des = supabase.table("geih_desempleo_departamento").select("*").eq("departamento", depto).execute()
    ocupados = ocu.data[0].get("ocupados", 0) if ocu.data else 0
    no_ocupados = des.data[0].get("no_ocupados", 0) if des.data else 0
    total_pea = ocupados + no_ocupados
    tasa_desempleo = (no_ocupados / total_pea * 100) if total_pea > 0 else 0

    # Determinar códigos CIIU2 del sector
    ciiu2_codes: list[str] | None = None
    if sector:
        # Intentar como grupos12 (int)
        try:
            g12 = int(sector)
            if g12 in _GRUPOS12_TO_CIIU2:
                ciiu2_codes = _GRUPOS12_TO_CIIU2[g12]
        except (ValueError, TypeError):
            pass
        # Si no es grupos12, intentar como CIIU2 directo
        if not ciiu2_codes:
            ciiu2_codes = [sector]
        # Si tampoco, detectar desde texto de la idea
        if not ciiu2_codes:
            g12 = _detectar_grupos12(sector)
            if g12 and g12 in _GRUPOS12_TO_CIIU2:
                ciiu2_codes = _GRUPOS12_TO_CIIU2[g12]

    # Datos RUES: activas del sector en el departamento + activas/nuevas nacionales
    rues_local = _rues_por_sector_depto(depto, ciiu2_codes or [])
    empresas_activas_depto = rues_local["empresas_activas_sector_depto"]
    empresas_nuevas_nacional = rues_local["empresas_nuevas_sector_nacional"]
    anio_nuevas_nacional = rues_local["anio_nuevas"]

    rues = supabase.table("rues_resumen_camara_ciiu").select("*").execute()
    df_rues = pd.DataFrame(rues.data or [])
    if ciiu2_codes and not df_rues.empty:
        # ciiu2 en RUES es float (47.0); convertir códigos a float para comparar
        ciiu2_floats = [float(c) for c in ciiu2_codes]
        df_sector = df_rues[df_rues["ciiu2"].isin(ciiu2_floats)]
    elif sector and not df_rues.empty:
        # Fallback: búsqueda por texto (menos precisa)
        sector_q = str(sector).upper()
        mask = df_rues.apply(
            lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
            axis=1,
        )
        df_sector = df_rues[mask]
    else:
        df_sector = df_rues
    empresas_activas_nacional = int(df_sector["empresas_activas"].sum()) if not df_sector.empty else 0
    # rues_resumen_camara_ciiu no tiene empresas_nuevas; usar rues_empresas_nuevas
    empresas_nuevas = 0
    if ciiu2_codes:
        for code in ciiu2_codes:
            r_new = supabase.table("rues_empresas_nuevas").select("empresas_nuevas").eq("ciiu2", float(code)).execute()
            empresas_nuevas += sum(int(r.get("empresas_nuevas", 0) or 0) for r in (r_new.data or []))

    # Demanda laboral real del sector: empleo GEIH del último periodo (reemplaza PILA)
    empleo_sector = 0
    try:
        r_per = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
        periodo = r_per.data[0]["periodo"] if r_per.data else None
        if periodo and ciiu2_codes:
            r_emp = supabase.table("geih_empleo_sector_mensual").select("rama_ciiu, empleo").eq("periodo", periodo).execute()
            seen = set()
            for row in r_emp.data or []:
                rama = str(row.get("rama_ciiu") or "")
                if rama[:2].zfill(2) in ciiu2_codes and rama not in seen:
                    seen.add(rama)
                    empleo_sector += int(row.get("empleo") or 0)
    except Exception:
        pass

    # Contexto EMICRON: micronegocios del mismo sector a nivel nacional
    emicron_contexto = {}
    try:
        g12 = int(sector) if sector and sector.isdigit() else None
        if not g12:
            g12 = _detectar_grupos12(sector or "")
        if g12:
            r_ano = supabase.table("emicron_resumen_nacional_v2").select("ano").order("ano", desc=True).limit(1).execute()
            ano = r_ano.data[0]["ano"] if r_ano.data else 2024
            r_emic = supabase.table("emicron_por_sector_v2").select("*").eq("grupos12", g12).eq("ano", ano).execute()
            if r_emic.data:
                e = r_emic.data[0]
                emicron_contexto = {
                    "ano": ano,
                    "micronegocios": int(e.get("micronegocios") or 0),
                    "ingreso_promedio_mensual": int(e.get("ingreso_promedio") or 0),
                    "pct_usa_internet": e.get("pct_usa_internet"),
                    "pct_tiene_credito": e.get("pct_tiene_credito"),
                }
    except Exception:
        pass

    emergentes = supabase.table("rues_top_sectores_nacional").select("*").limit(5).execute()

    # Contexto sectorial adicional (turismo o agro) si aplica a la idea/sector
    contexto_sectorial = {}
    cat_rnt = _detectar_categoria_rnt(sector or "")
    if cat_rnt:
        try:
            rnt = supabase.table("rnt_resumen_departamento_categoria").select("*") \
                .eq("departamento", depto).execute()
            rnt_df = pd.DataFrame(rnt.data or [])
            if not rnt_df.empty:
                contexto_sectorial["turismo"] = {
                    "categoria_detectada": cat_rnt,
                    "establecimientos_turisticos_depto": int(rnt_df["establecimientos"].sum()),
                    "camas_depto": int(rnt_df["camas"].sum()) if "camas" in rnt_df else 0,
                    "empleados_turismo_depto": int(rnt_df["empleados"].sum()) if "empleados" in rnt_df else 0,
                }
        except Exception:
            pass

    # Si la idea menciona cultivos/agro, traer FINAGRO del departamento
    idea_lower = (sector or "").lower()
    keywords_agro = ["cultivar", "finca", "agro", "agricola", "ganader", "siembra",
                     "cacao", "cafe", "arroz", "palma", "bovino", "porcino", "avicola"]
    if any(kw in idea_lower for kw in keywords_agro):
        try:
            fin = supabase.table("finagro_resumen_departamento").select("*") \
                .eq("departamento_inversion", depto).execute()
            if fin.data:
                f = fin.data[0]
                contexto_sectorial["agro"] = {
                    "total_colocacion_cop": int(f.get("total_colocacion") or 0),
                    "num_operaciones": int(f.get("num_operaciones") or 0),
                    "cultivos_distintos": int(f.get("cultivos_distintos") or 0),
                }
        except Exception:
            pass

    return {
        "departamento": departamento,
        "tasa_desempleo": round(tasa_desempleo, 2),
        "ocupados": ocupados,
        "no_ocupados": no_ocupados,
        "empresas_activas_sector": empresas_activas_depto,
        "empresas_activas_sector_nacional": empresas_activas_nacional,
        "empresas_nuevas_sector": empresas_nuevas,
        "empresas_nuevas_sector_nacional": empresas_nuevas_nacional,
        "anio_ultimas_nuevas": anio_nuevas_nacional,
        "empleo_sector_geih": empleo_sector,
        "contexto_emicron": emicron_contexto,
        "sectores_emergentes_nacional": [
            {"ciiu2": s.get("ciiu2"), "empresas_activas": s.get("empresas_activas")}
            for s in (emergentes.data or [])
        ],
        "contexto_sectorial": contexto_sectorial,
    }


@router.post("/evaluar-idea")
async def evaluar_idea(req: EvaluarIdeaRequest):
    """Evalúa una idea de negocio con LLM + datos reales de mercado."""
    try:
        # Detectar el sector de la idea usando el mapeo de palabras clave (grupos12)
        # para filtrar RUES/PILA por CIIU2 correcto, no por texto aleatorio de la idea.
        grupos12 = _detectar_grupos12(req.idea)
        sector = str(grupos12) if grupos12 else None

        contexto = _contexto_mercado(req.departamento, sector)
        emicron = contexto.get("contexto_emicron") or {}
        contexto_texto = (
            f"Tasa de desempleo en {contexto['departamento']}: {contexto['tasa_desempleo']}%\n"
            f"Ocupados: {contexto['ocupados']:,}, no ocupados: {contexto['no_ocupados']:,}\n"
            f"Empresas activas en sector relacionado: {contexto['empresas_activas_sector']:,}\n"
            f"Empresas nuevas recientes: {contexto['empresas_nuevas_sector']:,}\n"
            f"Empleo real del sector (GEIH): {contexto.get('empleo_sector_geih', 0):,}\n"
            f"Micronegocios del sector en Colombia (EMICRON {emicron.get('ano', '')}): {emicron.get('micronegocios', 'n/a'):,}\n"
            f"Ingreso promedio mensual de micronegocios del sector: ${emicron.get('ingreso_promedio_mensual', 0):,}\n"
            f"Sectores emergentes a nivel nacional: {', '.join(str(s.get('ciiu2')) for s in contexto['sectores_emergentes_nacional'])}"
        )

        if is_gemini_available():
            llm_result = gemini_evaluar_idea(req.idea, req.departamento, req.inversion, contexto_texto)
        else:
            llm_result = deepinfra_evaluar_idea(req.idea, req.departamento, req.inversion, contexto_texto)

        return {
            "idea": req.idea,
            "departamento": req.departamento,
            "inversion": req.inversion,
            "score_potencial": llm_result.get("score_potencial", 0),
            "veredicto": llm_result.get("veredicto", ""),
            "razones_a_favor": llm_result.get("razones_a_favor", []),
            "riesgos": llm_result.get("riesgos", []),
            "pasos": llm_result.get("pasos", []),
            "fuentes_recursos": llm_result.get("fuentes_recursos", []),
            "oportunidad_nicho": llm_result.get("oportunidad_nicho", ""),
            "contexto_mercado": contexto,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/oportunidad")
async def calcular_oportunidad(req: OportunidadRequest):
    """Calcula el Índice de Oportunidad 0-100 para un municipio/departamento y sector."""
    try:
        depto = _normalizar(req.departamento)

        # 1. Datos de desempleo del departamento (GEIH)
        ocu = supabase.table("geih_resumen_departamento").select("*").eq("departamento", depto).execute()
        des = supabase.table("geih_desempleo_departamento").select("*").eq("departamento", depto).execute()
        ocupados = ocu.data[0].get("ocupados", 0) if ocu.data else 0
        no_ocupados = des.data[0].get("no_ocupados", 0) if des.data else 0
        total_pea = ocupados + no_ocupados
        tasa_desempleo = (no_ocupados / total_pea * 100) if total_pea > 0 else 0

        # 2. Empresas del sector en el departamento (RUES por cámara)
        rues = supabase.table("rues_resumen_camara_ciiu").select("*").execute()
        df_rues = pd.DataFrame(rues.data or [])

        # Filtrar por sector CIIU2 si se especifica
        # req.sector puede ser un código CIIU2 directo (ej: "47") o un grupos12 (ej: "9")
        ciiu2_codes = None
        if req.sector:
            # Intentar como grupos12 primero
            try:
                g12 = int(req.sector)
                ciiu2_codes = _GRUPOS12_TO_CIIU2.get(g12)
            except (ValueError, TypeError):
                pass
            # Si no es grupos12, asumir que es CIIU2 directo
            if not ciiu2_codes:
                ciiu2_codes = [req.sector]
        if ciiu2_codes and not df_rues.empty:
            ciiu2_floats = [float(c) for c in ciiu2_codes]
            df_sector = df_rues[df_rues["ciiu2"].isin(ciiu2_floats)]
        elif req.sector and not df_rues.empty:
            # Fallback: buscar por CIIU2 directo o texto
            sector_q = req.sector.upper()
            mask = df_rues.apply(
                lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
                axis=1,
            )
            df_sector = df_rues[mask]
        else:
            df_sector = df_rues

        empresas_activas = int(df_sector["empresas_activas"].sum()) if not df_sector.empty else 0
        # rues_resumen_camara_ciiu no tiene empresas_nuevas; usar rues_empresas_nuevas
        empresas_nuevas = 0
        if ciiu2_codes:
            for code in ciiu2_codes:
                try:
                    r_new = supabase.table("rues_empresas_nuevas").select("empresas_nuevas").eq("ciiu2", float(code)).execute()
                    empresas_nuevas += sum(int(r.get("empresas_nuevas", 0) or 0) for r in (r_new.data or []))
                except (ValueError, TypeError):
                    pass

        # 3. Demanda laboral real del sector: empleo GEIH del último periodo (reemplaza PILA)
        empleo_sector = 0
        periodo_geih = None
        try:
            r_per = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
            periodo_geih = r_per.data[0]["periodo"] if r_per.data else None
            if periodo_geih and ciiu2_codes:
                r_emp = supabase.table("geih_empleo_sector_mensual").select("rama_ciiu, empleo").eq("periodo", periodo_geih).execute()
                seen = set()
                for row in r_emp.data or []:
                    rama = str(row.get("rama_ciiu") or "")
                    if rama[:2].zfill(2) in ciiu2_codes and rama not in seen:
                        seen.add(rama)
                        empleo_sector += int(row.get("empleo") or 0)
        except Exception:
            pass

        # 4. Contexto EMICRON del sector
        emicron_contexto = {}
        try:
            g12 = int(req.sector) if req.sector and req.sector.isdigit() else None
            if not g12:
                g12 = _detectar_grupos12(req.sector or "")
            if g12:
                r_ano = supabase.table("emicron_resumen_nacional_v2").select("ano").order("ano", desc=True).limit(1).execute()
                ano = r_ano.data[0]["ano"] if r_ano.data else 2024
                r_emic = supabase.table("emicron_por_sector_v2").select("*").eq("grupos12", g12).eq("ano", ano).execute()
                if r_emic.data:
                    e = r_emic.data[0]
                    emicron_contexto = {
                        "ano": ano,
                        "micronegocios": int(e.get("micronegocios") or 0),
                        "ingreso_promedio_mensual": int(e.get("ingreso_promedio") or 0),
                        "pct_usa_internet": e.get("pct_usa_internet"),
                        "pct_tiene_credito": e.get("pct_tiene_credito"),
                    }
        except Exception:
            pass

        # 5. Sectores emergentes nacionales (RUES)
        emergentes = supabase.table("rues_top_sectores_nacional").select("*").limit(10).execute()

        # Calcular componentes del índice 0-100
        # Crecimiento: empresas nuevas recientes vs activas (0-25)
        crecimiento_score = min(25, (empresas_nuevas / max(empresas_activas, 1)) * 100 * 5)

        # Demanda laboral: empleo GEIH normalizado (0-25); 500K = máximo
        demanda_score = min(25, (empleo_sector / 500_000) * 25)

        # Competencia: inverso a empresas activas (menos competencia = mejor) (0-25)
        competencia_score = max(0, 25 - min(25, (empresas_activas / 20000) * 25))

        # Contexto regional: menor desempleo = mejor (0-25)
        contexto_score = max(0, 25 - (tasa_desempleo / 20) * 25)

        indice = round(crecimiento_score + demanda_score + competencia_score + contexto_score)

        # Determinar nivel y recomendaciones base
        if indice >= 75:
            nivel = "Alto potencial"
            color = "verde"
        elif indice >= 50:
            nivel = "Potencial moderado"
            color = "amarillo"
        elif indice >= 25:
            nivel = "Potencial bajo"
            color = "naranja"
        else:
            nivel = "Muy bajo potencial"
            color = "rojo"

        recomendaciones = []
        if crecimiento_score < 10:
            recomendaciones.append("El sector muestra poca dinámica de nuevas empresas; considera validar la idea con encuestas locales.")
        if demanda_score < 10:
            recomendaciones.append("El empleo real en este sector es reducido; evalúa si el negocio puede generar sus propios puestos de trabajo.")
        if competencia_score < 10:
            recomendaciones.append("Hay mucha competencia establecida; diferenciación y nicho serán clave.")
        if contexto_score < 10:
            recomendaciones.append(f"El desempleo en {depto.title()} es alto ({tasa_desempleo:.1f}%); esto puede afectar el poder adquisitivo local.")

        if not recomendaciones:
            recomendaciones.append("El sector muestra condiciones favorables en crecimiento, demanda y competencia.")
            recomendaciones.append("Revisa convocatorias de Fondo Emprender, iNNpulsa y la Cámara de Comercio local.")

        return {
            "municipio": req.municipio,
            "departamento": depto.title(),
            "sector_consultado": req.sector,
            "indice_oportunidad": indice,
            "nivel": nivel,
            "color": color,
            "componentes": {
                "crecimiento": round(crecimiento_score, 1),
                "demanda_laboral": round(demanda_score, 1),
                "competencia": round(competencia_score, 1),
                "contexto_regional": round(contexto_score, 1),
            },
            "datos": {
                "ocupados": ocupados,
                "no_ocupados": no_ocupados,
                "tasa_desempleo": round(tasa_desempleo, 2),
                "empresas_activas_sector": empresas_activas,
                "empresas_nuevas_sector": empresas_nuevas,
                "empleo_sector_geih": empleo_sector,
                "periodo_empleo_geih": periodo_geih,
                "contexto_emicron": emicron_contexto,
            },
            "recomendaciones": recomendaciones,
            "sectores_emergentes_nacional": [
                {"ciiu2": s.get("ciiu2"), "empresas_activas": s.get("empresas_activas")}
                for s in (emergentes.data or [])[:5]
            ],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-sectores/{departamento}")
async def top_sectores_oportunidad(departamento: str):
    """Devuelve los sectores con mayor Índice de Oportunidad para un departamento."""
    try:
        depto = _normalizar(departamento)

        des = supabase.table("geih_desempleo_departamento").select("*").eq("departamento", depto).execute()
        no_ocupados = des.data[0].get("no_ocupados", 0) if des.data else 0
        ocu = supabase.table("geih_resumen_departamento").select("*").eq("departamento", depto).execute()
        ocupados = ocu.data[0].get("ocupados", 0) if ocu.data else 0
        total_pea = ocupados + no_ocupados
        tasa_desempleo = (no_ocupados / total_pea * 100) if total_pea > 0 else 0

        rues = supabase.table("rues_resumen_camara_ciiu").select("*").execute()
        df_rues = pd.DataFrame(rues.data or [])

        pila = supabase.table("pila_resumen_sector").select("*").execute()
        df_pila = pd.DataFrame(pila.data or [])

        resultados = []
        # Agrupar por CIIU2
        if not df_rues.empty and "ciiu2" in df_rues.columns:
            for ciiu2, group in df_rues.groupby("ciiu2"):
                emp_activas = int(group["empresas_activas"].sum())
                emp_nuevas = int(group["empresas_nuevas"].sum()) if "empresas_nuevas" in group.columns else 0
                desc_raw = str(group["actividadeconomicadesc"].iloc[0]) if "actividadeconomicadesc" in group.columns else ""
                desc = desc_raw.strip() or CIIU2_DESCRIPCIONES.get(ciiu2, f"CIIU {ciiu2}")

                # Buscar cotizantes PILA por descripción similar (PILA no tiene ciiu2)
                cotizantes = 0
                if not df_pila.empty and "actividadeconomicadesc" in df_pila.columns and "total_cotizantes" in df_pila.columns:
                    desc_upper = desc.upper()
                    # Extraer código CIIU4 del inicio de la descripción si existe
                    codigo_pila = None
                    if " - " in desc:
                        codigo_pila = desc.split(" - ")[0].strip()
                    if codigo_pila and codigo_pila[:2] == ciiu2:
                        pila_group = df_pila[df_pila["actividadeconomicadesc"].str.upper().str.startswith(codigo_pila, na=False)]
                    else:
                        pila_group = df_pila[df_pila["actividadeconomicadesc"].str.upper().str.contains(ciiu2, na=False)]
                    cotizantes = int(pila_group["total_cotizantes"].sum()) if not pila_group.empty else 0

                # Nombre legible: mapeo CIIU2 canonico
                nombre_sector = CIIU_NOMBRES.get(ciiu2, desc[:60].strip() or f"Sector CIIU {ciiu2}")

                # Normalizar scores usando percentiles logarítmicos para evitar saturación
                import math
                def _log_score(val: float, cap: float = 25) -> float:
                    return min(cap, math.log1p(val) / math.log1p(cap * 100) * cap)

                crecimiento = min(25, (emp_nuevas / max(emp_activas, 1)) * 100 * 5)
                demanda = _log_score(cotizantes, 25)
                competencia = max(0, 25 - _log_score(emp_activas, 25))
                contexto = max(0, 25 - (tasa_desempleo / 20) * 25)
                indice = round(crecimiento + demanda + competencia + contexto)

                resultados.append({
                    "ciiu2": ciiu2,
                    "sector": nombre_sector,
                    "indice_oportunidad": indice,
                    "empresas_activas": emp_activas,
                    "empresas_nuevas": emp_nuevas,
                    "cotizantes_formales": cotizantes,
                })

        resultados = sorted(resultados, key=lambda x: x["indice_oportunidad"], reverse=True)[:10]
        return {"departamento": depto.title(), "sectores": resultados}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NUEVOS ENDPOINTS: EMICRON + GEIH real (datos del ETL)
# ============================================================================

@router.get("/emicron/resumen")
async def get_emicron_resumen():
    """Resumen nacional de micronegocios (EMICRON 2021-2024)."""
    try:
        r = supabase.table("emicron_resumen_nacional").select("*").order("ano", desc=True).execute()
        return {
            "total_anios": len(r.data),
            "resumen": [
                {
                    "ano": row.get("ano"),
                    "total_micronegocios": int(row.get("total_micronegocios") or 0),
                    "pct_usa_internet": row.get("pct_usa_internet"),
                    "pct_tiene_credito": row.get("pct_tiene_credito"),
                    "empleo_generado": int(row.get("empleo_generado") or 0),
                    "ingreso_promedio_mensual": int(row.get("ingreso_promedio_mensual") or 0) if row.get("ingreso_promedio_mensual") else None,
                }
                for row in r.data
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emicron/motivos-emprendimiento")
async def get_emicron_motivos():
    """Distribucion de motivos de emprendimiento (EMICRON).
    1=Perdida empleo, 2=Oportunidad, 3=Dificultad conseguir empleo, 4=Tradicion familiar."""
    try:
        r = supabase.table("emicron_emprendimiento").select("*").order("ano", desc=True).order("micronegocios", desc=True).execute()
        motivos_map = {
            1: "Perdida o cierre de empleo",
            2: "Oportunidad de negocio",
            3: "Dificultad para conseguir empleo",
            4: "Tradicion familiar",
            5: "Independencia",
            6: "Otro",
        }
        return {
            "motivos": [
                {
                    "ano": row.get("ano"),
                    "codigo_motivo": int(row.get("codigo_motivo") or 0),
                    "motivo": motivos_map.get(int(row.get("codigo_motivo") or 0), "Otro"),
                    "micronegocios": int(row.get("micronegocios") or 0),
                }
                for row in r.data
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emicron/departamento/{dpto}")
async def get_emicron_por_depto(dpto: int):
    """Micronegocios por departamento (codigo DIVIPOLA) a lo largo de los anos."""
    try:
        r = supabase.table("emicron_por_departamento").select("*").eq("dpto", dpto).order("ano", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay datos para departamento {dpto}")
        return {
            "dpto": dpto,
            "serie": [
                {"ano": row.get("ano"), "micronegocios": int(row.get("micronegocios") or 0)}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# RNT - Registro Nacional de Turismo (MinCIT) para Emprende IA
# Sector: alojamiento, restaurantes, agencias de viaje, guias, etc.
# ============================================================================

# Palabras clave por categoria RNT para detectar sector desde una idea de negocio
RNT_CATEGORIAS_POR_KEYWORD = {
    "alojamiento": ["hotel", "hostal", "apartahotel", "hospedaje", "alojamiento",
                    "finca turistica", "casa turistica", "apartamento turistico",
                    "vivienda turistica", "posada", "cabaña"],
    "gastronomia": ["restaurante", "bar", "cafeteria", "comida", "gastronomia",
                    "fritanga", "comidas rapidas", "delivery saludable"],
    "agencias": ["agencia de viajes", "tour", "operador turistico", "tours",
                "operador turista"],
    "guias": ["guia de turismo", "guia turistico"],
    "transporte": ["transporte turistico", "transporte de turistas"],
    "eventos": ["congreso", "feria", "convencion", "eventos"],
}


def _detectar_categoria_rnt(idea: str) -> str | None:
    """Detecta la categoria RNT relevante a partir de una idea de negocio."""
    idea_lower = idea.lower()
    for cat, keywords in RNT_CATEGORIAS_POR_KEYWORD.items():
        for kw in keywords:
            if kw in idea_lower:
                return cat
    return None


@router.get("/turismo/resumen-nacional")
async def get_rnt_resumen_nacional():
    """Establecimientos turisticos activos a nivel nacional por categoria y sub_categoria."""
    try:
        r = supabase.table("rnt_resumen_nacional_categoria").select("*") \
            .order("establecimientos", desc=True).execute()
        return {
            "total_establecimientos": sum(int(row.get("establecimientos") or 0) for row in r.data),
            "categorias": [
                {
                    "categoria": row.get("categoria"),
                    "sub_categoria": row.get("sub_categoria"),
                    "establecimientos": int(row.get("establecimientos") or 0),
                    "habitaciones": int(row.get("habitaciones") or 0),
                    "camas": int(row.get("camas") or 0),
                    "empleados": int(row.get("empleados") or 0),
                }
                for row in r.data
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/turismo/departamento/{departamento}")
async def get_rnt_por_departamento(departamento: str):
    """Establecimientos turisticos activos por departamento y categoria."""
    try:
        depto = _normalizar(departamento)
        r = supabase.table("rnt_resumen_departamento_categoria").select("*") \
            .eq("departamento", depto).order("establecimientos", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Sin datos RNT para {departamento}")
        total = sum(int(row.get("establecimientos") or 0) for row in r.data)
        return {
            "departamento": depto.title(),
            "total_establecimientos": total,
            "por_categoria": [
                {
                    "categoria": row.get("categoria"),
                    "establecimientos": int(row.get("establecimientos") or 0),
                    "habitaciones": int(row.get("habitaciones") or 0),
                    "camas": int(row.get("camas") or 0),
                    "empleados": int(row.get("empleados") or 0),
                }
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/turismo/top-municipios")
async def get_rnt_top_municipios(categoria: str | None = None, limit: int = 10):
    """Top municipios con mas establecimientos turisticos (opcionalmente por categoria)."""
    try:
        query = supabase.table("rnt_resumen_municipio_categoria").select("*")
        if categoria:
            query = query.eq("categoria", _normalizar(categoria))
        r = query.execute()
        if not r.data:
            return {"municipios": []}
        df = pd.DataFrame(r.data)
        agg = df.groupby(["departamento", "municipio"], as_index=False).agg({
            "establecimientos": "sum",
            "habitaciones": "sum",
            "camas": "sum",
            "empleados": "sum",
        }).sort_values("establecimientos", ascending=False).head(limit)
        return {
            "categoria": categoria,
            "municipios": [
                {
                    "departamento": row["departamento"].title(),
                    "municipio": row["municipio"].title(),
                    "establecimientos": int(row["establecimientos"]),
                    "habitaciones": int(row["habitaciones"]),
                    "camas": int(row["camas"]),
                    "empleados": int(row["empleados"]),
                }
                for _, row in agg.iterrows()
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# FINAGRO - Credito agropecuario para Emprende IA
# Sector: agricultura, ganaderia, actividades rurales
# ============================================================================

@router.get("/agro/resumen-nacional-anual")
async def get_finagro_resumen_nacional():
    """Resumen nacional anual de colocaciones de credito agropecuario (FINAGRO)."""
    try:
        r = supabase.table("finagro_resumen_nacional_anual").select("*") \
            .order("ano", desc=True).execute()
        return {
            "resumen": [
                {
                    "ano": int(row.get("ano")),
                    "total_colocacion_cop": int(row.get("total_colocacion") or 0),
                    "total_inversion_cop": int(row.get("total_inversion") or 0),
                    "num_operaciones": int(row.get("num_operaciones") or 0),
                    "departamentos_atendidos": int(row.get("departamentos_atendidos") or 0),
                    "cultivos_atendidos": int(row.get("cultivos_atendidos") or 0),
                }
                for row in r.data
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agro/top-cultivos")
async def get_finagro_top_cultivos(limit: int = 20):
    """Top cultivos/actividades con mas credito desembolsado a nivel nacional."""
    try:
        r = supabase.table("finagro_colocaciones_cadena").select("*") \
            .order("total_colocacion", desc=True).limit(limit).execute()
        return {
            "cultivos": [
                {
                    "cultivo": row.get("cultivo"),
                    "total_colocacion_cop": int(row.get("total_colocacion") or 0),
                    "num_operaciones": int(row.get("num_operaciones") or 0),
                    "departamentos": int(row.get("departamentos") or 0),
                }
                for row in r.data
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agro/departamento/{departamento}")
async def get_finagro_por_departamento(departamento: str):
    """Creditos agropecuarios desembolsados por departamento (2020-2024)."""
    try:
        depto = _normalizar(departamento)
        r = supabase.table("finagro_resumen_departamento").select("*") \
            .eq("departamento_inversion", depto).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Sin datos FINAGRO para {departamento}")
        row = r.data[0]
        # Top cultivos de ese departamento
        top = supabase.table("finagro_top_cadenas_departamento").select("*") \
            .eq("departamento_inversion", depto).order("rank").limit(10).execute()
        return {
            "departamento": depto.title(),
            "total_colocacion_cop": int(row.get("total_colocacion") or 0),
            "total_inversion_cop": int(row.get("total_inversion") or 0),
            "num_operaciones": int(row.get("num_operaciones") or 0),
            "cultivos_distintos": int(row.get("cultivos_distintos") or 0),
            "top_cultivos": [
                {
                    "rank": int(t.get("rank") or 0),
                    "cultivo": t.get("cultivo"),
                    "total_colocacion_cop": int(t.get("total_colocacion") or 0),
                    "num_operaciones": int(t.get("num_operaciones") or 0),
                }
                for t in (top.data or [])
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agro/cultivo/{cultivo}")
async def get_finagro_por_cultivo(cultivo: str):
    """Top departamentos que mas credito recibieron para un cultivo especifico
    (ej. ARROZ SECANO, VIENTRES BOVINOS, SOSTENIMIENTO CAFE)."""
    try:
        cultivo_q = _normalizar(cultivo)
        r = supabase.table("finagro_top_cadenas_departamento").select("*") \
            .eq("cultivo", cultivo_q).order("total_colocacion", desc=True).limit(20).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Sin datos FINAGRO para cultivo '{cultivo}'")
        return {
            "cultivo": cultivo,
            "departamentos": [
                {
                    "departamento": row.get("departamento_inversion", "").title(),
                    "total_colocacion_cop": int(row.get("total_colocacion") or 0),
                    "num_operaciones": int(row.get("num_operaciones") or 0),
                }
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EMICRON v2 - Micronegocios por sector (costos, tipos de local, ingresos)
# ============================================================================

# Mapeo de sector de idea de negocio -> GRUPOS12
SECTOR_IDEA_GRUPOS12 = {
    "restaurante": 9, "cafeteria": 9, "comida": 9, "fritanga": 9, "delivery": 9,
    "bar": 9, "alojamiento": 9, "hotel": 9, "hostal": 9, "posada": 9, "hospedaje": 9,
    "finca turistica": 9, "apartamento turistico": 9,
    "comercio": 7, "tienda": 7, "venta": 7, "mayorista": 6, "distribuidor": 6,
    "agricultura": 1, "cultivo": 1, "finca": 1, "ganaderia": 1, "agro": 1,
    "construccion": 5, "obra": 5, "constructora": 5,
    "manufactura": 3, "fabrica": 3, "taller": 3, "produccion": 3,
    "transporte": 8, "logistica": 8, "flete": 8,
    "software": 12, "tecnologia": 12, "consultoria": 12, "servicios profesionales": 12,
    "financiero": 11, "seguros": 11,
}


def _detectar_grupos12(idea: str) -> int | None:
    """Detecta el sector GRUPOS12 relevante a partir de una idea de negocio."""
    idea_lower = idea.lower()
    for kw, g in SECTOR_IDEA_GRUPOS12.items():
        if kw in idea_lower:
            return g
    return None


@router.get("/emicron/sector/{grupos12}")
async def get_emicron_por_sector(grupos12: int, ano: int | None = None):
    """Perfil completo de un sector de micronegocios (EMICRON v2):
    cuantos hay, ingreso promedio, costo de operacion, tipos de local."""
    try:
        if ano is None:
            r_ano = supabase.table("emicron_resumen_nacional_v2").select("ano").order("ano", desc=True).limit(1).execute()
            ano = r_ano.data[0]["ano"] if r_ano.data else 2024

        # Datos del sector
        r = supabase.table("emicron_por_sector_v2").select("*").eq("grupos12", grupos12).eq("ano", ano).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Sin datos EMICRON para sector {grupos12} en {ano}")
        sec = r.data[0]

        # Costos del sector
        r_cost = supabase.table("emicron_costos_sector").select("*").eq("grupos12", grupos12).eq("ano", ano).execute()
        costo = r_cost.data[0] if r_cost.data else {}

        # Tipos de local del sector
        r_loc = supabase.table("emicron_ubicacion_sector").select("*").eq("grupos12", grupos12).eq("ano", ano).order("pct", desc=True).execute()
        tipos_local = [
            {
                "p3053": int(row.get("p3053") or 0),
                "tipo_local": row.get("tipo_local"),
                "pct": row.get("pct"),
            }
            for row in (r_loc.data or [])
        ]

        return {
            "grupos12": grupos12,
            "sector": sec.get("sector"),
            "ano": ano,
            "micronegocios": int(sec.get("micronegocios") or 0),
            "ingreso_promedio_mensual": int(sec.get("ingreso_promedio") or 0),
            "pct_usa_internet": sec.get("pct_usa_internet"),
            "pct_tiene_credito": sec.get("pct_tiene_credito"),
            "costo_operacion": {
                "costo_mediano_mensual": int(costo.get("costo_mediano_mensual") or 0),
                "consumo_intermedio_mediano": int(costo.get("consumo_intermedio_mediano") or 0),
            } if costo else None,
            "tipos_local": tipos_local,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
