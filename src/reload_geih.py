"""
Recarga limpia de tablas GEIH en Supabase despues de reprocesar con factor de expansion.
"""
import os
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
load_dotenv("backend/.env", override=True)

ROOT = Path.cwd()
PROCESSED = ROOT / "data" / "processed"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("[ERROR] Faltan SUPABASE_URL o SUPABASE_KEY")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def clean_records(path: Path, allowed_columns=None):
    if not path.exists():
        print(f"[SKIP] No existe {path}")
        return []
    df = pd.read_csv(path, encoding="utf-8")
    df.columns = [c.lower().replace(" ", "_").replace("-", "_") for c in df.columns]
    if allowed_columns:
        cols_to_keep = [c for c in df.columns if c in allowed_columns]
        df = df[cols_to_keep]
    df = df.where(pd.notna(df), None)
    df = df.replace([np.inf, -np.inf], None)
    records = df.to_dict("records")
    import math
    for rec in records:
        for k, v in rec.items():
            if isinstance(v, float):
                if math.isnan(v) or math.isinf(v):
                    rec[k] = None
                elif k in ('ocupados', 'no_ocupados'):
                    rec[k] = int(round(v))
                elif k in ('ingreso_promedio', 'ingreso_mediano'):
                    rec[k] = int(round(v))
                elif k in ('tasa_formalidad', 'mujeres_pct'):
                    rec[k] = round(v, 4)
    return records


def reload_table(table_name: str, records: list, batch_size=500):
    if not records:
        print(f"[SKIP] {table_name}: sin registros")
        return
    print(f"\n[>] Truncando {table_name}...")
    supabase.table(table_name).delete().neq("id", 0).execute()
    print(f"[>] Subiendo {len(records)} registros a {table_name}...")
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        try:
            supabase.table(table_name).insert(batch).execute()
            print(f"  [OK] Lote {i // batch_size + 1}: {len(batch)} registros")
        except Exception as e:
            print(f"  [ERROR] Lote {i // batch_size + 1}: {e}")
            raise


def main():
    tables = {
        "geih_resumen_departamento.csv": ("geih_resumen_departamento", None),
        "geih_desempleo_departamento.csv": ("geih_desempleo_departamento", None),
    }
    for csv_file, (table_name, allowed_cols) in tables.items():
        path = PROCESSED / csv_file
        records = clean_records(path, allowed_cols)
        reload_table(table_name, records)
    print("\n[OK] Recarga de GEIH finalizada")


if __name__ == "__main__":
    main()
