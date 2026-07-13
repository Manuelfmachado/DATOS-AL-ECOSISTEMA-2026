"""
ALBA - Analítica Laboral Basada en IA
Backend FastAPI principal.

Ejecutar:
    cd backend
    uvicorn app.main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import observatorio, prediccion, match, emprende, coach, coach_live, simulacion

app = FastAPI(
    title="ALBA - Analítica Laboral Basada en IA",
    description="Plataforma Nacional de Inteligencia Laboral para Colombia",
    version="1.0.0",
)

# CORS para permitir conexiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers de las 5 funciones
app.include_router(observatorio.router)
app.include_router(prediccion.router)
app.include_router(match.router)
app.include_router(emprende.router)
app.include_router(coach.router)
app.include_router(coach_live.router)
app.include_router(simulacion.router)


@app.get("/")
async def root():
    return {
        "proyecto": "ALBA - Analítica Laboral Basada en IA",
        "version": "1.0.0",
        "funciones": [
            "1. Observatorio Inteligente",
            "2. Predicción IA",
            "3. Match Inteligente",
            "4. Emprende IA",
            "5. Coach IA",
            "6. Simulación",
        ],
        "endpoints": {
            "observatorio": "/api/observatorio",
            "prediccion": "/api/prediccion",
            "match": "/api/match",
            "emprende": "/api/emprende",
            "coach": "/api/coach",
            "coach_live_ws": "/api/coach/live (WebSocket, Gemini Live API)",
            "simulacion": "/api/simulacion",
        },
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "ok", "message": "ALBA backend funcionando"}
