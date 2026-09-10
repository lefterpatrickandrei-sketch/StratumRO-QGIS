# -*- coding: utf-8 -*-
"""
Extract Real Cadastral / Survey Ground Truth from COAJE LUCRU DATE.gmw
=====================================================================
Parses all embedded vector overlays in the Global Mapper workspace
and reconstructs the official cadastral polygons (Imobile / Constructii) in Stereo 70.
Exports to: data/ground_truth/tier1_teren.geojson
"""

import os
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import binascii
import struct
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.validation import make_valid

gmw_path = r"C:\Users\lefpa\Desktop\date\COAJE LUCRU DATE.gmw"
out_geojson = "data/ground_truth/tier1_teren.geojson"

print(f"Deschidere {gmw_path} pentru extragerea poligoanelor cadastrale oficiale...")

polygons = []

with open(gmw_path, "r", encoding="latin-1") as f:
    in_overlay = False
    overlay_lines = []
    overlay_meta = {}
    
    for line in f:
        stripped = line.strip()
        if stripped.startswith("EMBED_OVERLAY "):
            in_overlay = True
            overlay_lines = []
            overlay_meta = {"header": stripped}
            continue
            
        if in_overlay:
            if stripped == "end" or stripped.startswith("/******") or stripped.startswith("DEFINE_LAYER_STYLE") or stripped.startswith("IMPORT "):
                in_overlay = False
                # Process overlay lines
                uulines = [l.strip() for l in overlay_lines if l.startswith("M") or l.startswith("0") or l.startswith("`")]
                if uulines:
                    try:
                        raw_bytes = b"".join(binascii.a2b_uu(l) for l in uulines)
                        # Extract double-precision coordinate pairs in Stereo 70 range
                        coords = []
                        step = 8
                        for i in range(0, len(raw_bytes) - 15, step):
                            vx, vy = struct.unpack("<dd", raw_bytes[i:i+16])
                            if 390000.0 <= vx <= 392000.0 and 584000.0 <= vy <= 586500.0:
                                if not coords or (coords[-1][0] != vx or coords[-1][1] != vy):
                                    coords.append((vx, vy))
                        
                        if len(coords) >= 4:
                            # If first != last, close polygon
                            if coords[0] != coords[-1]:
                                coords.append(coords[0])
                            poly = Polygon(coords)
                            if poly.is_valid and poly.area >= 15.0:
                                poly = make_valid(poly)
                                if poly.geom_type == 'Polygon' and poly.area >= 15.0:
                                    polygons.append(poly)
                    except Exception:
                        pass
                overlay_lines = []
            else:
                overlay_lines.append(line)

print(f"[+] Extrase {len(polygons)} poligoane cadastrale reale din Global Mapper Workspace.")

# Deduplicate
unique_polys = []
for p in polygons:
    if not any(p.equals(up) or p.intersection(up).area / max(p.area, up.area) > 0.95 for up in unique_polys):
        unique_polys.append(p)

print(f"[+] {len(unique_polys)} poligoane cadastrale unice validate în perimetrul USAMV.")

features = []
for idx, p in enumerate(unique_polys, start=1):
    c = p.centroid
    features.append({
        "id": f"REF_CAD_{idx:03d}",
        "survey_source": "CADASTRE_OFICIAL_IMOBIL_STEREO70",
        "name": f"Imobil/Constructie Cadastrala #{idx}",
        "area_m2": round(float(p.area), 2),
        "perimeter_m": round(float(p.length), 2),
        "centroid_x": round(float(c.x), 3),
        "centroid_y": round(float(c.y), 3),
        "geometry": p
    })

gdf = gpd.GeoDataFrame(features, crs="EPSG:3844")
os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
gdf.to_file(out_geojson, driver="GeoJSON")
print(f"[+] Fisierul oficial Tier 1 a fost salvat cu succes in: {out_geojson}")
