"""
Descarga EMICRON (Encuesta de Micronegocios) del DANE - 4 anos (2021-2024)
Cada ano tiene 12+ modulos en formato ZIP descargables directamente del DANE.
"""
import urllib.request
import os
import time

DEST = r'C:\Users\crist\Documents\PROYECTOS\DATOS AL ECOSISTEMA 2026\EMICRON_DANE'
os.makedirs(DEST, exist_ok=True)

# URLs de descarga directa del DANE para cada modulo por ano
# Formato: (nombre_archivo, url, ano)
DOWNLOADS = [
    # === 2024 (catalog 875) ===
    ('2024_Capital_Social.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24185', 2024),
    ('2024_Caracteristicas.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24186', 2024),
    ('2024_Costos_Gastos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24187', 2024),
    ('2024_Emprendimiento.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24188', 2024),
    ('2024_Identificacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24189', 2024),
    ('2024_Inclusion_Financiera.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24190', 2024),
    ('2024_Personal_Ocupado.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24192', 2024),
    ('2024_Personal_Propietario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24191', 2024),
    ('2024_Sitio_Ubicacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24193', 2024),
    ('2024_TIC.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24194', 2024),
    ('2024_Ventas_Ingresos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24195', 2024),
    ('2024_Factores_Departamental.zip', 'https://microdatos.dane.gov.co/index.php/catalog/875/download/24196', 2024),

    # === 2023 (catalog 832) ===
    ('2023_Diccionario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23525', 2023),
    ('2023_Factores_Departamental.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/24179', 2023),
    ('2023_Capital_Social.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23526', 2023),
    ('2023_Caracteristicas.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23527', 2023),
    ('2023_Costos_Gastos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23528', 2023),
    ('2023_Emprendimiento.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23529', 2023),
    ('2023_Identificacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23530', 2023),
    ('2023_Inclusion_Financiera.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23531', 2023),
    ('2023_Personal_Ocupado.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23532', 2023),
    ('2023_Sitio_Ubicacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23533', 2023),
    ('2023_TIC.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23534', 2023),
    ('2023_Ventas_Ingresos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23535', 2023),
    ('2023_Personal_Propietario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/832/download/23536', 2023),

    # === 2022 (catalog 796) ===
    ('2022_Diccionario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22665', 2022),
    ('2022_Factores_Departamental.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/23114', 2022),
    ('2022_Capital_Social.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22671', 2022),
    ('2022_Caracteristicas.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22672', 2022),
    ('2022_Costos_Gastos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22673', 2022),
    ('2022_Emprendimiento.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22674', 2022),
    ('2022_Identificacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22675', 2022),
    ('2022_Inclusion_Financiera.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22676', 2022),
    ('2022_Personal_Ocupado.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22677', 2022),
    ('2022_Sitio_Ubicacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22678', 2022),
    ('2022_TIC.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22679', 2022),
    ('2022_Ventas_Ingresos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22680', 2022),
    ('2022_Personal_Propietario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/796/download/22681', 2022),

    # === 2021 (catalog 742) ===
    ('2021_Diccionario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/22750', 2021),
    ('2021_Factores_Departamental.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/23519', 2021),
    ('2021_Caracteristicas.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21252', 2021),
    ('2021_Costos_Gastos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21254', 2021),
    ('2021_Emprendimiento.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21248', 2021),
    ('2021_Identificacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21247', 2021),
    ('2021_Inclusion_Financiera.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21405', 2021),
    ('2021_Personal_Ocupado.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21250', 2021),
    ('2021_Personal_Propietario.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21251', 2021),
    ('2021_Sitio_Ubicacion.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21249', 2021),
    ('2021_TIC.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21253', 2021),
    ('2021_Ventas_Ingresos.zip', 'https://microdatos.dane.gov.co/index.php/catalog/742/download/21255', 2021),
]

def main():
    print(f'Descargando EMICRON - {len(DOWNLOADS)} archivos ZIP')
    print('=' * 70)

    ok = 0
    skip = 0
    fail = 0

    for i, (fname, url, ano) in enumerate(DOWNLOADS, 1):
        path = os.path.join(DEST, fname)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            skip += 1
            continue

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
            with open(path, 'wb') as f:
                f.write(data)
            ok += 1
            print(f'[{i:2d}/{len(DOWNLOADS)}] [OK] {fname} ({len(data)/1024:.0f} KB)')
        except Exception as e:
            fail += 1
            print(f'[{i:2d}/{len(DOWNLOADS)}] [FAIL] {fname}: {e}')

    print('=' * 70)
    print(f'Resumen: {ok} descargados, {skip} omitidos, {fail} errores')

    total = sum(os.path.getsize(os.path.join(DEST, f)) for f in os.listdir(DEST))
    print(f'Total: {len(os.listdir(DEST))} archivos, {total/1e6:.1f} MB')


if __name__ == '__main__':
    main()