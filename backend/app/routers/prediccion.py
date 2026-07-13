"""
Router del módulo Predicción IA.
Expone predicciones de sectores, profesiones, habilidades y salarios
entrenadas con Chronos T5 sobre datos mundiales (World Bank) + GEIH mensual.
"""
import json
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from app.db.supabase import supabase
from app.services.llm_gemini import generar_insights_prediccion, is_gemini_available

router = APIRouter(prefix="/api/prediccion", tags=["Predicción IA"])

DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "predicciones_mundiales.json"


def _load_predictions() -> dict[str, Any]:
    if not DATA_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Predicciones no generadas. Ejecuta prediccion_chronos.py primero.",
        )
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/resumen")
async def resumen():
    """Metadata del modelo, horizontes e insights."""
    data = _load_predictions()
    insights = data.get("insights", {})
    # Refrescar insights con Gemini si es posible
    if is_gemini_available() and not insights:
        try:
            insights = generar_insights_prediccion(
                data.get("sectores_cagr_5a", {}),
                data.get("profesiones", []),
                data.get("habilidades", []),
            )
        except Exception as e:
            print(f"[Prediccion] Gemini insights falló: {e}")
    return {
        "modelo": data.get("modelo"),
        "pais": data.get("pais"),
        "fuente": data.get("fuente"),
        "ultimo_año_historico": data.get("ultimo_año_historico"),
        "horizontes": data.get("horizontes"),
        "sectores_cagr_5a": data.get("sectores_cagr_5a", {}),
        "otros_indicadores": data.get("otros_indicadores", {}),
        "insights": insights,
    }


@router.get("/sectores")
async def sectores():
    """Predicción de participación sectorial del empleo (%)."""
    data = _load_predictions()
    return data.get("sectores", {})


@router.get("/profesiones")
async def profesiones():
    """Ranking de profesiones proyectadas a 5 y 10 años."""
    data = _load_predictions()
    return {"profesiones": data.get("profesiones", [])}


@router.get("/habilidades")
async def habilidades():
    """Ranking de habilidades con mayor demanda futura."""
    data = _load_predictions()
    return {"habilidades": data.get("habilidades", [])}


@router.get("/salarios")
async def salarios():
    """Proyección salarial proxy basada en PIB por empleado."""
    data = _load_predictions()
    return data.get("salarios", {})


