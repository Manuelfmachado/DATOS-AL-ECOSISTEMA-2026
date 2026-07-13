# Changelog

Registro cronológico de versiones y cambios del proyecto ALBA.

## [1.0.0] — 2026-07-13

### Añadido
- Plataforma ALBA con 5 módulos: Observatorio, Predicción IA, Match Inteligente, Emprende IA, Coach IA
- Backend FastAPI con 5 routers y 40+ endpoints
- Frontend React 18 + TypeScript + Vite + Tailwind CSS 3
- Base de datos Supabase con 44 tablas y ~744K filas
- Integración de 11 fuentes de datos abiertos (DANE, MinTrabajo, MEN, SENA, Confecámaras, DNP, ESCO, O*NET, World Bank)
- Forecasting con Chronos T5 Small (predicciones a 5 y 10 años)
- LLM Gemini 2.5 Flash-Lite con fallback Gemma 4 E4B (DeepInfra)
- RAG con Gemma Embeddings 300 (768 dimensiones) + Supabase pgvector
- Matching híbrido: ESCO (habilidades reales) + OLE-MEN (salarios reales) + LLM (interpretación)
- Salarios reales del DANE GEIH (406 ocupaciones)
- Empleo por departamento × sector CIIU (95K registros)
- Mapa interactivo de Colombia con GeoJSON real (33 departamentos)
- Diseño visual "lámina metálica" con bordes dorados (#d4af37)
- Documentación técnica completa (docs/ con 6 archivos)

### Corregido
- Normalización de pesos de brechas en Match (suman exactamente 100 - score)
- Formato de números en todo el frontend (toLocaleString es-CO, sin decimales)
- Gráficos de Predicción con márgenes correctos y líneas alineadas
- Endpoint /observatorio/mapa-metricas (error de clave en diccionario)
- Detección de años parciales vs completos en proyecciones de empleo

## [0.9.0] — 2026-07-10

### Añadido
- Carga de 31 tablas faltantes a Supabase (GEIH completo, OLE ingresos, ESCO, EMICRON, World Bank)
- Endpoints de salarios reales y empleo por sector departamental
- Notas metodológicas en todos los módulos
- Unificación de estilo visual entre módulos

## [0.5.0] — 2026-07-05

### Añadido
- Módulo Coach IA con mejorar CV y practicar entrevista
- Módulo Emprende IA con índice de oportunidad
- Pipeline ETL completo (etl_pipeline.py)
- Scripts de carga a Supabase (load_to_supabase.py)

## [0.3.0] — 2026-07-01

### Añadido
- Módulo Match Inteligente (CV vs vacante + pensum vs mercado)
- Módulo Predicción IA con Chronos T5
- Integración con Gemini 2.5 Flash-Lite y Gemma 4 E4B
- Embeddings con Gemma 300 vía DeepInfra

## [0.1.0] — 2026-06-20

### Añadido
- Estructura inicial del proyecto
- Módulo Observatorio Inteligente con mapa de Colombia
- Dashboard con KPIs nacionales
- Conexión a Supabase PostgreSQL
- Descarga y procesamiento inicial de datasets del DANE y SENA