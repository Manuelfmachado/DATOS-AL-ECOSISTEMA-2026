"""
Procesa archivos TXT de O*NET 30.3 y genera CSVs limpios listos para Supabase.
"""
import os
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE = Path("data/raw/onet_30_3/db_30_3_text")
OUT = Path("data/processed/onet")
OUT.mkdir(parents=True, exist_ok=True)


def read_onet(filename):
    path = BASE / filename
    if not path.exists():
        print(f"[SKIP] No existe {filename}")
        return None
    return pd.read_csv(path, sep="\t", low_memory=False)


def process_occupations():
    df = read_onet("Occupation Data.txt")
    if df is None:
        return
    df = df.rename(columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Title": "title",
        "Description": "description",
    })
    df.to_csv(OUT / "onet_occupations.csv", index=False)
    print(f"[OK] onet_occupations.csv: {len(df)} rows")
    return df


def process_skills():
    # Essential Skills
    df_ess = read_onet("Essential Skills.txt")
    if df_ess is not None:
        df_ess = df_ess.rename(columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Scale ID": "scale_id",
            "Data Value": "data_value",
        })
        df_ess["domain"] = "essential_skill"
        df_ess["is_essential"] = True
        df_ess["is_software"] = False
    else:
        df_ess = pd.DataFrame()

    # Transferable Skills
    df_trans = read_onet("Transferable Skills.txt")
    if df_trans is not None:
        df_trans = df_trans.rename(columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Scale ID": "scale_id",
            "Data Value": "data_value",
        })
        df_trans["domain"] = "transferable_skill"
        df_trans["is_essential"] = False
        df_trans["is_software"] = False
    else:
        df_trans = pd.DataFrame()

    # Knowledge
    df_know = read_onet("Knowledge.txt")
    if df_know is not None:
        df_know = df_know.rename(columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Scale ID": "scale_id",
            "Data Value": "data_value",
        })
        df_know["domain"] = "knowledge"
        df_know["is_essential"] = False
        df_know["is_software"] = False
    else:
        df_know = pd.DataFrame()

    # Abilities
    df_abil = read_onet("Abilities.txt")
    if df_abil is not None:
        df_abil = df_abil.rename(columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Scale ID": "scale_id",
            "Data Value": "data_value",
        })
        df_abil["domain"] = "ability"
        df_abil["is_essential"] = False
        df_abil["is_software"] = False
    else:
        df_abil = pd.DataFrame()

    # Software Skills
    df_soft = read_onet("Software Skills.txt")
    if df_soft is not None:
        df_soft = df_soft.rename(columns={
            "O*NET-SOC Code": "onet_soc_code",
            "Element ID": "element_id",
            "Element Name": "element_name",
            "Hot Technology": "hot_technology",
            "In Demand": "in_demand",
        })
        df_soft["domain"] = "software_skill"
        df_soft["is_essential"] = False
        df_soft["is_software"] = True
        df_soft["scale_id"] = None
        df_soft["data_value"] = None
    else:
        df_soft = pd.DataFrame()

    cols = ["onet_soc_code", "element_id", "element_name", "domain", "scale_id", "data_value", "is_essential", "is_software", "hot_technology", "in_demand"]
    all_skills = pd.concat([df_ess, df_trans, df_know, df_abil, df_soft], ignore_index=True)
    all_skills = all_skills[[c for c in cols if c in all_skills.columns]]
    all_skills.to_csv(OUT / "onet_occupation_skills.csv", index=False)
    print(f"[OK] onet_occupation_skills.csv: {len(all_skills)} rows")

    # Skill definitions
    defs = []
    for domain, df in [("essential_skill", df_ess), ("transferable_skill", df_trans), ("knowledge", df_know), ("ability", df_abil), ("software_skill", df_soft)]:
        if df.empty:
            continue
        sub = df[["element_id", "element_name"]].drop_duplicates()
        for _, row in sub.iterrows():
            defs.append({
                "element_id": row["element_id"],
                "element_name": row["element_name"],
                "domain": domain,
                "description": None,
            })
    df_defs = pd.DataFrame(defs).drop_duplicates("element_id")
    df_defs.to_csv(OUT / "onet_skill_definitions.csv", index=False)
    print(f"[OK] onet_skill_definitions.csv: {len(df_defs)} rows")


def process_related():
    df = read_onet("Related Occupations.txt")
    if df is None:
        return
    df = df.rename(columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Related O*NET-SOC Code": "related_onet_soc_code",
        "Relatedness Tier": "relatedness_tier",
        "Index": "related_index",
    })
    df.to_csv(OUT / "onet_related_occupations.csv", index=False)
    print(f"[OK] onet_related_occupations.csv: {len(df)} rows")


def process_job_titles():
    df = read_onet("Job Titles.txt")
    if df is None:
        return
    df = df.rename(columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Job Title": "job_title",
        "Short Title": "short_title",
    })
    df.to_csv(OUT / "onet_job_titles.csv", index=False)
    print(f"[OK] onet_job_titles.csv: {len(df)} rows")


def process_education():
    df = read_onet("Education.txt")
    if df is None:
        return
    df = df.rename(columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Element ID": "element_id",
        "Element Name": "element_name",
        "Category": "category",
        "Data Value": "data_value",
    })
    df.to_csv(OUT / "onet_education.csv", index=False)
    print(f"[OK] onet_education.csv: {len(df)} rows")


def process_tasks():
    df = read_onet("Task Statements.txt")
    if df is None:
        return
    df = df.rename(columns={
        "O*NET-SOC Code": "onet_soc_code",
        "Task ID": "task_id",
        "Task": "task",
        "Task Type": "task_type",
    })
    df.to_csv(OUT / "onet_task_statements.csv", index=False)
    print(f"[OK] onet_task_statements.csv: {len(df)} rows")


def main():
    process_occupations()
    process_skills()
    process_related()
    process_job_titles()
    process_education()
    process_tasks()
    print("\nTodos los CSVs de O*NET generados en", OUT)


if __name__ == "__main__":
    main()
