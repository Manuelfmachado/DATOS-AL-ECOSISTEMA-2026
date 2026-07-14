# Guía de validación técnica

Este documento resume cómo un evaluador puede verificar que ALBA cumple los requisitos técnicos del **Concurso Datos al Ecosistema 2026 — Reto 5: Economía y Empleo**.

## 1. Cumplimiento de datos abiertos

| Requisito | Evidencia | Estado |
|-----------|-----------|--------|
| Mínimo un dataset de datos.gov.co | 11 fuentes colombianas, la mayoría descargadas directamente de datos.gov.co y microdatos.dane.gov.co | ✅ |
| Formatos abiertos | Todos los datasets en CSV, JSON o API REST | ✅ |
| Fuentes documentadas | [`docs/fuentes_datos.md`](fuentes_datos.md) con URLs oficiales | ✅ |
| Volumen | 44 tablas cargadas en Supabase, ~744.000 filas | ✅ |

## 2. Componente de inteligencia artificial

| Componente | Modelo | Archivo clave |
|------------|--------|---------------|
| LLM primario | Gemini 2.5 Flash-Lite | `backend/app/services/llm.py`, `backend/app/services/llm_gemini.py` |
| LLM conversacional | Gemini Live | `backend/app/routers/coach.py` |
| Forecasting | Chronos T5 Small | `backend/app/routers/prediccion.py`, `prediccion_chronos.py` |
| Embeddings | Gemma Embeddings 300 (768d) | `backend/app/services/embeddings.py`, `pdf_to_rag.py` |
| Matching híbrido | ESCO + OLE + LLM | `backend/app/routers/match.py` |

## 3. Verificación de endpoints principales

Con el backend corriendo en `http://127.0.0.1:8000`:

```bash
# Documentación interactiva
GET http://127.0.0.1:8000/docs

# Resumen nacional del Observatorio
GET /api/observatorio/resumen-nacional

# Tendencias de empleo
GET /api/observatorio/tendencia-empleo

# Predicciones
GET /api/prediccion/resumen
GET /api/prediccion/sectores
GET /api/prediccion/profesiones

# Matching CV vs vacante
POST /api/match/cv-vacante
# body: { cv_text, vacante_text }

# Emprende IA
POST /api/emprende/evaluar-idea
# body: { municipio, sector, inversion }

# Coach IA
POST /api/coach/mejorar-cv
# body: { cv_text }
```

## 4. Verificación de la base de datos

Desde el SQL Editor de Supabase:

```sql
-- Número de tablas cargadas
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public';

-- Filas totales (aproximado, depende del motor)
SELECT schemaname, relname, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Función de búsqueda vectorial para RAG
SELECT * FROM pg_proc WHERE proname = 'buscar_embeddings_vector';
```

## 5. Verificación del frontend

```bash
cd frontend
npm run build
```

El build debe terminar con `✓ built in ...` y sin errores de TypeScript.

## 6. Verificación de la presentación

```bash
# Abrir presentación editable
recursos/presentacion.pptx

# Abrir PDF para compartir
recursos/presentacion.pdf

# Ver portada
recursos/portada.png
```

## 7. Checklist de entrega

- [x] Repositorio organizado con `README.md`, `LICENSE`, `Changelog.md`.
- [x] Documentación técnica completa en `docs/`.
- [x] Código fuente funcional (`backend/` y `frontend/`).
- [x] Datos procesados en `data/processed/` (o instrucciones para descargarlos).
- [x] Scripts ETL y carga en `src/`.
- [x] Schemas SQL en `sql/`.
- [x] Presentación en `recursos/presentacion.pptx` y `.pdf`.
- [x] Portada en `recursos/portada.png`.
- [x] Demo funcional o instrucciones claras para ejecutar localmente.

## 8. Limitaciones conocidas

1. Series históricas de GEIH solo 2022-2026; el forecasting usa World Bank para ampliar el horizonte.
2. SPE/APE solo tiene ~566 registros nacionales; no hay demanda municipal.
3. OLE ingresos de egresados hasta 2022.
4. No se incluye SECOP por tamaño (~9 GB) en el MVP.

Ver detalles en [`docs/conclusiones.md`](conclusiones.md).

## 9. Contacto

- **Líder / Desarrollador:** Manuel Francisco Machado
- **Repositorio:** GitHub *(por configurar remote)*
