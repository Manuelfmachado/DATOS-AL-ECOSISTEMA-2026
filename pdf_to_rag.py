"""
pdf_to_rag.py
Pipeline: PDFs -> PyMuPDF -> chunks -> Gemma 300 embeddings (768d) -> Supabase pgvector.
Uso:
    python pdf_to_rag.py --source "https://.../guia.pdf" --name "Guia formalizacion SENA" --category "emprende"
    python pdf_to_rag.py --source "data/raw/mipdf.pdf" --name "Mi PDF" --category "coach"
"""
import argparse
import json
import logging
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

import fitz  # PyMuPDF
import httpx
from dotenv import load_dotenv

# Cargar variables de entorno desde raiz y backend/.env
load_dotenv()
load_dotenv("backend/.env", override=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from backend.app.services.embeddings import get_embeddings_sync, EMBEDDING_DIM

# Configuracion Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL y SUPABASE_KEY deben estar configuradas")

SUPABASE_REST_URL = f"{SUPABASE_URL}/rest/v1"
HEADERS_SUPABASE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}


def download_pdf(source: str) -> bytes:
    """Descarga un PDF desde URL o lee desde disco."""
    parsed = urlparse(source)
    if parsed.scheme in ("http", "https"):
        logger.info("Descargando PDF desde %s", source)
        response = httpx.get(source, follow_redirects=True, timeout=120.0)
        response.raise_for_status()
        return response.content
    else:
        logger.info("Leyendo PDF local %s", source)
        return Path(source).read_bytes()


def extract_text(pdf_bytes: bytes) -> str:
    """Extrae texto plano de un PDF usando PyMuPDF."""
    text_parts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            if text.strip():
                text_parts.append(f"--- Pagina {page_num} ---\n{text.strip()}")
    return "\n\n".join(text_parts)


