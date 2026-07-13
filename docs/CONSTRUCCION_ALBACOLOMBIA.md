# ALBACOLOMBIA — Documento Técnico de Construcción

**Acrónimo:** **A**lineación **L**aboral **B**asada en **A**nalítica en **Colombia**
**Concurso:** Datos al Ecosistema 2026 — Reto 5: Economía y Empleo
**Versión del documento:** 1.0
**Fecha:** Julio 2026

---

## 1. Propósito general del proyecto

ALBACOLOMBIA es una plataforma de inteligencia laboral que usa datos abiertos del DANE y otras fuentes oficiales colombianas para alinear la **oferta educativa** (SNIES, SENA, Saber Pro) con la **demanda real del mercado laboral** (GEIH, PILA, RUES y vacantes curadas).

La plataforma se materializa en **5 funciones** accesibles vía API REST (FastAPI) y consumidas por un frontend SPA (React + Vite + Tailwind):

1. **Observatorio Laboral Predictivo Territorial**
2. **Simulador de Empleabilidad**
3. **Sistema de Alerta Curricular Nacional**
4. **Match Predictivo Universidad–Mercado**
5. **Coach de Empleabilidad Multimodal**

---

## 2. Arquitectura general

```
┌──────────────────────────────────────────────────────────────────┐
│                       FRONTEND (SPA)                             │
│  React 18 + TypeScript + Vite + Tailwind + Recharts + Axios     │
│  Páginas: Dashboard, Observatorio, Simulador, Alerta, Match,    │
│           Coach                                                  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP /api/*
┌────────────────────────────▼─────────────────────────────────────┐
│                       BACKEND (API)                              │
│            FastAPI + Uvicorn (Python 3.11)                       │
│  Routers:                                                       │
│    /api/observatorio       → Función 1                           │
│    /api/simulador          → Función 2                           │
│    /api/alerta-curricular  → Función 3                           │
│    /api/match              → Función 4                           │
│    /api/coach              → Función 5 (LLM + RAG)               │
└────────────────────────────┬─────────────────────────────────────┘
                             │ cliente supabase-py
┌────────────────────────────▼─────────────────────────────────────┐
│                  SUPABASE (PostgreSQL + pgvector)                │
│  Tablas cargadas vía load_to_supabase.py desde CSVs procesados. │
└────────────────────────────┬─────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────┐
│                PIPELINE DE DATOS (ETL offline)                   │
│  data/raw/  →  etl_pipeline.py  →  data/processed/               │
│                              →  load_to_supabase.py              │
└──────────────────────────────────────────────────────────────────┘
                             │
                             ▼
            LLM opcional: Gemma 4 vía DeepInfra (función 5)
```

---

## 3. Stack tecnológico detallado

### 3.1 Frontend

| Tecnología | Versión | Uso |
|---|---|---|
| React | 18.3.1 | Framework UI por componentes |
| TypeScript | 5.5.4 | Tipado estático |
| Vite | 5.4.2 | Bundler / dev server (`http://localhost:5173`) |
| Tailwind CSS | 3.4.10 | Estilos utilitarios (paleta `alba-*`) |
| React Router DOM | 6.26 | Navegación entre páginas |
| Axios | 1.7.5 | Cliente HTTP hacia FastAPI |
| Recharts | 2.12.7 | Gráficos (barras, líneas, áreas) |
| react-simple-maps + d3-geo | 3.x | Mapas coropléticos de Colombia |
| lucide-react | 0.439 | Iconografía |

### 3.2 Backend

| Tecnología | Versión | Uso |
|---|---|---|
| FastAPI | 0.115 | Framework API REST + docs automáticas (`/docs`) |
| Uvicorn | 0.30 | Servidor ASGI |
| Pydantic | 2.9 | Validación de esquemas (request/response) |
| supabase-py | 2.7.4 | Cliente REST de Supabase |
| pandas | 2.2.2 | Limpieza y agregaciones |
| numpy | 1.26.4 | Operaciones numéricas |
| scikit-learn | 1.5.1 | Métricas y preprocesamiento ML |
| xgboost | 2.1.0 | Modelo predictivo de empleabilidad (fase 2) |
| prophet | 1.1.5 | Series de tiempo / proyección de demanda |
| sentence-transformers | 3.0.1 | Embeddings `all-MiniLM-L6-v2` (RAG del coach) |
| httpx | 0.27 | Llamadas async al LLM (DeepInfra) |
| python-dotenv | 1.0.1 | Carga de variables `.env` |

