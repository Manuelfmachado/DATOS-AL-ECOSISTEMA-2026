"""
Cliente LLM local usando llama-cpp-python con Qwen3.5-2B.
Funciona 100% offline, sin servidor externo, sin internet.

Arquitectura:
  - Llama el modelo GGUF directamente en memoria (in-process)
  - Lazy init: se carga solo al primer uso
  - Cache: se mantiene en memoria mientras el backend este vivo
  - Timeout: 300s max por llamada (configurable con LLM_TIMEOUT)
"""
import os
import json
import time
import re
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models"

GEMMA_MODEL_PATH = os.environ.get(
    "GEMMA_MODEL_PATH",
    str(_MODELS_DIR / "Qwen3.5-2B-Q4_K_M.gguf"),
)

LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "300"))
LLM_N_THREADS = int(os.environ.get("LLM_N_THREADS", "2"))

_llm = None


def _get_llm():
    """Lazy init: carga el modelo GGUF en memoria solo cuando se necesita."""
    global _llm
    if _llm is not None:
        return _llm
    if not _is_available():
        return None
    try:
        from llama_cpp import Llama
        path = GEMMA_MODEL_PATH
        if not Path(path).exists():
            # Fallback: cualquier .gguf en models/
            ggufs = sorted(_MODELS_DIR.glob("*.gguf"))
            if ggufs:
                path = str(ggufs[0])
                print(f"[LLM] Qwen3.5-2B no encontrado, usando: {Path(path).name}")
            else:
                print(f"[LLM] No se encontro ningun .gguf en {_MODELS_DIR}")
                print(f"[LLM] Ejecuta: python descargar_modelos.py")
                return None

        print(f"[LLM] Cargando modelo: {Path(path).name}...")
        t0 = time.time()
        _llm = Llama(
            model_path=path,
            n_ctx=4096,
            n_threads=LLM_N_THREADS,
            n_threads_batch=LLM_N_THREADS,
            verbose=False,
        )
        print(f"[LLM] Modelo cargado en {time.time() - t0:.0f}s")
        return _llm
    except Exception as e:
        print(f"[LLM] Error cargando modelo: {e}")
        return None


def _is_available() -> bool:
    try:
        import llama_cpp  # noqa: F401
        return True
    except ImportError:
        return False


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Intentar reparar JSON truncado: cerrar llaves y comillas pendientes
    stripped = text.strip()
    if stripped.startswith("{"):
        # Contar llaves abiertas vs cerradas
        opens = stripped.count("{") - stripped.count("}")
        if opens > 0:
            stripped += "}" * opens
        # Contar corchetes
        opens = stripped.count("[") - stripped.count("]")
        if opens > 0:
            stripped += "]" * opens
        # Cerrar strings truncados
        if stripped.rstrip().endswith('"'):
            pass  # ya termina bien
        elif '"' in stripped:
            stripped += '"'
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
    return {"error": "No se encontro JSON valido", "raw": text[:200]}


def call_llm_text(system_prompt: str, user_prompt: str, temperature: float = 0.4, max_tokens: int = 600) -> str | None:
    """Llama al LLM y devuelve texto plano. Timeout controlado por LLM_TIMEOUT (default 120s)."""
    llm = _get_llm()
    if llm is None:
        return None
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                llm.create_chat_completion,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                repeat_penalty=1.1,
            )
            r = future.result(timeout=LLM_TIMEOUT)
        elapsed = time.time() - t0
        tokens = r.get("usage", {}).get("completion_tokens", 0)
        tps = tokens / elapsed if elapsed > 0 else 0
        content = r["choices"][0]["message"]["content"] or ""
        # Limpiar think tags si el modelo los genero
        content = re.sub(r"<\s*think\s*>.*?<\s*/\s*think\s*>", "", content, flags=re.DOTALL).strip()
        print(f"[LLM] {tokens} tokens en {elapsed:.1f}s ({tps:.1f} tok/s)")
        return content
    except FutureTimeoutError:
        print(f"[LLM] Timeout: el modelo no respondio en {LLM_TIMEOUT}s")
        return None
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return None


def call_llm_json(system_prompt: str, user_prompt: str, temperature: float = 0.3, max_tokens: int = 1000) -> dict[str, Any]:
    """Llama al LLM y devuelve el contenido como JSON."""
    text = call_llm_text(system_prompt, user_prompt, temperature, max_tokens)
    if text is None:
        return {"error": "LLM no disponible"}
    try:
        return _extract_json(text)
    except Exception:
        return {"error": "No se pudo parsear JSON", "raw": text[:500], "last_chars": text[-200:]}


def call_llm_audio(system_prompt: str, audio_path: str, temperature: float = 0.4) -> str | None:
    """Procesa audio. Requiere mmproj (no implementado sin llama-server)."""
    return None


def is_model_loaded() -> bool:
    return _get_llm() is not None
