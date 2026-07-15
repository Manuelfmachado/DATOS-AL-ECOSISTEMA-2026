"""
Router del Coach de Empleabilidad Multimodal (Función #5).
Versión simplificada y poderosa:
  1. Mejorar CV (texto o archivo PDF/Word) con LLM.
  2. Practicar entrevista con chatbot LLM.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from app.db.supabase import supabase
from app.services.embeddings import get_embedding
from app.services.knowledge_graph import get_knowledge_graph
from app.services.llm import mejorar_cv as deepinfra_mejorar_cv, entrevista_chat as deepinfra_entrevista_chat
from app.services.llm_gemini import (
    mejorar_cv as gemini_mejorar_cv,
    entrevista_chat as gemini_entrevista_chat,
    is_gemini_available,
    call_gemini_json,
)
import os
import httpx
import json
import math
import fitz  # PyMuPDF
import docx

router = APIRouter(prefix="/api/coach", tags=["coach"])

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"


class ChatRequest(BaseModel):
    mensaje: str
    contexto: dict | None = None


class EntrevistaRequest(BaseModel):
    vacante: str
    sector: str | None = None


class RespuestaRequest(BaseModel):
    session_id: str
    pregunta: str
    respuesta: str


@router.post("/chat")
async def chat_con_agente(req: ChatRequest):
    """Agente conversacional que responde usando datos del sistema."""
    try:
        # Buscar datos relevantes en Supabase según el mensaje
        contexto_datos = await _buscar_contexto(req.mensaje)

        # Si hay API key de DeepInfra, usar Gemma 4
        if DEEPINFRA_API_KEY:
            try:
                respuesta = await _llamar_gemma4(req.mensaje, contexto_datos)
            except Exception as e:
                print(f"[Coach] DeepInfra falló: {e}. Usando modo demo.")
                respuesta = _respuesta_demo(req.mensaje, contexto_datos)
        else:
            # Respuesta estructurada sin LLM (modo demo)
            respuesta = _respuesta_demo(req.mensaje, contexto_datos)

        return {"respuesta": respuesta, "contexto_usado": contexto_datos}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entrevista/iniciar")
async def iniciar_entrevista(req: EntrevistaRequest):
    """Inicia una entrevista simulada basada en una vacante."""
    try:
        # Analizar la vacante
        vacante_analizada = _analizar_vacante(req.vacante)

        # Generar primera pregunta
        if DEEPINFRA_API_KEY:
            try:
                pregunta = await _generar_pregunta_gemma4(req.vacante, vacante_analizada)
            except Exception as e:
                print(f"[Coach] DeepInfra falló: {e}. Usando pregunta demo.")
                pregunta = f"Cuéntame sobre tu experiencia relacionada con: {vacante_analizada['cargo_detectado']}"
        else:
            pregunta = f"Cuéntame sobre tu experiencia relacionada con: {vacante_analizada['cargo_detectado']}"

        return {
            "session_id": f"ent_{hash(req.vacante) % 100000}",
            "vacante_analizada": vacante_analizada,
            "primera_pregunta": pregunta,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entrevista/respuesta")
async def evaluar_respuesta(req: RespuestaRequest):
    """Evalúa la respuesta del candidato en la entrevista simulada."""
    try:
        if DEEPINFRA_API_KEY:
            try:
                evaluacion = await _evaluar_gemma4(req.pregunta, req.respuesta)
            except Exception as e:
                print(f"[Coach] DeepInfra falló: {e}. Usando evaluación demo.")
                score = min(100, max(20, len(req.respuesta) // 5))
                evaluacion = {
                    "score": score,
                    "feedback": f"Respuesta de {len(req.respuesta)} caracteres.",
                    "puntos_fuertes": [],
                    "puntos_mejora": ["Agregar ejemplos específicos"],
                }
        else:
            # Evaluación demo
            score = min(100, max(20, len(req.respuesta) // 5))
            evaluacion = {
                "score": score,
                "feedback": f"Respuesta de {len(req.respuesta)} caracteres. " + ("Buena extensión." if len(req.respuesta) > 100 else "Podría ser más detallada."),
                "puntos_fuertes": ["Claridad"] if score > 60 else [],
                "puntos_mejora": ["Agregar ejemplos específicos"] if score < 70 else [],
            }

        return {"evaluacion": evaluacion}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CVRequest(BaseModel):
    cv: str
    vacante: str = ""


class EntrevistaChatRequest(BaseModel):
    mensaje: str
    modo: str = "preguntar"  # "preguntar" | "practicar"
    vacante: str = ""
    historial: str = ""


@router.post("/mejorar-cv")
async def mejorar_cv_endpoint(req: CVRequest):
    """Mejora un CV pegado como texto usando LLM (Gemini con fallback a DeepInfra)."""
    try:
        if is_gemini_available():
            return gemini_mejorar_cv(req.cv, req.vacante)
        return deepinfra_mejorar_cv(req.cv, req.vacante)
    except Exception as e:
        print(f"[Coach] Gemini falló ({e}), usando DeepInfra fallback.")
        try:
            return deepinfra_mejorar_cv(req.cv, req.vacante)
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


@router.post("/mejorar-cv-archivo")
async def mejorar_cv_archivo(file: UploadFile = File(...), vacante: str = ""):
    """Recibe un archivo PDF o Word, extrae el texto y mejora el CV con LLM."""
    try:
        contenido = await file.read()
        extension = (file.filename or "").lower()

        if extension.endswith(".pdf"):
            texto = _extraer_texto_pdf(contenido)
        elif extension.endswith((".docx", ".doc")):
            texto = _extraer_texto_word(contenido)
        else:
            raise HTTPException(status_code=400, detail="Solo se aceptan archivos PDF o Word (.docx)")

        if not texto.strip():
            raise HTTPException(status_code=400, detail="No se pudo extraer texto del archivo")

        try:
            resultado = gemini_mejorar_cv(texto, vacante) if is_gemini_available() else deepinfra_mejorar_cv(texto, vacante)
        except Exception as e:
            print(f"[Coach] Gemini falló ({e}), usando DeepInfra fallback.")
            resultado = deepinfra_mejorar_cv(texto, vacante)
        return {**resultado, "archivo": file.filename, "texto_extraido": texto[:500]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entrevista")
async def entrevista_endpoint(req: EntrevistaChatRequest):
    """Chatbot para practicar entrevistas o preguntar sobre procesos de selección."""
    try:
        if is_gemini_available():
            respuesta = gemini_entrevista_chat(req.mensaje, req.modo, req.historial, req.vacante)
        else:
            respuesta = deepinfra_entrevista_chat(req.mensaje, req.modo, req.historial, req.vacante)
        return {"respuesta": respuesta}
    except Exception as e:
        print(f"[Coach] Gemini falló ({e}), usando DeepInfra fallback.")
        try:
            respuesta = deepinfra_entrevista_chat(req.mensaje, req.modo, req.historial, req.vacante)
            return {"respuesta": respuesta}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


# ============================================================================
# Entrevista estructurada (Reclutador real): CV + vacante -> 10 preguntas -> feedback
# ============================================================================

import uuid

_sesiones_entrevista: dict[str, dict] = {}


class EntrevistaRealistaIniciarReq(BaseModel):
    cv: str
    vacante: str


class EntrevistaRealistaAvanzarReq(BaseModel):
    session_id: str
    respuesta: str


@router.post("/entrevista-realista/iniciar")
async def iniciar_entrevista_realista(req: EntrevistaRealistaIniciarReq):
    """Analiza el CV y la vacante, genera 10 preguntas de entrevista y devuelve
    el saludo inicial + la primera pregunta. El flujo es: saludo -> 10 preguntas
    una a una -> feedback oral final."""
    try:
        system = (
            "Eres ALBA, una reclutadora experta de RRHH en Colombia. Vas a conducir "
            "una entrevista estructurada de EXACTAMENTE 10 preguntas basadas en el CV "
            "del candidato y la vacante objetivo.\n\n"
            "Genera 10 preguntas relevantes y específicas que un reclutador real haría "
            "para evaluar si el candidato encaja en la vacante. Usa el CV para personalizar "
            "las preguntas (pedir detalles de experiencias, profundizar en habilidades, etc).\n\n"
            "Las preguntas deben seguir una progresión lógica:\n"
            "1-2: Presentación y experiencia general\n"
            "3-5: Experiencia técnica específica relacionada con la vacante\n"
            "6-7: Habilidades blandas, trabajo en equipo, liderazgo\n"
            "8-9: Casos prácticos o hipotéticos del rol\n"
            "10: Motivación y expectativas\n\n"
            "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
            "{\n"
            '  "saludo": string,\n'
            '  "preguntas": [string, string, ...]  (exactamente 10)\n'
            "}\n"
            "El saludo debe ser cálido, presentar la vacante brevemente y mencionar que la "
            "entrevista tendrá 10 preguntas. En español neutro colombiano."
        )
        user = f"CV DEL CANDIDATO:\n{req.cv}\n\nVACANTE OBJETIVO:\n{req.vacante}"

        resultado = call_gemini_json(system, user, temperature=0.5, max_tokens=3000)

        saludo = resultado.get("saludo", "")
        preguntas = resultado.get("preguntas", [])

        if len(preguntas) < 10:
            while len(preguntas) < 10:
                preguntas.append(f"Cuéntame más sobre tu experiencia relacionada con la vacante.")
        preguntas = preguntas[:10]

        session_id = str(uuid.uuid4())[:12]
        _sesiones_entrevista[session_id] = {
            "cv": req.cv,
            "vacante": req.vacante,
            "preguntas": preguntas,
            "indice_actual": 0,
            "respuestas": [],
            "estado": "en_curso",
        }

        return {
            "session_id": session_id,
            "saludo": saludo,
            "pregunta_actual": preguntas[0],
            "numero_pregunta": 1,
            "total_preguntas": 10,
            "estado": "en_curso",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/entrevista-realista/avanzar")
async def avanzar_entrevista_realista(req: EntrevistaRealistaAvanzarReq):
    """Recibe la respuesta del candidato a la pregunta actual y devuelve la siguiente
    pregunta, o el feedback final si era la última. Guarda cada respuesta para el
    feedback final."""
    try:
        sesion = _sesiones_entrevista.get(req.session_id)
        if not sesion:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o expirada")
        if sesion["estado"] != "en_curso":
            raise HTTPException(status_code=400, detail="La entrevista ya terminó")

        idx = sesion["indice_actual"]
        sesion["respuestas"].append({
            "pregunta": sesion["preguntas"][idx],
            "respuesta": req.respuesta,
        })
        sesion["indice_actual"] += 1
        siguiente_idx = sesion["indice_actual"]

        if siguiente_idx >= 10:
            sesion["estado"] = "finalizada"
            feedback = await _generar_feedback_final(sesion)
            return {
                "estado": "finalizada",
                "feedback": feedback,
                "numero_pregunta": 10,
                "total_preguntas": 10,
            }

        return {
            "estado": "en_curso",
            "pregunta_actual": sesion["preguntas"][siguiente_idx],
            "numero_pregunta": siguiente_idx + 1,
            "total_preguntas": 10,
            "breve_reconocimiento": _reconocimiento_aleatorio(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def _generar_feedback_final(sesion: dict) -> dict:
    """Genera el feedback oral final usando el LLM con todas las preguntas y respuestas."""
    system = (
        "Eres ALBA, una reclutadora experta en Colombia. La entrevista ha terminado "
        "(10 preguntas respondidas). Genera un feedback estructurado y realista.\n\n"
        "Sé honesta, específica y útil. Basa el puntaje en la calidad de las respuestas, "
        "la alineación del CV con la vacante y la comunicación general.\n\n"
        "Devuelve ÚNICAMENTE un JSON válido con esta estructura exacta:\n"
        "{\n"
        '  "puntaje_general": number (0-100),\n'
        '  "fortalezas": [string],\n'
        '  "areas_mejora": [string],\n'
        '  "recomendacion": string (pasaría o no a siguiente fase y por qué),\n'
        '  "sugerencia_practica": string\n'
        "}\n"
    )
    texto_preguntas = ""
    for i, par in enumerate(sesion["respuestas"], 1):
        texto_preguntas += f"\n--- Pregunta {i} ---\nQ: {par['pregunta']}\nR: {par['respuesta']}\n"

    user = (
        f"CV DEL CANDIDATO:\n{sesion['cv']}\n\n"
        f"VACANTE OBJETIVO:\n{sesion['vacante']}\n\n"
        f"RESPUESTAS DE LA ENTREVISTA:{texto_preguntas}"
    )

    try:
        resultado = call_gemini_json(system, user, temperature=0.4, max_tokens=2500)
        if "error" in resultado:
            raise Exception(resultado.get("raw", ""))
        return resultado
    except Exception as e:
        print(f"[Coach] Feedback final LLM falló: {e}")
        return {
            "puntaje_general": 70,
            "fortalezas": ["Disposición para responder todas las preguntas"],
            "areas_mejora": ["Profundizar más en experiencias específicas"],
            "recomendacion": "Pasaría a una segunda entrevista para evaluar aspectos técnicos.",
            "sugerencia_practica": "Prepara ejemplos concretos usando la técnica STAR (Situación, Tarea, Acción, Resultado).",
        }


def _reconocimiento_aleatorio() -> str:
    import random
    opciones = ["Gracias.", "Entendido.", "Muy bien.", "Claro.", "Perfecto.", "Bien, sigamos."]
    return random.choice(opciones)


@router.post("/cv/generar")
async def generar_cv_personalizado(req: CVRequest):
    """Genera sugerencias de CV personalizadas para una vacante."""
    try:
        vacante_analizada = _analizar_vacante(req.vacante)

        if DEEPINFRA_API_KEY:
            try:
                sugerencia = await _generar_cv_gemma4(req.perfil or req.cv, vacante_analizada)
            except Exception as e:
                print(f"[Coach] DeepInfra falló: {e}. Usando sugerencia demo.")
                sugerencia = {
                    "habilidades_destacar": vacante_analizada["habilidades_detectadas"][:5],
                    "experiencia_relevante": "Enfocar en experiencias relacionadas con " + vacante_analizada["cargo_detectado"],
                    "formato_recomendado": "Cronológico inverso, máximo 2 páginas",
                }
        else:
            sugerencia = {
                "habilidades_destacar": vacante_analizada["habilidades_detectadas"][:5],
                "experiencia_relevante": "Enfocar en experiencias relacionadas con " + vacante_analizada["cargo_detectado"],
                "formato_recomendado": "Cronológico inverso, máximo 2 páginas",
            }

        return {"cv_sugerencia": sugerencia, "vacante_analizada": vacante_analizada}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Funciones auxiliares de extracción de archivos
# ============================================================================

def _extraer_texto_pdf(contenido: bytes) -> str:
    """Extrae texto de un PDF usando PyMuPDF."""
    doc = fitz.open(stream=contenido, filetype="pdf")
    texto = "\n".join(page.get_text() for page in doc)
    doc.close()
    return texto


def _extraer_texto_word(contenido: bytes) -> str:
    """Extrae texto de un documento Word usando python-docx."""
    import io
    document = docx.Document(io.BytesIO(contenido))
    texto = "\n".join(parrafo.text for parrafo in document.paragraphs)
    return texto


# ============================================================================
# Funciones auxiliares
# ============================================================================

def _cosine_similarity(a: list, b: list) -> float:
    """Calcula similitud coseno entre dos vectores."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


