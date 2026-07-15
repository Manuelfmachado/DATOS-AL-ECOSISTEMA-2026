# ALBA — Analítica Laboral Basada en IA

**Plataforma de Inteligencia Laboral para Colombia**

ALBA es una plataforma web que conecta la oferta educativa con la demanda real del mercado laboral colombiano, generando recomendaciones accionables para ciudadanos, empresas, universidades y gobiernos mediante inteligencia artificial.

> **Todos los datos provienen de [datos.gov.co](https://www.datos.gov.co)** — la plataforma oficial de datos abiertos del Estado colombiano.

---

## Enlaces

| | |
|---|---|
| 🌐 Sitio web | [albacolombia.com](https://albacolombia.com) |
| 📊 Presentación | [`recursos/alba_slides.html`](recursos/alba_slides.html) |
| 🔗 Repositorio | [github.com/Manuelfmachado/DATOS-AL-ECOSISTEMA-2026](https://github.com/Manuelfmachado/DATOS-AL-ECOSISTEMA-2026) |
| 📖 Documentación | [`docs/`](docs/) |
| 🎥 Video demo | [`recursos/DEMO DE ALBA.mp4`](recursos/DEMO%20DE%20ALBA.mp4) |

---

## El problema

Colombia enfrenta una desconexión estructural entre lo que se enseña, lo que se aprende y lo que el mercado laboral necesita:

- **24 millones** de colombianos ocupados, pero **53.3% en informalidad** (GEIH 2025)
- **428.000** programas académicos matriculados en SNIES, muchos sin clara correspondencia con la demanda laboral
- Sin datos unificados, un ciudadano no sabe qué estudiar, un emprendedor no sabe qué negocio tiene potencial, y un gobierno no sabe dónde intervenir
- **Millones de colombianos en zonas rurales no tienen internet** para acceder a herramientas de IA laboral

ALBA resuelve esto con una plataforma que **observa, anticipa, conecta, orienta y prepara** al ecosistema laboral colombiano — **con y sin internet**.

---

## La solución — 6 módulos

```
Observo el mercado  →  Anticipo cambios  →  Encuentro mi lugar  →  Decido emprender  →  Me preparo  →  Simulo escenarios
  (Observatorio)     (Predicción IA)         (Match)              (Emprende IA)        (Coach IA)       (Simulación)
```

| # | Módulo | Pregunta | Actor principal |
|---|--------|----------|-----------------|
| 1 | Observatorio Inteligente | ¿Qué está pasando en el mercado laboral? | Todos |
| 2 | Predicción IA | ¿Qué podría pasar en el futuro? | Gobierno / Universidades |
| 3 | Match Inteligente | ¿Dónde encajo según mi perfil? | Persona / Universidad / Empresa |
| 4 | Emprende IA | ¿Qué negocio tiene potencial en mi municipio? | Emprendedores |
| 5 | Coach IA | ¿Cómo me preparo para conseguir el empleo? | Personas |
| 6 | Simulación | ¿Qué pasaría si cambio mi carrera o sector? | Todos |

---

## Datos abiertos — [www.datos.gov.co](https://www.datos.gov.co)

**12 fuentes oficiales · 44 tablas · ~744.000 filas en Supabase**

Trabajamos exclusivamente con datos abiertos publicados en [datos.gov.co](https://www.datos.gov.co) y portales oficiales, priorizando los datasets de las **Hojas de Ruta Sectoriales y Nacional de Datos Abiertos Estratégicos**.

### Fuentes colombianas · datos.gov.co

| Fuente | Dataset | Tablas | Filas |
|--------|---------|--------|-------|
| DANE | GEIH — empleo, salarios, informalidad | 8 | ~120K |
| DANE | EMICRON — micronegocios | 5 | ~109 |
| DNP | MDM — desempeño municipal | 3 | ~22K |
| MinTrabajo | PILA — empleo formal por CIIU | 2 | ~652 |
| Confecámaras | RUES — empresas nuevas | 3 | ~26K |
| MEN | SNIES — matriculados | 2 | ~85K |
| MEN | OLE/ETDH — educación para el trabajo | 2 | ~20K |
| SENA | Programas activos + SPE/APE | 4 | ~17K |
| MEN | Saber Pro — calidad educativa | 1 | ~1.4K |

### Fuentes internacionales

| Fuente | Dataset | Tablas | Filas |
|--------|---------|--------|-------|
| ESCO (UE) | Ocupaciones y habilidades | 7 | ~155K |
| O*NET (EE.UU.) | Ocupaciones estandarizadas | 7 | ~12K |
| World Bank | Indicadores macro Colombia 2010–2025 | 1 | 128 |

### Proceso ETL

1. Descarga de datasets desde [datos.gov.co](https://www.datos.gov.co) y microdatos.dane.gov.co
2. Limpieza y transformación con pipeline ETL (`etl_pipeline.py`)
3. Carga a Supabase PostgreSQL (`load_to_supabase.py`)
4. Generación de embeddings con Gemma 300 para búsqueda semántica (RAG)

---

## Versión offline

ALBA es la **única plataforma del concurso con versión offline completa**. Funciona con SQLite y modelos locales, permitiendo que municipios rurales y zonas sin conectividad accedan a las mismas 6 herramientas de IA laboral sin depender de la nube.

Ver [`alba-offline/`](alba-offline/) y [`alba-offline/README_OFFLINE.txt`](alba-offline/README_OFFLINE.txt).

---

## Inteligencia artificial

| Componente | Modelo | Aplicación |
|------------|--------|------------|
| LLM primario | Gemini 2.5 Flash-Lite | Match (CV vs vacante), Coach (mejorar CV, entrevista), Emprende (evaluar ideas) |
| LLM conversacional | Gemini Live | Coach IA — simulacros de entrevista por voz y texto |
| Forecasting | Chronos T5 Small | Predicción zero-shot a 5 y 10 años de empleo, desempleo, informalidad y salarios |
| Embeddings | Gemma Embeddings 300 | RAG — base de conocimiento para Coach IA (768 dimensiones) |
| Matching híbrido | ESCO + OLE + LLM | Score: 50% habilidades reales + 50% análisis del LLM |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                       │
│  TypeScript · Tailwind CSS · react-simple-maps · recharts       │
├─────────────────────────────────────────────────────────────────┤
│                          /api (proxy)                            │
├─────────────────────────────────────────────────────────────────┤
│                    BACKEND (FastAPI + Uvicorn)                  │
│  6 routers: observatorio · prediccion · match · emprende ·      │
│             coach · simulacion                                  │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Supabase   │  Gemini 2.5  │  Chronos T5  │   Gemini Live       │
│  PostgreSQL  │  Flash-Lite  │  (forecast)  │   (coach voz)       │
│  + pgvector  │              │              │                     │
│  44 tablas   │  Análisis    │  Zero-shot   │  STT + TTS          │
│  ~744K filas │  de texto    │  5 y 10 años │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | React 18 + TypeScript + Vite + Tailwind CSS 3 |
| Backend | FastAPI (Python) + Uvicorn |
| Base de datos | Supabase (PostgreSQL + pgvector) |
| LLM | Gemini 2.5 Flash-Lite + Gemini Live (Google Cloud) |
| Forecasting | Chronos T5 Small (zero-shot) |
| Embeddings | Gemma Embeddings 300 (768 dimensiones) |
| RAG | PyMuPDF + pgvector + búsqueda coseno |
| Mapas | react-simple-maps + GeoJSON Colombia (33 departamentos) |
| Voz | faster-whisper (STT) + Edge-TTS (TTS) |
| Offline | SQLite + modelos locales (versión offline) |

---

## Estructura del repositorio

```
├── README.md
├── LICENSE
├── AGENTS.md
│
├── docs/                        Documentación técnica
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── planteamiento_problema.md
│   ├── marco_metodologico.md
│   ├── fuentes_datos.md
│   └── conclusiones.md
│
├── recursos/                    Material para sustentación
│   ├── alba_slides.html         Presentación web interactiva
│   ├── presentacion.pptx
│   ├── presentacion.pdf
│   └── portada.png
│
├── backend/app/                 API FastAPI
│   ├── main.py
│   ├── db/supabase.py
│   ├── services/embeddings.py
│   └── routers/                 6 módulos
│
├── frontend/src/                App React + TypeScript
│   ├── components/
│   ├── pages/
│   └── services/
│
├── alba-offline/                Versión offline (SQLite + modelos locales)
│
├── data/                        Datos
│   ├── raw/
│   └── processed/
│
└── scripts/                     ETL, carga, utilidades
```

---

## Equipo

- **Manuel Francisco Machado** — Líder · Data / IA / Frontend
- **Maria Angel Henao** — Investigación / Documentación

---

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
