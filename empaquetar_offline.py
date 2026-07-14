"""
Prepara el paquete ALBA Offline:
1. Copia CSVs procesados a alba-offline/data/processed/
2. Copia predicciones JSON
3. Compila el frontend y copia el build
4. Crea el ZIP final

Uso: python empaquetar_offline.py
"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFLINE = ROOT / "alba-offline"


def copiar_datos():
    src = ROOT / "data" / "processed"
    dst = OFFLINE / "data" / "processed"
    dst.mkdir(parents=True, exist_ok=True)
    if src.exists():
        copiados = 0
        for f in src.glob("*.csv"):
            shutil.copy2(f, dst / f.name)
            copiados += 1
        pred = src / "predicciones_mundiales.json"
        if pred.exists():
            shutil.copy2(pred, dst / pred.name)
        print(f"  [OK] {copiados} CSVs + predicciones copiados")
    else:
        print("  [WARN] No se encontro data/processed/")


def compilar_frontend():
    """
    ALBA Offline ya tiene un frontend HTML estatico en alba-offline/frontend/index.html.
    No necesita compilacion npm. Solo verificamos que existe.
    """
    fe = OFFLINE / "frontend" / "index.html"
    if fe.exists():
        size_kb = fe.stat().st_size / 1024
        print(f"  [OK] Frontend estatico encontrado ({size_kb:.1f} KB)")
    else:
        print("  [FALTA] frontend/index.html no encontrado")


def main():
    print("=" * 55)
    print("ALBA Offline - Empaquetando")
    print("=" * 55)

    print("\n1. Copiando datos procesados...")
    copiar_datos()

    print("\n2. Compilando frontend...")
    compilar_frontend()

    print("\n3. Verificando estructura...")
    for p in ["backend/app/main.py", "iniciar_alba.bat", "requirements.txt",
              "descargar_modelos.py", "crear_sqlite.py", "README_OFFLINE.txt"]:
        if (OFFLINE / p).exists():
            print(f"  [OK] {p}")
        else:
            print(f"  [FALTA] {p}")

    print("\n4. Creando ZIP...")
    zip_path = ROOT / "ALBA-Offline-v1.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(ROOT / "ALBA-Offline-v1"), "zip", OFFLINE)
    size_mb = zip_path.stat().st_size / 1e6
    print(f"  [OK] {zip_path.name} ({size_mb:.1f} MB)")

    print("\n" + "=" * 55)
    print("Paquete listo: ALBA-Offline-v1.zip")
    print("Distribuye este ZIP a los usuarios.")
    print("=" * 55)


if __name__ == "__main__":
    main()