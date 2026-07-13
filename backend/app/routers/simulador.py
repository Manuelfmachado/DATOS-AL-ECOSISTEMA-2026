"""
Router del Simulador IA (Función #2).
Permite proyectar escenarios de mercado laboral y generar recomendaciones
accionables para gobiernos, universidades y el SENA.

El simulador no requiere series de tiempo largas. Usa variaciones históricas
disponibles (SPE 2019-2020, RUES anual) y reglas de negocio para construir
proyecciones bajo escenarios optimista, base y pesimista.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase import supabase
import pandas as pd
import numpy as np

router = APIRouter(prefix="/api/simulador", tags=["simulador"])


SCENARIOS = {
    "optimista": {"empleo": 1.035, "empresas": 1.12, "formacion": 1.15, "label": "Optimista"},
    "base": {"empleo": 1.015, "empresas": 1.05, "formacion": 1.05, "label": "Base"},
    "pesimista": {"empleo": 0.985, "empresas": 0.95, "formacion": 0.98, "label": "Pesimista"},
}


def _norm(text: str) -> str:
    return text.upper().replace("Á", "A").replace("É", "E").replace("Í", "I").replace("Ó", "O").replace("Ú", "U").replace("Ñ", "N").strip()


def _clean_num(v):
    if v is None:
        return 0
    try:
        f = float(v)
        if pd.isna(f) or abs(f) == float('inf'):
            return 0
        return f
    except Exception:
        return 0


class ProyectarRequest(BaseModel):
    actor: str = "gobierno"  # gobierno | universidad | sena
    foco: str = "empleo"     # empleo | empresas | educacion
    departamento: str = "BOGOTA"
    carrera: str = ""
    sector: str = ""
    horizonte: int = 3       # años
    escenario: str = "base"


class DepartamentoRequest(BaseModel):
    departamento: str = "BOGOTA"
    horizonte: int = 3
    escenario: str = "base"


class RecomendacionesRequest(BaseModel):
    actor: str = "gobierno"
    departamento: str = "BOGOTA"
    sector_prioritario: str = ""
    carrera_prioritaria: str = ""


def _get_scenario_factor(escenario: str, key: str) -> float:
    return SCENARIOS.get(escenario, SCENARIOS["base"]).get(key, 1.0)


def _proyectar_serie(valor_base: float, tasa_anual: float, horizonte: int) -> list[float]:
    """Genera proyección año a año compuesta."""
    return [round(valor_base * (tasa_anual ** (i + 1)), 2) for i in range(horizonte)]


@router.get("/escenarios")
async def list_escenarios():
    """Devuelve los escenarios disponibles."""
    return {"escenarios": SCENARIOS}


@router.post("/proyectar")
async def proyectar(req: ProyectarRequest):
    """Proyecta escenarios por carrera, sector o departamento."""
    try:
        depto_norm = _norm(req.departamento)
        horizonte = min(max(req.horizonte, 1), 5)
        factor_empleo = _get_scenario_factor(req.escenario, "empleo")
        factor_empresas = _get_scenario_factor(req.escenario, "empresas")
        factor_formacion = _get_scenario_factor(req.escenario, "formacion")

        resultado = {
            "actor": req.actor,
            "foco": req.foco,
            "departamento": req.departamento,
            "escenario": req.escenario,
            "horizonte_anos": horizonte,
            "metricas": [],
            "series": {},
            "recomendaciones": [],
        }

        if req.foco == "empleo":
            # Demanda laboral: SPE
            spe = supabase.table("spe_ape_inscritos_ocupacion").select("*")
            if req.carrera:
                spe = spe.ilike("ocupacion", f"%{req.carrera[:30]}%")
            spe = spe.order("inscritos_2020", desc=True).limit(10).execute()

            base = sum(_clean_num(s.get("inscritos_2020")) for s in spe.data) or 1
            variacion_historica = []
            for s in spe.data:
                v2019 = _clean_num(s.get("inscritos_2019"))
                v2020 = _clean_num(s.get("inscritos_2020"))
                if v2019 > 0:
                    variacion_historica.append((v2020 - v2019) / v2019)
            tasa_base = 1.0 + (np.mean(variacion_historica) if variacion_historica else 0.0)
            tasa_ajustada = tasa_base * factor_empleo

            resultado["series"]["demanda_laboral"] = _proyectar_serie(base, tasa_ajustada, horizonte)
            resultado["metricas"] = [
                {"label": "Demanda base (2020)", "valor": int(base)},
                {"label": "Tasa anual proyectada", "valor": f"{(tasa_ajustada - 1) * 100:.1f}%"},
                {"label": "Demanda proyectada (año final)", "valor": int(resultado["series"]["demanda_laboral"][-1])},
            ]

            # Recomendaciones
            if tasa_ajustada > 1.05:
                resultado["recomendaciones"].append("Alta demanda proyectada: ampliar cursos SENA y formación técnica en esta área.")
            elif tasa_ajustada < 0.98:
                resultado["recomendaciones"].append("Demanda estancada o decreciente: evitar saturar la oferta de programas en esta ocupación.")
            resultado["recomendaciones"].append("Priorizar alianzas con empresas del sector para inserción laboral.")

        elif req.foco == "empresas":
            # Dinamismo empresarial: RUES
            rues = supabase.table("rues_empresas_nuevas").select("*").limit(1000).execute()
            df_rues = pd.DataFrame(rues.data or [])
            base = 0
            tasa_base = 1.05
            if not df_rues.empty and "anio_matricula" in df_rues.columns:
                df_rues["empresas_nuevas"] = pd.to_numeric(df_rues["empresas_nuevas"], errors="coerce").fillna(0)
                df_rues["anio_matricula"] = pd.to_numeric(df_rues["anio_matricula"], errors="coerce")
                df_rues = df_rues[(df_rues["anio_matricula"] >= 2020) & (df_rues["anio_matricula"] <= 2025)]
                anual = df_rues.groupby("anio_matricula")["empresas_nuevas"].sum().sort_index()
                if len(anual) >= 2:
                    base = float(anual.iloc[-1])
                    # CAGR entre primer y ultimo año valido
                    anos = len(anual) - 1
                    tasa_base = float((anual.iloc[-1] / max(anual.iloc[0], 1)) ** (1 / anos))
                elif len(anual) == 1:
                    base = float(anual.iloc[-1])
            tasa_ajustada = tasa_base * factor_empresas
            base = base or 100000

            resultado["series"]["empresas_nuevas"] = _proyectar_serie(base, tasa_ajustada, horizonte)
            resultado["metricas"] = [
                {"label": "Empresas nuevas base", "valor": int(base)},
                {"label": "Tasa anual proyectada", "valor": f"{(tasa_ajustada - 1) * 100:.1f}%"},
                {"label": "Empresas proyectadas (año final)", "valor": int(resultado["series"]["empresas_nuevas"][-1])},
            ]
            if tasa_ajustada > 1.05:
                resultado["recomendaciones"].append("Dinamismo empresarial positivo: simplificar trámites de formalización y ofrecer incentivos fiscales.")
            else:
                resultado["recomendaciones"].append("Baja creación de empresas: fortalecer líneas de crédito y asesoría a emprendedores.")

        else:  # educacion
            snies = supabase.table("snies_programas_matriculados").select("*").ilike("departamento", f"%{depto_norm}%")
            if req.carrera:
                snies = snies.ilike("programa", f"%{req.carrera[:30]}%")
            snies = snies.limit(200).execute()

            base = sum(_clean_num(s.get("matriculados")) for s in snies.data) or 1
            tasa_ajustada = factor_formacion
            resultado["series"]["matriculados"] = _proyectar_serie(base, tasa_ajustada, horizonte)
            resultado["metricas"] = [
                {"label": "Matriculados base", "valor": int(base)},
                {"label": "Tasa anual proyectada", "valor": f"{(tasa_ajustada - 1) * 100:.1f}%"},
                {"label": "Matriculados proyectados (año final)", "valor": int(resultado["series"]["matriculados"][-1])},
            ]
            if tasa_ajustada > 1.05:
                resultado["recomendaciones"].append("Crecimiento de matriculados proyectado: verificar que la demanda laboral absorba esa oferta.")
            else:
                resultado["recomendaciones"].append("Oferta educativa estancada: evaluar si hay brechas de formación no cubiertas.")

        return resultado

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/departamento")
async def simular_departamento(req: DepartamentoRequest):
    """Simula indicadores macro de un departamento a futuro."""
    try:
        depto_norm = _norm(req.departamento)
        horizonte = min(max(req.horizonte, 1), 5)
        factor_empleo = _get_scenario_factor(req.escenario, "empleo")
        factor_empresas = _get_scenario_factor(req.escenario, "empresas")

        # GEIH estado actual
        geih = supabase.table("geih_resumen_departamento").select("*").ilike("departamento", f"%{depto_norm}%").limit(1).execute()
        geih_des = supabase.table("geih_desempleo_departamento").select("*").ilike("departamento", f"%{depto_norm}%").limit(1).execute()

        ocupados_base = _clean_num(geih.data[0].get("ocupados")) if geih.data else 0
        no_ocupados_base = _clean_num(geih_des.data[0].get("no_ocupados")) if geih_des.data else 0

        # SPE demanda
        spe = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(10).execute()
        spe_base = sum(_clean_num(s.get("inscritos_2020")) for s in spe.data)
        variaciones = []
        for s in spe.data:
            v2019 = _clean_num(s.get("inscritos_2019"))
            v2020 = _clean_num(s.get("inscritos_2020"))
            if v2019 > 0:
                variaciones.append((v2020 - v2019) / v2019)
        tasa_spe = 1.0 + (np.mean(variaciones) if variaciones else 0.0)

        # RUES
        rues = supabase.table("rues_empresas_nuevas").select("*").limit(1000).execute()
        df_rues = pd.DataFrame(rues.data or [])
        empresas_base = 0
        tasa_empresas = 1.05
        if not df_rues.empty and "anio_matricula" in df_rues.columns:
            df_rues["empresas_nuevas"] = pd.to_numeric(df_rues["empresas_nuevas"], errors="coerce").fillna(0)
            df_rues["anio_matricula"] = pd.to_numeric(df_rues["anio_matricula"], errors="coerce")
            df_rues = df_rues[(df_rues["anio_matricula"] >= 2020) & (df_rues["anio_matricula"] <= 2025)]
            anual = df_rues.groupby("anio_matricula")["empresas_nuevas"].sum().sort_index()
            if len(anual) >= 2:
                empresas_base = float(anual.iloc[-1])
                anos = len(anual) - 1
                tasa_empresas = float((anual.iloc[-1] / max(anual.iloc[0], 1)) ** (1 / anos))
            elif len(anual) == 1:
                empresas_base = float(anual.iloc[-1])
        empresas_base = empresas_base or 100000

        # Proyecciones
        ocupados_proy = _proyectar_serie(ocupados_base, factor_empleo, horizonte)
        no_ocupados_proy = _proyectar_serie(no_ocupados_base, factor_empleo * 0.99, horizonte)
        spe_proy = _proyectar_serie(spe_base, tasa_spe * factor_empleo, horizonte)
        empresas_proy = _proyectar_serie(empresas_base, tasa_empresas * factor_empresas, horizonte)

        anios = [f"{2026 + i}" for i in range(horizonte)]

        return {
            "departamento": req.departamento,
            "escenario": req.escenario,
            "horizonte_anos": horizonte,
            "anios": anios,
            "series": {
                "ocupados": ocupados_proy,
                "no_ocupados": no_ocupados_proy,
                "demanda_spe": spe_proy,
                "empresas_nuevas": empresas_proy,
            },
            "metricas": [
                {"label": "Ocupados base", "valor": int(ocupados_base)},
                {"label": "No ocupados base", "valor": int(no_ocupados_base)},
                {"label": "Demanda SPE base", "valor": int(spe_base)},
                {"label": "Empresas nuevas base", "valor": int(empresas_base)},
            ],
            "recomendaciones_macro": _generar_recomendaciones_macro(
                req.escenario, ocupados_base, no_ocupados_base, tasa_spe, tasa_empresas
            ),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _generar_recomendaciones_macro(escenario: str, ocupados: float, no_ocupados: float, tasa_spe: float, tasa_empresas: float) -> list[str]:
    recs = []
    if escenario == "optimista":
        recs.append("Aprovechar el ciclo expansivo para atraer inversión en sectores de alto crecimiento.")
    elif escenario == "pesimista":
        recs.append("Activar programas de protección al empleo y subsidios transitorios a sectores afectados.")
    else:
        recs.append("Mantener políticas activas de empleo y formación continua.")

    if tasa_spe > 1.03:
        recs.append("Demanda laboral creciente: acelerar oferta de cursos cortos y técnicos en áreas críticas.")
    elif tasa_spe < 0.98:
        recs.append("Demanda laboral débil: reorientar programas hacia sectores con mayor dinamismo.")

    if tasa_empresas > 1.05:
        recs.append("Alto dinamismo empresarial: fortalecer la articulación universidad-empresa- Estado.")
    else:
        recs.append("Baja creación de empresas: simplificar trámites y ampliar financiación a emprendedores.")

    return recs


@router.post("/recomendaciones")
async def generar_recomendaciones(req: RecomendacionesRequest):
    """Genera recomendaciones específicas según actor y territorio."""
    try:
        depto_norm = _norm(req.departamento)
        recs = []

        # Datos de contexto
        spe = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(5).execute()
        top_ocupaciones = [s.get("ocupacion") for s in spe.data]

        sena = supabase.table("sena_programas_activos").select("*").ilike("departamento", f"%{depto_norm}%").limit(5).execute()
        cursos_sena = [s.get("programa") for s in sena.data]

        rues = supabase.table("rues_empresas_nuevas").select("*").limit(50).execute()
        df_rues = pd.DataFrame(rues.data or [])
        top_ciiu = []
        if not df_rues.empty and "ciiu2" in df_rues.columns:
            df_rues["empresas_nuevas"] = pd.to_numeric(df_rues["empresas_nuevas"], errors="coerce").fillna(0)
            top_ciiu = df_rues.groupby("ciiu2")["empresas_nuevas"].sum().sort_values(ascending=False).head(3).index.tolist()

        if req.actor == "gobierno":
            recs.append(f"En {req.departamento}, las ocupaciones con mayor demanda son: {', '.join(top_ocupaciones[:3])}. Orientar la inversión social y los convenios de empleo hacia ellas.")
            recs.append("Simplificar trámites de formalización para los sectores CIIU2 con más nuevas empresas.")
            recs.append("Crear bolsas de empleo locales articuladas con SPE SENA y RUES.")
            if req.sector_prioritario:
                recs.append(f"Incentivar la inversión en el sector {req.sector_prioritario} mediante alivios tributarios o zonas de desarrollo.")

        elif req.actor == "universidad":
            recs.append("Revisar la oferta de programas con alta matrícula y baja demanda laboral observada en PILA/SPE.")
            recs.append("Potenciar prácticas empresariales y pasantías con sectores de crecimiento.")
            recs.append("Diseñar microcredenciales y especializaciones en áreas de demanda creciente.")
            if req.carrera_prioritaria:
                recs.append(f"Evaluar la pertinencia del programa {req.carrera_prioritaria}: ¿su demanda justifica más cupos o una especialización?")

        else:  # sena
            recs.append(f"Ampliar cursos técnicos en: {', '.join(top_ocupaciones[:3])}.")
            recs.append("Mapear cursos activos vs demanda SPE para cerrar brechas regionales.")
            recs.append("Fortalecer certificaciones en competencias digitales y verdes.")

        return {
            "actor": req.actor,
            "departamento": req.departamento,
            "recomendaciones": recs,
            "contexto": {
                "top_demanda_spe": top_ocupaciones,
                "cursos_sena_disponibles": cursos_sena,
                "top_ciiu_rues": top_ciiu,
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoints legacy mantenidos para compatibilidad
class SimuladorRequest(BaseModel):
    carrera: str
    departamento: str = "BOGOTÁ"
    semestre: int | None = None
    promedio: float | None = None


@router.post("/proyectar-legacy")
async def proyectar_empleabilidad_legacy(req: SimuladorRequest):
    """Endpoint legacy de proyección por carrera."""
    try:
        res = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{req.carrera}%").eq("departamento", req.departamento.upper()).execute()
        programas = res.data
        total_matriculados = sum(p.get("matriculados", 0) or 0 for p in programas)

        pila = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(10).execute()
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{req.carrera}%").limit(10).execute()

        cotizantes_total = sum(p.get("total_cotizantes", 0) or 0 for p in pila.data)
        if total_matriculados > 0 and cotizantes_total > 0:
            saturacion = total_matriculados / (cotizantes_total / 100)
        else:
            saturacion = None

        if saturacion is not None:
            status = "saturado" if saturacion > 5 else "equilibrado" if saturacion > 2 else "demanda_insatisfecha"
        else:
            status = "datos_insuficientes"

        return {
            "carrera": req.carrera,
            "departamento": req.departamento,
            "programas_encontrados": len(programas),
            "total_matriculados": total_matriculados,
            "cotizantes_formales_top_sectores": cotizantes_total,
            "indice_saturacion": round(saturacion, 2) if saturacion else None,
            "status_sector": status,
            "cursos_sena_recomendados": len(sena.data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/saturacion/{carrera}")
async def get_saturacion_carrera(carrera: str):
    """Alerta de saturación de carrera a nivel nacional."""
    try:
        res = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{carrera}%").execute()
        programas = res.data

        if not programas:
            raise HTTPException(status_code=404, detail=f"No se encontraron programas para {carrera}")

        total_matriculados = sum(p.get("matriculados", 0) or 0 for p in programas)
        df = pd.DataFrame(programas)
        por_departamento = df.groupby("departamento")["matriculados"].sum().reset_index().sort_values("matriculados", ascending=False)

        return {
            "carrera": carrera,
            "total_programas": len(programas),
            "total_matriculados_nacional": total_matriculados,
            "por_departamento": por_departamento.to_dict("records")[:10],
            "alerta": "Saturación alta" if total_matriculados > 50000 else "Demanda moderada" if total_matriculados > 10000 else "Baja oferta",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
