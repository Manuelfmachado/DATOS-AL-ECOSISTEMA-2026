"""
Router Emprende IA para ALBA Offline.
Usa Qwen3.5-2B local para evaluar ideas de negocio.
Enriquece el prompt con datos reales de mercado (GEIH + RUES + PILA desde SQLite)
igual que la version online, para que el LLM base su analisis en cifras concretas.
Devuelve la estructura IdeaResultado que espera el frontend y blinda la forma
para que un JSON parcial del LLM no rompa la pagina.
"""
import unicodedata
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_json
from app.db.sqlite_db import query_sql, query_all
from app.data.ciiu_nombres import CIIU_NOMBRES

router = APIRouter(prefix="/api/emprende", tags=["emprende"])


def _as_list(v):
    return v if isinstance(v, list) else []


def _as_str(v):
    return v if isinstance(v, str) else ""


def _as_num(v, default=0):
    try:
        f = float(v)
        return f if f == f else default
    except Exception:
        return default


def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _norm_depto(name: str) -> str:
    s = _norm(name)
    if "BOGOTA" in s:
        return "BOGOTA"
    if "SAN ANDRES" in s or "ARCHIPIELAGO" in s:
        return "ARCHIPIELAGO DE SAN ANDRES"
    if s == "GUAJIRA":
        return "LA GUAJIRA"
    if s == "NARINIO":
        return "NARINO"
    return s


def _contexto_mercado(departamento: str, sector: str | None = None) -> str:
    """Construye un texto con indicadores reales de mercado desde SQLite
    para enriquecer el prompt del LLM (igual que la version online con Supabase)."""
    depto_norm = _norm_depto(departamento)

    # GEIH: ocupados + desempleo del departamento
    ocu_rows = [r for r in (query_sql("SELECT * FROM geih_resumen_departamento") or [])
                if _norm_depto(r.get("departamento", "")) == depto_norm]
    des_rows = [r for r in (query_sql("SELECT * FROM geih_desempleo_departamento") or [])
                if _norm_depto(r.get("departamento", "")) == depto_norm]
    ocupados = sum(r.get("ocupados", 0) or 0 for r in ocu_rows)
    no_ocupados = sum(r.get("no_ocupados", 0) or 0 for r in des_rows)
    total_pea = ocupados + no_ocupados
    tasa_desempleo = round((no_ocupados / total_pea * 100), 2) if total_pea > 0 else 0
    ingreso_prom = round(sum((r.get("ingreso_promedio", 0) or 0) * (r.get("ocupados", 0) or 0) for r in ocu_rows) / max(ocupados, 1)) if ocupados else 0

    # RUES: empresas activas y nuevas por sector
    rues_rows = query_sql("SELECT ciiu2, empresas_activas FROM rues_top_sectores_nacional") or []
    sector_norm = _norm(sector) if sector else ""
    if sector_norm:
        rues_filtered = [r for r in rues_rows if sector_norm in _norm(str(r.get("ciiu2", ""))) or
                         sector_norm in _norm(CIIU_NOMBRES.get(str(r.get("ciiu2", "")), ""))]
    else:
        rues_filtered = rues_rows
    empresas_activas = sum(r.get("empresas_activas", 0) or 0 for r in rues_filtered)

    # RUES: empresas nuevas recientes (ultimos 3 anos)
    rues_new = query_sql("SELECT ciiu2, empresas_nuevas FROM rues_empresas_nuevas") or []
    empresas_nuevas = sum(r.get("empresas_nuevas", 0) or 0 for r in rues_new)

    # PILA: cotizantes formales
    pila_rows = query_sql("SELECT total_cotizantes FROM pila_cotizantes") or []
    cotizantes = sum(r.get("total_cotizantes", 0) or 0 for r in pila_rows)

    # Sectores emergentes (top 5)
    emergentes = (query_sql("SELECT ciiu2, empresas_activas FROM rues_top_sectores_nacional ORDER BY empresas_activas DESC LIMIT 5") or [])
    emergentes_txt = ", ".join(
        f"{CIIU_NOMBRES.get(str(r.get('ciiu2', '')), 'CIIU ' + str(r.get('ciiu2', '')))} ({r.get('empresas_activas', 0)} empresas)"
        for r in emergentes
    )

    return (
        f"DATOS REALES DEL MERCADO PARA TU ANALISIS:\n"
        f"- Departamento: {departamento}\n"
        f"- Tasa de desempleo: {tasa_desempleo}%\n"
        f"- Poblacion ocupada: {ocupados:,}\n"
        f"- Ingreso promedio mensual: ${ingreso_prom:,} COP\n"
        f"- Empresas activas en sector relacionado: {empresas_activas:,}\n"
        f"- Empresas nuevas recientes (nacional): {empresas_nuevas:,}\n"
        f"- Cotizantes formales (PILA, nacional): {cotizantes:,}\n"
        f"- Sectores emergentes: {emergentes_txt}\n\n"
        f"Usa estos datos para fundamentar tu evalucion. Menciona programas colombianos reales: "
        f"Fondo Emprender del SENA, iNNpulsa, Camara de Comercio local, cursos SENA."
    )


