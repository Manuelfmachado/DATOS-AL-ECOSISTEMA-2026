"""
Mapeo de departamentos de Colombia con su codigo DIVIPOLA oficial.
Fuente: DANE - DIVIPOLA (Division Politico Administrativa de Colombia).
33 departamentos + Distrito Capital.
"""

# Codigo DIVIPOLA (entero) -> nombre oficial del departamento
DIVIPOLA_CODIGO_A_NOMBRE = {
    5: "Antioquia",
    8: "Atlantico",
    11: "Bogota D.C.",
    13: "Bolivar",
    15: "Boyaca",
    17: "Caldas",
    18: "Caqueta",
    19: "Cauca",
    20: "Cauca",  # placeholder legacy, no usar
    21: "Cesar",
    23: "Cordoba",
    25: "Cundinamarca",
    27: "Choco",
    41: "Huila",
    44: "La Guajira",
    47: "Magdalena",
    50: "Meta",
    52: "Narino",
    54: "Norte de Santander",
    63: "Quindio",
    66: "Risaralda",
    68: "Santander",
    70: "Sucre",
    73: "Tolima",
    76: "Valle del Cauca",
    81: "Arauca",
    85: "Casanare",
    86: "Putumayo",
    88: "Archipielago de San Andres, Providencia y Santa Catalina",
    91: "Amazonas",
    94: "Guainia",
    95: "Guaviare",
    97: "Vaupes",
    99: "Vichada",
}

# Nombre normalizado (mayusculas, sin tildes) -> codigo DIVIPOLA
# 33 departamentos de Colombia
DIVIPOLA_NOMBRE_A_CODIGO = {
    "AMAZONAS": 91,
    "ANTIOQUIA": 5,
    "ARAUCA": 81,
    "ARCHIPIELAGO DE SAN ANDRES": 88,
    "ATLANTICO": 8,
    "BOGOTA": 11,
    "BOLIVAR": 13,
    "BOYACA": 15,
    "CALDAS": 17,
    "CAQUETA": 18,
    "CASANARE": 85,
    "CAUCA": 19,
    "CESAR": 21,
    "CHOCO": 27,
    "CORDOBA": 23,
    "CUNDINAMARCA": 25,
    "GUAINIA": 94,
    "GUAVIARE": 95,
    "HUILA": 41,
    "LA GUAJIRA": 44,
    "MAGDALENA": 47,
    "META": 50,
    "NARINO": 52,
    "NORTE DE SANTANDER": 54,
    "PUTUMAYO": 86,
    "QUINDIO": 63,
    "RISARALDA": 66,
    "SANTANDER": 68,
    "SUCRE": 70,
    "TOLIMA": 73,
    "VALLE DEL CAUCA": 76,
    "VAUPES": 97,
    "VICHADA": 99,
}

# Lista de departamentos para selectores: nombre en Title Case + codigo
DEPARTAMENTOS_COLOMBIA = sorted(
    [{"nombre": nombre.title(), "codigo": codigo} for nombre, codigo in DIVIPOLA_NOMBRE_A_CODIGO.items()],
    key=lambda x: x["nombre"],
)


def obtener_codigo_divipola(nombre: str) -> int | None:
    """Devuelve el codigo DIVIPOLA a partir de un nombre de departamento (cualquier capitalizacion o tildes)."""
    import unicodedata

    if not nombre:
        return None
    s = nombre.upper().strip()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    # Casos especiales
    if "BOGOTA" in s:
        return 11
    if "SAN ANDRES" in s or "ARCHIPIELAGO" in s or "PROVIDENCIA" in s:
        return 88
    if s == "GUAJIRA":
        return 44
    if s == "NARINIO":
        return 52
    return DIVIPOLA_NOMBRE_A_CODIGO.get(s)


def obtener_nombre_departamento(codigo: int) -> str:
    """Devuelve el nombre oficial del departamento a partir de su codigo DIVIPOLA."""
    return DIVIPOLA_CODIGO_A_NOMBRE.get(codigo, f"Dpto {codigo}")
