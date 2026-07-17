"""
ALBA Offline - Backend FastAPI principal.
Usa Qwen3.5-2B local en lugar de Gemini cloud.
Sirve el frontend React compilado (mismo que ALBA Online).
"""
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.routers import observatorio, prediccion, match, emprende, coach, simulacion, ia

app = FastAPI(
    title="ALBA Offline - Analitica Laboral Basada en IA",
    description="Version offline 100% local con Qwen3.5-2B",
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

# Servir archivos estaticos del frontend React compilado
if (_FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_FRONTEND_DIR / "assets")), name="assets")

# Servir archivos publicos del frontend (logo, geojson, dashboard.json, etc.)
if (_FRONTEND_DIR / "colombia-departments.geojson").exists():
    @app.get("/colombia-departments.geojson")
    async def geojson():
        return FileResponse(str(_FRONTEND_DIR / "colombia-departments.geojson"))

if (_FRONTEND_DIR / "colombia.geo.json").exists():
    @app.get("/colombia.geo.json")
    async def geo_json():
        return FileResponse(str(_FRONTEND_DIR / "colombia.geo.json"))

if (_FRONTEND_DIR / "dashboard.json").exists():
    @app.get("/dashboard.json")
    async def dashboard():
        return FileResponse(str(_FRONTEND_DIR / "dashboard.json"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

if (_FRONTEND_DIR / "logo-alba.png").exists():
    @app.get("/logo-alba.png")
    async def logo():
        return FileResponse(str(_FRONTEND_DIR / "logo-alba.png"))

if (_FRONTEND_DIR / "pcm-processor.js").exists():
    @app.get("/pcm-processor.js")
    async def pcm():
        return FileResponse(str(_FRONTEND_DIR / "pcm-processor.js"))


@app.get("/")
async def root():
    index = _FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {"proyecto": "ALBA Offline", "docs": "/docs"}


def _health_payload():
    from app.db.sqlite_db import list_tables
    from app.services.llm_local import GEMMA_MODEL_PATH
    import os
    model_name = os.path.basename(GEMMA_MODEL_PATH).replace(".gguf", "").replace("-GGUF", "")
    return {
        "status": "ok",
        "mode": "offline",
        "llm": model_name or "Qwen3.5-2B",
        "db_tables": len(list_tables()),
    }


@app.get("/health")
async def health():
    return _health_payload()


@app.get("/api/health")
async def api_health():
    return _health_payload()


# Catch-all para SPA routing (React Router)
@app.get("/{path:path}")
async def spa_fallback(path: str):
    # No interceptar API
    if path.startswith("api/") or path.startswith("assets/") or path.startswith("docs"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    index = _FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"error": "Not found"}, status_code=404)