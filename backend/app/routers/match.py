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
    """Analiza el match entre un CV/perfil y una vacante laboral usando LLM (Gemini + fallback DeepInfra)."""
    try:
        if is_gemini_available():
            return gemini_match_cv_vacante(req.cv, req.vacante)
        return deepinfra_match_cv_vacante(req.cv, req.vacante)
    except Exception as e:
        print(f"[Match] Gemini falló ({e}), usando DeepInfra fallback.")
        try:
            return deepinfra_match_cv_vacante(req.cv, req.vacante)
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
    """Encuentra dónde encaja una persona según su perfil y habilidades."""
    try:
        q = req.perfil[:40]

        # SPE demanda nacional
        spe = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(6).execute()

        # SENA activos relacionados
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{q}%").limit(8).execute()

        # PILA sectores nacionales con demanda
        pila = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(8).execute()

        # Ocupaciones O*NET/ESCO relacionadas con el perfil
        ocupaciones = []
        try:
            onet = supabase.table("onet_occupations").select("*").ilike("title", f"%{q}%").limit(4).execute()
            esco = supabase.table("esco_occupations").select("*").ilike("title", f"%{q}%").limit(4).execute()
            for o in onet.data:
                ocupaciones.append({"id": o.get("onet_code"), "title": o.get("title"), "source": "O*NET"})
            for e in esco.data:
                ocupaciones.append({"id": e.get("concept_uri"), "title": e.get("title"), "source": "ESCO"})
        except Exception:
            pass

        # Score de empleabilidad proxy
        empleabilidad = 50
        if req.habilidades:
            empleabilidad += min(25, len(req.habilidades) * 3)
        empleabilidad += min(20, req.experiencia_anos * 2)
        empleabilidad = min(95, empleabilidad)

        return {
            "perfil": req.perfil,
            "departamento": req.departamento,
            "empleabilidad_score": empleabilidad,
            "ocupaciones_sugeridas": ocupaciones[:6],
            "demanda_spe": [{"ocupacion": s.get("ocupacion"), "inscritos": s.get("inscritos_2020")} for s in spe.data],
            "sectores_demandados": [{"sector": p.get("actividadeconomicadesc"), "cotizantes": p.get("total_cotizantes")} for p in pila.data],
            "cursos_sena_recomendados": [{"programa": s.get("programa"), "area": s.get("area_desempeno")} for s in sena.data[:6]],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/empresa")
async def match_empresa(req: EmpresaRequest):
    """Muestra dónde encontrar talento para una empresa."""
    try:
        depto_norm = _norm(req.departamento)
        sector_q = req.sector[:30]

        # Programas universitarios relacionados con el sector/cargo
        snies = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{sector_q}%").limit(6).execute()

        # Cursos SENA activos
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{sector_q}%").limit(6).execute()

        # SPE demanda nacional filtrada por ocupación
        spe = supabase.table("spe_ape_inscritos_ocupacion").select("*").ilike("ocupacion", f"%{sector_q}%").order("inscritos_2020", desc=True).limit(6).execute()

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
                "postulantes_spe": sum(s.get("inscritos_2020", 0) or 0 for s in spe.data),
            },
            "programas_relacionados": [{"programa": s.get("programa"), "institucion": s.get("institucion"), "matriculados": s.get("matriculados")} for s in snies.data[:6]],
            "cursos_sena_disponibles": [{"programa": s.get("programa"), "area": s.get("area_desempeno")} for s in sena.data[:6]],
            "postulantes_spe": [{"ocupacion": s.get("ocupacion"), "inscritos": s.get("inscritos_2020")} for s in spe.data],
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

            # Salario real de GEIH (buscar por oficio similar)
            salario = None
            try:
                r_sal = supabase.table("geih_salario_ocupacion").select("*").order("empleo_total", desc=True).limit(1).execute()
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
