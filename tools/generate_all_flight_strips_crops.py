# -*- coding: utf-8 -*-
"""
Generate Photogrammetric Drone Flight Strips & Real Ortho Frame Crops
=====================================================================
Calculates all 11 boustrophedon flight strips (253 flight stations, 60% forward, 40% side overlap)
across the 1.05 km x 1.05 km Cluj-Napoca AOI in Stereo 70 (EPSG:3844).
Crops real aerial orthophoto frames from ortofoto_cluj_usamv_rgb.vrt and saves them
as compressed, lightweight JPEGs in workspace/reviews/drone_flight_strips/frames_jpg/.
Associates each station with telemetry (heading, coordinates, altitude, buildings in view).
"""

import json
import math
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import geopandas as gpd
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from PIL import Image
from shapely.geometry import box, Point
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parent.parent

# 1. Coordinate Extents & Flight Parameters (Stereo 70 EPSG:3844)
X_MIN = 390530.0
Y_MIN = 584838.0
X_MAX = 391578.0
Y_MAX = 585886.0

W_TOTAL = X_MAX - X_MIN # 1048.0 m
H_TOTAL = Y_MAX - Y_MIN # 1048.0 m

FRAME_W = 180.0 # m (transversal)
FRAME_H = 120.0 # m (longitudinal)

OVERLAP_FORWARD = 0.60 # 60% longitudinal
OVERLAP_SIDE = 0.40    # 40% transversal

STEP_FORWARD = FRAME_H * (1.0 - OVERLAP_FORWARD) # 48.0 m baseline
STEP_SIDE = FRAME_W * (1.0 - OVERLAP_SIDE)       # 108.0 m strip spacing

N_STRIPS = int(math.ceil(W_TOTAL / STEP_SIDE)) + 1 # 11 strips
N_PHOTOS_PER_STRIP = int(math.ceil(H_TOTAL / STEP_FORWARD)) + 1 # 23 photos per strip

OUT_FRAMES_DIR = ROOT / "workspace" / "reviews" / "drone_flight_strips" / "frames_jpg"
OUT_FRAMES_DIR.mkdir(parents=True, exist_ok=True)

VRT_PATH = ROOT / "workspace" / "output" / "ortofoto_cluj_usamv_rgb.vrt"
GPKG_PATH = ROOT / "workspace" / "option_b_validation_20261019" / "b_proposals_cleaned.gpkg"

print(f"[*] Lansare generator benzi de zbor: {N_STRIPS} benzi x {N_PHOTOS_PER_STRIP} cadre = {N_STRIPS * N_PHOTOS_PER_STRIP} stații foto")
print(f"[*] Parametri: Altitudine 120m AGL | Pas 48m | Distanță benzi 108m | Overlap 60%/40%")

# 2. Load Buildings for In-Frame Detection
print(f"[*] Încărcare clădiri cadastrale din GPKG...")
gdf_b = gpd.read_file(GPKG_PATH, layer="B_ROOF_PROPOSALS")
b_tree = STRtree(gdf_b.geometry.values)

# 3. Generate Flight Stations
stations = []
t0 = time.time()

ds = rasterio.open(str(VRT_PATH))

station_global_idx = 0
for strip_idx in range(N_STRIPS):
    cx = X_MIN + strip_idx * STEP_SIDE
    is_even = (strip_idx % 2 == 0)
    
    # Even strips: North -> South (heading 180 deg)
    # Odd strips: South -> North (heading 0 deg)
    heading = 180 if is_even else 0
    strip_num = strip_idx + 1
    
    if is_even:
        y_range = [Y_MAX - i * STEP_FORWARD for i in range(N_PHOTOS_PER_STRIP)]
    else:
        y_range = [Y_MIN + i * STEP_FORWARD for i in range(N_PHOTOS_PER_STRIP)]
        
    for photo_idx, cy in enumerate(y_range):
        station_global_idx += 1
        photo_num = photo_idx + 1
        station_id = f"STRIP_{strip_num:02d}_FRAME_{photo_num:02d}"
        img_filename = f"{station_id.lower()}.jpg"
        img_out_path = OUT_FRAMES_DIR / img_filename
        
        # Ground Footprint Bounds
        bx_min = cx - FRAME_W / 2.0
        by_min = cy - FRAME_H / 2.0
        bx_max = cx + FRAME_W / 2.0
        by_max = cy + FRAME_H / 2.0
        b_box = box(bx_min, by_min, bx_max, by_max)
        
        # Find intersecting buildings
        inter_idx = b_tree.query(b_box)
        buildings_in_view = [gdf_b.iloc[i]["candidate_id"] for i in inter_idx if gdf_b.iloc[i].geometry.intersects(b_box)]
        
        # Crop real orthophoto frame if not already present or force write
        if not img_out_path.exists():
            win = from_bounds(bx_min, by_min, bx_max, by_max, ds.transform)
            arr = ds.read(window=win, boundless=True, fill_value=0)
            if arr.shape[0] >= 3:
                rgb = np.transpose(arr[:3], (1, 2, 0))
            else:
                rgb = np.dstack([arr[0], arr[0], arr[0]])
            im = Image.fromarray(rgb).resize((400, 267), Image.Resampling.LANCZOS)
            im.save(img_out_path, format="JPEG", quality=75, optimize=True)
            
        sz_kb = round(img_out_path.stat().st_size / 1024, 1)
        
        station_info = {
            "index": station_global_idx - 1,
            "id": station_id,
            "strip": strip_num,
            "frame": photo_num,
            "heading": heading,
            "altitude_m": 120.0,
            "gsd_cm": 1.5,
            "speed_ms": 12.5,
            "x": round(cx, 2),
            "y": round(cy, 2),
            "bounds": [round(bx_min, 2), round(by_min, 2), round(bx_max, 2), round(by_max, 2)],
            "image": f"frames_jpg/{img_filename}",
            "size_kb": sz_kb,
            "bldg_count": len(buildings_in_view),
            "buildings": buildings_in_view[:10] # list up to 10 in view
        }
        stations.append(station_info)

ds.close()
elapsed = round(time.time() - t0, 2)
print(f"[SUCCESS] Generat {len(stations)} cadre aeriene în {elapsed} secunde!")

# 4. Save Flight Manifest JSON
manifest = {
    "mission_name": "StratumRO Cluj AOI Photogrammetric Flight 60/40",
    "crs": "Stereo 70 (EPSG:3844)",
    "aoi_bounds": [X_MIN, Y_MIN, X_MAX, Y_MAX],
    "flight_specs": {
        "n_strips": N_STRIPS,
        "photos_per_strip": N_PHOTOS_PER_STRIP,
        "total_stations": len(stations),
        "frame_width_m": FRAME_W,
        "frame_height_m": FRAME_H,
        "forward_overlap": 0.60,
        "side_overlap": 0.40,
        "altitude_agl_m": 120.0,
        "sensor_focal_mm": 35.0,
        "speed_kmh": 45.0
    },
    "stations": stations
}

manifest_path = ROOT / "workspace" / "reviews" / "drone_flight_strips" / "flight_mission_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(f"[+] Manifest salvat la: {manifest_path}")