### 3.3 Datos y servicios externos

| Servicio / Dataset | Rol en el sistema |
|---|---|
| **Supabase** (PostgreSQL + pgvector) | Almacén central y vector store para RAG |
| **DANE — GEIH** | Ocupados / desempleados por departamento |
| **DANE — PILA** | Cotizantes formales por sector económico |
| **RUES (Cámaras de Comercio)** | Empresas activas, matrículas por sector y cámara |
| **SNIES (Mineducación)** | Programas, matriculados, instituciones |
| **SENA** | Cursos activos y áreas de desempeño |
| **ICFES — Saber Pro** | Puntajes por módulo (inglés, cuantitativo, etc.) |
| **DeepInfra** | Inferencia de **Gemma 4 (E4B / 31B IT)** para el coach |
| **Ofertas laborales curadas** | 30–50 vacantes en `data/raw/` para el coach |

### 3.4 Variables de entorno (`.env` raíz y `backend/.env`)

```env
SUPABASE_URL=https://vyerhngdkzyhbhucolek.supabase.co
SUPABASE_KEY=<service_role_key>
DEEPINFRA_API_KEY=keLkyno8SpPdoNhd6VCAXXivKEgbdkjs
```

---

## 4. Pipeline de datos (ETL)

Archivos clave en la raíz del repositorio:

- `etl_pipeline.py` — lee `data/raw/`, normaliza columnas, limpia nulos, deduplica y exporta a `data/processed/`.
- `load_to_supabase.py` — toma los CSV limpios y los inserta en las tablas de Supabase.
- `schema_supabase.sql` y `schema_fix.sql` — DDL de las tablas.
- `evaluar_datasets.py` — puntúa y prioriza datasets según utilidad para las 5 funciones.

**Flujo:**

```
data/raw/  ──►  etl_pipeline.py  ──►  data/processed/  ──►  load_to_supabase.py  ──►  Supabase
```

**Decisión de diseño:** los datos se descargan una sola vez y se procesan localmente; **no** se consulta la API Socrata en cada request. Esto reduce latencia y dependencias en tiempo de ejecución.

---

## 5. Las 5 funciones: endpoints, herramientas y propósito

Cada función se implementa como un **router** independiente bajo `backend/app/routers/`. A continuación se listan los endpoints reales expuestos por el backend y la intención de cada uno.

### 5.1 Función 1 — Observatorio Laboral Predictivo Territorial

**Router:** `app/routers/observatorio.py` → `prefix=/api/observatorio`
**Datasets involucrados:** GEIH (ocupados y desempleados), PILA, RUES.

| Método | Endpoint | Propósito | Resultado devuelto |
|---|---|---|---|
| GET | `/api/observatorio/departamentos` | Panorama nacional cruzado de ocupados vs. desocupados | Lista de departamentos con ocupados, no_ocupados y **tasa de desempleo calculada** |
| GET | `/api/observatorio/departamentos/{departamento}` | Ficha detallada de un departamento | Tasa de desempleo, ocupados y no ocupados del depto |
| GET | `/api/observatorio/sectores-formales?limit=50` | Top de sectores con más cotizantes (PILA) | Ranking de sectores económicos formales |
| GET | `/api/observatorio/sectores-emergentes?limit=20` | Sectores con más empresas activas (RUES) como **proxy de sectores emergentes** | Lista de sectores con `empresas_activas` |
| GET | `/api/observatorio/empresas-nuevas` | Series anuales de matrículas nuevas (RUES) | Series de tiempo por año y sector |
| GET | `/api/observatorio/camara/{camara}` | Desagregación por cámara de comercio y código CIIU | Sectores CIIU de una cámara específica |

**Propósito general:** ofrecer un **mapa territorial** de la empleabilidad y la dinámica empresarial para que un tomador de decisiones (alcaldía, cámara de comercio, ministerio) identifique dónde hay demanda insatisfecha.

---

### 5.2 Función 2 — Simulador de Empleabilidad

**Router:** `app/routers/simulador.py` → `prefix=/api/simulador`
**Datasets:** SNIES, PILA, RUES, SENA.

