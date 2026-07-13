"""
Evaluación de datasets propuestos para ALBACOLOMBIA.

Salida: lista priorizada y realista para 7 semanas de MVP.
"""

DATASETS = {
    # Prioridad 1: Imprescindibles y accesibles
    "P1": [
        {"nombre": "GEIH", "entidad": "DANE", "dificultad": "Fácil", "uso": "Funciones 1, 2", "accion": "Descargar hoy"},
        {"nombre": "PILA", "entidad": "MinTrabajo", "dificultad": "Fácil", "uso": "Funciones 1, 2, 4", "accion": "Descargar hoy"},
        {"nombre": "SNIES", "entidad": "MinEducación", "dificultad": "Fácil", "uso": "Funciones 2, 3, 4", "accion": "Descargar hoy"},
        {"nombre": "Saber Pro", "entidad": "ICFES", "dificultad": "Fácil", "uso": "Funciones 3, 4", "accion": "Descargar esta semana"},
        {"nombre": "SENA", "entidad": "SENA", "dificultad": "Fácil", "uso": "Funciones 2, 3, 4, 5", "accion": "Descargar esta semana"},
        {"nombre": "SECOP", "entidad": "Colombia Compra", "dificultad": "Media", "uso": "Función 1", "accion": "Descargar muestra esta semana"},
        {"nombre": "RUES", "entidad": "Confecámaras", "dificultad": "Media", "uso": "Funciones 1, 2", "accion": "Descargar muestra esta semana"},
        {"nombre": "ENUT", "entidad": "DANE", "dificultad": "Media", "uso": "Función 1", "accion": "Buscar disponibilidad"},
    ],
    # Prioridad 2: Importantes pero difíciles
    "P2": [
        {"nombre": "SPADIES", "entidad": "MinEducación", "dificultad": "Difícil", "uso": "Función 3", "accion": "Buscar acceso; si no hay, usar SNIES como proxy"},
        {"nombre": "Cuentas Nacionales Departamentales", "entidad": "DANE", "dificultad": "Media", "uso": "Funciones 1, 2", "accion": "Roadmap Fase 2"},
        {"nombre": "Proyecciones de población", "entidad": "DANE", "dificultad": "Fácil", "uso": "Funciones 1, 2", "accion": "Opcional esta semana"},
    ],
    # Prioridad 3: Roadmap / post-concurso
    "P3": [
        {"nombre": "Supersociedades", "entidad": "Supersociedades", "dificultad": "Difícil", "uso": "Funciones 1, 2", "accion": "Roadmap"},
        {"nombre": "DIAN", "entidad": "DIAN", "dificultad": "Difícil", "uso": "Función 1", "accion": "Roadmap"},
        {"nombre": "MinTIC - Encuesta TIC", "entidad": "MinTIC", "dificultad": "Difícil", "uso": "Función 1", "accion": "Roadmap"},
        {"nombre": "MinCiencias - Patentes", "entidad": "MinCiencias", "dificultad": "Difícil", "uso": "Función 1", "accion": "Roadmap"},
        {"nombre": "Migración Colombia", "entidad": "Migración", "dificultad": "Difícil", "uso": "Función 1", "accion": "Roadmap"},
        {"nombre": "Banco de la República", "entidad": "BanRep", "dificultad": "Media", "uso": "Funciones 1, 2", "accion": "Roadmap"},
        {"nombre": "DNP - SISBEN/IPM", "entidad": "DNP", "dificultad": "Media", "uso": "Funciones 1, 7", "accion": "Roadmap"},
    ],
    # Datos a curar manualmente para el demo
    "MANUAL": [
        {"nombre": "Ofertas laborales de ejemplo", "cantidad": "30-50", "uso": "NLP skills + entrevistas", "accion": "Curar hoy"},
        {"nombre": "Pensums universitarios", "cantidad": "5-10 programas", "uso": "Comparar con skills", "accion": "Curar esta semana"},
    ]
}


def main():
    print("=" * 80)
    print("EVALUACIÓN DE DATASETS PARA ALBACOLOMBIA - MVP 7 SEMANAS")
    print("=" * 80)

    for prioridad, datasets in DATASETS.items():
        if prioridad == "P1":
            titulo = "PRIORIDAD 1: IMPRESCINDIBLES (descargar en las primeras 2 semanas)"
        elif prioridad == "P2":
            titulo = "PRIORIDAD 2: IMPORTANTES PERO DIFÍCILES (intentar, no bloqueantes)"
        elif prioridad == "P3":
            titulo = "PRIORIDAD 3: ROADMAP (no bloquear el MVP)"
        else:
            titulo = "DATOS MANUALES PARA EL DEMO"

        print(f"\n{titulo}")
        print("-" * 80)

        for ds in datasets:
            print(f"\n• {ds['nombre']}")
            print(f"  Entidad: {ds.get('entidad', ds.get('cantidad', 'N/A'))}")
            if 'dificultad' in ds:
                print(f"  Dificultad: {ds['dificultad']}")
            print(f"  Uso: {ds['uso']}")
            print(f"  Acción: {ds['accion']}")

    print("\n" + "=" * 80)
    print("RECOMENDACIÓN FINAL")
    print("=" * 80)
    print("Para el MVP de 7 semanas, enfocarse SOLO en:")
    print("  1. GEIH, PILA, SNIES, Saber Pro (descargar en los primeros 3 días)")
    print("  2. SENA, SECOP muestra, RUES muestra, ENUT (primera semana)")
    print("  3. SPADIES: buscar; si no se consigue, usar SNIES como proxy de deserción")
    print("  4. Todo lo demás: ROADMAP o mencionarlo en el pitch")
    print("  5. Curar manualmente 30-50 vacantes y 5-10 pensums para el demo")
    print("=" * 80)


if __name__ == "__main__":
    main()
