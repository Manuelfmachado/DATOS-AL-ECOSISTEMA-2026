"""
Wrapper de la Gemini Live API para el Modulo 5 (Coach IA - Entrevista en vivo).
Basado en el demo oficial de Google (plain-js-python-sdk-demo-app), simplificado a SOLO AUDIO.

Flujo:
  - El frontend abre un WebSocket y envia chunks PCM 16kHz mono 16-bit.
  - Este wrapper los reenvia a Gemini Live con send_realtime_input.
  - Recibe audio de respuesta (PCM 24kHz mono 16-bit) y lo devuelve al cliente.
  - Tambien emite eventos JSON: transcripcion de usuario, transcripcion de Gemini,
    turn_complete e interrupted.
"""

import asyncio
import inspect
from google import genai
from google.genai import types
from app.services.llm_gemini import (
    GOOGLE_CLOUD_PROJECT,
    GOOGLE_CLOUD_LOCATION,
    GOOGLE_API_KEY,
    LIVE_MODEL,
)


def _get_live_client() -> genai.Client:
    """Cliente para Live API. Usa Vertex (ADC con service account) si hay proyecto, sino AI Studio."""
    if GOOGLE_CLOUD_PROJECT:
        return genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
            http_options=types.HttpOptions(api_version="v1"),
        )
    if GOOGLE_API_KEY:
        return genai.Client(api_key=GOOGLE_API_KEY)
    raise RuntimeError(
        "Gemini Live requiere GOOGLE_CLOUD_PROJECT (con service account) o GOOGLE_API_KEY. "
        "En local: gcloud auth application-default login"
    )


COACH_SYSTEM_BASE = (
    "Eres ALBA, una entrevistadora laboral experta y exreclutadora de RRHH en Colombia. "
    "Estás realizando entrevistas de trabajo por voz en español neutro y cálido. "
    "Tu objetivo es evaluar al candidato con rigor, pero con un tono humano, profesional y respetuoso.\n\n"
    "Reglas generales:\n"
    "- Actúa como un reclutador real: saluda, presenta el rol, explica brevemente la dinámica y haz preguntas relevantes.\n"
    "- NUNCA respondas preguntas por el candidato ni inventes datos suyos.\n"
    "- Evalúa en tiempo real: claridad, experiencia alineada, habilidades blandas, motivación y ajuste cultural.\n"
    "- Haz UNA sola pregunta por turno. Deja que el candidato termine antes de continuar.\n"
    "- Si el candidato evade la pregunta o es vago, haz una pregunta de seguimiento concreta (por ejemplo: '¿Podrías contarme un ejemplo específico?').\n"
    "- Si el candidato responde muy bien, profundiza con detalle, no saltes inmediatamente.\n"
    "- Da feedback breve y útil al final de la entrevista: fortalezas, áreas de mejora y si recomendarías pasar a siguiente fase.\n"
    "- Si el usuario dice 'terminar', 'finalizar' o similar, cierra la entrevista con un resumen y feedback.\n"
)

COACH_SYSTEM_REALISTA = (
    COACH_SYSTEM_BASE +
    "\nModo realista: tienes el CV y la vacante del candidato. "
    "Debes hacer una entrevista de verdad basada en esa información. "
    "- Lee el CV y la vacante y formula preguntas directas sobre experiencia, habilidades, logros y brechas.\n"
    "- Compara lo que dice el candidato con los requisitos de la vacante.\n"
    "- Si menciona algo en el CV, pide que lo profundice con el método STAR (situación, tarea, acción, resultado).\n"
    "- Detecta contradicciones o carencias respecto a la vacante y pregunta por ellas de forma respetuosa.\n"
    "- Al final, entrega un feedback estructurado: puntaje 0-100, fortalezas, riesgos y recomendación de pasar/no pasar.\n"
)

COACH_SYSTEM_LIBRE = (
    COACH_SYSTEM_BASE +
    "\nModo libre: el usuario quiere practicar cualquier tipo de entrevista. "
    "Pregunta al inicio qué tipo de entrevista desea practicar y a qué cargo/sector se postula. "
    "Luego conduce la entrevista como un reclutador real. "
    "Al final, entrega feedback con puntaje 0-100, fortalezas y áreas de mejora.\n"
)


