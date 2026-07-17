"""
Router Observatorio para ALBA Offline.
Lee datos de SQLite local en lugar de Supabase.
"""
import unicodedata
from fastapi import APIRouter, HTTPException
from app.db.sqlite_db import query_all, query_sql, query_one
from app.data.ciiu_nombres import obtener_nombre_ciiu

router = APIRouter(prefix="/api/observatorio", tags=["observatorio"])


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
    if "BOGOTA" in s or s == "BOGOTA":
        return "BOGOTA"
    if "SAN ANDRES" in s or "ARCHIPIELAGO" in s or "PROVIDENCIA" in s or "SANTA CATALINA" in s:
        return "ARCHIPIELAGO DE SAN ANDRES"
    if s == "GUAJIRA":
        return "LA GUAJIRA"
    if s == "NARINIO":
        return "NARINO"
    return s


# Mapping nombre normalizado -> codigo DIVIPOLA (igual que la version online)
DEPTO_DIVIPOLA = {
    "BOGOTA": 11, "ANTIOQUIA": 5, "ATLANTICO": 8, "BOLIVAR": 13,
    "BOYACA": 15, "CALDAS": 17, "CAQUETA": 18, "CASANARE": 19,
    "CAUCA": 20, "CESAR": 21, "CHOCO": 27, "CORDOBA": 23,
    "CUNDINAMARCA": 25, "GUAINIA": 94, "GUAVIARE": 95, "HUILA": 41,
    "LA GUAJIRA": 44, "MAGDALENA": 47, "META": 50, "NARINO": 52,
    "NORTE DE SANTANDER": 54, "PUTUMAYO": 86, "QUINDIO": 63,
    "RISARALDA": 66, "ARCHIPIELAGO DE SAN ANDRES": 88, "SANTANDER": 68,
    "SUCRE": 70, "TOLIMA": 73, "VALLE DEL CAUCA": 76, "VAUPES": 97,
    "VICHADA": 99, "AMAZONAS": 91, "ARAUCA": 81,
}


@router.get("/resumen-nacional")
async def resumen_nacional():
    rows = query_sql(
        "SELECT * FROM geih_resumen_nacional ORDER BY periodo DESC LIMIT 1"
    )
    if not rows:
        return {"error": "No hay datos"}
    r = rows[0]
    return {
        "periodo": r.get("periodo"),
        "empleo_nacional": r.get("empleo_nacional"),
        "tasa_desempleo": r.get("tasa_desempleo_nacional"),
        "tasa_informalidad": r.get("tasa_informalidad_nacional"),
        "salario_promedio": r.get("salario_promedio_nacional"),
        "pea_nacional": r.get("pea_nacional"),
        "desempleados": r.get("desempleados_nacional"),
        "informales": r.get("informales_nacional"),
    }


@router.get("/tendencia-empleo")
async def tendencia_empleo():
    rows = query_sql(
        "SELECT periodo, ano, mes, empleo_nacional, tasa_desempleo_nacional, "
        "tasa_informalidad_nacional, salario_promedio_nacional "
        "FROM geih_resumen_nacional ORDER BY periodo"
    )
    return {"tendencia": rows}


@router.get("/empleo-departamento")
async def empleo_departamento():
    rows = query_sql(
        "SELECT departamento, SUM(ocupados) as ocupados "
        "FROM geih_resumen_departamento GROUP BY departamento "
        "ORDER BY ocupados DESC"
    )
    return {"departamentos": rows}


@router.get("/sectores-emergentes-tendencia")
async def sectores_emergentes():
    if query_sql("SELECT name FROM sqlite_master WHERE type='table' AND name='rues_sectores_emergentes'"):
        rows = query_all("rues_sectores_emergentes", limit=20)
    else:
        rows = query_all("rues_empresas_nuevas", limit=20)
    return {"sectores": rows}


