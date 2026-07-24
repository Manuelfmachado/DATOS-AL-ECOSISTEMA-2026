"""
Router del Match Inteligente (Función #3).
Cruza perfiles, programas, empresas y territorios con la demanda laboral real.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase import supabase
from app.services.llm import match_cv_vacante as deepinfra_match_cv_vacante, match_pensum as deepinfra_match_pensum
from app.services.llm_gemini import (
    match_cv_vacante as gemini_match_cv_vacante,
    match_pensum_mercado as gemini_match_pensum_mercado,
    is_gemini_available,
)
import pandas as pd

router = APIRouter(prefix="/api/match", tags=["match"])


def _norm(text: str) -> str:
    return text.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N").strip()


class MatchRequest(BaseModel):
    universidad: str
    programa: str
    sector_objetivo: str | None = None
    departamento: str = "BOGOTÁ"


class PersonaRequest(BaseModel):
    perfil: str
    habilidades: list[str] = []
    experiencia_anos: int = 0
    departamento: str = "BOGOTÁ"


class EmpresaRequest(BaseModel):
    sector: str
    cargo: str = ""
    tamano: str = "mediana"
    departamento: str = "BOGOTÁ"


class MunicipioRequest(BaseModel):
    departamento: str
    municipio: str = ""


class ReskillingRequest(BaseModel):
    habilidad_actual: str
    habilidad_objetivo: str


class CvVacanteRequest(BaseModel):
    cv: str
    vacante: str


class PensumRequest(BaseModel):
    pensum: str


@router.post("/cv-vacante")
async def analizar_cv_vacante(req: CvVacanteRequest):
    """Analiza el match entre un CV/perfil y una vacante laboral usando ESCO + OLE + LLM."""
    try:
        # 1. Extraer ocupación de la vacante (primeras palabras clave)
        vacante_palabras = req.vacante.split('\n')[0][:50]  # Primera línea o título
        
        # 2. Buscar ocupación en ESCO
        esco_data = None
        habilidades_requeridas = []
        try:
            r_occ = supabase.table("esco_ocupaciones").select("*").ilike("nombre", f"%{vacante_palabras}%").limit(1).execute()
            if r_occ.data:
                occ_nombre = r_occ.data[0].get("nombre")
                r_skills = supabase.table("esco_ocupacion_habilidades").select("*").eq("ocupacion_nombre", occ_nombre).execute()
                habilidades_requeridas = [s.get("habilidad_nombre") for s in r_skills.data if s.get("habilidad_nombre")]
                esco_data = {
                    "ocupacion": occ_nombre,
                    "habilidades_esenciales": [s.get("habilidad_nombre") for s in r_skills.data if s.get("tipo_relacion") == "essential"],
                    "habilidades_opcionales": [s.get("habilidad_nombre") for s in r_skills.data if s.get("tipo_relacion") == "optional"],
                }
        except Exception as e:
            print(f"[Match] Error buscando ESCO: {e}")
        
        # 3. Buscar salarios reales en OLE (si hay programa relacionado)
        ole_data = None
        try:
            programa_busqueda = vacante_palabras.split()[0] if vacante_palabras else ""
            if programa_busqueda:
                r_ole = supabase.table("ole_ingresos_por_programa").select("*").ilike("programa", f"%{programa_busqueda}%").order("graduados", desc=True).limit(10).execute()
                if r_ole.data:
                    # Calcular rango modal
                    rangos = {}
                    for row in r_ole.data:
                        rango = row.get("rango_ingreso")
                        if rango:
                            if rango not in rangos:
                                rangos[rango] = 0
                            rangos[rango] += int(row.get("graduados") or 0)
                    if rangos:
                        rango_modal = max(rangos.items(), key=lambda x: x[1])[0]
                        total_graduados = sum(rangos.values())
                        ole_data = {
                            "rango_modal": rango_modal,
                            "total_graduados": total_graduados,
                            "fuente": "OLE-MEN 2001-2022"
                        }
        except Exception as e:
            print(f"[Match] Error buscando OLE: {e}")
        
        # 4. Usar LLM para análisis cualitativo (interpretación, recursos)
        if is_gemini_available():
            resultado = gemini_match_cv_vacante(req.cv, req.vacante)
        else:
            resultado = deepinfra_match_cv_vacante(req.cv, req.vacante)
        
        # 5. Si tenemos ESCO, ajustar score basado en datos reales
        if esco_data and habilidades_requeridas:
            # Extraer habilidades del CV (simple: palabras clave comunes)
            cv_lower = req.cv.lower()
            habilidades_cv = [h for h in habilidades_requeridas if h.lower() in cv_lower]
            
            # Score real basado en intersección
            if habilidades_requeridas:
                score_real = round(len(habilidades_cv) / len(habilidades_requeridas) * 100)
                # Promediar con score del LLM (50% cada uno)
                score_llm = resultado.get("score_match", 50)
                resultado["score_match"] = round((score_real + score_llm) / 2)
                
                # Añadir metadatos de ESCO
                resultado["esco_ocupacion"] = esco_data["ocupacion"]
                resultado["habilidades_requeridas_esco"] = len(habilidades_requeridas)
                resultado["habilidades_detectadas"] = habilidades_cv
        
        # 6. Si tenemos OLE, añadir datos de salarios reales
        if ole_data:
            resultado["salario_real"] = ole_data
        
        # 7. Normalizar pesos de brechas para que sumen exactamente (100 - score)
        score = resultado.get("score_match", 0)
        brechas = resultado.get("brechas", [])
        if brechas:
            peso_total = sum(b.get("peso", 0) for b in brechas)
            peso_objetivo = max(0, 100 - score)
            if peso_total > 0:
                for b in brechas:
                    b["peso"] = round(b.get("peso", 0) / peso_total * peso_objetivo)
        
        return resultado
    except Exception as e:
        print(f"[Match] Gemini falló ({e}), usando DeepInfra fallback.")
        try:
            resultado = deepinfra_match_cv_vacante(req.cv, req.vacante)
            # Normalizar pesos también en fallback
            score = resultado.get("score_match", 0)
            brechas = resultado.get("brechas", [])
            if brechas:
                peso_total = sum(b.get("peso", 0) for b in brechas)
                peso_objetivo = max(0, 100 - score)
                if peso_total > 0:
                    for b in brechas:
                        b["peso"] = round(b.get("peso", 0) / peso_total * peso_objetivo)
            return resultado
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


@router.post("/pensum")
async def analizar_pensum(req: PensumRequest):
    """Analiza la alineación de un pensum académico con el mercado laboral usando LLM."""
    try:
        if is_gemini_available():
            return gemini_match_pensum_mercado(req.pensum)
        return deepinfra_match_pensum(req.pensum)
    except Exception as e:
        print(f"[Match] Gemini falló ({e}), usando DeepInfra fallback.")
        try:
            return deepinfra_match_pensum(req.pensum)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


@router.post("/perfil")
async def analizar_match(req: MatchRequest):
    """Analiza el match entre un programa universitario y el mercado laboral."""
    try:
        # Programas de la universidad
        snies = supabase.table("snies_programas_matriculados").select("*").ilike("institucion", f"%{req.universidad}%").ilike("programa", f"%{req.programa}%").execute()

        if not snies.data:
            # Buscar solo por programa
            snies = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{req.programa}%").execute()

        # Resultados Saber Pro
        saber = supabase.table("saberpro_resumen_programas").select("*").ilike("programa", f"%{req.programa}%").execute()

        # Sectores formales (demanda)
        pila = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(30).execute()

        # Cursos SENA complementarios
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{req.programa[:15]}%").limit(10).execute()

        # Calcular score de match (proxy)
        matriculados = sum(p.get("matriculados", 0) or 0 for p in snies.data)
        cotizantes = sum(p.get("total_cotizantes", 0) or 0 for p in pila.data)

        if matriculados > 0 and cotizantes > 0:
            ratio = cotizantes / matriculados
            if ratio > 10:
                match_score = 85
                status = "alta_demanda"
            elif ratio > 3:
                match_score = 65
                status = "demanda_media"
            elif ratio > 1:
                match_score = 45
                status = "equilibrado"
            else:
                match_score = 25
                status = "saturado"
        else:
            match_score = None
            status = "datos_insuficientes"

        return {
            "universidad": req.universidad,
            "programa": req.programa,
            "departamento": req.departamento,
            "programas_encontrados": len(snies.data),
            "total_matriculados": matriculados,
            "cotizantes_formales": cotizantes,
            "match_score": match_score,
            "status_match": status,
            "resultados_saber_pro": len(saber.data),
            "saber_pro": saber.data[0] if saber.data else None,
            "cursos_sena_complementarios": [{"programa": s.get("programa"), "area": s.get("area_desempeno")} for s in sena.data[:5]],
            "sectores_demanda": [{"sector": p.get("actividadeconomicadesc"), "cotizantes": p.get("total_cotizantes")} for p in pila.data[:10]],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills-gap/{programa}")
async def get_skills_gap(programa: str):
    """Identifica brechas de habilidades para un programa."""
    try:
        # Buscar programa y cursos SENA
        snies = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{programa}%").limit(5).execute()
        sena = supabase.table("sena_programas_activos").select("*").limit(50).execute()
        saber = supabase.table("saberpro_resumen_programas").select("*").ilike("programa", f"%{programa}%").limit(5).execute()

        brechas = []
        if saber.data:
            ingles = saber.data[0].get("mod_ingles_punt")
            if ingles and ingles < 100:
                brechas.append({"habilidad": "Inglés", "nivel_actual": f"{ingles} pts", "nivel_requerido": "B2 (150+ pts)", "prioridad": "alta"})

            razonamiento = saber.data[0].get("mod_razona_cuantitat_punt")
            if razonamiento and razonamiento < 120:
                brechas.append({"habilidad": "Razonamiento cuantitativo", "nivel_actual": f"{razonamiento} pts", "nivel_requerido": "150+ pts", "prioridad": "media"})

        return {
            "programa": programa,
            "brechas_detectadas": brechas,
            "cursos_sena_disponibles": len(sena.data),
            "programas_snies_relacionados": len(snies.data),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/persona")
async def match_persona(req: PersonaRequest):
    """Encuentra dónde encaja una persona según su perfil y habilidades.

    Busca ocupaciones ESCO/O*NET usando el perfil del usuario (su descripción
    profesional) y términos derivados de sus habilidades. Busca cursos SENA
    por área de desempeño y programa."""
    try:
        # Palabras genéricas de habilidades blandas que producen falsos positivos
        # en búsquedas de ocupaciones (ej: "trabajo" → "trabajo social").
        _STOPWORDS = {
            "trabajo", "equipo", "comunicacion", "comunicación", "liderazgo",
            "gestion", "gestión", "responsabilidad", "iniciativa", "proactivo",
            "proactiva", "creatividad", "persona", "personas", "service",
            "cliente", "clientes", "organizacion", "organización",
            "experiencia", "conocimiento", "conocimientos", "manejo",
            "habilidad", "habilidades", "capacidad", "actitud",
        }
        # Términos muy genéricos que producen muchos falsos positivos. Se buscan
        # pero con menor prioridad (al final de la lista).
        _TERMINOS_GENERICOS = {
            "analisis", "análisis", "sistemas", "desarrollo", "gestión",
            "administracion", "administración", "servicios",
        }

        # Términos de búsqueda: extraer palabras significativas del perfil y habilidades.
        # Separar términos específicos (prioridad alta) de genéricos (prioridad baja).
        terminos_especificos: list[str] = []
        terminos_genericos_encontrados: list[str] = []
        todas_palabras: list[str] = []
        if req.perfil:
            todas_palabras.extend(req.perfil.split())
        for hab in (req.habilidades or []):
            todas_palabras.extend(hab.split())
        for palabra in todas_palabras:
            p = palabra.strip().lower()
            if len(p) < 4 or p in _STOPWORDS:
                continue
            if p in _TERMINOS_GENERICOS:
                if p not in terminos_genericos_encontrados:
                    terminos_genericos_encontrados.append(p)
            else:
                if p not in terminos_especificos:
                    terminos_especificos.append(p)
        # Términos específicos primero, genéricos al final
        terminos_unicos = terminos_especificos + terminos_genericos_encontrados

        # Buscar ocupaciones O*NET/ESCO: recopilar todas y rankear por relevancia
        # (cuántos términos del perfil matchean). Así "ingeniero de datos" (matchea
        # "datos" y "ingeniero") queda sobre "análisis sensorial" (solo "análisis").
        ocupaciones_vistas: set = set()
        ocupaciones_puntuadas: list[tuple[int, dict]] = []
        try:
            for termino in terminos_unicos[:6]:
                if not termino or len(termino) < 3:
                    continue
                # O*NET (títulos en inglés)
                onet = supabase.table("onet_occupations").select("*").ilike("title", f"%{termino}%").limit(5).execute()
                for o in onet.data:
                    title = o.get("title", "")
                    if title and title not in ocupaciones_vistas:
                        ocupaciones_vistas.add(title)
                        # Score: términos específicos valen 2, genéricos valen 1
                        title_lower = title.lower()
                        score = sum(2 if t in terminos_especificos else 1 for t in terminos_unicos if t in title_lower)
                        ocupaciones_puntuadas.append((score, {"id": o.get("onet_code"), "title": title, "source": "O*NET", "isco": o.get("isco_code")}))
                # ESCO ocupaciones
                esco = supabase.table("esco_ocupaciones").select("uri,nombre,codigo_isco").ilike("nombre", f"%{termino}%").limit(5).execute()
                for e in esco.data:
                    title = e.get("nombre", "")
                    if title and title not in ocupaciones_vistas:
                        ocupaciones_vistas.add(title)
                        title_lower = title.lower()
                        score = sum(2 if t in terminos_especificos else 1 for t in terminos_unicos if t in title_lower)
                        ocupaciones_puntuadas.append((score, {"id": e.get("uri"), "title": title, "source": "ESCO", "isco": e.get("codigo_isco")}))
        except Exception:
            pass

        # Ordenar por score de relevancia descendente (más términos matcheados primero)
        ocupaciones_puntuadas.sort(key=lambda x: -x[0])
        ocupaciones = [occ for _, occ in ocupaciones_puntuadas[:8]]

        # Agregar salario real y empleo real GEIH por código ISCO
        try:
            iscos = [int(o.get("isco")) for o in ocupaciones if o.get("isco")]
            salarios_map = {}
            if iscos:
                r_sal = supabase.table("geih_salario_ocupacion").select(
                    "oficio_c8,salario_promedio,salario_mediano,empleo_total,confianza"
                ).in_("oficio_c8", iscos).order("empleo_total", desc=True).execute()
                for row in r_sal.data or []:
                    cod = int(row.get("oficio_c8") or 0)
                    if cod not in salarios_map:
                        salarios_map[cod] = {
                            "promedio": row.get("salario_promedio"),
                            "mediano": row.get("salario_mediano"),
                            "empleo_total": row.get("empleo_total"),
                            "confianza": row.get("confianza"),
                        }
            for o in ocupaciones:
                isco = o.get("isco")
                datos = salarios_map.get(int(isco)) if isco else None
                o["salario_mercado"] = datos
        except Exception:
            pass

        # Buscar cursos SENA por programa y área de desempeño
        cursos_vistos: set = set()
        cursos: list[dict] = []
        try:
            for termino in terminos_unicos[:6]:
                if not termino or len(termino) < 3:
                    continue
                # Buscar en programa Y en area_desempeno
                sena_prog = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{termino}%").limit(3).execute()
                sena_area = supabase.table("sena_programas_activos").select("*").ilike("area_desempeno", f"%{termino}%").limit(3).execute()
                for s in (sena_prog.data + sena_area.data):
                    prog = s.get("programa", "")
                    if prog and prog not in cursos_vistos:
                        cursos_vistos.add(prog)
                        cursos.append({"programa": prog, "area": s.get("area_desempeno", "")})
                    if len(cursos) >= 6:
                        break
                if len(cursos) >= 6:
                    break
        except Exception:
            pass

        return {
            "perfil": req.perfil,
            "departamento": req.departamento,
            "ocupaciones_sugeridas": ocupaciones[:8],
            "cursos_sena_recomendados": cursos[:6],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/empresa")
async def match_empresa(req: EmpresaRequest):
    """Muestra dónde encontrar talento para una empresa.

    Demanda laboral medida con empleo real GEIH del último mes en lugar de
    inscritos SPE de 2020. Incluye salarios reales de la ocupación si están
    disponibles."""
    try:
        depto_norm = _norm(req.departamento)
        sector_q = req.sector[:30]

        # Programas universitarios relacionados con el sector/cargo
        snies = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{sector_q}%").limit(6).execute()

        # Cursos SENA activos
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{sector_q}%").limit(6).execute()

        # Demanda laboral real: ocupados GEIH del último periodo, filtrados por
        # ocupaciones ESCO cuyo nombre coincide con el cargo/sector buscado.
        empleo_total = 0
        ocupaciones_demandadas: list[dict] = []
        salario_ocupacion = None
        try:
            r_per = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
            periodo = r_per.data[0]["periodo"] if r_per.data else None

            # Buscar ocupaciones ESCO relacionadas
            esco = supabase.table("esco_ocupaciones").select("nombre,codigo_isco").ilike("nombre", f"%{sector_q}%").limit(10).execute()
            iscos = [int(e.get("codigo_isco")) for e in esco.data if e.get("codigo_isco")]

            if periodo and iscos:
                # Cruce GEIH: empleo por ocupación en el último periodo
                r_emp = supabase.table("geih_salario_ocupacion").select(
                    "oficio_c8,salario_promedio,salario_mediano,empleo_total,confianza"
                ).in_("oficio_c8", iscos).order("empleo_total", desc=True).limit(6).execute()
                for row in r_emp.data or []:
                    empleo = int(row.get("empleo_total") or 0)
                    if empleo > 0:
                        empleo_total += empleo
                        ocupaciones_demandadas.append({
                            "ocupacion": next((e.get("nombre") for e in esco.data if int(e.get("codigo_isco") or 0) == int(row.get("oficio_c8") or 0)), f"CIUO {row.get('oficio_c8')}"),
                            "empleo_total": empleo,
                            "salario_promedio": row.get("salario_promedio"),
                            "salario_mediano": row.get("salario_mediano"),
                            "confianza": row.get("confianza"),
                        })
                # Salario de la ocupación principal (mayor empleo)
                if r_emp.data:
                    top = r_emp.data[0]
                    salario_ocupacion = {
                        "promedio": top.get("salario_promedio"),
                        "mediano": top.get("salario_mediano"),
                        "confianza": top.get("confianza"),
                    }
        except Exception:
            pass

        # Graduados y matriculados
        total_graduados = sum(s.get("graduados", 0) or 0 for s in snies.data)
        total_matriculados = sum(s.get("matriculados", 0) or 0 for s in snies.data)

        return {
            "sector": req.sector,
            "cargo": req.cargo,
            "departamento": req.departamento,
            "talento_disponible": {
                "matriculados": total_matriculados,
                "graduados_anuales": total_graduados,
                "demanda_empleo_geih": empleo_total,
            },
            "programas_relacionados": [{"programa": s.get("programa"), "institucion": s.get("institucion"), "matriculados": s.get("matriculados")} for s in snies.data[:6]],
            "cursos_sena_disponibles": [{"programa": s.get("programa"), "area": s.get("area_desempeno")} for s in sena.data[:6]],
            "ocupaciones_demandadas_geih": ocupaciones_demandadas,
            "salario_ocupacion": salario_ocupacion,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/municipio")
async def match_municipio(req: MunicipioRequest):
    """Identifica sectores con mayor potencial en un municipio/departamento."""
    try:
        depto_norm = _norm(req.departamento)

        # RUES nacional: sectores con más nuevas empresas
        rues = supabase.table("rues_empresas_nuevas").select("*").order("empresas_nuevas", desc=True).limit(50).execute()
        df_rues = pd.DataFrame(rues.data or [])
        sectores = []
        if not df_rues.empty and "ciiu2" in df_rues.columns:
            df_rues["empresas_nuevas"] = pd.to_numeric(df_rues["empresas_nuevas"], errors="coerce").fillna(0)
            sectores = df_rues.groupby("ciiu2")["empresas_nuevas"].sum().reset_index().sort_values("empresas_nuevas", ascending=False).head(8).to_dict("records")
            sectores = [{"ciiu2": s.get("ciiu2"), "empresas_nuevas": int(s.get("empresas_nuevas", 0))} for s in sectores]

        # SPE demanda nacional
        spe = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(8).execute()

        # DNP desempeño por departamento
        dnp = supabase.table("dnp_medicion_desempeno_municipal").select("*").ilike("departamento", f"%{depto_norm}%").limit(50).execute()
        df_dnp = pd.DataFrame(dnp.data or [])
        dnp_pilar = None
        if not df_dnp.empty and "indicador" in df_dnp.columns and "dato" in df_dnp.columns:
            try:
                df_dnp["dato_num"] = pd.to_numeric(df_dnp["dato"], errors="coerce")
                pilar = df_dnp.groupby("indicador")["dato_num"].mean().dropna().sort_values(ascending=False).head(1)
                if not pilar.empty:
                    val = float(pilar.iloc[0])
                    if pd.notna(val) and abs(val) != float('inf'):
                        dnp_pilar = {"dimension": str(pilar.index[0]), "puntaje": round(val, 2)}
            except Exception:
                pass

        # Cursos SENA activos en el departamento
        sena = supabase.table("sena_programas_activos").select("*").ilike("departamento", f"%{depto_norm}%").limit(8).execute()

        def clean_num(v):
            if v is None:
                return None
            try:
                f = float(v)
                if pd.isna(f) or abs(f) == float('inf'):
                    return None
                return int(f) if f == int(f) else round(f, 2)
            except Exception:
                return None

        return {
            "departamento": req.departamento,
            "municipio": req.municipio or "Todos",
            "pilar_fortaleza_dnp": dnp_pilar,
            "sectores_emergentes_rues": [{"sector": f"CIIU2 {s.get('ciiu2')}", "nuevas_empresas": clean_num(s.get("empresas_nuevas"))} for s in sectores],
            "demanda_spe": [{"ocupacion": s.get("ocupacion"), "inscritos": clean_num(s.get("inscritos_2020"))} for s in spe.data],
            "cursos_sena_disponibles": [{"programa": s.get("programa"), "area": s.get("area_desempeno")} for s in sena.data[:6]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reskilling")
async def match_reskilling(req: ReskillingRequest):
    """Sugiere una ruta de reconversión entre una habilidad actual y una objetivo."""
    try:
        actual = req.habilidad_actual[:30]
        objetivo = req.habilidad_objetivo[:30]

        # Cursos SENA cercanos a ambas habilidades
        cursos_actual = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{actual}%").limit(4).execute()
        cursos_objetivo = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{objetivo}%").limit(6).execute()

        # Ocupaciones ESCO/O*NET relacionadas con objetivo
        ocupaciones = []
        try:
            onet = supabase.table("onet_occupations").select("*").ilike("title", f"%{objetivo}%").limit(3).execute()
            esco = supabase.table("esco_occupations").select("*").ilike("title", f"%{objetivo}%").limit(3).execute()
            for o in onet.data:
                ocupaciones.append({"id": o.get("onet_code"), "title": o.get("title"), "source": "O*NET"})
            for e in esco.data:
                ocupaciones.append({"id": e.get("concept_uri"), "title": e.get("title"), "source": "ESCO"})
        except Exception:
            pass

        # Ruta sugerida
        pasos = [
            f"Refuerza {actual} con un curso corto",
            f"Aprende fundamentos de {objetivo}",
            f"Practica con proyectos reales de {objetivo}",
            f"Certifícate en {objetivo} vía SENA u otra entidad",
            f"Postúlate a vacantes de {objetivo}",
        ]

        return {
            "habilidad_actual": req.habilidad_actual,
            "habilidad_objetivo": req.habilidad_objetivo,
            "ruta_sugerida": pasos,
            "cursos_puente": [{"programa": c.get("programa"), "area": c.get("area_desempeno")} for c in cursos_actual.data[:3]],
            "cursos_objetivo": [{"programa": c.get("programa"), "area": c.get("area_desempeno")} for c in cursos_objetivo.data[:6]],
            "ocupaciones_objetivo": ocupaciones[:4],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NUEVOS ENDPOINTS: ESCO + OLE + GEIH (datos reales del ETL)
# ============================================================================

@router.get("/esco/ocupacion/{nombre}")
async def get_ocupacion_esco(nombre: str):
    """Busca una ocupacion en ESCO y devuelve sus habilidades esenciales y opcionales."""
    try:
        # Buscar ocupacion
        r_occ = supabase.table("esco_ocupaciones").select("*").ilike("nombre", f"%{nombre}%").limit(5).execute()
        if not r_occ.data:
            raise HTTPException(status_code=404, detail=f"Ocupacion '{nombre}' no encontrada en ESCO")

        resultados = []
        for occ in r_occ.data:
            occ_nombre = occ.get("nombre")
            # Buscar habilidades de esa ocupacion
            r_skills = supabase.table("esco_ocupacion_habilidades").select("*").eq("ocupacion_nombre", occ_nombre).execute()
            esenciales = [s for s in r_skills.data if s.get("tipo_relacion") == "essential"]
            opcionales = [s for s in r_skills.data if s.get("tipo_relacion") == "optional"]

            # Indice de verdor
            verde = None
            try:
                r_verde = supabase.table("esco_green_share_ocupaciones").select("*").ilike("nombre", f"%{occ_nombre}%").limit(1).execute()
                if r_verde.data:
                    verde = r_verde.data[0].get("indice_verdor")
            except Exception:
                pass

            # Salario real de GEIH vinculado a la ocupación por su código ISCO.
            # Antes la query no filtraba por ocupación y devolvía siempre la fila
            # con mayor empleo_total (mismo salario para todas las ocupaciones).
            # Ahora usamos el codigo_isco de ESCO (campo oficio_c8 en GEIH).
            salario = None
            try:
                isco = occ.get("codigo_isco")
                if isco:
                    r_sal = supabase.table("geih_salario_ocupacion").select(
                        "salario_promedio,salario_mediano,empleo_total"
                    ).eq("oficio_c8", int(isco)).limit(1).execute()
                    if r_sal.data:
                        salario = {
                            "promedio": r_sal.data[0].get("salario_promedio"),
                            "mediano": r_sal.data[0].get("salario_mediano"),
                            "empleo_total": r_sal.data[0].get("empleo_total"),
                        }
            except Exception:
                pass

            resultados.append({
                "ocupacion": occ_nombre,
                "codigo_isco": occ.get("codigo_isco"),
                "codigo_nace": occ.get("codigo_nace"),
                "definicion": occ.get("definicion"),
                "habilidades_esenciales": [
                    {"nombre": s.get("habilidad_nombre"), "tipo": s.get("tipo_habilidad")}
                    for s in esenciales
                ],
                "habilidades_opcionales": [
                    {"nombre": s.get("habilidad_nombre"), "tipo": s.get("tipo_habilidad")}
                    for s in opcionales
                ],
                "indice_verdor": verde,
                "salario_mercado": salario,
            })

        return {"resultados": resultados, "total": len(resultados)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/esco/skills-gap")
async def get_skills_gap_esco(habilidades_usuario: list[str], ocupacion_objetivo: str):
    """Calcula el gap de habilidades entre las del usuario y las requeridas por una ocupacion ESCO."""
    try:
        # Buscar ocupacion
        r_occ = supabase.table("esco_ocupaciones").select("*").ilike("nombre", f"%{ocupacion_objetivo}%").limit(1).execute()
        if not r_occ.data:
            raise HTTPException(status_code=404, detail=f"Ocupacion '{ocupacion_objetivo}' no encontrada")

        occ_nombre = r_occ.data[0].get("nombre")
        # Habilidades requeridas
        r_skills = supabase.table("esco_ocupacion_habilidades").select("*").eq("ocupacion_nombre", occ_nombre).execute()
        requeridas = {s.get("habilidad_nombre").lower() for s in r_skills.data if s.get("habilidad_nombre")}
        esenciales = {s.get("habilidad_nombre").lower() for s in r_skills.data if s.get("tipo_relacion") == "essential" and s.get("habilidad_nombre")}

        # Habilidades del usuario (normalizadas)
        usuario_set = {h.lower().strip() for h in habilidades_usuario}

        # Calcular gap
        tiene = requeridas & usuario_set
        falta = requeridas - usuario_set
        falta_esenciales = esenciales - usuario_set

        match_score = round(len(tiene) / len(requeridas) * 100) if requeridas else 0

        return {
            "ocupacion": occ_nombre,
            "match_score": match_score,
            "habilidades_tiene": sorted(list(tiene)),
            "habilidades_faltan": sorted(list(falta)),
            "habilidades_esenciales_faltan": sorted(list(falta_esenciales)),
            "total_requeridas": len(requeridas),
            "total_tiene": len(tiene),
            "total_faltan": len(falta),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ole/ingresos-programa/{programa}")
async def get_ingresos_programa_ole(programa: str):
    """Distribucion de ingresos por programa academico (OLE-IBC, 2001-2022)."""
    try:
        r = supabase.table("ole_ingresos_por_programa").select("*").ilike("programa", f"%{programa}%").order("graduados", desc=True).limit(20).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Programa '{programa}' no encontrado en OLE")

        # Agrupar por rango de ingreso
        rangos = {}
        for row in r.data:
            rango = row.get("rango_ingreso")
            if rango not in rangos:
                rangos[rango] = {"graduados": 0, "porcentaje": 0}
            rangos[rango]["graduados"] += int(row.get("graduados") or 0)
            rangos[rango]["porcentaje"] += float(row.get("porcentaje") or 0)

        # Rango modal (el de mas graduados)
        rango_modal = max(rangos.items(), key=lambda x: x[1]["graduados"])[0] if rangos else None

        return {
            "programa": programa,
            "total_graduados": sum(v["graduados"] for v in rangos.values()),
            "rango_modal": rango_modal,
            "distribucion_ingresos": [
                {"rango": k, "graduados": v["graduados"], "porcentaje": round(v["porcentaje"], 1)}
                for k, v in sorted(rangos.items(), key=lambda x: -x[1]["graduados"])
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
