"""
Router Simulacion para ALBA Offline.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_json
from app.db.sqlite_db import query_sql

router = APIRouter(prefix="/api/simulacion", tags=["simulacion"])


class TrayectoriaRequest(BaseModel):
    carrera_actual: str = ""
    carrera_destino: str = ""
    departamento: str = ""


@router.post("/trayectoria")
async def trayectoria(req: TrayectoriaRequest):
    system = (
        "Eres un orientador vocacional en Colombia. Simula el cambio de carrera. "
        "Devuelve JSON con:\n"
        '{"factibilidad": number, "pasos": [string], "riesgos": [string], '
        '"tiempo_estimado": string, "salario_estimado": string}\n'
        "factibilidad es 0-100."
    )
    user = (
        f"Carrera actual: {req.carrera_actual}\n"
        f"Carrera destino: {req.carrera_destino}\n"
        f"Departamento: {req.departamento}"
    )
    try:
        result = call_llm_json(system, user, temperature=0.4)
        if result is None or "error" in result:
            return {"error": "IA no disponible. Instala llama-cpp-python."}
        return result
    except Exception as e:
        return {"error": str(e)}


@router.get("/demanda-sectorial")
async def demanda_sectorial():
    rows = query_sql(
        "SELECT * FROM geih_empleo_sector_nacional LIMIT 20"
    )
    return {"sectores": rows}