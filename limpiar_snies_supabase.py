"""
Limpia la tabla snies_matriculados_departamento en Supabase.
Consolida filas duplicadas/mal escritas en 33 departamentos estandarizados.
"""
import os
import unicodedata
from collections import defaultdict
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def _norm(s: str) -> str:
    if not s:
        return ""
    s = s.upper().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def _norm_depto(name: str) -> str:
    s = _norm(name)
    if "BOGOTA" in s or s == "BOGOTA":
        return "BOGOTA"
    if (
        "SAN ANDRES" in s
        or "ARCHIPIELAGO" in s
        or "PROVIDENCIA" in s
        or "SANTA CATALINA" in s
    ):
        return "ARCHIPIELAGO DE SAN ANDRES"
    if s == "GUAJIRA":
        return "LA GUAJIRA"
    if s == "NARINIO":
        return "NARINO"
    return s


def _denorm(key: str) -> str:
    """Devuelve nombre canónico con tildes para mostrar."""
    mapping = {
        "AMAZONAS": "Amazonas",
        "ANTIOQUIA": "Antioquia",
        "ARAUCA": "Arauca",
        "ARCHIPIELAGO DE SAN ANDRES": "Archipiélago de San Andrés",
        "ATLANTICO": "Atlántico",
        "BOGOTA": "Bogotá",
        "BOLIVAR": "Bolívar",
        "BOYACA": "Boyacá",
        "CALDAS": "Caldas",
        "CAQUETA": "Caquetá",
        "CASANARE": "Casanare",
        "CAUCA": "Cauca",
        "CESAR": "Cesar",
        "CHOCO": "Chocó",
        "CORDOBA": "Córdoba",
        "CUNDINAMARCA": "Cundinamarca",
        "GUAINIA": "Guainía",
        "GUAVIARE": "Guaviare",
        "HUILA": "Huila",
        "LA GUAJIRA": "La Guajira",
        "MAGDALENA": "Magdalena",
        "META": "Meta",
        "NARINO": "Nariño",
        "NORTE DE SANTANDER": "Norte de Santander",
        "PUTUMAYO": "Putumayo",
        "QUINDIO": "Quindío",
        "RISARALDA": "Risaralda",
        "SANTANDER": "Santander",
        "SUCRE": "Sucre",
        "TOLIMA": "Tolima",
        "VALLE DEL CAUCA": "Valle del Cauca",
        "VAUPES": "Vaupés",
        "VICHADA": "Vichada",
    }
    return mapping.get(key, key.title())


def main():
    print("Leyendo snies_matriculados_departamento...")
    r = supabase.table("snies_matriculados_departamento").select("*").execute()
    rows = r.data
    print(f"Filas actuales: {len(rows)}")

    consolidado = defaultdict(float)
    for row in rows:
        key = _norm_depto(row.get("departamento", ""))
        consolidado[key] += float(row.get("matriculados") or 0)

    print(f"Departamentos únicos tras normalizar: {len(consolidado)}")
    for k, v in sorted(consolidado.items()):
        print(f"  {_denorm(k)}: {v:,.0f}")

    # Borrar todas las filas viejas
    print("\nBorrando filas antiguas...")
    ids = [row["id"] for row in rows if "id" in row]
    # Supabase limita deletes por id; procesamos en lotes de 500
    BATCH = 500
    for i in range(0, len(ids), BATCH):
        batch = ids[i : i + BATCH]
        supabase.table("snies_matriculados_departamento").delete().in_("id", batch).execute()
        print(f"  Borradas {len(batch)} filas")

    # Insertar filas limpias
    print("\nInsertando filas limpias...")
    nuevas = [
        {"departamento": _denorm(k), "matriculados": round(v, 2)}
        for k, v in consolidado.items()
    ]
    for i in range(0, len(nuevas), BATCH):
        batch = nuevas[i : i + BATCH]
        supabase.table("snies_matriculados_departamento").insert(batch).execute()
        print(f"  Insertadas {len(batch)} filas")

    print("\nLimpieza completada.")


if __name__ == "__main__":
    main()
