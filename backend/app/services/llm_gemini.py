"""
Cliente de LLM basado en Google Gemini (2.5 Flash-Lite y Live).
Reemplaza progresivamente a DeepInfra/Gemma 4 para reducir costos y habilitar
 Grounding con búsqueda de Google, multimodalidad y audio nativo.
"""

import os
import json
from typing import Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "datos-al-ecosistema-501905")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
# Variable recomendada por Google para forzar endpoint empresarial de Agent Platform
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "True")

# Modelo por defecto para tareas de texto estructurado
TEXT_MODEL = "gemini-2.5-flash-lite"

# Modelo para tareas donde se prefiere razonamiento más profundo
REASONING_MODEL = "gemini-2.5-flash"

# Modelo para conversacion de audio en vivo (Gemini Live API).
# En Vertex AI el modelo de audio nativo usa este nombre; en AI Studio es "gemini-2.5-flash-live".
# Sobreescribible con la variable de entorno GEMINI_LIVE_MODEL.
LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio")


def _get_client() -> genai.Client:
    # Para Agent Platform / Vertex AI se usa ADC (Application Default Credentials).
    # En local: gcloud auth application-default login
    # En produccin (Railway): variable GOOGLE_APPLICATION_CREDENTIALS apuntando a service account JSON.
    if GOOGLE_CLOUD_PROJECT:
        try:
            return genai.Client(
                vertexai=True,
                project=GOOGLE_CLOUD_PROJECT,
                location=GOOGLE_CLOUD_LOCATION,
                http_options=types.HttpOptions(api_version="v1"),
            )
        except Exception as e:
            msg = (
                "No se pudieron cargar credenciales de Google Cloud. "
                "En local ejecuta: gcloud auth application-default login. "
                "En produccin configura GOOGLE_APPLICATION_CREDENTIALS con el path a un service account JSON. "
                f"Error: {e}"
            )
            raise RuntimeError(msg)
    if GOOGLE_API_KEY:
        # Fallback a AI Studio si no hay proyecto de Cloud
        return genai.Client(api_key=GOOGLE_API_KEY)
    raise RuntimeError("GOOGLE_CLOUD_PROJECT o GOOGLE_API_KEY deben estar configurados")


def _build_config(
    system: str | None = None,
    grounding: bool = False,
    temperature: float = 0.4,
    max_tokens: int = 2048,
) -> types.GenerateContentConfig:
    tools = []
    if grounding:
        tools.append(types.Tool(google_search=types.GoogleSearch()))
    kwargs: dict[str, Any] = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
        "tools": tools,
    }
    if system:
        kwargs["system_instruction"] = system
    return types.GenerateContentConfig(**kwargs)


def call_gemini_text(
    system: str,
    user: str,
    model: str = TEXT_MODEL,
    grounding: bool = False,
    temperature: float = 0.4,
    max_tokens: int = 2048,
) -> str:
    """Envía un prompt a Gemini y devuelve texto plano."""
    client = _get_client()
    config = _build_config(system=system, grounding=grounding, temperature=temperature, max_tokens=max_tokens)
    response = client.models.generate_content(
        model=model,
        config=config,
        contents=user,
    )
    return response.text or ""


