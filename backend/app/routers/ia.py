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
    historial: list[dict[str, Any]] | None = None  # Historial de la conversación


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
    system = """Eres ALBA, un asistente de inteligencia laboral para Colombia. Eres experto en empleo, educación, emprendimiento, economía, ciudades, costo de vida y cualquier tema relacionado con Colombia.

REGLAS OBLIGATORIAS:
1. Responde TODA pregunta del usuario, sin importar si está o no relacionada con los datos del widget. No digas "no tengo datos" ni "no puedo responder".
2. Usa tu conocimiento entrenado sobre Colombia libremente. Eres un experto.
3. Si tienes duda sobre una cifra específica, usa Google Search (está habilitado) para buscar información actual y real.
4. ANTI-ALUCINACIONES: si no estás seguro de una cifra exacta, da un rango o di "aproximadamente". Nunca inventes números precisos.
5. Cuando los datos del widget sean relevantes, úsalos y cítalos. NO contradigas los datos del widget bajo ninguna circunstancia.
6. CONTEXTO COLOMBIANO OBLIGATORIO:
   - Usa SIEMPRE pesos colombianos (COP, $) para dinero. NUNCA uses dólares (USD) ni euros.
   - Cita fuentes colombianas cuando busques en internet: DANE, Banco de la República, MinTrabajo, MEN, SENA, Confecámaras, etc.
   - Prefiere datos de Colombia. Si buscas en Google, prioriza resultados .co o de fuentes oficiales colombianas.
   - Menciona ciudades y departamentos por su nombre en Colombia.
7. Sé conciso: máximo 3-4 párrafos. Usa **negrita** para resaltar datos clave.
8. Responde en español de Colombia, con tono profesional pero cercano.
9. NO comiences con "¡Hola!" ni "Entiendo que..." ni "Claro!". Responde directamente a la pregunta."""

    historial_txt = ""
    if req.historial:
        historial_txt = "\n\n## Historial de la conversación\n" + "\n".join(
            [f"- **{'Usuario' if h.get('role') == 'user' else 'ALBA'}**: {h.get('content', '')}" for h in req.historial]
        )

    user = f"""## Contexto del widget
- **Dashboard**: {req.dashboard}
- **Widget**: {req.widget_title}
- **Tipo**: {req.widget_type}
- **Filtros activos**: {req.filters or "Ninguno"}

## Datos del widget
{req.data}{historial_txt}

## Pregunta del usuario
{req.question}
"""

    try:
        # Intentar con Gemini primero (con Google Search habilitado para preguntas generales)
        if is_gemini_available():
            # Detectar si la pregunta es general (no sobre el widget)
            pregunta_lower = req.question.lower()
            palabras_generales = ['costo de vida', 'vivir en', 'caro', 'barato', 'mejor ciudad', 'seguridad', 'clima', 'universidad', 'salario mínimo', 'inflación', 'pib', 'producto interno']
            es_general = any(p in pregunta_lower for p in palabras_generales) or not req.data
            # Activar grounding solo para preguntas generales (evita latencia innecesaria en analisis de widget)
            respuesta = call_gemini_text(system, user, grounding=es_general)
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
