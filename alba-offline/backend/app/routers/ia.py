"""
Router IA para ALBA Offline - Analizar con IA en widgets.
Usa Gemma 4 E4B local.
"""
import json
from fastapi import APIRouter
from typing import Any
from pydantic import BaseModel, Field
from app.services.llm_local import call_llm_text

router = APIRouter(prefix="/api/ia", tags=["ia"])


class WidgetRequest(BaseModel):
    dashboard: str = ""
    widget_title: str = ""
    widget_type: str = ""
    filters: dict = {}
    data: Any = None
    question: str = ""


@router.post("/analizar-widget")
async def analizar_widget(req: WidgetRequest):
    system = (
        f"Eres un analista de datos experto en el mercado laboral de Colombia. "
        f"El usuario esta viendo el widget '{req.widget_title}' en el dashboard '{req.dashboard}'. "
        f"Tipo de widget: {req.widget_type}. "
        f"Responde la pregunta del usuario basandote en los datos proporcionados. "
        f"Responde en espanol, de forma clara y concisa (maximo 200 palabras)."
    )
    data_str = json.dumps(req.data, ensure_ascii=False, default=str) if req.data else "Sin datos"
    filters_str = json.dumps(req.filters, ensure_ascii=False) if req.filters else ""
    user = (
        f"Filtros: {filters_str}\n"
        f"Datos del widget:\n{data_str[:3000]}\n\n"
        f"Pregunta: {req.question}"
    )
    try:
        result = call_llm_text(system, user, temperature=0.4, max_tokens=500)
        if result is None:
            return {"error": "IA no disponible", "respuesta": "La IA local no esta disponible. Instala llama-cpp-python para activar el analisis con IA.", "widget_title": req.widget_title, "dashboard": req.dashboard}
        return {
            "respuesta": result,
            "widget_title": req.widget_title,
            "dashboard": req.dashboard,
        }
    except Exception as e:
        return {"error": str(e), "respuesta": "No se pudo analizar en este momento."}


class PreguntaRequest(BaseModel):
    question: str = ""


@router.post("/pregunta-general")
async def pregunta_general(req: PreguntaRequest):
    system = (
        "Eres ALBA, una plataforma de inteligencia laboral de Colombia. "
        "Responde preguntas sobre empleo, educacion, salarios y mercado laboral. "
        "Responde en espanol, de forma clara y concisa."
    )
    try:
        result = call_llm_text(system, req.question, temperature=0.4, max_tokens=500)
        if result is None:
            return {"respuesta": "La IA local no esta disponible. Instala llama-cpp-python para activar esta funcion."}
        return {"respuesta": result}
    except Exception as e:
        return {"error": str(e), "respuesta": "No se pudo procesar la pregunta."}