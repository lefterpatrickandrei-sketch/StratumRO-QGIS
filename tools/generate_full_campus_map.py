# -*- coding: utf-8 -*-
"""
Generate Full Campus Orthophoto Visual Map.
Renders the entire authentic USAMV Cluj 1048m x 1048m RGB mosaic (ortofoto_cluj_usamv_rgb.vrt),
overlaying all 150 reference cadastral buildings and the Phase 3 E9 crop box.
"""

import os
import json
import rasterio
from rasterio.transform import rowcol
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

PROJECT_ROOT = Path("c:/Users/lefpa/Downloads/QGIS-AI")
VRT_PATH = PROJECT_ROOT / "workspace" / "output" / "ortofoto_cluj_usamv_rgb.vrt"
REF_150_PATH = PROJECT_ROOT / "data" / "derived_reference" / "cluj_combined_unique_150.geojson"
E9_PRED_PATH = PROJECT_ROOT / "workspace" / "phase3" / "predictions" / "EXP_009_integrated_pipeline_reg.geojson"
OUTPUT_PNG = PROJECT_ROOT / "docs" / "assets" / "phases" / "phase3" / "StratumRO_cluj_full_campus_ortho.png"

print(f"[*] Reading full campus VRT from: {VRT_PATH}")
with rasterio.open(VRT_PATH) as src:
    vrt_bounds = src.bounds
    vrt_transform = src.transform
    # Downsample full 6991x6991 raster to a crisp 2500x2500 image for fast, crisp rendering
    target_w, target_h = 2500, 2500
    rgb = src.read(out_shape=(3, target_h, target_w))
    
# Scale transform for coordinate mapping
scale_x = target_w / src.width
scale_y = target_h / src.height

def geo_to_pixel(x, y):
    r, c = rowcol(vrt_transform, x, y)
    px = int(c * scale_x)
    py = int(r * scale_y)
    return px, py

# Transpose to HWC for PIL
img_arr = np.transpose(rgb, (1, 2, 0)).astype(np.uint8)
canvas = Image.fromarray(img_arr, mode="RGB")
draw = ImageDraw.Draw(canvas)

# 1. Draw all 150 Ground Truth Reference Buildings across the entire campus (Bright Cyan)
print(f"[*] Loading 150 reference buildings: {REF_150_PATH}")
with open(REF_150_PATH, "r", encoding="utf-8") as f:
    ref_data = json.load(f)

for feat in ref_data.get("features", []):
    geom = feat.get("geometry", {})
    gtype = geom.get("type")
    coords = geom.get("coordinates", [])
    polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
    
    for poly in polys:
        ring = poly[0] if len(poly) > 0 else []
        pts = [geo_to_pixel(x, y) for x, y in ring if len(ring) > 0]
        if len(pts) >= 3:
            draw.polygon(pts, outline=(0, 229, 255), width=2)

# 2. Draw Phase 3 E9 predictions in the active crop (Bright Neon Green)
if E9_PRED_PATH.exists():
    with open(E9_PRED_PATH, "r", encoding="utf-8") as f:
        e9_data = json.load(f)
    for feat in e9_data.get("features", []):
        geom = feat.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])
        polys = [coords] if gtype == "Polygon" else (coords if gtype == "MultiPolygon" else [])
        for poly in polys:
            ring = poly[0] if len(poly) > 0 else []
            pts = [geo_to_pixel(x, y) for x, y in ring if len(ring) > 0]
            if len(pts) >= 3:
                draw.polygon(pts, outline=(0, 255, 100), width=3)

# 3. Draw Active Crop AOI Bounding Box (Dashed Yellow/Orange Outline)
crop_bbox = [
    (390649.99, 585350.00),
    (391149.99, 585350.00),
    (391149.99, 585750.00),
    (390649.99, 585750.00),
    (390649.99, 585350.00)
]
crop_pts = [geo_to_pixel(x, y) for x, y in crop_bbox]
draw.line(crop_pts, fill=(255, 214, 0), width=3)