| Método | Endpoint | Propósito | Resultado |
|---|---|---|---|
| POST | `/api/simulador/proyectar` | Dado `{carrera, departamento, semestre, promedio}` calcula la empleabilidad esperada | Programas SNIES relacionados, total de matriculados, índice de saturación y `status_sector` ∈ {`saturado`, `equilibrado`, `demanda_insatisfecha`, `datos_insuficientes`} + cursos SENA sugeridos |
| GET | `/api/simulador/saturacion/{carrera}` | Alerta de saturación nacional de una carrera | Total de programas, matriculados agregados, distribución por departamento (top 10) y etiqueta `Saturación alta / Demanda moderada / Baja oferta` |

**Propósito general:** permitir que un **estudiante** simule su futuro laboral antes de elegir carrera o universidad, o que un **orientador** anticipe riesgos de saturación.

---

### 5.3 Función 3 — Sistema de Alerta Curricular Nacional

**Router:** `app/routers/alerta_curricular.py` → `prefix=/api/alerta-curricular`
**Datasets:** SNIES, SENA, Saber Pro.

| Método | Endpoint | Propósito | Resultado |
|---|---|---|---|
| GET | `/api/alerta-curricular/programas?departamento=` | Listar programas educativos con métricas de matriculados | Listado filtrable por departamento |
| GET | `/api/alerta-curricular/programa/{id}/diagnostico` | Diagnóstico curricular de un programa | Cruza Saber Pro (puntaje inglés/cuantitativo) + cursos SENA complementarios y genera **alertas automáticas** (saturación, inglés bajo, ausencia de oferta SENA) |
| POST | `/api/alerta-curricular/brecha` | Analiza la brecha entre oferta educativa y demanda formal (PILA) | `{oferta_educativa, demanda_laboral, cursos_sena_recomendados}` |

**Propósito general:** dar a **rectores y diseñadores curriculares** señales tempranas para actualizar planes de estudio (p. ej., reforzar inglés, abrir electivas en áreas emergentes detectadas vía RUES).

---

### 5.4 Función 4 — Match Predictivo Universidad–Mercado

**Router:** `app/routers/match.py` → `prefix=/api/match`
**Datasets:** SNIES, Saber Pro, PILA, SENA.

| Método | Endpoint | Propósito | Resultado |
|---|---|---|---|
| POST | `/api/match/perfil` | Dado `{universidad, programa, sector_objetivo, departamento}` mide el acoplamiento con el mercado | `match_score` (0–100), `status_match` ∈ {`alta_demanda`, `demanda_media`, `equilibrado`, `saturado`}, Saber Pro del programa, cursos SENA complementarios, sectores con mayor demanda |
| GET | `/api/match/skills-gap/{programa}` | Identifica brechas de habilidades usando Saber Pro | Lista priorizada de brechas (`Inglés`, `Razonamiento cuantitativo`, etc.) con `nivel_actual` vs `nivel_requerido` |

**Propósito general:** ofrecer a **universidades y oficinas de egresados** un indicador objetivo de qué tan alineado está su programa con la demanda, y un plan remedial concreto (cursos SENA).

---

### 5.5 Función 5 — Coach de Empleabilidad Multimodal

**Router:** `app/routers/coach.py` → `prefix=/api/coach`
**Componentes:** LLM Gemma 4 vía DeepInfra + RAG sobre Supabase + modo demo (sin LLM).

| Método | Endpoint | Propósito | Resultado |
|---|---|---|---|
| POST | `/api/coach/chat` | Agente conversacional que responde preguntas usando **datos reales** del sistema | Respuesta en lenguaje natural (Gemma 4) o respuesta estructurada (modo demo), con el `contexto_usado` extraído de Supabase |
| POST | `/api/coach/entrevista/iniciar` | Inicia entrevista simulada para una vacante | `session_id`, análisis básico de la vacante (cargo, habilidades, ubicación) y primera pregunta |
| POST | `/api/coach/entrevista/respuesta` | Evalúa respuesta del candidato | `score` 0–100, `feedback`, `puntos_fuertes`, `puntos_mejora` |
| POST | `/api/coach/cv/generar` | Sugiere CV personalizado para una vacante | `habilidades_destacar`, `experiencia_relevante`, `formato_recomendado` |

