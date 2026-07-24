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
from app.data.ciuo_nombres import obtener_nombre_ciuo

router = APIRouter(prefix="/api/prediccion", tags=["Predicción IA"])

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "predicciones_mundiales.json"


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
    """Proyección salarial nacional con Chronos T5 sobre salario promedio GEIH.

    El crecimiento_anual_pct proviene de Chronos (no de una constante fija).
    Incluye la serie completa del salario nacional proyectada (serie_salario_nacional).
    """
    data = _load_predictions()
    return data.get("salarios", {})


@router.get("/geih-nacional")
async def geih_nacional():
    """Indicadores nacionales GEIH proyectados con TimesFM 2.5 + blend (serie mensual).

    Devuelve salario, empleo, desempleo e informalidad nacional con histórico
    anual (2022-2025) y proyección a 5 y 10 años (mediana + bandas p10-p90).
    """
    data = _load_predictions()
    geih = data.get("geih_nacional", {})
    if not geih:
        raise HTTPException(
            status_code=503,
            detail="Predicciones GEIH nacional no generadas. Ejecuta src/prediccion_chronos.py.",
        )
    return {
        "modelo": data.get("modelo"),
        "indicadores": geih,
        "anio_base_proyeccion": (data.get("sectores_geih") or {}).get("anio_base_proyeccion"),
        "metodologia": "TimesFM 2.5 200M (Google Research) + blend CAGR histórico 50/50 sobre serie mensual GEIH (DANE). Proyección mensual anualizada. Bandas p10-p90 de TimesFM. Acotado a -5%/+8% anual.",
    }


@router.get("/spe-vacantes")
async def spe_vacantes():
    """Demanda laboral del Servicio Publico de Empleo (SPE/UAESPE) 2015-2023.

    Tres dimensiones disponibles:
      - Por macro-grupo CIUO (1 digito): 9 ocupaciones + total nacional.
      - Por macro-seccion CIIU (letra A-U): 21 sectores + total nacional.
      - Por nivel educativo, rango salarial, experiencia: 9-15 categorias.

    Fuente: Anexo Estadistico de Demanda Laboral 2015-2023 (noviembre),
    publicado en agosto 2025 por la Unidad Administrativa Especial del SPE.
    Series anuales calculadas sumando los 12 meses de cada anio.
    """
    try:
        # Sectores (CIIU letras A-U) - formato: una fila por (seccion, anio, vacantes)
        r = supabase.table("spe_vacantes_sector").select("*").execute()
        sectores = r.data or []

        # Ocupaciones (CIUO 1 digito) - formato: una fila por (id_dim, anio, total_AAAA)
        r = supabase.table("spe_ocupaciones_anual").select("*").execute()
        ocupaciones = r.data or []

        # Educacion
        r = supabase.table("spe_educacion_anual").select("*").execute()
        educacion = r.data or []

        # Salarios
        r = supabase.table("spe_salarios_anual").select("*").execute()
        salarios = r.data or []

        # Calcular crecimiento agrupando por seccion/ocupacion
        def _crecimiento_sectores(rows):
            vistos = {}
            for r in rows:
                k = r.get("seccion")
                if not k:
                    continue
                if k not in vistos:
                    vistos[k] = {"nombre": r.get("seccion_nombre", k), "anios": {}}
                anio = r.get("anio")
                val = r.get("vacantes")
                if anio and val is not None:
                    vistos[k]["anios"][anio] = val
            result = []
            for k, v in vistos.items():
                anios = sorted(v["anios"].keys())
                if not anios:
                    continue
                primer = anios[0]
                ultimo = anios[-1]
                inicio = v["anios"][primer]
                fin = v["anios"][ultimo]
                crec = ((fin - inicio) / inicio * 100) if inicio > 0 else 0
                result.append({
                    "label": k,
                    "nombre": v["nombre"],
                    "vacantes_inicio": inicio,
                    "vacantes_fin": fin,
                    "anio_inicio": primer,
                    "anio_fin": ultimo,
                    "crecimiento_pct": round(crec, 1),
                })
            return sorted(result, key=lambda x: -x["vacantes_fin"])

        def _crecimiento_ocupaciones(rows):
            vistos = {}
            for r in rows:
                k = r.get("nombre_dim")
                if not k:
                    continue
                if k not in vistos:
                    vistos[k] = {"anios": {}}
                # Buscar columnas total_AAAA
                for key, val in r.items():
                    if key.startswith("total_") and val is not None:
                        try:
                            anio = int(key.replace("total_", ""))
                            vistos[k]["anios"][anio] = float(val)
                        except (ValueError, TypeError):
                            pass
            result = []
            for k, v in vistos.items():
                anios = sorted(v["anios"].keys())
                if not anios:
                    continue
                primer = anios[0]
                ultimo = anios[-1]
                inicio = v["anios"][primer]
                fin = v["anios"][ultimo]
                crec = ((fin - inicio) / inicio * 100) if inicio > 0 else 0
                result.append({
                    "label": k,
                    "vacantes_inicio": inicio,
                    "vacantes_fin": fin,
                    "anio_inicio": primer,
                    "anio_fin": ultimo,
                    "crecimiento_pct": round(crec, 1),
                })
            return sorted(result, key=lambda x: -x["vacantes_fin"])

        sectores_con_crec = _crecimiento_sectores(sectores)
        ocupaciones_con_crec = _crecimiento_ocupaciones(ocupaciones)

        return {
            "fuente": "Unidad Administrativa Especial del Servicio Publico de Empleo (UAESPE) - Anexo Estadistico de Demanda Laboral 2015-2023 (publicado agosto 2025)",
            "periodo": "2015-2023",
            "ultima_actualizacion": "noviembre 2023",
            "sectores": sectores_con_crec,
            "ocupaciones": ocupaciones_con_crec,
            "educacion": educacion,
            "salarios": salarios,
            "metodologia": "Series anuales construidas sumando los 12 meses de cada anio del anexo estadistico del SPE. Los totales nacionales son la suma de todos los registros. Sectores corresponden a secciones CIIU (letra) y Ocupaciones a macro-grupos CIUO 1 digito.",
        }
    except Exception as e:
        print(f"[Prediccion] spe-vacantes error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spe-ocupaciones-detalle")
