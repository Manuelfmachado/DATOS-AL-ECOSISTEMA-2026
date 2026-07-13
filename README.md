# ALBA — Analítica Laboral Basada en IA

Plataforma Nacional de Inteligencia Laboral para Colombia, construida para el **Reto 5: Economía y Empleo** del concurso **Datos al Ecosistema 2026**.

> **ALBA** conecta la oferta educativa (SNIES, SENA) con la demanda real del mercado laboral (GEIH, PILA, RUES) usando inteligencia artificial, series temporales y datos abiertos de Colombia.

## Los 5 módulos de ALBA

### 1. 📊 Observatorio Inteligente
¿Qué está pasando en el mercado laboral colombiano?

- Mapa interactivo de Colombia con 33 departamentos.
- Empleo, desempleo e ingresos por departamento (GEIH).
- Sectores formales más grandes (PILA).
- Sectores emergentes según creación de empresas (RUES).
- Comparaciones regionales y dashboard ejecutivo.

### 2. 🔮 Simulador IA
¿Qué podría pasar en el futuro?

- Predicción de empleo y desempleo con Chronos-Bolt Small.
- Demanda laboral futura y crecimiento de sectores.
- Recomendaciones automáticas para entidades públicas y política de formación.

### 3. 🎓 Match Inteligente
¿Dónde encaja mi perfil, carrera, empresa o municipio?

- **Persona ↔ Mercado:** qué tan empleable es tu perfil.
- **Universidad ↔ Mercado:** carreras saturadas o emergentes (antes Alerta Curricular).
- **Empresa ↔ Talento:** déficit de perfiles en una región.
- **Municipio ↔ Sectores:** sectores con mayor potencial local.
- **Reskilling:** ruta de aprendizaje para cerrar brechas de habilidades.

### 4. 🚀 Emprende IA
¿Qué negocio tiene mayor potencial en mi municipio?

- Oportunidades por municipio basadas en datos reales.
- Sectores emergentes, competencia y demanda laboral.
- Índice de Oportunidad 0-100 (no promesa de éxito, sino potencial basado en datos).
- Guía de formalización y convocatorias (Fondo Emprender, SENA, iNNpulsa, Cámaras).

### 5. 🎤 Coach IA
¿Cómo me preparo para conseguir el empleo?

- Mock Interviews por voz (Whisper + Edge-TTS) con fallback a texto.
- Evaluación, retroalimentación y puntuación de respuestas.
- Sugerencias de CV personalizadas por vacante.

## Flujo de uso

```
Observo el mercado  →  Anticipo cambios  →  Encuentro mi lugar  →  Decido trabajar o emprender  →  Me preparo
    (Observatorio)      (Simulador IA)         (Match)                (Emprende IA)                 (Coach)
```

## Tecnologías

- **Frontend:** React 18 + TypeScript + Vite + Tailwind CSS + Playfair Display + Inter
- **Backend:** FastAPI + Python
- **Datos:** Supabase (PostgreSQL + pgvector)
- **LLM:** Gemma 4 (DeepInfra)
- **Forecasting:** Chronos-Bolt Small
- **ML:** XGBoost, Prophet, scikit-learn
- **Embeddings:** sentence-transformers
- **Mapas:** react-simple-maps + GeoJSON real de Colombia
- **Voz:** faster-whisper + Edge-TTS

## Datos utilizados

| Fuente | Uso |
|---|---|
| GEIH (DANE) | Empleo, ingresos, desempleo, informalidad |
| PILA (MinTrabajo) | Sectores formales, cotizantes |
| SNIES (MinEducación) | Programas de educación superior |
| SENA | Cursos técnicos y tecnológicos |
| RUES (Confecámaras) | Nuevas empresas, sectores emergentes, competencia |
| Ofertas laborales curadas | Entrenamiento del coach y detección de skills |

## Instalación y uso

### 1. Clonar y entrar al directorio

```bash
cd "C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026"
```

### 2. Backend

```bash
cd backend
# Crear entorno virtual recomendado
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

La app estará en `http://localhost:5173`.

## Estado del proyecto

- ✅ Frontend y backend funcionando localmente.
- ✅ Datos cargados en Supabase (~97.000 filas).
- ✅ 5 endpoints principales probados.
- ✅ Mapa real de Colombia con 33 departamentos.
- 🔄 Módulo Emprende IA en desarrollo.
- 🔄 Match Inteligente en reorganización.
- 🔄 Coach con voz en planificación.
- 🔄 Modelo predictivo Chronos-Bolt en desarrollo.

## Licencia

Proyecto desarrollado para fines de concurso. Datos provenientes de fuentes públicas colombianas.

---

**ALBA** = **A**nalítica **L**aboral **B**asada en **IA**