class IdeaRequest(BaseModel):
    idea: str
    departamento: str = ""
    inversion: str = ""


@router.post("/evaluar-idea")
async def evaluar_idea(req: IdeaRequest):
    # Extraer palabras clave del sector de la idea
    palabras_clave = [p for p in req.idea.split() if len(p) > 4][:3]
    sector = " ".join(palabras_clave)

    contexto_texto = _contexto_mercado(req.departamento, sector)

    system = (
        "Eres un consultor de emprendimiento experto en Colombia. Evalua una idea de negocio "
        "basandote en los datos reales del mercado que se te proporcionan. "
        "Devuelve UNICAMENTE un JSON valido con EXACTAMENTE esta estructura:\n"
        "{\n"
        '  "score_potencial": number,\n'
        '  "veredicto": string,\n'
        '  "razones_a_favor": [string],\n'
        '  "riesgos": [string],\n'
        '  "pasos": [string],\n'
        '  "fuentes_recursos": [string],\n'
        '  "oportunidad_nicho": string\n'
        "}\n"
        "score_potencial es 0-100 (indice de potencial basado en crecimiento del sector, "
        "competencia, demanda laboral e incentivos). "
        "Usa los datos del mercado para fundamentar cada razon, riesgo y paso. "
        "Menciona programas colombianos especificos: Fondo Emprender del SENA, iNNpulsa, "
        "Camara de Comercio local, cursos SENA. "
        "Las razones_a_favor, riesgos, pasos y fuentes_recursos deben ser listas de 4-6 elementos cada una."
    )
    user = (
        f"{contexto_texto}\n\n"
        f"IDEA A EVALUAR:\n"
        f"Idea: {req.idea}\n"
        f"Departamento: {req.departamento}\n"
        f"Inversion: {req.inversion}"
    )
    try:
        result = call_llm_json(system, user, temperature=0.4, max_tokens=1200)
        if result is None or not isinstance(result, dict) or "error" in result:
            result = {}
    except Exception:
        result = {}
    return {
        "score_potencial": _as_num(result.get("score_potencial")),
        "veredicto": _as_str(result.get("veredicto")) or "IA no disponible en este momento.",
        "razones_a_favor": _as_list(result.get("razones_a_favor")),
        "riesgos": _as_list(result.get("riesgos")),
        "pasos": _as_list(result.get("pasos")),
        "fuentes_recursos": _as_list(result.get("fuentes_recursos")),
        "oportunidad_nicho": _as_str(result.get("oportunidad_nicho")),
    }


@router.get("/sectores-municipio/{municipio}")
async def sectores_municipio(municipio: str):
    try:
        rows = query_sql(
            "SELECT * FROM rues_empresas_nuevas WHERE ciiu2 LIKE ? LIMIT 20",
            (f"%{municipio}%",),
        )
    except Exception:
        rows = query_all("rues_empresas_nuevas", limit=20)
    return {"municipio": municipio, "sectores": rows}