def call_gemini_json(
    system: str,
    user: str,
    model: str = TEXT_MODEL,
    grounding: bool = False,
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> dict[str, Any]:
    """Envía un prompt a Gemini y devuelve JSON parseado.
    Solicita explícitamente JSON válido en el system prompt."""
    system_json = (
        system.rstrip()
        + "\n\nDevuelve ÚNICAMENTE un JSON válido. No incluyas explicaciones ni markdown fuera del JSON."
    )
    client = _get_client()
    config = _build_config(system=system_json, grounding=grounding, temperature=temperature, max_tokens=max_tokens)
    response = client.models.generate_content(
        model=model,
        config=config,
        contents=user,
    )
    text = response.text or "{}"
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except Exception as e:
        return {"error": f"No se pudo parsear JSON: {e}", "raw": text}


def is_gemini_available() -> bool:
    return bool(GOOGLE_API_KEY)


# ============================================================================
# Funciones de negocio (reemplazan las de llm.py)
# ============================================================================

def evaluar_idea_negocio(idea: str, departamento: str, inversion: str, contexto_mercado: str = "") -> dict[str, Any]:
    system = (
        "Eres un asesor de emprendimiento experto en Colombia. Analiza una idea de negocio "
        "considerando el contexto local, la inversión inicial, la competencia, la demanda laboral "
        "y las oportunidades de nicho. Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        "{\n"
        '  "score_potencial": number,\n'
        '  "veredicto": string,\n'
        '  "razones_a_favor": [string],\n'
        '  "riesgos": [string],\n'
        '  "pasos": [string],\n'
        '  "fuentes_recursos": [string],\n'
        '  "oportunidad_nicho": string\n'
        "}\n"
        "El score debe ser entre 0 y 100. Sé honesto, práctico y útil. Las recomendaciones deben "
        "ser específicas para Colombia (Fondo Emprender, iNNpulsa, Cámaras de Comercio, SENA, etc.)."
    )
    user = (
        f"IDEA DE NEGOCIO:\n{idea}\n\n"
        f"DEPARTAMENTO/MUNICIPIO: {departamento}\n"
        f"INVERSIÓN INICIAL APROXIMADA: {inversion}\n"
    )
    if contexto_mercado:
        user += f"\nCONTEXTO DE MERCADO LOCAL:\n{contexto_mercado}\n"
    return call_gemini_json(system, user, grounding=True)


def mejorar_cv(cv_texto: str, vacante: str = "") -> dict[str, Any]:
    system = (
        "Eres un reclutador y redactor de CV experto en Colombia. Mejora el siguiente CV para que sea "
        "atractivo para reclutadores y filtros ATS, pero MANTÉNLO REALISTA: NO inventes experiencias, "
        "títulos, empresas ni habilidades que no estén en el CV original. Puedes reformular, enfatizar "
        "logros cuantificables y usar palabras clave relevantes. "
        "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        "{\n"
        '  "cv_mejorado": string,\n'
        '  "por_que_es_bueno": string,\n'
        '  "palabras_clave_ats": [string],\n'
        '  "cambios_realizados": [string]\n'
        "}\n"
        "El cv_mejorado debe estar formateado con secciones claras y listo para copiar y pegar."
    )
    user = f"CV ORIGINAL:\n{cv_texto}\n"
    if vacante:
        user += f"\nVACANTE OBJETIVO:\n{vacante}\n"
    return call_gemini_json(system, user)


def entrevista_chat(mensaje: str, modo: str, historial: str = "", vacante: str = "") -> str:
    if modo == "preguntar":
        system = (
            "Eres un coach de entrevistas laborales experto en Colombia. Responde preguntas sobre "
            "cómo prepararse, qué responder, cómo negociar salario, etc. Sé claro, práctico y con "
            "ejemplos concretos para el contexto colombiano."
        )
        user = mensaje
    else:
        system = (
            "Eres un entrevistador laboral experto en Colombia. Genera preguntas de entrevista "
            "realistas según la vacante y, si el usuario responde, evalúa la respuesta dando feedback "
            "constructivo. Sé honesto, claro y útil."
        )
        user = mensaje
        if vacante:
            user = f"VACANTE:\n{vacante}\n\n{user}"
        if historial:
            user = f"HISTORIAL DE LA ENTREVISTA:\n{historial}\n\n{user}"
    return call_gemini_text(system, user, max_tokens=1500)


def match_cv_vacante(cv: str, vacante: str) -> dict[str, Any]:
    system = (
        "Eres un reclutador senior en Colombia. Compara un CV con una vacante y devuelve "
        "ÚNICAMENTE un JSON con esta estructura exacta:\n"
        "{\n"
        '  "score_match": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas": [{"requisito": string, "peso": number, "como_cubrir": string}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "El score debe ser entre 0 y 100. Las brechas deben ser reales y medibles. "
        "No inventes experiencias ni habilidades que no estén en el CV."
    )
    user = f"CV:\n{cv}\n\nVACANTE:\n{vacante}"
    return call_gemini_json(system, user)


def match_pensum_mercado(pensum: str) -> dict[str, Any]:
    system = (
        "Eres un experto en educación superior y mercado laboral en Colombia. Analiza un pensum "
        "académico y compáralo con la demanda laboral actual. Devuelve ÚNICAMENTE un JSON con esta "
        "estructura exacta:\n"
        "{\n"
        '  "score_alineacion": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas_mercado": [{"area": string, "nivel_importancia": "alta"|"media"|"baja", "sugerencia": string}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "El score debe ser entre 0 y 100. Las brechas deben ser demandas reales del mercado colombiano."
    )
    user = f"PENSUM ACADÉMICO:\n{pensum}"
    return call_gemini_json(system, user, grounding=True)


def generar_insights_prediccion(sectores: dict, profesiones: list, habilidades: list) -> dict[str, Any]:
    system = (
        "Eres un analista laboral y económico experto en Colombia. A partir de proyecciones de sectores, "
        "profesiones y habilidades, genera insights en JSON con esta estructura exacta:\n"
        "{\n"
        '  "sectores": {"principal_empleador": string, "mas_estable": string, "mensaje": string},\n'
        '  "profesiones": {"top_1": string, "top_3": [string], "mensaje": string}\n'
        "}\n"
        "Sé conciso, útil y basado en evidencia."
    )
    user = (
        f"SECTORES (CAGR 5a): {json.dumps(sectores, ensure_ascii=False)}\n"
        f"TOP PROFESIONES: {json.dumps(profesiones[:10], ensure_ascii=False)}\n"
        f"TOP HABILIDADES: {json.dumps(habilidades[:10], ensure_ascii=False)}"
    )
    return call_gemini_json(system, user, grounding=True)