**Funciones auxiliares internas (módulo `coach.py`):**

- `_buscar_contexto(mensaje)` — RAG ligero: top sectores PILA + programas SNIES cuya descripción coincida con palabras del mensaje.
- `_analizar_vacante(vacante)` — detecta cargo, habilidades (`python`, `sql`, `excel`, `inglés`, `react`, …) y ciudad.
- `_respuesta_demo(...)` — fallback determinista cuando no hay `DEEPINFRA_API_KEY`.
- `_llamar_gemma4`, `_generar_pregunta_gemma4`, `_evaluar_gemma4`, `_generar_cv_gemma4` — wrappers async contra `https://api.deepinfra.com/v1/openai/chat/completions` con el modelo `google/gemma-4-31b-it`.

**Propósito general:** asistir al **candidato** con chat contextual, simulacros de entrevista y optimización de CV. En fase 2 se sumará un **coach offline** con Gemma 4 4B IT GGUF para zonas de baja conectividad.

---

## 6. Modelos analíticos previstos

| Modelo | Función donde se usa | Estado |
|---|---|---|
| **Índice de saturación** (matriculados SNIES vs cotizantes PILA) | Simulador, Alerta, Match | Implementado (proxy determinista) |
| **Tasa de desempleo departamental** (no_ocupados / PEA) | Observatorio | Implementado |
| **Match score** (ratio cotizantes/matriculados) | Match | Implementado (heurística) |
| **Prophet** para proyección de demanda | Observatorio (series) | Dependencias instaladas, pendiente de calibrar |
| **XGBoost** de empleabilidad por perfil | Simulador / Match | Dependencias instaladas, pendiente de entrenar |
| **Embeddings `all-MiniLM-L6-v2` + pgvector** | Coach (RAG semántico) | Dependencias instaladas, RAG en modo simple |

---

## 7. Decisiones de diseño relevantes

1. **Datos locales, no API en vivo** — los datasets del DANE se descargan una vez y se consultan desde Supabase.
2. **Sin scraping masivo** — se curan manualmente ~30–50 vacantes y 5–10 pensums/currículos para alimentar el coach.
3. **RUES como detector de sectores emergentes** — las nuevas matrículas mercantiles se usan como proxy de demanda futura.
4. **Coach online + offline** — Gemma 4 en DeepInfra para el modo online; en fase 2, Gemma 4 4B IT GGUF local para zonas sin buena conectividad.
5. **SECOP-II fuera del MVP** — su tamaño (~9 GB) no aporta directamente a las 5 funciones; se difiere.
6. **Idioma** — UI, endpoints y documentación en español; variables técnicas en inglés cuando es estándar (`loading`, `data`, `handleSubmit`).
7. **Paleta de marca** — prefijo `alba-` en `tailwind.config.js` (reemplaza al antiguo `enil-`).

---

## 8. Cómo ejecutar el proyecto

### Backend
```powershell
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Documentación interactiva: `http://127.0.0.1:8000/docs`

### Frontend
```powershell
cd frontend
npm run dev
```
App: `http://localhost:5173` (Vite redirige `/api/*` al backend en `:8000`).

---

## 9. Próximos pasos

- [ ] Activar saldo en DeepInfra para desactivar el modo demo del coach.
- [ ] Terminar `etl_pipeline.py` y verificar la carpeta `data/processed/`.
- [ ] Entrenar y servir el modelo XGBoost de empleabilidad.
- [ ] Migrar el RAG del coach a búsqueda semántica con `pgvector` + `sentence-transformers`.
- [ ] Construir el coach offline (`offline_coach/`) con Gemma 4 4B IT GGUF.
- [ ] Empaquetar despliegue en Kubernetes sobre Namecheap.
- [ ] Limpiar duplicados en Supabase (departamentos, etc.).

---

## 10. Resumen ejecutivo

ALBACOLOMBIA cierra la brecha entre **lo que Colombia enseña** y **lo que el país necesita** cruzando cinco datasets abiertos con analítica y un coach con IA. La arquitectura — **React + FastAPI + Supabase + Gemma 4** — prioriza simplicidad operativa (datos locales, sin scraping) y reproducibilidad, y entrega cinco funciones concretas con valor medible para estudiantes, universidades, entidades territoriales y candidatos.
