"""
ALBA Offline - Backend FastAPI principal.
Usa Gemma 4 E4B local en lugar de Gemini cloud.
"""
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routers import observatorio, prediccion, match, emprende, coach, simulacion, ia

app = FastAPI(
    title="ALBA Offline - Analitica Laboral Basada en IA",
    description="Version offline 100% local con Gemma 4 E4B",
    version="1.0.0-offline",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(observatorio.router)
app.include_router(prediccion.router)
app.include_router(match.router)
app.include_router(emprende.router)
app.include_router(coach.router)
app.include_router(simulacion.router)
app.include_router(ia.router)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


@app.get("/")
async def root():
    frontend_index = _FRONTEND_DIR / "index.html"
    if frontend_index.exists():
        return FileResponse(str(frontend_index))
    return {
        "proyecto": "ALBA Offline",
        "version": "1.0.0-offline",
        "modelo_llm": "Gemma 4 E4B (local)",
        "modelo_tts": "OmniVoice (local)",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    from app.services.llm_local import is_model_loaded
    from app.services.tts_local import is_tts_available
    from app.db.sqlite_db import list_tables
    return {
        "status": "ok",
        "mode": "offline",
        "llm_loaded": is_model_loaded(),
        "tts_available": is_tts_available(),
        "db_tables": len(list_tables()),
    }