async def spe_ocupaciones_detalle():
    """Detalle de demanda SPE por ocupacion CIUO 1 digito x departamento x anio.

    Devuelve las 362 filas del anexo (33 deptos x 11 ocupaciones macro).
    Util para el modulo Match: que ocupaciones se demandan en cada departamento.
    """
    try:
        r = supabase.table("spe_ocupaciones_detalle_anual").select("*").execute()
        return {
            "total_filas": len(r.data or []),
            "ocupaciones": r.data or [],
            "metodologia": "Demanda de empleo por ocupacion (CIUO 1 digito) y departamento, 2015-2023. Fuente: UAESPE.",
        }
    except Exception as e:
        print(f"[Prediccion] spe-ocupaciones-detalle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectores-geih")
async def sectores_geih():
    """10 macrosectores colombianos proyectados con Chronos T5 sobre GEIH mensual."""
    data = _load_predictions()
    sg = data.get("sectores_geih", {})
    if not sg.get("sectores"):
        raise HTTPException(
            status_code=503,
            detail="Predicciones GEIH por sector no generadas. Ejecuta src/prediccion_chronos.py.",
        )
    return sg


@router.get("/salarios-reales")
async def salarios_reales_geih(limit: int = 500, ordenar_por: str = "empleo_total"):
    """Salarios reales por ocupación del DANE GEIH (406 ocupaciones).

    Datos oficiales de la Gran Encuesta Integrada de Hogares (GEIH) del DANE.
    Incluye salario promedio, mediano y empleo total por ocupación.

    Args:
        limit: Número máximo de ocupaciones a devolver (default 500 para traer todas)
        ordenar_por: Campo para ordenar ('empleo_total', 'salario_promedio', 'salario_mediano')
    """
    try:
        # Validar campo de ordenamiento
        campos_validos = ["empleo_total", "salario_promedio", "salario_mediano"]
        if ordenar_por not in campos_validos:
            ordenar_por = "empleo_total"

        # Consultar tabla geih_salario_ocupacion (cargada multiples veces en Supabase;
        # pedimos mas filas y deduplicamos por oficio_c8, igual que _dedup_pila/_dedup_spe).
        fetch_n = limit * 4
        r = supabase.table("geih_salario_ocupacion").select("*").order(ordenar_por, desc=True).limit(fetch_n).execute()

        if not r.data:
            raise HTTPException(status_code=404, detail="No hay datos de salarios en geih_salario_ocupacion")

        # Deduplicar por oficio_c8 conservando la primera ocurrencia (mayor segun el orden pedido)
        seen = set()
        ocupaciones = []
        for row in r.data:
            codigo = row.get("oficio_c8")
            if codigo is None or codigo in seen:
                continue
            seen.add(codigo)
            empleo = round(float(row.get("empleo_total") or 0), 0)
            muestra = int(row.get("ocupados_muestra") or 0)
            ventana = int(row.get("muestra_ventana") or muestra or 0)
            confianza = str(row.get("confianza") or "media").lower()
            ocupaciones.append({
                "oficio_codigo": codigo,
                "oficio_nombre": obtener_nombre_ciuo(codigo),
                "salario_promedio": round(float(row.get("salario_promedio") or 0), 0),
                "salario_mediano": round(float(row.get("salario_mediano") or 0), 0),
                "empleo_total": empleo,
                "ocupados_muestra": muestra,
                "muestra_ventana": ventana,
                "confianza": confianza,
                "periodo": row.get("periodo"),
            })
            if len(ocupaciones) >= limit:
                break

        return {
            "fuente": "DANE GEIH - Gran Encuesta Integrada de Hogares",
            "descripcion": "Salarios reales por ocupación (datos oficiales del DANE). Promedio móvil de los últimos 12 meses.",
            "total_ocupaciones": len(ocupaciones),
            "periodo": ocupaciones[0]["periodo"] if ocupaciones else None,
            "metodologia": "Promedio móvil 12 meses del ingreso laboral ponderado por factor de expansión FEX_C18. La confianza depende del tamaño de muestra real y del empleo estimado.",
            "ocupaciones": ocupaciones,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# NUEVOS ENDPOINTS: Predicciones Chronos T5 sobre GEIH mensual (52 meses)
# ============================================================================

GEIH_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "predicciones_geih.json"


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

        # D) Salarios por sector (GEIH - último periodo disponible).
        # La tabla geih_empleo_sector_mensual fue cargada multiples veces en Supabase
        # (cada rama aparece 3x por periodo); pedimos mas filas y deduplicamos por rama_ciiu.
        r_periodo = supabase.table("geih_empleo_sector_mensual").select("periodo").order("periodo", desc=True).limit(1).execute()
        periodo = r_periodo.data[0]["periodo"] if r_periodo.data else None
        top_salarios = []
        if periodo:
            r_sal = supabase.table("geih_empleo_sector_mensual").select("*").eq("periodo", periodo).order("salario_promedio", desc=True).limit(60).execute()
            seen_sal = set()
            for row in r_sal.data:
                codigo_raw = row.get("rama_ciiu")
                if codigo_raw is None or codigo_raw in seen_sal:
                    continue
                seen_sal.add(codigo_raw)
                codigo = str(codigo_raw).zfill(2)
                nombre = CIIU2_NAMES.get(codigo, f"CIIU {codigo}")
                top_salarios.append({
                    "sector": nombre,
                    "salario_promedio": int(row.get("salario_promedio", 0) or 0),
                    "empleo": int(row.get("empleo", 0) or 0),
                    "periodo": periodo,
                })
                if len(top_salarios) >= 15:
                    break

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

GEIH_SECTOR_PATH = Path(__file__).resolve().parents[2] / "data" / "processed" / "geih_empleo_sector_mensual.csv"


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
    """Proyección de TODOS los macrosectores colombianos con Chronos T5.

    Sirve las proyecciones pre-calculadas por Chronos en predicciones_mundiales.json
    (clave `sectores_geih`), generadas por src/prediccion_chronos.py sobre la serie
    mensual GEIH. Si el JSON no contiene la nueva estructura, cae a la heurística
    GEIH anterior (baseline 1.8% + 20% CAGR) como fallback.
    """
    try:
        pred = _load_predictions()
    except HTTPException:
        pred = {}

    sectores_geih = pred.get("sectores_geih") or {}

    # Rama principal: proyecciones Chronos pre-calculadas
    if sectores_geih.get("sectores"):
        return {
            "sectores": sectores_geih["sectores"],
            "periodo_historico": sectores_geih.get("periodo_historico", ""),
            "anio_base_proyeccion": sectores_geih.get("anio_base_proyeccion"),
            "ultimo_periodo": sectores_geih.get("ultimo_periodo", ""),
            "anio_actual_incompleto": sectores_geih.get("anio_actual_incompleto"),
            "chronos_baseline_pct": round(pred.get("salarios", {}).get("crecimiento_anual_pct", 0), 2),
            "baseline_empleo_pct": None,
            "metodologia": sectores_geih.get("metodologia",
                "Chronos T5 Small sobre serie mensual GEIH (DANE). Proyección mensual anualizada por bloques de 12 meses."),
            "motor_prediccion": "chronos_t5",
        }

    # Fallback: heurística GEIH (si el JSON no tiene sectores_geih todavía)
    if not GEIH_SECTOR_PATH.exists():
        raise HTTPException(status_code=503, detail="Datos GEIH no disponibles y predicciones Chronos no generadas")

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
        "periodo_historico": f"{min(anios_completos)}-{max(anios_completos)}",
        "anio_base_proyeccion": ultimo_ano_completo,
        "ultimo_periodo": ultimo_periodo_str,
        "anio_actual_incompleto": ultimo_ano_crudo if ultimo_ano_crudo != ultimo_ano_completo else None,
        "chronos_baseline_pct": round(chronos_baseline * 100, 1),
        "baseline_empleo_pct": round(baseline_empleo * 100, 1),
        "metodologia": "Fallback heurístico: 80% crecimiento base del empleo (1.8% anual) + 20% tendencia real GEIH. Cap 0.5%-4% anual.",
        "motor_prediccion": "heuristica_geih",
    }


