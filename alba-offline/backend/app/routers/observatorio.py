"""
Router Observatorio para ALBA Offline.
Lee datos de SQLite local en lugar de Supabase.
"""
from fastapi import APIRouter
from app.db.sqlite_db import query_all, query_sql, query_one

router = APIRouter(prefix="/api/observatorio", tags=["observatorio"])


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