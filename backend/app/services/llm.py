"""
Cliente LLM para ALBA usando DeepInfra (API compatible con OpenAI).
Modelo: Gemma 4 vía DeepInfra.
"""
import json
import os
import re
from typing import Any

from openai import OpenAI

DEEPINFRA_API_KEY = os.environ.get("DEEPINFRA_API_KEY", "keLkyno8SpPdoNhd6VCAXXivKEgbdkjs")
MODEL_NAME = "google/gemma-4-26B-A4B-it"

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=DEEPINFRA_API_KEY,
            base_url="https://api.deepinfra.com/v1/openai",
        )
    return _client


def _extract_json(text: str) -> dict[str, Any]:
    """Extrae el primer bloque JSON válido de la respuesta del LLM."""
    # Buscar bloque markdown ```json ... ```
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    # Buscar primer objeto JSON { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No se encontró JSON válido en la respuesta del modelo")


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
    """Llama al LLM y devuelve el contenido como JSON."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=1500,
    )
    text = response.choices[0].message.content or ""
    return _extract_json(text)


def match_cv_vacante(cv: str, vacante: str) -> dict[str, Any]:
    system = (
        "Eres un reclutador experto en Colombia. Analiza un CV/perfil y una vacante laboral. "
        "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        "{\n"
        '  "score_match": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas": [{"requisito": string, "peso": number, "como_cubrir": string}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "El score debe ser entre 0 y 100. El peso de cada brecha debe ser entre 5 y 25. "
        "Sé honesto, objetivo y útil."
    )
    user = f"CV / PERFIL:\n{cv}\n\nVACANTE LABORAL:\n{vacante}"
    return call_llm_json(system, user)


def match_pensum(pensum: str) -> dict[str, Any]:
    system = (
        "Eres un asesor académico y de mercado laboral en Colombia. Analiza un pensum académico "
        "y evalúa su alineación con las necesidades actuales y futuras del mercado laboral colombiano. "
        "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        "{\n"
        '  "score_alineacion": number,\n'
        '  "interpretacion": string,\n'
        '  "fortalezas": [string],\n'
        '  "brechas_mercado": [{"area": string, "nivel_importancia": "alta" | "media" | "baja", "sugerencia": string}],\n'
        '  "recomendacion_general": string\n'
        "}\n"
        "El score debe ser entre 0 y 100. Sé honesto, objetivo y útil."
    )
    user = f"PENSUM ACADÉMICO:\n{pensum}"
    return call_llm_json(system, user)


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
    return call_llm_json(system, user)


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
    return call_llm_json(system, user)


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

    client = get_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=1500,
    )
    return response.choices[0].message.content or ""
