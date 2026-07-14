"""
Crea la base de datos SQLite desde los CSVs procesados de ALBA.
Ejecutar una sola vez: python crear_sqlite.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "alba_offline.db"

CSV_TO_TABLE = {
    "geih_resumen_nacional.csv": "geih_resumen_nacional",
    "geih_resumen_departamento.csv": "geih_resumen_departamento",
    "geih_salario_ocupacion.csv": "geih_salario_ocupacion",
    "geih_empleo_sector_nacional.csv": "geih_empleo_sector_nacional",
    "geih_empleo_depto_sector.csv": "geih_empleo_depto_sector",
    "geih_tendencia_mensual.csv": "geih_tendencia_mensual",
    "pila_cotizantes.csv": "pila_cotizantes",
    "pila_resumen.csv": "pila_resumen",
    "rues_empresas_nuevas.csv": "rues_empresas_nuevas",
    "rues_sectores_emergentes.csv": "rues_sectores_emergentes",
    "snies_matriculados.csv": "snies_matriculados",
    "snies_programas.csv": "snies_programas",
    "ole_graduados.csv": "ole_graduados",
    "ole_ingresos.csv": "ole_ingresos",
    "sena_programas.csv": "sena_programas",
    "spe_inscritos.csv": "spe_inscritos",
    "dnp_mdm.csv": "dnp_mdm",
    "emicron_micronegocios.csv": "emicron_micronegocios",
    "saber_pro.csv": "saber_pro",
    "esco_ocupaciones.csv": "esco_ocupaciones",
    "esco_habilidades.csv": "esco_habilidades",
    "esco_ocupacion_habilidad.csv": "esco_ocupacion_habilidad",
    "onet_ocupaciones.csv": "onet_ocupaciones",
    "onet_habilidades.csv": "onet_habilidades",
    "onet_ocupacion_habilidad.csv": "onet_ocupacion_habilidad",
    "worldbank_colombia.csv": "worldbank_colombia",
    "geih_extras_departamento.csv": "geih_extras_departamento",
}


def crear_db():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")

    cargadas = 0
    for csv_file, table_name in CSV_TO_TABLE.items():
        csv_path = CSV_DIR / csv_file
        if not csv_path.exists():
            print(f"  [SKIP] {csv_file} no encontrado")
            continue
        try:
            df = pd.read_csv(csv_path, encoding="utf-8", low_memory=False)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            print(f"  [OK] {table_name}: {len(df)} filas")
            cargadas += 1
        except Exception as e:
            print(f"  [ERROR] {csv_file}: {e}")

    conn.execute("PRAGMA optimize")
    conn.close()
    print(f"\nBase de datos creada: {DB_PATH}")
    print(f"Tablas cargadas: {cargadas}")
    return cargadas


if __name__ == "__main__":
    print("=" * 50)
    print("ALBA Offline - Creando base de datos SQLite")
    print("=" * 50)
    crear_db()
    print("\nListo. Ejecuta iniciar_alba.bat para levantar el sistema.")