async def _buscar_embeddings_local(
    mensaje: str, tabla: str, top_k: int = 5, categoria: str | None = None
) -> list:
    """Fallback local: descarga embeddings y calcula similitud coseno en Python.
    Util hasta que se aplique schema_rag_rpc.sql y schema_fix_embeddings_dim.sql."""
    try:
        query_embedding = await get_embedding(mensaje)

        # Construir query
        query = supabase.table(tabla).select("id, texto, metadata, embedding")
        if categoria:
            # PostgREST no permite filtrar JSONB anidado directamente por metadata->>category
            # asi que traemos todo y filtramos localmente
            pass

        response = query.limit(1000).execute()
        rows = response.data or []

        # Filtrar por categoria si se especifica
        if categoria:
            rows = [r for r in rows if r.get("metadata", {}).get("category") == categoria]

        # Calcular similitud
        scored = []
        for r in rows:
            emb = r.get("embedding")
            if not emb:
                continue
            # PostgREST devuelve el vector como string JSON; parsearlo si es necesario
            if isinstance(emb, str):
                try:
                    emb = json.loads(emb)
                except Exception:
                    continue
            if not isinstance(emb, list) or len(emb) != len(query_embedding):
                continue
            sim = _cosine_similarity(query_embedding, emb)
            scored.append({**r, "similitud": sim})

        scored.sort(key=lambda x: x["similitud"], reverse=True)
        return [
            {
                "texto": r["texto"][:500],
                "fuente": r["metadata"].get("source_name"),
                "categoria": r["metadata"].get("category"),
                "similitud": round(r["similitud"], 4),
            }
            for r in scored[:top_k]
        ]
    except Exception as e2:
        print(f"[Coach] Fallback local tambien falló: {e2}")
        return []


