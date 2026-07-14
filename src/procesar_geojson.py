import json
from pathlib import Path

ROOT = Path("C:/Users/crist/Documents/PROYECTOS/DATOS AL ECOSISTEMA 2026")
RESOURCES = ROOT / "recursos"

with open(RESOURCES / "colombia_deptos_full.json", encoding="utf-8") as f:
    data = json.load(f)

# Calcular bbox
all_coords = []
for feat in data["features"]:
    geom = feat["geometry"]
    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            for pt in ring:
                all_coords.append(pt)
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                for pt in ring:
                    all_coords.append(pt)

lons = [c[0] for c in all_coords]
lats = [c[1] for c in all_coords]
min_lon, max_lon = min(lons), max(lons)
min_lat, max_lat = min(lats), max(lats)

margin = 0.10
vb_w, vb_h = 420, 420
lon_range = max_lon - min_lon
lat_range = max_lat - min_lat
scale = min((vb_w * (1 - 2*margin)) / lon_range, (vb_h * (1 - 2*margin)) / lat_range)
offset_x = vb_w/2 - ((min_lon + max_lon)/2) * scale
offset_y = vb_h/2 + ((min_lat + max_lat)/2) * scale

def project_ring(ring):
    if len(ring) < 4:
        return None
    step = max(1, len(ring) // 35)
    pts = ring[::step]
    if pts[-1] != ring[-1]:
        pts.append(ring[-1])
    svg_pts = []
    for lon, lat in pts:
        x = lon * scale + offset_x
        y = -lat * scale + offset_y
        svg_pts.append("{:.1f},{:.1f}".format(x, y))
    return " ".join(svg_pts)

def project_geometry(geom):
    paths = []
    if geom["type"] == "Polygon":
        for ring in geom["coordinates"]:
            d = project_ring(ring)
            if d:
                paths.append(d)
    elif geom["type"] == "MultiPolygon":
        for poly in geom["coordinates"]:
            for ring in poly:
                d = project_ring(ring)
                if d:
                    paths.append(d)
    return paths

deptos = []
for feat in data["features"]:
    name = feat["properties"]["name"]  # UTF-8 string
    paths = project_geometry(feat["geometry"])
    deptos.append({"name": name, "paths": paths})

# Guardar con UTF-8 sin escape
out_path = RESOURCES / "colombia_svg_paths.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(deptos, f, ensure_ascii=False, separators=(",", ":"))

# Verificar
with open(out_path, encoding="utf-8") as f:
    verify = json.load(f)
for d in verify[:5]:
    print(repr(d["name"]))
print("Total deptos:", len(verify))