@router.get("/sectores-formales")
async def sectores_formales():
    rows = query_all("pila_cotizantes", limit=20)
    return {"sectores": rows}


@router.get("/salarios")
async def salarios():
    rows = query_sql(
        "SELECT * FROM geih_salario_ocupacion ORDER BY salario_promedio DESC LIMIT 20"
    )
    return {"salarios": rows}


@router.get("/prioridad-intervencion")
async def prioridad_intervencion():
    rows = query_all("dnp_mdm", limit=33)
    return {"departamentos": rows}


@router.get("/departamentos/{depto}/sectores")
async def departamentos_sectores(depto: str):
    """Empleo por sector economico en un departamento (GEIH depto-sector, 95K registros).

    Devuelve sectores con rama_ciiu / rama_ciiu_nombre / empleo (forma esperada por
    el frontend) y la lista de departamentos disponibles para el selector.
    """
    depto_norm = _norm_depto(depto)

    # Lista de departamentos disponibles para el selector (igual que la version online)
    deptos_lista = sorted(
        [{"nombre": nombre.title(), "codigo": codigo} for nombre, codigo in DEPTO_DIVIPOLA.items()],
        key=lambda x: x["nombre"],
    )

    depto_id = DEPTO_DIVIPOLA.get(depto_norm)
    if depto_id is None:
        # Departamento no reconocido: devolver lista y sectores vacios (sin crashear)
        return {
            "departamento": depto,
            "sectores": [],
            "departamentos_disponibles": deptos_lista,
        }

    # Periodo mas reciente disponible para ese departamento
    periodo_row = query_sql(
        "SELECT periodo FROM geih_empleo_depto_sector WHERE dpto = ? "
        "ORDER BY periodo DESC LIMIT 1",
        (depto_id,),
    )
    periodo = periodo_row[0]["periodo"] if periodo_row else None

    sectores = []
    if periodo:
        rows = query_sql(
            "SELECT rama_ciiu, empleo, periodo FROM geih_empleo_depto_sector "
            "WHERE dpto = ? AND periodo = ? ORDER BY empleo DESC LIMIT 50",
            (depto_id, periodo),
        )
        vistos = set()
        for row in rows or []:
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
        "periodo": periodo,
        "sectores": sectores,
        "departamentos_disponibles": deptos_lista,
    }


@router.get("/dashboard")
async def dashboard():
    """Endpoint combinado: todos los datos del observatorio en una respuesta.

    Lee el dashboard.json estatico y lo enriquece con campos adicionales del mapa
    (mujeres_cabeza_hogar_pct, pct_educacion_superior, nivel_educativo_etiqueta)
    desde geih_resumen_departamento en SQLite, para que el tooltip del mapa muestre
    los mismos indicadores que la version online.
    """
    from pathlib import Path
    import json
    dashboard_path = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dashboard.json"
    if not dashboard_path.exists():
        return {"error": "dashboard.json no encontrado"}
    data = json.loads(dashboard_path.read_text(encoding="utf-8"))

    # Enriquecer mapa.departamentos con campos extra de GEIH (SQLite)
    deptos_mapa = (data.get("mapa") or {}).get("departamentos") or []
    if deptos_mapa:
        extras = {}
        for row in (query_sql("SELECT * FROM geih_resumen_departamento") or []):
            key = _norm_depto(row.get("departamento", ""))
            extras[key] = {
                "mujeres_cabeza_hogar_pct": row.get("mujeres_cabeza_hogar_pct"),
                "pct_educacion_superior": row.get("pct_educacion_superior"),
                "nivel_educativo_etiqueta": row.get("nivel_educativo_etiqueta"),
            }
        for d in deptos_mapa:
            extra = extras.get(_norm_depto(d.get("departamento", "")))
            if extra:
                d["mujeres_cabeza_hogar_pct"] = extra["mujeres_cabeza_hogar_pct"]
                d["pct_educacion_superior"] = extra["pct_educacion_superior"]
                d["nivel_educativo_etiqueta"] = extra["nivel_educativo_etiqueta"]

    # Deduplicar SPE por nombre de ocupacion (la tabla SENA tiene filas repetidas)
    spe = (data.get("spe") or {}).get("ocupaciones_demanda_creciente") or []
    if spe:
        vistos = set()
        dedup = []
        for s in spe:
            nombre = s.get("ocupacion", "")
            if nombre and nombre not in vistos:
                vistos.add(nombre)
                dedup.append(s)
        data["spe"]["ocupaciones_demanda_creciente"] = dedup

    return data