async def _buscar_contexto(mensaje: str) -> dict:
    """Busca datos relevantes en Supabase según el mensaje del usuario.
    Usa RAG vectorial sobre embeddings_guias con Gemma 300 (768d)."""
    contexto = {}

    # 1. Busqueda vectorial en guias/documentos (RAG)
    # Intentar RPC primero; si falla o devuelve vacio, usar fallback local
    rpc_resultados = []
    try:
        query_embedding = await get_embedding(mensaje)
        # NOTA: categoria_filter se envia como string vacio en vez de null porque
        # PostgREST serializa null de forma que la condicion SQL no evalua correctamente.
        resultados = supabase.rpc(
            "buscar_embeddings_vector",
            {
                "consulta_embedding": query_embedding,
                "nombre_tabla": "embeddings_guias",
                "limite_resultados": 5,
                "categoria_filter": "",
            },
        ).execute()
        rpc_resultados = resultados.data or []
    except Exception as e:
        print(f"[Coach] RAG RPC falló: {e}")

    if rpc_resultados:
        contexto["guias_relacionadas"] = [
            {
                "texto": r["texto"][:500],
                "fuente": r["metadata"].get("source_name"),
                "categoria": r["metadata"].get("category"),
                "similitud": round(r["similitud"], 4),
            }
            for r in rpc_resultados
        ]
    else:
        # Fallback local: descarga embeddings y calcula similitud coseno en Python
        contexto["guias_relacionadas"] = await _buscar_embeddings_local(
            mensaje, "embeddings_guias", 5
        )

    # 2. Datos estructurados: sectores con mas empleo formal
    try:
        sectores = (
            supabase.table("pila_resumen_sector")
            .select("*")
            .order("total_cotizantes", desc=True)
            .limit(5)
            .execute()
        )
        contexto["top_sectores"] = [
            {"sector": s["actividadeconomicadesc"], "cotizantes": s["total_cotizantes"]}
            for s in sectores.data
        ]
    except Exception:
        contexto["top_sectores"] = []

    # 3. Datos estructurados: programas relacionados (busqueda por palabra clave)
    palabras = mensaje.lower().split()
    for palabra in palabras:
        if len(palabra) > 4:
            try:
                snies = (
                    supabase.table("snies_programas_matriculados")
                    .select("*")
                    .ilike("programa", f"%{palabra}%")
                    .limit(3)
                    .execute()
                )
                if snies.data:
                    contexto["programas_relacionados"] = [
                        {"programa": p["programa"], "matriculados": p["matriculados"]}
                        for p in snies.data
                    ]
                    break
            except Exception:
                pass

    # 4. Knowledge Graph: ocupaciones similares en O*NET/ESCO
    try:
        kg = get_knowledge_graph()
        ocupaciones_similares = kg.search_occupations(mensaje, top_k=3)
        contexto["ocupaciones_similares"] = ocupaciones_similares
    except Exception as e:
        print(f"[Coach] Knowledge graph falló: {e}")
        contexto["ocupaciones_similares"] = []

    return contexto


