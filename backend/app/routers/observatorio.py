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


# ============================================================================
# Endpoints legacy (mantenidos por compatibilidad con Dashboard y vistas previas)
# ============================================================================

@router.get("/departamentos")
async def get_resumen_departamentos():
    """Devuelve resumen laboral por departamento (GEIH + desempleo)."""
    try:
        ocu = supabase.table("geih_resumen_departamento").select("*").execute()
        des = supabase.table("geih_desempleo_departamento").select("*").execute()
        df_ocu = pd.DataFrame(ocu.data)
        df_des = pd.DataFrame(des.data)
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
        ocu = supabase.table("geih_resumen_departamento").select("*").eq("departamento", departamento.upper()).execute()
        des = supabase.table("geih_desempleo_departamento").select("*").eq("departamento", departamento.upper()).execute()
        if not ocu.data:
            raise HTTPException(status_code=404, detail=f"Departamento {departamento} no encontrado")
        data = ocu.data[0]
        if des.data:
            data["no_ocupados"] = des.data[0].get("no_ocupados")
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
        depto_norm = _norm_depto(departamento)
        
        # Mapeo de nombre de departamento a código DIVIPOLA
        DEPTO_DIVIPOLA = {
            "BOGOTA": 11, "ANTIOQUIA": 5, "ATLANTICO": 8, "BOLIVAR": 13,
            "BOYACA": 15, "CALDAS": 17, "CAQUETA": 18, "CASANARE": 19,
            "CAUCA": 20, "CESAR": 21, "CHOCO": 27, "CORDOBA": 23,
            "CUNDINAMARCA": 25, "GUAINIA": 94, "GUAVIARE": 95, "HUILA": 41,
            "LA GUAJIRA": 44, "MAGDALENA": 47, "META": 50, "NARINO": 52,
            "NORTE DE SANTANDER": 54, "PUTUMAYO": 86, "QUINDIO": 63,
            "RISARALDA": 66, "ARCHIPIELAGO DE SAN ANDRES": 88, "SANTANDER": 68,
            "SUCRE": 70, "TOLIMA": 73, "VALLE DEL CAUCA": 76, "VAUPES": 97,
            "VICHADA": 99, "AMAZONAS": 91,
        }

        # Lista de departamentos disponibles para el selector
        DEPTOS_LISTA = sorted([{"nombre": nombre.title(), "codigo": codigo} for nombre, codigo in DEPTO_DIVIPOLA.items()], key=lambda x: x["nombre"])
        
        depto_id = DEPTO_DIVIPOLA.get(depto_norm)
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
            "departamento": depto_norm,
            "fuente": "DANE GEIH - Empleo por departamento y sector",
            "total_sectores": len(sectores),
            "periodo": sectores[0]["periodo"] if sectores else None,
            "sectores": sectores,
            "departamentos_disponibles": DEPTOS_LISTA,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectores-formales")
