"""
Router Prediccion para ALBA Offline.
Sirve predicciones desde JSON pre-generado (Chronos T5 ya ejecutado en batch).
"""
import json
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException
from app.db.sqlite_db import query_sql
from app.data.ciuo_nombres import obtener_nombre_ciuo

router = APIRouter(prefix="/api/prediccion", tags=["prediccion"])

_PRED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed"
_PRED_FILE = _PRED_DIR / "predicciones_mundiales.json"
GEIH_SECTOR_PATH = _PRED_DIR / "geih_empleo_sector_mensual.csv"

_data = None


def _load():
    global _data
    if _data is None and _PRED_FILE.exists():
        with open(_PRED_FILE, encoding="utf-8") as f:
            _data = json.load(f)
    return _data or {}


def _macrosector_name(code: int) -> str:
    if code < 10: return "Agricultura y recursos"
    if code < 20: return "Alimentos y manufactura"
    if code < 30: return "Industria y tecnologia"
    if code < 40: return "Energia y agua"
    if code < 48: return "Construccion y comercio"
    if code < 54: return "Transporte y logistica"
    if code < 57: return "Alojamiento y comida"
    if code < 67: return "Informacion y finanzas"
    if code < 83: return "Servicios empresariales"
    return "Servicios publicos y sociales"


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


@router.get("/salarios-reales")
async def salarios_reales(limit: int = 50, ordenar_por: str = "empleo_total"):
    """Salarios reales por ocupacion (DANE GEIH) - mismo formato que la version online."""
    campos_validos = ["empleo_total", "salario_promedio", "salario_mediano"]
    if ordenar_por not in campos_validos:
        ordenar_por = "empleo_total"
    rows = query_sql(
        f"SELECT OFICIO_C8, salario_promedio, salario_mediano, empleo_total, "
        f"ocupados_muestra, periodo FROM geih_salario_ocupacion "
        f"ORDER BY {ordenar_por} DESC LIMIT ?",
        (limit,),
    )
    ocupaciones = []
    for row in rows or []:
        codigo = row.get("OFICIO_C8")
        ocupaciones.append({
            "oficio_codigo": codigo,
            "oficio_nombre": obtener_nombre_ciuo(codigo),
            "salario_promedio": round(float(row.get("salario_promedio") or 0), 0),
            "salario_mediano": round(float(row.get("salario_mediano") or 0), 0),
            "empleo_total": round(float(row.get("empleo_total") or 0), 0),
            "ocupados_muestra": int(row.get("ocupados_muestra") or 0),
            "periodo": row.get("periodo"),
        })
    return {
        "fuente": "DANE GEIH - Gran Encuesta Integrada de Hogares",
        "total_ocupaciones": len(ocupaciones),
        "periodo": ocupaciones[0]["periodo"] if ocupaciones else None,
        "ocupaciones": ocupaciones,
    }


@router.get("/todos-los-sectores")
async def todos_los_sectores():
    """Proyeccion de TODOS los macrosectores colombianos.

    Combina tendencia historica real del GEIH (2022-2026) con Chronos T5 baseline.
    Devuelve la misma forma que la version online (sector, empleo_actual, empleo_10y,
    variacion_10y_pct, serie) para que el frontend renderice sin errores.
    """
    if not GEIH_SECTOR_PATH.exists():
        raise HTTPException(status_code=503, detail="Datos GEIH no disponibles")

    df = pd.read_csv(GEIH_SECTOR_PATH)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    ci = df["rama_ciiu"].fillna(0).astype(int)
    df["macrosector"] = ci.apply(_macrosector_name)

    anual = df.groupby(["ano", "macrosector"]).agg(
        empleo=("empleo", "sum"), meses=("mes", "nunique")
    ).reset_index()
    anual["empleo_prom"] = anual["empleo"] / anual["meses"]

    meses_por_ano = df.groupby("ano")["mes"].nunique().to_dict()
    anios_completos = [a for a, m in meses_por_ano.items() if m >= 12]
    ultimo_ano_completo = max(anios_completos) if anios_completos else int(anual["ano"].max())
    ultimo_ano_crudo = int(anual["ano"].max())

    ultimo_periodo = df.sort_values(["ano", "mes"]).iloc[-1]
    ultimo_periodo_str = f"{int(ultimo_periodo['ano']):04d}-{int(ultimo_periodo['mes']):02d}"

    pred = _load()
    chronos_baseline = pred.get("salarios", {}).get("crecimiento_anual_pct", 3.5) / 100
    baseline_empleo = 0.018

    sectores = []
    for sec in sorted(anual["macrosector"].unique()):
        hist = anual[anual["macrosector"] == sec].sort_values("ano")

        serie_historica = [
            {"ano": int(row["ano"]), "empleo": int(round(row["empleo_prom"]))}
            for _, row in hist.iterrows()
            if int(row["ano"]) in anios_completos
        ]

        hist_completo = hist[hist["ano"].isin(anios_completos)].sort_values("ano")
        if len(hist_completo) >= 2:
            first = float(hist_completo.iloc[0]["empleo_prom"])
            last_base = float(hist_completo.iloc[-1]["empleo_prom"])
            years = int(hist_completo.iloc[-1]["ano"]) - int(hist_completo.iloc[0]["ano"])
            cagr = ((last_base / first) ** (1 / years) - 1) if years > 0 and first > 0 else 0
        else:
            last_base = float(hist.iloc[-1]["empleo_prom"])
            cagr = 0

        crec_blend = baseline_empleo + (cagr - baseline_empleo) * 0.20
        crec_blend = max(0.005, min(0.04, crec_blend))

        empleo_5y = last_base * ((1 + crec_blend) ** 5)
        empleo_10y = last_base * ((1 + crec_blend) ** 10)
        var_5y_pct = ((empleo_5y / last_base) - 1) * 100
        var_10y_pct = ((empleo_10y / last_base) - 1) * 100

        serie = list(serie_historica)
        for y in range(1, 11):
            fy = int(ultimo_ano_completo) + y
            val = float(last_base) * ((1 + crec_blend) ** y)
            serie.append({"ano": fy, "empleo": int(round(val)), "proyectado": True})

        sectores.append({
            "sector": str(sec),
            "empleo_actual": int(round(last_base)),
            "cagr_historico_pct": round(float(cagr) * 100, 1),
            "crecimiento_blend_pct": round(float(crec_blend) * 100, 1),
            "empleo_5y": int(round(empleo_5y)),
            "empleo_10y": int(round(empleo_10y)),
            "variacion_5y_pct": round(float(var_5y_pct), 1),
            "variacion_10y_pct": round(float(var_10y_pct), 1),
            "serie": serie,
        })

    return {
        "sectores": sorted(sectores, key=lambda s: -s["empleo_actual"]),
        "periodo_historico": f"{min(anios_completos)}-{max(anios_completos)}" if anios_completos else f"{int(anual['ano'].min())}-{ultimo_ano_completo}",
        "anio_base_proyeccion": ultimo_ano_completo,
        "ultimo_periodo": ultimo_periodo_str,
        "anio_actual_incompleto": ultimo_ano_crudo if ultimo_ano_crudo != ultimo_ano_completo else None,
        "chronos_baseline_pct": round(chronos_baseline * 100, 1),
        "baseline_empleo_pct": round(baseline_empleo * 100, 1),
        "metodologia": "80% crecimiento base del empleo en Colombia (1.8% anual) + 20% tendencia real GEIH. Proyeccion desde el ultimo ano completo disponible. Cap 0.5%-4% anual.",
    }