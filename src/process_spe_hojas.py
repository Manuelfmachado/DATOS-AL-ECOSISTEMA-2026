"""
Procesa multiples hojas del Anexo SPE 2015-2023 y genera CSVs limpios.
Hojas procesadas: Ocupaciones, Salarios, Educacion, Experiencia.
Cada una con series anuales (suma de los 12 meses) + nivel nacional.
"""
import pandas as pd
from pathlib import Path

INPUT = Path("data/raw/spe/anexo_demanda_laboral_2015_2023.xlsx")
OUT_DIR = Path("data/processed")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def parsear_sheet(sheet_name, col_id_name, n_anios=9, col_tercera=None):
    """Parser generico para las hojas del SPE.
    Asume estructura: cod_dpto | dpto | <id_dim> | <nombre_dim> | Ene..Dic | Total | (repetir 9x)
    Devuelve DataFrame con una fila por (cod_dpto, dpto, id_dim) y col total_<anio> para cada anio.
    """
    print(f"\n=== Procesando {sheet_name} ===")
    df = pd.read_excel(INPUT, sheet_name=sheet_name, skiprows=3)
    print(f"  Shape: {df.shape}")

    # Filtrar solo "Total nacional" (codigo 0 o string "TN")
    df = df[(df.iloc[:, 0] == 0) | (df.iloc[:, 0] == "TN")].copy()
    print(f"  Filas Total nacional: {len(df)}")

    # Columnas de identificacion
    col_dpto = df.columns[1]
    col_id = df.columns[2]   # ej: ocupacion, nivel educativo
    col_nombre = df.columns[3]  # ej: Grupo ocupacional, nivel educ nombre

    # Identificar bloques por anio. Estructura: tras las 4 cols de id, vienen
    # 13 cols por anio (12 meses + Total), repetido n_anios veces.
    # Los anios 2015-2023 estan en la primera fila.
    cols = list(df.columns)
    col_anio_marker = 4  # el primer anio (2015) esta en esta columna

    # Construir diccionario {anio: [cols_meses]}
    year_cols = {}
    for anio_idx in range(n_anios):
        anio = 2015 + anio_idx
        start = col_anio_marker + anio_idx * 13
        cols_meses = []
        for mes_idx, mes in enumerate(MESES):
            col_idx = start + mes_idx
            if col_idx < len(cols):
                col_name = cols[col_idx]
                if col_name in MESES:
                    cols_meses.append(col_name)
                else:
                    # Tomar el nombre que sea (puede ser Total)
                    cols_meses.append(col_name)
        if len(cols_meses) == 12:
            # Sumar 12 meses
            df[f"total_{anio}"] = df[cols_meses].apply(
                lambda r: pd.to_numeric(r, errors="coerce").sum(), axis=1
            )
            total_nac = df[f"total_{anio}"].sum()
            print(f"  Anio {anio}: 12 meses, total nacional = {total_nac:,.0f}")
            year_cols[anio] = f"total_{anio}"

    # Construir DataFrame final
    out = df[[col_dpto, col_id, col_nombre]].copy()
    out.columns = ["departamento", "id_dim", "nombre_dim"]
    for anio, col in year_cols.items():
        out[f"total_{anio}"] = df[col]
    # Limpiar
    out = out.dropna(subset=["nombre_dim"])
    return out


def guardar(df, name, key="id_dim"):
    path = OUT_DIR / f"spe_{name}.csv"
    df.to_csv(path, index=False)
    print(f"  Guardado: {path} ({len(df)} filas)")
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # === Ocupaciones (CIUO 08) ===
    df_ocu = parsear_sheet("Ocupaciones", "ocupacion")
    guardar(df_ocu, "ocupaciones_anual")

    # === Salarios ===
    df_sal = parsear_sheet("Salarios", "rango_salario")
    guardar(df_sal, "salarios_anual")

    # === Educacion ===
    df_edu = parsear_sheet("Educación", "nivel_educativo")
    guardar(df_edu, "educacion_anual")

    # === Experiencia ===
    df_exp = parsear_sheet("Experiencia", "experiencia")
    guardar(df_exp, "experiencia_anual")


if __name__ == "__main__":
    main()