async def get_sectores_formales(limit: int = 50):
    """Top sectores por cotizantes formales (PILA)."""
    try:
        res = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(limit).execute()
        return {"sectores": res.data}
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
            "n": 0,
            "no_ocupados": 0,
        })
        for row in r_ocu.data:
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["n"] += 1
        for row in r_des.data:
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
            })

        # Agregar SNIES por depto normalizado
        snies_map = {}
        for row in r_snies.data:
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        # Agregar DNP por depto normalizado
        dnp_map = {}
        for row in r_dnp.data:
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
            "n": 0,
            "no_ocupados": 0,
        })
        for row in r_ocu.data:
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["n"] += 1
        for row in r_des.data:
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
            })

        snies_map = {}
        for row in r_snies.data:
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        dnp_map = {}
        for row in r_dnp.data:
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
            "n": 0,
            "no_ocupados": 0,
        })
        for row in r_ocu.data:
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["n"] += 1
        for row in r_des.data:
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
            })

        # Agregar SNIES por depto normalizado
        snies_map = {}
        for row in r_snies.data:
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        # Agregar DNP por depto normalizado
        dnp_map = {}
        for row in r_dnp.data:
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
            matching_rows_all = [r for r in r_ocu.data]
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
_NUCLEO_TO_CAT = {
    "TECNOLOGIA": ["SISTEMAS", "TELEMATICA", "ELECTRONICA", "INFORMATICA", "COMPUTACION"],
    "INGENIERIAS": ["INGENIERIA", "ARQUITECTURA", "CIVIL", "MECANICA", "INDUSTRIAL", "ALIMENTOS", "AGROINDUSTRIAL", "AMBIENTAL"],
    "SALUD": ["MEDICINA", "ENFERMERIA", "ODONTOLOGIA", "SALUD", "FARMACIA", "BACTERIOLOGIA", "NUTRICION", "OPTOMETRIA"],
    "EDUCACION": ["EDUCACION", "LICENCIATURA", "PEDAGOGIA", "FILOSOFIA", "HISTORIA", "LINGUISTICA", "IDIOMAS"],
    "ADMINISTRACION": ["ADMINISTRACION", "ECONOMIA", "CONTADURIA", "FINANZAS", "NEGOCIOS", "MERCADEO", "PUBLICIDAD", "COMERCIO"],
    "DERECHO": ["DERECHO", "JURISPRUDENCIA", "POLITICA", "RELACIONES INTERNACIONALES"],
    "ARTES": ["ARTE", "DISENO", "MUSICA", "TEATRO", "CINE", "COMUNICACION SOCIAL", "LITERATURA"],
    "AGROPECUARIO": ["AGRONOMIA", "ZOOTECNIA", "VETERINARIA", "AGRICOLA", "FORESTAL", "PESQUERA"],
    "CIENCIAS_BASICAS": ["MATEMATICAS", "FISICA", "QUIMICA", "BIOLOGIA", "GEOLOGIA", "ESTADISTICA", "ECOLOGIA"],
}

# Mapeo de CIIU 2 digitos -> categoria macro
_CIIU_TO_CAT = {
    "01": "AGROPECUARIO", "02": "AGROPECUARIO", "03": "AGROPECUARIO", "75": "AGROPECUARIO",
    "05": "AGROPECUARIO", "07": "AGROPECUARIO", "08": "AGROPECUARIO", "09": "AGROPECUARIO",
    "10": "INGENIERIAS", "11": "INGENIERIAS", "12": "INGENIERIAS",
    "13": "INGENIERIAS", "14": "INGENIERIAS", "15": "INGENIERIAS",
    "16": "INGENIERIAS", "17": "INGENIERIAS", "18": "INGENIERIAS", "19": "INGENIERIAS",
    "20": "INGENIERIAS", "21": "INGENIERIAS", "22": "INGENIERIAS", "23": "INGENIERIAS",
    "24": "INGENIERIAS", "25": "INGENIERIAS", "26": "INGENIERIAS", "27": "INGENIERIAS",
    "28": "INGENIERIAS", "29": "INGENIERIAS", "30": "INGENIERIAS", "31": "INGENIERIAS",
    "32": "INGENIERIAS", "33": "INGENIERIAS", "41": "INGENIERIAS", "42": "INGENIERIAS",
    "43": "INGENIERIAS", "71": "INGENIERIAS",
    "62": "TECNOLOGIA", "63": "TECNOLOGIA", "95": "TECNOLOGIA",
    "86": "SALUD", "87": "SALUD", "88": "SALUD",
    "85": "EDUCACION",
    "64": "ADMINISTRACION", "65": "ADMINISTRACION", "66": "ADMINISTRACION",
    "69": "ADMINISTRACION", "70": "ADMINISTRACION", "73": "ADMINISTRACION",
    "58": "ARTES", "59": "ARTES", "60": "ARTES", "90": "ARTES", "91": "ARTES", "93": "ARTES",
    "72": "CIENCIAS_BASICAS", "74": "CIENCIAS_BASICAS",
    "45": "ADMINISTRACION", "46": "ADMINISTRACION", "47": "ADMINISTRACION",
    "55": "ADMINISTRACION", "56": "ADMINISTRACION",
    "68": "ADMINISTRACION", "79": "ADMINISTRACION",
    "94": "ADMINISTRACION", "96": "ADMINISTRACION", "97": "ADMINISTRACION", "98": "ADMINISTRACION", "99": "ADMINISTRACION",
}


