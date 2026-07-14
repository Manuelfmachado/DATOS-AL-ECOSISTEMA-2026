"""
Router Coach IA para ALBA Offline.
Usa Gemma 4 E4B local para mejorar CV y simular entrevistas.
Usa OmniVoice local para TTS en modo voz.
"""
import base64
import tempfile
from fastapi import APIRouter
from pydantic import BaseModel
from app.services.llm_local import call_llm_text, call_llm_audio

router = APIRouter(prefix="/api/coach", tags=["coach"])


class CVRequest(BaseModel):
    cv_text: str


@router.post("/mejorar-cv")
async def mejorar_cv(req: CVRequest):
    system = (
        "Eres un experto en recursos humanos en Colombia. Mejora el CV del usuario "
        "para que sea atractivo pero realista (sin inventar experiencias). "
        "Optimiza palabras clave para filtros ATS. "
        "Responde en texto plano con: 1) CV mejorado, 2) Explicacion de cambios."
    )
    try:
        result = call_llm_text(system, req.cv_text, temperature=0.4, max_tokens=3000)
        return {"cv_mejorado": result}
    except Exception as e:
        return {"error": str(e)}


class EntrevistaRequest(BaseModel):
    mensaje: str
    contexto: str = ""
    historial: list[dict] = []


@router.post("/entrevista")
async def entrevista(req: EntrevistaRequest):
    system = (
        "Eres un entrevistador profesional en Colombia. Simulas una entrevista de trabajo. "
        "Haz una pregunta a la vez. Se profesional pero desafiante. "
        "Responde en espanol, de forma concisa (maximo 3 parrafos)."
    )
    user = req.mensaje
    if req.contexto:
        user = f"Contexto del puesto: {req.contexto}\n\nRespuesta del candidato: {req.mensaje}"
    try:
        result = call_llm_text(system, user, temperature=0.7, max_tokens=500)
        return {"respuesta": result}
    except Exception as e:
        return {"error": str(e)}


@router.post("/voz")
async def coach_voz(audio_b64: str = ""):
    """
    Recibe audio en base64, lo procesa con Gemma 4 E4B (audio nativo),
    genera respuesta de texto y la convierte a voz con OmniVoice.
    """
    from app.services.tts_local import text_to_speech, is_tts_available

    if not audio_b64:
        return {"error": "No se recibio audio"}

    tmp_audio = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_audio.write(base64.b64decode(audio_b64))
    tmp_audio.close()

    system = (
        "Eres un coach laboral en Colombia. El usuario te habla por voz. "
        "Escucha su audio y responde de forma profesional y concisa en espanol. "
        "Maximo 150 palabras."
    )
    try:
        respuesta_texto = call_llm_audio(system, tmp_audio.name, temperature=0.5)

        audio_respuesta = None
        if is_tts_available():
            audio_respuesta = text_to_speech(respuesta_texto)
            if audio_respuesta:
                with open(audio_respuesta, "rb") as f:
                    audio_b64_resp = base64.b64encode(f.read()).decode()
                return {
                    "texto": respuesta_texto,
                    "audio": audio_b64_resp,
                }

        return {"texto": respuesta_texto, "audio": None}
    except Exception as e:
        return {"error": str(e)}