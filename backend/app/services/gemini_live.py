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
    """Cliente para Live API. Usa Vertex (ADC) si hay proyecto, sino AI Studio."""
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
        "Gemini Live requiere GOOGLE_CLOUD_PROJECT o GOOGLE_API_KEY. "
        "En local: gcloud auth application-default login"
    )


COACH_SYSTEM_INSTRUCTION = (
    "Eres ALBA, una entrevistadora laboral experta. Estás simulando una entrevista de trabajo por voz en español.\n\n"
    "Personalidad: eres cálida, natural y conversacional, como una entrevistadora humana con experiencia. "
    "Hablas con confianza, haces sentir cómodo al candidato y la conversación fluye como una charla real, no como un interrogatorio rígido.\n\n"
    "Estilo de comunicación:\n"
    "- Expándete al hablar: no des respuestas de una sola frase. Converseza naturalmente, con un tono cercano.\n"
    "- Cuando el candidato responda, reacciona genuinamente: comenta qué te pareció, da ejemplos concretos de lo que esperas o de cómo podría mejorar.\n"
    "- Da sugerencias prácticas y útiles, como lo haría un buen mentor durante una entrevista.\n"
    "- Usa expresiones naturales del español hablado (por ejemplo: 'me encanta eso', 'eso es clave', 'te cuento que...').\n"
    "- Haz una pregunta por turno, pero rodéala de contexto y comentarios, no la lances en seco.\n"
    "- Si el candidato duda, anímalo y dale una pista o reformula la pregunta para ayudarlo.\n"
    "- No inventes datos del candidato ni respondas las preguntas por él."
)


class GeminiLiveCoach:
    """Gestiona una sesion de entrevista en vivo con Gemini Live API (solo audio)."""

    def __init__(
        self,
        model: str = LIVE_MODEL,
        input_sample_rate: int = 16000,
        vacante: str = "",
        voice_name: str = "Puck",
    ):
        self.model = model
        self.input_sample_rate = input_sample_rate
        self.vacante = vacante
        self.voice_name = voice_name
        self.client = _get_live_client()

    async def start_session(
        self,
        audio_input_queue: asyncio.Queue,
        audio_output_callback,
        audio_interrupt_callback=None,
    ):
        """Inicia la sesion Live y emite eventos via yield (async generator).

        Args:
            audio_input_queue: cola con chunks PCM (bytes) del microfono del usuario.
            audio_output_callback: async (bytes) -> None con audio PCM 24kHz de Gemini.
            audio_interrupt_callback: async () -> None opcional al interrumpirse.

        Yields:
            dict: eventos {"type": "user"|"gemini"|"turn_complete"|"interrupted"|"error", ...}
        """
        system_instruction = COACH_SYSTEM_INSTRUCTION
        if self.vacante:
            system_instruction += (
                f"\n\nLa vacante objetivo de esta entrevista es:\n{self.vacante}\n"
                "Adapta tus preguntas a esa vacante."
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

            # Texto de arranque: ALBA se presenta con calidez y empieza la entrevista.
            await session.send_client_content(
                turns=types.Content(
                    parts=[types.Part(text="Preséntate como ALBA con calidez, agradece al candidato por venir, comentale brevemente de qué va la entrevista según la vacante, y haz la primera pregunta con contexto.")]
                ),
                turn_complete=True,
            )

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