# Conclusiones

## Hallazgos principales

### 1. Integración de 11 fuentes de datos en una sola plataforma
ALBA logró integrar datos del DANE (GEIH, EMICRON, DNP), MinTrabajo (PILA), Confecámaras (RUES), MEN (SNIES, OLE, Saber Pro), SENA (programas + SPE/APE), y fuentes internacionales (ESCO, O*NET, World Bank) en una base de datos unificada de 44 tablas y ~744.000 filas en Supabase.

### 2. Predicción de empleo y salarios con Chronos T5
Se implementó forecasting zero-shot con Chronos T5 Small sobre series del Banco Mundial y GEIH, generando proyecciones a 5 y 10 años para sectores, profesiones, habilidades y salarios. Las proyecciones son conservadoras (cap 0.5%-4% anual) para evitar sobreestimaciones.

### 3. Salarios reales del DANE en vez de estimaciones
Se cargaron 406 ocupaciones con salarios reales observados por el DANE GEIH (periodo 2026-04), reemplazando las estimaciones del LLM con datos oficiales verificables.

### 4. Matching híbrido (datos reales + LLM)
El módulo Match combina:
- Habilidades reales de ESCO (126K relaciones ocupación-habilidad)
- Salarios reales de egresados de OLE-MEN (37K registros)
- Análisis cualitativo del LLM (Gemini/Gemma)
- Score: 50% intersección de habilidades + 50% análisis del LLM

### 5. Empleo por departamento y sector (95K registros)
Se cargó el cruce de empleo por departamento × sector CIIU del DANE, permitiendo que el mapa del Observatorio muestre datos reales territoriales (ej: "Antioquia tiene 400K en comercio, 336K en agricultura").

## Métricas del proyecto

| Métrica | Valor |
|---------|-------|
| Fuentes de datos integradas | 11 |
| Tablas en Supabase | 44 |
| Filas totales | ~744.000 |
| Módulos funcionales | 5 |
| Modelos de IA | 4 (Gemini, Gemma, Chronos, Gemma Embeddings) |
| Endpoints API | 40+ |
| Páginas frontend | 6 |
| Departamentos cubiertos | 33 |
| Ocupaciones con salario real | 406 |
| Profesiones proyectadas | 21 |
| Habilidades catalogadas | 14.000+ |

## Limitaciones

1. **Datos GEIH solo 2022-2026:** Las series históricas son de 4 años, insuficientes para forecasting de largo plazo. Chronos T5 funciona zero-shot pero más datos mejorarían la precisión.

2. **SPE/APE solo nacional (566 registros):** No hay datos de demanda laboral por municipio. La granularidad territorial de la demanda laboral es limitada.

3. **Sin PIB sectorial:** No se descargaron las Cuentas Nacionales del DANE, por lo que las predicciones sectoriales se basan en el Banco Mundial (3 macrosectores) en lugar de los 12-33 sectores del DANE.

4. **OLE ingresos hasta 2022:** Los datos de ingresos de egresados son de 2001-2022, pueden no reflejar el mercado actual.

5. **LLM con hallucinations:** Aunque se normalizan los pesos de las brechas y se complementa con datos reales de ESCO y OLE, el LLM puede generar recomendaciones de recursos que no existen exactamente como los describe.

6. **Sin datos de costo de vida:** Las recomendaciones de emprendimiento no consideran el costo de vida por municipio.

## Próximos pasos

### Corto plazo (1-3 meses)
- Descargar e ingestar **SINIDEL** (DANE "Saber para Decidir") para demanda laboral por sector × ciudad
- Descargar **Cuentas Nacionales del DANE** (PIB sectorial trimestral 2005-2024)
- Migrar a **Chronos-Bolt** cuando el paquete oficial lo soporte
- Cargar predicciones a Supabase para servir desde producción

### Mediano plazo (3-6 meses)
- Añadir **SECOP** (contratación pública) como fuente de demanda laboral
- Integrar **datos de costo de vida** (DANE SIPSA) para recomendaciones más completas
- Mejorar el matching con **NLP para extracción de habilidades** del CV

### Largo plazo (6-12 meses)
- Desplegar en producción (Vercel + Railway + Supabase + Namecheap)
- Integrar **datos en tiempo real** vía APIs de DANE y SENA
- Añadir **notificaciones proactivas** (alertas de oportunidades laborales por sector)
- Implementar **recomendaciones personalizadas** basadas en historial del usuario

## Impacto esperado

ALBA tiene el potencial de convertirse en una herramienta de referencia para el ecosistema laboral colombiano:

- **Ciudadanos:** Pueden tomar decisiones informadas sobre qué estudiar y dónde buscar empleo
- **Emprendedores:** Identifican oportunidades de negocio con datos reales de su territorio
- **Universidades:** Evalúan la alineación de sus programas con el mercado laboral
- **Gobierno:** Tiene visibilidad integral para diseñar políticas de empleo y formación
- **Empresas:** Encuentran talento y entienden la demanda de su sector

La plataforma demuestra que los datos abiertos colombianos, combinados con IA, pueden generar valor público concreto y accionable.