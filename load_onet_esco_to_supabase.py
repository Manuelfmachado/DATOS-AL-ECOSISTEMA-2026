"""
Carga datos procesados de O*NET y ESCO a Supabase.
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
    """Limpia valores no serializables: NaN, Inf, numpy types."""
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


def load_onet():
    print("\n=== Cargando O*NET ===")

    # Occupations
    truncate_table("onet_occupations")
    df = pd.read_csv(DATA / "onet" / "onet_occupations.csv")
    records = df.rename(columns={
        "onet_soc_code": "onet_soc_code",
        "title": "title",
        "description": "description",
    }).to_dict("records")
    batch_insert("onet_occupations", records)

    # Skill definitions
    truncate_table("onet_skill_definitions")
    df = pd.read_csv(DATA / "onet" / "onet_skill_definitions.csv")
    records = df.to_dict("records")
    batch_insert("onet_skill_definitions", records)

    # Occupation skills
    truncate_table("onet_occupation_skills")
    df = pd.read_csv(DATA / "onet" / "onet_occupation_skills.csv")
    # Deduplicar por onet_soc_code + element_id + domain + scale_id
    df = df.drop_duplicates(subset=["onet_soc_code", "element_id", "domain", "scale_id"], keep="first")
    records = df.to_dict("records")
    batch_insert("onet_occupation_skills", records)

    # Related occupations
    truncate_table("onet_related_occupations")
    df = pd.read_csv(DATA / "onet" / "onet_related_occupations.csv")
    records = df.to_dict("records")
    batch_insert("onet_related_occupations", records)

    # Job titles
    truncate_table("onet_job_titles")
    df = pd.read_csv(DATA / "onet" / "onet_job_titles.csv")
    df = df[["onet_soc_code", "job_title", "short_title"]]
    records = df.to_dict("records")
    batch_insert("onet_job_titles", records)

    # Education
    truncate_table("onet_education")
    df = pd.read_csv(DATA / "onet" / "onet_education.csv")
    df = df[["onet_soc_code", "element_id", "element_name", "category", "data_value"]]
    df["category"] = pd.to_numeric(df["category"], errors="coerce").astype("Int64")
    records = df.to_dict("records")
    batch_insert("onet_education", records)


def load_esco():
    print("\n=== Cargando ESCO ===")

    # Occupations
    truncate_table("esco_occupations")
    df = pd.read_csv(DATA / "esco" / "esco_occupations.csv")
    df = df.drop_duplicates(subset=["uri"], keep="first")
    records = []
    for _, row in df.iterrows():
        records.append({
            "uri": row["uri"],
            "code": row.get("code"),
            "title": row["title"],
            "title_es": row.get("title_es"),
            "description": row.get("description", ""),
            "preferred_label": json.dumps({"es": row["preferred_label"]}, ensure_ascii=False) if pd.notna(row.get("preferred_label")) else None,
            "alternative_label": json.dumps({"es": row["alternative_label"].split("|")}, ensure_ascii=False) if pd.notna(row.get("alternative_label")) else None,
            "broader_isco_group": row.get("broader_isco_group"),
        })
    batch_insert("esco_occupations", records)

    # Skills
    truncate_table("esco_skills")
    df = pd.read_csv(DATA / "esco" / "esco_skills.csv")
    df = df.drop_duplicates(subset=["uri"], keep="first")
    records = []
    for _, row in df.iterrows():
        records.append({
            "uri": row["uri"],
            "skill_type": row.get("skill_type"),
            "title": row["title"],
            "title_es": row.get("title_es"),
            "description": row.get("description", ""),
            "preferred_label": json.dumps({"es": row["preferred_label"]}, ensure_ascii=False) if pd.notna(row.get("preferred_label")) else None,
            "alternative_label": json.dumps({"es": row["alternative_label"].split("|")}, ensure_ascii=False) if pd.notna(row.get("alternative_label")) else None,
        })
    batch_insert("esco_skills", records)

    # Occupation skills
    truncate_table("esco_occupation_skills")
    df = pd.read_csv(DATA / "esco" / "esco_occupation_skills.csv")
    df = df.drop_duplicates(subset=["esco_uri", "esco_skill_uri", "relation_type"], keep="first")
    records = df.to_dict("records")
    batch_insert("esco_occupation_skills", records)


def load_embeddings():
    print("\n=== Cargando embeddings ===")

    # O*NET
    truncate_table("embeddings_onet_occupations")
    with open(DATA / "embeddings" / "onet_occupations_embeddings.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    records = [
        {"onet_soc_code": item["onet_soc_code"], "texto": item["texto"], "embedding": item["embedding"]}
        for item in data
    ]
    batch_insert("embeddings_onet_occupations", records)

    # ESCO
    truncate_table("embeddings_esco_occupations")
    with open(DATA / "embeddings" / "esco_occupations_embeddings.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    records = [
        {"esco_uri": item["esco_uri"], "texto": item["texto"], "embedding": item["embedding"]}
        for item in data
    ]
    batch_insert("embeddings_esco_occupations", records)


def load_mappings():
    print("\n=== Cargando mapeos a SPE SENA ===")

    # O*NET -> SPE
    truncate_table("onet_spe_mapping")
    df = pd.read_csv(DATA / "mappings" / "onet_spe_mapping.csv")
    df = df.rename(columns={"onet_soc_code": "onet_soc_code", "spe_ocupacion": "spe_ocupacion", "similarity_score": "similarity_score"})
    records = df.to_dict("records")
    batch_insert("onet_spe_mapping", records)

    # ESCO -> SPE
    truncate_table("esco_spe_mapping")
    df = pd.read_csv(DATA / "mappings" / "esco_spe_mapping.csv")
    df = df.rename(columns={"esco_uri": "esco_uri", "spe_ocupacion": "spe_ocupacion", "similarity_score": "similarity_score"})
    records = df.to_dict("records")
    batch_insert("esco_spe_mapping", records)


def main():
    load_onet()
    load_esco()
    load_embeddings()
    load_mappings()
    print("\nCarga completada.")


if __name__ == "__main__":
    main()
