"""
Router Match Inteligente para ALBA Offline.
Usa Gemma 4 E4B local para analisis de CV vs vacante.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_json, call_llm_text
from app.db.sqlite_db import query_sql
from typing import Any

router = APIRouter(prefix="/api/match", tags=["match"])


class CVVacanteRequest(BaseModel):
    cv_text: str
    vacante_text: str


@router.post("/cv-vacante")
async def match_cv_vacante(req: CVVacanteRequest):
    system = (
        "Eres un reclutador experto en Colombia. Analiza un CV/perfil y una vacante laboral. "
        "Devuelve UNICAMENTE un JSON valido con esta estructura:\n"
        "{\n"
        '  "score_match": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas": [{"requisito": string, "peso": number, "como_cubrir": string, "recursos": [{"tipo": string, "nombre": string}]}],\n'
        '  "recomendacion": string\n'
        "}\n"
        "El score_match debe ser 0-100. Los pesos de brechas deben sumar (100 - score_match)."
    )
    user = f"CV:\n{req.cv_text}\n\nVacante:\n{req.vacante_text}"
    try:
        result = call_llm_json(system, user, temperature=0.3)
        if result is None or "error" in result:
            return {"error": "IA no disponible. Instala llama-cpp-python.", "score_match": 0}
        return result
    except Exception as e:
        return {"error": str(e), "score_match": 0}


class PensumRequest(BaseModel):
    pensum: str
    mercado: str = ""


@router.post("/pensum-mercado")
async def match_pensum_mercado(req: PensumRequest):
    system = (
        "Eres un experto en curriculo academico en Colombia. Compara un pensum universitario "
        "con la demanda del mercado laboral. Devuelve JSON con:\n"
        '{"alineacion": number, "fortalezas": [string], "alertas": [string], '
        '"recomendaciones": [string]}\n'
        "alineacion es 0-100."
    )
    user = f"Pensum:\n{req.pensum}\n\nMercado:\n{req.mercado}"
    try:
        result = call_llm_json(system, user, temperature=0.3)
        return result
    except Exception as e:
        return {"error": str(e)}