"""
ALBA Desktop — Aplicacion nativa sin consola ni navegador.

Arquitectura:
  1. Inicia FastAPI (UVicorn) en un hilo oculto en segundo plano
  2. Abre una ventana nativa con pywebview (Edge WebView2)
  3. La ventana carga el frontend servido por FastAPI
  4. Al cerrar la ventana, detiene el backend

El usuario solo ve una ventana como VS Code o Discord.
Nunca ve localhost, ni consola, ni pip install.

Uso:
  python alba_app.py           — desarrollo
  ALBA.exe (PyInstaller)        — distribucion
"""
import sys
import os
import time
import threading

# Asegurar que el directorio del backend esta en el path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(APP_DIR, "backend")
sys.path.insert(0, BACKEND_DIR)

# Cambiar al directorio de la app para que las rutas relativas funcionen
os.chdir(APP_DIR)

# Variables de entorno para el backend
os.environ.setdefault("ALBA_DB_PATH", os.path.join(APP_DIR, "data", "alba_offline.db"))
os.environ.setdefault("GEMMA_MODEL_PATH", os.path.join(APP_DIR, "models", "Qwen3.5-2B-Q4_K_M.gguf"))
os.environ.setdefault("MMPROJ_PATH", os.path.join(APP_DIR, "models", "mmproj-F16.gguf"))
os.environ.setdefault("N_THREADS", "4")
os.environ.setdefault("N_CTX", "8192")

PORT = 8080


def iniciar_backend():
    """Inicia FastAPI en un hilo daemon (oculto, deja de funcionar al cerrar)."""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=PORT,
        log_level="warning",
        access_log=False,
    )


def esperar_backend(timeout=30):
    """Espera hasta que el backend responda o agote el timeout."""
    import urllib.request
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def crear_base_datos_si_falta():
    """Crea SQLite desde CSVs si no existe (silencioso)."""
    db_path = os.path.join(APP_DIR, "data", "alba_offline.db")
    csv_dir = os.path.join(APP_DIR, "data", "processed")
    if not os.path.exists(db_path) and os.path.exists(csv_dir):
        print("[ALBA] Creando base de datos SQLite desde CSVs...")
        sys.path.insert(0, APP_DIR)
        import crear_sqlite
        try:
            crear_sqlite.crear_db()
        except Exception as e:
            print(f"[ALBA] Error creando DB: {e}")
    elif not os.path.exists(db_path):
        print("[ALBA] No se encontro base de datos ni CSVs para crearla.")
        print("[ALBA] Algunas funciones pueden no estar disponibles.")


def main():
    # 1. Crear SQLite si no existe (antes de iniciar el backend)
    crear_base_datos_si_falta()

    # 2. Iniciar backend en hilo daemon
    print("Iniciando ALBA...")
    backend_thread = threading.Thread(target=iniciar_backend, daemon=True)
    backend_thread.start()

    # 3. Esperar a que el backend este listo
    if not esperar_backend(30):
        print("Error: El backend no respondio. Verifica que los modelos esten en models/")
        input("Presiona Enter para salir...")
        sys.exit(1)

    # 4. Abrir ventana nativa con pywebview
    import webview

    window = webview.create_window(
        title="ALBA — Analitica Laboral Basada en IA",
        url=f"http://127.0.0.1:{PORT}",
        width=1400,
        height=900,
        min_size=(1024, 700),
        text_select=True,
        confirm_close=False,
    )

    # El icono se puede anadir despues con:
    # webview.start(icon="alba.ico")

    webview.start()
    # Al cerrar la ventana, el hilo daemon se detiene automaticamente
    print("ALBA cerrado. Hasta pronto!")


if __name__ == "__main__":
    main()