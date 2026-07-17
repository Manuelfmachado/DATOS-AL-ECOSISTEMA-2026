"""
Descarga los modelos necesarios para ALBA Offline:
1. Qwen3.5-2B GGUF (Q4_K_M) - desde HuggingFace (~1.2 GB)
2. OmniVoice (TTS) - se descarga automaticamente al primer uso

Ejecutar una sola vez: python descargar_modelos.py
"""
import os
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODELS_DIR = ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

GEMMA_REPO = "unsloth/Qwen3.5-2B-GGUF"
GEMMA_FILENAME = "Qwen3.5-2B-Q4_K_M.gguf"
GEMMA_PATH = MODELS_DIR / GEMMA_FILENAME


def verificar_dependencias():
    print("Verificando dependencias de Python...")

    deps_pip = [
        ("llama-cpp-python", "llama_cpp"),
        ("huggingface-hub", "huggingface_hub"),
        ("pandas", "pandas"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("soundfile", "soundfile"),
        ("faster-whisper", "faster_whisper"),
        ("torch", "torch"),
        ("scipy", "scipy"),
    ]

    faltantes = []
    for pip_name, import_name in deps_pip:
        try:
            __import__(import_name)
            print(f"  [OK] {pip_name}")
        except ImportError:
            print(f"  [FALTA] {pip_name}")
            faltantes.append(pip_name)

    if faltantes:
        print(f"\nInstalando dependencias faltantes: {', '.join(faltantes)}")
        for dep in faltantes:
            if dep == "llama-cpp-python":
                # Intentar instalar con soporte CUDA si hay GPU
                try:
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "llama-cpp-python",
                         "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu121"],
                        check=False,
                    )
                except Exception:
                    subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python"], check=False)
            else:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], check=False)

    # Pocket TTS se instala via pip
    try:
        import pocket_tts
        print("  [OK] pocket-tts")
    except ImportError:
        print("  [FALTA] pocket-tts (instalando...)")
        subprocess.run([sys.executable, "-m", "pip", "install", "pocket-tts"], check=False)

    print("  Dependencias verificadas.")


def descargar_gemma():
    if GEMMA_PATH.exists() and GEMMA_PATH.stat().st_size > 1_000_000_000:
        size_gb = GEMMA_PATH.stat().st_size / 1e9
        print(f"  [OK] Qwen3.5-2B ya descargado ({size_gb:.1f} GB)")
        return True

    print("\n  Descargando Qwen3.5-2B (Q4_K_M)...")
    print(f"  Repo: https://huggingface.co/{GEMMA_REPO}")
    print(f"  Tamano estimado: ~1.2 GB")
    print(f"  Esto puede tardar 3-8 minutos segun tu conexion...\n")

    try:
        from huggingface_hub import hf_hub_download
        print(f"  Descargando: {GEMMA_FILENAME}")
        downloaded_path = hf_hub_download(
            repo_id=GEMMA_REPO,
            filename=GEMMA_FILENAME,
            local_dir=str(MODELS_DIR),
        )
        downloaded = Path(downloaded_path)
        if downloaded.exists():
            if GEMMA_PATH.exists():
                GEMMA_PATH.unlink()
            shutil_move(downloaded, GEMMA_PATH)
            size_gb = GEMMA_PATH.stat().st_size / 1e9
            print(f"  [OK] Modelo descargado: {GEMMA_PATH.name} ({size_gb:.1f} GB)")
            return True
    except Exception as e:
        print(f"  [ERROR] No se pudo descargar: {e}")
        print(f"\n  Descarga manual:")
        print(f"  1. Ve a: https://huggingface.co/{GEMMA_REPO}")
        print(f"  2. Descarga: {GEMMA_FILENAME} (~2.6 GB)")
        print(f"  3. Colocalo en: {MODELS_DIR}/")
        return False


def shutil_move(src, dst):
    import shutil
    shutil.move(str(src), str(dst))


def verificar_pocket_tts():
    print("\n  Pocket TTS (Kyutai) se descarga automaticamente al primer uso.")
    print("  Es ligero (~100 MB), corre en CPU y soporta espanol (voz 'lola').")
    print("  No requiere accion manual ahora.")
    return True


def verificar_gpu():
    print("\nVerificando GPU...")
    try:
        result = subprocess.run(["nvidia-smi"], capture_output=True, text=True)
        if result.returncode == 0:
            print("  [OK] GPU NVIDIA detectada")
            print("  Gemma usara GPU automaticamente (mucho mas rapido)")
            return True
        else:
            print("  [INFO] No se detecto GPU NVIDIA")
            print("  Gemma correra en CPU (mas lento pero funcional)")
            return False
    except Exception:
            print("  [INFO] No se detecto GPU")
            print("  El modelo correra en CPU (funcional)")
        else:
            print("  [INFO] GPU detectada")
    except Exception:
        print("  El modelo correra en CPU (funcional)")

    print("\n" + "-" * 55)
    print("1/2 - Modelo LLM: Qwen3.5-2B")
    print("-" * 55)

    if not descargar_gemma():
        print("\n  [ADVERTENCIA] No se pudo descargar el modelo LLM.")
        print("  ALBA funcionara pero las funciones de IA no estaran disponibles.")
        print("  Puedes descargar el modelo manualmente desde:")
        print(f"  https://huggingface.co/{GEMMA_REPO}")
        return False


def main():
    print("=" * 55)
    print("ALBA Offline - Descarga de modelos")
    print("=" * 55)

    verificar_dependencias()
    verificar_gpu()

    print("\n" + "-" * 55)
    print("1/2 - Modelo LLM: Qwen3.5-2B")
    print("-" * 55)
    ok_gemma = descargar_gemma()

    print("\n" + "-" * 55)
    print("2/2 - Modelo TTS: Pocket TTS")
    print("-" * 55)
    verificar_pocket_tts()

    print("\n" + "=" * 55)
    if ok_gemma:
        print("Modelos listos!")
        print("Ejecuta iniciar_alba.bat para iniciar ALBA Offline")
    else:
        print("Descarga manual requerida para Gemma.")
        print(f"Coloca el .gguf en: {MODELS_DIR}/")
    print("=" * 55)


if __name__ == "__main__":
    main()