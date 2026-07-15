"""
Router Emprende IA para ALBA Offline.
Usa Gemma 4 E4B local para evaluar ideas de negocio.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_json
from app.db.sqlite_db import query_sql, query_all

router = APIRouter(prefix="/api/emprende", tags=["emprende"])


class IdeaRequest(BaseModel):
    municipio: str = ""
    sector: str = ""
    inversion: str = ""
    descripcion: str = ""


@router.post("/evaluar-idea")
async def evaluar_idea(req: IdeaRequest):
    system = (
        "Eres un consultor de emprendimiento en Colombia. Evalua una idea de negocio "
        "y devuelve JSON con:\n"
        '{"indice_oportunidad": number, "fortalezas": [string], "riesgos": [string], '
        '"recomendaciones": [string], "competencia": string}\n'
        "indice_oportunidad es 0-100."
    )
    user = (
        f"Municipio: {req.municipio}\nSector: {req.sector}\n"
        f"Inversion: {req.inversion}\nDescripcion: {req.descripcion}"
    )
    try:
        result = call_llm_json(system, user, temperature=0.4)
        return result
    except Exception as e:
        return {"error": str(e), "indice_oportunidad": 0}


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