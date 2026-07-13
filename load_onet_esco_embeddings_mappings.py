"""
Carga embeddings y mapeos de O*NET/ESCO a Supabase.
Asume que las tablas principales ya estan cargadas.
"""
import os
import json
import math
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

DATA = Path("data/processed")
BATCH = 500


def clean_record(record):
    cleaned = {}
    for k, v in record.items():
        if isinstance(v, list):
            cleaned[k] = v
        elif isinstance(v, np.ndarray):
            cleaned[k] = v.tolist()
        elif isinstance(v, float):
            if math.isnan(v) or math.isinf(v):
                cleaned[k] = None
            else:
                cleaned[k] = v
        elif isinstance(v, (np.integer, np.floating)):
            cleaned[k] = v.item()
        elif pd.isna(v):
            cleaned[k] = None
        else:
            cleaned[k] = v
    return cleaned


def batch_insert(table, records):
    if not records:
        print(f"  [SKIP] {table}: no hay registros")
        return
    print(f"  Insertando {len(records)} registros en {table}...")
    for i in range(0, len(records), BATCH):
        batch = [clean_record(r) for r in records[i : i + BATCH]]
        try:
            supabase.table(table).insert(batch).execute()
        except Exception as e:
            print(f"    [ERROR] batch {i}: {e}")
            raise
    print(f"  [OK] {table}")


def truncate_table(table):
    try:
        supabase.table(table).delete().neq("id", 0).execute()
        print(f"  [OK] {table} truncada")
    except Exception as e:
        print(f"  [WARN] No se pudo truncar {table}: {e}")


def load_embeddings():
    print("\n=== Cargando embeddings ===")

    truncate_table("embeddings_onet_occupations")
    with open(DATA / "embeddings" / "onet_occupations_embeddings.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    records = [
        {"onet_soc_code": item["onet_soc_code"], "texto": item["texto"], "embedding": item["embedding"]}
        for item in data
    ]
    batch_insert("embeddings_onet_occupations", records)

    truncate_table("embeddings_esco_occupations")
    with open(DATA / "embeddings" / "esco_occupations_embeddings.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    seen = set()
    records = []
    for item in data:
        if item["esco_uri"] in seen:
            continue
        seen.add(item["esco_uri"])
        records.append({"esco_uri": item["esco_uri"], "texto": item["texto"], "embedding": item["embedding"]})
    batch_insert("embeddings_esco_occupations", records)


def load_mappings():
    print("\n=== Cargando mapeos a SPE SENA ===")

    # O*NET -> SPE
    try:
        truncate_table("onet_spe_mapping")
        df = pd.read_csv(DATA / "mappings" / "onet_spe_mapping.csv")
        df = df.rename(columns={"onet_soc_code": "onet_soc_code", "spe_ocupacion": "spe_ocupacion", "similarity_score": "similarity_score"})
        records = df.to_dict("records")
        batch_insert("onet_spe_mapping", records)
    except Exception as e:
        print(f"  [WARN] onet_spe_mapping no cargada: {e}")
        print("  Ejecuta en SQL Editor: CREATE TABLE ... para onet_spe_mapping (ver schema_onet_esco.sql)")

    # ESCO -> SPE
    truncate_table("esco_spe_mapping")
    df = pd.read_csv(DATA / "mappings" / "esco_spe_mapping.csv")
    df = df.rename(columns={"esco_uri": "esco_uri", "spe_ocupacion": "spe_ocupacion", "similarity_score": "similarity_score"})
    df = df.drop_duplicates(subset=["esco_uri", "spe_ocupacion"], keep="first")
    records = df.to_dict("records")
    batch_insert("esco_spe_mapping", records)


def main():
    load_embeddings()
    load_mappings()
    print("\nCarga completada.")


if __name__ == "__main__":
    main()
