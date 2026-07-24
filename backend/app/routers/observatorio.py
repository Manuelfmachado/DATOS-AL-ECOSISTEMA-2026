"""
Router del Observatorio Inteligente (Modulo #1).
Cruza GEIH + PILA + RUES + SNIES + SENA + SPE + DNP para responder:
  - Donde hay empleo y cuanto se gana (territorio)
  - Que sectores contratan mas (demanda)
  - Que se esta formando vs que se necesita (brecha oferta-demanda)
  - Como esta la gestion territorial (DNP)
  - Que ocupaciones crecen en demanda (SPE)
"""
import json
import unicodedata
from collections import defaultdict
from pathlib import Path
import pandas as pd
from fastapi import APIRouter, HTTPException, Query
from app.db.supabase import supabase
from app.data.ciuo_nombres import obtener_nombre_ciuo
from app.data.ciiu_nombres import obtener_nombre_ciiu
from app.data.divipola import (
    DEPARTAMENTOS_COLOMBIA,
    obtener_codigo_divipola,
    obtener_nombre_departamento,
)

router = APIRouter(prefix="/api/observatorio", tags=["observatorio"])

PREDICCIONES_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "predicciones_mundiales.json"


def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s


def _norm_depto(name: str) -> str:
    """Normaliza nombre de departamento para cruzar tablas con distintas denominaciones."""
    if not name:
        return ""
    s = _norm(name)
    # Casos especiales: el mismo departamento aparece con nombres distintos en distintas fuentes
    if "BOGOTA" in s or s == "BOGOTA":
        return "BOGOTA"
    if "SAN ANDRES" in s or "ARCHIPIELAGO" in s or "PROVIDENCIA" in s or "SANTA CATALINA" in s:
        return "ARCHIPIELAGO DE SAN ANDRES"
    if s == "GUAJIRA":
        return "LA GUAJIRA"
    if s == "NARINIO":
        return "NARINO"
    return s


def _dedup_filas(rows: list, key: str = "departamento") -> list:
    """Elimina filas duplicadas de una tabla de Supabase, conservando la primera
    ocurrencia de cada valor de `key`. Las tablas departamentales se cargaron
    multiples veces (insert sin upsert) y acumularon filas repetidas."""
    seen = set()
    out = []
    for r in rows or []:
        k = r.get(key)
        if k is None or k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def _dedup_sectores_geih(rows: list) -> list:
    """Deduplica filas de geih_empleo_sector_mensual por rama_ciiu.
    La tabla se cargo multiples veces (3x) acumulando filas repetidas por periodo.
    Agrega el nombre amigable del sector para no mostrar codigos CIIU al usuario."""
    seen = set()
    out = []
    for s in rows or []:
        rama = s.get("rama_ciiu")
        if rama is None or rama in seen:
            continue
        seen.add(rama)
        out.append({
            "rama_ciiu": rama,
            "rama_ciiu_nombre": obtener_nombre_ciiu(rama),
            "empleo": int(s.get("empleo") or 0),
            "salario_promedio": int(s.get("salario_promedio") or 0),
        })
    return out


def _dedup_pila(rows: list) -> list:
    """Deduplica filas de pila_resumen_sector por actividadeconomicadesc.
    La tabla se cargo multiples veces (4x) acumulando filas repetidas."""
    seen = set()
    out = []
    for r in rows or []:
        desc = r.get("actividadeconomicadesc")
        if not desc or desc in seen:
            continue
        seen.add(desc)
        out.append(r)
    return out


def _dedup_spe(rows: list) -> list:
    """Deduplica filas de spe_ape_inscritos_ocupacion por ocupacion.
    La tabla se cargo multiples veces (~4x) acumulando filas repetidas."""
    seen = set()
    out = []
    for r in rows or []:
        occ = r.get("ocupacion")
        if not occ or occ in seen:
            continue
        seen.add(occ)
        out.append(r)
    return out


def _ultimo_anio_rues(df) -> int:
    """Devuelve el ultimo anio valido de rues_empresas_nuevas.
    Filtra anos imposibles (>2030) que aparecen por errores de datos."""
    anios_validos = df[df["anio_matricula"] <= 2030]["anio_matricula"]
    return int(anios_validos.max()) if not anios_validos.empty else 0


# ============================================================================
# Endpoints legacy (mantenidos por compatibilidad con Dashboard y vistas previas)
# ============================================================================