def _analizar_vacante(vacante: str) -> dict:
    """Análisis de vacante usando Knowledge Graph (O*NET/ESCO) + reglas locales."""
    vacante_lower = vacante.lower()

    # Detectar cargo con Knowledge Graph
    try:
        kg = get_knowledge_graph()
        ocupaciones_similares = kg.search_occupations(vacante, top_k=3)
    except Exception:
        ocupaciones_similares = []

    if ocupaciones_similares:
        cargo_detectado = ocupaciones_similares[0]["title"]
        ocupacion_principal = ocupaciones_similares[0]
    else:
        cargos = ["analista", "ingeniero", "contador", "abogado", "asistente", "coordinador", "gerente", "developer", "designer", "vendedor"]
        cargo_detectado = next((c for c in cargos if c in vacante_lower), "cargo no identificado").capitalize()
        ocupacion_principal = None

    # Detectar habilidades con O*NET/ESCO si tenemos ocupación principal
    habilidades = []
    if ocupacion_principal:
        try:
            kg = get_knowledge_graph()
            skills = kg.get_skills(ocupacion_principal["id"], source=ocupacion_principal["source"], top_n=8)
            habilidades = [s["name"] for s in skills]
        except Exception:
            pass

    # Fallback local
    if not habilidades:
        skills_db = ["python", "sql", "excel", "power bi", "inglés", "english", "java", "javascript", "react", "node", "contabilidad", "auditoria", "marketing", "ventas"]
        for skill in skills_db:
            if skill in vacante_lower:
                habilidades.append(skill.capitalize())

    # Detectar ubicación
    ciudades = ["bogotá", "medellín", "cali", "barranquilla", "cartagena", "bucaramanga"]
    ubicacion = next((c for c in ciudades if c in vacante_lower), "No especificada")

    return {
        "cargo_detectado": cargo_detectado,
        "habilidades_detectadas": habilidades,
        "ubicacion": ubicacion.capitalize(),
        "longitud_texto": len(vacante),
        "ocupaciones_sugeridas": ocupaciones_similares,
    }


