"""
Procesa el dump CSV de ESCO v1.2.1 en español y genera CSVs limpios.
"""
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE = Path("ESCO dataset - v1.2.1 - classification - es - csv")
OUT = Path("data/processed/esco")
OUT.mkdir(parents=True, exist_ok=True)


def read_csv(filename):
    path = BASE / filename
    return pd.read_csv(path, sep=None, engine="python")


def parse_json_like_labels(value):
    """Las columnas altLabels/hiddenLabels vienen como strings con corchetes."""
    if pd.isna(value) or value == "[]":
        return []
    # Eliminar corchetes y comillas, dividir por coma
    text = str(value).strip("[]")
    if not text:
        return []
    return [x.strip().strip('"').strip("'") for x in text.split(",") if x.strip()]


def process_occupations():
    df = read_csv("occupations_es.csv")
    print(f"Ocupaciones ESCO raw: {len(df)}")

    records = []
    for _, row in df.iterrows():
        records.append({
            "uri": row["conceptUri"],
            "code": row.get("code"),
            "title": row["preferredLabel"],
            "title_es": row["preferredLabel"],
            "description": row.get("description", ""),
            "preferred_label": row["preferredLabel"],
            "alternative_label": "|".join(parse_json_like_labels(row.get("altLabels", ""))),
            "broader_isco_group": row.get("iscoGroup"),
        })

    df_out = pd.DataFrame(records)
    df_out.to_csv(OUT / "esco_occupations.csv", index=False)
    print(f"[OK] esco_occupations.csv: {len(df_out)} rows")
    return df_out


def process_skills():
    df = read_csv("skills_es.csv")
    print(f"Skills ESCO raw: {len(df)}")

    records = []
    for _, row in df.iterrows():
        records.append({
            "uri": row["conceptUri"],
            "skill_type": row.get("skillType"),
            "title": row["preferredLabel"],
            "title_es": row["preferredLabel"],
            "description": row.get("description", ""),
            "preferred_label": row["preferredLabel"],
            "alternative_label": "|".join(parse_json_like_labels(row.get("altLabels", ""))),
        })

    df_out = pd.DataFrame(records)
    df_out.to_csv(OUT / "esco_skills.csv", index=False)
    print(f"[OK] esco_skills.csv: {len(df_out)} rows")
    return df_out


def process_relations():
    df = read_csv("occupationSkillRelations_es.csv")
    print(f"Relaciones ESCO raw: {len(df)}")

    df_out = df.rename(columns={
        "occupationUri": "esco_uri",
        "skillUri": "esco_skill_uri",
        "relationType": "relation_type",
    })[["esco_uri", "esco_skill_uri", "relation_type"]]
    df_out.to_csv(OUT / "esco_occupation_skills.csv", index=False)
    print(f"[OK] esco_occupation_skills.csv: {len(df_out)} rows")
    return df_out


def main():
    process_occupations()
    process_skills()
    process_relations()
    print("\nESCO CSV procesado completo.")


if __name__ == "__main__":
    main()
