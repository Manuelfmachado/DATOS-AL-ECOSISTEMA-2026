# Diccionario de datos

## Resumen general

ALBA utiliza **44 tablas** en Supabase con **~744.000 filas** provenientes de 11 fuentes de datos abiertos.

## Tablas por fuente

### DANE — GEIH (Gran Encuesta Integrada de Hogares)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `geih_resumen_departamento` | 33 | departamento, ocupados, ingreso_promedio, ingreso_mediano, tasa_formalidad, mujeres_pct, pct_educacion_superior, nivel_educativo_etiqueta | Resumen laboral por departamento |
| `geih_desempleo_departamento` | 33 | departamento, no_ocupados | Desempleo por departamento |
| `geih_resumen_nacional` | ~12 | periodo, ocupados, desempleo, informalidad | Serie nacional mensual |
| `geih_desempleo_mensual` | ~52 | periodo, tasa_desempleo | Desempleo nacional mensual 2022-2026 |
| `geih_empleo_sector_mensual` | ~4.500 | ano, mes, rama_ciiu, empleo, periodo | Empleo por sector CIIU mensual |
| `geih_informalidad_mensual` | ~52 | periodo, informalidad | Informalidad nacional mensual |
| `geih_empleo_depto_sector` | ~95.000 | dpto, rama_ciiu, empleo, periodo | Empleo cruzado por departamento × sector |
| `geih_salario_ocupacion` | 406 | oficio_c8, salario_promedio, salario_mediano, empleo_total, ocupados_muestra, periodo | Salarios reales por ocupación (DANE) |
| `geih_extras_departamento` | 33 | departamento, mujeres_cabeza_hogar_pct, total_jefes_hogar, pct_educacion_superior, nivel_educativo_categoria | Indicadores adicionales por departamento |

### DANE — EMICRON (Micronegocios)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `emicron_resumen_nacional` | ~10 | ano, micronegocios | Serie nacional de micronegocios |
| `emicron_por_sector` | ~10 | sector, micronegocios | Micronegocios por sector económico |
| `emicron_emprendimiento` | ~60 | ano, codigo_motivo, micronegocios | Motivos de emprendimiento por año |
| `emicron_por_departamento` | ~100 | dpto, ano, micronegocios | Micronegocios por departamento y año |
| `emicron_inclusion_financiera` | ~10 | indicador, valor | Inclusión financiera de micronegocios |

### MinTrabajo — PILA (Plan Integrado de Liquidación de Aportes)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `pila_resumen_sector` | 496 | actividadeconomicadesc, total_cotizantes | Cotizantes formales por sector CIIU |
| `pila_resumen_tipo` | 156 | tipo, total_cotizantes | Cotizantes por tipo de cotizante |

### Confecámaras — RUES (Registro Único de Empresas)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `rues_empresas_nuevas` | 1.400 | ciiu2, empresas_nuevas, anio_matricula | Empresas nuevas por sector CIIU |
| `rues_resumen_camara_ciiu` | 25.000 | camara, ciiu, empresas | Empresas por cámara de comercio |
| `rues_top_sectores_nacional` | ~90 | sector, empresas_nuevas | Top sectores con más empresas nuevas |

### MEN — SNIES (Sistema Nacional de Información de Educación Superior)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `snies_programas_matriculados` | ~85.000 | institucion, programa, matriculados, departamento | Programas académicos con matriculados |
| `snies_matriculados_departamento` | ~500 | departamento, matriculados | Matriculados por departamento |

### MEN — OLE/ETDH (Educación para el Trabajo y Desarrollo Humano)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `ole_etdh_programas_activos` | ~20.000 | programa, institucion, departamento, area_desempeno, costo, duracion_horas | Programas activos de educación para el trabajo |
| `ole_etdh_resumen_departamento_area` | ~500 | departamento, area, programas | Resumen por departamento y área |
| `ole_ingresos_por_programa` | ~37.000 | programa, rango_ingreso, graduados, porcentaje | Ingresos reales de egresados por programa |
| `ole_ingresos_por_area` | ~500 | area, rango_ingreso, graduados | Ingresos por área del conocimiento |
| `ole_ingresos_por_nivel` | ~100 | nivel, rango_ingreso, graduados | Ingresos por nivel educativo |
| `ole_ingresos_por_ies` | ~276 | institucion, rango_ingreso, graduados | Ingresos por institución |
| `ole_graduados_por_anio` | ~178 | ano, area, graduados | Graduados por año y área |

### SENA — Programas + SPE/APE

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `sena_programas_activos` | ~16.000 | programa, departamento, area_desempeno, costo, duracion_horas | Cursos SENA activos |
| `spe_ape_inscritos_ocupacion` | 566 | ocupacion, inscritos_2020 | Inscritos en SPE por ocupación |
| `spe_ape_inscritos_nivel` | ~10 | nivel, inscritos | Inscritos por nivel educativo |

### MEN — Saber Pro

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `saberpro_resumen_programas` | 1.400 | institucion, programa, mod_ingles_punt, mod_razona_cuantitat_punt | Resultados Saber Pro por programa |

### ESCO (European Skills/Competences)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `esco_ocupaciones` | ~3.000 | nombre, codigo_isco, definicion | Ocupaciones estandarizadas |
| `esco_habilidades` | ~14.000 | nombre, tipo_habilidad | Habilidades catalogadas |
| `esco_ocupacion_habilidades` | ~126.000 | ocupacion_nombre, habilidad_nombre, tipo_relacion | Relación ocupación-habilidad |
| `esco_skill_relations` | ~6.000 | skill1, skill2, tipo | Relaciones entre habilidades |
| `esco_habilidades_verdes` | 629 | habilidad, descripcion | Habilidades para economía verde |
| `esco_habilidades_digitales` | 1.300 | habilidad, descripcion | Habilidades digitales |
| `esco_green_share_ocupaciones` | 3.600 | nombre, indice_verdor | Índice de verdor por ocupación |

### O*NET (Occupational Information Network)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `onet_occupations` | ~1.000 | onet_code, title, description | Ocupaciones estandarizadas EE.UU. |
| `onet_skills` | ~6.000 | onet_code, skill, level | Habilidades por ocupación |
| `onet_tasks` | ~4.000 | onet_code, task | Tareas por ocupación |
| `onet_tools` | ~2.000 | onet_code, tool | Herramientas por ocupación |
| `onet_knowledge` | ~2.000 | onet_code, knowledge, level | Conocimientos por ocupación |
| `onet_abilities` | ~2.000 | onet_code, ability, level | Habilidades cognitivas |
| `onet_work_values` | ~1.000 | onet_code, value, level | Valores laborales |

### DNP — Medición del Desempeño Municipal (MDM)

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `dnp_medicion_desempeno_municipal` | ~22.000 | departamento, indicador, dato | Desempeño municipal por indicador |
| `dnp_medicion_desempeno_ultimo` | ~1.100 | departamento, indicador, dato | Última medición disponible |
| `dnp_desempeno_departamento` | ~1.000 | departamento, promedio_desempeno | Promedio de desempeño por departamento |

### World Bank — Colombia

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `worldbank_colombia` | 128 | indicator_code, indicator_name, year, value | Indicadores macro de Colombia 2010-2025 |

### IA — Predicciones Chronos T5

| Tabla | Filas | Variables clave | Descripción |
|-------|-------|-----------------|-------------|
| `predicciones_geih` | ~436 | tipo, horizonte, periodo, mediana, p10, p90 | Predicciones de series temporales |
| `predicciones_mundiales` (JSON) | — | sectores, profesiones, habilidades, salarios | Predicciones estructuradas |