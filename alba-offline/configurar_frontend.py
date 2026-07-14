"""
Script de configuracion del frontend offline.
Modifica el api.ts para apuntar a localhost:8080 en lugar del proxy de Vite.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FE = ROOT / "frontend"
API_FILE = FE / "src" / "services" / "api.ts"

OFFLINE_BASE = """const API_BASE = 'http://localhost:8080/api'
"""

if API_FILE.exists():
    content = API_FILE.read_text(encoding="utf-8")
    if "localhost:8080" not in content:
        import re
        content = re.sub(
            r"const API_BASE.*",
            OFFLINE_BASE.strip(),
            content,
            count=1,
        )
        API_FILE.write_text(content, encoding="utf-8")
        print(f"  [OK] api.ts configurado para offline (localhost:8080)")
    else:
        print(f"  [OK] api.ts ya configurado para offline")
else:
    print(f"  [SKIP] api.ts no encontrado")