def _categoria_nucleo(nucleo: str) -> str:
    n = _norm(nucleo)
    for cat, keywords in _NUCLEO_TO_CAT.items():
        for kw in keywords:
            if kw in n:
                return cat
    return "OTROS"


def _categoria_ciiu(ciiu_code: str) -> str:
    code = str(ciiu_code).strip()
    if len(code) >= 2 and code[:2].isdigit():
        return _CIIU_TO_CAT.get(code[:2], "OTROS")
    return "OTROS"


@router.get("/brecha")
async def get_brecha_oferta_demanda():
    """Calcula la brecha entre formacion (SNIES matriculados) y empleo formal (PILA cotizantes).
    Retorna categorias con su share en oferta y demanda, e indice de desajuste."""
    try:
        # Oferta: SNIES matriculados por nucleo_conocimiento
        r_snies = supabase.table("snies_programas_matriculados").select("nucleo_conocimiento, matriculados").execute()
        oferta = defaultdict(float)
        for row in r_snies.data:
            cat = _categoria_nucleo(row.get("nucleo_conocimiento", ""))
            oferta[cat] += row.get("matriculados") or 0
        total_oferta = sum(oferta.values()) or 1

        # Demanda: PILA por codigo CIIU (2 digitos)
        r_pila = supabase.table("pila_resumen_sector").select("actividadeconomicadesc, total_cotizantes").execute()
        # Deduplicar sectores PILA (la tabla tiene filas repetidas por sector)
        pila_map = {}
        for row in r_pila.data:
            desc = row.get("actividadeconomicadesc", "")
            if desc not in pila_map:
                pila_map[desc] = row.get("total_cotizantes") or 0
        demanda = defaultdict(float)
        for desc, cotizantes in pila_map.items():
            ciiu = desc.split(" - ")[0].strip() if " - " in desc else desc.split()[0]
            cat = _categoria_ciiu(ciiu)
            demanda[cat] += cotizantes
        total_demanda = sum(demanda.values()) or 1

        # Combinar todas las categorias
        cats = set(oferta.keys()) | set(demanda.keys())
        brecha = []
        for cat in cats:
            oferta_share = (oferta.get(cat, 0) / total_oferta) * 100
            demanda_share = (demanda.get(cat, 0) / total_demanda) * 100
            desajuste = oferta_share - demanda_share  # positivo = sobre-oferta, negativo = sub-oferta
            brecha.append({
                "categoria": cat,
                "oferta_matriculados": round(oferta.get(cat, 0), 0),
                "demanda_cotizantes": round(demanda.get(cat, 0), 0),
                "oferta_share": round(oferta_share, 2),
                "demanda_share": round(demanda_share, 2),
                "desajuste": round(desajuste, 2),
                "tipo": "sobre-oferta" if desajuste > 2 else ("sub-oferta" if desajuste < -2 else "equilibrado"),
            })

        # Ordenar por desajuste absoluto
        brecha.sort(key=lambda x: abs(x["desajuste"]), reverse=True)

        # Top 5 sobre-oferta y top 5 sub-oferta
        sobre = sorted([b for b in brecha if b["desajuste"] > 0], key=lambda x: -x["desajuste"])[:5]
        sub = sorted([b for b in brecha if b["desajuste"] < 0], key=lambda x: x["desajuste"])[:5]

        return {
            "brecha_categorias": brecha,
            "top_sobre_oferta": sobre,
            "top_sub_oferta": sub,
            "totales": {
                "matriculados_snies": round(total_oferta, 0),
                "cotizantes_pila": round(total_demanda, 0),
            },
        }

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
                .limit(limit)
                .execute()
            )
            rows = r.data or []
            # Filtrar los que tienen variacion_pct no nula; completar con inscritos_2020
            con_var = [x for x in rows if x.get("variacion_pct") is not None]
            if len(con_var) < limit:
                restantes = limit - len(con_var)
                r2 = (
                    supabase.table("spe_ape_inscritos_ocupacion")
                    .select("*")
                    .order("inscritos_2020", desc=True)
                    .limit(restantes + 50)
                    .execute()
                )
                ids_vistos = {x["id"] for x in con_var}
                extras = [x for x in r2.data if x["id"] not in ids_vistos][:restantes]
                rows = con_var + extras
            else:
                rows = con_var[:limit]
        except Exception:
            r = (
                supabase.table("spe_ape_inscritos_ocupacion")
                .select("*")
                .order("inscritos_2020", desc=True)
                .limit(limit)
                .execute()
            )
            rows = r.data
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
        ocu_rows = [r for r in r_ocu.data if _norm_depto(r["departamento"]) == depto_norm]
        des_rows = [r for r in r_des.data if _norm_depto(r["departamento"]) == depto_norm]

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
        snies_row = next((r for r in r_snies.data if _norm_depto(r["departamento"]) == depto_norm), None)
        dnp_row = next((r for r in r_dnp.data if _norm_depto(r["departamento"]) == depto_norm), None)

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
        ocu_rows = [r for r in r_ocu.data if _norm_depto(r.get("departamento", "")) == depto_norm]
        des_rows = [r for r in r_des.data if _norm_depto(r.get("departamento", "")) == depto_norm]

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
        # Top 5 sectores por empleo del ultimo mes
        periodo = ultima.get("periodo")
        r_sec = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("empleo", desc=True).limit(5).execute()
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
            "top_sectores_empleo": [
                {"rama_ciiu": s.get("rama_ciiu"), "empleo": int(s.get("empleo") or 0), "salario_promedio": int(s.get("salario_promedio") or 0)}
                for s in r_sec.data
            ],
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
        r_sec = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("empleo", desc=True).limit(5).execute() if periodo else {"data": []}
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
            "top_sectores_empleo": [
                {"rama_ciiu": s.get("rama_ciiu"), "empleo": int(s.get("empleo") or 0), "salario_promedio": int(s.get("salario_promedio") or 0)}
                for s in r_sec.data
            ],
        }

        # 2. Tendencia de empleo (CSV local)
        tendencia = _calcular_tendencia_empleo()

        # 3. Sectores emergentes (CSV local)
        emergentes = _calcular_sectores_emergentes()

        # 4. Indice de prioridad (CSV local)
        prioridad = _calcular_indice_prioridad()

        # 5. Brecha oferta-demanda (Supabase)
        brecha = _calcular_brecha_oferta_demanda()

        # 6. Sectores formales (Supabase)
        r_formal = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(50).execute()
        formales = {"sectores": r_formal.data or []}

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
    try:
        df = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")
        df = df[df["anio_matricula"] <= 2026]
        df = df[df["anio_matricula"] >= 2018]
        if df.empty:
            return {"sectores": [], "periodo": ""}
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
        ultimo_anio = int(anual["anio"].max()) if not anual.empty else 0
        if ultimo_anio < 2018 or anual.empty:
            return {"sectores": [], "periodo": ""}
        top = anual[anual["anio"] == ultimo_anio].nlargest(10, "empresas_nuevas")
        tendencias = []
        for _, row_top in top.iterrows():
            sec = str(row_top["ciiu"])
            hist = anual[anual["ciiu"] == sec].sort_values("anio")
            puntos = [{"ano": int(row["anio"]), "empresas": int(row["empresas_nuevas"])} for row in hist.to_dict("records")]
            delta = ((puntos[-1]["empresas"] - puntos[0]["empresas"]) / puntos[0]["empresas"]) * 100 if len(puntos) >= 2 else 0
            tendencias.append({
                "sector": nombres.get(sec, f"Sector {sec}"),
                "ciiu": sec,
                "empresas_nuevas_ultimo_ano": int(row_top["empresas_nuevas"]),
                "variacion_pct": round(delta, 1),
                "datos": puntos,
            })
        return {"sectores": sorted(tendencias, key=lambda s: -s["empresas_nuevas_ultimo_ano"]), "periodo": f"{int(df['anio'].min())}-{ultimo_anio}"}
    except Exception as e:
        print(f"[Dashboard] sectores-emergentes error: {e}")
        import traceback; traceback.print_exc()
        return {"sectores": [], "periodo": ""}