def _respuesta_demo(mensaje: str, contexto: dict) -> str:
    """Respuesta de demostración sin LLM."""
    respuesta = f"Recibí tu consulta: '{mensaje}'. "

    if "programas_relacionados" in contexto:
        prog = contexto["programas_relacionados"][0]
        respuesta += f"Encontré el programa '{prog['programa']}' con {prog['matriculados']} matriculados. "

    if "top_sectores" in contexto:
        top = contexto["top_sectores"][0]
        respuesta += f"El sector con más empleo formal es '{top['sector']}' con {top['cotizantes']:,} cotizantes. "

    respuesta += "\n\n[Nota: Esta es una respuesta de demostración. Configura DEEPINFRA_API_KEY en .env para activar Gemma 4.]"
    return respuesta


async def _llamar_gemma4(mensaje: str, contexto: dict) -> str:
    """Llama a Gemma 4 via DeepInfra API."""
    guias = contexto.get("guias_relacionadas", [])
    guias_str = "\n\n".join(
        f"[Fuente: {g['fuente']} | similitud: {g['similitud']}]\n{g['texto']}"
        for g in guias
    ) if guias else "No se encontraron guias relevantes."

    estructurados = {k: v for k, v in contexto.items() if k != "guias_relacionadas"}
    contexto_str = f"""### Guias/documentos relevantes (RAG):
{guias_str}

### Datos estructurados del sistema:
{json.dumps(estructurados, ensure_ascii=False, default=str)}
"""

    prompt = f"""Eres ALBA, un asistente de empleabilidad colombiano. Responde en español.
Usa estos datos del sistema para contextualizar tu respuesta. Prioriza las guias/documentos relevantes.
{contexto_str}

Pregunta del usuario: {mensaje}
"""

    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEEPINFRA_URL,
            headers={"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "google/gemma-4-31b-it",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.7,
            },
            timeout=30,
        )
        data = response.json()
        return data["choices"][0]["message"]["content"]