class GeminiLiveCoach:
    """Gestiona una sesion de entrevista en vivo con Gemini Live API (solo audio)."""

    def __init__(
        self,
        model: str = LIVE_MODEL,
        input_sample_rate: int = 16000,
        modo: str = "libre",
        cv: str = "",
        vacante: str = "",
        voice_name: str = "Puck",
    ):
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.modo = modo
        self.cv = cv
        self.vacante = vacante
        self.voice_name = voice_name
        self.client = _get_live_client()

    async def start_session(
        self,
        audio_input_queue: asyncio.Queue,
        audio_output_callback,
        audio_interrupt_callback=None,
        text_input_queue: asyncio.Queue | None = None,
    ):
        """Inicia la sesion Live y emite eventos via yield (async generator).

        Args:
            audio_input_queue: cola con chunks PCM (bytes) del microfono del usuario.
            audio_output_callback: async (bytes) -> None con audio PCM 24kHz de Gemini.
            audio_interrupt_callback: async () -> None opcional al interrumpirse.
            text_input_queue: cola opcional para mensajes de texto (ej. CV en modo realista).

        Yields:
            dict: eventos {"type": "user"|"gemini"|"turn_complete"|"interrupted"|"error", ...}
        """
        system_instruction = COACH_SYSTEM_REALISTA if self.modo == "realista" else COACH_SYSTEM_LIBRE
        if self.vacante:
            system_instruction += (
                f"\n\nVACANTE OBJETIVO:\n{self.vacante}\n"
                "Usa esta vacante para contextualizar las preguntas y el feedback."
            )
        if self.modo == "realista" and self.cv:
            system_instruction += (
                f"\n\nCV DEL CANDIDATO:\n{self.cv}\n"
                "Usa el CV para hacer preguntas específicas. No repitas todo el CV, selecciona lo más relevante para la vacante."
            )

        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            system_instruction=types.Content(
                parts=[types.Part(text=system_instruction)]
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        async with self.client.aio.live.connect(model=self.model, config=config) as session:

            # Texto de arranque según modo
            if self.modo == "realista" and self.cv:
                prompt_inicio = (
                    "Preséntate como ALBA, entrevistadora de RRHH. Agradece al candidato por asistir. "
                    "Dile que revisaste su CV y la vacante, y que harás una entrevista basada en su perfil real. "
                    "Haz la primera pregunta relacionada con su experiencia más relevante para la vacante."
                )
            elif self.vacante:
                prompt_inicio = (
                    "Preséntate como ALBA, entrevistadora de RRHH. Agradece al candidato por asistir. "
                    "Coméntale brevemente de qué va la vacante y haz la primera pregunta contextual."
                )
            else:
                prompt_inicio = (
                    "Preséntate como ALBA, entrevistadora de RRHH. Pregunta al candidato qué tipo de entrevista "
                    "quiere practicar y a qué cargo o sector se postula. Luego comienza la entrevista."
                )

            await session.send_client_content(
                turns=types.Content(
                    parts=[types.Part(text=prompt_inicio)]
                ),
                turn_complete=True,
            )

            # Hilo opcional para enviar texto plano (CV) recibido por cola
            async def send_text_loop():
                if not text_input_queue:
                    return
                while True:
                    try:
                        text_msg = await text_input_queue.get()
                        if text_msg is None:
                            break
                        await session.send_client_content(
                            turns=types.Content(parts=[types.Part(text=text_msg)]),
                            turn_complete=False,
                        )
                    except asyncio.CancelledError:
                        break

            send_text_task = asyncio.create_task(send_text_loop()) if text_input_queue else None

            async def send_audio():
                try:
                    while True:
                        chunk = await audio_input_queue.get()
                        await session.send_realtime_input(
                            audio=types.Blob(
                                data=chunk,
                                mime_type=f"audio/pcm;rate={self.input_sample_rate}",
                            )
                        )
                except asyncio.CancelledError:
                    pass

            event_queue: asyncio.Queue = asyncio.Queue()

            async def receive_loop():
                try:
                    while True:
                        async for response in session.receive():
                            server_content = response.server_content

                            if server_content:
                                if server_content.model_turn:
                                    for part in server_content.model_turn.parts:
                                        if part.inline_data:
                                            if inspect.iscoroutinefunction(audio_output_callback):
                                                await audio_output_callback(part.inline_data.data)
                                            else:
                                                audio_output_callback(part.inline_data.data)

                                if server_content.input_transcription and server_content.input_transcription.text:
                                    await event_queue.put(
                                        {"type": "user", "text": server_content.input_transcription.text}
                                    )

                                if server_content.output_transcription and server_content.output_transcription.text:
                                    await event_queue.put(
                                        {"type": "gemini", "text": server_content.output_transcription.text}
                                    )

                                if server_content.turn_complete:
                                    await event_queue.put({"type": "turn_complete"})

                                if server_content.interrupted:
                                    if audio_interrupt_callback:
                                        if inspect.iscoroutinefunction(audio_interrupt_callback):
                                            await audio_interrupt_callback()
                                        else:
                                            audio_interrupt_callback()
                                    await event_queue.put({"type": "interrupted"})

                except Exception as e:
                    await event_queue.put({"type": "error", "error": str(e)})
                finally:
                    await event_queue.put(None)

            send_audio_task = asyncio.create_task(send_audio())
            receive_task = asyncio.create_task(receive_loop())

            try:
                while True:
                    event = await event_queue.get()
                    if event is None:
                        break
                    if isinstance(event, dict) and event.get("type") == "error":
                        yield event
                        break
                    yield event
            finally:
                send_audio_task.cancel()
                receive_task.cancel()
                if send_text_task:
                    send_text_task.cancel()