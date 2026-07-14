"""
Cliente TTS local usando Pocket TTS (Kyutai).
Ligero: ~100MB, corre en CPU, soporta espanol.
Modelo incluido en el paquete (no requiere descarga).

Solo 2 modelos en ALBA Offline:
  1. Gemma 4 E4B (LLM + audio nativo) — models/gemma-4-E4B-it-qat-GGUF.gguf
  2. Pocket TTS (TTS) — models/pocket-tts/ (incluido, no se descarga)
"""
import os
import tempfile
from pathlib import Path

_MODELS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "models"
_POCKET_TTS_CACHE = _MODELS_DIR / "pocket-tts"

_tts_model = None
_tts_ready = False


def _get_tts():
    global _tts_model, _tts_ready
    if _tts_model is None:
        try:
            from pocket_tts import TTSModel

            # Configurar HuggingFace para usar el cache local del paquete
            if _POCKET_TTS_CACHE.exists():
                os.environ["HF_HOME"] = str(_MODELS_DIR)
                os.environ["HF_HUB_CACHE"] = str(_MODELS_DIR)
                print(f"[TTS] Usando modelo local: {_POCKET_TTS_CACHE}")

            print("[TTS] Cargando Pocket TTS...")
            _tts_model = TTSModel.load_model()
            _tts_ready = True
            print("[TTS] Pocket TTS listo!")
        except Exception as e:
            print(f"[TTS] Pocket TTS no disponible: {e}")
            _tts_ready = False
    return _tts_model


def text_to_speech(text: str, output_path: str = None, voice: str = "lola") -> str:
    """
    Convierte texto a archivo de audio WAV usando Pocket TTS.
    Voz "lola" es la voz predefinida en espanol.
    Devuelve la ruta al archivo de audio generado.
    """
    model = _get_tts()
    if model is None:
        return None

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_path = tmp.name
        tmp.close()

    try:
        import scipy.io.wavfile
        voice_state = model.get_state_for_audio_prompt(voice)
        audio = model.generate_audio(voice_state, text)
        scipy.io.wavfile.write(output_path, model.sample_rate, audio.numpy())
        return output_path
    except Exception as e:
        print(f"[TTS] Error generando audio: {e}")
        return None


def is_tts_available() -> bool:
    return _tts_ready