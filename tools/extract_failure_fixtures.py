# -*- coding: utf-8 -*-
"""
Extracts real failure cases discovered in Cluj USAMV benchmark as permanent regression fixtures:
  1. case_06_usamv_library_split.geojson (Oversegmentation / Split building: 1288m² -> 493m² + 351m²)
  2. case_07_sf_maria_calcan_merge.geojson (Undersegmentation / Merged building: 396m² -> 955m²)
"""

import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import json
import geopandas as gpd
from shapely.geometry import mapping

gdf_ref = gpd.read_file("data/ground_truth/tier4_osm_diagnostic_cluj.geojson")
gdf_pred = gpd.read_file("workspace/output/cladiri_stereo70.gpkg", layer="CLADIRI_HIBRID")

# --- Fixture 6: Biblioteca USAMV (Split building) ---
lib_ref = gdf_ref[gdf_ref["id"] == "REF_OSM_260081500"]
if not lib_ref.empty:
    ref_geom = lib_ref.geometry.iloc[0]
    intersecting_preds = gdf_pred[gdf_pred.geometry.intersects(ref_geom)]
    
    features = [
        {
            "type": "Feature",
            "properties": {
                "role": "GROUND_TRUTH_REFERENCE",
                "id": "REF_OSM_260081500",
                "name": "Complex Biblioteca USAMV",
                "morphology": "COMPLEX_ROOF_WINGED",
                "expected_behavior": "Corp unitar continuu, arie ~1288 mp",
                "failure_mode": "SUPRA_SEGMENTARE_SPLIT"
            },
            "geometry": mapping(ref_geom)
        }
    ]
    for _, row in intersecting_preds.iterrows():
        features.append({
            "type": "Feature",
            "properties": {
                "role": "CURRENT_PIPELINE_PREDICTION",
                "id": f"PRED_{row.get('id', 0)}",
                "area_m2": round(row.geometry.area, 1),
                "failure_mode": "FRAGMENTARE_COAME_DIFERITE"
            },
            "geometry": mapping(row.geometry)
        })
    
    fc = {
        "type": "FeatureCollection",
        "name": "case_06_usamv_library_split",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}},
        "features": features
    }
    with open("data/fixtures/case_06_usamv_library_split.geojson", "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2, ensure_ascii=False)
    print(f"[+] Salvat fixture: data/fixtures/case_06_usamv_library_split.geojson ({len(features)} corpuri)")

# --- Fixture 7: Biserica Catolică Sf. Maria (Merged building) ---
church_ref = gdf_ref[gdf_ref["id"] == "REF_OSM_297540956"]
if not church_ref.empty:
    ref_geom = church_ref.geometry.iloc[0]
    intersecting_preds = gdf_pred[gdf_pred.geometry.intersects(ref_geom)]
    
    features = [
        {
            "type": "Feature",
            "properties": {
                "role": "GROUND_TRUTH_REFERENCE",
                "id": "REF_OSM_297540956",
                "name": "Biserica Catolica Sf. Maria",
                "morphology": "CHURCH_WITH_PARISH_HOUSE",
                "expected_behavior": "Corp biserica separat de anexa parohiala, arie ~396 mp",
                "failure_mode": "SUB_SEGMENTARE_MERGED"
            },
            "geometry": mapping(ref_geom)
        }
    ]
    for _, row in intersecting_preds.iterrows():
        features.append({
            "type": "Feature",
            "properties": {
                "role": "CURRENT_PIPELINE_PREDICTION",
                "id": f"PRED_{row.get('id', 0)}",
                "area_m2": round(row.geometry.area, 1),
                "failure_mode": "CONTOPIT_CU_CLADIREA_ADIACENTA"
            },
            "geometry": mapping(row.geometry)
        })
    
    fc = {
        "type": "FeatureCollection",
        "name": "case_07_sf_maria_calcan_merge",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}},
        "features": features
    }
    with open("data/fixtures/case_07_sf_maria_calcan_merge.geojson", "w", encoding="utf-8") as f:
        json.dump(fc, f, indent=2, ensure_ascii=False)
    print(f"[+] Salvat fixture: data/fixtures/case_07_sf_maria_calcan_merge.geojson ({len(features)} corpuri)")
