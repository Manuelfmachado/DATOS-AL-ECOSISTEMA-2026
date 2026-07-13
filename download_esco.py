"""
Descarga ocupaciones y competencias ESCO en español desde la API oficial.
Guarda resultados intermedios para poder reanudar.
"""
import os
import json
import time
import requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

OUT = Path("data/raw/esco")
OUT.mkdir(parents=True, exist_ok=True)

BASE_API = "https://ec.europa.eu/esco/api"
SCHEME = "http://data.europa.eu/esco/concept-scheme/member-occupations"
LANG = "es"
LIMIT = 50
MAX_WORKERS = 10


def get_json(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                return r.json()
            time.sleep(1)
        except Exception as e:
            if attempt == retries - 1:
                print(f"[ERROR] {url}: {e}")
                return None
            time.sleep(1)
    return None


def fetch_occupation_list():
    """Descarga la lista paginada de ocupaciones ESCO miembro."""
    cache = OUT / "occupations_list.json"
    if cache.exists():
        print(f"[CACHE] Cargando lista de ocupaciones desde {cache}")
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    occupations = []
    url = f"{BASE_API}/resource/occupation?isInScheme={SCHEME}&language={LANG}&offset=0&limit={LIMIT}"
    while url:
        data = get_json(url)
        if not data:
            break
        total = data.get("total", 0)
        offset = data.get("offset", 0)
        count = data.get("count", 0)
        print(f"  Descargando ocupaciones offset={offset}/{total}")
        for concept in data.get("concepts", []):
            occupations.append({
                "uri": concept["uri"],
                "href": concept["href"],
            })
        # Usar el link next proporcionado por el API para evitar doble encoding
        url = data.get("_links", {}).get("next", {}).get("href")
        if not url or count == 0:
            break

    with open(cache, "w", encoding="utf-8") as f:
        json.dump(occupations, f, ensure_ascii=False, indent=2)
    print(f"[OK] Lista de ocupaciones: {len(occupations)}")
    return occupations


def fetch_occupation_detail(uri):
    """Descarga detalle de una ocupación incluyendo skills."""
    cache_file = OUT / "occupations" / f"{uri.split('/')[-1]}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{BASE_API}/resource/occupation?uri={uri}&language={LANG}"
    data = get_json(url)
    if data:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def fetch_skill_detail(uri):
    """Descarga detalle de una competencia ESCO."""
    cache_file = OUT / "skills" / f"{uri.split('/')[-1]}.json"
    if cache_file.exists():
        with open(cache_file, "r", encoding="utf-8") as f:
            return json.load(f)

    url = f"{BASE_API}/resource/skill?uri={uri}&language={LANG}"
    data = get_json(url)
    if data:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return data


def parse_occupation(data):
    """Extrae campos relevantes de una ocupación ESCO."""
    if not data:
        return None
    pref = data.get("preferredLabel", {})
    alt = data.get("alternativeLabel", {})
    desc_obj = data.get("description", {})
    description = desc_obj.get(LANG, desc_obj.get("en", "")) if isinstance(desc_obj, dict) else ""
    if isinstance(description, dict):
        description = description.get("literal", "")

    broader = data.get("broaderIscoGroup", [])
    broader_group = broader[0] if broader else None
    broader_code = broader_group.split("/")[-1] if broader_group else None

    return {
        "uri": data.get("uri"),
        "code": data.get("code"),
        "title": data.get("title", ""),
        "title_es": pref.get("es", data.get("title", "")),
        "description": description,
        "preferred_label": pref,
        "alternative_label": alt,
        "broader_isco_group": broader_code,
    }


def parse_skill(data):
    """Extrae campos relevantes de una competencia ESCO."""
    if not data:
        return None
    pref = data.get("preferredLabel", {})
    alt = data.get("alternativeLabel", {})
    desc_obj = data.get("description", {})
    description = desc_obj.get(LANG, desc_obj.get("en", "")) if isinstance(desc_obj, dict) else ""
    if isinstance(description, dict):
        description = description.get("literal", "")

    return {
        "uri": data.get("uri"),
        "skill_type": data.get("classId", "").split("#")[-1] if data.get("classId") else None,
        "title": data.get("title", ""),
        "title_es": pref.get("es", data.get("title", "")),
        "description": description,
        "preferred_label": pref,
        "alternative_label": alt,
    }


def main():
    print("[1/4] Descargando lista de ocupaciones ESCO...")
    occupations = fetch_occupation_list()

    print(f"\n[2/4] Descargando detalle de {len(occupations)} ocupaciones...")
    occupation_details = []
    skill_uris = set()
    occ_skill_relations = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_uri = {executor.submit(fetch_occupation_detail, occ["uri"]): occ["uri"] for occ in occupations}
        for i, future in enumerate(as_completed(future_to_uri), 1):
            uri = future_to_uri[future]
            data = future.result()
            parsed = parse_occupation(data)
            if parsed:
                occupation_details.append(parsed)
                links = data.get("_links", {})
                for rel_type in ["hasEssentialSkill", "hasOptionalSkill"]:
                    for skill in links.get(rel_type, []):
                        skill_uri = skill["uri"]
                        skill_uris.add(skill_uri)
                        occ_skill_relations.append({
                            "esco_uri": uri,
                            "esco_skill_uri": skill_uri,
                            "relation_type": "essential" if rel_type == "hasEssentialSkill" else "optional",
                        })
            if i % 100 == 0:
                print(f"  Procesadas {i}/{len(occupations)} ocupaciones")

    print(f"\n[3/4] Descargando detalle de {len(skill_uris)} competencias...")
    skill_details = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_uri = {executor.submit(fetch_skill_detail, uri): uri for uri in skill_uris}
        for i, future in enumerate(as_completed(future_to_uri), 1):
            data = future.result()
            parsed = parse_skill(data)
            if parsed:
                skill_details.append(parsed)
            if i % 100 == 0:
                print(f"  Procesadas {i}/{len(skill_uris)} competencias")

    print("\n[4/4] Guardando CSVs procesados...")
    processed_out = Path("data/processed/esco")
    processed_out.mkdir(parents=True, exist_ok=True)

    df_occ = pd.DataFrame(occupation_details)
    df_occ.to_csv(processed_out / "esco_occupations.csv", index=False)
    print(f"[OK] esco_occupations.csv: {len(df_occ)} rows")

    df_skills = pd.DataFrame(skill_details)
    df_skills.to_csv(processed_out / "esco_skills.csv", index=False)
    print(f"[OK] esco_skills.csv: {len(df_skills)} rows")

    df_rel = pd.DataFrame(occ_skill_relations)
    df_rel.to_csv(processed_out / "esco_occupation_skills.csv", index=False)
    print(f"[OK] esco_occupation_skills.csv: {len(df_rel)} rows")

    print("\nListo.")


if __name__ == "__main__":
    main()
