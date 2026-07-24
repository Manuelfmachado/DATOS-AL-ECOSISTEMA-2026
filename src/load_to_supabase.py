"""
Carga los datos procesados del ETL a Supabase.
Requiere archivo .env con SUPABASE_URL y SUPABASE_KEY.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

ROOT = Path.cwd()
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan SUPABASE_URL o SUPABASE_KEY en archivo .env")
    print("1. Copiá .env.example a .env")
    print("2. Completá con tus credenciales de Supabase (Project Settings → API → anon public)")
    exit(1)

print(f"Conectando a Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def csv_to_records(path: Path, allowed_columns=None):
    """Lee CSV y devuelve lista de diccionarios, limpiando NaN/Inf."""
    if not path.exists():
        print(f"  [SKIP] No existe {path}")
        return []
    df = pd.read_csv(path, encoding='utf-8')
    
    # Reemplazar columnas problemáticas
    df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
    
    # Filtrar solo columnas permitidas si se especifican
    if allowed_columns:
        cols_to_keep = [c for c in df.columns if c in allowed_columns]
        df = df[cols_to_keep]
    
    # Limpiar NaN, Inf, -Inf → None (agresivo)
    df = df.where(pd.notna(df), None)
    df = df.replace([np.inf, -np.inf], None)
    
    records = df.to_dict('records')
    
    # Post-procesar: reemplazar float('nan') y float('inf') con None
    import math
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    rec[k] = None
    
    print(f"  [OK] {len(records)} registros listos")
    return records


def upload_table(table_name: str, records: list, batch_size=500, truncate_first=False):
    """Sube registros a Supabase en lotes.
    Si truncate_first=True, borra las filas existentes antes de insertar
    (util para recargar tablas sin chocar con unique constraints)."""
    if not records:
        return

    print(f"\n[>] Subiendo {table_name}...")

    if truncate_first:
        try:
            supabase.table(table_name).delete().neq("id", -1).execute()
            print(f"  [OK] Tabla {table_name} vaciada (delete previo)")
        except Exception as e:
            print(f"  [WARN] No se pudo vaciar {table_name}: {e}")
    
    for i in range(0, len(records), batch_size):
        batch = records[i:i + batch_size]
        try:
            response = supabase.table(table_name).insert(batch).execute()
            print(f"  [OK] Lote {i//batch_size + 1}: {len(batch)} registros")
        except Exception as e:
            print(f"  [ERROR] Lote {i//batch_size + 1}: {e}")
            print(f"  Intentando con lote más pequeño...")
            # Fallback: subir de a 50
            for j in range(0, len(batch), 50):
                try:
                    supabase.table(table_name).insert(batch[j:j+50]).execute()
                except Exception as e2:
                    print(f"    [ERROR FATAL] {e2}")
                    break


def main(only_tables=None, truncate_tables=None):
    only_tables = only_tables or None
    truncate_tables = truncate_tables or set()
    # Mapeo archivo CSV → tabla Supabase + columnas permitidas
    tables = {
        # === CARGADAS ANTERIORMENTE ===
        'geih_resumen_departamento.csv': ('geih_resumen_departamento', [
            'departamento', 'ocupados', 'ingreso_promedio', 'ingreso_mediano',
            'tasa_formalidad', 'mujeres_pct', 'mujeres_cabeza_hogar_pct',
            'pct_educacion_superior', 'nivel_educativo_etiqueta'
        ]),
        'geih_desempleo_departamento.csv': ('geih_desempleo_departamento', None),
        'pila_resumen_sector.csv': ('pila_resumen_sector', None),
        'pila_resumen_tipo.csv': ('pila_resumen_tipo', None),
        'rues_resumen_camara_ciiu.csv': ('rues_resumen_camara_ciiu', None),
        'rues_top_sectores_nacional.csv': ('rues_top_sectores_nacional', None),
        'rues_empresas_nuevas.csv': ('rues_empresas_nuevas', None),
        'snies_programas_matriculados.csv': ('snies_programas_matriculados', None),
        'snies_matriculados_departamento.csv': ('snies_matriculados_departamento', None),
        'sena_programas_activos.csv': ('sena_programas_activos', [
            'programa', 'departamento', 'area_desempeno', 'tipo_certificado',
            'escolaridad', 'costo', 'duracion_horas', 'estado_programa', 'institucion'
        ]),
        'saberpro_resumen_programas.csv': ('saberpro_resumen_programas', [
            'institucion', 'programa', 'departamento',
            'mod_razona_cuantitat_punt', 'mod_comuni_escrita_punt',
            'mod_lectura_critica_punt', 'mod_ingles_punt', 'mod_competen_ciudada_punt'
        ]),
        'spe_ape_inscritos_ocupacion.csv': ('spe_ape_inscritos_ocupacion', None),
        # spe_ape_inscritos_nivel fue DROP (duplicada, spe_ape_inscritos_ocupacion la supera).
        'ole_etdh_programas_activos.csv': ('ole_etdh_programas_activos', [
            'programa', 'institucion', 'departamento', 'municipio',
            'area_desempeno', 'tipo_certificado', 'escolaridad',
            'costo', 'duracion_horas', 'estado_programa'
        ]),
        'ole_etdh_resumen_departamento_area.csv': ('ole_etdh_resumen_departamento_area', None),
        'dnp_medicion_desempeno_municipal.csv': ('dnp_medicion_desempeno_municipal', None),
        # dnp_medicion_desempeno_ultimo fue DROP (incompleto, solo 4 filas).
        'dnp_desempeno_departamento.csv': ('dnp_desempeno_departamento', None),
        
        # === NUEVAS TABLAS A CARGAR ===
        # GEIH completo
        'geih_resumen_nacional.csv': ('geih_resumen_nacional', None),
        'geih_desempleo_mensual.csv': ('geih_desempleo_mensual', None),
        'geih_empleo_sector_mensual.csv': ('geih_empleo_sector_mensual', None),
        'geih_informalidad_mensual.csv': ('geih_informalidad_mensual', None),
        'geih_empleo_depto_sector.csv': ('geih_empleo_depto_sector', None),
        'geih_salario_ocupacion.csv': ('geih_salario_ocupacion', [
            'oficio_c8', 'salario_promedio', 'salario_mediano',
            'empleo_total', 'ocupados_muestra', 'periodo'
        ]),
        'geih_extras_departamento.csv': ('geih_extras_departamento', [
            'departamento', 'mujeres_cabeza_hogar_pct', 'total_jefes_hogar',
            'pct_educacion_superior', 'nivel_educativo_categoria', 'nivel_educativo_etiqueta'
        ]),
        
        # OLE - Ingresos por carrera
        'ole_ingresos_por_programa.csv': ('ole_ingresos_por_programa', None),
        'ole_ingresos_por_area.csv': ('ole_ingresos_por_area', None),
        'ole_ingresos_por_nivel.csv': ('ole_ingresos_por_nivel', None),
        'ole_ingresos_por_ies.csv': ('ole_ingresos_por_ies', None),
        'ole_graduados_por_anio.csv': ('ole_graduados_por_anio', None),
        
        # ESCO - Ocupaciones y habilidades
        'esco_ocupaciones.csv': ('esco_ocupaciones', None),
        'esco_habilidades.csv': ('esco_habilidades', None),
        'esco_ocupacion_habilidades.csv': ('esco_ocupacion_habilidades', None),
        'esco_skill_relations.csv': ('esco_skill_relations', None),
        'esco_habilidades_verdes.csv': ('esco_habilidades_verdes', None),
        # esco_habilidades_digitales fue DROP (subset redundante de esco_habilidades).
        'esco_green_share_ocupaciones.csv': ('esco_green_share_ocupaciones', None),
        # NOTA: esco_skills.csv fue DROP (duplicado de esco_habilidades).
        
        # EMICRON - Micronegocios
        'emicron_resumen_nacional.csv': ('emicron_resumen_nacional', None),
        # emicron_por_sector fue DROP (incompleta: solo 2 sectores de ~20).
        'emicron_emprendimiento.csv': ('emicron_emprendimiento', None),
        'emicron_por_departamento.csv': ('emicron_por_departamento', None),
        # emicron_inclusion_financiera fue DROP (incompleta: solo 2 sectores).

        # EMICRON v2 - Corregido con GRUPOS12 (13 sectores) + modulos nuevos
        'emicron_por_sector_v2.csv': ('emicron_por_sector_v2', None),
        'emicron_costos_sector.csv': ('emicron_costos_sector', None),
        'emicron_ubicacion_sector.csv': ('emicron_ubicacion_sector', None),
        'emicron_resumen_nacional_v2.csv': ('emicron_resumen_nacional_v2', None),
        'emicron_por_departamento_v2.csv': ('emicron_por_departamento_v2', None),

        # RNT - Registro Nacional de Turismo (MinCIT) - Emprende IA
        'rnt_resumen_departamento_categoria.csv': ('rnt_resumen_departamento_categoria', None),
        'rnt_resumen_municipio_categoria.csv': ('rnt_resumen_municipio_categoria', None),
        'rnt_resumen_nacional_categoria.csv': ('rnt_resumen_nacional_categoria', None),
        # rnt_establecimientos.csv es grande (245K filas); cargar aparte si se necesita detalle

        # FINAGRO - Credito agropecuario - Emprende IA
        'finagro_colocaciones_detalle.csv': ('finagro_colocaciones_detalle', None),
        'finagro_resumen_departamento.csv': ('finagro_resumen_departamento', None),
        'finagro_colocaciones_cadena.csv': ('finagro_colocaciones_cadena', None),
        'finagro_resumen_nacional_anual.csv': ('finagro_resumen_nacional_anual', None),
        'finagro_top_cadenas_departamento.csv': ('finagro_top_cadenas_departamento', None),

        # World Bank
        'worldbank_colombia.csv': ('worldbank_colombia', [
            'indicator_code', 'indicator_name', 'year', 'value', 'country'
        ]),
    }
    
    print("=" * 70)
    print("CARGA DE DATOS A SUPABASE")
    print("=" * 70)
    
    # Verificar conexión y tablas
    print("\n[!] IMPORTANTE:")
    print("Las tablas deben estar creadas en Supabase antes de cargar datos.")
    print("Si no las creaste todavía:")
    print("1. Andá al SQL Editor de Supabase")
    print("2. Copiá el contenido de schema_supabase.sql")
    print("3. Ejecutalo (Run)")
    print("4. Luego ejecutá de nuevo este script")
    print()
    
    # Chequear primera tabla
    try:
        response = supabase.table('geih_resumen_departamento').select('id', count='exact').limit(1).execute()
        print(f"[OK] Conexión a Supabase verificada. Tablas existen.")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar o las tablas no existen: {e}")
        print("[ERROR] Creá las tablas con schema_supabase.sql primero.")
        return
    
    for csv_file, (table_name, allowed_cols) in tables.items():
        # Si se paso un filtro por argumento, solo cargar las tablas indicadas
        if only_tables and table_name not in only_tables:
            continue
        path = PROCESSED / csv_file
        records = csv_to_records(path, allowed_cols)
        # Truncar antes de insertar para las tablas marcadas (evita duplicados)
        truncate = table_name in truncate_tables
        upload_table(table_name, records, truncate_first=truncate)
    
    print("\n" + "=" * 70)
    print("CARGA FINALIZADA")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    # Soporte para argumentos:
    #   python src/load_to_supabase.py                          -> carga todo
    #   python src/load_to_supabase.py finagro_colocaciones_detalle   -> solo esa tabla
    #   python src/load_to_supabase.py rnt_resumen_departamento_categoria finagro_resumen_departamento
    only_tables = set(sys.argv[1:]) if len(sys.argv) > 1 else None
    # Tablas con unique constraint que conviene vaciar antes de recargar
    truncate_tables = {
        'rnt_resumen_departamento_categoria',
        'rnt_resumen_municipio_categoria',
        'rnt_resumen_nacional_categoria',
        'finagro_resumen_departamento',
        'finagro_colocaciones_cadena',
        'finagro_resumen_nacional_anual',
        'dnp_desempeno_departamento',
        'emicron_por_sector_v2',
        'emicron_costos_sector',
        'emicron_resumen_nacional_v2',
    }
    main(only_tables=only_tables, truncate_tables=truncate_tables)
