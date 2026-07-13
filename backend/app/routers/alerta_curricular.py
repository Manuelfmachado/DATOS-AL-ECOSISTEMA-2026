"""
Router del Sistema de Alerta Curricular (Función #3).
Analiza programas educativos vs demanda laboral usando Saber Pro y SNIES.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.db.supabase import supabase
import pandas as pd

router = APIRouter(prefix="/api/alerta-curricular", tags=["alerta-curricular"])


@router.get("/programas")
async def get_programas(limit: int = 100, departamento: str | None = None):
    """Lista programas educativos con métricas."""
    try:
        query = supabase.table("snies_programas_matriculados").select("*")
        if departamento:
            query = query.eq("departamento", departamento.upper())
        res = query.order("matriculados", desc=True).limit(limit).execute()
        return {"programas": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/programa/{programa_id}/diagnostico")
async def get_diagnostico_programa(programa_id: int):
    """Diagnóstico curricular de un programa específico."""
    try:
        # Obtener programa
        res = supabase.table("snies_programas_matriculados").select("*").eq("id", programa_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Programa no encontrado")

        programa = res.data[0]

        # Buscar cursos SENA relacionados
        nombre_programa = programa.get("programa", "")
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{nombre_programa[:20]}%").limit(5).execute()

        # Buscar resultados Saber Pro relacionados
        saber = supabase.table("saberpro_resumen_programas").select("*").ilike("programa", f"%{nombre_programa[:20]}%").limit(5).execute()

        # Generar diagnóstico
        diagnostico = {
            "programa": nombre_programa,
            "institucion": programa.get("institucion"),
            "departamento": programa.get("departamento"),
            "matriculados": programa.get("matriculados"),
            "nucleo_conocimiento": programa.get("nucleo_conocimiento"),
            "cursos_sena_relacionados": len(sena.data),
            "resultados_saber_pro": len(saber.data),
            "saber_pro_promedios": saber.data[0] if saber.data else None,
            "alertas": []
        }

        # Generar alertas automáticas
        if programa.get("matriculados", 0) and programa["matriculados"] > 10000:
            diagnostico["alertas"].append("Alto número de matriculados: posible saturación del programa")

        if saber.data:
            ingles = saber.data[0].get("mod_ingles_punt")
            if ingles and ingles < 100:
                diagnostico["alertas"].append(f"Puntaje de inglés bajo ({ingles}): el mercado laboral demanda inglés B2+")

        if not sena.data:
            diagnostico["alertas"].append("No se encontraron cursos SENA complementarios")

        return {"diagnostico": diagnostico}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BrechaRequest(BaseModel):
    programa: str
    departamento: str = "BOGOTÁ"


@router.post("/brecha")
async def analizar_brecha_curricular(req: BrechaRequest):
    """Analiza brecha entre oferta educativa y demanda laboral."""
    try:
        # Programas SNIES
        snies = supabase.table("snies_programas_matriculados").select("*").ilike("programa", f"%{req.programa}%").eq("departamento", req.departamento.upper()).execute()

        # Cursos SENA
        sena = supabase.table("sena_programas_activos").select("*").ilike("programa", f"%{req.programa}%").limit(20).execute()

        # Sectores formales (PILA) como proxy de demanda
        pila = supabase.table("pila_resumen_sector").select("*").order("total_cotizantes", desc=True).limit(20).execute()

        return {
            "programa": req.programa,
            "departamento": req.departamento,
            "oferta_educativa": {
                "programas_snies": len(snies.data),
                "cursos_sena": len(sena.data),
                "total_matriculados": sum(p.get("matriculados", 0) or 0 for p in snies.data),
            },
            "demanda_laboral": {
                "sectores_formales_top": len(pila.data),
                "cotizantes_total": sum(p.get("total_cotizantes", 0) or 0 for p in pila.data),
            },
            "cursos_sena_recomendados": [{"programa": s.get("programa"), "area": s.get("area_desempeno"), "duracion": s.get("duracion_horas")} for s in sena.data[:10]],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