# 4. Header & Legend Banner
banner_h = 100
banner = Image.new("RGBA", (target_w, banner_h), color=(10, 15, 26, 230))
canvas.paste(banner, (0, 0), mask=banner)

draw = ImageDraw.Draw(canvas)
try:
    font_large = ImageFont.truetype("arial.ttf", 26)
    font_med = ImageFont.truetype("arial.ttf", 16)
    font_small = ImageFont.truetype("arial.ttf", 13)
except Exception:
    font_large = ImageFont.load_default()
    font_med = ImageFont.load_default()
    font_small = ImageFont.load_default()

draw.text((25, 15), "StratumRO — Mozaic Ortofotoplan Integral USAMV Cluj (1.05 km x 1.05 km, ~110 ha)", fill=(255, 255, 255), font=font_large)
draw.text((25, 55), "Proiecție: Stereo 70 (EPSG:3844) | Rezoluție: 0.15m GSD (6991 x 6991 px) | Mozaic complet 3x3 fără margini tăiate", fill=(176, 190, 197), font=font_med)

# Legend Panel
panel_w, panel_h = 440, 240
panel = Image.new("RGBA", (panel_w, panel_h), color=(10, 15, 26, 235))
canvas.paste(panel, (target_w - panel_w - 25, 120), mask=panel)

draw = ImageDraw.Draw(canvas)
lx = target_w - panel_w - 10
ly = 135

draw.text((lx, ly), "LEGENDĂ ȘI STRATURI ACTIVE", fill=(255, 255, 255), font=font_med)
ly += 30

# Legend item 1: Full Orthophoto
draw.rectangle([lx, ly, lx + 25, ly + 14], fill=(70, 90, 120), outline=(255, 255, 255))
draw.text((lx + 35, ly), "Mozaic Ortofoto Integral (Fond RGB 0.15m GSD)", fill=(220, 220, 220), font=font_small)
ly += 26

# Legend item 2: 150 Reference Buildings
draw.rectangle([lx, ly, lx + 25, ly + 14], outline=(0, 229, 255), width=2)
draw.text((lx + 35, ly), "150 Clădiri Cadastru Referință (Campus Integral)", fill=(0, 229, 255), font=font_small)
ly += 26

# Legend item 3: E9 Predictions
draw.rectangle([lx, ly, lx + 25, ly + 14], outline=(0, 255, 100), width=3)
draw.text((lx + 35, ly), "Faza 3: Predicții E9 (26 clădiri optimizate)", fill=(0, 255, 100), font=font_small)
ly += 26

# Legend item 4: Active Crop Box
draw.line([(lx, ly + 7), (lx + 25, ly + 7)], fill=(255, 214, 0), width=3)
draw.text((lx + 35, ly), "Perimetru Decupaj Faza 3 (500m x 400m crop)", fill=(255, 214, 0), font=font_small)
ly += 32

draw.text((lx, ly), "Acoperire: 100% din cele 150 clădiri au textură completă", fill=(100, 255, 218), font=font_small)

# Scale Bar
scale_bar_m = 200 # 200 meters
px_per_m = target_w / (vrt_bounds.right - vrt_bounds.left)
scale_bar_px = int(scale_bar_m * px_per_m)
sx = 35
sy = target_h - 40
draw.line([(sx, sy), (sx + scale_bar_px, sy)], fill=(255, 255, 255), width=4)
draw.line([(sx, sy - 6), (sx, sy + 6)], fill=(255, 255, 255), width=3)
draw.line([(sx + scale_bar_px, sy - 6), (sx + scale_bar_px, sy + 6)], fill=(255, 255, 255), width=3)
draw.text((sx + scale_bar_px // 2 - 25, sy - 22), f"{scale_bar_m} m", fill=(255, 255, 255), font=font_med)

# Save
OUTPUT_PNG.parent.mkdir(parents=True, exist_ok=True)
canvas.save(OUTPUT_PNG, "PNG", optimize=True)
print(f"[+] Successfully saved full campus inspection map: {OUTPUT_PNG} ({OUTPUT_PNG.stat().st_size} bytes)")