async def _generar_pregunta_gemma4(vacante: str, analisis: dict) -> str:
    """Genera pregunta de entrevista con Gemma 4."""
    prompt = f"""Eres un reclutador. Genera UNA pregunta de entrevista para esta vacante:
{vacante}

Análisis: {analisis}
Genera una pregunta específica y profesional.
"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEEPINFRA_URL,
            headers={"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"},
            json={"model": "google/gemma-4-31b-it", "messages": [{"role": "user", "content": prompt}], "max_tokens": 200},
            timeout=30,
        )
        return response.json()["choices"][0]["message"]["content"]


async def _evaluar_gemma4(pregunta: str, respuesta: str) -> dict:
    """Evalúa respuesta con Gemma 4."""
    prompt = f"""Evalúa esta respuesta de entrevista.
Pregunta: {pregunta}
Respuesta del candidato: {respuesta}

Devuelve JSON con: score (0-100), feedback, puntos_fuertes (lista), puntos_mejora (lista).
"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEEPINFRA_URL,
            headers={"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"},
            json={"model": "google/gemma-4-31b-it", "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
            timeout=30,
        )
        return {"evaluacion_gemma4": response.json()["choices"][0]["message"]["content"]}


async def _generar_cv_gemma4(perfil: str, vacante: dict) -> dict:
    """Genera sugerencias de CV con Gemma 4."""
    prompt = f"""Sugiere cómo estructurar un CV para esta vacante:
{vacante}

Perfil del candidato: {perfil}

Devuelve JSON con: habilidades_destacar (lista), experiencia_relevante (texto), formato_recomendado (texto).
"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            DEEPINFRA_URL,
            headers={"Authorization": f"Bearer {DEEPINFRA_API_KEY}", "Content-Type": "application/json"},
            json={"model": "google/gemma-4-31b-it", "messages": [{"role": "user", "content": prompt}], "max_tokens": 400},
            timeout=30,
        )
        return {"sugerencia_gemma4": response.json()["choices"][0]["message"]["content"]}


# ============================================================================
# Knowledge Graph: O*NET + ESCO
# ============================================================================

class BuscarOcupacionesRequest(BaseModel):
    q: str
    top_k: int = 5


@router.post("/buscar-ocupaciones")
async def buscar_ocupaciones(req: BuscarOcupacionesRequest):
    """Busca ocupaciones similares en O*NET y ESCO."""
    try:
        kg = get_knowledge_graph()
        resultados = kg.search_occupations(req.q, req.top_k)
        return {"query": req.q, "ocupaciones": resultados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocupacion-skills")
async def ocupacion_skills(occupation_id: str, source: str = "auto", top_n: int = 10):
    """Devuelve las principales skills de una ocupación O*NET o ESCO."""
    try:
        kg = get_knowledge_graph()
        skills = kg.get_skills(occupation_id, source, top_n)
        occ = kg.onet_occupations.get(occupation_id) or kg.esco_occupations.get(occupation_id)
        result = {
            "occupation_id": occupation_id,
            "title": (occ.get("title") if occ else occupation_id) or occupation_id,
            "source": source,
            "skills": skills,
        }
        # Sanitizar floats no JSON-compliant (NaN/Inf)
        import json, math
        def sanitize(obj):
            if isinstance(obj, float):
                if math.isnan(obj) or math.isinf(obj):
                    return None
                return obj
            if isinstance(obj, dict):
                return {k: sanitize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [sanitize(v) for v in obj]
            return obj
        return sanitize(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class BrechaHabilidadesRequest(BaseModel):
    user_skills: list[str]
    occupation_id: str
    source: str = "auto"


@router.post("/brecha-habilidades")
async def brecha_habilidades(req: BrechaHabilidadesRequest):
    """Compara habilidades del usuario con las requeridas por una ocupación."""
    try:
        kg = get_knowledge_graph()
        resultado = kg.skill_gap(req.user_skills, req.occupation_id, req.source)
        return resultado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ocupaciones-relacionadas")
async def ocupaciones_relacionadas(onet_soc_code: str, top_k: int = 5):
    """Devuelve ocupaciones relacionadas según O*NET."""
    try:
        kg = get_knowledge_graph()
        resultados = kg.get_related_occupations(onet_soc_code, top_k)
        return {"onet_soc_code": onet_soc_code, "relacionadas": resultados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sugerir-por-habilidades")
async def sugerir_por_habilidades(req: BrechaHabilidadesRequest):
    """Sugiere ocupaciones basadas en las habilidades del usuario."""
    try:
        kg = get_knowledge_graph()
        resultados = kg.suggest_occupations_from_skills(req.user_skills, req.top_k if hasattr(req, "top_k") else 5)
        return {"user_skills": req.user_skills, "ocupaciones": resultados}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


