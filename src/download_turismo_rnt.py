"""
Descarga el Registro Nacional de Turismo (RNT) - MinCIT desde datos.gov.co (API Socrata).

Dataset: thwd-ivmp (Registro Nacional de Turismo - RNT)
~15-20K establecimientos turisticos por municipio/categoria/subcategoria
con camas, habitaciones, empleados y estado.

Salida: data/raw/rnt_establecimientos.csv
"""
import urllib.request
import json
import os
import time
import csv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

RESOURCE_ID = 'thwd-ivmp'
API_URL = f'https://www.datos.gov.co/resource/{RESOURCE_ID}.json'
OUT_CSV = os.path.join(RAW_DIR, 'rnt_establecimientos.csv')

PAGE_SIZE = 5000


def fetch_page(offset: int, limit: int) -> list:
    url = f'{API_URL}?$limit={limit}&$offset={offset}&$order=codigo_rnt'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode('utf-8'))


def main():
    print('Descargando Registro Nacional de Turismo (RNT) - MinCIT')
    print('=' * 70)

    all_rows = []
    offset = 0
    page = 1
    while True:
        try:
            rows = fetch_page(offset, PAGE_SIZE)
        except Exception as e:
            print(f'  [ERROR] pagina {page} (offset {offset}): {e}')
            # Reintento
            time.sleep(5)
            try:
                rows = fetch_page(offset, PAGE_SIZE)
            except Exception as e2:
                print(f'  [FAIL] reintento tambien fallo: {e2}')
                break

        if not rows:
            print(f'  Pagina {page}: 0 filas (fin)')
            break

        all_rows.extend(rows)
        print(f'  Pagina {page}: +{len(rows)} filas (total {len(all_rows):,})')
        offset += len(rows)
        page += 1
        if len(rows) < PAGE_SIZE:
            break
        time.sleep(0.5)

    if not all_rows:
        print('[FAIL] No se descargaron datos')
        return

    # Resolver columnas: union de todas las keys
    fieldnames = []
    seen = set()
    for r in all_rows:
        for k in r.keys():
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)

    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        w.writeheader()
        for r in all_rows:
            # Socrata devuelve :@computed_region_* que ignoramos via extrasaction
            w.writerow(r)

    size_kb = os.path.getsize(OUT_CSV) / 1024
    print('=' * 70)
    print(f'[OK] {OUT_CSV}')
    print(f'     {len(all_rows):,} establecimientos, {len(fieldnames)} columnas, {size_kb:.0f} KB')

    # Resumen rapido por categoria
    from collections import Counter
    cats = Counter(r.get('categoria', 'NO ESPECIFICADA') for r in all_rows)
    print('\nTop categorias:')
    for cat, n in cats.most_common(10):
        print(f'  {n:>6,}  {cat}')


if __name__ == '__main__':
    main()