@router.get("/micronegocios-tendencia")
async def get_micronegocios_tendencia():
    """Tendencia de creacion de microempresas por sector (EMICRON 2022-2024).
    Identifica sectores donde el emprendimiento informal esta creciendo o
    decayendo, como señal temprana de demanda emergente."""
    try:
        r = supabase.table("emicron_por_sector_v2").select("*").order("grupos12").order("ano").execute()
        if not r.data:
            raise HTTPException(status_code=404, detail="Sin datos EMICRON sectoriales")
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
        resultado = []
        for g, info in sorted(sectores.items()):
            serie = info["serie"]
            if len(serie) >= 2:
                prim = serie[0]["micronegocios"]
                ult = serie[-1]["micronegocios"]
                crec = ((ult / prim) - 1) * 100 if prim else 0
                # Tendencia: creciendo, estable, decayendo
                if crec > 5:
                    tendencia = "creciendo"
                elif crec < -5:
                    tendencia = "decayendo"
                else:
                    tendencia = "estable"
            else:
                crec = None
                tendencia = "datos_insuficientes"
            resultado.append({
                "grupos12": g,
                "sector": info["sector"],
                "serie": serie,
                "crecimiento_pct": round(crec, 1) if crec is not None else None,
                "tendencia": tendencia,
            })
        return {
            "sectores": sorted(resultado, key=lambda x: x["crecimiento_pct"] or -999, reverse=True),
            "periodo": f"{serie[0]['ano']}-{serie[-1]['ano']}" if serie else "",
            "nota": "Tendencia basada en EMICRON (DANE). creciendo >+5%, estable ±5%, decayendo <-5%.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
