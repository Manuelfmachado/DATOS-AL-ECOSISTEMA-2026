"""
Procesa el Anexo Estadistico SPE 2015-2023 y genera un CSV limpio de
vacantes por sector economico (CIIU seccion) y anio, a nivel nacional.
"""
import pandas as pd
from pathlib import Path

INPUT = Path("data/raw/spe/anexo_demanda_laboral_2015_2023.xlsx")
OUTPUT = Path("data/processed/spe_vacantes_sector_anual.csv")

MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
         "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

SECCION_NOMBRE = {
    "A": "Agricultura, ganaderia, caza, silvicultura y pesca",
    "B": "Explotacion de minas y canteras",
    "C": "Industrias manufactureras",
    "D": "Suministro de electricidad, gas, vapor y aire acondicionado",
    "E": "Suministro de agua, alcantarillado y saneamiento",
    "F": "Construccion",
    "G": "Comercio al por mayor y al por menor",
    "H": "Transporte y almacenamiento",
    "I": "Alojamiento y servicios de comida",
    "J": "Informacion y comunicaciones",
    "K": "Actividades financieras y de seguros",
    "L": "Actividades inmobiliarias",
    "M": "Actividades profesionales, cientificas y tecnicas",
    "N": "Actividades de servicios administrativos y de apoyo",
    "O": "Administracion publica y defensa",
    "P": "Educacion",
    "Q": "Salud humana y asistencia social",
    "R": "Actividades artistas y de entretenimiento",
    "S": "Otras actividades de servicios",
    "T": "Hogares como empleadores",
    "U": "Organizaciones extraterritoriales",
}


def main():
    print(f"Leyendo {INPUT} ...")
    # Leemos con skiprows=3 para que la primera fila sea el header real:
    # Codigo DIVIPOLA | Departamento | Seccion | Nombre Seccion | Ene | Feb | ... | Total | Ene | Feb | ... (por cada anio)
    df = pd.read_excel(INPUT, sheet_name="Sectores", skiprows=3)
    print(f"Shape: {df.shape}")
    print(f"Columnas: {list(df.columns)[:6]} ...")

    col_dpto_codigo = df.columns[0]
    col_dpto_nombre = df.columns[1]
    col_seccion = df.columns[2]
    col_nombre = df.columns[3]

    # Filtrar solo "Total nacional" (codigo 0)
    df = df[df[col_dpto_codigo] == 0].copy()
    print(f"Filas Total nacional: {len(df)}")

    # Extraer letra de seccion
    df["seccion_letra"] = df[col_seccion].astype(str).str.extract(r"SECCI[OÓ]N\s+([A-Z])", expand=False)
    df = df[df["seccion_letra"].notna()].copy()
    print(f"Filas con seccion valida: {len(df)}")

    # Limpiar el nombre: si el campo trae "SECCION X  ", quitarlo
    df["seccion_nombre"] = df[col_nombre].astype(str).str.replace(
        r"^SECCI[OÓ]N\s+[A-Z]\s+", "", regex=True
    ).str.strip()
    # Si quedo igual al nombre "crudo", usar el mapeo SECCION_NOMBRE
    df["seccion_nombre"] = df.apply(
        lambda r: SECCION_NOMBRE.get(r["seccion_letra"], r["seccion_nombre"]),
        axis=1,
    )

    # Identificar bloques por año. Cada bloque tiene 13 columnas:
    # (Ene, Feb, Mar, Abr, May, Jun, Jul, Ago, Sep, Oct, Nov, Dic, Total)
    # El primer bloque empieza despues de col_nombre (col 3), indice 4.
    # Vamos a recorrer las columnas restantes y detectar cambios.
    # Estrategia: para cada seccion, los valores de las celdas "Total" en el
    # bloque son anuales. Mejor: identificar por nombre de columna exacta.
    cols = list(df.columns)
    print(f"\nColumnas (10-25): {cols[10:25]}")

    # Las columnas de mes se llaman "Ene", "Feb", etc. Total se llama "Total".
    # Estructura: col 4=Ene, 5=Feb, ..., 15=Dic, 16=Total, 17=Ene, 18=Feb, ...
    # Como el sheet tiene 13 cols de datos por anio * 9 anios = 117 cols
    # + 4 cols de identificacion = 121 cols.
    # 117 / 13 = 9 anios (2015-2023). Coincide.

    records = []
    for anio_idx in range(9):
        anio = 2015 + anio_idx
        start = 4 + anio_idx * 13
        # Columnas de meses para este anio
        cols_meses = []
        for mes_idx, mes in enumerate(MESES):
            col_idx = start + mes_idx
            if col_idx < len(cols):
                col_name = cols[col_idx]
                if col_name == mes:
                    cols_meses.append(col_name)
                else:
                    # Buscar por nombre
                    cols_meses.append(col_name)

        if not cols_meses:
            print(f"Anio {anio}: no se encontraron columnas de meses")
            continue

        # Sumar los 12 meses para cada fila
        df[f"total_{anio}"] = df[cols_meses].apply(
            lambda r: pd.to_numeric(r, errors="coerce").sum(), axis=1
        )
        total_nac = df[f"total_{anio}"].sum()
        print(f"Anio {anio}: {len(cols_meses)} meses, total nacional = {total_nac:,.0f} vacantes")

    # Consolidar: una fila por (seccion, anio)
    out_rows = []
    for _, row in df.iterrows():
        seccion = row["seccion_letra"]
        nombre = row["seccion_nombre"]
        for anio_idx in range(9):
            anio = 2015 + anio_idx
            val = row.get(f"total_{anio}", 0)
            if val and val > 0:
                out_rows.append({
                    "seccion": seccion,
                    "seccion_nombre": nombre,
                    "anio": anio,
                    "vacantes": int(round(val)),
                })

    df_out = pd.DataFrame(out_rows)
    print(f"\nTotal registros: {len(df_out)}")
    print(f"Vacantes totales: {df_out['vacantes'].sum():,.0f}")
    print(f"Anios: {sorted(df_out['anio'].unique())}")
    print(f"\nTop 5 secciones por vacantes totales:")
    top5 = df_out.groupby("seccion_nombre")["vacantes"].sum().sort_values(ascending=False).head(5)
    for name, v in top5.items():
        print(f"  {name}: {v:,.0f}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT, index=False)
    print(f"\nGuardado: {OUTPUT}")


if __name__ == "__main__":
    main()
