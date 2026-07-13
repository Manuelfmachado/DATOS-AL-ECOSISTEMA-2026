# ALBA — Analítica Laboral Basada en IA

**Plataforma Nacional de Inteligencia Laboral para Colombia**

> **Concurso Datos al Ecosistema 2026 — Reto 5: Economía y Empleo**
> Nivel: Avanzado | **www.albacolombia.com**

ALBA es una plataforma web que conecta la oferta educativa (SNIES, SENA, OLE/MEN) con la demanda real del mercado laboral (GEIH, PILA, RUES, SPE/APE) y el contexto territorial (DNP/MDM), generando recomendaciones accionables para ciudadanos, empresas, universidades y gobiernos mediante inteligencia artificial.

**Todos los datos provienen de fuentes oficiales colombianas disponibles en [datos.gov.co](https://datos.gov.co).**

---

## ¿Qué problema resuelve ALBA?

Colombia enfrenta una desconexión estructural entre lo que se enseña, lo que se aprende y lo que el mercado laboral necesita:

- **24 millones** de colombianos ocupados, pero **58% en informalidad** (GEIH 2025)
- **428.000** programas académicos matriculados en SNIES, muchos sin clara correspondencia con la demanda laboral
- Sin datos unificados, un ciudadano no sabe qué estudiar, un emprendedor no sabe qué negocio tiene potencial, y un gobierno no sabe dónde intervenir

ALBA resuelve esto con una plataforma que **observa, anticipa, conecta, orienta y prepara** al ecosistema laboral colombiano usando datos abiertos del DANE, SENA, MEN, DNP y fuentes internacionales (O*NET, ESCO, World Bank).

---

## ¿Cómo lo resuelve?

ALBA es una plataforma web con 5 módulos que siguen un flujo narrativo:

```
Observo el mercado  →  Anticipo cambios  →  Encuentro mi lugar  →  Decido emprender  →  Me preparo
  (Observatorio)     (Predicción IA)         (Match)              (Emprende IA)        (Coach IA)
```

| # | Módulo | Pregunta | Actor principal |
|---|--------|----------|-----------------|
| 1 | Observatorio Inteligente | ¿Qué está pasando en el mercado laboral? | Todos |
| 2 | Predicción IA | ¿Qué podría pasar en el futuro? | Gobierno / Universidades |
| 3 | Match Inteligente | ¿Dónde encajo según mi perfil? | Persona / Universidad / Empresa |
| 4 | Emprende IA | ¿Qué negocio tiene potencial en mi municipio? | Emprendedores |
| 5 | Coach IA | ¿Cómo me preparo para conseguir el empleo? | Personas |

---

## Datos abiertos utilizados

**Todos los datos provienen de [datos.gov.co](https://datos.gov.co) y portales oficiales colombianos.**

| Fuente | Dataset | Tablas | Filas |
|--------|---------|--------|-------|
| [datos.gov.co](https://datos.gov.co) (DANE) | GEIH — empleo, salarios, informalidad | 8 | ~120K |
| [datos.gov.co](https://datos.gov.co) (DANE) | EMICRON — micronegocios | 5 | ~109 |
| [datos.gov.co](https://datos.gov.co) (DNP) | MDM — desempeño municipal | 3 | ~22K |
| [datos.gov.co](https://datos.gov.co) (MinTrabajo) | PILA — empleo formal por CIIU | 2 | ~652 |
| [datos.gov.co](https://datos.gov.co) (Confecámaras) | RUES — empresas nuevas | 3 | ~26K |
| [datos.gov.co](https://datos.gov.co) (MEN) | SNIES — matriculados | 2 | ~85K |
| [datos.gov.co](https://datos.gov.co) (MEN) | OLE/ETDH — educación para el trabajo | 2 | ~20K |
| [datos.gov.co](https://datos.gov.co) (SENA) | Programas activos + SPE/APE | 4 | ~17K |
| [datos.gov.co](https://datos.gov.co) (MEN) | Saber Pro — calidad educativa | 1 | ~1.4K |
| [ESCO](https://esco.ec.europa.eu) (EU) | Ocupaciones y habilidades | 7 | ~155K |
| [O*NET](https://www.onetcenter.org) (EE.UU.) | Ocupaciones estandarizadas | 7 | ~12K |
| [World Bank](https://data.worldbank.org/country/colombia) | Indicadores macro Colombia | 1 | 128 |
| IA | Predicciones Chronos T5 | 2 | ~436 |

**Total: 44 tablas · ~744K filas en Supabase**

---

## Inteligencia artificial

| Componente | Modelo | Uso |
|------------|--------|-----|
| LLM primario | **Gemini 2.5 Flash-Lite** | Match (CV vs vacante), Coach (mejorar CV, entrevista), Emprende (evaluar ideas) |
| LLM conversacional | **Gemini Live** | Coach IA — simulacros de entrevista por voz y texto |
| Forecasting | **Chronos T5 Small** | Predicción zero-shot de empleo, desempleo, informalidad y salarios a 5 y 10 años |
| Embeddings | **Gemma Embeddings 300** | RAG — base de conocimiento para Coach IA (768 dimensiones) |
| Matching | **ESCO + OLE + LLM** | Score híbrido: 50% habilidades reales + 50% análisis del LLM |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Vercel)                             │
│  React 18 + TypeScript + Vite + Tailwind CSS 3                  │
│  albacolombia.com                                               │
├─────────────────────────────────────────────────────────────────┤
│                    /api/* → Railway (rewrites)                   │
├─────────────────────────────────────────────────────────────────┤
│                    BACKEND (Railway)                             │
│  FastAPI + Uvicorn · 5 routers · 40+ endpoints                  │
│  albacolombia-backend.railway.app                               │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Supabase   │  Gemini 2.5  │  Chronos T5  │   Gemini Live       │
│  PostgreSQL  │  Flash-Lite  │  (forecast)  │   (coach)           │
│  + pgvector  │              │              │                     │
│  44 tablas   │              │              │                     │
│  ~744K filas │              │              │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS 3 |
| Backend | FastAPI (Python) + Uvicorn |
| Base de datos | Supabase (PostgreSQL + pgvector) |
| LLM primario | Gemini 2.5 Flash-Lite (Google Cloud) |
| LLM conversacional | Gemini Live (Google Cloud) |
| Forecasting | Chronos T5 Small (zero-shot, cron batch) |
| ML tradicional | XGBoost + Prophet + scikit-learn |
| Embeddings | Gemma Embeddings 300 (768 dimensiones) |
| RAG | PyMuPDF + pgvector + búsqueda coseno |
| Mapas | react-simple-maps + GeoJSON Colombia (33 deptos) |
| Voz Coach | faster-whisper (STT) + Edge-TTS (TTS) |
| Infraestructura | Vercel (frontend) + Railway (backend) + Supabase + Namecheap |

---

## Cómo ejecutarlo localmente

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
```

---

## Despliegue en producción

### 1. Dominio

- **Namecheap:** `www.albacolombia.com`

### 2. Frontend → Vercel

- Conectar repo de GitHub
- Vercel detecta Vite automáticamente
- URL: `albacolombia.vercel.app`

### 3. Backend → Railway

- Conectar carpeta `backend/`
- Apuntar a `main.py` con Uvicorn
- URL: `albacolombia-backend.railway.app`

### 4. DNS en Namecheap

| Registro | Nombre | Valor |
|----------|--------|-------|
| CNAME | www | cname.vercel-dns.com |
| A | @ | 76.76.21.21 |

### 5. Variables de entorno

Configurar en Vercel y Railway:
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `GOOGLE_API_KEY`

### 6. Vercel rewrites

Agregar `vercel.json` en la raíz del frontend para redirigir `/api/*` a Railway.

---

## Estructura del repositorio

```
DATOS AL ECOSISTEMA 2026/
├── README.md
├── LICENSE
├── Changelog.md
├── AGENTS.md
├── requirements.txt
├── vercel.json
│
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── planteamiento_problema.md
│   ├── marco_metodologico.md
│   ├── fuentes_datos.md
│   └── conclusiones.md
│
├── RECURSOS/
│   └── (presentación y portada)
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── db/supabase.py
│   │   ├── services/
│   │   │   ├── llm_gemini.py
│   │   │   └── embeddings.py
│   │   └── routers/
│   │       ├── observatorio.py
│   │       ├── prediccion.py
│   │       ├── match.py
│   │       ├── emprende.py
│   │       └── coach.py
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/api.ts
│   │   └── utils/format.ts
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── etl_pipeline.py
│   ├── download_worldbank.py
│   ├── prediccion_chronos.py
│   ├── pdf_to_rag.py
│   ├── load_to_supabase.py
│   └── ...
│
├── sql/
│   ├── schema_supabase.sql
│   ├── schema_fix.sql
│   └── ...
│
└── tests/
    └── test_chronos.py
```

---

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

---

## Equipo

- **Líder / Desarrollador:** Manuel Francisco Machado

---

## Licencia

Este proyecto está bajo la Licencia MIT — ver [`LICENSE`](LICENSE).