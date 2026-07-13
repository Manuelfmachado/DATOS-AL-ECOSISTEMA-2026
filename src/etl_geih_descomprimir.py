"""
ETL ALBA - Paso 0: Descomprimir solo los CSV de los 52 ZIPs de GEIH
Extrae los 8 archivos CSV de cada ZIP a una carpeta estructurada por ano/mes.
Ignora archivos SAV (SPSS) y DTA (Stata) para ahorrar espacio (~1.7 GB -> ~52 MB por mes).

Maneja 3 estructuras de ZIP encontradas en el DANE:
1. csv_directo: Los CSV estan directamente en el ZIP (41 ZIPs)
2. csv_zip_dentro: Hay un CSV.zip dentro del ZIP que contiene los CSV (9 ZIPs)
3. csv_zip_subcarpeta: CSV.zip dentro de una subcarpeta (2 ZIPs)
"""
import zipfile
import os
import time
import io

ORIGEN = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\GEIH_2026_DANE'
DESTINO = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\data\raw\geih'

MODULOS = [
    ('caracteristicas', 'Caracteristicas generales'),
    ('hogar', 'Datos del hogar'),
    ('fuerza', 'Fuerza de trabajo'),
    ('no ocupado', 'No ocupados'),
    ('ocupado', 'Ocupados'),
    ('otras formas', 'Otras formas'),
    ('otros ingresos', 'Otros ingresos'),
    ('migracion', 'Migracion'),
]


def normalizar_nombre_archivo(filename):
    """Dado el nombre del archivo CSV, devuelve el modulo normalizado o None."""
    # Normalizar encoding: los nombres vienen en latin1 con \xed, \xf3, \xa0
    try:
        fname_decoded = filename.encode('raw_unicode_escape').decode('latin1', errors='ignore')
    except Exception:
        fname_decoded = filename
    # Quitar tildes y normalizar espacios
    fname_lower = fname_decoded.lower()
    fname_lower = fname_lower.replace('\xa0', ' ')
    tildes = {'\xe1': 'a', '\xe9': 'e', '\xed': 'i', '\xf3': 'o', '\xfa': 'u',
              '\xc1': 'a', '\xc9': 'e', '\xcd': 'i', '\xd3': 'o', '\xda': 'u',
              '\xf1': 'n', '\xd1': 'n'}
    for k, v in tildes.items():
        fname_lower = fname_lower.replace(k, v)
    for clave, modulo in MODULOS:
        if clave in fname_lower:
            return modulo
    return None


def extraer_csv_de_zip(zf, entry_name, carpeta_destino):
    """Extrae un CSV de un ZipFile al destino con nombre normalizado."""
    modulo = normalizar_nombre_archivo(entry_name)
    if modulo is None:
        return False
    dest_name = f'{modulo}.csv'
    dest_path = os.path.join(carpeta_destino, dest_name)
    with zf.open(entry_name) as src, open(dest_path, 'wb') as dst:
        dst.write(src.read())
    return True


def extraer_csv_de_zip_anidado(zf, csv_zip_entry, carpeta_destino):
    """Lee un CSV.zip anidado dentro del ZIP principal y extrae sus CSV."""
    count = 0
    with zf.open(csv_zip_entry) as src:
        csv_zip_data = src.read()
    with zipfile.ZipFile(io.BytesIO(csv_zip_data), 'r') as inner_zf:
        for info in inner_zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.lower().endswith('.csv'):
                continue
            modulo = normalizar_nombre_archivo(info.filename)
            if modulo is None:
                continue
            dest_name = f'{modulo}.csv'
            dest_path = os.path.join(carpeta_destino, dest_name)
            with inner_zf.open(info) as src2, open(dest_path, 'wb') as dst2:
                dst2.write(src2.read())
            count += 1
    return count


