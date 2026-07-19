# ALBA — Analítica Laboral Basada en IA

> **Plataforma de inteligencia laboral para Colombia**

ALBA conecta la oferta educativa con la demanda real del mercado laboral colombiano. Mediante inteligencia artificial, transforma datos públicos en análisis, predicciones y recomendaciones para ciudadanos, empresas, universidades y entidades gubernamentales.

🌐 **Sitio web:** [www.albacolombia.com](https://www.albacolombia.com)

---

## Propuesta de valor

ALBA permite **observar, anticipar, conectar, orientar y preparar** al ecosistema laboral colombiano desde una sola plataforma, con herramientas disponibles tanto en línea como sin conexión.

### ¿A quién ayuda?

- **Personas:** orientación académica y laboral según su perfil.
- **Emprendedores:** identificación de oportunidades con potencial en su municipio.
- **Empresas:** análisis de perfiles, habilidades y necesidades de talento.
- **Universidades:** conexión de la oferta educativa con la demanda laboral.
- **Gobiernos:** información territorial para orientar políticas y programas.

---

## El problema

Colombia enfrenta una desconexión estructural entre lo que se enseña, lo que se aprende y lo que necesita el mercado laboral:

- **24 millones** de personas ocupadas y **53,3 % de informalidad**, según la GEIH 2025.
- **428.000** registros de programas académicos matriculados en SNIES, muchos sin una correspondencia clara con la demanda laboral.
- La información laboral, educativa, empresarial y territorial se encuentra dispersa.
- Millones de personas en zonas rurales tienen dificultades de conectividad para acceder a herramientas de inteligencia artificial.

> **Origen de los datos nacionales:** las cifras, indicadores y registros utilizados por ALBA provienen de datos abiertos oficiales publicados en `www.datos.gov.co` y, cuando corresponde, de otros portales oficiales del Estado colombiano.

---

## La solución: seis módulos integrados

**Observo el mercado → Anticipo cambios → Encuentro mi lugar → Decido emprender → Me preparo → Simulo escenarios**

| # | Módulo                            | Pregunta que responde                           | Actor principal                    |
| -: | ---------------------------------- | ----------------------------------------------- | ---------------------------------- |
| 1 | **Observatorio Inteligente** | ¿Qué está pasando en el mercado laboral?     | Todos                              |
| 2 | **Predicción IA**           | ¿Qué podría pasar en el futuro?              | Gobierno y universidades           |
| 3 | **Match Inteligente**        | ¿Dónde encajo según mi perfil?               | Personas, universidades y empresas |
| 4 | **Emprende IA**              | ¿Qué negocio tiene potencial en mi municipio? | Emprendedores                      |
| 5 | **Coach IA**                 | ¿Cómo me preparo para conseguir empleo?       | Personas                           |
| 6 | **Simulación**              | ¿Qué pasaría si cambio de carrera o sector?  | Todos                              |

---

# Datos y transparencia

## Datos oficiales de Colombia

> ### 🇨🇴 INFORMACIÓN PROVENIENTE DE `www.datos.gov.co`
>
> Los análisis nacionales de ALBA se construyen con datos abiertos del Estado colombiano. Los conjuntos de datos se obtienen principalmente de `www.datos.gov.co` y se complementan, cuando aplica, con otros portales oficiales de las entidades públicas responsables.

**12 fuentes oficiales · 44 tablas · aproximadamente 744.000 filas almacenadas en Supabase**

ALBA prioriza conjuntos de datos asociados con las Hojas de Ruta Sectoriales y la Hoja de Ruta Nacional de Datos Abiertos Estratégicos.

### Fuentes nacionales

| Fuente        | Información utilizada                 | Tablas | Filas aproximadas | Procedencia                                                |
| ------------- | -------------------------------------- | -----: | ----------------: | ---------------------------------------------------------- |
| DANE          | GEIH: empleo, salarios e informalidad  |      8 |           120.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| DANE          | EMICRON: micronegocios                 |      5 |               109 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| DNP           | MDM: desempeño municipal              |      3 |            22.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| MinTrabajo    | PILA: empleo formal por CIIU           |      2 |               652 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| Confecámaras | RUES: empresas nuevas                  |      3 |            26.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| MEN           | SNIES: estudiantes matriculados        |      2 |            85.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| MEN           | OLE y ETDH: educación para el trabajo |      2 |            20.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| SENA          | Programas activos y SPE/APE            |      4 |            17.000 | **Datos abiertos oficiales — `www.datos.gov.co`** |
| MEN           | Saber Pro: calidad educativa           |      1 |             1.400 | **Datos abiertos oficiales — `www.datos.gov.co`** |

## Fuentes internacionales

Las fuentes internacionales se mantienen diferenciadas de los datos oficiales colombianos y se utilizan para enriquecer la clasificación de ocupaciones, habilidades e indicadores macroeconómicos.

| Fuente                  | Dataset                                              | Tablas | Filas aproximadas |
| ----------------------- | ---------------------------------------------------- | -----: | ----------------: |
| ESCO (Unión Europea)   | Ocupaciones y habilidades                            |      7 |           155.000 |
| O\*NET (Estados Unidos) | Ocupaciones estandarizadas                           |      7 |            12.000 |
| World Bank              | Indicadores macroeconómicos de Colombia, 2010–2025 |      1 |               128 |

> **Nota:** estas fuentes son internacionales y no se atribuyen a `www.datos.gov.co`.

---

## Proceso de datos

1. **Obtención:** descarga de conjuntos de datos publicados en `www.datos.gov.co` y en portales oficiales de las entidades responsables.
2. **Limpieza:** validación, normalización y transformación mediante el pipeline ETL.
3. **Carga:** almacenamiento estructurado en Supabase PostgreSQL.
4. **Enriquecimiento:** generación de embeddings para búsqueda semántica y recuperación aumentada de información.
5. **Consumo:** uso de los datos en los módulos de observación, predicción, match, emprendimiento, preparación y simulación.

---

## Inteligencia artificial

| Componente         | Modelo                | Aplicación                                                                           |
| ------------------ | --------------------- | ------------------------------------------------------------------------------------- |
| LLM principal      | Gemini 2.5 Flash-Lite | Match entre CV y vacante, mejora de CV, entrevistas y evaluación de ideas de negocio |
| LLM conversacional | Gemini Live           | Simulacros de entrevista por voz y texto en Coach IA                                  |
| Forecasting        | Chronos T5 Small      | Predicción zero-shot a 5 y 10 años de empleo, desempleo, informalidad y salarios    |
| Embeddings         | Gemma Embeddings 300  | Base de conocimiento RAG para Coach IA, con 768 dimensiones                           |
| Matching híbrido  | ESCO + OLE + LLM      | Puntaje compuesto por habilidades y análisis del modelo                              |

---

## Versión offline

ALBA cuenta con una versión offline basada en SQLite y modelos locales. Esta versión permite que municipios rurales y zonas con conectividad limitada accedan a las seis herramientas de inteligencia laboral sin depender permanentemente de servicios en la nube.

---

## Arquitectura

```text
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND: React + Vite                        │
│  TypeScript · Tailwind CSS · react-simple-maps · Recharts       │
├─────────────────────────────────────────────────────────────────┤
│                         API / Proxy                             │
├─────────────────────────────────────────────────────────────────┤
│                 BACKEND: FastAPI + Uvicorn                      │
│  Observatorio · Predicción · Match · Emprende · Coach ·         │
│  Simulación                                                     │
├──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Supabase   │  Gemini 2.5  │  Chronos T5  │   Gemini Live       │
│  PostgreSQL  │  Flash-Lite  │  Forecasting │   Coach por voz     │
│  + pgvector  │              │              │                     │
│  44 tablas   │  Análisis    │  Zero-shot   │  STT + TTS          │
│  ~744K filas │  de texto    │  5 y 10 años │                     │
└──────────────┴──────────────┴──────────────┴─────────────────────┘
```

---

## Stack tecnológico

| Capa                | Tecnología                                        |
| ------------------- | -------------------------------------------------- |
| Frontend            | React 18, TypeScript, Vite y Tailwind CSS 3        |
| Backend             | FastAPI, Python y Uvicorn                          |
| Base de datos       | Supabase, PostgreSQL y pgvector                    |
| Modelos de lenguaje | Gemini 2.5 Flash-Lite y Gemini Live                |
| Forecasting         | Chronos T5 Small                                   |
| Embeddings          | Gemma Embeddings 300, 768 dimensiones              |
| RAG                 | PyMuPDF, pgvector y búsqueda por similitud coseno |
| Mapas               | react-simple-maps y GeoJSON de Colombia            |
| Voz                 | faster-whisper y Edge-TTS                          |
| Offline             | SQLite y modelos locales                           |

---

## Estructura del repositorio

```text
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
│   ├── alba_slides.html
│   ├── presentacion.pptx
│   ├── presentacion.pdf
│   └── portada.png
│
├── backend/app/                 API FastAPI
│   ├── main.py
│   ├── db/supabase.py
│   ├── services/embeddings.py
│   └── routers/                 Seis módulos
│
├── frontend/src/                Aplicación React + TypeScript
│   ├── components/
│   ├── pages/
│   └── services/
│
├── alba-offline/                Versión offline
├── data/                        Datos crudos y procesados
└── scripts/                     ETL, carga y utilidades
```

---

## Equipo

- **Manuel Francisco Machado** — Líder · Magíster en Inteligencia Artificial
- **Maria Angel Henao** — Estudiante de Licenciatura · Investigación

---

## Licencia

Este proyecto se distribuye bajo la licencia MIT.