def _calcular_indice_prioridad():
    try:
        geih = pd.read_csv(DATA_PROCESSED / "geih_resumen_departamento.csv")
        rues = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")
        ultimo_anio = int(rues["anio_matricula"].max())
        nuevas_total_ultimo = rues[rues["anio_matricula"] == ultimo_anio]["empresas_nuevas"].sum()
        resultados = []
        for _, row in geih.iterrows():
            depto = row["departamento"]
            ocupados = row.get("ocupados", 0) or 0
            ingreso = row.get("ingreso_promedio", 0) or 0
            formalidad = (row.get("tasa_formalidad", 0) or 0) * 100 if row.get("tasa_formalidad", 0) < 1 else row.get("tasa_formalidad", 0)
            educacion = (row.get("pct_educacion_superior", 0) or 0) * 100 if row.get("pct_educacion_superior", 0) < 1 else row.get("pct_educacion_superior", 0)
            ingreso_norm = max(0, min(100, ingreso / 3_000_000 * 100)) if ingreso > 0 else 0
            score = (
                (100 - min(100, formalidad or 0)) * 0.35 +
                (100 - min(100, educacion or 0)) * 0.25 +
                (100 - ingreso_norm) * 0.25 +
                (0 if ocupados > 500_000 else 15)
            )
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
            })
        return {
            "departamentos": sorted(resultados, key=lambda d: -d["indice_prioridad"]),
            "total_empresas_nuevas_nacional": int(nuevas_total_ultimo),
            "nota": "Indice compuesto: >70 urgente, 50-70 atencion, <50 estable.",
        }
    except Exception as e:
        print(f"[Dashboard] indice-prioridad error: {e}")
        return {"departamentos": [], "total_empresas_nuevas_nacional": 0, "nota": ""}


