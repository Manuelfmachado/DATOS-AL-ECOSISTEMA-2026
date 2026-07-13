"""
Servicio de embeddings via DeepInfra usando Gemma 300 (google/embeddinggemma-300m).
Modelo OpenAI-compatible; retorna vectores de 768 dimensiones (calidad maxima).
"""
import os
import logging
from typing import List, Union
import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API_KEY")
DEEPINFRA_EMBEDDINGS_URL = "https://api.deepinfra.com/v1/openai/embeddings"
EMBEDDING_MODEL = "google/embeddinggemma-300m"
EMBEDDING_DIM = 768


async def get_embeddings(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos usando DeepInfra.
    Retorna lista de vectores de 768 dimensiones.
    """
    if not DEEPINFRA_API_KEY:
        raise RuntimeError("DEEPINFRA_API_KEY no configurada en variables de entorno")

    results: List[List[float]] = []
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json",
    }

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        # Filtrar vacios y reemplazar por espacio para evitar errores de API
        batch = [t.strip() if t.strip() else " " for t in batch]

        payload = {
            "model": EMBEDDING_MODEL,
            "input": batch,
            "encoding_format": "float",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    DEEPINFRA_EMBEDDINGS_URL, headers=headers, json=payload
                )
                response.raise_for_status()
                data = response.json()

            embeddings = sorted(data["data"], key=lambda x: x["index"])
            for item in embeddings:
                vector = item["embedding"]
                if len(vector) != EMBEDDING_DIM:
                    logger.warning(
                        "Embedding recibido con %d dimensiones; se esperaban %d",
                        len(vector),
                        EMBEDDING_DIM,
                    )
                results.append(vector)

        except httpx.HTTPStatusError as e:
            logger.error("Error HTTP en DeepInfra embeddings: %s - %s", e.response.status_code, e.response.text)
            raise
        except Exception as e:
            logger.error("Error generando embeddings: %s", e)
            raise

    return results


async def get_embedding(text: str) -> List[float]:
    """Genera un unico embedding de 768 dimensiones."""
    embeddings = await get_embeddings([text])
    return embeddings[0]


def get_embeddings_sync(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Version sincrona para scripts batch como pdf_to_rag.py."""
    if not DEEPINFRA_API_KEY:
        raise RuntimeError("DEEPINFRA_API_KEY no configurada en variables de entorno")

    results: List[List[float]] = []
    headers = {
        "Authorization": f"Bearer {DEEPINFRA_API_KEY}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch = [t.strip() if t.strip() else " " for t in batch]

            payload = {
                "model": EMBEDDING_MODEL,
                "input": batch,
                "encoding_format": "float",
            }

            response = client.post(DEEPINFRA_EMBEDDINGS_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            embeddings = sorted(data["data"], key=lambda x: x["index"])
            for item in embeddings:
                vector = item["embedding"]
                if len(vector) != EMBEDDING_DIM:
                    logger.warning(
                        "Embedding recibido con %d dimensiones; se esperaban %d",
                        len(vector),
                        EMBEDDING_DIM,
                    )
                results.append(vector)

    return results


def get_embedding_sync(text: str) -> List[float]:
    """Version sincrona para un solo texto."""
    return get_embeddings_sync([text])[0]
