"""
Descarga los modelos necesarios para ALBA Offline:
1. Gemma 4 E4B IT (GGUF QAT 4-bit) - desde HuggingFace
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

GEMMA_REPO = "unsloth/gemma-4-E4B-it-qat-GGUF"
GEMMA_FILENAME_PATTERNS = [
    "gemma-4-E4B-it-qat-UD-Q4_K_XL.gguf",
    "gemma-4-E4B-it-qat-UD-Q2_K_XL.gguf",
]
MMPROJ_FILE = "mmproj-F16.gguf"
GEMMA_PATH = MODELS_DIR / "gemma-4-E4B-it-qat-GGUF.gguf"
MMPROJ_PATH = MODELS_DIR / "mmproj-F16.gguf"


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
        print(f"  [OK] Gemma 4 E4B ya descargado ({size_gb:.1f} GB)")
        return True

    print("\n  Descargando Gemma 4 E4B IT (QAT 4-bit)...")
    print(f"  Repo: https://huggingface.co/{GEMMA_REPO}")
    print(f"  Tamano estimado: ~5-6 GB")
    print(f"  Esto puede tardar 10-30 minutos segun tu conexion...\n")

    try:
        from huggingface_hub import hf_hub_download, list_repo_files

        # Listar archivos del repo para encontrar el GGUF correcto
        try:
            files = list_repo_files(GEMMA_REPO)
            print(f"  Archivos disponibles en el repo: {files[:10]}")
        except Exception:
            files = GEMMA_FILENAME_PATTERNS

        # Buscar el primer archivo .gguf que coincida
        gguf_file = None
        for pattern in GEMMA_FILENAME_PATTERNS:
            if pattern in files:
                gguf_file = pattern
                break

        # Si no encontro por patron, buscar cualquier .gguf
        if not gguf_file:
            gguf_files = [f for f in files if f.endswith(".gguf")]
            if gguf_files:
                # Preferir el de 4-bit
                for f in gguf_files:
                    if "4" in f.lower() and "bit" in f.lower():
                        gguf_file = f
                        break
                if not gguf_file:
                    gguf_file = gguf_files[0]

        if not gguf_file:
            print(f"  [ERROR] No se encontro archivo .gguf en el repo {GEMMA_REPO}")
            print(f"  Descarga manual desde: https://huggingface.co/{GEMMA_REPO}")
            print(f"  Coloca el archivo .gguf en: {MODELS_DIR}/")
            print(f"  Y renombralo a: gemma-4-E4B-it-qat-GGUF.gguf")
            return False

        print(f"  Descargando: {gguf_file}")
        downloaded_path = hf_hub_download(
            repo_id=GEMMA_REPO,
            filename=gguf_file,
            local_dir=str(MODELS_DIR),
        )

        # Mover/renombrar al nombre esperado
        downloaded = Path(downloaded_path)
        if downloaded.exists():
            if GEMMA_PATH.exists():
                GEMMA_PATH.unlink()
            shutil_move(downloaded, GEMMA_PATH)
            size_gb = GEMMA_PATH.stat().st_size / 1e9
            print(f"  [OK] Gemma descargado: {GEMMA_PATH.name} ({size_gb:.1f} GB)")
            return True
    except Exception as e:
        print(f"  [ERROR] No se pudo descargar Gemma: {e}")
        print(f"\n  Descarga manual:")
        print(f"  1. Ve a: https://huggingface.co/{GEMMA_REPO}")
        print(f"  2. Descarga el archivo .gguf (version 4-bit, ~5-6 GB)")
        print(f"  3. Colocalo en: {MODELS_DIR}/")
        print(f"  4. Renombralo a: gemma-4-E4B-it-qat-GGUF.gguf")
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
        print("  Gemma correra en CPU (mas lento pero funcional)")
        return False


def main():
    print("=" * 55)
    print("ALBA Offline - Descarga de modelos")
    print("=" * 55)

    verificar_dependencias()
    verificar_gpu()

    print("\n" + "-" * 55)
    print("1/2 - Modelo LLM: Gemma 4 E4B")
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