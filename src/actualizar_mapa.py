"""
Actualiza alba_slides.html con:
1. Mapa de Colombia real con paths SVG (embebidos)
2. Colores sólidos en las gráficas
3. Navegación en pie de página sin solapamiento
"""
import json
from pathlib import Path

ROOT = Path("C:/Users/crist/Documents/PROYECTOS/DATOS AL ECOSISTEMA 2026")
RESOURCES = ROOT / "recursos"
HTML_PATH = RESOURCES / "alba_slides.html"
JSON_PATH = RESOURCES / "colombia_svg_paths.json"

with open(JSON_PATH, encoding="utf-8") as f:
    deptos_json = json.load(f)
deptos_str = json.dumps(deptos_json, ensure_ascii=False, separators=(",", ":"))

# Generar el bloque JS que reemplaza el código de círculos
new_map_js = '''        // ===== Mapa de Colombia con paths SVG reales =====
        const COLOMBIA_DEPTOS = ''' + deptos_str + ''';
        const mapSvg = document.getElementById('colombiaMap');
        if (mapSvg) {
            // Datos de empleo por departamento (top 10 = valores altos)
            const empleo = {
                "Bogot\u00e1": 4.3, "Antioquia": 3.4, "Valle del Cauca": 2.3,
                "Cundinamarca": 1.8, "Atl\u00e1ntico": 1.3, "Santander": 1.1,
                "Bol\u00edvar": 1.0, "Nari\u00f1o": 0.9, "C\u00f3rdoba": 0.8,
                "Norte de Santander": 0.7, "Cauca": 0.7, "Tolima": 0.6,
                "Boyac\u00e1": 0.6, "Magdalena": 0.6, "Cesar": 0.5,
                "Caldas": 0.5, "Huila": 0.5, "Meta": 0.5, "Risaralda": 0.4,
                "Quind\u00edo": 0.3, "Sucre": 0.3, "La Guajira": 0.3,
                "Caquet\u00e1": 0.2, "Casanare": 0.2, "Putumayo": 0.2,
                "Choc\u00f3": 0.2, "Arauca": 0.15, "Guaviare": 0.1,
                "Amazonas": 0.08, "Vichada": 0.06, "Guain\u00eda": 0.05,
                "Vaup\u00e9s": 0.05, "San Andr\u00e9s y Providencia": 0.04
            };
            const maxEmpleo = 4.3;
            let html = '';
            COLOMBIA_DEPTOS.forEach(d => {
                const v = empleo[d.name] || 0;
                const intensity = v / maxEmpleo;
                const opacity = 0.15 + intensity * 0.75;
                d.paths.forEach(p => {
                    html += '<polygon points="' + p + '" fill="rgba(197,164,74,' + opacity.toFixed(2) + ')" stroke="#0a0e1a" stroke-width="0.6"/>';
                });
            });
            mapSvg.innerHTML = html;
        }'''

# Leer HTML actual
with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()

# Encontrar y reemplazar el bloque del mapa de círculos
import re
pattern = re.compile(
    r"        // ===== Mapa de Colombia.*?mapSvg\.innerHTML = html;\s*\}",
    re.DOTALL
)
new_html = pattern.sub(new_map_js, html, count=1)

if new_html == html:
    print("No se encontró el bloque a reemplazar")
else:
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(new_html)
    print("Mapa de Colombia actualizado con paths SVG reales")