@router.get("/departamentos")
async def get_resumen_departamentos():
    """Devuelve resumen laboral por departamento (GEIH + desempleo)."""
    try:
        ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        des = supabase.table("geih_desempleo_departamento").select("*").execute()
        df_ocu = pd.DataFrame(_dedup_filas(ocu.data))
        df_des = pd.DataFrame(_dedup_filas(des.data))
        if not df_ocu.empty and not df_des.empty:
            df = df_ocu.merge(df_des, on="departamento", how="outer")
        elif not df_ocu.empty:
            df = df_ocu
            df["no_ocupados"] = None
        else:
            return {"departamentos": []}
        df["tasa_desempleo"] = df.apply(
            lambda r: (r["no_ocupados"] / (r["no_ocupados"] + r["ocupados"]) * 100)
            if r.get("no_ocupados") and r.get("ocupados") and (r["no_ocupados"] + r["ocupados"]) > 0
            else None,
            axis=1,
        )
        departamentos = df.drop(columns=["id_x", "id_y", "created_at_x", "created_at_y"], errors="ignore").to_dict("records")
        return {"departamentos": departamentos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/departamentos/{departamento}")
async def get_departamento_detalle(departamento: str):
    """Detalle laboral de un departamento específico."""
    try:
        ocu = _dedup_filas(
            supabase.table("geih_resumen_departamento").select("*").eq("departamento", departamento.upper()).execute().data
        )
        des = _dedup_filas(
            supabase.table("geih_desempleo_departamento").select("*").eq("departamento", departamento.upper()).execute().data
        )
        if not ocu:
            raise HTTPException(status_code=404, detail=f"Departamento {departamento} no encontrado")
        data = ocu[0]
        if des:
            data["no_ocupados"] = des[0].get("no_ocupados")
            ocu_count = data.get("ocupados", 0)
            des_count = data.get("no_ocupados", 0)
            total = ocu_count + des_count
            data["tasa_desempleo"] = (des_count / total * 100) if total > 0 else None
        return {"departamento": data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/departamentos/{departamento}/sectores")
async def get_departamento_sectores(departamento: str, periodo: str = None):
    """Empleo por sector económico en un departamento (GEIH depto-sector, 95K registros).

    Datos oficiales del DANE: empleo desglosado por departamento y rama CIIU.
    """
    try:
        # Mapeo robusto via modulo divipola: maneja tildes y mayusculas
        depto_id = obtener_codigo_divipola(departamento)
        if depto_id is None:
            raise HTTPException(status_code=404, detail=f"Departamento '{departamento}' no encontrado")

        # Consultar empleo por sector
        query = supabase.table("geih_empleo_depto_sector").select("*").eq("dpto", depto_id)

        if not periodo:
            # Usar el periodo más reciente
            latest = supabase.table("geih_empleo_depto_sector").select("periodo").eq("dpto", depto_id).order("periodo", desc=True).limit(1).execute()
            if latest.data:
                query = query.eq("periodo", latest.data[0].get("periodo"))

        r = query.order("empleo", desc=True).limit(50).execute()

        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay datos de empleo por sector para {departamento}")

        # Procesar resultados y eliminar duplicados por rama_ciiu
        vistos = set()
        sectores = []
        for row in r.data:
            rama = row.get("rama_ciiu")
            if rama in vistos:
                continue
            vistos.add(rama)
            sectores.append({
                "rama_ciiu": rama,
                "rama_ciiu_nombre": obtener_nombre_ciiu(rama),
                "empleo": int(row.get("empleo") or 0),
                "periodo": row.get("periodo"),
            })

        return {
            "departamento": obtener_nombre_departamento(depto_id),
            "departamento_codigo": depto_id,
            "fuente": "DANE GEIH - Empleo por departamento y sector",
            "total_sectores": len(sectores),
            "periodo": sectores[0]["periodo"] if sectores else None,
            "sectores": sectores,
            "departamentos_disponibles": DEPARTAMENTOS_COLOMBIA,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectores-formales")
async def get_sectores_formales(limit: int = 50):
    """Top sectores por cotizantes formales (PILA)."""
    try:
        res = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(limit * 4).execute()
        # Deduplicar (la tabla tiene ~4x filas repetidas por cargas multiples)
        dedup = _dedup_pila(res.data)[:limit]
        return {"sectores": dedup}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectores-emergentes")
async def get_sectores_emergentes(limit: int = 20):
    """Sectores emergentes según creación de empresas (RUES)."""
    try:
        res = supabase.table("rues_top_sectores_nacional").select("*").order("empresas_activas", desc=True).limit(limit).execute()
        return {"sectores_emergentes": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/empresas-nuevas")
async def get_empresas_nuevas():
    """Empresas nuevas por año y sector (RUES)."""
    try:
        res = supabase.table("rues_empresas_nuevas").select("*").order("anio_matricula", desc=False).execute()
        return {"empresas_nuevas": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/camara/{camara}")
async def get_camara_detalle(camara: str):
    """Detalle de empresas activas por cámara de comercio."""
    try:
        res = supabase.table("rues_resumen_camara_ciiu").select("*").eq("camara_comercio", camara.upper()).order("empresas_activas", desc=True).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail=f"Cámara {camara} no encontrada")
        return {"camara": camara.upper(), "sectores": res.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 1. MAPA DE METRICAS (territorio)
# ============================================================================

@router.get("/mapa-metricas")
async def get_mapa_metricas():
    """Devuelve una fila por departamento con TODAS las metricas disponibles.
    Pensado para alimentar el mapa interactivo con selector de metrica."""
    try:
        # GEIH ocupado (5 filas por depto, promediamos)
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        # GEIH desempleo
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        # SNIES matriculados
        r_snies = supabase.table("snies_matriculados_departamento").select("*").execute()
        # DNP desempeno
        r_dnp = supabase.table("dnp_desempeno_departamento").select("*").execute()

        # Agregar GEIH por departamento (promedios ponderados por ocupados)
        agg = defaultdict(lambda: {
            "departamento": "",
            "ocupados": 0,
            "sum_ingreso_prom": 0.0,
            "sum_ingreso_med": 0.0,
            "sum_formalidad": 0.0,
            "sum_mujeres_ocu": 0.0,
            "sum_mujeres_cabeza": 0.0,
            "sum_edu_superior": 0.0,
            "n": 0,
            "no_ocupados": 0,
        })
        for row in _dedup_filas(r_ocu.data):
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_cabeza"] += row.get("mujeres_cabeza_hogar_pct") or 0
            agg[d]["sum_edu_superior"] += row.get("pct_educacion_superior") or 0
            agg[d]["n"] += 1
        for row in _dedup_filas(r_des.data):
            d = row["departamento"]
            if d in agg:
                agg[d]["no_ocupados"] += row.get("no_ocupados") or 0
            else:
                agg[d]["departamento"] = d
                agg[d]["no_ocupados"] = row.get("no_ocupados") or 0

        # Calcular promedios ponderados
        departamentos = []
        for d, a in agg.items():
            ocu = a["ocupados"] or 1
            departamentos.append({
                "departamento": d,
                "departamento_norm": _norm_depto(d),
                "ocupados": a["ocupados"],
                "no_ocupados": a["no_ocupados"],
                "tasa_desempleo": round(
                    a["no_ocupados"] / (a["no_ocupados"] + a["ocupados"]) * 100, 2
                ) if (a["no_ocupados"] + a["ocupados"]) > 0 else None,
                "ingreso_promedio": round(a["sum_ingreso_prom"] / ocu, 0) if a["ocupados"] else None,
                "ingreso_mediano": round(a["sum_ingreso_med"] / ocu, 0) if a["ocupados"] else None,
                "tasa_formalidad": round(a["sum_formalidad"] / ocu * 100, 2) if a["ocupados"] else None,
                "mujeres_pct": round(a["sum_mujeres_ocu"] / ocu * 100, 2) if a["ocupados"] and a["sum_mujeres_ocu"] > 0 else None,
                "tasa_ocupacion": round(
                    a["ocupados"] / (a["ocupados"] + a["no_ocupados"]) * 100, 2
                ) if (a["ocupados"] + a["no_ocupados"]) > 0 else None,
                "mujeres_cabeza_hogar_pct": round(a["sum_mujeres_cabeza"] / a["n"], 2) if a["n"] and a["sum_mujeres_cabeza"] > 0 else None,
                "pct_educacion_superior": round(a["sum_edu_superior"] / a["n"], 2) if a["n"] and a["sum_edu_superior"] > 0 else None,
            })

        # Agregar SNIES por depto normalizado
        snies_map = {}
        for row in _dedup_filas(r_snies.data):
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        # Agregar DNP por depto normalizado
        dnp_map = {}
        for row in _dedup_filas(r_dnp.data):
            key = _norm_depto(row["departamento"])
            dnp_map[key] = row.get("promedio_desempeno")
        for d in departamentos:
            d["dnp_desempeno"] = round(dnp_map[d["departamento_norm"]], 2) if dnp_map.get(d["departamento_norm"]) is not None else None

        return {"departamentos": departamentos, "total": len(departamentos)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/mapa-metricas-fast")
async def get_mapa_metricas_fast():
    """Version ligera del mapa de metricas sin extras opcionales, para el endpoint consolidado."""
    try:
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        r_snies = supabase.table("snies_matriculados_departamento").select("*").execute()
        r_dnp = supabase.table("dnp_desempeno_departamento").select("*").execute()

        agg = defaultdict(lambda: {
            "departamento": "",
            "ocupados": 0,
            "sum_ingreso_prom": 0.0,
            "sum_ingreso_med": 0.0,
            "sum_formalidad": 0.0,
            "sum_mujeres_ocu": 0.0,
            "sum_mujeres_cabeza": 0.0,
            "sum_edu_superior": 0.0,
            "n": 0,
            "no_ocupados": 0,
        })
        for row in _dedup_filas(r_ocu.data):
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_cabeza"] += row.get("mujeres_cabeza_hogar_pct") or 0
            agg[d]["sum_edu_superior"] += row.get("pct_educacion_superior") or 0
            agg[d]["n"] += 1
        for row in _dedup_filas(r_des.data):
            d = row["departamento"]
            if d in agg:
                agg[d]["no_ocupados"] += row.get("no_ocupados") or 0
            else:
                agg[d]["departamento"] = d
                agg[d]["no_ocupados"] = row.get("no_ocupados") or 0

        departamentos = []
        for d, a in agg.items():
            ocu = a["ocupados"] or 1
            departamentos.append({
                "departamento": d,
                "departamento_norm": _norm_depto(d),
                "ocupados": a["ocupados"],
                "no_ocupados": a["no_ocupados"],
                "tasa_desempleo": round(a["no_ocupados"] / (a["no_ocupados"] + a["ocupados"]) * 100, 2) if (a["no_ocupados"] + a["ocupados"]) > 0 else None,
                "ingreso_promedio": round(a["sum_ingreso_prom"] / ocu, 0) if a["ocupados"] else None,
                "ingreso_mediano": round(a["sum_ingreso_med"] / ocu, 0) if a["ocupados"] else None,
                "tasa_formalidad": round(a["sum_formalidad"] / ocu * 100, 2) if a["ocupados"] else None,
                "mujeres_pct": round(a["sum_mujeres_ocu"] / ocu * 100, 2) if a["ocupados"] and a["sum_mujeres_ocu"] > 0 else None,
                "tasa_ocupacion": round(a["ocupados"] / (a["ocupados"] + a["no_ocupados"]) * 100, 2) if (a["ocupados"] + a["no_ocupados"]) > 0 else None,
                "mujeres_cabeza_hogar_pct": round(a["sum_mujeres_cabeza"] / a["n"], 2) if a["n"] and a["sum_mujeres_cabeza"] > 0 else None,
                "pct_educacion_superior": round(a["sum_edu_superior"] / a["n"], 2) if a["n"] and a["sum_edu_superior"] > 0 else None,
            })

        snies_map = {}
        for row in _dedup_filas(r_snies.data):
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        dnp_map = {}
        for row in _dedup_filas(r_dnp.data):
            key = _norm_depto(row["departamento"])
            dnp_map[key] = row.get("promedio_desempeno")
        for d in departamentos:
            d["dnp_desempeno"] = round(dnp_map[d["departamento_norm"]], 2) if dnp_map.get(d["departamento_norm"]) is not None else None

        for d in departamentos:
            d.pop("departamento_norm", None)
            if d.get("tasa_formalidad") is not None:
                d["tasa_informalidad"] = round(100 - d["tasa_formalidad"], 2)

        sector_lider_nacional = None
        try:
            pred = _load_predicciones() or {}
            sectores_pred = pred.get("sectores", {})
            mejor_crec = -float("inf")
            for sector, info in sectores_pred.items():
                v2025 = info.get("historico", {}).get("valores", [0])[-1]
                v2035 = info.get("prediccion", {}).get("mediana", [0])[-1]
                crec = ((v2035 - v2025) / max(v2025, 0.01)) * 100 if v2025 else 0
                if crec > mejor_crec:
                    mejor_crec = crec
                    sector_lider_nacional = {"sector": sector, "crecimiento_2035_pct": round(crec, 1)}
        except Exception:
            pass

        return {"departamentos": departamentos, "total": len(departamentos), "sector_lider_nacional": sector_lider_nacional}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 1. MAPA DE METRICAS (territorio)
# ============================================================================

@router.get("/mapa-metricas")
async def get_mapa_metricas():
    """Devuelve una fila por departamento con TODAS las metricas disponibles.
    Pensado para alimentar el mapa interactivo con selector de metrica."""
    try:
        # GEIH ocupado (5 filas por depto, promediamos)
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        # GEIH desempleo
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        # SNIES matriculados
        r_snies = supabase.table("snies_matriculados_departamento").select("*").execute()
        # DNP desempeno
        r_dnp = supabase.table("dnp_desempeno_departamento").select("*").execute()

        # Agregar GEIH por departamento (promedios ponderados por ocupados)
        agg = defaultdict(lambda: {
            "departamento": "",
            "ocupados": 0,
            "sum_ingreso_prom": 0.0,
            "sum_ingreso_med": 0.0,
            "sum_formalidad": 0.0,
            "sum_mujeres_ocu": 0.0,
            "sum_mujeres_cabeza": 0.0,
            "sum_edu_superior": 0.0,
            "n": 0,
            "no_ocupados": 0,
        })
        for row in _dedup_filas(r_ocu.data):
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_cabeza"] += row.get("mujeres_cabeza_hogar_pct") or 0
            agg[d]["sum_edu_superior"] += row.get("pct_educacion_superior") or 0
            agg[d]["n"] += 1
        for row in _dedup_filas(r_des.data):
            d = row["departamento"]
            if d in agg:
                agg[d]["no_ocupados"] += row.get("no_ocupados") or 0
            else:
                agg[d]["departamento"] = d
                agg[d]["no_ocupados"] = row.get("no_ocupados") or 0

        # Calcular promedios ponderados
        departamentos = []
        for d, a in agg.items():
            ocu = a["ocupados"] or 1
            departamentos.append({
                "departamento": d,
                "departamento_norm": _norm_depto(d),
                "ocupados": a["ocupados"],
                "no_ocupados": a["no_ocupados"],
                "tasa_desempleo": round(
                    a["no_ocupados"] / (a["no_ocupados"] + a["ocupados"]) * 100, 2
                ) if (a["no_ocupados"] + a["ocupados"]) > 0 else None,
                "ingreso_promedio": round(a["sum_ingreso_prom"] / ocu, 0) if a["ocupados"] else None,
                "ingreso_mediano": round(a["sum_ingreso_med"] / ocu, 0) if a["ocupados"] else None,
                "tasa_formalidad": round(a["sum_formalidad"] / ocu * 100, 2) if a["ocupados"] else None,
                "mujeres_pct": round(a["sum_mujeres_ocu"] / ocu * 100, 2) if a["ocupados"] and a["sum_mujeres_ocu"] > 0 else None,
                "tasa_ocupacion": round(
                    a["ocupados"] / (a["ocupados"] + a["no_ocupados"]) * 100, 2
                ) if (a["ocupados"] + a["no_ocupados"]) > 0 else None,
                "mujeres_cabeza_hogar_pct": round(a["sum_mujeres_cabeza"] / a["n"], 2) if a["n"] and a["sum_mujeres_cabeza"] > 0 else None,
                "pct_educacion_superior": round(a["sum_edu_superior"] / a["n"], 2) if a["n"] and a["sum_edu_superior"] > 0 else None,
            })

        # Agregar SNIES por depto normalizado
        snies_map = {}
        for row in _dedup_filas(r_snies.data):
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        # Agregar DNP por depto normalizado
        dnp_map = {}
        for row in _dedup_filas(r_dnp.data):
            key = _norm_depto(row["departamento"])
            dnp_map[key] = row.get("promedio_desempeno")
        for d in departamentos:
            d["dnp_desempeno"] = round(dnp_map[d["departamento_norm"]], 2) if dnp_map.get(d["departamento_norm"]) is not None else None

        # Agregar mujeres cabeza de hogar y nivel educativo.
        # Estos datos vienen de etl_extras_geih.py que hace join con Caracteristicas generales.csv.
        # Se cargan a geih_resumen_departamento si las columnas existen en Supabase,
        # sino se leen del CSV local como fallback.
        extras_map = {}
        # Intentar leer de Supabase primero
        try:
            matching_rows_all = [r for r in _dedup_filas(r_ocu.data)]
            for r in matching_rows_all:
                key = _norm_depto(r.get("departamento", ""))
                muj = r.get("mujeres_cabeza_hogar_pct")
                edu = r.get("pct_educacion_superior")
                etiqueta = r.get("nivel_educativo_etiqueta")
                if muj is not None or edu is not None:
                    extras_map[key] = {
                        "mujeres_cabeza_hogar_pct": round(muj, 1) if muj is not None else None,
                        "pct_educacion_superior": round(edu, 1) if edu is not None else None,
                        "nivel_educativo_etiqueta": etiqueta,
                    }
        except Exception:
            pass

        # Fallback: leer del CSV local si Supabase no tiene las columnas
        if not extras_map:
            extras_path = Path(__file__).resolve().parents[2] / "data" / "processed" / "geih_extras_departamento.csv"
            if extras_path.exists():
                try:
                    df_extras = pd.read_csv(extras_path)
                    for _, row in df_extras.iterrows():
                        key = _norm_depto(str(row.get("departamento", "")))
                        extras_map[key] = {
                            "mujeres_cabeza_hogar_pct": round(float(row["mujeres_cabeza_hogar_pct"]), 1) if pd.notna(row.get("mujeres_cabeza_hogar_pct")) else None,
                            "pct_educacion_superior": round(float(row["pct_educacion_superior"]), 1) if pd.notna(row.get("pct_educacion_superior")) else None,
                            "nivel_educativo_etiqueta": str(row["nivel_educativo_etiqueta"]) if pd.notna(row.get("nivel_educativo_etiqueta")) else None,
                        }
                except Exception:
                    pass

        for d in departamentos:
            d_norm = d.get("departamento_norm")
            extra = extras_map.get(d_norm)
            if extra:
                d["mujeres_cabeza_hogar_pct"] = extra.get("mujeres_cabeza_hogar_pct")
                d["pct_educacion_superior"] = extra.get("pct_educacion_superior")
                d["nivel_educativo_etiqueta"] = extra.get("nivel_educativo_etiqueta")
            else:
                d["mujeres_cabeza_hogar_pct"] = None
                d["pct_educacion_superior"] = None
                d["nivel_educativo_etiqueta"] = None

        # Eliminar campo auxiliar
        for d in departamentos:
            d.pop("departamento_norm", None)

        # Calcular tasa de informalidad (complemento de la formalidad)
        for d in departamentos:
            if d.get("tasa_formalidad") is not None:
                d["tasa_informalidad"] = round(100 - d["tasa_formalidad"], 2)
            else:
                d["tasa_informalidad"] = None

        # Determinar el sector con mayor crecimiento proyectado a nivel nacional
        sector_lider_nacional = None
        try:
            pred = _load_predicciones() or {}
            sectores_pred = pred.get("sectores", {})
            mejor_crec = -float("inf")
            for sector, info in sectores_pred.items():
                v2025 = info.get("historico", {}).get("valores", [0])[-1]
                v2035 = info.get("prediccion", {}).get("mediana", [0])[-1]
                crec = ((v2035 - v2025) / max(v2025, 0.01)) * 100 if v2025 else 0
                if crec > mejor_crec:
                    mejor_crec = crec
                    sector_lider_nacional = {
                        "sector": sector,
                        "crecimiento_2035_pct": round(crec, 1),
                    }
        except Exception:
            pass

        return {
            "departamentos": departamentos,
            "total": len(departamentos),
            "sector_lider_nacional": sector_lider_nacional,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 2. BRECHA OFERTA EDUCATIVA vs DEMANDA LABORAL
# ============================================================================

# Mapeo de nucleo_conocimiento (SNIES) -> categoria macro
# IMPORTANTE: el orden del diccionario importa porque _categoria_nucleo hace
# coincidencia de substring y devuelve el primer match.
# TECNOLOGIA va ANTES que INGENIERIAS para que "Ingeniería de Sistemas" (el
# programa de tecnología más grande de Colombia) caiga en TECNOLOGIA y no en
# INGENIERIAS. Las ingenierías tradicionales (civil, mecánica) no tienen las
# keywords de TECNOLOGIA, así que seguirán en INGENIERIAS correctamente.
# Se evitan keywords demasiado cortas (ej. "IA") que producen falsos positivos.
_NUCLEO_TO_CAT = {
    "SALUD": ["MEDICINA", "ENFERMERIA", "ODONTOLOGIA", "FARMACIA", "BACTERIOLOGIA",
              "NUTRICION", "OPTOMETRIA", "FISIOTERAPIA", "TERAPIA OCUPACIONAL",
              "PSICOLOGIA", "SALUD PUBLICA", "REGULACION SANITARIA",
              "MEDIO AMBIENTE SANITARIO", "INSTRUMENTACION QUIRURGICA",
              "TERAPIA RESPIRATORIA", "GERONTOLOGIA", "SALUD OCUPACIONAL",
              "FONOAUDIOLOGIA", "SALUD"],
    "TECNOLOGIA": ["INGENIERIA DE SISTEMAS", "INGENIERIA DE SOFTWARE",
                   "INGENIERIA INFORMATICA", "INGENIERIA DE DATOS",
                   "INGENIERIA DE TELECOMUNICACIONES",
                   "TELEMATICA", "SOFTWARE", "CIBERSEGURIDAD",
                   "INTELIGENCIA ARTIFICIAL", "TELECOMUNICACION",
                   "INFORMATICA", "COMPUTACION", "CIENCIA DE DATOS",
                   "DESARROLLO DE SOFTWARE", "SISTEMAS DE INFORMACION",
                   "REDES DE COMPUTADORES", "DATOS",
                   "SISTEMAS", "MULTIMEDIA", "TECNOLOG"],
    "INGENIERIAS": ["INGENIERIA", "ARQUITECTURA", "AGROINDUSTRIAL", "BIOMEDICA",
                    "BIOTECNOLOGIA", "METALURGIA", "AUTOMOTRIZ",
                    "CONSTRUCCION", "TOPOGRAFIA", "SANEAMIENTO",
                    "HIDRAULICA", "GEOLOGIA", "MINAS", "PETROLEO", "NAVAL"],
    "AGROPECUARIO": ["AGRONOMIA", "ZOOTECNIA", "VETERINARIA",
                     "FORESTAL", "PESQUERA", "ACUICULTURA"],
    "CIENCIAS_BASICAS": ["MATEMATICAS", "ESTADISTICA", "BIOQUIMICA",
                         "MICROBIOLOGIA", "FISICA", "QUIMICA", "BIOLOGIA",
                         "ECOLOGIA", "OCEANOGRAFIA"],
    "ADMINISTRACION": ["ADMINISTRACION", "ECONOMIA", "CONTADURIA", "FINANZAS",
                       "NEGOCIOS", "MERCADEO", "MARKETING", "PUBLICIDAD",
                       "COMERCIO EXTERIOR", "LOGISTICA", "TURISMO",
                       "HOTELERIA", "GASTRONOMIA", "COMERCIO",
                       "GERENCIA", "RELACIONES INDUSTRIALES"],
    "EDUCACION": ["EDUCACION", "LICENCIATURA", "PEDAGOGIA",
                  "FILOSOFIA", "TEOLOGIA", "HISTORIA", "LINGUISTICA",
                  "LENGUAS MODERNAS", "IDIOMAS", "ESPAÑOL", "TRABAJO SOCIAL"],
    "DERECHO": ["DERECHO", "JURISPRUDENCIA", "POLITICA", "CIENCIA POLITICA",
                "RELACIONES INTERNACIONALES", "ESTUDIOS POLITICOS"],
    "GOBIERNO": ["GOBIERNO", "MILITAR", "POLICIAL", "DEFENSA",
                 "SEGURIDAD Y DEFENSA", "CAMPO MILITAR", "FUERZAS MILITARES"],
    "ARTES": ["ARTES PLASTICAS", "BELLAS ARTES", "MUSICA", "TEATRO",
              "DANZA", "CINE", "COMUNICACION SOCIAL", "COMUNICACION AUDIOVISUAL",
              "LITERATURA", "FOTOGRAFIA", "AUDIOVISUAL", "ANIMACION",
              "PERIODISMO", "DISENO GRAFICO", "DISENO INDUSTRIAL",
              "COMUNICACION VISUAL", "ARTES", "DISENO", "DISENIO", "DISEÑO"],
    "COMUNICACION": ["LENGUAJES", "LINGÜISTICA", "COMUNICACION"],
}

# Mapeo de CIIU 2 digitos -> categoria macro
# Debe cubrir todos los códigos con peso en PILA para que no caigan en OTROS
# (antes el 19% de la demanda quedaba sin clasificar, distorsionando la brecha).
_CIIU_TO_CAT = {
    # Agropecuario
    "01": "AGROPECUARIO", "02": "AGROPECUARIO", "03": "AGROPECUARIO",
    "05": "AGROPECUARIO", "07": "AGROPECUARIO", "08": "AGROPECUARIO", "09": "AGROPECUARIO",
    # Ingenierías: industria manufacturera + construcción + técnicas
    "10": "INGENIERIAS", "11": "INGENIERIAS", "12": "INGENIERIAS",
    "13": "INGENIERIAS", "14": "INGENIERIAS", "15": "INGENIERIAS",
    "16": "INGENIERIAS", "17": "INGENIERIAS", "18": "INGENIERIAS", "19": "INGENIERIAS",
    "20": "INGENIERIAS", "21": "INGENIERIAS", "22": "INGENIERIAS", "23": "INGENIERIAS",
    "24": "INGENIERIAS", "25": "INGENIERIAS", "26": "INGENIERIAS", "27": "INGENIERIAS",
    "28": "INGENIERIAS", "29": "INGENIERIAS", "30": "INGENIERIAS", "31": "INGENIERIAS",
    "32": "INGENIERIAS", "33": "INGENIERIAS", "41": "INGENIERIAS", "42": "INGENIERIAS",
    "43": "INGENIERIAS", "71": "INGENIERIAS",
    # Electricidad, gas, agua y saneamiento -> Ingenierías (civil/ambiental)
    "35": "INGENIERIAS", "36": "INGENIERIAS", "37": "INGENIERIAS", "38": "INGENIERIAS", "39": "INGENIERIAS",
    # Tecnología / Informática
    "61": "TECNOLOGIA", "62": "TECNOLOGIA", "63": "TECNOLOGIA", "95": "TECNOLOGIA",
    # Salud
    "75": "SALUD", "86": "SALUD", "87": "SALUD", "88": "SALUD",
    # Educación
    "85": "EDUCACION",
    # Comercio (al por mayor, menor, vehiculos)
    "45": "ADMINISTRACION", "46": "ADMINISTRACION", "47": "ADMINISTRACION",
    # Alojamiento y servicios de comida
    "55": "ADMINISTRACION", "56": "ADMINISTRACION",
    # Finanzas y seguros
    "64": "ADMINISTRACION", "65": "ADMINISTRACION", "66": "ADMINISTRACION",
    # Actividades inmobiliarias -> Administracion
    "68": "ADMINISTRACION",
    # Actividades juridicas y de contabilidad -> DERECHO (antes mal mapeadas a Administracion)
    "69": "DERECHO",
    # Oficinas principales, consultoria, publicidad -> Administracion
    "70": "ADMINISTRACION", "73": "ADMINISTRACION",
    # Actividades de alquiler y agencias de viaje -> Administracion
    "77": "ADMINISTRACION", "79": "ADMINISTRACION",
    # Otros servicios personales y hogares como empleadores
    "94": "ADMINISTRACION", "96": "ADMINISTRACION", "97": "ADMINISTRACION", "98": "ADMINISTRACION", "99": "ADMINISTRACION",
    # Artes / Comunicación / Diseño / Entretenimiento
    "58": "ARTES", "59": "ARTES", "60": "ARTES", "90": "ARTES", "91": "ARTES", "93": "ARTES",
    # Ciencias básicas e investigación
    "72": "CIENCIAS_BASICAS", "74": "CIENCIAS_BASICAS",
    # Transporte y logística -> Administración (programas de logística caen bajo Administración/Comercio)
    "49": "ADMINISTRACION", "50": "ADMINISTRACION", "51": "ADMINISTRACION",
    "52": "ADMINISTRACION", "53": "ADMINISTRACION",
    # Gobierno y seguridad (administración pública, defensa, seguridad privada)
    "80": "GOBIERNO", "81": "GOBIERNO", "82": "GOBIERNO", "84": "GOBIERNO",
    # Actividades de empleo/servicios de apoyo -> Administración
    "78": "ADMINISTRACION",
}

# Mapeo CIIU -> sub-categoria (para desglosar el antiguo "OTROS" en grupos mas especificos)
# Solo aplica a CIIUs que NO tienen match en _CIIU_TO_CAT (los que estaban cayendo a OTROS).
_CIIU_SUBGRUPO = {
    # Agropecuario, silvicultura, pesca
    "1": "AGROPECUARIO", "2": "AGROPECUARIO",
    "3": "AGROPECUARIO", "4": "AGROPECUARIO",
    # Mineria y extraccion
    "5": "MINAS", "6": "MINAS", "7": "MINAS", "8": "MINAS", "9": "MINAS",
    # Otros codigos sin categoria formativa especifica
    "34": "OTROS_INDUSTRIA", "40": "OTROS_INDUSTRIA",
    "44": "OTROS_INDUSTRIA", "48": "OTROS_INDUSTRIA",
    "54": "OTROS_INDUSTRIA", "57": "OTROS_INDUSTRIA",
    "67": "OTROS_INDUSTRIA", "76": "OTROS_INDUSTRIA",
    "83": "OTROS_INDUSTRIA", "89": "OTROS_INDUSTRIA",
    "92": "OTROS_INDUSTRIA",
}


def _categoria_nucleo(nucleo: str) -> str:
    n = _norm(nucleo)
    for cat, keywords in _NUCLEO_TO_CAT.items():
        for kw in keywords:
            if kw in n:
                return cat
    return "OTROS"


def _categoria_ciiu(ciiu_code: str) -> str:
    """Mapea un codigo CIIU a una macro-categoria.
    Primero intenta con la tabla principal (_CIIU_TO_CAT).
    Si no hay match, cae a una sub-categoria mas especifica (manufactura, minas, etc.)
    para que el 'OTROS' residual sea minimo y util para el usuario.
    Acepta int, float (ej. 1.0), str numerico ('1', '01', '0110')."""
    # Normalizar a entero para manejar floats como 1.0 -> "1" (no "1.")
    try:
        code_int = int(float(str(ciiu_code).strip()))
        code = str(code_int)
    except (ValueError, TypeError):
        return "OTROS"
    if len(code) >= 1 and code.isdigit():
        cat = _CIIU_TO_CAT.get(code)
        if cat:
            return cat
        return _CIIU_SUBGRUPO.get(code, "OTROS")
    return "OTROS"


@router.get("/brecha")
async def get_brecha_oferta_demanda():
    """Brecha entre formación (SNIES) y empleo real (GEIH, no PILA).
    Retorna categorias con su share en oferta y demanda, e indice de desajuste."""
    try:
        return _calcular_brecha_oferta_demanda()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 3. DNP - Desempeno territorial
# ============================================================================

@router.get("/dnp")
async def get_dnp_desempeno(limit: int = Query(default=33, ge=1, le=33)):
    """Devuelve desempeno municipal promedio por departamento (DNP MDM)."""
    try:
        r = (
            supabase.table("dnp_desempeno_departamento")
            .select("*")
            .order("promedio_desempeno", desc=True)
            .limit(limit)
            .execute()
        )
        return {"dnp": r.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 4. SPE - Demanda de ocupaciones
# ============================================================================

@router.get("/spe-demanda")
async def get_spe_demanda(limit: int = Query(default=20, ge=1, le=100)):
    """Ocupaciones con mayor variacion positiva de inscritos (senal de demanda creciente).
    Si variacion_pct es null, ordena por inscritos_2020 desc como proxy de demanda absoluta."""
    try:
        # Intentar ordenar por variacion_pct primero
        try:
            r = (
                supabase.table("spe_ape_inscritos_ocupacion")
                .select("*")
                .order("variacion_pct", desc=True, nullsfirst=False)
                .limit(limit * 4)
                .execute()
            )
            rows = _dedup_spe(r.data or [])
            con_var = [x for x in rows if x.get("variacion_pct") is not None]
            if len(con_var) < limit:
                restantes = limit - len(con_var)
                r2 = (
                    supabase.table("spe_ape_inscritos_ocupacion")
                    .select("*")
                    .order("inscritos_2020", desc=True)
                    .limit((restantes + 50) * 4)
                    .execute()
                )
                rows2 = _dedup_spe(r2.data or [])
                occ_vistos = {x["ocupacion"] for x in con_var}
                extras = [x for x in rows2 if x["ocupacion"] not in occ_vistos][:restantes]
                rows = con_var + extras
            else:
                rows = con_var[:limit]
        except Exception:
            r = (
                supabase.table("spe_ape_inscritos_ocupacion")
                .select("*")
                .order("inscritos_2020", desc=True)
                .limit(limit * 4)
                .execute()
            )
            rows = _dedup_spe(r.data or [])[:limit]
        return {"ocupaciones_demanda_creciente": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 5. Detalle por departamento (consolidado)
# ============================================================================

@router.get("/detalle/{departamento}")
async def get_detalle_departamento(departamento: str):
    """Detalle consolidado de un departamento: mercado laboral + formacion + desempeno."""
    try:
        depto_norm = _norm_depto(departamento)

        # Mercado laboral
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        r_snies = supabase.table("snies_matriculados_departamento").select("*").execute()
        r_dnp = supabase.table("dnp_desempeno_departamento").select("*").execute()
        r_sena = supabase.table("sena_programas_activos").select("programa, area_desempeno, duracion_horas").eq("departamento", departamento.upper()).limit(50).execute()

        # Filtrar GEIH por depto
        ocu_rows = [r for r in _dedup_filas(r_ocu.data) if _norm_depto(r["departamento"]) == depto_norm]
        des_rows = [r for r in _dedup_filas(r_des.data) if _norm_depto(r["departamento"]) == depto_norm]

        if not ocu_rows:
            raise HTTPException(status_code=404, detail=f"Departamento {departamento} no encontrado")

        ocupados = sum(r.get("ocupados") or 0 for r in ocu_rows)
        no_ocupados = sum(r.get("no_ocupados") or 0 for r in des_rows) if des_rows else 0
        total = ocupados + no_ocupados

        # Promedios ponderados
        ingreso_prom = sum((r.get("ingreso_promedio") or 0) * (r.get("ocupados") or 0) for r in ocu_rows) / max(ocupados, 1)
        ingreso_med = sum((r.get("ingreso_mediano") or 0) * (r.get("ocupados") or 0) for r in ocu_rows) / max(ocupados, 1)
        formalidad = sum((r.get("tasa_formalidad") or 0) * (r.get("ocupados") or 0) for r in ocu_rows) / max(ocupados, 1)
        mujeres = sum((r.get("mujeres_pct") or 0) * (r.get("ocupados") or 0) for r in ocu_rows) / max(ocupados, 1)

        # Formacion
        snies_row = next((r for r in _dedup_filas(r_snies.data) if _norm_depto(r["departamento"]) == depto_norm), None)
        dnp_row = next((r for r in _dedup_filas(r_dnp.data) if _norm_depto(r["departamento"]) == depto_norm), None)

        # Top areas SENA en este depto
        sena_areas = defaultdict(int)
        for row in r_sena.data:
            a = _norm(row.get("area_desempeno", ""))
            if a:
                sena_areas[a] += 1
        top_sena = sorted(sena_areas.items(), key=lambda x: -x[1])[:5]

        return {
            "departamento": departamento.upper(),
            "mercado_laboral": {
                "ocupados": ocupados,
                "no_ocupados": no_ocupados,
                "tasa_desempleo": round(no_ocupados / total * 100, 2) if total else None,
                "tasa_ocupacion": round(ocupados / total * 100, 2) if total else None,
                "ingreso_promedio": round(ingreso_prom, 0),
                "ingreso_mediano": round(ingreso_med, 0),
                "tasa_formalidad": round(formalidad * 100, 2),
                "mujeres_pct": round(mujeres * 100, 2),
            },
            "formacion": {
                "matriculados_snies": round(snies_row.get("matriculados", 0), 0) if snies_row else 0,
                "programas_sena_muestra": len(r_sena.data),
                "top_areas_sena": [{"area": a, "programas": c} for a, c in top_sena],
            },
            "gestion_territorial": {
                "dnp_desempeno": round(dnp_row.get("promedio_desempeno", 0), 2) if dnp_row else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 7. Insights por departamento (aproximación para Dashboard interactivo)
# ============================================================================

def _load_predicciones():
    if not PREDICCIONES_PATH.exists():
        return None
    with open(PREDICCIONES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/departamento-insights/{departamento}")
async def get_departamento_insights(departamento: str):
    """Devuelve profesiones y sectores destacados para un departamento
    usando datos claros y comprensibles para el ciudadano promedio.

    - Profesiones con más desempleo: ordenadas por crecimiento negativo proyectado
      (cuanto más negativo, más difícil conseguir empleo).
    - Profesiones más demandadas: ordenadas por crecimiento positivo proyectado
      (cuanto más positivo, más fácil conseguir empleo).
    - Sectores con mayor crecimiento: cambio porcentual de participación proyectado.
    """
    try:
        depto_norm = _norm_depto(departamento)

        # Datos del departamento
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        ocu_rows = [r for r in _dedup_filas(r_ocu.data) if _norm_depto(r.get("departamento", "")) == depto_norm]
        des_rows = [r for r in _dedup_filas(r_des.data) if _norm_depto(r.get("departamento", "")) == depto_norm]

        ocupados = sum(r.get("ocupados") or 0 for r in ocu_rows)
        no_ocupados = sum(r.get("no_ocupados") or 0 for r in des_rows)
        total = ocupados + no_ocupados
        tasa_desempleo = (no_ocupados / total * 100) if total else 10.0
        ingreso_prom = sum((r.get("ingreso_promedio") or 0) * (r.get("ocupados") or 0) for r in ocu_rows) / max(ocupados, 1)

        pred = _load_predicciones() or {}
        profesiones = pred.get("profesiones", [])
        sectores_raw = pred.get("sectores", {})

        # Factor local: compara el depto con el promedio nacional (~10% desempleo, ~2.5M ingreso)
        factor_desempleo_local = max(0.5, tasa_desempleo / 10.0)  # 10% = factor 1.0
        factor_ingreso_local = max(0.5, ingreso_prom / 2_500_000)  # 2.5M = factor 1.0

        # Profesiones con más desempleo / dificultad.
        # El score base se ajusta por el desempleo real del departamento:
        # un depto con 20% de desempleo hace TODAS las profesiones mas dificiles.
        def _score_dificultad(p):
            crec = p.get("crecimiento_5a_pct", 0)
            demanda = p.get("demanda", "media")
            salario = p.get("salario_mensual_cop", 2_500_000)
            # Base por demanda: baja = 55, media = 28, alta = 10
            base = {"baja": 55, "media": 28, "alta": 10}.get(demanda, 28)
            # Penalizacion por crecimiento negativo
            penalizacion = max(0, -crec) * 6
            # Profesiones de bajo salario son mas vulnerables al desempleo local
            vulnerabilidad_salario = 1.3 if salario < 2_500_000 else 1.0
            score = (base + penalizacion) * factor_desempleo_local * vulnerabilidad_salario
            return min(99, max(15, round(score)))

        profesiones_desempleo = sorted(
            [
                {
                    "profesion": p["profesion"],
                    "riesgo_desempleo": _score_dificultad(p),
                    "crecimiento_5a_pct": round(p.get("crecimiento_5a_pct", 0), 1),
                }
                for p in profesiones
                if p.get("demanda") == "baja" or p.get("crecimiento_5a_pct", 0) < 0
            ],
            key=lambda x: -x["riesgo_desempleo"],
        )[:5]

        # Profesiones más demandadas: crecimiento ajustado por ingreso del departamento.
        # Deptos de altos ingresos: mas demanda para tech/datos/finanzas.
        # Deptos de bajos ingresos: mas demanda relativa para oficios/agro/salud.
        def _score_demanda(p):
            crec = p.get("crecimiento_5a_pct", 0)
            salario = p.get("salario_mensual_cop", 2_500_000)
            if salario > 5_000_000:
                # Profesiones de alta calificacion: se potencian en deptos ricos
                ajuste = 0.6 + factor_ingreso_local * 0.5
            elif salario < 2_500_000:
                # Profesiones de baja calificacion: mas relevantes en deptos pobres
                ajuste = 1.4 - factor_ingreso_local * 0.3
            else:
                # Profesiones medias: ajuste suave
                ajuste = 1.0 + (factor_ingreso_local - 1.0) * 0.2
            return round(crec * ajuste, 1)

        profesiones_demanda = sorted(
            [
                {
                    "profesion": p["profesion"],
                    "demanda_score": _score_demanda(p),
                }
                for p in profesiones
                if p.get("crecimiento_5a_pct", 0) > 0
            ],
            key=lambda x: -x["demanda_score"],
        )[:5]

        # Sectores con mayor crecimiento: el crecimiento se ajusta por el desempleo local.
        # Deptos con alto desempleo pueden ver crecimientos relativos mayores en sectores
        # que estan recuperandose, porque parten de una base mas baja.
        sectores = []
        for sector, info in sectores_raw.items():
            v2025 = info.get("historico", {}).get("valores", [0])[-1]
            v2035 = info.get("prediccion", {}).get("mediana", [0])[-1]
            crec = ((v2035 - v2025) / max(v2025, 0.01)) * 100 if v2025 else 0
            # Ajuste: en deptos con alto desempleo, los sectores en crecimiento
            # tienen mayor impacto relativo (mas recuperación posible)
            crec_ajustado = crec * (0.7 + factor_desempleo_local * 0.4)
            sectores.append({
                "sector": sector,
                "crecimiento_2035_pct": round(crec_ajustado, 1),
                "participacion_2025": round(v2025, 1),
                "participacion_2035": round(v2035, 1),
            })
        sectores = sorted(sectores, key=lambda x: -x["crecimiento_2035_pct"])[:5]

        return {
            "departamento": departamento.upper(),
            "tasa_desempleo": round(tasa_desempleo, 1),
            "ingreso_promedio": round(ingreso_prom, 0),
            "profesiones_mas_desempleo": profesiones_desempleo,
            "profesiones_mas_demandadas": profesiones_demanda,
            "sectores_mayor_crecimiento": sectores,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 6. Resumen ejecutivo nacional (KPIs para Dashboard)
# ============================================================================

@router.get("/resumen-nacional")
async def get_resumen_nacional():
    """KPIs nacionales del ultimo mes disponible (GEIH real, 52 meses)."""
    try:
        r = supabase.table("geih_resumen_nacional").select("*").order("ano", desc=True).order("mes", desc=True).limit(1).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="No hay datos de GEIH")
        ultima = r.data[0]
        # Top sectores por empleo del ultimo mes (top 21 = todos los sectores CIIU de 2 digitos)
        periodo = ultima.get("periodo")
        r_sec = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("empleo", desc=True).limit(50).execute()
        empleo_raw = int(ultima.get("empleo_nacional") or 0)
        pea = int(ultima.get("pea_nacional") or 0)
        desempleados = int(ultima.get("desempleados_nacional") or 0)
        # Corregir incoherencia: si empleo > PEA, calcular ocupados como PEA - desempleados
        if pea > 0 and empleo_raw > pea:
            empleo = pea - desempleados
        else:
            empleo = empleo_raw
        # Recalcular tasa de ocupación de forma coherente
        tasa_ocupacion = round((pea - desempleados) / pea * 100, 2) if pea > 0 else None
        return {
            "periodo": periodo,
            "tasa_desempleo_nacional": ultima.get("tasa_desempleo_nacional"),
            "empleo_nacional": empleo,
            "salario_promedio_nacional": int(ultima.get("salario_promedio_nacional") or 0),
            "tasa_informalidad_nacional": ultima.get("tasa_informalidad_nacional"),
            "pea_nacional": pea,
            "ocupados_totales": empleo,
            "desocupados_totales": desempleados,
            "tasa_ocupacion_nacional": tasa_ocupacion,
            "ingreso_promedio_nacional": int(ultima.get("salario_promedio_nacional") or 0),
            "top_sectores_empleo": _dedup_sectores_geih(r_sec.data),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/serie-desempleo")
async def get_serie_desempleo():
    """Serie temporal de desempleo nacional (52 puntos mensuales 2022-2026)."""
    try:
        r = supabase.table("geih_resumen_nacional").select("periodo,ano,mes,tasa_desempleo_nacional,empleo_nacional,salario_promedio_nacional,tasa_informalidad_nacional").order("ano", desc=False).order("mes", desc=False).execute()
        return {
            "total_puntos": len(r.data),
            "serie": [
                {
                    "periodo": row.get("periodo"),
                    "tasa_desempleo": row.get("tasa_desempleo_nacional"),
                    "empleo": int(row.get("empleo_nacional") or 0),
                    "salario_promedio": int(row.get("salario_promedio_nacional") or 0),
                    "tasa_informalidad": row.get("tasa_informalidad_nacional"),
                }
                for row in r.data if row.get("tasa_desempleo_nacional") is not None
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/desempleo-departamental/{periodo}")
async def get_desempleo_depto_periodo(periodo: str):
    """Desempleo por departamento para un periodo especifico (ej: 2026-04)."""
    try:
        r = supabase.table("geih_desempleo_mensual").select("*").eq("periodo", periodo).order("tasa", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay datos para periodo {periodo}")
        return {
            "periodo": periodo,
            "departamentos": [
                {"dpto": row.get("dpto"), "pea": int(row.get("pea") or 0), "desempleados": int(row.get("desempleados") or 0), "tasa": row.get("tasa")}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/empleo-sector/{periodo}")
async def get_empleo_sector_periodo(periodo: str):
    """Empleo y salario por sector CIIU para un periodo especifico."""
    try:
        r = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("empleo", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay datos para periodo {periodo}")
        return {
            "periodo": periodo,
            "sectores": [
                {"rama_ciiu": row.get("rama_ciiu"), "empleo": int(row.get("empleo") or 0), "salario_promedio": int(row.get("salario_promedio") or 0)}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/informalidad/{periodo}")
async def get_informalidad_periodo(periodo: str):
    """Tasa de informalidad por departamento para un periodo especifico."""
    try:
        r = supabase.table("geih_informalidad_mensual").select("*").eq("periodo", periodo).order("tasa_informalidad", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay datos para periodo {periodo}")
        return {
            "periodo": periodo,
            "departamentos": [
                {"dpto": row.get("dpto"), "empleo": int(row.get("empleo") or 0), "informales": int(row.get("informales") or 0), "tasa_informalidad": row.get("tasa_informalidad")}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/salario-ocupacion")
async def get_salario_ocupacion():
    """Salario promedio y mediano por ocupacion (ultima foto disponible)."""
    try:
        r = supabase.table("geih_salario_ocupacion").select("*").order("empleo_total", desc=True).limit(50).execute()
        return {
            "total_ocupaciones": len(r.data),
            "ocupaciones": [
                {
                    "oficio_c8": row.get("oficio_c8"),
                    "oficio_nombre": obtener_nombre_ciuo(row.get("oficio_c8")),
                    "salario_promedio": int(row.get("salario_promedio") or 0),
                    "salario_mediano": int(row.get("salario_mediano") or 0),
                    "empleo_total": int(row.get("empleo_total") or 0),
                    "periodo": row.get("periodo"),
                }
                for row in r.data
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────── NUEVOS ENDPOINTS (ALBA v2 — impacto política pública) ──────────

DATA_PROCESSED = Path(__file__).resolve().parents[2] / "data" / "processed"


@router.get("/dashboard")
async def get_dashboard():
    """Endpoint consolidado que devuelve toda la data inicial del Observatorio y Dashboard en una sola llamada."""
    try:
        # 1. Resumen nacional
        r = supabase.table("geih_resumen_nacional").select("*").order("ano", desc=True).order("mes", desc=True).limit(1).execute()
        ultima = r.data[0] if r.data else {}
        periodo = ultima.get("periodo")
        r_sec = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("empleo", desc=True).limit(50).execute() if periodo else {"data": []}
        empleo_raw = int(ultima.get("empleo_nacional") or 0)
        pea = int(ultima.get("pea_nacional") or 0)
        desempleados = int(ultima.get("desempleados_nacional") or 0)
        empleo = pea - desempleados if pea > 0 and empleo_raw > pea else empleo_raw
        tasa_ocupacion = round((pea - desempleados) / pea * 100, 2) if pea > 0 else None
        resumen_nacional = {
            "periodo": periodo,
            "tasa_desempleo_nacional": ultima.get("tasa_desempleo_nacional"),
            "empleo_nacional": empleo,
            "salario_promedio_nacional": int(ultima.get("salario_promedio_nacional") or 0),
            "tasa_informalidad_nacional": ultima.get("tasa_informalidad_nacional"),
            "pea_nacional": pea,
            "ocupados_totales": empleo,
            "desocupados_totales": desempleados,
            "tasa_ocupacion_nacional": tasa_ocupacion,
            "ingreso_promedio_nacional": int(ultima.get("salario_promedio_nacional") or 0),
            "top_sectores_empleo": _dedup_sectores_geih(r_sec.data),
        }

        # 2. Tendencia de empleo (CSV local)
        tendencia = _calcular_tendencia_empleo()

        # 3. Sectores emergentes (CSV local)
        emergentes = _calcular_sectores_emergentes()

        # 4. Indice de prioridad (CSV local)
        prioridad = _calcular_indice_prioridad()

        # 5. Brecha oferta-demanda (Supabase)
        brecha = _calcular_brecha_oferta_demanda()
        # 5b. Indice de oportunidad (GEIH + SPE + RUES)
        indice = _calcular_indice_oportunidad()

        # 6. Sectores formales (Supabase) - deduplicados
        r_formal = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(200).execute()
        formales = {"sectores": _dedup_pila(r_formal.data)[:50]}

        # 7. SPE demanda (Supabase)
        spe = _calcular_spe_demanda(15)

        # 8. Mapa metricas (Supabase + CSV fallback)
        mapa = _calcular_mapa_metricas_sync()

        result = {
            "resumen_nacional": resumen_nacional,
            "tendencia": tendencia,
            "emergentes": emergentes,
            "prioridad": prioridad,
            "brecha": brecha,
            "sectores_formales": formales,
            "spe": spe,
            "mapa": mapa,
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _calcular_tendencia_empleo():
    try:
        df = pd.read_csv(DATA_PROCESSED / "geih_empleo_sector_mensual.csv")
        df["ano"] = df["ano"].astype(int)
        ci = df["rama_ciiu"].fillna(0).astype(int)

        def _macrosector(codigo: int) -> str:
            if codigo < 10: return "Agricultura y recursos"
            if codigo < 20: return "Alimentos y manufactura"
            if codigo < 30: return "Industria y tecnologia"
            if codigo < 40: return "Energia y agua"
            if codigo < 48: return "Construccion y comercio"
            if codigo < 54: return "Transporte y logistica"
            if codigo < 57: return "Alojamiento y comida"
            if codigo < 67: return "Informacion y finanzas"
            if codigo < 83: return "Servicios empresariales"
            return "Servicios publicos y sociales"

        df["macrosector"] = ci.apply(_macrosector)
        anual = df.groupby(["ano", "macrosector"]).agg(empleo=("empleo", "sum"), meses=("mes", "nunique")).reset_index()
        anual["empleo_mensual"] = anual["empleo"] / anual["meses"]
        ultimo = df["ano"].max()
        primero = df["ano"].min()
        top = anual[anual["ano"] == ultimo].nlargest(6, "empleo_mensual")
        series = []
        for _, s_row in top.iterrows():
            sec = s_row["macrosector"]
            hist = anual[anual["macrosector"] == sec].sort_values("ano")
            puntos = [{"ano": int(r["ano"]), "empleo": round(r["empleo_mensual"])} for _, r in hist.iterrows()]
            if len(puntos) >= 2:
                delta = ((puntos[-1]["empleo"] - puntos[0]["empleo"]) / puntos[0]["empleo"]) * 100
                tendencia = "crece" if delta > 1 else ("declina" if delta < -1 else "estable")
            else:
                delta = 0; tendencia = "estable"
            series.append({"sector": sec, "tendencia": tendencia, "variacion_pct": round(delta, 1), "datos": puntos})
        return {"sectores": sorted(series, key=lambda s: -s["variacion_pct"]), "periodo": f"{primero}-{ultimo}"}
    except Exception as e:
        print(f"[Dashboard] tendencia-empleo error: {e}")
        return {"sectores": [], "periodo": ""}


def _calcular_sectores_emergentes():
    """Sectores emergentes según RUES: top 5 CIIU2 por empresas nuevas 2023-2025.

    Filtros aplicados:
      - Años 2000-2026 (descarta registros espurios como 2088).
      - Suma de empresas nuevas en 2023-2025 para cada CIIU2.
      - Top 5 CIIU2 con más nuevas empresas en ese periodo reciente.
      - Serie histórica completa (años disponibles) para cada top sector.
    """
    try:
        df = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")
        # Limpiar años espurios
        df = df[df["anio_matricula"].between(2000, 2026)]
        if df.empty:
            return {"sectores": [], "periodo": ""}
        df["anio"] = df["anio_matricula"].astype(int)
        df["ciiu"] = df["ciiu2"].astype(str).str.zfill(2)

        # Ranking por empresas nuevas en 2023-2025
        reciente = df[df["anio"].between(2023, 2025)]
        top5 = (
            reciente.groupby("ciiu")["empresas_nuevas"]
            .sum()
            .reset_index()
            .sort_values("empresas_nuevas", ascending=False)
            .head(5)
        )
        if top5.empty:
            return {"sectores": [], "periodo": ""}

        nombres = {
            "01": "Agricultura", "02": "Silvicultura", "03": "Pesca", "05": "Carbón", "06": "Petróleo",
            "07": "Minerales metálicos", "08": "Otras minas", "09": "Apoyo a minería",
            "10": "Alimentos", "11": "Bebidas", "12": "Tabaco", "13": "Textiles",
            "14": "Prendas de vestir", "15": "Cuero", "16": "Madera", "17": "Papel",
            "18": "Impresión", "19": "Coque y refinación", "20": "Químicos",
            "21": "Farmacéuticos", "22": "Caucho y plástico", "23": "Minerales no metálicos",
            "24": "Metales básicos", "25": "Productos metálicos", "26": "Informática/electrónica",
            "27": "Equipo eléctrico", "28": "Maquinaria", "29": "Vehículos",
            "30": "Otros equipos de transporte", "31": "Muebles", "32": "Otros manufacturas",
            "33": "Reparaciones", "35": "Electricidad", "36": "Agua", "37": "Saneamiento",
            "38": "Recolección de desechos", "39": "Actividades de saneamiento",
            "41": "Construcción de edificios", "42": "Obras civiles",
            "43": "Construcción especializada", "45": "Comercio de vehículos",
            "46": "Comercio mayorista", "47": "Comercio al por menor",
            "49": "Transporte terrestre", "50": "Transporte acuático", "51": "Transporte aéreo",
            "52": "Almacenamiento", "53": "Correo y mensajería", "55": "Alojamiento",
            "56": "Servicios de comida", "58": "Edición", "59": "Cine y TV",
            "61": "Telecomunicaciones", "62": "Software", "63": "Información",
            "64": "Financieros", "65": "Seguros", "66": "Auxiliares financieros",
            "68": "Inmobiliarias", "69": "Jurídicas y contables", "70": "Consultoría",
            "71": "Servicios técnicos", "72": "Investigación científica",
            "73": "Publicidad", "74": "Otras profesionales", "75": "Veterinaria",
            "77": "Alquiler de maquinaria", "78": "Actividades de empleo",
            "79": "Agencias de viaje", "80": "Seguridad", "81": "Servicios a edificios",
            "82": "Administrativos", "84": "Administración pública", "85": "Educación",
            "86": "Salud humana", "87": "Asistencia social", "88": " residencial?",
            "90": "Artes", "93": "Deportes", "94": "Asociaciones", "96": "Servicios personales",
            "97": "Hogares como empleadores", "98": "No clasificable", "99": "No clasificable",
            "00": "Sin clasificar",
        }

        anual = df.groupby(["anio", "ciiu"])["empresas_nuevas"].sum().reset_index()
        tendencias = []
        for _, row_top in top5.iterrows():
            sec = str(row_top["ciiu"])
            hist = anual[anual["ciiu"] == sec].sort_values("anio")
            puntos = [
                {"ano": int(row["anio"]), "empresas": int(row["empresas_nuevas"])}
                for _, row in hist.iterrows()
            ]
            delta = 0
            if len(puntos) >= 2 and puntos[0]["empresas"] > 0:
                delta = ((puntos[-1]["empresas"] - puntos[0]["empresas"]) / puntos[0]["empresas"]) * 100
            tendencias.append({
                "sector": nombres.get(sec, f"Sector {sec}"),
                "ciiu": sec,
                "empresas_nuevas_2023_2025": int(row_top["empresas_nuevas"]),
                "variacion_pct": round(delta, 1),
                "variacion_periodo": f"{int(df['anio'].min())}-{int(df['anio'].max())}",
                "datos": puntos,
            })

        return {
            "sectores": sorted(tendencias, key=lambda s: -s["empresas_nuevas_2023_2025"]),
            "periodo": f"{int(df['anio'].min())}-{int(df['anio'].max())}",
            "periodo_ranking": "2023-2025",
        }
    except Exception as e:
        print(f"[Dashboard] sectores-emergentes error: {e}")
        import traceback; traceback.print_exc()
        return {"sectores": [], "periodo": ""}


def _calcular_indice_prioridad():
    try:
        geih = pd.read_csv(DATA_PROCESSED / "geih_resumen_departamento.csv")
        desempleo = pd.read_csv(DATA_PROCESSED / "geih_desempleo_departamento.csv")
        dnp = pd.read_csv(DATA_PROCESSED / "dnp_desempeno_departamento.csv")
        rues = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")
        ultimo_anio = _ultimo_anio_rues(rues)
        nuevas_total_ultimo = rues[rues["anio_matricula"] == ultimo_anio]["empresas_nuevas"].sum()

        # Mapas para cruce
        dnp_map = {}
        for _, r in dnp.iterrows():
            dnp_map[_norm_depto(r["departamento"])] = r.get("promedio_desempeno", 50)

        des_map = {}
        for _, r in desempleo.iterrows():
            deps_key = _norm_depto(r["departamento"])
            ocup = r.get("ocupados", r.get("no_ocupados", 0))
            if isinstance(ocup, (int, float)) and ocup:
                des_map[deps_key] = float(ocup)

        resultados = []
        for _, row in geih.iterrows():
            depto = row["departamento"]
            key = _norm_depto(depto)
            ocupados = row.get("ocupados", 0) or 0
            ingreso = row.get("ingreso_promedio", 0) or 0
            formalidad = (row.get("tasa_formalidad", 0) or 0) * 100 if float(row.get("tasa_formalidad", 0) or 0) < 1 else row.get("tasa_formalidad", 0)
            educacion = (row.get("pct_educacion_superior", 0) or 0) * 100 if float(row.get("pct_educacion_superior", 0) or 0) < 1 else row.get("pct_educacion_superior", 0)

            # Tasa desempleo
            no_ocu = des_map.get(key, 0)
            tasa_des = round(no_ocu / (ocupados + no_ocu) * 100, 1) if (ocupados + no_ocu) > 0 else 0

            # DNP desempeño (0-100, invertido: bajo = peor = más urgente)
            dnp_val = float(dnp_map.get(key, 50))
            dnp_penal = max(0, 100 - dnp_val)

            # Score compuesto con DNP y desempleo
            informalidad = max(0, 100 - (formalidad or 0))
            ingreso_norm = max(0, min(100, ingreso / 3_000_000 * 100)) if ingreso > 0 else 0
            pen_tamano = 0 if ocupados > 500_000 else 10

            contrib_informalidad = round(informalidad * 0.25, 1)
            contrib_desempleo = round(tasa_des * 0.25, 1)
            contrib_dnp = round(dnp_penal * 0.20, 1)
            contrib_educacion = round(max(0, 100 - educacion) * 0.15, 1)
            contrib_ingreso = round(max(0, 100 - ingreso_norm) * 0.05, 1)

            score = contrib_informalidad + contrib_desempleo + contrib_dnp + contrib_educacion + contrib_ingreso + pen_tamano
            score = round(max(20, min(85, score)))
            tag = "urgente" if score >= 70 else ("atencion" if score >= 50 else "estable")

            resultados.append({
                "departamento": depto,
                "indice_prioridad": score,
                "nivel": tag,
                "ocupados": round(ocupados),
                "ingreso_promedio": round(ingreso),
                "tasa_formalidad": round(formalidad, 1),
                "pct_educacion_superior": round(educacion, 1),
                "tasa_desempleo": round(tasa_des, 1),
                "dnp_desempeno": round(dnp_val, 1),
                "desglose": [
                    f"Informalidad {round(informalidad)}% → {contrib_informalidad} pts" if informalidad > 0 else "",
                    f"Desempleo {tasa_des}% → {contrib_desempleo} pts" if tasa_des > 0 else "",
                    f"Gestión pública {round(dnp_val)}/100 → {contrib_dnp} pts" if dnp_val > 0 else "",
                    f"Educación superior {round(educacion)}% → {contrib_educacion} pts",
                    f"Ingreso promedio ${ingreso:,.0f} → {contrib_ingreso} pts" if ingreso > 0 else "",
                    f"Territorio pequeño (+{pen_tamano} pts)" if pen_tamano > 0 else "",
                ],
            })
        # Año de los datos usados para contextualizar el score
        anio_datos = None
        try:
            anio_datos = int(rues["anio_matricula"].max()) if not rues.empty else None
        except Exception:
            pass

        return {
            "departamentos": sorted(resultados, key=lambda d: -d["indice_prioridad"]),
            "total_empresas_nuevas_nacional": int(nuevas_total_ultimo),
            "nota": "Indice compuesto: >70 urgente, 50-70 atencion, <50 estable.",
            "anio_datos": anio_datos,
            "metodologia": (
                "Score 0-100 = informalidad×0.25 + desempleo×0.25 + (100 - DNP)×0.20 + "
                "(100 - educación superior)×0.15 + (100 - ingreso normalizado)×0.05 + "
                "penalización territorio pequeño (+10). Datos: GEIH (último periodo), DNP/MDM, RUES."
            ),
            "variables": ["informalidad", "desempleo", "gestion_publica_dnp", "educacion_superior", "ingreso_promedio", "tamano_territorio"],
            "pesos": {"informalidad": 0.25, "desempleo": 0.25, "gestion_publica_dnp": 0.20, "educacion_superior": 0.15, "ingreso_promedio": 0.05, "tamano_territorio": 0.10},
        }
    except Exception as e:
        print(f"[Dashboard] indice-prioridad error: {e}")
        return {"departamentos": [], "total_empresas_nuevas_nacional": 0, "nota": ""}


def _calcular_brecha_oferta_demanda():
    """Brecha entre matriculados SNIES y empleo real GEIH por macro-categoría.

    Reemplaza PILA por GEIH: la demanda laboral se mide con ocupados reales
    de la última foto GEIH (último mes disponible), clasificados por CIIU a la
    misma taxonomía macro que los núcleos de conocimiento SNIES.
    """
    try:
        r_snies = supabase.table("snies_programas_matriculados").select("nucleo_conocimiento, matriculados").execute()
        oferta = defaultdict(float)
        for row in r_snies.data or []:
            cat = _categoria_nucleo(row.get("nucleo_conocimiento", ""))
            oferta[cat] += row.get("matriculados") or 0
        total_oferta = sum(oferta.values()) or 1

        # Demanda: empleo real GEIH del último periodo disponible
        r_periodo = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
        periodo = r_periodo.data[0]["periodo"] if r_periodo.data else None
        demanda = defaultdict(float)
        periodo_demanda = periodo
        if periodo:
            r_geih = supabase.table("geih_empleo_sector_mensual").select("rama_ciiu, empleo").eq("periodo", periodo).execute()
            seen = set()
            for row in r_geih.data or []:
                rama = row.get("rama_ciiu")
                if rama is None or rama in seen:
                    continue
                seen.add(rama)
                cat = _categoria_ciiu(rama)
                demanda[cat] += row.get("empleo") or 0
        total_demanda = sum(demanda.values()) or 1

        cats = set(oferta.keys()) | set(demanda.keys())
        brecha = []
        for cat in cats:
            oferta_share = (oferta.get(cat, 0) / total_oferta) * 100
            demanda_share = (demanda.get(cat, 0) / total_demanda) * 100
            desajuste = oferta_share - demanda_share
            brecha.append({
                "categoria": cat,
                "oferta_matriculados": round(oferta.get(cat, 0), 0),
                "demanda_empleo": round(demanda.get(cat, 0), 0),
                "oferta_share": round(oferta_share, 2),
                "demanda_share": round(demanda_share, 2),
                "desajuste": round(desajuste, 2),
                "tipo": "sobre-oferta" if desajuste > 2 else ("sub-oferta" if desajuste < -2 else "equilibrado"),
            })
        brecha.sort(key=lambda x: abs(x["desajuste"]), reverse=True)
        sobre = sorted([b for b in brecha if b["desajuste"] > 0], key=lambda x: -x["desajuste"])[:5]
        sub = sorted([b for b in brecha if b["desajuste"] < 0], key=lambda x: x["desajuste"])[:5]
        return {
            "brecha_categorias": brecha,
            "top_sobre_oferta": sobre,
            "top_sub_oferta": sub,
            "totales": {
                "matriculados_snies": round(total_oferta, 0),
                "empleo_geih": round(total_demanda, 0),
                "periodo_demanda": periodo_demanda,
            },
            "metodologia": "Oferta = matriculados SNIES por nucleo de conocimiento. Demanda = ocupados GEIH del ultimo mes por CIIU, ambos agrupados en macro-categorias. CIIUs sin categoria formativa en SNIES (industria manufacturera, mineria, pesca) se desglosan en sub-grupos para no quedar como OTROS. No usa PILA.",
        }
    except Exception as e:
        print(f"[Dashboard] brecha error: {e}")
        return {"brecha_categorias": [], "top_sobre_oferta": [], "top_sub_oferta": [], "totales": {"matriculados_snies": 0, "empleo_geih": 0}, "metodologia": ""}


# Mapeo de macro-categorias del Indice de Oportunidad (las usamos para cruzar
# GEIH, SPE y RUES en la misma taxonomia)
# Usamos las mismas 9 macro-categorias de _NUCLEO_TO_CAT para mantener consistencia
# con el resto de ALBA (oferta educativa SNIES, brecha, etc.)
_INDICE_CATEGORIAS = [
    "ADMINISTRACION", "AGROPECUARIO", "ARTES", "CIENCIAS_BASICAS",
    "DERECHO", "EDUCACION", "GOBIERNO", "INGENIERIAS",
    "SALUD", "TECNOLOGIA",
]

_INDICE_NOMBRES = {
    "ADMINISTRACION": "Administracion, comercio y servicios",
    "AGROPECUARIO": "Agropecuario, silvicultura y pesca",
    "ARTES": "Artes, diseno y entretenimiento",
    "CIENCIAS_BASICAS": "Ciencias basicas e investigacion",
    "DERECHO": "Derecho y ciencias politicas",
    "EDUCACION": "Educacion",
    "GOBIERNO": "Gobierno, defensa y seguridad",
    "INGENIERIAS": "Ingenieria, industria y manufactura",
    "SALUD": "Salud humana y asistencia social",
    "TECNOLOGIA": "Tecnologia, informacion y datos",
}

# Mapeo de seccion CIIU del SPE (letras A-U) -> macro-categoria del indice.
# Como el SPE agrupa por seccion CIIU (letra) y ALBA usa las 10 categorias
# macro de nucleo de conocimiento, mapeamos las secciones a las categorias
# mas cercanas. Las que no tienen equivalente (transporte, alojamiento, etc.)
# se agregan a ADMINISTRACION (la categoria mas amplia del lado SNIES).
_INDICE_POR_SECCION_SPE = {
    "A": "AGROPECUARIO",
    "B": "INGENIERIAS",   # Minas
    "C": "INGENIERIAS",   # Manufactura
    "D": "INGENIERIAS",   # Electricidad/gas
    "E": "INGENIERIAS",   # Agua/saneamiento
    "F": "INGENIERIAS",   # Construccion
    "G": "ADMINISTRACION",# Comercio
    "H": "ADMINISTRACION",# Transporte
    "I": "ADMINISTRACION",# Alojamiento
    "J": "TECNOLOGIA",    # Informacion
    "K": "ADMINISTRACION",# Finanzas
    "L": "ADMINISTRACION",# Inmobiliarias
    "M": "DERECHO",      # Actividades profesionales, cientificas y tecnicas
                        # (incluye juridicas, contables, ingenieria tecnica, etc.)
                        # Se asigna a DERECHO porque es la categoria mas representativa
                        # de las actividades profesionales en el SNIES.
    "N": "ADMINISTRACION",# Servicios admin
    "O": "GOBIERNO",      # Adm publica
    "P": "EDUCACION",
    "Q": "SALUD",
    "R": "ARTES",
    "S": "ADMINISTRACION",
    "T": "ADMINISTRACION",
    "U": "ADMINISTRACION",
}


def _calcular_indice_oportunidad():
    """Indice de Oportunidad Laboral por macro-categoria, basado en RANKING.

    Metodologia (revisada para resistir auditoria metodologica):

      En lugar de usar variacion porcentual (sensible a valores iniciales
      pequenos que producen crecimientos explosivos como 121764%), usamos
      RANKING POR CUOTA ABSOLUTA en cada fuente oficial. Esto es estable
      y comparable entre areas.

      Para cada macro-categoria calculamos 3 rankings (percentil 0-100):
        - Ranking GEIH: posicion por cuota de empleo en el ultimo periodo.
        - Ranking SPE: posicion por total de vacantes registradas en 2023.
        - Ranking RUES: posicion por total de empresas nuevas 2020-2026.

      Score = 0.40 * ranking_GEIH + 0.35 * ranking_SPE + 0.25 * ranking_RUES

      Nota: los periodos son diferentes porque cada fuente oficial tiene
      su propia ventana de actualizacion:
        - GEIH: 2022-2026 (DANE, mensual)
        - SPE: 2019-2023 (UAESPE, ultimo publicado)
        - RUES: 2020-2026 (Camaras de Comercio)

      Ademas: la categoria "Tecnologia, informacion y datos" se construye
      agregando las secciones CIIU J (informacion y comunicaciones),
      62 (desarrollo de sistemas informaticos) y 63 (servicios de informacion).
    """
    try:
        from collections import defaultdict

        # === Componente 1: GEIH - cuota de empleo por categoria (ultimo periodo) ===
        r = supabase.table("geih_empleo_sector_mensual").select("rama_ciiu, periodo, empleo").execute()
        # Determinar el ultimo periodo disponible
        periodos = sorted(set((row.get("periodo") for row in (r.data or []) if row.get("periodo"))), reverse=True)
        ultimo_periodo = periodos[0] if periodos else None

        geih_empleo_por_cat = defaultdict(float)
        geih_empleo_total = 0.0
        if ultimo_periodo:
            for row in r.data or []:
                if row.get("periodo") != ultimo_periodo:
                    continue
                rama = row.get("rama_ciiu")
                empleo = float(row.get("empleo") or 0)
                if rama is None or empleo <= 0:
                    continue
                cat = _categoria_ciiu(rama)
                geih_empleo_por_cat[cat] += empleo
                geih_empleo_total += empleo

        # Cuota (%) de cada categoria
        geih_cuota = {}
        if geih_empleo_total > 0:
            for cat, v in geih_empleo_por_cat.items():
                geih_cuota[cat] = (v / geih_empleo_total) * 100

        # === Componente 2: SPE - total de vacantes por categoria (ultimo anio) ===
        r = supabase.table("spe_vacantes_sector").select("seccion, anio, vacantes").execute()
        # Agrupar por categoria del indice
        spe_vacantes_por_cat = defaultdict(int)
        spe_vacantes_total = 0
        for row in r.data or []:
            seccion = row.get("seccion")
            anio = int(row.get("anio") or 0)
            vac = int(row.get("vacantes") or 0)
            if not seccion or not anio or not vac or anio > 2030:
                continue
            cat = _INDICE_POR_SECCION_SPE.get(seccion, "OTROS_SERVICIOS")
            spe_vacantes_por_cat[cat] += vac
            spe_vacantes_total += vac

        # Cuota (%) de cada categoria (total del periodo completo)
        spe_cuota = {}
        if spe_vacantes_total > 0:
            for cat, v in spe_vacantes_por_cat.items():
                spe_cuota[cat] = (v / spe_vacantes_total) * 100

        # === Componente 3: RUES - total de empresas nuevas por categoria (2020-2026) ===
        r = supabase.table("rues_empresas_nuevas").select("anio_matricula, ciiu2, empresas_nuevas").execute()
        rues_empresas_por_cat = defaultdict(int)
        rues_empresas_total = 0
        for row in r.data or []:
            anio = int(row.get("anio_matricula") or 0)
            ciiu2 = row.get("ciiu2")
            emp = int(row.get("empresas_nuevas") or 0)
            if not anio or not ciiu2 or not emp or anio > 2030:
                continue
            cat = _categoria_ciiu(ciiu2)
            if cat not in _INDICE_CATEGORIAS:
                continue
            rues_empresas_por_cat[cat] += emp
            rues_empresas_total += emp

        rues_cuota = {}
        if rues_empresas_total > 0:
            for cat, v in rues_empresas_por_cat.items():
                rues_cuota[cat] = (v / rues_empresas_total) * 100

        # === Calcular ranking por percentil (0-100) por fuente ===
        def _ranking_percentil(valores):
            """Convierte un dict {cat: valor} en {cat: percentil 0-100}.
            El que tiene el valor mas alto recibe 100, el mas bajo 0."""
            if not valores:
                return {}
            cats = list(valores.keys())
            if len(cats) < 2:
                return {c: 50.0 for c in cats}
            sorted_cats = sorted(cats, key=lambda c: valores[c])
            n = len(sorted_cats)
            return {c: (i / (n - 1)) * 100 for i, c in enumerate(sorted_cats)}

        ranking_geih = _ranking_percentil(geih_cuota)
        ranking_spe = _ranking_percentil(spe_cuota)
        ranking_rues = _ranking_percentil(rues_cuota)

        # === Calcular score por categoria ===
        indices = []
        for cat in _INDICE_CATEGORIAS:
            r_geih = ranking_geih.get(cat, 0)
            r_spe = ranking_spe.get(cat, 0)
            r_rues = ranking_rues.get(cat, 0)
            # Score: 40% empleo + 35% vacantes + 25% empresas
            score = 0.40 * r_geih + 0.35 * r_spe + 0.25 * r_rues
            if score >= 66:
                nivel = "ALTA"
                color = "alta"
            elif score >= 33:
                nivel = "MEDIA"
                color = "media"
            else:
                nivel = "BAJA"
                color = "baja"
            indices.append({
                "categoria": cat,
                "categoria_nombre": _INDICE_NOMBRES.get(cat, cat),
                "score": round(score, 1),
                "ranking_geih": round(r_geih, 1),
                "ranking_spe": round(r_spe, 1),
                "ranking_rues": round(r_rues, 1),
                "geih_cuota_pct": round(geih_cuota.get(cat, 0), 2),
                "geih_empleo": int(geih_empleo_por_cat.get(cat, 0)),
                "spe_vacantes": int(spe_vacantes_por_cat.get(cat, 0)),
                "spe_cuota_pct": round(spe_cuota.get(cat, 0), 2),
                "rues_empresas": int(rues_empresas_por_cat.get(cat, 0)),
                "rues_cuota_pct": round(rues_cuota.get(cat, 0), 2),
                "nivel": nivel,
                "color": color,
            })
        # Ordenar por score descendente
        indices.sort(key=lambda x: -x["score"])
        # Asignar posicion
        for i, idx in enumerate(indices):
            idx["posicion"] = i + 1
            idx["total_categorias"] = len(indices)

        return {
            "indices": indices,
            "metodologia": (
                "Indice de Oportunidad calculado como RANKING POR PERCENTIL en 3 fuentes oficiales. "
                "Para cada macro-categoria se calcula su posicion relativa (0-100) por: "
                "(a) cuota de empleo en GEIH 2026, (b) total de vacantes en SPE 2023, "
                "(c) total de empresas nuevas en RUES 2020-2026. "
                "Score = 0.40*GEIH + 0.35*SPE + 0.25*RUES. "
                "Las 3 fuentes tienen ventanas de tiempo diferentes porque cada una "
                "tiene su propia fecha de actualizacion oficial."
            ),
            "categorizacion": (
                "Las 10 macro-categorias se construyen asi: "
                "Tecnologia, informacion y datos = CIIU J (informacion) + 62 (software) + 63 (servicios info). "
                "Salud = CIIU 75, 86, 87, 88. "
                "Educacion = CIIU 85. "
                "Derecho = CIIU 69 (actividades juridicas y contables). "
                "Gobierno = CIIU 80, 81, 82, 84. "
                "Ingenieria, industria y manufactura = CIIU 10-39, 41-43, 71. "
                "Administracion, comercio y servicios = resto de CIIU (comercio, finanzas, transporte, etc.). "
                "Agropecuario = CIIU 1, 2, 3, 4. "
                "Ciencias basicas = CIIU 72, 74. "
                "Artes, diseno y entretenimiento = CIIU 58, 59, 60, 90, 91, 93."
            ),
            "fuentes": {
                "geih": f"DANE GEIH {ultimo_periodo or 'ultimo disponible'} (mensual, 2022-2026)",
                "spe": "UAESPE Anexo Demanda Laboral 2015-2023 (publicado agosto 2025, ultimo dato noviembre 2023)",
                "rues": "RUES 2020-2026 (Camaras de Comercio)",
            },
            "ventanas_tiempo": {
                "geih": "2022-02 a 2026-04 (52 meses)",
                "spe": "2019 a 2023 (5 anos, ultimo publicado)",
                "rues": "2020 a 2026 (7 anos)",
            },
        }
    except Exception as e:
        print(f"[Dashboard] indice-oportunidad error: {e}")
        return {"indices": [], "metodologia": "", "categorizacion": "", "fuentes": {}, "ventanas_tiempo": {}}


# Mapeo codigo DIVIPOLA -> nombre departamento (para emicron_por_departamento_v2)
_DIVIPOLA_NOMBRE = {
    5: "Antioquia", 8: "Atlántico", 11: "Bogotá D.C.", 13: "Bolívar",
    15: "Boyacá", 17: "Caldas", 18: "Caquetá", 19: "Casanare",
    20: "Cauca", 21: "Cesar", 27: "Chocó", 23: "Córdoba",
    25: "Cundinamarca", 41: "Huila", 44: "La Guajira", 47: "Magdalena",
    50: "Meta", 52: "Nariño", 54: "Norte de Santander", 63: "Quindío",
    66: "Risaralda", 68: "Santander", 70: "Sucre", 73: "Tolima",
    76: "Valle del Cauca", 81: "Arauca", 85: "Casanare", 86: "Putumayo",
    88: "San Andrés", 91: "Amazonas", 94: "Guainía", 95: "Guaviare",
    97: "Vaupés", 99: "Vichada",
}


# 4 indicadores macro laborales clave del Banco Mundial para Colombia.
# Se usa el mismo orden y nomenclatura amigable en backend y frontend.
_MACRO_INDICADORES = {
    "SL.UEM.TOTL.ZS": "Desempleo total (% fuerza laboral)",
    "SL.EMP.SELF.ZS": "Trabajadores por cuenta propia (% del empleo)",
    "SL.GDP.PCAP.EM.KD": "PIB por persona empleada (USD const. 2017)",
    "SL.SRV.EMPL.ZS": "Empleo en servicios (% del total)",
}

def _calcular_macro_worldbank():
    """Contexto macro laboral de Colombia 2010-2025 (World Bank).

    Retorna exactamente los 4 indicadores clave solicitados, con su variación
    2010-2025 (primer año disponible vs último). Los demás indicadores se
    omiten para no dispersar el mensaje del dashboard.
    """
    try:
        r = supabase.table("worldbank_colombia").select("*").execute()
        if not r.data:
            return {"indicadores": []}

        series: dict[str, list[dict]] = {code: [] for code in _MACRO_INDICADORES}
        for row in r.data:
            code = row.get("indicator_code")
            if code not in _MACRO_INDICADORES:
                continue
            val = row.get("value")
            if val is None:
                continue
            try:
                val = float(val)
            except (TypeError, ValueError):
                continue
            series[code].append({"year": int(row.get("year")), "value": round(val, 2)})

        indicadores = []
        for code, puntos in series.items():
            puntos.sort(key=lambda x: x["year"])
            if not puntos:
                continue
            primero = puntos[0]
            ultimo = puntos[-1]
            cambio = round(ultimo["value"] - primero["value"], 2)
            es_usd = _wb_unidad(code) == "USD"
            indicadores.append({
                "indicator_code": code,
                "indicator_name": _MACRO_INDICADORES[code],
                "unidad": _wb_unidad(code),
                "anio_inicio": primero["year"],
                "anio_fin": ultimo["year"],
                "valor_inicio": primero["value"],
                "valor_fin": ultimo["value"],
                "variacion": cambio,
                "datos": puntos,
            })

        # Orden fijo: desempleo, cuenta propia, PIB/empleado, servicios
        orden = list(_MACRO_INDICADORES.keys())
        indicadores.sort(key=lambda x: orden.index(x["indicator_code"]))
        return {"indicadores": indicadores}
    except Exception as e:
        print(f"[Dashboard] macro-worldbank error: {e}")
        return {"indicadores": []}


def _wb_unidad(indicator_code: str) -> str:
    """Devuelve la unidad de medida de un indicador del Banco Mundial.
    La mayoría son %, pero el PIB va en USD."""
    if indicator_code == "SL.GDP.PCAP.EM.KD":
        return "USD"  # PIB por persona empleada (dólares constantes 2017)
    return "porcentaje"


def _calcular_informalidad_territorial():
    """Micronegocios (informalidad) por departamento (EMICRON v2, 2022-2024).

    Complementa el empleo formal por departamento con la dimensión informal.
    Muestra el año real del dato, la variación 2022-2024 y el ingreso promedio
    mensual del micronegocio típico del departamento cuando está disponible.
    """
    try:
        r = supabase.table("emicron_por_departamento_v2").select("*").execute()
        if not r.data:
            return {"departamentos": []}

        # Agrupar por dpto, usando solo años 2022-2024
        por_depto = defaultdict(list)
        for row in r.data:
            dpto = int(row.get("dpto") or 0)
            ano = int(row.get("ano") or 0)
            if dpto == 0 or ano < 2022 or ano > 2024:
                continue
            por_depto[dpto].append({
                "ano": ano,
                "micronegocios": float(row.get("micronegocios") or 0),
                "ingreso_promedio": float(row.get("ingreso_promedio") or 0) if row.get("ingreso_promedio") is not None else None,
            })

        resultado = []
        for dpto_cod, puntos in por_depto.items():
            nombre = _DIVIPOLA_NOMBRE.get(dpto_cod, f"Dpto {dpto_cod}")
            puntos.sort(key=lambda x: x["ano"])
            if not puntos:
                continue
            ultimo = puntos[-1]
            primero_2022 = next((p for p in puntos if p["ano"] == 2022), None)
            # Variación 2022->último año disponible
            crec_pct = None
            if primero_2022 and primero_2022["micronegocios"] > 0:
                crec_pct = round(
                    ((ultimo["micronegocios"] - primero_2022["micronegocios"]) / primero_2022["micronegocios"]) * 100, 1
                )
            resultado.append({
                "departamento": nombre,
                "micronegocios": int(ultimo["micronegocios"]),
                "ano": ultimo["ano"],
                "serie_anios": len(puntos),
                "micronegocios_2022": int(primero_2022["micronegocios"]) if primero_2022 else None,
                "micronegocios_2023": int(next((p["micronegocios"] for p in puntos if p["ano"] == 2023), 0)) or None,
                "crecimiento_pct": crec_pct,
                "ingreso_promedio_mensual": round(ultimo["ingreso_promedio"]) if ultimo.get("ingreso_promedio") else None,
                "ingreso_disponible": ultimo.get("ingreso_promedio") is not None,
            })
        resultado.sort(key=lambda x: x["micronegocios"], reverse=True)
        return {
            "departamentos": resultado,
            "periodo": "2022-2024",
            "nota": "Micronegocios por departamento según EMICRON/DANE. Variación comparada con 2022.",
        }
    except Exception as e:
        print(f"[Dashboard] informalidad-territorial error: {e}")
        return {"departamentos": []}


def _calcular_composicion_empleo_formal():
    """Composición del empleo formal por tipo de cotizante (PILA).
    Muestra dependientes, independientes, aprendices SENA, cooperados, etc."""
    try:
        r = supabase.table("pila_resumen_tipo").select("*").execute()
        if not r.data:
            return {"tipos": []}
        total = sum(float(row.get("total_cotizantes") or 0) for row in r.data) or 1
        tipos = []
        for row in r.data:
            cotizantes = float(row.get("total_cotizantes") or 0)
            tipos.append({
                "tipo": row.get("tipocotizantepiladesc", "Otro"),
                "cotizantes": int(cotizantes),
                "share_pct": round((cotizantes / total) * 100, 1),
            })
        tipos.sort(key=lambda x: x["cotizantes"], reverse=True)
        return {"tipos": tipos, "total_cotizantes": int(total)}
    except Exception as e:
        print(f"[Dashboard] composicion-empleo error: {e}")
        return {"tipos": []}


def _calcular_sectores_crecimiento_geih(limit: int = 10):
    """Sectores con mayor crecimiento de empleo real según GEIH (serie 2022-2026).

    Reemplaza al widget SPE/SENA (que solo tenía 2019-2020) con datos más
    actuales y representativos (encuesta nacional continua). Calcula el
    crecimiento comparando el promedio de los primeros 3 meses vs últimos 3
    meses disponibles, para suavizar ruido estacional.
    """
    try:
        from app.data.ciiu_nombres import obtener_nombre_ciiu
        r = supabase.table("geih_empleo_sector_mensual").select(
            "rama_ciiu, empleo, periodo"
        ).execute()
        if not r.data:
            return {"sectores_crecimiento": []}

        # Agrupar empleo por rama_ciiu y periodo
        por_sector: dict = {}
        periodos = set()
        for row in r.data:
            rama = row.get("rama_ciiu")
            periodo = row.get("periodo")
            if rama is None or periodo is None:
                continue
            por_sector.setdefault(rama, []).append((periodo, float(row.get("empleo") or 0)))
            periodos.add(periodo)

        periodos_ordenados = sorted(periodos)
        if len(periodos_ordenados) < 4:
            return {"sectores_crecimiento": []}

        crecimiento = []
        for rama, puntos in por_sector.items():
            puntos.sort(key=lambda x: x[0])
            # Promediar primeros 3 y últimos 3 periodos para suavizar
            n_ini = min(3, len(puntos))
            n_fin = min(3, len(puntos))
            empleo_ini = sum(p[1] for p in puntos[:n_ini]) / n_ini
            empleo_fin = sum(p[1] for p in puntos[-n_fin:]) / n_fin
            # Solo sectores con empleo significativo (>10.000) para evitar ruido
            if empleo_fin < 10000:
                continue
            if empleo_ini <= 0:
                continue
            crec = ((empleo_fin - empleo_ini) / empleo_ini) * 100
            crecimiento.append({
                "rama_ciiu": rama,
                "sector": obtener_nombre_ciiu(rama),
                "variacion_pct": round(crec, 1),
                "empleo_inicial": int(empleo_ini),
                "empleo_final": int(empleo_fin),
            })

        # Ordenar por crecimiento descendente y tomar los top
        crecimiento.sort(key=lambda x: x["variacion_pct"], reverse=True)
        periodo_ini = periodos_ordenados[0]
        periodo_fin = periodos_ordenados[-1]
        return {
            "sectores_crecimiento": crecimiento[:limit],
            "periodo": f"{periodo_ini} a {periodo_fin}",
        }
    except Exception as e:
        print(f"[Dashboard] sectores-crecimiento-geih error: {e}")
        return {"sectores_crecimiento": []}


def _calcular_spe_demanda(limit: int):
    try:
        # Traer suficientes filas para compensar duplicados (~4x) y ordenar en Python.
        # La capa SQLite no soporta NULLS LAST, así que filtramos NULL aquí.
        r = supabase.table("spe_ape_inscritos_ocupacion").select("*").limit(limit * 20).execute()
        rows = _dedup_spe(r.data or [])
        # Separar ocupaciones con variación real (no NULL) y ordenar descendente.
        # Solo nos interesan las que CRECIERON (variacion_pct > 0) para "demanda creciente".
        con_var = [
            x for x in rows
            if x.get("variacion_pct") is not None and float(x.get("variacion_pct") or 0) > 0
        ]
        con_var.sort(key=lambda x: float(x.get("variacion_pct") or 0), reverse=True)

        # Si no hay suficientes positivas, completamos con las de mayor demanda absoluta
        # (inscritos_2020 más alto) para no dejar la lista vacía.
        if len(con_var) < limit:
            r2 = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(limit * 20).execute()
            rows2 = _dedup_spe(r2.data or [])
            occ_vistos = {x.get("ocupacion") for x in con_var}
            extras = [x for x in rows2 if x.get("ocupacion") not in occ_vistos][:limit - len(con_var)]
            con_var = con_var + extras
        rows = con_var[:limit]
        return {"ocupaciones_demanda_creciente": rows}
    except Exception as e:
        print(f"[Dashboard] spe-demanda error: {e}")
        return {"ocupaciones_demanda_creciente": []}


def _calcular_mapa_metricas_sync():
    try:
        r_ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        r_des = supabase.table("geih_desempleo_departamento").select("*").execute()
        r_snies = supabase.table("snies_matriculados_departamento").select("*").execute()
        r_dnp = supabase.table("dnp_desempeno_departamento").select("*").execute()

        agg = defaultdict(lambda: {
            "departamento": "",
            "ocupados": 0,
            "sum_ingreso_prom": 0.0,
            "sum_ingreso_med": 0.0,
            "sum_formalidad": 0.0,
            "sum_mujeres_ocu": 0.0,
            "sum_mujeres_cabeza": 0.0,
            "sum_edu_superior": 0.0,
            "n": 0,
            "no_ocupados": 0,
            "nivel_educativo_etiqueta": None,
        })
        for row in _dedup_filas(r_ocu.data or []):
            d = row["departamento"]
            agg[d]["departamento"] = d
            # `ocupados` representa personas: redondear al cargar para evitar sumas con decimales
            # que aparecen cuando la tabla geih_resumen_departamento se cargo multiples veces.
            ocupados = float(row.get("ocupados") or 0)
            agg[d]["ocupados"] += int(round(ocupados))
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * ocupados
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * ocupados
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * ocupados
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * ocupados
            agg[d]["sum_mujeres_cabeza"] += row.get("mujeres_cabeza_hogar_pct") or 0
            agg[d]["sum_edu_superior"] += row.get("pct_educacion_superior") or 0
            agg[d]["n"] += 1
            if row.get("nivel_educativo_etiqueta") and not agg[d]["nivel_educativo_etiqueta"]:
                agg[d]["nivel_educativo_etiqueta"] = row["nivel_educativo_etiqueta"]
        for row in _dedup_filas(r_des.data or []):
            d = row["departamento"]
            no_ocu = float(row.get("no_ocupados") or 0)
            if d in agg:
                agg[d]["no_ocupados"] += int(round(no_ocu))
            else:
                agg[d]["departamento"] = d
                agg[d]["no_ocupados"] = int(round(no_ocu))

        departamentos = []
        for d, a in agg.items():
            ocu = a["ocupados"] or 1
            departamentos.append({
                "departamento": d,
                "departamento_norm": _norm_depto(d),
                "ocupados": a["ocupados"],
                "no_ocupados": a["no_ocupados"],
                "tasa_desempleo": round(a["no_ocupados"] / (a["no_ocupados"] + a["ocupados"]) * 100, 2) if (a["no_ocupados"] + a["ocupados"]) > 0 else None,
                "ingreso_promedio": round(a["sum_ingreso_prom"] / ocu, 0) if a["ocupados"] else None,
                "ingreso_mediano": round(a["sum_ingreso_med"] / ocu, 0) if a["ocupados"] else None,
                "tasa_formalidad": round(a["sum_formalidad"] / ocu * 100, 2) if a["ocupados"] else None,
                "mujeres_pct": round(a["sum_mujeres_ocu"] / ocu * 100, 2) if a["ocupados"] and a["sum_mujeres_ocu"] > 0 else None,
                "tasa_ocupacion": round(a["ocupados"] / (a["ocupados"] + a["no_ocupados"]) * 100, 2) if (a["ocupados"] + a["no_ocupados"]) > 0 else None,
                "mujeres_cabeza_hogar_pct": round(a["sum_mujeres_cabeza"] / a["n"], 2) if a["n"] and a["sum_mujeres_cabeza"] > 0 else None,
                "pct_educacion_superior": round(a["sum_edu_superior"] / a["n"], 2) if a["n"] and a["sum_edu_superior"] > 0 else None,
                "nivel_educativo_etiqueta": a.get("nivel_educativo_etiqueta"),
            })

        snies_map = {}
        for row in _dedup_filas(r_snies.data) or []:
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        dnp_map = {}
        for row in _dedup_filas(r_dnp.data) or []:
            key = _norm_depto(row["departamento"])
            dnp_map[key] = row.get("promedio_desempeno")
        for d in departamentos:
            d["dnp_desempeno"] = round(dnp_map[d["departamento_norm"]], 2) if dnp_map.get(d["departamento_norm"]) is not None else None

        for d in departamentos:
            d.pop("departamento_norm", None)
            if d.get("tasa_formalidad") is not None:
                d["tasa_informalidad"] = round(100 - d["tasa_formalidad"], 2)

        sector_lider_nacional = None
        try:
            pred = _load_predicciones() or {}
            sectores_pred = pred.get("sectores", {})
            mejor_crec = -float("inf")
            for sector, info in sectores_pred.items():
                v2025 = info.get("historico", {}).get("valores", [0])[-1]
                v2035 = info.get("prediccion", {}).get("mediana", [0])[-1]
                crec = ((v2035 - v2025) / max(v2025, 0.01)) * 100 if v2025 else 0
                if crec > mejor_crec:
                    mejor_crec = crec
                    sector_lider_nacional = {"sector": sector, "crecimiento_2035_pct": round(crec, 1)}
        except Exception:
            pass

        # Sector dominante por departamento: promedio móvil 12 meses de GEIH por macrosector CIIU2
        sector_dominante_por_depto = {}
        try:
            sector_dominante_por_depto = _calcular_sector_dominante_por_depto()
        except Exception as e:
            print(f"[Dashboard] sector-dominante error: {e}")

        return {
            "departamentos": departamentos,
            "total": len(departamentos),
            "sector_lider_nacional": sector_lider_nacional,
            "sector_dominante_por_depto": sector_dominante_por_depto,
        }
    except Exception as e:
        print(f"[Dashboard] mapa-metricas error: {e}")
        return {"departamentos": [], "total": 0, "sector_lider_nacional": None, "sector_dominante_por_depto": {}}


def _calcular_sector_dominante_por_depto():
    """Calcula el macrosector con mayor empleo promedio por departamento usando
    una ventana móvil de 12 meses de GEIH (CIIU2 amplios)."""
    df = pd.read_csv(DATA_PROCESSED / "geih_empleo_depto_sector.csv")
    df["dpto"] = df["dpto"].astype(int).astype(str).str.zfill(2)
    df["periodo"] = df["periodo"].astype(str)
    periodos = sorted(df["periodo"].unique())
    if len(periodos) < 1:
        return {}
    ventana = periodos[-12:]
    df_w = df[df["periodo"].isin(ventana)].copy()

    def _broad_sector(codigo: int) -> str:
        if codigo < 10: return "Agricultura"
        if codigo < 40: return "Industria"
        if codigo < 55: return "Comercio y transporte"
        if codigo < 65: return "Alojamiento y restaurantes"
        if codigo < 68: return "Información y comunicaciones"
        if codigo < 77: return "Financieros e inmobiliarios"
        if codigo < 84: return "Servicios profesionales"
        if codigo < 85: return "Administración pública"
        if codigo < 86: return "Educación"
        if codigo < 88: return "Salud"
        if codigo < 98: return "Servicios comunales, sociales y personales"
        return "Otros"

    DPTO_CODE_TO_NAME = {
        "05": "ANTIOQUIA", "08": "ATLÁNTICO", "11": "BOGOTÁ", "13": "BOLÍVAR", "15": "BOYACÁ",
        "17": "CALDAS", "18": "CAQUETÁ", "19": "CAUCA", "20": "CESAR", "23": "CÓRDOBA",
        "25": "CUNDINAMARCA", "27": "CHOCÓ", "41": "HUILA", "44": "LA GUAJIRA", "47": "MAGDALENA",
        "50": "META", "52": "NARIÑO", "54": "NORTE DE SANTANDER", "63": "QUINDÍO", "66": "RISARALDA",
        "68": "SANTANDER", "70": "SUCRE", "73": "TOLIMA", "76": "VALLE DEL CAUCA", "81": "ARAUCA",
        "85": "CASANARE", "86": "PUTUMAYO", "91": "AMAZONAS", "94": "GUAINÍA", "95": "GUAVIARE",
        "97": "VAUPÉS", "99": "VICHADA", "88": "ARCHIPIÉLAGO DE SAN ANDRÉS",
    }

    df_w["sector"] = df_w["rama_ciiu"].fillna(0).astype(int).apply(_broad_sector)
    agg = df_w.groupby(["dpto", "rama_ciiu", "sector"]).agg(empleo_sector=("empleo", "mean")).reset_index()
    agg["empleo_sector"] = agg["empleo_sector"].round(0)
    total_depto = agg.groupby("dpto")["empleo_sector"].sum().to_dict()
    agg["pct_broad_total"] = agg.apply(lambda r: round(r["empleo_sector"] / max(total_depto[r["dpto"]], 1) * 100, 1), axis=1)
    dominant = agg.loc[agg.groupby("dpto")["empleo_sector"].idxmax()]

    out = {}
    for _, r in dominant.iterrows():
        depto_name = DPTO_CODE_TO_NAME.get(r["dpto"], r["dpto"])
        out[depto_name] = {
            "rama_ciiu": int(r["rama_ciiu"]),
            "sector": r["sector"],
            "empleo_sector": int(r["empleo_sector"]),
            "pct_broad_total": r["pct_broad_total"],
            "periodo_inicio": ventana[0],
            "periodo_fin": ventana[-1],
            "meses": len(ventana),
        }
    return out


@router.get("/tendencia-empleo")
async def get_tendencia_empleo():
    """Empleo por macrosector a traves del tiempo. Identifica sectores en crecimiento y declive."""
    df = pd.read_csv(DATA_PROCESSED / "geih_empleo_sector_mensual.csv")
    df["ano"] = df["ano"].astype(int)
    ci = df["rama_ciiu"].fillna(0).astype(int)

    def _macrosector(codigo: int) -> str:
        if codigo < 10: return "Agricultura y recursos"
        if codigo < 20: return "Alimentos y manufactura"
        if codigo < 30: return "Industria y tecnologia"
        if codigo < 40: return "Energia y agua"
        if codigo < 48: return "Construccion y comercio"
        if codigo < 54: return "Transporte y logistica"
        if codigo < 57: return "Alojamiento y comida"
        if codigo < 67: return "Informacion y finanzas"
        if codigo < 83: return "Servicios empresariales"
        return "Servicios publicos y sociales"

    df["macrosector"] = ci.apply(_macrosector)

    # Agrupar por ano + macrosector: sumar empleo, contar meses
    anual = df.groupby(["ano", "macrosector"]).agg(empleo=("empleo", "sum"), meses=("mes", "nunique")).reset_index()
    anual["empleo_mensual"] = anual["empleo"] / anual["meses"]  # normalizar a empleo mensual promedio

    ultimo = df["ano"].max()
    primero = df["ano"].min()

    # Top macrosectores
    top = anual[anual["ano"] == ultimo].nlargest(6, "empleo_mensual")

    series = []
    for _, s_row in top.iterrows():
        sec = s_row["macrosector"]
        hist = anual[anual["macrosector"] == sec].sort_values("ano")
        puntos = [{"ano": int(r["ano"]), "empleo": round(r["empleo_mensual"])} for _, r in hist.iterrows()]
        if len(puntos) >= 2:
            delta = ((puntos[-1]["empleo"] - puntos[0]["empleo"]) / puntos[0]["empleo"]) * 100
            tendencia = "crece" if delta > 1 else ("declina" if delta < -1 else "estable")
        else:
            delta = 0; tendencia = "estable"
        series.append({
            "sector": sec,
            "tendencia": tendencia,
            "variacion_pct": round(delta, 1),
            "datos": puntos,
        })

    return {
        "sectores": sorted(series, key=lambda s: -s["variacion_pct"]),
        "periodo": f"{primero}-{ultimo}",
    }


@router.get("/sectores-emergentes-tendencia")
async def get_sectores_emergentes_tendencia():
    """Tendencia de nuevas empresas por sector segun RUES. Muestra momentum empresarial."""
    df = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")
    df = df[df["anio_matricula"] <= 2026]  # filtrar datos espurios
    df["anio"] = df["anio_matricula"].astype(int)
    df["ciiu"] = df["ciiu2"].astype(str)

    nombres = {
        "47": "Comercio", "56": "Alojamiento y comida", "41": "Construccion",
        "01": "Agricultura", "49": "Transporte", "10": "Alimentos",
        "26": "Informatica", "62": "Tecnologia", "20": "Quimicos",
        "21": "Farmaceuticos", "35": "Energia", "28": "Maquinaria",
        "29": "Vehiculos", "25": "Productos metalicos", "13": "Textiles",
        "14": "Prendas de vestir", "11": "Bebidas", "42": "Obras civiles",
        "00": "Sin clasificar", "02": "Silvicultura", "03": "Pesca",
        "05": "Carbon", "06": "Petroleo", "31": "Muebles", "32": "Otros manuf",
        "33": "Reparaciones", "43": "Construc especializada", "45": "Comercio vehiculos",
        "46": "Comercio mayorista", "50": "Transporte agua", "51": "Transporte aereo",
        "52": "Almacenamiento", "53": "Correo y mensajeria", "68": "Inmobiliarias",
        "70": "Consultoria", "73": "Publicidad", "82": "Servicios administrativos",
        "86": "Salud humana", "93": "Deportes y recreacion", "94": "Asociaciones",
        "96": "Servicios personales",
    }

    anual = df.groupby(["anio", "ciiu"])["empresas_nuevas"].sum().reset_index()
    ultimo_anio = anual["anio"].max()

    # Top 10 sectores por empresas nuevas en el ultimo ano
    top = anual[anual["anio"] == ultimo_anio].nlargest(10, "empresas_nuevas")

    tendencias = []
    for _, row_top in top.iterrows():
        sec = row_top["ciiu"]
        hist = anual[anual["ciiu"] == sec].sort_values("anio")
        puntos = [{"ano": int(r["anio"]), "empresas": int(r["empresas_nuevas"])} for _, r in hist.iterrows()]
        if len(puntos) >= 2:
            delta = ((puntos[-1]["empresas"] - puntos[0]["empresas"]) / puntos[0]["empresas"]) * 100
        else:
            delta = 0
        tendencias.append({
            "sector": nombres.get(sec, f"Sector {sec}"),
            "ciiu": sec,
            "empresas_nuevas_ultimo_ano": int(row_top["empresas_nuevas"]),
            "variacion_pct": round(delta, 1),
            "datos": puntos,
        })

    return {
        "sectores": sorted(tendencias, key=lambda s: -s["empresas_nuevas_ultimo_ano"]),
        "periodo": f"{df['anio'].min()}-{ultimo_anio}",
    }


@router.get("/indice-prioridad")
async def get_indice_prioridad():
    """Indice compuesto 0-100 de prioridad de intervencion por departamento.
    Combina: informalidad (25%), desempleo (25%), DNP desempeno (20%), educacion (15%), ingreso (5%), tamano (10%)."""
    geih = pd.read_csv(DATA_PROCESSED / "geih_resumen_departamento.csv")
    desempleo = pd.read_csv(DATA_PROCESSED / "geih_desempleo_departamento.csv")
    dnp = pd.read_csv(DATA_PROCESSED / "dnp_desempeno_departamento.csv")
    rues = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")

    dnp_map = {}
    for _, r in dnp.iterrows():
        dnp_map[_norm_depto(r["departamento"])] = r.get("promedio_desempeno", 50)

    des_map = {}
    for _, r in desempleo.iterrows():
        dk = _norm_depto(r["departamento"])
        n = r.get("no_ocupados", 0) or 0
        if n:
            des_map[dk] = float(n)

    ultimo_anio = _ultimo_anio_rues(rues)
    nuevas_total_ultimo = rues[rues["anio_matricula"] == ultimo_anio]["empresas_nuevas"].sum()

    resultados = []
    for _, row in geih.iterrows():
        depto = row["departamento"]
        key = _norm_depto(depto)
        ocupados = row.get("ocupados", 0) or 0
        ingreso = row.get("ingreso_promedio", 0) or 0
        formalidad = (row.get("tasa_formalidad", 0) or 0) * 100 if float(row.get("tasa_formalidad", 0) or 0) < 1 else row.get("tasa_formalidad", 0)
        educacion = (row.get("pct_educacion_superior", 0) or 0) * 100 if float(row.get("pct_educacion_superior", 0) or 0) < 1 else row.get("pct_educacion_superior", 0)

        no_ocu = des_map.get(key, 0)
        tasa_des = round(no_ocu / (ocupados + no_ocu) * 100, 1) if (ocupados + no_ocu) > 0 else 0
        dnp_val = float(dnp_map.get(key, 50))
        dnp_penal = max(0, 100 - dnp_val)

        informalidad = max(0, 100 - (formalidad or 0))
        ingreso_norm = max(0, min(100, ingreso / 3_000_000 * 100)) if ingreso > 0 else 0
        pen_tamano = 0 if ocupados > 500_000 else 10

        contrib_informalidad = round(informalidad * 0.25, 1)
        contrib_desempleo = round(tasa_des * 0.25, 1)
        contrib_dnp = round(dnp_penal * 0.20, 1)
        contrib_educacion = round(max(0, 100 - educacion) * 0.15, 1)
        contrib_ingreso = round(max(0, 100 - ingreso_norm) * 0.05, 1)

        score = contrib_informalidad + contrib_desempleo + contrib_dnp + contrib_educacion + contrib_ingreso + pen_tamano
        score = round(max(20, min(85, score)))
        tag = "urgente" if score >= 70 else ("atencion" if score >= 50 else "estable")

        resultados.append({
            "departamento": depto,
            "indice_prioridad": score,
            "nivel": tag,
            "ocupados": round(ocupados),
            "ingreso_promedio": round(ingreso),
            "tasa_formalidad": round(formalidad, 1),
            "pct_educacion_superior": round(educacion, 1),
            "tasa_desempleo": round(tasa_des, 1),
            "dnp_desempeno": round(dnp_val, 1),
            "desglose": [
                f"Informalidad {round(informalidad)}% → {contrib_informalidad} pts" if informalidad > 0 else "",
                f"Desempleo {tasa_des}% → {contrib_desempleo} pts" if tasa_des > 0 else "",
                f"Gestión pública {round(dnp_val)}/100 → {contrib_dnp} pts" if dnp_val > 0 else "",
                f"Educación superior {round(educacion)}% → {contrib_educacion} pts",
                f"Ingreso promedio ${ingreso:,.0f} → {contrib_ingreso} pts" if ingreso > 0 else "",
                f"Territorio pequeño (+{pen_tamano} pts)" if pen_tamano > 0 else "",
            ],
        })

    return {
        "departamentos": sorted(resultados, key=lambda d: -d["indice_prioridad"]),
        "total_empresas_nuevas_nacional": int(nuevas_total_ultimo),
        "nota": "Indice compuesto: >70 urgente, 50-70 atencion, <50 estable.",
    }


# ============================================================================
# EMICRON v2 - Estructura del empleo informal por sector
# ============================================================================

@router.get("/micronegocios")
async def get_micronegocios(ano: int | None = None):
    """Estructura sectorial de micronegocios (EMICRON 2022-2024).
    Muestra cuantos micronegocios hay por sector (GRUPOS12), ingreso promedio,
    adopcion de internet y acceso a credito. Complementa los datos de empleo
    formal (PILA) con el empleo informal que PILA no captura."""
    try:
        if ano is None:
            r_ano = supabase.table("emicron_resumen_nacional_v2").select("ano").order("ano", desc=True).limit(1).execute()
            ano = r_ano.data[0]["ano"] if r_ano.data else 2024
        r = supabase.table("emicron_por_sector_v2").select("*").eq("ano", ano).order("micronegocios", desc=True).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"Sin datos EMICRON para {ano}")
        total = sum(int(row.get("micronegocios") or 0) for row in r.data)
        return {
            "ano": ano,
            "total_micronegocios": total,
            "sectores": [
                {
                    "grupos12": int(row.get("grupos12") or 0),
                    "sector": row.get("sector"),
                    "micronegocios": int(row.get("micronegocios") or 0),
                    "pct_participacion": round(int(row.get("micronegocios") or 0) / total * 100, 1) if total else 0,
                    "ingreso_promedio_mensual": int(row.get("ingreso_promedio") or 0),
                    "pct_usa_internet": row.get("pct_usa_internet"),
                    "pct_tiene_credito": row.get("pct_tiene_credito"),
                }
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/micronegocios/serie")
async def get_micronegocios_serie():
    """Evolucion de micronegocios por sector 2022-2024 (tendencia de creacion
    de microempresas por sector). Util para Prediccion y Observatorio."""
    try:
        r = supabase.table("emicron_por_sector_v2").select("*").order("grupos12").order("ano").execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Sin datos EMICRON sectoriales")
        # Agrupar por sector
        sectores = {}
        for row in r.data:
            g = int(row.get("grupos12") or 0)
            if g not in sectores:
                sectores[g] = {"sector": row.get("sector"), "serie": []}
            sectores[g]["serie"].append({
                "ano": int(row.get("ano") or 0),
                "micronegocios": int(row.get("micronegocios") or 0),
                "ingreso_promedio": int(row.get("ingreso_promedio") or 0),
            })
        # Calcular crecimiento 2022->ultimo ano
        resultado = []
        for g, info in sorted(sectores.items()):
            serie = info["serie"]
            if len(serie) >= 2:
                prim = serie[0]["micronegocios"]
                ult = serie[-1]["micronegocios"]
                crec = ((ult / prim) - 1) * 100 if prim else 0
            else:
                crec = None
            resultado.append({
                "grupos12": g,
                "sector": info["sector"],
                "serie": serie,
                "crecimiento_pct": round(crec, 1) if crec is not None else None,
            })
        return {"sectores": sorted(resultado, key=lambda x: x["crecimiento_pct"] or -999, reverse=True)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
