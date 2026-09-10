# -*- coding: utf-8 -*-
"""
Helper script to extract independent ground truth reference polygons for Cluj USAMV
from cached OpenStreetMap building footprints in Stereo 70 (EPSG:3844).
"""

import os
import sys
import json
from shapely.geometry import Polygon, mapping
from pyproj import Transformer

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

transformer = Transformer.from_crs("EPSG:4326", "EPSG:3844", always_xy=True)

cache_file = "workspace/output/osm_ancpi_cache.json"
out_gt_file = "data/ground_truth/tier2_osm_cluj_usamv.geojson"

if not os.path.exists(cache_file):
    print(f"Eroare: {cache_file} nu exista.")
    sys.exit(1)

with open(cache_file, "r", encoding="utf-8") as f:
    data = json.load(f)

nodes = {el["id"]: (el["lon"], el["lat"]) for el in data.get("elements", []) if el["type"] == "node"}
ways = [el for el in data.get("elements", []) if el["type"] == "way" and "building" in el.get("tags", {})]

features = []
for w in ways:
    w_nodes = w.get("nodes", [])
    if len(w_nodes) >= 4 and w_nodes[0] == w_nodes[-1]:
        coords_4326 = [nodes[nid] for nid in w_nodes if nid in nodes]
        if len(coords_4326) == len(w_nodes):
            coords_3844 = [transformer.transform(lon, lat) for lon, lat in coords_4326]
            poly = Polygon(coords_3844)
            if poly.is_valid and poly.area >= 15.0:
                features.append({
                    "type": "Feature",
                    "properties": {
                        "id": f"REF_OSM_{w['id']}",
                        "survey_source": "INDEPENDENT_OSM_VECTOR",
                        "name": w.get("tags", {}).get("name", "Cladire"),
                        "building_type": w.get("tags", {}).get("building", "yes"),
                        "area_m2": round(poly.area, 2)
                    },
                    "geometry": mapping(poly)
                })

fc = {
    "type": "FeatureCollection",
    "name": "tier2_osm_cluj_usamv",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}},
    "features": features
}

os.makedirs(os.path.dirname(out_gt_file), exist_ok=True)
with open(out_gt_file, "w", encoding="utf-8") as f:
    json.dump(fc, f, indent=2, ensure_ascii=False)

print(f"[+] Salvat {len(features)} cladiri de referinta independente in: {out_gt_file}")
