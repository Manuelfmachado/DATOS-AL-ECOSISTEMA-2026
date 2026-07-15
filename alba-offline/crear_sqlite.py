"""
Crea la base de datos SQLite desde los CSVs procesados de ALBA.
Ejecutar una sola vez: python crear_sqlite.py
"""
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_DIR = ROOT / "data" / "processed"
DB_PATH = ROOT / "data" / "alba_offline.db"

CSV_TO_TABLE = {
    "geih_resumen_nacional.csv": "geih_resumen_nacional",
    "geih_resumen_departamento.csv": "geih_resumen_departamento",
    "geih_desempleo_departamento.csv": "geih_desempleo_departamento",
    "geih_desempleo_mensual.csv": "geih_desempleo_mensual",
    "geih_salario_ocupacion.csv": "geih_salario_ocupacion",
    "geih_empleo_sector_mensual.csv": "geih_empleo_sector_nacional",
    "geih_empleo_depto_sector.csv": "geih_empleo_depto_sector",
    "geih_informalidad_mensual.csv": "geih_informalidad_mensual",
    "geih_extras_departamento.csv": "geih_extras_departamento",
    "pila_resumen_sector.csv": "pila_cotizantes",
    "pila_resumen_tipo.csv": "pila_resumen_tipo",
    "rues_empresas_nuevas.csv": "rues_empresas_nuevas",
    "rues_resumen_camara_ciiu.csv": "rues_sectores_emergentes",
    "rues_top_sectores_nacional.csv": "rues_top_sectores_nacional",
    "snies_matriculados_departamento.csv": "snies_matriculados_departamento",
    "snies_programas_matriculados.csv": "snies_programas_matriculados",
    "ole_etdh_programas_activos.csv": "sena_programas",
    "ole_etdh_resumen_departamento_area.csv": "ole_etdh_resumen_departamento_area",
    "ole_graduados_por_anio.csv": "ole_graduados",
    "ole_ingresos_por_area.csv": "ole_ingresos",
    "ole_ingresos_por_ies.csv": "ole_ingresos_ies",
    "ole_ingresos_por_nivel.csv": "ole_ingresos_nivel",
    "ole_ingresos_por_programa.csv": "ole_ingresos_programa",
    "sena_programas_activos.csv": "sena_programas_activos",
    "spe_ape_inscritos_ocupacion.csv": "spe_inscritos",
    "spe_ape_inscritos_nivel.csv": "spe_inscritos_nivel",
    "dnp_desempeno_departamento.csv": "dnp_mdm",
    "dnp_medicion_desempeno_municipal.csv": "dnp_medicion_municipal",
    "dnp_medicion_desempeno_ultimo.csv": "dnp_medicion_ultimo",
    "emicron_resumen_nacional.csv": "emicron_micronegocios",
    "emicron_por_departamento.csv": "emicron_por_departamento",
    "emicron_por_sector.csv": "emicron_por_sector",
    "emicron_emprendimiento.csv": "emicron_emprendimiento",
    "emicron_inclusion_financiera.csv": "emicron_inclusion_financiera",
    "saberpro_resumen_programas.csv": "saber_pro",
    "esco_ocupaciones.csv": "esco_ocupaciones",
    "esco_habilidades.csv": "esco_habilidades",
    "esco_ocupacion_habilidades.csv": "esco_ocupacion_habilidad",
    "esco_skill_relations.csv": "esco_skill_relations",
    "esco_habilidades_verdes.csv": "esco_habilidades_verdes",
    "esco_habilidades_digitales.csv": "esco_habilidades_digitales",
    "esco_green_share_ocupaciones.csv": "esco_green_share_ocupaciones",
    "worldbank_colombia.csv": "worldbank_colombia",
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