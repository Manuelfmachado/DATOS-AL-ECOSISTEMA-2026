@echo off
chcp 65001 >nul
title ALBA - Version Offline
color 0A

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         ALBA - Version Offline           ║
echo  ║   Analitica Laboral Basada en IA         ║
echo  ║   Todo incluido - Listo para usar        ║
echo  ╚══════════════════════════════════════════╝
echo.

REM --- Verificar Python ---
echo [1/4] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no esta instalado.
    echo  Descarga Python 3.11+ desde: https://www.python.org/downloads/
    echo  Asegurate de marcar "Add Python to PATH" durante la instalacion.
    echo.
    pause
    exit /b 1
)
echo       Python OK

REM --- Instalar dependencias (una sola vez) ---
echo [2/4] Verificando dependencias...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       Instalando dependencias (puede tardar 3-5 min la primera vez)...
    pip install -r requirements.txt -q
    if errorlevel 1 (
        echo       Reintentando instalacion...
        pip install -r requirements.txt
    )
)
echo       Dependencias OK

REM --- Crear base de datos SQLite (una sola vez) ---
echo [3/4] Verificando base de datos...
if not exist "data\alba_offline.db" (
    echo       Creando base de datos SQLite desde CSVs...
    python crear_sqlite.py
)
echo       Base de datos OK

REM --- Iniciar ---
echo [4/4] Iniciando ALBA Offline...
echo.
echo  ══════════════════════════════════════════
echo  ALBA estara disponible en:
echo  http://localhost:8080
echo.
echo  Modelos incluidos (no requieren descarga):
echo    LLM:   Gemma 4 E4B (audio nativo)
echo    TTS:   Pocket TTS (voz en espanol)
echo  100%% offline - sin internet requerido
echo  ══════════════════════════════════════════
echo.
echo  Presiona Ctrl+C para detener.
echo.

REM Abrir navegador despues de 4 segundos
start /b cmd /c "timeout /t 4 >nul && start http://localhost:8080"

REM Iniciar servidor
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8080