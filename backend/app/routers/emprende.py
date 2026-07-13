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


def _contexto_mercado(departamento: str, sector: str | None = None) -> dict:
    """Obtiene indicadores de mercado para enriquecer la evaluación con LLM."""
    depto = _normalizar(departamento)

    ocu = supabase.table("geih_resumen_departamento").select("*").eq("departamento", depto).execute()
    des = supabase.table("geih_desempleo_departamento").select("*").eq("departamento", depto).execute()
    ocupados = ocu.data[0].get("ocupados", 0) if ocu.data else 0
    no_ocupados = des.data[0].get("no_ocupados", 0) if des.data else 0
    total_pea = ocupados + no_ocupados
    tasa_desempleo = (no_ocupados / total_pea * 100) if total_pea > 0 else 0

    rues = supabase.table("rues_resumen_camara_ciiu").select("*").execute()
    df_rues = pd.DataFrame(rues.data or [])
    if sector and not df_rues.empty:
        sector_q = sector.upper()
        mask = df_rues.apply(
            lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
            axis=1,
        )
        df_sector = df_rues[mask]
    else:
        df_sector = df_rues
    empresas_activas = int(df_sector["empresas_activas"].sum()) if not df_sector.empty else 0
    empresas_nuevas = int(df_sector["empresas_nuevas"].sum()) if not df_sector.empty and "empresas_nuevas" in df_sector.columns else 0

    pila = supabase.table("pila_resumen_sector").select("*").execute()
    df_pila = pd.DataFrame(pila.data or [])
    if sector and not df_pila.empty:
        sector_q = sector.upper()
        mask_pila = df_pila.apply(
            lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
            axis=1,
        )
        df_pila_sector = df_pila[mask_pila]
    else:
        df_pila_sector = df_pila
    cotizantes = int(df_pila_sector["total_cotizantes"].sum()) if not df_pila_sector.empty else 0

    emergentes = supabase.table("rues_top_sectores_nacional").select("*").limit(5).execute()

    return {
        "departamento": departamento,
        "tasa_desempleo": round(tasa_desempleo, 2),
        "ocupados": ocupados,
        "no_ocupados": no_ocupados,
        "empresas_activas_sector": empresas_activas,
        "empresas_nuevas_sector": empresas_nuevas,
        "cotizantes_formales_sector": cotizantes,
        "sectores_emergentes_nacional": [
            {"ciiu2": s.get("ciiu2"), "empresas_activas": s.get("empresas_activas")}
            for s in (emergentes.data or [])
        ],
    }


@router.post("/evaluar-idea")
async def evaluar_idea(req: EvaluarIdeaRequest):
    """Evalúa una idea de negocio con LLM + datos reales de mercado."""
    try:
        # Extraer palabras clave del sector de la idea (primeras palabras significativas)
        palabras_clave = [p for p in req.idea.split() if len(p) > 4][:3]
        sector = " ".join(palabras_clave)

        contexto = _contexto_mercado(req.departamento, sector)
        contexto_texto = (
            f"Tasa de desempleo en {contexto['departamento']}: {contexto['tasa_desempleo']}%\n"
            f"Ocupados: {contexto['ocupados']:,}, no ocupados: {contexto['no_ocupados']:,}\n"
            f"Empresas activas en sector relacionado: {contexto['empresas_activas_sector']:,}\n"
            f"Empresas nuevas recientes: {contexto['empresas_nuevas_sector']:,}\n"
            f"Cotizantes formales en sector: {contexto['cotizantes_formales_sector']:,}\n"
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

        # Filtrar por sector si se especifica
        if req.sector:
            sector_q = req.sector.upper()
            mask = df_rues.apply(
                lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
                axis=1,
            )
            df_sector = df_rues[mask]
        else:
            df_sector = df_rues

        empresas_activas = int(df_sector["empresas_activas"].sum()) if not df_sector.empty else 0
        empresas_nuevas = int(df_sector["empresas_nuevas"].sum()) if not df_sector.empty and "empresas_nuevas" in df_sector.columns else 0

        # 3. Demanda laboral del sector (PILA)
        pila = supabase.table("pila_resumen_sector").select("*").execute()
        df_pila = pd.DataFrame(pila.data or [])
        if req.sector:
            sector_q = req.sector.upper()
            mask_pila = df_pila.apply(
                lambda r: sector_q in str(r.get("ciiu2", "")).upper() or sector_q in str(r.get("actividadeconomicadesc", "")).upper(),
                axis=1,
            )
            df_pila_sector = df_pila[mask_pila]
        else:
            df_pila_sector = df_pila
        cotizantes = int(df_pila_sector["total_cotizantes"].sum()) if not df_pila_sector.empty else 0

        # 4. Sectores emergentes nacionales (RUES)
        emergentes = supabase.table("rues_top_sectores_nacional").select("*").limit(10).execute()

        # Calcular componentes del índice 0-100
        # Crecimiento: empresas nuevas recientes vs activas (0-25)
        crecimiento_score = min(25, (empresas_nuevas / max(empresas_activas, 1)) * 100 * 5)

        # Demanda laboral: cotizantes normalizados (0-25)
        demanda_score = min(25, (cotizantes / 50000) * 25)

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
            recomendaciones.append("La demanda laboral formal en este sector es limitada; evalúa si el negocio depende de empleados formales.")
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
                "cotizantes_formales_sector": cotizantes,
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
                    "sector": desc[:60],
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
