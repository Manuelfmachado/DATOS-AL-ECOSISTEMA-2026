"""
Router Prediccion para ALBA Offline.
Sirve predicciones desde JSON pre-generado (Chronos T5 ya ejecutado en batch).
"""
import json
from pathlib import Path
from fastapi import APIRouter

router = APIRouter(prefix="/api/prediccion", tags=["prediccion"])

_PRED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
_PRED_FILE = _PRED_DIR / "predicciones_mundiales.json"

_data = None


def _load():
    global _data
    if _data is None and _PRED_FILE.exists():
        with open(_PRED_FILE, encoding="utf-8") as f:
            _data = json.load(f)
    return _data or {}


@router.get("/resumen")
async def resumen():
    d = _load()
    return {
        "modelo": d.get("modelo", "chronos-t5-small"),
        "horizontes": d.get("horizontes", {"5a": 5, "10a": 10}),
        "sectores": list(d.get("sectores", {}).keys()),
        "num_profesiones": len(d.get("profesiones", [])),
        "num_habilidades": len(d.get("habilidades", [])),
    }


@router.get("/sectores")
async def sectores():
    d = _load()
    return {"sectores": d.get("sectores", {})}


@router.get("/profesiones")
async def profesiones():
    d = _load()
    return {"profesiones": d.get("profesiones", [])}


@router.get("/habilidades")
async def habilidades():
    d = _load()
    return {"habilidades": d.get("habilidades", [])}


@router.get("/salarios")
async def salarios():
    d = _load()
    profs = sorted(
        d.get("profesiones", []),
        key=lambda x: x.get("salario_mensual_cop", 0),
        reverse=True,
    )
    return {"salarios": profs}