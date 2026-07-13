# Arquitectura de ALBA

## Visión general

ALBA es una aplicación web full-stack con arquitectura en 3 capas:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CAPA DE PRESENTACIÓN                         │
│                                                                      │
│  React 18 + TypeScript + Vite + Tailwind CSS 3                       │
│  ├── Layout (sidebar metálico dorado)                                │
│  ├── Dashboard (KPIs nacionales)                                     │
│  ├── Observatorio (mapa + gráficos + tablas)                         │
│  ├── Predicción IA (4 pestañas: sectores, profesiones, habilidades) │
│  ├── Match Inteligente (CV vs vacante + pensum vs mercado)          │
│  ├── Emprende IA (índice de oportunidad + evaluación de ideas)      │
│  └── Coach IA (mejorar CV + practicar entrevista)                   │
│                                                                      │
│  react-simple-maps + GeoJSON Colombia (33 departamentos)             │
│  recharts (gráficos) · Playfair Display + Inter                      │
│  Puerto: 5173                                                        │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ /api (proxy Vite)
┌──────────────────────────────┴───────────────────────────────────────┐
│                         CAPA DE LÓGICA                               │
│                                                                      │
│  FastAPI (Python) + Uvicorn                                          │
│  ├── /api/observatorio  → GEIH + PILA + RUES + DNP + SPE             │
│  ├── /api/prediccion    → Chronos T5 + World Bank + GEIH salarios    │
│  ├── /api/match         → ESCO + OLE + LLM híbrido                   │
│  ├── /api/emprende      → EMICRON + RUES + LLM                       │
│  └── /api/coach         → Gemini/Gemma + RAG + faster-whisper        │
│                                                                      │
│  Puerto: 8000                                                        │
└──────┬───────────────┬───────────────┬───────────────┬───────────────┘
       │               │               │               │
┌──────┴───────┐ ┌─────┴──────┐ ┌──────┴───────┐ ┌─────┴──────┐
│  Supabase    │ │  Gemini    │ │  Chronos T5  │ │  Gemini    │
│  PostgreSQL  │ │  2.5 Flash │ │  Small       │ │  Live      │
│  + pgvector  │ │  -Lite     │ │  (batch)     │ │  (coach)   │
│              │ │            │ │              │ │            │
│  44 tablas   │ │  Análisis  │ │  Forecasting │ │  Voz +     │
│  ~744K filas │ │  de texto  │ │  series      │ │  texto     │
└──────────────┘ └────────────┘ └──────────────┘ └────────────┘
```

## Flujo de datos

```
1. Descarga (una sola vez)
   DANE · SENA · MEN · DNP · World Bank → data/raw/

2. ETL (etl_pipeline.py)
   data/raw/ → limpieza + transformación → data/processed/

3. Carga (load_to_supabase.py)
   data/processed/*.csv → Supabase PostgreSQL (44 tablas)

4. Forecasting batch (prediccion_chronos.py)
   World Bank + GEIH → Chronos T5 → predicciones_mundiales.json
                      → Supabase predicciones_geih

5. RAG (pdf_to_rag.py)
   PDFs → PyMuPDF → chunks → Gemma 300 embeddings → Supabase pgvector

6. Request del usuario
   Frontend → /api/* → Supabase + LLM + Chronos → respuesta JSON → Frontend
```

## Componentes de IA

### 1. Gemini 2.5 Flash-Lite (LLM primario)
- **Uso:** Match (CV vs vacante), Coach (mejorar CV, entrevista), Emprende (evaluar ideas)
- **Endpoint:** Google Cloud Agent Platform / Google AI Studio

### 2. Gemini Live (LLM conversacional)
- **Uso:** Coach IA — simulacros de entrevista por voz y texto
- **Endpoint:** Google Cloud Agent Platform
- **Características:** Streaming de audio bidireccional, contexto persistente

### 2. Chronos T5 Small (Forecasting)
- **Uso:** Predicción de empleo, desempleo, informalidad y salarios a 5 y 10 años
- **Método:** Zero-shot forecasting sobre series temporales del Banco Mundial y GEIH
- **Ejecución:** Cron job batch → guarda en JSON y Supabase

### 3. Gemma Embeddings 300 (RAG)
- **Uso:** Base de conocimiento para Coach IA (guías, formalización, normativas)
- **Dimensiones:** 768 (sin truncar, calidad máxima)
- **Búsqueda:** Similitud coseno vía función SQL `buscar_embeddings_vector`

### 4. Matching híbrido (Match Inteligente)
- **Paso 1:** Extraer ocupación de la vacante → buscar en ESCO
- **Paso 2:** Comparar habilidades reales requeridas vs detectadas en CV
- **Paso 3:** Buscar salarios reales de egresados en OLE-MEN
- **Paso 4:** LLM genera interpretación textual (no números)
- **Score:** 50% intersección de habilidades + 50% análisis del LLM

## Infraestructura de despliegue

| Componente | Plataforma | URL |
|------------|-----------|-----|
| Frontend | Vercel | albacolombia.com |
| Backend | Railway | albacolombia-backend.railway.app |
| Base de datos | Supabase | supabase.co |
| Dominio | Namecheap | www.albacolombia.com |

## Seguridad

- Variables de entorno en `.env` (no commiteadas)
- `.gitignore` excluye credenciales, datos pesados y archivos temporales
- Supabase Row Level Security deshabilitada para tablas de datos públicos
- API keys nunca se exponen al frontend