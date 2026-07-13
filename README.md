# ALBA — Analítica Laboral Basada en IA

**Plataforma Nacional de Inteligencia Laboral para Colombia**

> Concurso **Datos al Ecosistema 2026 — Reto 5: Economía y Empleo**
> Nivel: Avanzado

ALBA conecta la oferta educativa (SNIES, SENA, OLE/MEN) con la demanda real del mercado laboral (GEIH, PILA, RUES, SPE/APE) y el contexto territorial (DNP/MDM), generando recomendaciones accionables para ciudadanos, empresas, universidades y gobiernos mediante inteligencia artificial.

## Tabla de contenidos

- [El problema](#el-problema)
- [La solución](#la-solución)
- [Arquitectura](#arquitectura)
- [Stack tecnológico](#stack-tecnológico)
- [Los 5 módulos](#los-5-módulos)
- [Inteligencia artificial](#inteligencia-artificial)
- [Datos abiertos utilizados](#datos-abiertos-utilizados)
- [Cómo ejecutarlo](#cómo-ejecutarlo)
- [Estructura del repositorio](#estructura-del-repositorio)
- [Equipo](#equipo)
- [Licencia](#licencia)

## El problema

Colombia enfrenta una desconexión estructural entre lo que se enseña, lo que se aprende y lo que el mercado laboral necesita:

- **24 millones** de colombianos ocupados, pero **58% en informalidad** (GEIH 2025)
- **428.000** programas académicos matriculados en SNIES, muchos sin clara correspondencia con la demanda laboral
- Sin datos unificados, un ciudadano no sabe qué estudiar, un emprendedor no sabe qué negocio tiene potencial, y un gobierno no sabe dónde intervenir

ALBA resuelve esto con una plataforma que **observa, anticipa, conecta, orienta y prepara** al ecosistema laboral colombiano usando datos abiertos del DANE, SENA, MEN, DNP y fuentes internacionales (O*NET, ESCO, World Bank).

## La solución

ALBA es una plataforma web con 5 módulos que siguen un flujo narrativo:

```
Observo el mercado  →  Anticipo cambios  →  Encuentro mi lugar  →  Decido emprender  →  Me preparo
  (Observatorio)     (Predicción IA)         (Match)              (Emprende IA)        (Coach IA)
```

Cada módulo responde a una pregunta concreta:

| # | Módulo | Pregunta | Actor principal |
|---|--------|----------|-----------------|
| 1 | Observatorio Inteligente | ¿Qué está pasando en el mercado laboral? | Todos |
| 2 | Predicción IA | ¿Qué podría pasar en el futuro? | Gobierno / Universidades |
| 3 | Match Inteligente | ¿Dónde encajo según mi perfil? | Persona / Universidad / Empresa |
| 4 | Emprende IA | ¿Qué negocio tiene mayor potencial en mi municipio? | Emprendedores |
| 5 | Coach IA | ¿Cómo me preparo para conseguir el empleo? | Personas |

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                   │
│  Tailwind CSS · Playfair Display + Inter · react-simple-maps     │
│  Puerto: 5173                                                    │
├─────────────────────────────────────────────────────────────────┤
│                          /api (proxy)                            │
├─────────────────────────────────────────────────────────────────┤
│                     BACKEND (FastAPI + Uvicorn)                  │
│  5 routers: observatorio · prediccion · match · emprende · coach │
│  Puerto: 8000                                                    │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Supabase   │  LLM Gemini  │  Chronos T5  │   DeepInfra Gemma   │
│  PostgreSQL  │  2.5 Flash   │  (forecast)  │   4 E4B (fallback)  │
│  + pgvector  │  -Lite       │              │                     │
│  (44 tablas  │              │              │                     │
│   744K filas)│              │              │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

Detalle completo en [`docs/architecture.md`](docs/architecture.md).

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS 3 |
| Backend | FastAPI (Python) + Uvicorn |
| Base de datos | Supabase (PostgreSQL + pgvector) |
| LLM primario | Gemini 2.5 Flash-Lite (Google Cloud) |
| LLM fallback | Gemma 4 E4B (DeepInfra) |
| Forecasting | Chronos T5 Small (zero-shot, cron batch) |
| ML tradicional | XGBoost + Prophet + scikit-learn |
| Embeddings | Gemma Embeddings 300 (768 dimensiones) |
| RAG | PyMuPDF + pgvector + búsqueda coseno |
| Mapas | react-simple-maps + GeoJSON Colombia (33 deptos) |
| Voz Coach | faster-whisper (STT) + Edge-TTS (TTS) |
| Infraestructura | Vercel (frontend) + Railway (backend) + Supabase + Namecheap |

## Inteligencia artificial

ALBA integra múltiples componentes de IA:

### Modelos de lenguaje (LLM)
- **Gemini 2.5 Flash-Lite** (primario): análisis de CV vs vacante, evaluación de ideas de negocio, coaching de entrevistas, mejora de CV
- **Gemma 4 E4B** (fallback vía DeepInfra): respaldo cuando Gemini no está disponible

### Forecasting con redes neuronales Transformer
- **Chronos T5 Small**: predicción zero-shot de series temporales (empleo, desempleo, informalidad, salarios) con datos del Banco Mundial y GEIH

### RAG (Retrieval-Augmented Generation)
- Ingesta de PDFs con PyMuPDF → chunks con overlap → embeddings Gemma 300 (768d) → Supabase pgvector
- Búsqueda semántica con similitud coseno vía función SQL `buscar_embeddings_vector`

### Embeddings
- `google/embeddinggemma-300m` vía DeepInfra, 768 dimensiones (calidad máxima sin truncar)

### Matching con datos reales
- ESCO (habilidades por ocupación) + OLE-MEN (ingresos reales de egresados) + LLM para interpretación
- Score híbrido: 50% intersección de habilidades reales + 50% análisis del LLM

## Datos abiertos utilizados

| Fuente | Dataset | Tablas | Filas |
|--------|---------|--------|-------|
| DANE | GEIH (empleo, salarios, informalidad) | 8 | ~120K |
| DANE | EMICRON (micronegocios) | 5 | ~109 |
| DANE | DNP-MDM (desempeño municipal) | 3 | ~22K |
| MinTrabajo | PILA (empleo formal por CIIU) | 2 | ~652 |
| Confecámaras | RUES (empresas nuevas) | 3 | ~26K |
| MEN | SNIES (matriculados) | 2 | ~85K |
| MEN | OLE/ETDH (educación para el trabajo) | 2 | ~20K |
| SENA | Programas activos + SPE/APE | 4 | ~17K |
| EU (ESCO) | Ocupaciones y habilidades | 7 | ~155K |
| EE.UU. (O*NET) | Ocupaciones estandarizadas | 7 | ~12K |
| MEN | Saber Pro (calidad educativa) | 1 | ~1.4K |
| World Bank | Indicadores macro Colombia | 1 | 128 |
| IA | Predicciones Chronos T5 | 2 | ~436 |

**Total: 44 tablas · ~744K filas en Supabase**

Detalle de variables en [`docs/data_dictionary.md`](docs/data_dictionary.md).
Enlaces oficiales en [`docs/fuentes_datos.md`](docs/fuentes_datos.md).

## Cómo ejecutarlo

### Requisitos

- Python 3.11+
- Node.js 18+
- Cuenta de Supabase (PostgreSQL + pgvector)
- API keys: Google (Gemini), DeepInfra (Gemma)

### Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

El frontend corre en `http://localhost:5173` y redirige `/api` al backend en `http://127.0.0.1:8000`.

### Variables de entorno

Crear `backend/.env`:

```env
SUPABASE_URL=https://[tu-proyecto].supabase.co
SUPABASE_KEY=[service_role_key]
GOOGLE_API_KEY=[tu_api_key]
DEEPINFRA_API_KEY=[tu_api_key]
```

## Estructura del repositorio

```
DATOS AL ECOSISTEMA 2026/
├── README.md                          # Este archivo
├── LICENSE                            # Licencia MIT
├── AGENTS.md                          # Documentación técnica del proyecto
├── Changelog.md                       # Registro de versiones
├── requirements.txt                   # Dependencias Python (raíz)
│
├── docs/                              # Documentación técnica
│   ├── architecture.md                # Diagrama de arquitectura
│   ├── data_dictionary.md             # Diccionario de datos
│   ├── planteamiento_problema.md      # Definición del problema
│   ├── marco_metodologico.md          # Metodología CRISP-ML
│   ├── fuentes_datos.md               # Enlaces a fuentes oficiales
│   └── conclusiones.md                # Hallazgos y próximos pasos
│
├── RECURSOS/                          # Material visual para sustentación
│   └── (presentación y portada)
│
├── backend/                           # API FastAPI
│   ├── app/
│   │   ├── main.py                    # Entrypoint
│   │   ├── db/supabase.py             # Cliente Supabase
│   │   ├── services/
│   │   │   ├── llm_gemini.py          # Gemini 2.5 Flash-Lite
│   │   │   ├── llm.py                 # Gemma 4 (DeepInfra fallback)
│   │   │   └── embeddings.py          # Gemma 300 embeddings
│   │   └── routers/
│   │       ├── observatorio.py        # /api/observatorio
│   │       ├── prediccion.py          # /api/prediccion
│   │       ├── match.py               # /api/match
│   │       ├── emprende.py            # /api/emprende
│   │       └── coach.py               # /api/coach
│   └── requirements.txt
│
├── frontend/                          # App React + TypeScript
│   ├── src/
│   │   ├── components/                # Layout, MapaColombia, Icon
│   │   ├── pages/                     # 6 páginas (Dashboard + 5 módulos)
│   │   ├── services/api.ts            # Cliente Axios
│   │   └── utils/format.ts            # Formato COP, números, porcentajes
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── data/
│   ├── raw/                           # Datasets originales descargados
│   └── processed/                     # CSVs limpios listos para cargar
│
├── src/                               # Scripts ETL, carga y utilidades
│   ├── etl_pipeline.py                # Pipeline principal de limpieza
│   ├── download_worldbank.py          # Descarga indicadores Banco Mundial
│   ├── prediccion_chronos.py          # Entrena Chronos T5 + genera JSON
│   ├── pdf_to_rag.py                  # Ingesta PDFs a RAG
│   ├── load_to_supabase.py            # Carga CSVs a Supabase
│   └── ...                            # Otros scripts de ETL y carga
│
├── sql/                               # Eschemas de base de datos
│   ├── schema_supabase.sql            # DDL inicial
│   ├── schema_fix.sql                 # Correcciones
│   ├── schema_nuevas_tablas.sql       # Tablas nuevas
│   └── ...                            # Otros schemas
│
├── tests/                             # Pruebas y archivos temporales
│   └── test_chronos.py
│
├── notebooks/                         # Notebooks (si aplican)
├── docs/                              # Documentación técnica
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── planteamiento_problema.md
│   ├── marco_metodologico.md
│   ├── fuentes_datos.md
│   └── conclusiones.md
│
└── RECURSOS/                          # Material visual para sustentación
    └── README.md
```

## Estado del proyecto

✅ Frontend y backend funcionando localmente
✅ Datos cargados en Supabase (44 tablas, ~744K filas)
✅ 5 módulos completos: Observatorio, Predicción IA, Match Inteligente, Emprende IA, Coach IA
✅ 40+ endpoints API probados
✅ Mapa real de Colombia con 33 departamentos
✅ Salarios reales del DANE GEIH (406 ocupaciones)
✅ Empleo por departamento × sector CIIU (95K registros)
✅ ESCO + OLE integrados en Match Inteligente
✅ Documentación técnica completa (docs/)
🔄 Despliegue en producción (Vercel + Railway + Supabase)
🔄 Presentación para concurso (13 julio deadline)

## Equipo

- **Líder / Desarrollador:** Manuel Francisco Machado

## Licencia

Este proyecto está bajo la Licencia MIT — ver [`LICENSE`](LICENSE).