@router.get("/salarios-reales")
async def salarios_reales_geih(limit: int = 50, ordenar_por: str = "empleo_total"):
    """Salarios reales por ocupación del DANE GEIH (406 ocupaciones).
    
    Datos oficiales de la Gran Encuesta Integrada de Hogares (GEIH) del DANE.
    Incluye salario promedio, mediano y empleo total por ocupación.
    
    Args:
        limit: Número máximo de ocupaciones a devolver (default 50)
        ordenar_por: Campo para ordenar ('empleo_total', 'salario_promedio', 'salario_mediano')
    """
    try:
        # Validar campo de ordenamiento
        campos_validos = ["empleo_total", "salario_promedio", "salario_mediano"]
        if ordenar_por not in campos_validos:
            ordenar_por = "empleo_total"
        
        # Consultar tabla geih_salario_ocupacion
        r = supabase.table("geih_salario_ocupacion").select("*").order(ordenar_por, desc=True).limit(limit).execute()
        
        if not r.data:
            raise HTTPException(status_code=404, detail="No hay datos de salarios en geih_salario_ocupacion")
        
        # Procesar resultados
        ocupaciones = []
        for row in r.data:
            ocupaciones.append({
                "oficio_codigo": row.get("oficio_c8"),
                "salario_promedio": round(float(row.get("salario_promedio") or 0), 0),
                "salario_mediano": round(float(row.get("salario_mediano") or 0), 0),
                "empleo_total": round(float(row.get("empleo_total") or 0), 0),
                "ocupados_muestra": int(row.get("ocupados_muestra") or 0),
                "periodo": row.get("periodo"),
            })
        
        return {
            "fuente": "DANE GEIH - Gran Encuesta Integrada de Hogares",
            "descripcion": "Salarios reales por ocupación (datos oficiales del DANE)",
            "total_ocupaciones": len(ocupaciones),
            "periodo": ocupaciones[0]["periodo"] if ocupaciones else None,
            "ocupaciones": ocupaciones,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NUEVOS ENDPOINTS: Predicciones Chronos T5 sobre GEIH mensual (52 meses)
# ============================================================================

GEIH_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "predicciones_geih.json"


def _load_geih_predictions() -> dict[str, Any]:
    if not GEIH_PATH.exists():
        raise HTTPException(
            status_code=503,
            detail="Predicciones GEIH no generadas.",
        )
    with open(GEIH_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/geih")
async def geih_full():
    """Predicciones mensuales GEIH completas (desempleo, informalidad, salario, sectores)."""
    return _load_geih_predictions()


@router.get("/geih/desempleo")
async def prediccion_desempleo_geih(horizonte: str = "prediccion_1ano"):
    """Prediccion de desempleo nacional con Chronos T5 sobre 52 meses de GEIH.
    horizonte: 'prediccion_1ano' (12 meses) o 'prediccion_5anos' (60 meses)."""
    try:
        r = supabase.table("predicciones_geih").select("*").eq("tipo", "desempleo_nacional").eq("horizonte", horizonte).order("periodo", desc=False).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay predicciones para horizonte {horizonte}")
        return {
            "tipo": "desempleo_nacional",
            "horizonte": horizonte,
            "modelo": "Chronos T5 Small",
            "total_puntos": len(r.data),
            "predicciones": [
                {"periodo": row.get("periodo"), "mediana": row.get("mediana"), "p10": row.get("p10"), "p90": row.get("p90")}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/geih/sector/{rama_ciiu}")
async def prediccion_sector_geih(rama_ciiu: str, horizonte: str = "prediccion_1ano"):
    """Prediccion de empleo por sector CIIU con Chronos T5."""
    try:
        r = supabase.table("predicciones_geih").select("*").eq("tipo", f"sector_{rama_ciiu}").eq("horizonte", horizonte).order("periodo", desc=False).execute()
        if not r.data:
            raise HTTPException(status_code=404, detail=f"No hay predicciones para sector {rama_ciiu}")
        return {
            "tipo": f"sector_{rama_ciiu}",
            "horizonte": horizonte,
            "modelo": "Chronos T5 Small",
            "total_puntos": len(r.data),
            "predicciones": [
                {"periodo": row.get("periodo"), "mediana": row.get("mediana"), "p10": row.get("p10"), "p90": row.get("p90")}
                for row in r.data
            ],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NUEVOS ENDPOINTS: Dashboards de sectores (PILA + RUES + GEIH)
# ============================================================================

CIIU2_NAMES = {
    "01": "Agricultura, ganadería y caza", "02": "Silvicultura y madera",
    "03": "Pesca y acuicultura", "05": "Extracción de carbón",
    "06": "Extracción de petróleo y gas", "07": "Minería de metales",
    "08": "Otras minas y canteras", "09": "Actividades de apoyo a la minería",
    "10": "Elaboración de alimentos", "11": "Elaboración de bebidas",
    "12": "Fabricación de tabaco", "13": "Fabricación de textiles",
    "14": "Confección de prendas", "15": "Curtido de cueros",
    "16": "Transformación de madera", "17": "Fabricación de papel",
    "18": "Impresión y reproducción", "19": "Coque y refinería de petróleo",
    "20": "Sustancias y productos químicos", "21": "Productos farmacéuticos",
    "22": "Productos de caucho y plástico", "23": "Productos minerales no metálicos",
    "24": "Metales básicos", "25": "Productos metálicos",
    "26": "Equipos informáticos y electrónicos", "27": "Aparatos eléctricos",
    "28": "Maquinaria y equipo", "29": "Vehículos automotores",
    "30": "Otros equipos de transporte", "31": "Fabricación de muebles",
    "32": "Otras industrias manufactureras", "33": "Reparación de maquinaria",
    "35": "Electricidad, gas y vapor", "36": "Captación y distribución de agua",
    "37": "Evacuación de aguas residuales", "38": "Recogida y tratamiento de desechos",
    "39": "Actividades de saneamiento", "41": "Construcción de edificios",
    "42": "Ingeniería civil", "43": "Actividades especializadas de construcción",
    "45": "Venta y reparación de vehículos", "46": "Comercio al por mayor",
    "47": "Comercio al por menor", "49": "Transporte terrestre y por tuberías",
    "50": "Transporte acuático", "51": "Transporte aéreo",
    "52": "Almacenamiento y transporte complementario", "53": "Actividades postales y mensajería",
    "55": "Alojamiento", "56": "Servicios de comida",
    "58": "Edición de software", "59": "Cine, radio y televisión",
    "60": "Programación y transmisión", "61": "Telecomunicaciones",
    "62": "Desarrollo de software", "63": "Servicios de información",
    "64": "Servicios financieros", "65": "Seguros",
    "66": "Actividades auxiliares financieras", "68": "Actividades inmobiliarias",
    "69": "Actividades jurídicas y contabilidad", "70": "Consultoría y gestión",
    "71": "Servicios técnicos y arquitectura", "72": "Investigación científica",
    "73": "Publicidad y estudios de mercado", "74": "Otras actividades profesionales",
    "75": "Actividades veterinarias", "77": "Alquiler de maquinaria",
    "78": "Actividades de empleo", "79": "Agencias de viaje",
    "80": "Seguridad e investigación", "81": "Servicios a edificios",
    "82": "Actividades administrativas de oficina", "84": "Administración pública y defensa",
    "85": "Educación", "86": "Servicios de salud humana",
    "87": "Asistencia social con alojamiento", "88": "Asistencia social sin alojamiento",
    "90": "Actividades creativas y artísticas", "91": "Bibliotecas y museos",
    "92": "Juegos de azar", "93": "Actividades deportivas y recreativas",
    "94": "Actividades de asociaciones", "95": "Reparación de computadores",
    "96": "Otros servicios personales", "97": "Actividades de los hogares",
    "98": "Actividades no diferenciadas de los hogares", "99": "Organizaciones extraterritoriales",
}


def _clean_sector_name(name: str) -> str:
    if not name:
        return "N/D"
    if " - " in name:
        return name.split(" - ", 1)[-1].strip().title()
    return name.strip().title()


@router.get("/sectores-dashboards")
async def sectores_dashboards():
    """3 dashboards de sectores: empleo formal (PILA), emergentes (RUES) y salarios (GEIH)."""
    try:
        from collections import defaultdict

        # A) Top sectores por empleo formal (PILA)
        pila = supabase.table("pila_resumen_sector").select("*").execute()
        pila_map = {}
        for row in pila.data:
            desc = row.get("actividadeconomicadesc", "")
            cotizantes = row.get("total_cotizantes", 0) or 0
            if desc not in pila_map:
                pila_map[desc] = cotizantes
            else:
                pila_map[desc] = max(pila_map[desc], cotizantes)

        top_empleo = [
            {"sector": _clean_sector_name(desc), "cotizantes": int(cot)}
            for desc, cot in sorted(pila_map.items(), key=lambda x: x[1], reverse=True)[:15]
        ]

        # B) Sectores emergentes (RUES - nuevas empresas últimos 3 años)
        rues = supabase.table("rues_empresas_nuevas").select("*").execute()
        empresas_por_ciiu2 = defaultdict(int)
        for row in rues.data:
            anio = row.get("anio_matricula", 0)
            if anio and anio >= 2023:
                ciiu2 = str(row.get("ciiu2", "")).zfill(2)
                empresas = row.get("empresas_nuevas", 0) or 0
                empresas_por_ciiu2[ciiu2] += empresas

        top_emergentes = [
            {
                "sector": CIIU2_NAMES.get(ciiu2, f"CIIU {ciiu2}"),
                "empresas_nuevas": total,
            }
            for ciiu2, total in sorted(empresas_por_ciiu2.items(), key=lambda x: x[1], reverse=True)[:15]
        ]

        # D) Salarios por sector (GEIH - último periodo disponible)
        r_periodo = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
        periodo = r_periodo.data[0]["periodo"] if r_periodo.data else None
        top_salarios = []
        if periodo:
            r_sal = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("salario_promedio", desc=True).limit(15).execute()
            for row in r_sal.data:
                codigo = str(row.get("rama_ciiu", "")).zfill(2)
                nombre = CIIU2_NAMES.get(codigo, f"CIIU {codigo}")
                top_salarios.append({
                    "sector": nombre,
                    "salario_promedio": int(row.get("salario_promedio", 0) or 0),
                    "empleo": int(row.get("empleo", 0) or 0),
                    "periodo": periodo,
                })

        return {
            "top_empleo": top_empleo,
            "top_emergentes": top_emergentes,
            "top_salarios": top_salarios,
            "periodo_salarios": periodo,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Proyección de TODOS los macrosectores colombianos (GEIH + Chronos T5)
# ============================================================================

GEIH_SECTOR_PATH = Path(__file__).resolve().parents[3] / "data" / "processed" / "geih_empleo_sector_mensual.csv"


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


@router.get("/todos-los-sectores")
async def get_todos_los_sectores():
    """Proyeccion de TODOS los macrosectores colombianos.
    Combina tendencia historica real del GEIH (2022-2026) con Chronos T5 baseline."""
    if not GEIH_SECTOR_PATH.exists():
        raise HTTPException(status_code=503, detail="Datos GEIH no disponibles")

    df = pd.read_csv(GEIH_SECTOR_PATH)
    df["ano"] = df["ano"].astype(int)
    df["mes"] = df["mes"].astype(int)
    ci = df["rama_ciiu"].fillna(0).astype(int)
    df["macrosector"] = ci.apply(_macrosector_name)

    # Agrupación anual con promedio mensual real (divide por meses disponibles)
    anual = df.groupby(["ano", "macrosector"]).agg(
        empleo=("empleo", "sum"), meses=("mes", "nunique")
    ).reset_index()
    anual["empleo_prom"] = anual["empleo"] / anual["meses"]

    # Detectar años completos (12 meses) vs parciales. Usamos el último año
    # completo como base para la proyección para no sesgar por datos parciales.
    meses_por_ano = df.groupby("ano")["mes"].nunique().to_dict()
    anios_completos = [a for a, m in meses_por_ano.items() if m >= 12]
    ultimo_ano_completo = max(anios_completos) if anios_completos else int(anual["ano"].max())
    ultimo_ano_crudo = int(anual["ano"].max())
    primero_ano = int(anual["ano"].min())

    # Último periodo real disponible en el dataset
    ultimo_periodo = df.sort_values(["ano", "mes"]).iloc[-1]
    ultimo_periodo_str = f"{int(ultimo_periodo['ano']):04d}-{int(ultimo_periodo['mes']):02d}"

    pred = _load_predictions()
    chronos_baseline = pred.get("salarios", {}).get("crecimiento_anual_pct", 3.5) / 100

    # Baseline realista de empleo: ~1.8% anual en Colombia (crecimiento población + participación laboral)
    # Chronos 3.5% es para salarios; para empleo usamos un baseline menor.
    baseline_empleo = 0.018

    sectores = []
    for sec in sorted(anual["macrosector"].unique()):
        hist = anual[anual["macrosector"] == sec].sort_values("ano")

        # Serie histórica: solo años completos (12 meses). El año parcial actual
        # (ej. 2026 con datos hasta abril) queda fuera de la serie para no duplicar
        # el punto de inicio de la proyección; se reporta en los metadatos.
        serie_historica = [
            {"ano": int(row["ano"]), "empleo": int(round(row["empleo_prom"]))}
            for _, row in hist.iterrows()
            if int(row["ano"]) in anios_completos
        ]

        # CAGR histórico: comparar primer año completo vs último año completo
        hist_completo = hist[hist["ano"].isin(anios_completos)].sort_values("ano")
        if len(hist_completo) >= 2:
            first = float(hist_completo.iloc[0]["empleo_prom"])
            last_base = float(hist_completo.iloc[-1]["empleo_prom"])
            years = int(hist_completo.iloc[-1]["ano"]) - int(hist_completo.iloc[0]["ano"])
            cagr = ((last_base / first) ** (1 / years) - 1) if years > 0 and first > 0 else 0
        else:
            last_base = float(hist.iloc[-1]["empleo_prom"])
            cagr = 0

        # Blend conservador: 80% baseline empleo + 20% tendencia sectorial reciente
        # La tendencia post-COVID está inflada, por eso pesa poco
        crec_blend = baseline_empleo + (cagr - baseline_empleo) * 0.20
        crec_blend = max(0.005, min(0.04, crec_blend))  # cap 0.5% a 4% anual

        empleo_5y = last_base * ((1 + crec_blend) ** 5)
        empleo_10y = last_base * ((1 + crec_blend) ** 10)
        var_5y_pct = ((empleo_5y / last_base) - 1) * 100
        var_10y_pct = ((empleo_10y / last_base) - 1) * 100

        # La proyección parte del último año completo (2025) y llega 10 años adelante
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
        "periodo_historico": f"{min(anios_completos)}-{max(anios_completos)}",
        "anio_base_proyeccion": ultimo_ano_completo,
        "ultimo_periodo": ultimo_periodo_str,
        "anio_actual_incompleto": ultimo_ano_crudo if ultimo_ano_crudo != ultimo_ano_completo else None,
        "chronos_baseline_pct": round(chronos_baseline * 100, 1),
        "baseline_empleo_pct": round(baseline_empleo * 100, 1),
        "metodologia": "80% crecimiento base del empleo en Colombia (1.8% anual) + 20% tendencia real GEIH. Proyección desde el último año completo disponible. Cap 0.5%-4% anual.",
    }