def procesar_zip(zip_path, ano, mes):
    """Extrae solo los CSV de un ZIP a la carpeta destino."""
    carpeta_destino = os.path.join(DESTINO, str(ano), f'{ano}-{mes:02d}')
    os.makedirs(carpeta_destino, exist_ok=True)

    csv_existentes = [f for f in os.listdir(carpeta_destino) if f.endswith('.csv')]
    if len(csv_existentes) >= 8:
        return 'skip', len(csv_existentes)

    extraidos = 0
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            fname = info.filename
            fname_lower = fname.lower()

            # Caso 1: CSV directo
            if fname_lower.endswith('.csv'):
                if extraer_csv_de_zip(zf, fname, carpeta_destino):
                    extraidos += 1

            # Caso 2 y 3: CSV.zip anidado (puede llamarse CSV.zip, CSV 4.zip, etc.)
            elif 'csv' in fname_lower and fname_lower.endswith('.zip'):
                extraidos += extraer_csv_de_zip_anidado(zf, fname, carpeta_destino)

    return 'ok', extraidos


def parse_nombre_zip(nombre):
    """Extrae ano y mes del nombre del ZIP."""
    nombre = nombre.lower()
    ano = None
    for y in ['2026', '2025', '2024', '2023', '2022']:
        if y in nombre:
            ano = int(y)
            break
    if ano is None:
        return None, None

    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12,
        'ene_': 1, 'feb_': 2, 'mar_': 3, 'abr_': 4,
        'may_': 5, 'jun_': 6, 'jul_': 7, 'ago_': 8,
        'sep_': 9, 'oct_': 10, 'nov_': 11, 'dic_': 12,
    }
    mes = None
    for mname, mnum in meses.items():
        if mname in nombre:
            mes = mnum
            break
    return ano, mes


def main():
    os.makedirs(DESTINO, exist_ok=True)
    # Limpiar carpeta destino para re-procesar correctamente
    import shutil
    if os.path.exists(DESTINO):
        shutil.rmtree(DESTINO)
    os.makedirs(DESTINO, exist_ok=True)

    zips = sorted([f for f in os.listdir(ORIGEN) if f.endswith('.zip')])
    print(f'Total ZIPs a procesar: {len(zips)}')
    print('=' * 70)

    ok = 0
    skip = 0
    fail = 0
    total_csv = 0
    problemas = []

    t0 = time.time()

    for i, zip_name in enumerate(zips, 1):
        ano, mes = parse_nombre_zip(zip_name)
        if ano is None or mes is None:
            print(f'[{i:2d}/{len(zips)}] [SKIP] {zip_name} - no se pudo parsear')
            skip += 1
            continue

        zip_path = os.path.join(ORIGEN, zip_name)
        status, n = procesar_zip(zip_path, ano, mes)

        if status == 'skip':
            print(f'[{i:2d}/{len(zips)}] [SKIP] {ano}-{mes:02d} ya tiene {n} CSV')
            total_csv += n
        elif status == 'ok':
            if n == 8:
                print(f'[{i:2d}/{len(zips)}] [OK]   {ano}-{mes:02d} extraidos {n}/8 CSV')
            else:
                print(f'[{i:2d}/{len(zips)}] [WARN] {ano}-{mes:02d} extraidos {n}/8 CSV (faltan {8-n})')
                problemas.append((ano, mes, n))
            total_csv += n
            ok += 1
        else:
            print(f'[{i:2d}/{len(zips)}] [FAIL] {zip_name}')
            fail += 1

    elapsed = time.time() - t0
    print('=' * 70)
    print(f'Resumen: {ok} procesados, {skip} omitidos, {fail} errores')
    print(f'Total CSV extraidos: {total_csv} / {len(zips)*8} esperados')
    print(f'Tiempo: {elapsed:.1f}s')
    if problemas:
        print(f'\nMeses con CSV incompletos ({len(problemas)}):')
        for ano, mes, n in problemas:
            print(f'  {ano}-{mes:02d}: {n}/8 CSV')

    total_size = 0
    for root, dirs, files in os.walk(DESTINO):
        for f in files:
            if f.endswith('.csv'):
                total_size += os.path.getsize(os.path.join(root, f))
    print(f'Espacio en disco: {total_size / 1e6:.0f} MB ({total_size / 1e9:.2f} GB)')


if __name__ == '__main__':
    main()