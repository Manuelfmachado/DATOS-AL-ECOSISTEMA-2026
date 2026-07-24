"""
Procesa el Anexo SPE 2015-2023 extrayendo el DETALLE por departamento + ocupacion.
Genera un CSV con ~120K filas (411 ocupaciones x 33 deptos x 9 anios).
"""
import pandas as pd
from pathlib import Path

INPUT = Path("data/raw/spe/anexo_demanda_laboral_2015_2023.xlsx")
OUT = Path("data/processed/spe_ocupaciones_detalle_anual.csv")
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def main():
    print("Leyendo Ocupaciones (detalle por depto)...")
    df = pd.read_excel(INPUT, sheet_name="Ocupaciones", skiprows=3)
    print(f"Shape: {df.shape}")

    # Filtrar filas con codigo de departamento valido (1-99)
    col_dpto = df.columns[0]
    col_dpto_nombre = df.columns[1]
    col_digito = df.columns[2]
    col_ocupacion = df.columns[3]

    # Mantener solo filas con codigo de depto numerico 1-99
    mask = df[col_dpto].apply(lambda x: isinstance(x, (int, float)) and 1 <= x <= 99)
    df = df[mask].copy()
    print(f"Filas con depto valido: {len(df)}")

    # Columnas de cada anio
    cols = list(df.columns)
    col_anio_marker = 4

    # Para cada anio, sumar los 12 meses
    year_data = {}
    for anio_idx in range(9):
        anio = 2015 + anio_idx
        start = col_anio_marker + anio_idx * 13
        cols_meses = []
        for mes_idx in range(12):
            col_idx = start + mes_idx
            if col_idx < len(cols):
                cols_meses.append(cols[col_idx])
        if len(cols_meses) == 12:
            df[f"total_{anio}"] = df[cols_meses].apply(
                lambda r: pd.to_numeric(r, errors="coerce").sum(), axis=1
            )
            year_data[anio] = f"total_{anio}"
            tot = df[f"total_{anio}"].sum()
            print(f"  Anio {anio}: {len(df)} filas, total nacional = {tot:,.0f}")

    # Construir DataFrame final
    out = df[[col_dpto, col_dpto_nombre, col_digito, col_ocupacion]].copy()
    out.columns = ["dpto_codigo", "departamento", "ciuo_digito", "ocupacion"]
    for anio, col in year_data.items():
        out[f"total_{anio}"] = df[col]

    # Filtrar filas con datos
    out = out[out["total_2023"] > 0].copy()
    print(f"\nFilas con datos: {len(out)}")

    # Top 10 ocupaciones 2023
    top = out.groupby("ocupacion")["total_2023"].sum().sort_values(ascending=False).head(10)
    print("\nTop 10 ocupaciones 2023:")
    for o, v in top.items():
        print(f"  {o}: {v:,.0f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(f"\nGuardado: {OUT} ({OUT.stat().st_size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    main()
