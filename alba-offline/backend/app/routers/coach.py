"""
Router Coach IA para ALBA Offline.
Usa Gemma 4 E4B local para mejorar CV y entrevistas estructuradas.
"""
import base64
import json
import tempfile
import uuid
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from app.services.llm_local import call_llm_text, call_llm_json

router = APIRouter(prefix="/api/coach", tags=["coach"])

_sesiones_entrevista: dict[str, dict] = {}

_LLM_NO_DISPONIBLE = "La IA local no esta disponible. Instala llama-cpp-python para activar las funciones del Coach."


class CVRequest(BaseModel):
    cv: str = ""
    vacante: str = ""


@router.post("/mejorar-cv")
async def mejorar_cv(req: CVRequest):
    system = (
        "Eres un reclutador y redactor de CV experto en Colombia. Mejora el siguiente CV para que sea "
        "atractivo para reclutadores y filtros ATS, pero MANTENLO REALISTA: NO inventes experiencias, "
        "titulos, empresas ni habilidades que no esten en el CV original. Puedes reformular, enfatizar "
        "logros cuantificables y usar palabras clave relevantes. "
        "Devuelve UNICAMENTE un JSON valido con esta estructura exacta:\n"
        "{\n"
        '  "cv_mejorado": string,\n'
        '  "por_que_es_bueno": string,\n'
        '  "palabras_clave_ats": [string],\n'
        '  "cambios_realizados": [string]\n'
        "}\n"
        "El cv_mejorado debe estar formateado con secciones claras y listo para copiar y pegar."
    )
    user = f"CV ORIGINAL:\n{req.cv}\n"
    if req.vacante:
        user += f"\nVACANTE OBJETIVO:\n{req.vacante}\n"
    try:
        result = call_llm_json(system, user, temperature=0.4)
        if result is None or "error" in result:
            return {
                "cv_mejorado": _LLM_NO_DISPONIBLE,
                "por_que_es_bueno": "",
                "palabras_clave_ats": [],
                "cambios_realizados": [],
            }
        return result
    except Exception as e:
        return {
            "cv_mejorado": f"Error: {e}",
            "por_que_es_bueno": "",
            "palabras_clave_ats": [],
            "cambios_realizados": [],
        }


@router.post("/mejorar-cv-archivo")
async def mejorar_cv_archivo(file: UploadFile = File(...), vacante: str = ""):
    contenido = await file.read()
    texto = ""
    if file.filename and file.filename.endswith(".pdf"):
        import fitz
        doc = fitz.open(stream=contenido, filetype="pdf")
        texto = "\n".join(page.get_text() for page in doc)
        doc.close()
    elif file.filename and (file.filename.endswith(".docx") or file.filename.endswith(".doc")):
        import io
        import docx
        document = docx.Document(io.BytesIO(contenido))
        texto = "\n".join(p.text for p in document.paragraphs)
    else:
        try:
            texto = contenido.decode("utf-8")
        except Exception:
            texto = contenido.decode("latin-1", errors="ignore")

    return await mejorar_cv(CVRequest(cv=texto, vacante=vacante))


# ============================================================================
# Entrevista estructurada (10 preguntas + feedback)
# ============================================================================

class EntrevistaRealistaIniciarReq(BaseModel):
    cv: str = ""
    vacante: str = ""
    modo: str = "realista"


class EntrevistaRealistaAvanzarReq(BaseModel):
    session_id: str
    respuesta: str