def _calcular_brecha_oferta_demanda():
    try:
        r_snies = supabase.table("snies_programas_matriculados").select("nucleo_conocimiento, matriculados").execute()
        oferta = defaultdict(float)
        for row in r_snies.data or []:
            cat = _categoria_nucleo(row.get("nucleo_conocimiento", ""))
            oferta[cat] += row.get("matriculados") or 0
        total_oferta = sum(oferta.values()) or 1
        r_pila = supabase.table("pila_resumen_sector").select("actividadeconomicadesc, total_cotizantes").execute()
        pila_map = {}
        for row in r_pila.data or []:
            desc = row.get("actividadeconomicadesc", "")
            if desc not in pila_map:
                pila_map[desc] = row.get("total_cotizantes") or 0
        demanda = defaultdict(float)
        for desc, cotizantes in pila_map.items():
            ciiu = desc.split(" - ")[0].strip() if " - " in desc else desc.split()[0]
            cat = _categoria_ciiu(ciiu)
            demanda[cat] += cotizantes
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
                "demanda_cotizantes": round(demanda.get(cat, 0), 0),
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
            "totales": {"matriculados_snies": round(total_oferta, 0), "cotizantes_pila": round(total_demanda, 0)},
        }
    except Exception as e:
        print(f"[Dashboard] brecha error: {e}")
        return {"brecha_categorias": [], "top_sobre_oferta": [], "top_sub_oferta": [], "totales": {"matriculados_snies": 0, "cotizantes_pila": 0}}


