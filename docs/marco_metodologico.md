# Marco metodológico

ALBA sigue el ciclo de vida **CRISP-ML** (Cross-Industry Standard Process for Machine Learning), adaptado al contexto de datos abiertos colombianos.

## Fases del proyecto

### 1. Comprensión del problema (Business Understanding)

**Objetivo:** Conectar la oferta educativa y la demanda laboral en Colombia usando datos abiertos e IA.

**Preguntas clave:**
- ¿Qué está pasando en el mercado laboral?
- ¿Qué podría pasar en el futuro?
- ¿Dónde encaja mi perfil?
- ¿Qué negocio tiene potencial?
- ¿Cómo me preparo para conseguir empleo?

**Resultado:** 5 módulos definidos (Observatorio, Predicción, Match, Emprende, Coach).

### 2. Comprensión de los datos (Data Understanding)

**Fuentes identificadas:**

| Fuente | Tipo | Volumen |
|--------|------|---------|
| DANE GEIH | Encuesta de hogares | ~120K registros |
| DANE EMICRON | Censo de micronegocios | ~109 registros |
| MinTrabajo PILA | Registro administrativo | ~652 registros |
| Confecámaras RUES | Registro empresarial | ~26K registros |
| MEN SNIES | Registro educativo | ~85K registros |
| MEN OLE/ETDH | Observatorio laboral educación | ~37K registros |
| SENA SPE/APE | Servicio público de empleo | ~17K registros |
| ESCO | Taxonomía europea | ~155K registros |
| O*NET | Taxonomía EE.UU. | ~12K registros |
| DNP MDM | Desempeño municipal | ~22K registros |
| World Bank | Indicadores macro | 128 registros |

**Análisis exploratorio:** Se verificó cobertura temporal (2010-2026), geográfica (33 departamentos) y sectorial (89 ramas CIIU).

### 3. Preparación de los datos (Data Preparation)

**Pipeline ETL** (`etl_pipeline.py`):

```
data/raw/ (CSVs originales)
    ↓ Limpieza (nulos, tipos, duplicados)
    ↓ Normalización (nombres de departamentos, códigos CIIU)
    ↓ Transformación (agregaciones, cruzes, cálculos derivados)
data/processed/ (CSVs limpios)
    ↓ Carga a Supabase
Supabase PostgreSQL (44 tablas)
```

**Decisiones clave:**
- Normalización de nombres de departamentos (Bogotá D.C. → BOGOTA, etc.)
- Agrupación de 89 ramas CIIU en 10 macrosectores
- Detección de años completos (12 meses) vs parciales para proyecciones
- Embeddings a 768 dimensiones (sin truncar MRL)

### 4. Modelado (Modeling)

#### 4.1 Forecasting con Chronos T5 Small
- **Modelo:** Chronos T5 Small (Transformer para series temporales)
- **Método:** Zero-shot forecasting (sin fine-tuning)
- **Datos:** World Bank Colombia (2010-2025) + GEIH mensual (2022-2026)
- **Horizontes:** 5 y 10 años
- **Variables:** Participación sectorial del empleo, desempleo, informalidad, PIB por empleado
- **Ejecución:** Batch (`prediccion_chronos.py`) → JSON + Supabase

#### 4.2 LLM para análisis cualitativo
- **Modelo primario:** Gemini 2.5 Flash-Lite
- **Modelo fallback:** Gemma 4 E4B (DeepInfra)
- **Uso:** Match (CV vs vacante), Coach (CV + entrevista), Emprende (evaluar ideas)
- **Prompt engineering:** Sistema con instrucciones específicas + datos de contexto
- **Post-procesamiento:** Normalización de pesos de brechas (suman 100 - score)

#### 4.3 Matching híbrido (datos reales + LLM)
- **Paso 1:** Extraer ocupación de la vacante → buscar en ESCO
- **Paso 2:** Intersección de habilidades reales (ESCO) vs detectadas en CV
- **Paso 3:** Buscar salarios reales de egresados en OLE-MEN
- **Paso 4:** LLM genera interpretación textual
- **Score:** 50% intersección de habilidades + 50% análisis del LLM

#### 4.4 RAG (Retrieval-Augmented Generation)
- **Embeddings:** Gemma 300 (768d) vía DeepInfra
- **Vector store:** Supabase pgvector
- **Búsqueda:** Similitud coseno vía función SQL `buscar_embeddings_vector`
- **Uso:** Coach IA (guías de formalización, normativas laborales)

### 5. Evaluación (Evaluation)

**Métricas de calidad de datos:**
- 44 tablas cargadas en Supabase sin errores
- 744K filas validadas
- Normalización de nombres departamentales verificada
- Detección y exclusión de años parciales en proyecciones

**Validación de predicciones:**
- Chronos T5: comparación con valores históricos conocidos
- Proyecciones conservadoras (cap 0.5%-4% anual de crecimiento de empleo)
- Salarios reales del DANE GEIH (406 ocupaciones) como ground truth

**Validación del LLM:**
- Normalización de pesos de brechas (suma = 100 - score)
- Recursos clasificados por tipo (SENA, online, certificación, libre)
- Fallback automático de Gemini a Gemma 4

### 6. Despliegue (Deployment)

| Componente | Plataforma | Estado |
|------------|-----------|--------|
| Frontend | Vercel | Configurado |
| Backend | Railway | Configurado |
| Base de datos | Supabase | Activo (44 tablas) |
| Cron (Chronos) | Railway cron | Configurado |
| Dominio | Namecheap | Por configurar |

**Infraestructura como código:**
- `schema*.sql` para DDL de Supabase
- `requirements.txt` para dependencias Python
- `package.json` para dependencias Node.js
- Variables de entorno en `.env`