@router.post("/entrevista-realista/iniciar")
async def iniciar_entrevista_realista(req: EntrevistaRealistaIniciarReq):
    modo_libre = req.modo == "libre"

    if modo_libre:
        system = (
            "Eres ALBA, una reclutadora experta de RRHH en Colombia. Vas a conducir "
            "una entrevista general de EXACTAMENTE 10 preguntas.\n\n"
            "El usuario quiere practicar entrevista sin una vacante especifica. Genera "
            "10 preguntas de entrevista laborales generales y variadas que evaluen:\n"
            "1-2: Presentacion profesional y trayectoria\n"
            "3-5: Fortalezas, debilidades y logros\n"
            "6-7: Trabajo en equipo, manejo de conflictos, liderazgo\n"
            "8-9: Casos hipoteticos y resolucion de problemas\n"
            "10: Motivacion, metas y expectativas profesionales\n\n"
            "Devuelve UNICAMENTE un JSON valido con esta estructura exacta:\n"
            "{\n"
            '  "saludo": string,\n'
            '  "preguntas": [string, string, ...]  (exactamente 10)\n'
            "}\n"
            "El saludo debe ser calido y mencionar que la entrevista tendra 10 preguntas "
            "generales para practicar. En espanol neutro colombiano."
        )
        user = "Genera 10 preguntas de entrevista laboral general para practicar."
    else:
        system = (
            "Eres ALBA, una reclutadora experta de RRHH en Colombia. Vas a conducir "
            "una entrevista estructurada de EXACTAMENTE 10 preguntas basadas en el CV "
            "del candidato y la vacante objetivo.\n\n"
            "Genera 10 preguntas relevantes y especificas que un reclutador real haria "
            "para evaluar si el candidato encaja en la vacante. Usa el CV para personalizar "
            "las preguntas (pedir detalles de experiencias, profundizar en habilidades, etc).\n\n"
            "Las preguntas deben seguir una progresion logica:\n"
            "1-2: Presentacion y experiencia general\n"
            "3-5: Experiencia tecnica especifica relacionada con la vacante\n"
            "6-7: Habilidades blandas, trabajo en equipo, liderazgo\n"
            "8-9: Casos practicos o hipoteticos del rol\n"
            "10: Motivacion y expectativas\n\n"
            "Devuelve UNICAMENTE un JSON valido con esta estructura exacta:\n"
            "{\n"
            '  "saludo": string,\n'
            '  "preguntas": [string, string, ...]  (exactamente 10)\n'
            "}\n"
            "El saludo debe ser calido, presentar la vacante brevemente y mencionar que la "
            "entrevista tendra 10 preguntas. En espanol neutro colombiano."
        )
        user = f"CV DEL CANDIDATO:\n{req.cv}\n\nVACANTE OBJETIVO:\n{req.vacante}"

    try:
        resultado = call_llm_json(system, user, temperature=0.5)
        if resultado is None or "error" in resultado:
            return {"error": _LLM_NO_DISPONIBLE}

        saludo = resultado.get("saludo", "")
        preguntas = resultado.get("preguntas", [])
        if len(preguntas) < 10:
            while len(preguntas) < 10:
                preguntas.append("Cuéntame más sobre tu experiencia.")
        preguntas = preguntas[:10]

        session_id = str(uuid.uuid4())[:12]
        _sesiones_entrevista[session_id] = {
            "cv": req.cv,
            "vacante": req.vacante,
            "preguntas": preguntas,
            "indice_actual": 0,
            "respuestas": [],
            "estado": "en_curso",
        }

        return {
            "session_id": session_id,
            "saludo": saludo,
            "pregunta_actual": preguntas[0],
            "numero_pregunta": 1,
            "total_preguntas": 10,
            "estado": "en_curso",
        }
    except Exception as e:
        return {"error": f"Error al iniciar: {e}"}


@router.post("/entrevista-realista/avanzar")
async def avanzar_entrevista_realista(req: EntrevistaRealistaAvanzarReq):
    sesion = _sesiones_entrevista.get(req.session_id)
    if not sesion:
        return {"error": "Sesion no encontrada"}
    if sesion["estado"] != "en_curso":
        return {"error": "La entrevista ya termino"}

    idx = sesion["indice_actual"]
    sesion["respuestas"].append({
        "pregunta": sesion["preguntas"][idx],
        "respuesta": req.respuesta,
    })
    sesion["indice_actual"] += 1
    siguiente_idx = sesion["indice_actual"]

    if siguiente_idx >= 10:
        sesion["estado"] = "finalizada"
        feedback = await _generar_feedback_final(sesion)
        return {
            "estado": "finalizada",
            "feedback": feedback,
            "numero_pregunta": 10,
            "total_preguntas": 10,
        }

    import random
    reconocimiento = random.choice(["Gracias.", "Entendido.", "Muy bien.", "Claro.", "Perfecto."])

    return {
        "estado": "en_curso",
        "pregunta_actual": sesion["preguntas"][siguiente_idx],
        "numero_pregunta": siguiente_idx + 1,
        "total_preguntas": 10,
        "breve_reconocimiento": reconocimiento,
    }


async def _generar_feedback_final(sesion: dict) -> dict:
    system = (
        "Eres ALBA, una reclutadora experta en Colombia. La entrevista ha terminado "
        "(10 preguntas respondidas). Genera un feedback estructurado y realista.\n\n"
        "Devuelve UNICAMENTE un JSON valido con esta estructura exacta:\n"
        "{\n"
        '  "puntaje_general": number (0-100),\n'
        '  "fortalezas": [string],\n'
        '  "areas_mejora": [string],\n'
        '  "recomendacion": string,\n'
        '  "sugerencia_practica": string\n'
        "}\n"
    )
    texto_preguntas = ""
    for i, par in enumerate(sesion["respuestas"], 1):
        texto_preguntas += f"\n--- Pregunta {i} ---\nQ: {par['pregunta']}\nR: {par['respuesta']}\n"

    user = (
        f"CV DEL CANDIDATO:\n{sesion['cv']}\n\n"
        f"VACANTE OBJETIVO:\n{sesion['vacante']}\n\n"
        f"RESPUESTAS DE LA ENTREVISTA:{texto_preguntas}"
    )

    try:
        resultado = call_llm_json(system, user, temperature=0.4)
        if resultado is None or "error" in resultado:
            return {
                "puntaje_general": 0,
                "fortalezas": [],
                "areas_mejora": [],
                "recomendacion": _LLM_NO_DISPONIBLE,
                "sugerencia_practica": "",
            }
        return resultado
    except Exception:
        return {
            "puntaje_general": 0,
            "fortalezas": [],
            "areas_mejora": [],
            "recomendacion": "No se pudo generar el feedback.",
            "sugerencia_practica": "",
        }