def _calcular_spe_demanda(limit: int):
    try:
        try:
            r = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("variacion_pct", desc=True, nullsfirst=False).limit(limit).execute()
            rows = r.data or []
            con_var = [x for x in rows if x.get("variacion_pct") is not None]
            if len(con_var) < limit:
                restantes = limit - len(con_var)
                r2 = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(restantes + 50).execute()
                ids_vistos = {x["id"] for x in con_var}
                extras = [x for x in r2.data if x["id"] not in ids_vistos][:restantes]
                rows = con_var + extras
            else:
                rows = con_var[:limit]
        except Exception:
            r = supabase.table("spe_ape_inscritos_ocupacion").select("*").order("inscritos_2020", desc=True).limit(limit).execute()
            rows = r.data or []
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
            "n": 0,
            "no_ocupados": 0,
        })
        for row in r_ocu.data or []:
            d = row["departamento"]
            agg[d]["departamento"] = d
            agg[d]["ocupados"] += row.get("ocupados") or 0
            agg[d]["sum_ingreso_prom"] += (row.get("ingreso_promedio") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_ingreso_med"] += (row.get("ingreso_mediano") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_formalidad"] += (row.get("tasa_formalidad") or 0) * (row.get("ocupados") or 0)
            agg[d]["sum_mujeres_ocu"] += (row.get("mujeres_pct") or 0) * (row.get("ocupados") or 0)
            agg[d]["n"] += 1
        for row in r_des.data or []:
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
            })

        snies_map = {}
        for row in r_snies.data or []:
            key = _norm_depto(row["departamento"])
            snies_map[key] = (snies_map.get(key, 0) or 0) + (row.get("matriculados") or 0)
        for d in departamentos:
            d["matriculados_snies"] = round(snies_map.get(d["departamento_norm"], 0), 0)

        dnp_map = {}
        for row in r_dnp.data or []:
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
        print(f"[Dashboard] mapa-metricas error: {e}")
        return {"departamentos": [], "total": 0, "sector_lider_nacional": None}


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
    Combina: desempleo, informalidad, educacion, nuevas empresas y desempeno DNP."""
    geih = pd.read_csv(DATA_PROCESSED / "geih_resumen_departamento.csv")
    rues = pd.read_csv(DATA_PROCESSED / "rues_empresas_nuevas.csv")

    # Empresas nuevas por depto (RUES no tiene depto. Usar geih como proxy territorial)
    ultimo_anio = int(rues["anio_matricula"].max())
    nuevas_total_ultimo = rues[rues["anio_matricula"] == ultimo_anio]["empresas_nuevas"].sum()

    resultados = []
    for _, row in geih.iterrows():
        depto = row["departamento"]
        ocupados = row.get("ocupados", 0) or 0
        ingreso = row.get("ingreso_promedio", 0) or 0
        formalidad = (row.get("tasa_formalidad", 0) or 0) * 100 if row.get("tasa_formalidad", 0) < 1 else row.get("tasa_formalidad", 0)
        educacion = (row.get("pct_educacion_superior", 0) or 0) * 100 if row.get("pct_educacion_superior", 0) < 1 else row.get("pct_educacion_superior", 0)

        # Score: a menor formalidad/ingreso/educacion, mayor urgencia
        ingreso_norm = max(0, min(100, ingreso / 3_000_000 * 100)) if ingreso > 0 else 0
        score = (
            (100 - min(100, formalidad or 0)) * 0.35 +
            (100 - min(100, educacion or 0)) * 0.25 +
            (100 - ingreso_norm) * 0.25 +
            (0 if ocupados > 500_000 else 15)  # penalizar deptos pequeños
        )
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
        })

    return {
        "departamentos": sorted(resultados, key=lambda d: -d["indice_prioridad"]),
        "total_empresas_nuevas_nacional": int(nuevas_total_ultimo),
        "nota": "Indice compuesto: >70 urgente, 50-70 atencion, <50 estable.",
    }
