"""
Router Match Inteligente para ALBA Offline.
Usa Qwen3.5-2B local para analisis de CV vs vacante y pensum vs mercado.
Devuelve las mismas estructuras que espera el frontend (recomendacion_general,
brechas, brechas_mercado, score_alineacion, etc.) y blinda la forma para que
un JSON parcial del LLM no rompa la pagina (Match no tiene ErrorBoundary).
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_json

router = APIRouter(prefix="/api/match", tags=["match"])


def _as_list(v):
    return v if isinstance(v, list) else []


def _as_str(v):
    return v if isinstance(v, str) else ""


def _as_num(v, default=0):
    try:
        f = float(v)
        return f if f == f else default  # filtrar NaN
    except Exception:
        return default


def _safe_json(system: str, user: str, temperature: float = 0.3, max_tokens: int = 700):
    try:
        result = call_llm_json(system, user, temperature=temperature, max_tokens=max_tokens)
        if result is None or not isinstance(result, dict) or "error" in result:
            return None
        return result
    except Exception:
        return None


class CvVacanteRequest(BaseModel):
    cv: str
    vacante: str


@router.post("/cv-vacante")
async def match_cv_vacante(req: CvVacanteRequest):
    system = (
        "Eres un reclutador experto en Colombia. Analiza un CV/perfil y una vacante laboral. "
        "Devuelve UNICAMENTE un JSON valido con EXACTAMENTE esta estructura:\n"
        "{\n"
        '  "score_match": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas": [{"requisito": string, "peso": number, "como_cubrir": string, '
        '"recursos": [{"tipo": string, "nombre": string}]}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "score_match es 0-100. Los pesos de las brechas deben sumar (100 - score_match). "
        "recursos[].tipo debe ser uno de: SENA, online, certificacion, libre."
    )
    user = f"CV:\n{req.cv}\n\nVacante:\n{req.vacante}"
    result = _safe_json(system, user, temperature=0.3)
    if result is None:
        return {
            "score_match": 0, "interpretacion": "IA no disponible en este momento.",
            "fortalezas": [], "brechas": [], "recomendacion_general": "",
        }
    brechas = []
    for b in _as_list(result.get("brechas")):
        if not isinstance(b, dict):
            continue
        brechas.append({
            "requisito": _as_str(b.get("requisito")),
            "peso": _as_num(b.get("peso")),
            "como_cubrir": _as_str(b.get("como_cubrir")),
            "recursos": _as_list(b.get("recursos")),
        })
    return {
        "score_match": _as_num(result.get("score_match")),
        "interpretacion": _as_str(result.get("interpretacion")),
        "fortalezas": _as_list(result.get("fortalezas")),
        "brechas": brechas,
        "recomendacion_general": _as_str(result.get("recomendacion_general") or result.get("recomendacion")),
    }


class PensumRequest(BaseModel):
    pensum: str


@router.post("/pensum")
async def match_pensum(req: PensumRequest):
    system = (
        "Eres un experto en curriculo academico en Colombia. Compara un pensum universitario "
        "con la demanda del mercado laboral. Devuelve UNICAMENTE un JSON valido con EXACTAMENTE esta estructura:\n"
        "{\n"
        '  "score_alineacion": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas_mercado": [{"area": string, "nivel_importancia": "alta"|"media"|"baja", "sugerencia": string}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "score_alineacion es 0-100."
    )
    user = f"Pensum:\n{req.pensum}"
    result = _safe_json(system, user, temperature=0.3)
    if result is None:
        return {
            "score_alineacion": 0, "interpretacion": "IA no disponible en este momento.",
            "fortalezas": [], "brechas_mercado": [], "recomendacion_general": "",
        }
    brechas_mercado = []
    for b in _as_list(result.get("brechas_mercado")):
        if not isinstance(b, dict):
            continue
        nivel = b.get("nivel_importancia")
        if nivel not in ("alta", "media", "baja"):
            nivel = "media"
        brechas_mercado.append({
            "area": _as_str(b.get("area")),
            "nivel_importancia": nivel,
            "sugerencia": _as_str(b.get("sugerencia")),
        })
    return {
        "score_alineacion": _as_num(result.get("score_alineacion")),
        "interpretacion": _as_str(result.get("interpretacion")),
        "fortalezas": _as_list(result.get("fortalezas")),
        "brechas_mercado": brechas_mercado,
        "recomendacion_general": _as_str(result.get("recomendacion_general") or result.get("recomendacion")),
    }
