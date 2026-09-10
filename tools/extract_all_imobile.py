# -*- coding: utf-8 -*-
"""
Extract All Cadastral Properties (Imobile / Constructii) from GMW
=================================================================
Parses all 24+ cadastral overlays in COAJE LUCRU DATE.gmw
and generates data/ground_truth/tier1_teren.geojson in Stereo 70 (EPSG:3844).
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

print("Scanare Global Mapper Workspace pentru toate layerele 'Imobil'...")

overlays = []
current_lines = []
in_imobil = False
imobil_name = "Imobil"

with open(gmw_path, "r", encoding="latin-1") as f:
    for line in f:
        stripped = line.strip()
        if stripped.startswith("EMBED_OVERLAY") and 'LAYER_GROUP="Imobil"' in stripped:
            if current_lines:
                overlays.append((imobil_name, current_lines))
            current_lines = []
            in_imobil = True
            imobil_name = "Imobil"
            continue
            
        if in_imobil:
            if stripped.startswith("EMBED_OVERLAY") or stripped.startswith("DEFINE_LAYER_STYLE") or stripped == "end":
                if current_lines:
                    overlays.append((imobil_name, current_lines))
                    current_lines = []
                if stripped.startswith("EMBED_OVERLAY") and 'LAYER_GROUP="Imobil"' in stripped:
                    in_imobil = True
                else:
                    in_imobil = False
            else:
                if "IMOBIL" in stripped:
                    imobil_name = stripped
                current_lines.append(stripped)

if current_lines:
    overlays.append((imobil_name, current_lines))

print(f"[+] Gasite {len(overlays)} layere cadastrale Imobil.")

features = []
idx = 0
for name, lines in overlays:
    uulines = [l for l in lines if (l.startswith("M") or l.startswith("0") or l.startswith("`")) and len(l) > 10]
    if not uulines:
        continue
    try:
        raw_bytes = b"".join(binascii.a2b_uu(l) for l in uulines)
        coords = []
        # Find all double pairs (X, Y) in Stereo 70 Cluj range
        for i in range(0, len(raw_bytes) - 15):
            try:
                vx, vy = struct.unpack("<dd", raw_bytes[i:i+16])
                if 388000.0 <= vx <= 393000.0 and 583000.0 <= vy <= 587000.0:
                    if not coords or (abs(coords[-1][0] - vx) > 0.01 or abs(coords[-1][1] - vy) > 0.01):
                        coords.append((vx, vy))
            except Exception:
                pass
        
        if len(coords) >= 4:
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            poly = Polygon(coords)
            if poly.is_valid and poly.area >= 15.0:
                idx += 1
                poly = make_valid(poly)
                if poly.geom_type == 'Polygon':
                    c = poly.centroid
                    features.append({
                        "id": f"REF_TIER1_{idx:03d}",
                        "survey_source": "ANCPI_TEREN_CADASTRE_STEREO70",
                        "cadastral_imobil": f"Imobil #{idx}",
                        "area_m2": round(float(poly.area), 2),
                        "perimeter_m": round(float(poly.length), 2),
                        "centroid_x": round(float(c.x), 3),
                        "centroid_y": round(float(c.y), 3),
                        "geometry": poly
                    })
    except Exception as e:
        pass

print(f"[+] Decodate {len(features)} corpuri cadastrale de teren validate.")

gdf = gpd.GeoDataFrame(features, crs="EPSG:3844")
os.makedirs(os.path.dirname(out_geojson), exist_ok=True)
gdf.to_file(out_geojson, driver="GeoJSON")
print(f"[+] Salvat cu succes in: {out_geojson}")
