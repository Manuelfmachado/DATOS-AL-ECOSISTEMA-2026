# ALBA — Analítica Laboral Basada en IA

## Contexto del proyecto

**ALBA** es la Plataforma Nacional de Inteligencia Laboral construida para el concurso **Datos al Ecosistema 2026 — Reto 5: Economía y Empleo**. Usa datos abiertos del DANE y otras fuentes oficiales colombianas, combinados con inteligencia artificial, para conectar la oferta educativa (SNIES, SENA, OLE/MEN) con la demanda real del mercado laboral (GEIH, PILA, RUES, SPE/APE SENA) y el contexto territorial (DNP/MDM), generando recomendaciones accionables para ciudadanos, empresas, universidades y gobiernos.

**Acrónimo oficial:**
> **ALBA** = **A**nalítica **L**aboral **B**asada en **IA**

## Stack tecnológico

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS 3 + Playfair Display + Inter
- **Backend:** FastAPI (Python) + Uvicorn
- **Base de datos / vector store:** Supabase (PostgreSQL + pgvector)
- **LLM:** Gemini 2.5 Flash-Lite vía Google Cloud Agent Platform (primario); Gemini Live (coach conversacional)
- **ML / series temporales:** Chronos T5 Small (forecasting zero-shot, cron job batch); XGBoost + Prophet + scikit-learn
- **Embeddings:** Gemma Embeddings 300 (`google/embeddinggemma-300m`) vía Google Cloud, 768 dimensiones (calidad máxima sin truncar)
- **RAG ( conocimiento base):** PDFs -> PyMuPDF -> chunks -> Gemma 300 embeddings -> Supabase pgvector; búsqueda por similitud coseno con función SQL `buscar_embeddings_vector`
- **Mapas:** react-simple-maps + GeoJSON real de Colombia (33 departamentos)
- **Voz Coach:** faster-whisper (STT) + Edge-TTS (TTS) + fallback texto
- **Datos locales:** CSVs descargados en `data/raw/` → procesados en `data/processed/`
- **Infraestructura objetivo:** Vercel (frontend) + Railway (backend/cron) + Supabase + Namecheap

## Estructura del repositorio

```
C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026
├── backend/
│   ├── app/
│   │   ├── db/
│   │   │   └── supabase.py       # Cliente Supabase
│   │   ├── services/
│   │   │   └── embeddings.py     # Cliente Google Cloud Gemma 300 embeddings
│   │   ├── routers/
│   │   │   ├── observatorio.py   # /api/observatorio
│   │   │   ├── prediccion.py     # /api/prediccion
│   │   │   ├── match.py          # /api/match
│   │   │   ├── emprende.py       # /api/emprende
│   │   │   └── coach.py          # /api/coach
│   │   └── main.py               # Entrypoint FastAPI
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.tsx        # Sidebar metálico y navegación
│   │   │   └── MapaColombia.tsx  # Mapa real con react-simple-maps
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Observatorio.tsx
│   │   │   ├── Prediccion.tsx
│   │   │   ├── Match.tsx
│   │   │   ├── EmprendeIA.tsx
│   │   │   └── Coach.tsx
│   │   └── services/api.ts       # Cliente Axios hacia backend
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
├── data/
│   ├── raw/                      # Datasets descargados
│   └── processed/                # CSVs limpios listos para cargar
├── download_worldbank.py                    # Descarga indicadores del Banco Mundial para Colombia
├── prediccion_chronos.py                    # Entrena Chronos T5 y genera predicciones_mundiales.json
├── etl_pipeline.py                          # Pipeline principal de limpieza
├── pdf_to_rag.py                            # Ingesta PDFs a RAG (PyMuPDF + Gemma 300 embeddings)
├── load_to_supabase.py                      # Carga de CSVs a Supabase
├── schema_supabase.sql                      # DDL inicial
├── schema_fix.sql                           # DDL de correcciones
├── schema_fix_embeddings_dim.sql            # Migra tablas de embeddings a 768 dimensiones
├── schema_new_tables_spe_ole_dnp.sql        # DDL tablas SPE, OLE y DNP
├── schema_rag_rpc.sql                       # Función SQL buscar_embeddings_vector
└── evaluar_datasets.py                      # Evaluación y priorización de datasets
```

## Los 5 módulos de ALBA

| # | Módulo | ¿Qué responde? | Actor principal |
|---|---|---|---|
| 1 | **Observatorio Inteligente** | ¿Qué está pasando en el mercado laboral? | Todos |
| 2 | **Predicción IA** | ¿Qué podría pasar en el futuro? Sectores, profesiones, habilidades y salarios a 5 y 10 años | Gobierno / Universidades / Todos |
| 3 | **Match Inteligente** | ¿Dónde encaja mi perfil, carrera, empresa o municipio? | Persona / Universidad / Empresa / Municipio |
| 4 | **Emprende IA** | ¿Qué negocio tiene mayor potencial en mi municipio? | Emprendedores / Gobierno |
| 5 | **Coach IA** | ¿Cómo me preparo para conseguir el empleo? | Personas |

### Flujo narrativo

```
Observo el mercado  →  Anticipo cambios  →  Encuentro mi lugar  →  Decido trabajar o emprender  →  Me preparo
    (Observatorio)     (Predicción IA)         (Match)                (Emprende IA)                 (Coach)
```

## Cómo ejecutar localmente

### Backend

```powershell
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm run dev
```

El frontend corre en `http://localhost:5173` y redirige las llamadas `/api` al backend en `http://127.0.0.1:8000`.

## Convenciones de código