@router.get("/departamento-insights/{departamento}")
async def departamento_insights(departamento: str):
    """Insights de un departamento: profesiones destacadas y sectores.

    Devuelve la misma forma que la version online (profesiones_mas_desempleo,
    profesiones_mas_demandadas, sectores_mayor_crecimiento) para que el Dashboard
    renderice sin errores.
    """
    from pathlib import Path
    import json

    depto_norm = _norm_depto(departamento)

    # Cargar predicciones
    pred_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "processed" / "predicciones_mundiales.json"
    pred = {}
    if pred_path.exists():
        with open(pred_path, encoding="utf-8") as f:
            pred = json.load(f)

    # Datos del departamento desde SQLite (normalizando nombres)
    ocu_rows = [r for r in (query_sql("SELECT * FROM geih_resumen_departamento") or [])
                if _norm_depto(r.get("departamento", "")) == depto_norm]
    des_rows = [r for r in (query_sql("SELECT * FROM geih_desempleo_departamento") or [])
                if _norm_depto(r.get("departamento", "")) == depto_norm]

    ocupados = sum(r.get("ocupados", 0) or 0 for r in ocu_rows)
    no_ocupados = sum(r.get("no_ocupados", 0) or 0 for r in des_rows)
    total = ocupados + no_ocupados
    tasa_desempleo = (no_ocupados / total * 100) if total else 10.0
    ingreso_prom = sum((r.get("ingreso_promedio", 0) or 0) * (r.get("ocupados", 0) or 0) for r in ocu_rows) / max(ocupados, 1)

    profesiones = pred.get("profesiones", [])
    sectores_raw = pred.get("sectores", {})

    factor_desempleo_local = max(0.5, tasa_desempleo / 10.0)
    factor_ingreso_local = max(0.5, ingreso_prom / 2_500_000)

    def _score_dificultad(p):
        crec = p.get("crecimiento_5a_pct", 0)
        demanda = p.get("demanda", "media")
        salario = p.get("salario_mensual_cop", 2_500_000)
        base = {"baja": 55, "media": 28, "alta": 10}.get(demanda, 28)
        penalizacion = max(0, -crec) * 6
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

    def _score_demanda(p):
        crec = p.get("crecimiento_5a_pct", 0)
        salario = p.get("salario_mensual_cop", 2_500_000)
        if salario > 5_000_000:
            ajuste = 0.6 + factor_ingreso_local * 0.5
        elif salario < 2_500_000:
            ajuste = 1.4 - factor_ingreso_local * 0.3
        else:
            ajuste = 1.0 + (factor_ingreso_local - 1.0) * 0.2
        return round(crec * ajuste, 1)

    profesiones_demanda = sorted(
        [
            {"profesion": p["profesion"], "demanda_score": _score_demanda(p)}
            for p in profesiones
            if p.get("crecimiento_5a_pct", 0) > 0
        ],
        key=lambda x: -x["demanda_score"],
    )[:5]

    sectores = []
    for sector, info in sectores_raw.items():
        v2025 = info.get("historico", {}).get("valores", [0])[-1]
        v2035 = info.get("prediccion", {}).get("mediana", [0])[-1]
        crec = ((v2035 - v2025) / max(v2025, 0.01)) * 100 if v2025 else 0
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