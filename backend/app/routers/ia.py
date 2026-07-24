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


# ---------------------------------------------------------------------------
# Catálogo de metadatos por widget: fuente, período, qué significan las columnas.
# Se inyecta en el prompt del LLM para que sus respuestas sean precisas y no
# malinterprete los datos crudos del JSON.
# ---------------------------------------------------------------------------
_WIDGET_META: dict[str, dict[str, str]] = {
    "Ocupaciones con mayor demanda creciente": {
        "fuente": "Agencia Pública de Empleo (APE) del SENA — inscritos por ocupación",
        "periodo": "Variación entre 2019 y 2020 (pandemia). Son los únicos años disponibles en la fuente SPE/APE.",
        "columnas": "inscritos_2019/inscritos_2020 = personas inscritas buscando empleo; variacion_pct = crecimiento porcentual; nivel = calificación (técnicos, profesionales, etc.)",
        "caveat": "El crecimiento puede deberse a baja base en 2019 (pocos inscritos). Una ocupación con 10→133 inscritos sube 1230% pero sigue siendo nicho pequeño.",
    },
    "Actividades económicas en alza": {
        "fuente": "Agencia Pública de Empleo (APE) del SENA",
        "periodo": "2019-2020",
        "columnas": "variacion_pct = crecimiento de inscritos; nivel = calificación",
        "caveat": "Variación sobre base 2019; cuidado con crecimientos altos sobre bases pequeñas.",
    },
    "Sectores con mayor crecimiento de empleo": {
        "fuente": "GEIH-DANE — Gran Encuesta Integrada de Hogares (encuesta continua nacional)",
        "periodo": " Serie mensual 2022 a 2026 (4 años). El crecimiento compara el promedio de los primeros 3 meses vs los últimos 3 meses.",
        "columnas": "variacion_pct = crecimiento porcentual real del empleo; empleo_inicial/empleo_final = personas ocupadas al inicio y fin del período; sector = nombre CIIU; rama_ciiu = código.",
        "caveat": "Son sectores económicos (CIIU rev. 4), no ocupaciones individuales. El crecimiento es de personas ocupadas, no de vacantes. Sectores con poco empleo inicial pueden mostrar crecimientos altos en términos relativos.",
    },
    "Brecha oferta vs demanda": {
        "fuente": "Oferta: SNIES (matriculados por núcleo de conocimiento). Demanda: PILA (cotizantes por actividad CIIU).",
        "periodo": "SNIES y PILA más reciente disponible.",
        "columnas": "oferta_share = % de estudiantes en esa área; demanda_share = % de empleo formal en esa área; desajuste = oferta - demanda (positivo=sobre-formación, negativo=oportunidad).",
        "caveat": "Compara estructura de formación vs empleo formal. Los porcentajes son shares relativos, no absolutos.",
    },
    "Contexto macro laboral 2010-2025": {
        "fuente": "World Bank Open Data — indicadores laborales de Colombia",
        "periodo": "2010-2024 (15 años)",
        "columnas": "value = valor del indicador; unidad puede ser % o USD (PIB). Los de empleo por sector (agro/industria/servicios) suman ~100%.",
        "caveat": "Datos del Banco Mundial, comparables internacionalmente. El PIB por persona empleada va en USD constantes 2017, no en %.",
    },
    "Composición del empleo formal": {
        "fuente": "PILA — Plan Integrado de Aportes Laborales",
        "periodo": "Cotizaciones mensuales acumuladas (anualizadas)",
        "columnas": "share_pct = % del total de cotizaciones; cotizantes = número de cotizaciones (no personas únicas).",
        "caveat": "Los totales son cotizaciones mensuales acumuladas: un trabajador con 12 meses genera 12 cotizaciones. La PEA de Colombia es ~26M; el total de cotizaciones es ~99M por esto. El share_pct sí es comparable.",
    },
    "Informalidad: micronegocios por departamento": {
        "fuente": "EMICRON-DANE — Encuesta de Micronegocios",
        "periodo": "2021-2024",
        "columnas": "micronegocios = número de micronegocios informales por departamento; crecimiento_pct = variación entre primer y último año.",
        "caveat": "Micronegocios = unidades económicas pequeñas que no cotizan a PILA (informalidad).",
    },
    "Tendencias del empleo": {
        "fuente": "GEIH-DANE — Gran Encuesta Integrada de Hogares",
        "periodo": "2022-2026",
        "columnas": "empleo = personas ocupadas por sector; tendencia = crece/declina/estable.",
        "caveat": "Serie mensual reciente; para perspectiva histórica más larga ver el widget de Banco Mundial.",
    },
    "Empleo por departamento": {
        "fuente": "GEIH-DANE",
        "periodo": "Más reciente",
        "columnas": "ocupados = personas ocupadas; ingreso_promedio = salario promedio mensual COP.",
    },
    "Sectores formales": {
        "fuente": "PILA — cotizantes por actividad económica (CIIU)",
        "periodo": "Acumulado",
        "columnas": "cotizantes = cotizaciones mensuales; actividadeconomicadesc = sector CIIU.",
        "caveat": "Cotizaciones acumuladas, no personas únicas.",
    },
    "Preguntas y respuestas de entrevista": {
        "fuente": "Generadas por Gemini 2.5 Flash-Lite a partir de una vacante pegada por el usuario.",
        "periodo": "No aplica (generación instantánea).",
        "columnas": "pregunta = pregunta de entrevista; respuesta = respuesta modelo sugerida por ALBA.",
        "caveat": "Las respuestas son modelos genéricos: el candidato debe adaptarlas con ejemplos propios (técnica STAR). Las preguntas se generan en función de la vacante proporcionada.",
    },
}


def _meta_widget(widget_title: str) -> str:
    """Devuelve un texto descriptivo del widget para enriquecer el prompt del LLM."""
    meta = _WIDGET_META.get(widget_title)
    if not meta:
        return ""
    partes = [f"- Fuente: {meta['fuente']}", f"- Período: {meta['periodo']}"]
    if meta.get("columnas"):
        partes.append(f"- Significado de columnas: {meta['columnas']}")
    if meta.get("caveat"):
        partes.append(f"- Nota importante: {meta['caveat']}")
    return "\n".join(partes)


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

## Metadatos del widget (fuente, período y significado de los datos)
{_meta_widget(req.widget_title) or "No hay metadatos disponibles para este widget."}

## Datos del widget (JSON)
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
