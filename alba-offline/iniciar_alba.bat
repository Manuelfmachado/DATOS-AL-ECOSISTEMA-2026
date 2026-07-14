@echo off
chcp 65001 >nul
title ALBA - Version Offline

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║         ALBA - Version Offline           ║
echo  ║   Analitica Laboral Basada en IA         ║
echo  ╚══════════════════════════════════════════╝
echo.

REM --- Verificar Python ---
echo [1/3] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no esta instalado.
    echo  Descarga Python 3.11+ desde: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
echo       Python OK

REM --- Instalar dependencias (una sola vez) ---
echo [2/3] Verificando dependencias...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo       Instalando dependencias (3-5 min, una sola vez)...
    pip install -r requirements.txt -q
    pip install pywebview -q
)
echo       Dependencias OK

REM --- Iniciar ALBA como ventana nativa ---
echo [3/3] Iniciando ALBA...
echo.
echo  Se abrira una ventana de ALBA automaticamente.
echo  Cierra la ventana cuando termines.
echo.

python alba_app.py