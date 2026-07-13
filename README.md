# ALBA — Analítica Laboral Basada en IA

**Plataforma de Inteligencia Laboral para Colombia**

ALBA es una plataforma web que conecta la oferta educativa con la demanda real del mercado laboral colombiano, generando recomendaciones accionables para ciudadanos, empresas, universidades y gobiernos mediante inteligencia artificial.

**Todos los datos provienen de fuentes oficiales colombianas disponibles en [datos.gov.co](https://www.datos.gov.co).**

---

## El problema

Colombia enfrenta una desconexión estructural entre lo que se enseña, lo que se aprende y lo que el mercado laboral necesita:

- **24 millones** de colombianos ocupados, pero **58% en informalidad** (GEIH 2025)
- **428.000** programas académicos matriculados en SNIES, muchos sin clara correspondencia con la demanda laboral
- Sin datos unificados, un ciudadano no sabe qué estudiar, un emprendedor no sabe qué negocio tiene potencial, y un gobierno no sabe dónde intervenir

ALBA resuelve esto con una plataforma que **observa, anticipa, conecta, orienta y prepara** al ecosistema laboral colombiano.

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

## Datos abiertos utilizados

**12 fuentes oficiales · 44 tablas · ~744.000 filas en Supabase**

Todos los datos se obtuvieron de **[datos.gov.co](https://www.datos.gov.co)** y portales oficiales colombianos, priorizando los datasets definidos en las **Hojas de Ruta Sectoriales y Nacional de Datos Abiertos Estratégicos**.

| Fuente | Dataset | Enlace oficial | Tablas | Filas |
|--------|---------|----------------|--------|-------|
| DANE | GEIH — empleo, salarios, informalidad | [microdatos.dane.gov.co](https://microdatos.dane.gov.co/index.php/catalog/Mercado_Laboral) | 8 | ~120K |
| DANE | EMICRON — micronegocios | [microdatos.dane.gov.co](https://microdatos.dane.gov.co/index.php/catalog/875) | 5 | ~109 |
| DNP | MDM — desempeño municipal | [datos.gov.co](https://www.datos.gov.co/Estadisticas-Nacionales/Medici-n-del-Desempe-o-Municipal-MDM/nkjx-rsq7) | 3 | ~22K |
| MinTrabajo | PILA — empleo formal por CIIU | [datos.gov.co](https://www.datos.gov.co/Trabajo-y-Pensiones/Pensionados-y-Cotizantes-de-PILA-Boletin-Mensual-/8pqf-rmzr) | 2 | ~652 |
| Confecámaras | RUES — empresas nuevas | [rues.org.co](https://www.rues.org.co) | 3 | ~26K |
| MEN | SNIES — matriculados | [datos.gov.co](https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion/Sistema-Nacional-de-Informacion-de-la-Educacion-Su) | 2 | ~85K |
| MEN | OLE/ETDH — educación para el trabajo | [datos.gov.co](https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion/Programas-de-Educaci-n-para-el-Trabajo-y-el-Desarr/2v94-3ypi) | 2 | ~20K |
| SENA | Programas activos + SPE/APE | [datos.gov.co](https://www.datos.gov.co/Trabajo-y-Pensiones/Servicio-Publico-de-Empleo-SPE-Apuntados-por-Ocupac/8pqf-rmzr) | 4 | ~17K |
| MEN | Saber Pro — calidad educativa | [datos.gov.co](https://www.datos.gov.co/Ciencia-Tecnologia-e-Innovacion) | 1 | ~1.4K |
| ESCO (UE) | Ocupaciones y habilidades | [esco.ec.europa.eu](https://esco.ec.europa.eu) | 7 | ~155K |
| O*NET (EE.UU.) | Ocupaciones estandarizadas | [onetcenter.org](https://www.onetcenter.org) | 7 | ~12K |
| World Bank | Indicadores macro Colombia | [data.worldbank.org](https://data.worldbank.org/country/colombia) | 1 | 128 |

**Proceso de obtención de datos:**
1. Descarga de datasets originales desde [datos.gov.co](https://www.datos.gov.co) y microdatos.dane.gov.co
2. Limpieza y transformación con pipeline ETL (`src/etl_pipeline.py`)
3. Carga a Supabase PostgreSQL (`src/load_to_supabase.py`)
4. Generación de embeddings con Gemma 300 para búsqueda semántica

Detalle completo de variables en [`docs/data_dictionary.md`](docs/data_dictionary.md).

---

## Inteligencia artificial

| Componente | Modelo | Aplicación |
|------------|--------|------------|
| LLM primario | **Gemini 2.5 Flash-Lite** | Match (CV vs vacante), Coach (mejorar CV, entrevista), Emprende (evaluar ideas) |
| LLM conversacional | **Gemini Live** | Coach IA — simulacros de entrevista por voz y texto |
| Forecasting | **Chronos T5 Small** | Predicción zero-shot de empleo, desempleo, informalidad y salarios a 5 y 10 años |
| Embeddings | **Gemma Embeddings 300** | RAG — base de conocimiento para Coach IA (768 dimensiones) |
| Matching híbrido | **ESCO + OLE + LLM** | Score: 50% habilidades reales (ESCO) + 50% análisis del LLM |

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                       │
│  TypeScript · Tailwind CSS · react-simple-maps · recharts       │
│  Playfair Display + Inter                                       │
├─────────────────────────────────────────────────────────────────┤
│                          /api (proxy)                            │
├─────────────────────────────────────────────────────────────────┤
│                    BACKEND (FastAPI + Uvicorn)                  │
│  6 routers: observatorio · prediccion · match · emprende ·      │
│             coach · simulacion                                  │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Supabase   │  Gemini 2.5  │  Chronos T5  │   Gemini Live       │
│  PostgreSQL  │  Flash-Lite  │  (forecast)  │   (coach)           │
│  + pgvector  │              │              │                     │
│  44 tablas   │  Análisis de │  Forecasting │  Voz + texto        │
│  ~744K filas │  texto       │  de series   │  conversacional     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

Detalle completo en [`docs/architecture.md`](docs/architecture.md).

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
| Mapas | react-simple-maps + GeoJSON Colombia (33 deptos) |
| Voz | faster-whisper (STT) + Edge-TTS (TTS) |

---

## Estructura del repositorio

```
├── README.md
├── LICENSE
├── Changelog.md
├── AGENTS.md
├── requirements.txt
│
├── docs/                  # Documentación técnica
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── planteamiento_problema.md
│   ├── marco_metodologico.md
│   ├── fuentes_datos.md
│   └── conclusiones.md
│
├── RECURSOS/              # Material visual para sustentación
│
├── backend/               # API FastAPI
│   └── app/
│       ├── main.py
│       ├── db/
│       ├── services/
│       └── routers/       # 6 routers (observatorio, prediccion, match, emprende, coach, simulacion)
│
├── frontend/              # App React + TypeScript
│   └── src/
│       ├── components/
│       ├── pages/         # 7 páginas (Dashboard + 6 módulos)
│       ├── services/
│       └── utils/
│
├── data/
│   ├── raw/               # Datos originales
│   └── processed/         # Datos limpios
│
├── src/                   # Scripts ETL, carga y utilidades
├── sql/                   # Schemas de base de datos
└── tests/                 # Pruebas
```

---

## Documentación

- [`docs/architecture.md`](docs/architecture.md) — Diagrama de arquitectura e integración
- [`docs/data_dictionary.md`](docs/data_dictionary.md) — Diccionario de las 44 tablas
- [`docs/planteamiento_problema.md`](docs/planteamiento_problema.md) — Definición del problema
- [`docs/marco_metodologico.md`](docs/marco_metodologico.md) — Metodología CRISP-ML
- [`docs/fuentes_datos.md`](docs/fuentes_datos.md) — Enlaces a fuentes oficiales
- [`docs/conclusiones.md`](docs/conclusiones.md) — Hallazgos, limitaciones y próximos pasos

---

## Equipo

- **Líder / Desarrollador:** Manuel Francisco Machado

---

## Licencia

Distribuido bajo la Licencia MIT. Ver [`LICENSE`](LICENSE).
