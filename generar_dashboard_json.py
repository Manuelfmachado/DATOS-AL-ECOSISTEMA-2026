"""
Genera frontend/public/dashboard.json con todos los datos precalculados del Observatorio.
Esto permite que la pagina cargue instantaneamente sin consultar Supabase en cada visita.

Uso:
    python generar_dashboard_json.py

El archivo resultante se sirve como estatico desde el frontend (Vite/vercel).
Para actualizar los datos, volver a ejecutar este script y hacer deploy.
"""

import json
import sys
from pathlib import Path

# Asegurar que el backend este en el path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.routers.observatorio import (
    _calcular_tendencia_empleo,
    _calcular_sectores_emergentes,
    _calcular_indice_prioridad,
    _calcular_brecha_oferta_demanda,
    _calcular_spe_demanda,
    _calcular_mapa_metricas_sync,
)
from app.db.supabase import supabase


def generar():
    print("[generar_dashboard_json] Generando dashboard.json estatico...")

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
            for s in (r_sec.data if hasattr(r_sec, "data") else r_sec.get("data", []))
        ],
    }

    # 2-8. Funciones precalculadas
    tendencia = _calcular_tendencia_empleo()
    emergentes = _calcular_sectores_emergentes()
    prioridad = _calcular_indice_prioridad()
    brecha = _calcular_brecha_oferta_demanda()

    # 6. Sectores formales
    r_formal = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(50).execute()
    formales = {"sectores": r_formal.data or []}

    # 7. SPE demanda
    spe = _calcular_spe_demanda(15)

    # 8. Mapa metricas
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
        "_generado": str(__import__("datetime").datetime.now()),
    }

    out_path = Path(__file__).resolve().parent / "frontend" / "public" / "dashboard.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, default=str)

    size_kb = out_path.stat().st_size / 1024
    print(f"[generar_dashboard_json] OK -> {out_path} ({size_kb:.0f} KB)")
    print(f"  resumen_nacional: {'si' if resumen_nacional.get('periodo') else 'no'}")
    print(f"  tendencia: {len(tendencia.get('sectores', []))} sectores")
    print(f"  emergentes: {len(emergentes.get('sectores', []))} sectores")
    print(f"  prioridad: {len(prioridad.get('departamentos', []))} deptos")
    print(f"  brecha: {len(brecha.get('brecha_categorias', []))} categorias")
    print(f"  sectores_formales: {len(formales.get('sectores', []))} sectores")
    print(f"  spe: {len(spe.get('ocupaciones_demanda_creciente', []))} ocupaciones")
    print(f"  mapa: {mapa.get('total', 0)} deptos")


if __name__ == "__main__":
    generar()