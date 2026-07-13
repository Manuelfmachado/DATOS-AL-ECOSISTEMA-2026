"""
Router del Coach IA en vivo (Entrevista por voz con Gemini Live API).
Endpoint WebSocket que conecta el microfono del usuario con Gemini y devuelve audio + transcripciones.

Uso:
    ws://127.0.0.1:8000/api/coach/live?vacante=Desarrollador%20Full%20Stack

Protocolo:
    - Cliente -> Servidor: bytes PCM (16kHz mono 16-bit LE) del microfono.
    - Servidor -> Cliente: bytes PCM (24kHz mono 16-bit LE) de la voz de Gemini.
    - Servidor -> Cliente: mensajes JSON con eventos:
        {"type": "user",  "text": "..."}    transcripcion de lo que dijo el usuario
        {"type": "gemini","text": "..."}    transcripcion de lo que dijo Gemini
        {"type": "turn_complete"}            fin del turno de Gemini
        {"type": "interrupted"}              Gemini fue interrumpido
        {"type": "error", "error": "..."}    error de la sesion
"""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.gemini_live import GeminiLiveCoach

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/coach", tags=["coach-live"])


@router.websocket("/live")
async def coach_live_ws(websocket: WebSocket, vacante: str = "", voice: str = "Puck"):
    """WebSocket para entrevista laboral en vivo con Gemini Live API."""
    await websocket.accept()
    logger.info("[CoachLive] WebSocket aceptado. vacante=%r voice=%r", vacante, voice)

    audio_input_queue: asyncio.Queue = asyncio.Queue()

    async def audio_output_callback(data: bytes):
        await websocket.send_bytes(data)

    async def audio_interrupt_callback():
        pass

    gemini = GeminiLiveCoach(vacante=vacante, voice_name=voice)

    async def receive_from_client():
        try:
            while True:
                message = await websocket.receive()
                if message.get("bytes"):
                    await audio_input_queue.put(message["bytes"])
                # Ignoramos mensajes de texto: este endpoint es solo audio.
        except WebSocketDisconnect:
            logger.info("[CoachLive] Cliente desconectado")
        except Exception as e:
            logger.error("[CoachLive] Error recibiendo del cliente: %s", e)

    receive_task = asyncio.create_task(receive_from_client())

    async def run_session():
        async for event in gemini.start_session(
            audio_input_queue=audio_input_queue,
            audio_output_callback=audio_output_callback,
            audio_interrupt_callback=audio_interrupt_callback,
        ):
            if event:
                await websocket.send_json(event)

    try:
        await run_session()
    except Exception as e:
        logger.error("[CoachLive] Error en sesion Gemini: %s", e)
        try:
            await websocket.send_json({"type": "error", "error": str(e)})
        except Exception:
            pass
    finally:
        receive_task.cancel()
        try:
            await websocket.close()
        except Exception:
            pass