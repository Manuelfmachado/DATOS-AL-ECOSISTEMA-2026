"""
Descarga colocaciones de credito agropecuario (FINAGRO) desde datos.gov.co (API Socrata).

Datasets:
- w3uf-w9ey: Colocaciones de Credito Sector Agropecuario 2021-2024
- hbaj-th4x: Colocaciones de Credito Sector Agropecuario 2020

Para Emprende IA solo necesitamos agregaciones por departamento/cadena/linea/ano,
asi que usamos SoQL $select + $group para reducir el volumen descargado
(cada dataset individual tiene cientos de miles de filas).

Salidas:
- data/raw/finagro_colocaciones_detalle.csv   (agregado por dpto x cadena x ano)
- data/raw/finagro_colocaciones_resumen.csv    (totales anuales)
"""
import urllib.request
import urllib.parse
import json
import os
import time
import csv

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE, 'data', 'raw')
os.makedirs(RAW_DIR, exist_ok=True)

DATASETS = [
    # (id, anio_inicio, anio_fin, descripcion)
    ('w3uf-w9ey', 2021, 2024, 'Colocaciones Agro 2021-2024'),
    ('hbaj-th4x', 2020, 2020, 'Colocaciones Agro 2020'),
]

OUT_DETALLE = os.path.join(RAW_DIR, 'finagro_colocaciones_detalle.csv')
OUT_RESUMEN = os.path.join(RAW_DIR, 'finagro_colocaciones_resumen.csv')

PAGE_SIZE = 50000


def fetch_page(resource_id: str, query: str, offset: int, limit: int) -> list:
    # query ya viene sin URL-encode; lo construimos y codificamos completo
    full = f'{query}&$limit={limit}&$offset={offset}'
    url = f'https://www.datos.gov.co/resource/{resource_id}.json?{urllib.parse.quote(full, safe="=&$,")}'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read().decode('utf-8'))


def fetch_aggregated(resource_id: str, select_clause: str, group_clause: str) -> list:
    """Descarga un agregado SoQL completo con paginacion."""
    query = f'$select={select_clause}&$group={group_clause}&$order={group_clause}'
    all_rows = []
    offset = 0
    page = 1
    while True:
        try:
            rows = fetch_page(resource_id, query, offset, PAGE_SIZE)
        except Exception as e:
            print(f'  [ERROR] pagina {page}: {e}')
            time.sleep(5)
            try:
                rows = fetch_page(resource_id, query, offset, PAGE_SIZE)
            except Exception as e2:
                print(f'  [FAIL] reintento: {e2}')
                break

        if not rows:
            break

        all_rows.extend(rows)
        print(f'  [{resource_id}] pagina {page}: +{len(rows)} (total {len(all_rows):,})')
        offset += len(rows)
        page += 1
        if len(rows) < PAGE_SIZE:
            break
        time.sleep(0.3)
    return all_rows


def main():
    print('Descargando FINAGRO - Colocaciones Credito Agropecuario')
    print('=' * 70)

    # Agregado por departamento x destino_de_credito x ano (destino_de_credito trae el cultivo
    # real: "132310 Sostenimiento cafe", "253400 Vientres bovinos", etc.)
    select = ('departamento_inversion,destino_de_credito,a_o,'
              'SUM(colocacion) AS total_colocacion,'
              'SUM(valor_inversion) AS total_inversion,'
              'COUNT(*) AS num_operaciones')
    group = 'departamento_inversion,destino_de_credito,a_o'

    all_detalle = []
    for resource_id, anio_ini, anio_fin, desc in DATASETS:
        print(f'\n>> {desc} ({resource_id})')
        rows = fetch_aggregated(resource_id, select, group)
        # Normalizar nombre de columna de ano (a_o -> ano)
        for r in rows:
            r['ano'] = r.pop('a_o', None)
        all_detalle.extend(rows)
        print(f'   {len(rows):,} grupos')

    # Guardar detalle
    if all_detalle:
        fieldnames = ['departamento_inversion', 'destino_de_credito', 'ano',
                      'total_colocacion', 'total_inversion', 'num_operaciones']
        with open(OUT_DETALLE, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(all_detalle)
        print(f'\n[OK] {OUT_DETALLE}: {len(all_detalle):,} filas, '
              f'{os.path.getsize(OUT_DETALLE)/1024:.0f} KB')

    # Agregado resumen nacional por ano
    select_res = ('a_o,'
                  'SUM(colocacion) AS total_colocacion,'
                  'SUM(valor_inversion) AS total_inversion,'
                  'COUNT(*) AS num_operaciones,'
                  'COUNT(DISTINCT departamento_inversion) AS departamentos_atendidos')
    group_res = 'a_o'
    all_resumen = []
    for resource_id, anio_ini, anio_fin, desc in DATASETS:
        print(f'\n>> Resumen {desc}')
        rows = fetch_aggregated(resource_id, select_res, group_res)
        for r in rows:
            r['ano'] = r.pop('a_o', None)
        all_resumen.extend(rows)

    if all_resumen:
        fieldnames = ['ano', 'total_colocacion', 'total_inversion',
                      'num_operaciones', 'departamentos_atendidos']
        with open(OUT_RESUMEN, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(all_resumen)
        print(f'\n[OK] {OUT_RESUMEN}: {len(all_resumen)} filas')
        for r in sorted(all_resumen, key=lambda x: x.get('ano') or 0):
            print(f'  {r.get("ano")}: ${int(r.get("total_colocacion") or 0):,} '
                  f'colocados, {int(r.get("num_operaciones") or 0):,} operaciones')


if __name__ == '__main__':
    main()