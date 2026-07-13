"""
Reprocesa solo el archivo SNIES usando la lógica actualizada de etl_pipeline.py
y recarga la tabla en Supabase.
"""
import os
import unicodedata
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

RAW = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(exist_ok=True)


def _norm_depto_snies(name):
    if not isinstance(name, str):
        return name
    s = "".join(
        c for c in unicodedata.normalize("NFD", name.upper().strip())
        if unicodedata.category(c) != "Mn"
    )
    if "BOGOTA" in s or s == "BOGOTA":
        return "Bogotá"
    if (
        "SAN ANDRES" in s
        or "ARCHIPIELAGO" in s
        or "PROVIDENCIA" in s
        or "SANTA CATALINA" in s
    ):
        return "Archipiélago de San Andrés"
    if s == "GUAJIRA":
        return "La Guajira"
    if s == "NARINIO":
        return "Nariño"
    if s == "VALLE DEL CAUCA":
        return "Valle del Cauca"
    return name.strip().title()


def main():
    snies_path = RAW / "snies_matricula_20260608.csv"
    if not snies_path.exists():
        print("No se encontró el archivo SNIES raw.")
        return

    try:
        df_snies = pd.read_csv(snies_path, encoding="utf-8", low_memory=False)
    except UnicodeDecodeError:
        df_snies = pd.read_csv(snies_path, encoding="latin1", low_memory=False)
    print(f"SNIES raw: {len(df_snies):,} filas")

    df_snies.columns = [c.strip() for c in df_snies.columns]

    mat_cols = [c for c in df_snies.columns if "MATRI" in c.upper() or "INSCRIP" in c.upper()]
    year_cols = [c for c in df_snies.columns if c.upper() in ("AÑO", "ANO", "A�O")]
    sem_cols = [c for c in df_snies.columns if "SEMESTRE" in c.upper()]
    dpto_cols = [c for c in df_snies.columns if "DEPARTAMENTO" in c.upper() and "OFERTA" in c.upper()]

    mat_col = mat_cols[0]
    dpto_col = dpto_cols[0]
    df_snies[mat_col] = pd.to_numeric(df_snies[mat_col], errors="coerce").fillna(0)

    year_col = year_cols[0]
    sem_col = sem_cols[0]
    latest_year = int(df_snies[year_col].max())
    latest_sem = int(df_snies[df_snies[year_col] == latest_year][sem_col].max())
    df_snies = df_snies[(df_snies[year_col] == latest_year) & (df_snies[sem_col] == latest_sem)].copy()
    print(f"Filtrado a {latest_year}-{latest_sem}: {len(df_snies):,} filas")

    df_snies[dpto_col] = df_snies[dpto_col].apply(_norm_depto_snies)

    # Resumen por departamento
    resumen_dpto = df_snies.groupby(dpto_col, as_index=False)[mat_col].sum()
    resumen_dpto.columns = ["departamento", "matriculados"]
    resumen_dpto["matriculados"] = resumen_dpto["matriculados"].round(2)
    resumen_dpto.to_csv(PROCESSED / "snies_matriculados_departamento.csv", index=False)
    print(f"Guardado snies_matriculados_departamento.csv: {len(resumen_dpto)} deptos")
    print(resumen_dpto.sort_values("matriculados", ascending=False).head(10))

    # Recargar en Supabase
    print("\nRecargando en Supabase...")
    supabase.table("snies_matriculados_departamento").delete().neq("id", 0).execute()
    records = resumen_dpto.to_dict("records")
    BATCH = 500
    for i in range(0, len(records), BATCH):
        batch = records[i : i + BATCH]
        supabase.table("snies_matriculados_departamento").insert(batch).execute()
        print(f"  Insertadas {len(batch)} filas")

    print("Listo.")


if __name__ == "__main__":
    main()
