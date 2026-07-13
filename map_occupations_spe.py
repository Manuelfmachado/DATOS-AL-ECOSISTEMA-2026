"""
Genera embeddings para ocupaciones SPE SENA y calcula mapeo con ESCO y O*NET.
"""
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OUT = Path("data/processed/mappings")
OUT.mkdir(parents=True, exist_ok=True)


def get_embeddings(texts, batch_size=32):
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
            all_embeddings.extend([[0.0] * 768 for _ in batch])
    return np.array(all_embeddings)


def cosine_similarity(a, b):
    a = np.array(a)
    b = np.array(b)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def generate_spe_embeddings():
    df = pd.read_csv("data/processed/spe_ape_inscritos_ocupacion.csv")
    print(f"Generando embeddings para {len(df)} ocupaciones SPE SENA...")
    texts = [str(o) for o in df["ocupacion"].tolist()]
    embeddings = get_embeddings(texts)
    records = []
    for (_, row), emb in zip(df.iterrows(), embeddings):
        records.append({
            "ocupacion": row["ocupacion"],
            "id_ocupacion": int(row["id_ocupacion"]),
            "texto": row["ocupacion"],
            "embedding": emb.tolist(),
        })
    with open("data/processed/embeddings/spe_occupations_embeddings.json", "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"[OK] spe_occupations_embeddings.json: {len(records)} registros")
    return records


def load_embeddings(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def map_sources(source_embeddings, target_embeddings, source_key, target_key, top_k=3):
    """Para cada source, encuentra los top_k targets más similares."""
    source_matrix = np.array([s["embedding"] for s in source_embeddings])
    target_matrix = np.array([t["embedding"] for t in target_embeddings])
    
    # Normalizar
    source_norm = source_matrix / np.linalg.norm(source_matrix, axis=1, keepdims=True)
    target_norm = target_matrix / np.linalg.norm(target_matrix, axis=1, keepdims=True)
    
    # Similaridad coseno
    similarities = np.dot(source_norm, target_norm.T)
    
    mappings = []
    for i, source in enumerate(source_embeddings):
        top_indices = np.argsort(similarities[i])[::-1][:top_k]
        for idx in top_indices:
            target = target_embeddings[idx]
            mappings.append({
                source_key: source.get(source_key) or source.get("onet_soc_code") or source.get("esco_uri"),
                target_key: target.get(target_key) or target.get("ocupacion"),
                "similarity_score": float(similarities[i][idx]),
            })
    return mappings


def main():
    spe_records = generate_spe_embeddings()
    
    onet_records = load_embeddings("data/processed/embeddings/onet_occupations_embeddings.json")
    esco_records = load_embeddings("data/processed/embeddings/esco_occupations_embeddings.json")
    
    print("\nMapeando O*NET -> SPE SENA...")
    onet_spe = map_sources(onet_records, spe_records, "onet_soc_code", "spe_ocupacion")
    df_onet_spe = pd.DataFrame(onet_spe)
    df_onet_spe.to_csv(OUT / "onet_spe_mapping.csv", index=False)
    print(f"[OK] onet_spe_mapping.csv: {len(df_onet_spe)} rows")
    
    print("\nMapeando ESCO -> SPE SENA...")
    esco_spe = map_sources(esco_records, spe_records, "esco_uri", "spe_ocupacion")
    df_esco_spe = pd.DataFrame(esco_spe)
    df_esco_spe.to_csv(OUT / "esco_spe_mapping.csv", index=False)
    print(f"[OK] esco_spe_mapping.csv: {len(df_esco_spe)} rows")
    
    print("\nMapeo completado.")


if __name__ == "__main__":
    main()
