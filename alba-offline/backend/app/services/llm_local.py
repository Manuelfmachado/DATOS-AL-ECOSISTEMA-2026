"""
Cliente LLM local usando llama-server + Gemma 4 E4B con mmproj (audio nativo).
Reemplaza a Gemini/DeepInfra en la version offline.

Arquitectura:
  - llama-server se ejecuta como subprocess con --model + --mmproj
  - El backend FastAPI se comunica con llama-server via HTTP (API OpenAI-compatible)
  - Gemma 4 E4B procesa texto, imagenes y audio nativamente

Solo 2 modelos en todo el sistema:
  1. Gemma 4 E4B (LLM + audio + multimodal) — incluido en el ZIP
  2. Pocket TTS (TTS) — incluido en el ZIP
"""
import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from typing import Any

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models"

GEMMA_MODEL_PATH = os.environ.get(
    "GEMMA_MODEL_PATH",
    str(_MODELS_DIR / "gemma-4-E4B-it-qat-GGUF.gguf"),
)
MMPROJ_PATH = os.environ.get(
    "MMPROJ_PATH",
    str(_MODELS_DIR / "mmproj-F16.gguf"),
)

LLAMA_SERVER_URL = os.environ.get("LLAMA_SERVER_URL", "http://127.0.0.1:8081")
LLAMA_SERVER_PORT = int(os.environ.get("LLAMA_SERVER_PORT", "8081"))

_server_process = None
_server_ready = False


def _detect_gpu():
    """Detecta si hay GPU NVIDIA disponible."""
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            return True
    except Exception:
        pass
    return False


def _start_server():
    """Inicia llama-server como subprocess con modelo + mmproj."""
    global _server_process, _server_ready

    if _server_ready:
        return True

    if not Path(GEMMA_MODEL_PATH).exists():
        raise FileNotFoundError(
            f"Modelo no encontrado en {GEMMA_MODEL_PATH}. "
            "Los modelos deben venir incluidos en el paquete."
        )

    has_gpu = _detect_gpu()
    ngl = "999" if has_gpu else "0"
    n_threads = int(os.environ.get("N_THREADS", "4"))

    print(f"[LLM] Iniciando llama-server...")
    print(f"[LLM] Modelo: {GEMMA_MODEL_PATH}")
    print(f"[LLM] MMProj: {MMPROJ_PATH}")
    print(f"[LLM] GPU: {'SI' if has_gpu else 'NO (CPU)'}")
    print(f"[LLM] Puerto: {LLAMA_SERVER_PORT}")

    cmd = [
        sys.executable, "-m", "llama_cpp.server",
        "--model", GEMMA_MODEL_PATH,
        "--mmproj", MMPROJ_PATH,
        "--host", "127.0.0.1",
        "--port", str(LLAMA_SERVER_PORT),
        "--n-gpu-layers", ngl,
        "--n-threads", str(n_threads),
        "--ctx-size", "8192",
        "--chat-format", "gemma",
    ]

    _server_process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    # Esperar a que el servidor este listo
    print("[LLM] Esperando a que el servidor este listo...")
    for _ in range(60):
        try:
            r = requests.get(f"{LLAMA_SERVER_URL}/health", timeout=2)
            if r.status_code == 200:
                _server_ready = True
                print("[LLM] Servidor listo!")
                return True
        except Exception:
            pass
        time.sleep(1)

    print("[LLM] ERROR: El servidor no respondio en 60 segundos")
    return False


def _stop_server():
    """Detiene llama-server."""
    global _server_process, _server_ready
    if _server_process:
        _server_process.terminate()
        _server_process.wait(timeout=10)
        _server_process = None
    _server_ready = False


def _call_api(messages: list, temperature: float = 0.4, max_tokens: int = 2048) -> str:
    """Llama a la API de llama-server (compatible con OpenAI)."""
    if not _server_ready:
        _start_server()

    payload = {
        "messages": messages,
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 64,
        "max_tokens": max_tokens,
    }

    r = requests.post(
        f"{LLAMA_SERVER_URL}/v1/chat/completions",
        json=payload,
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"] or ""


def _extract_json(text: str) -> dict[str, Any]:
    import re
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    raise ValueError("No se encontro JSON valido en la respuesta del modelo")


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
    """Llama al LLM y devuelve el contenido como JSON."""
    text = call_llm_text(system_prompt, user_prompt, temperature, 1500)
    return _extract_json(text)


def call_llm_text(system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int = 2048) -> str:
    """Llama al LLM y devuelve texto plano."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return _call_api(messages, temperature, max_tokens)


def call_llm_audio(system_prompt: str, audio_path: str, temperature: float = 0.4) -> str:
    """
    Procesa audio nativamente con Gemma 4 E4B via mmproj.
    Gemma 4 E4B tiene codificador de audio nativo (~300M params).
    El archivo mmproj-F16.gguf habilita esta capacidad en llama-server.

    El audio se envia como input multimodal al modelo, que lo transcribe
    y genera una respuesta en un solo paso.
    """
    import base64

    if not Path(audio_path).exists():
        raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")

    if not _server_ready:
        _start_server()

    # Leer audio y convertir a base64
    with open(audio_path, "rb") as f:
        audio_b64 = base64.b64encode(f.read()).decode()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": "Transcribe y responde el siguiente audio:"},
            {"type": "audio_url", "audio_url": {"url": f"data:audio/wav;base64,{audio_b64}"}},
        ]},
    ]

    try:
        return _call_api(messages, temperature, 2048)
    except Exception as e:
        # Si el servidor no soporta audio nativo, informar
        print(f"[LLM] Error procesando audio nativo: {e}")
        raise


def is_model_loaded() -> bool:
    return _server_ready


def shutdown():
    """Detiene el servidor. Llamar al cerrar la aplicacion."""
    _stop_server()