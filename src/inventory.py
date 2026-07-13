from backend.app.db.supabase import supabase
import os

# Try to get all tables using PostgREST introspection
try:
    r = supabase.table('pila_resumen_sector').select('*', count='exact').limit(1).execute()
except Exception as e:
    print('Error:', e)

# Test a comprehensive list of candidate table names
candidates = [
    # PILA - cotizantes por sector
    'pila_resumen_sector', 'pila_resumen_tipo', 'pila_cotizantes_departamento',
    'pila_cotizantes_mensual', 'pila_ibc_promedio', 'pila_ingresos_departamento',
    'pila_cotizantes_actividad', 'pila_empleadores_sector',
    # GEIH - empleo
    'geih_empleo_departamento', 'geih_ocupados_departamento', 'geih_desempleo_departamento',
    'geih_informalidad_departamento', 'geih_resumen_departamento', 'geih_resumen_nacional',
    'geih_salario_departamento', 'geih_empleo_sector_mensual', 'geih_desempleo_mensual',
    'geih_informalidad_mensual', 'geih_extras_departamento', 'geih_poblacion_edad',
    'geih_pet', 'geih_pea',
    # SENA
    'sena_programas_activos', 'sena_cursos_ofertados', 'sena_egresados_sector',
    'sena_inscripciones', 'sena_contratos_aprendizaje',
    # SNIES / OLE / MEN
    'snies_programas_matriculados', 'snies_matriculados_departamento',
    'snies_graduados', 'snies_programas', 'snies_ies',
    'ole_etdh_programas_activos', 'ole_etdh_resumen_departamento_area',
    'ole_graduados_por_anio', 'ole_ingresos_por_area', 'ole_ingresos_por_ies',
    'ole_ingresos_por_nivel', 'ole_ingresos_por_programa',
    # RUES / Empresarial
    'rues_empresas_nuevas', 'rues_resumen_camara_ciiu', 'rues_top_sectores_nacional',
    'rues_empresas_activas', 'rues_empresas_segun_tamano', 'rues_empresas_departamento',
    # SPE / APE
    'spe_ape_inscritos_nivel', 'spe_ape_inscritos_ocupacion', 'spe_inscritos_areas',
    'spe_vacantes', 'spe_contratos', 'spe_colocaciones',
    # Saber Pro / Educación
    'saberpro_resumen_programas', 'saberpro_puntaje_ies', 'saberpro_puntaje_departamento',
    'saber11_puntajes',
    # DNP / MDM
    'dnp_desempeno_departamento', 'dnp_medicion_desempeno_municipal',
    'dnp_medicion_desempeno_ultimo',
    # EMICRON
    'emicron_emprendimiento', 'emicron_inclusion_financiera',
    'emicron_por_departamento', 'emicron_por_sector', 'emicron_resumen_nacional',
    # O*NET / ESCO
    'onet_education', 'onet_skills', 'onet_occupations', 'onet_work_activities',
    'esco_skills', 'esco_ocupaciones', 'esco_ocupacion_habilidades',
    'esco_habilidades', 'esco_habilidades_digitales', 'esco_habilidades_verdes',
    'esco_skill_relations', 'esco_green_share_ocupaciones',
    # World Bank
    'worldbank_colombia',
    # Predicciones generadas
    'predicciones_mundiales', 'predicciones_geih',
    # Otros
    'mapeo_ocupaciones_spe', 'map_occupations',
    'contratos', 'vacantes_empleo', 'oferta_laboral',
    'exportaciones', 'importaciones',
    'demografia_departamento', 'migracion',
    'salud_empleo', 'formalidad',
    'tabla_salarios', 'salarios_sector', 'salarios_departamento',
    'departamentos', 'municipios',
    'observatorio_nacional', 'observatorio_sector',
    'tendencias_mercado', 'sectores_emergentes',
]

found = []
missing = []
for t in candidates:
    try:
        r = supabase.table(t).select('*', count='exact').limit(1).execute()
        found.append((t, r.count))
    except Exception:
        missing.append(t)

print('=== EXISTING TABLES ===')
for t, c in sorted(found, key=lambda x: -x[1]):
    print(f'  {c:>10,}  {t}')
print(f'\nTotal: {len(found)} tables, {sum(c for _,c in found):,} rows total')
print(f'\n=== MISSING CANDIDATES ({len(missing)}) ===')
for t in missing[:20]:
    print(f'  {t}')
