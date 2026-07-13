"""
Genera embeddings para ocupaciones O*NET y ESCO usando Gemma 300 via DeepInfra.
Guarda resultados en archivos JSON locales.
"""
import os
import json
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

OUT = Path("data/processed/embeddings")
OUT.mkdir(parents=True, exist_ok=True)


def get_embeddings(texts, batch_size=32):
    """Genera embeddings via DeepInfra Gemma 300."""
    import requests
    api_key = os.getenv("DEEPINFRA_API_KEY")
    url = "https://api.deepinfra.com/v1/openai/embeddings"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        payload = {
            "model": "google/embeddinggemma-300m",
            "input": batch,
            "encoding_format": "float",
        }
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=120)
            r.raise_for_status()
            data = r.json()
            embeddings = [item["embedding"] for item in data["data"]]
            all_embeddings.extend(embeddings)
        except Exception as e:
            print(f"[ERROR] batch {i}: {e}")
            # Devolver zeros para no romper el pipeline
            all_embeddings.extend([[0.0] * 768 for _ in batch])
    return all_embeddings


def build_text(row, source):
    """Construye texto enriquecido para embedding."""
    if source == "onet":
        title = row.get("title", "")
        desc = row.get("description", "")
        return f"{title}. {desc}".strip()
    elif source == "esco":
        title = row.get("title_es") or row.get("title", "")
        desc = row.get("description", "")
        return f"{title}. {desc}".strip()
    return ""


def process_onet():
    df = pd.read_csv("data/processed/onet/onet_occupations.csv")
    print(f"Generando embeddings para {len(df)} ocupaciones O*NET...")
    texts = [build_text(row, "onet") for _, row in df.iterrows()]
    embeddings = get_embeddings(texts)
    records = []
    for (_, row), emb in zip(df.iterrows(), embeddings):
        records.append({
            "onet_soc_code": row["onet_soc_code"],
            "texto": build_text(row, "onet"),
            "embedding": emb,
        })
    with open(OUT / "onet_occupations_embeddings.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"[OK] onet_occupations_embeddings.json: {len(records)} registros")


def process_esco():
    df = pd.read_csv("data/processed/esco/esco_occupations.csv")
    print(f"Generando embeddings para {len(df)} ocupaciones ESCO...")
    texts = [build_text(row, "esco") for _, row in df.iterrows()]
    embeddings = get_embeddings(texts)
    records = []
    for (_, row), emb in zip(df.iterrows(), embeddings):
        records.append({
            "esco_uri": row["uri"],
            "texto": build_text(row, "esco"),
            "embedding": emb,
        })
    with open(OUT / "esco_occupations_embeddings.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"[OK] esco_occupations_embeddings.json: {len(records)} registros")


def main():
    process_onet()
    process_esco()
    print("\nEmbeddings generados.")


if __name__ == "__main__":
    main()
