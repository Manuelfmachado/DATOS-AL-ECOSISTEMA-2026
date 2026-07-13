"""
Router de IA contextual para análisis de widgets del dashboard.
Permite al usuario hacer preguntas sobre gráficos, tablas y KPIs específicos.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from app.services.llm_gemini import call_gemini_text, is_gemini_available
from app.services.llm import call_llm_text

router = APIRouter(prefix="/api/ia", tags=["ia"])


class AnalizarWidgetRequest(BaseModel):
    """Request para analizar un widget específico del dashboard."""
    dashboard: str  # Nombre del dashboard (ej: "observatorio", "prediccion")
    widget_title: str  # Título del widget (ej: "Tendencia de empleo")
    widget_type: str  # Tipo: "grafico", "tabla", "kpi", "mapa"
    filters: dict[str, Any] | None = None  # Filtros activos
    data: list[dict[str, Any]] | dict[str, Any] | None = None  # Datos del widget
    question: str  # Pregunta del usuario


class AnalizarWidgetResponse(BaseModel):
    """Response con el análisis de la IA."""
    respuesta: str
    widget_title: str
    dashboard: str


@router.post("/analizar-widget", response_model=AnalizarWidgetResponse)
async def analizar_widget(req: AnalizarWidgetRequest):
    """
    Analiza un widget específico del dashboard usando IA.
    
    Recibe el contexto completo del widget (título, tipo, filtros, datos)
    y la pregunta del usuario. Devuelve un análisis contextual y accionable.
    """
    # Construir prompt con contexto completo
    system = """Eres ALBA, una plataforma de inteligencia laboral para Colombia.
Analiza los datos del widget proporcionados y responde de forma clara, concisa y accionable.
Si hay tendencias o patrones, identifícalos. Si hay anomalías, explícalas.
Usa datos específicos del widget para respaldar tu respuesta.
Si no hay datos suficientes, indícalo claramente.
Responde en español de Colombia."""

    user = f"""## Contexto del widget
- **Dashboard**: {req.dashboard}
- **Widget**: {req.widget_title}
- **Tipo**: {req.widget_type}
- **Filtros activos**: {req.filters or "Ninguno"}

## Datos del widget
{req.data}

## Pregunta del usuario
{req.question}
"""

    try:
        # Intentar con Gemini primero
        if is_gemini_available():
            respuesta = call_gemini_text(system, user)
        else:
            # Fallback a DeepInfra/Gemma
            respuesta = call_llm_text(system, user)
        
        return AnalizarWidgetResponse(
            respuesta=respuesta,
            widget_title=req.widget_title,
            dashboard=req.dashboard,
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al analizar widget: {str(e)}"
        )


class PreguntaGeneralRequest(BaseModel):
    """Request para pregunta general sobre el dashboard."""
    dashboard: str
    pregunta: str
    contexto: dict[str, Any] | None = None


@router.post("/pregunta-general")
async def pregunta_general(req: PreguntaGeneralRequest):
    """
    Responde preguntas generales sobre el dashboard actual.
    Útil cuando el usuario pregunta sobre todo el dashboard, no un widget específico.
    """
    system = """Eres ALBA, una plataforma de inteligencia laboral para Colombia.
Responde de forma clara y concisa en español de Colombia.
Si necesitas más contexto, indícalo."""

    user = f"""## Contexto del dashboard
{req.dashboard}

{req.contexto or "No hay contexto adicional"}

## Pregunta del usuario
{req.pregunta}
"""

    try:
        if is_gemini_available():
            respuesta = call_gemini_text(system, user)
        else:
            respuesta = call_llm_text(system, user)
        
        return {"respuesta": respuesta, "dashboard": req.dashboard}
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al responder pregunta: {str(e)}"
        )