def clean_text(text: str) -> str:
    """Limpia saltos de linea excesivos y espacios."""
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 150,
) -> List[Dict[str, Any]]:
    """
    Divide el texto en chunks por parrafos respetando un tamano maximo aproximado.
    Retorna lista de dicts con texto y numero de pagina estimado.
    """
    # Separamos por paginas para mantener metadata
    page_pattern = re.compile(r"--- Pagina (\d+) ---\n(.*?)(?=\n--- Pagina \d+ ---|$)", re.DOTALL)
    pages = page_pattern.findall(text)

    if not pages:
        pages = [("1", text)]

    chunks: List[Dict[str, Any]] = []
    global_index = 0

    for page_num_str, page_text in pages:
        page_num = int(page_num_str)
        page_text = clean_text(page_text)
        if not page_text:
            continue

        # Dividir pagina en parrafos
        paragraphs = [p.strip() for p in page_text.split("\n\n") if p.strip()]
        current_chunk = ""

        for para in paragraphs:
            # Si un solo parrafo es muy largo, partirlo por oraciones
            if len(para) > chunk_size * 1.5:
                sentences = re.split(r"(?<=[.!?]) +", para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= chunk_size:
                        current_chunk += " " + sentence if current_chunk else sentence
                    else:
                        if current_chunk:
                            chunks.append({
                                "texto": current_chunk.strip(),
                                "pagina": page_num,
                                "chunk_index": global_index,
                            })
                            global_index += 1
                            # Overlap: conservar ultimas palabras del chunk anterior
                            words = current_chunk.strip().split()
                            overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else current_chunk
                            current_chunk = overlap_text + " " + sentence
                        else:
                            current_chunk = sentence
            else:
                if len(current_chunk) + len(para) + 2 <= chunk_size:
                    current_chunk += "\n\n" + para if current_chunk else para
                else:
                    if current_chunk:
                        chunks.append({
                            "texto": current_chunk.strip(),
                            "pagina": page_num,
                            "chunk_index": global_index,
                        })
                        global_index += 1
                        words = current_chunk.strip().split()
                        overlap_text = " ".join(words[-overlap:]) if len(words) > overlap else current_chunk
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para

        if current_chunk:
            chunks.append({
                "texto": current_chunk.strip(),
                "pagina": page_num,
                "chunk_index": global_index,
            })
            global_index += 1

    return chunks


def upsert_embeddings(
    table_name: str,
    source_name: str,
    source_url: str,
    category: str,
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    dry_run: bool = False,
) -> int:
    """Inserta chunks y embeddings en la tabla de Supabase indicada."""
    if len(chunks) != len(embeddings):
        raise ValueError("chunks y embeddings deben tener la misma longitud")

    if dry_run:
        logger.info("[DRY-RUN] Se insertarian %d registros en %s", len(chunks), table_name)
        return 0

    # Primero eliminar registros previos de la misma fuente para evitar duplicados
    delete_filter = f"metadata->>source_name=eq.{source_name}"
    httpx.delete(f"{SUPABASE_REST_URL}/{table_name}?{delete_filter}", headers=HEADERS_SUPABASE)

    records = []
    for chunk, vector in zip(chunks, embeddings):
        records.append({
            "texto": chunk["texto"],
            "embedding": vector,
            "metadata": {
                "source_name": source_name,
                "source_url": source_url,
                "category": category,
                "page": chunk["pagina"],
                "chunk_index": chunk["chunk_index"],
                "model": "google/embeddinggemma-300m",
                "dimensions": EMBEDDING_DIM,
            },
        })

    inserted = 0
    batch_size = 50
    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(records), batch_size):
            batch = records[i : i + batch_size]
            response = client.post(
                f"{SUPABASE_REST_URL}/{table_name}",
                headers=HEADERS_SUPABASE,
                json=batch,
            )
            try:
                response.raise_for_status()
                inserted += len(batch)
                logger.info("Insertados %d/%d registros en %s", inserted, len(records), table_name)
            except httpx.HTTPStatusError as e:
                logger.error("Error insertando batch: %s - %s", e.response.status_code, e.response.text)
                raise

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Ingesta PDFs a RAG con Gemma 300 embeddings")
    parser.add_argument("--source", required=True, help="URL o ruta local del PDF")
    parser.add_argument("--name", required=True, help="Nombre legible de la fuente")
    parser.add_argument("--category", default="general", help="Categoria: coach, emprende, simulador, observatorio, match")
    parser.add_argument("--table", default="embeddings_guias", help="Tabla de Supabase destino")
    parser.add_argument("--chunk-size", type=int, default=800, help="Tamano aproximado de chunk en caracteres")
    parser.add_argument("--overlap", type=int, default=150, help="Palabras de overlap entre chunks")
    parser.add_argument("--dry-run", action="store_true", help="No insertar en Supabase, solo mostrar estadisticas")
    args = parser.parse_args()

    logger.info("Iniciando pipeline RAG para: %s", args.name)

    # 1. Descargar/leer PDF
    pdf_bytes = download_pdf(args.source)
    logger.info("PDF cargado: %d bytes", len(pdf_bytes))

    # 2. Extraer texto con PyMuPDF
    raw_text = extract_text(pdf_bytes)
    logger.info("Texto extraido: %d caracteres", len(raw_text))

    if not raw_text.strip():
        logger.error("No se pudo extraer texto del PDF")
        sys.exit(1)

    # 3. Limpiar y chunking
    chunks = chunk_text(raw_text, chunk_size=args.chunk_size, overlap=args.overlap)
    logger.info("Chunks generados: %d", len(chunks))

    if not chunks:
        logger.error("No se generaron chunks validos")
        sys.exit(1)

    # 4. Generar embeddings
    texts = [c["texto"] for c in chunks]
    logger.info("Generando embeddings con Gemma 300 (%d dims)...", EMBEDDING_DIM)
    embeddings = get_embeddings_sync(texts, batch_size=16)
    logger.info("Embeddings generados: %d, dimensiones: %d", len(embeddings), len(embeddings[0]))

    # 5. Subir a Supabase
    inserted = upsert_embeddings(
        table_name=args.table,
        source_name=args.name,
        source_url=args.source,
        category=args.category,
        chunks=chunks,
        embeddings=embeddings,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        logger.info("Pipeline finalizado en modo dry-run. No se insertaron registros.")
    else:
        logger.info("Pipeline finalizado. %d chunks insertados en %s", inserted, args.table)


if __name__ == "__main__":
    main()