- Usar **español** para textos de UI, nombres de endpoints y documentación del proyecto (el concurso es en español).
- Usar **inglés** solo para variables técnicas del código cuando sea estándar (ej. `loading`, `data`, `handleSubmit`).
- Componentes React: PascalCase. Funciones auxiliares: camelCase.
- Estilos con clases Tailwind; el tema visual es "lámina metálica" con bordes dorados (#d4af37), fondo oscuro (#050813) y tipografías Playfair Display + Inter.
- Backend: routers en `app/routers/`, cada uno con su propio `router = APIRouter(prefix="/api/...", tags=["..."])`.

## Decisiones de diseño importantes

1. **Arquitectura de 5 módulos:** Se redujo de 6 a 5 módulos. Alerta Curricular y Reskilling quedan integrados dentro de **Match Inteligente** como pestañas/flujos internos.
2. **ALBA = Analítica Laboral Basada en IA:** El acrónimo se ajustó para destacar el uso de IA (Gemini, Chronos, embeddings, RAG), alineado con el enfoque del concurso.
3. **Emprende IA con Índice de Oportunidad:** En lugar de prometer "probabilidad de éxito" (difícil de justificar), se calcula un **Índice de Potencial** 0-100 basado en datos (crecimiento del sector, competencia, demanda laboral, incentivos).
4. **Predicción IA con Chronos T5 sobre datos mundiales:** El módulo renombrado de Simulador a Predicción genera proyecciones a 5 y 10 años para sectores, profesiones, habilidades y salarios. Las series temporales provienen del Banco Mundial (World Bank Open Data) para Colombia (2010-2025), con las que Chronos T5 Small predice zero-shot la participación sectorial del empleo, desempleo, formalidad y PIB por empleado. Profesiones y habilidades se proyectan con heurísticos basados en el crecimiento sectorial, O*NET/ESCO y el WEF Future of Jobs Report. Los resultados se guardan en `data/processed/predicciones_mundiales.json` y se sirven vía `/api/prediccion/*`.
5. **Coach IA simplificado y poderoso:** Dos funciones centrales:
   - **Mejorar CV:** El usuario pega su CV o carga PDF/Word; el LLM lo mejora para que sea atractivo pero realista (sin inventar experiencias), optimiza palabras clave para filtros ATS y explica por qué el CV mejorado es efectivo.
   - **Practicar entrevista:** Chatbot de texto para simular entrevistas y responder preguntas de procesos de selección.
6. **Forecasting con Chronos T5 Small:** Se ejecuta como cron job batch, guarda predicciones en `data/processed/predicciones_mundiales.json` y el frontend las consume. Chronos-Bolt y Chronos 2 se evaluarán si hay tiempo.
7. **Datos locales, no API en vivo:** Se descargan datasets oficiales una sola vez y se procesan localmente. No se consulta la API Socrata en cada request. SPE se aproxima con inscritos de la Agencia Pública de Empleo (APE) del SENA; OLE se aproxima con programas de Educación para el Trabajo y el Desarrollo Humano (ETDH) del MEN; DNP se aproxima con la Medición del Desempeño Municipal (MDM).
8. **Sin scraping masivo:** Se curan manualmente 30–50 ofertas laborales y 5–10 currículos/pensums para el coach.
9. **RUES como detector de sectores emergentes:** El registro de nuevas empresas se usa como proxy de sectores en crecimiento.
10. **Coach online:** El coach usa Gemini 2.5 Flash-Lite para análisis de CV y Gemini Live para simulacros de entrevista por voz y texto.
11. **Embeddings con Gemma 300 a 768 dimensiones:** Se usa `google/embeddinggemma-300m` vía Google Cloud en lugar de modelos locales, aprovechando calidad multilingüe. No se truncan las dimensiones (sin MRL).
12. **RAG con PyMuPDF:** La base de conocimiento se ingesta con PyMuPDF, se divide en chunks con overlap y se indexa en Supabase pgvector. La búsqueda usa similitud coseno mediante la función PostgreSQL `buscar_embeddings_vector`.
13. **No se incluye SECOP en el MVP:** El dataset es de ~9 GB y no aporta directamente a las 5 funciones principales.

## Variables de entorno

Ambos `.env` (raíz y `backend/.env`) deben contener:

```env
SUPABASE_URL=https://vyerhngdkzyhbhucolek.supabase.co
SUPABASE_KEY=<service_role_key>

# Google Cloud / Google AI Studio (primario)
GOOGLE_API_KEY=<tu_api_key_de_google>
```

## Próximos pasos abiertos

- Configurar GOOGLE_API_KEY y probar todos los endpoints con Gemini 2.5 Flash-Lite.
- Migrar embeddings de RAG a Gemini Multimodal Embeddings si aplica.
- Limpiar filas duplicadas en Supabase (departamentos, etc.).
- Ejecutar `schema_new_tables_spe_ole_dnp.sql` en Supabase SQL Editor y recargar las nuevas tablas.
- Ejecutar `schema_fix_embeddings_dim.sql` + `schema_rag_rpc.sql` para migrar a 768d y activar búsqueda vectorial.
- Evaluar Chronos-Bolt cuando el paquete oficial lo soporte o cuando se consigan series históricas locales de 5+ años.
- Cargar `predicciones_mundiales.json` a Supabase para servirlo desde producción.
- Ingerir guias/formalización en RAG con `pdf_to_rag.py`.
- Preparar despliegue en Vercel + Railway + Namecheap.

## Contacto / responsable

Proyecto personal para el concurso Datos al Ecosistema 2026.
