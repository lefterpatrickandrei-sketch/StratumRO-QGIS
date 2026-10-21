# -*- coding: utf-8 -*-
"""
Extracts USAMV Cluj validated building footprints from the visual catalog HTML
into a GeoJSON (EPSG:3844 Stereo 70) and a comprehensive CSV for ML evaluation.
"""

import json
import re
from pathlib import Path
import pandas as pd
from shapely.geometry import Polygon, mapping


def extract_buildings(html_path: str, output_geojson: str, output_csv: str):
    html_file = Path(html_path)
    if not html_file.exists():
        raise FileNotFoundError(f"HTML catalog not found at: {html_path}")

    text = html_file.read_text(encoding="utf-8", errors="ignore")
    match = re.search(r"const\s+BUILDINGS\s*=\s*(\[.*?\]);", text, re.DOTALL)
    if not match:
        raise ValueError("Could not find const BUILDINGS array in HTML file")

    buildings = json.loads(match.group(1))
    print(f"Loaded {len(buildings)} raw building objects from {html_path}")

    features = []
    csv_rows = []

    for b in buildings:
        b_id = b.get("id")
        status = b.get("status", "UNKNOWN")
        s70_pts = b.get("s70_points", [])
        
        # Build polygon if points are present
        poly = None
        if len(s70_pts) >= 3:
            coords = [(p["x"], p["y"]) for p in s70_pts]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
        
        props = {
            "id": b_id,
            "clean_id": b.get("clean_id"),
            "status": status,
            "reject_reason": b.get("reject_reason"),
            "family": b.get("family"),
            "nodes": b.get("nodes"),
            "area_roof": b.get("area_roof"),
            "area_sol": b.get("area_sol"),
            "area_diff": b.get("area_diff"),
            "eave_offset": b.get("eave_offset"),
            "h_mean": b.get("h_mean"),
            "h_max": b.get("h_max"),
            "h_min": b.get("h_min"),
            "h_regime": b.get("h_regime"),
            "has_calcan": b.get("has_calcan"),
            "ai_verdict": b.get("ai_verdict"),
            "ai_confidence": b.get("ai_confidence"),
            "ai_notes": b.get("ai_notes"),
            "mean_contrast": b.get("mean_contrast"),
        }

        if poly and not poly.is_empty:
            props["centroid_x"] = poly.centroid.x
            props["centroid_y"] = poly.centroid.y
            props["area_geo"] = poly.area

            # Only include validated ones in Tier 2 ground truth (or record status in properties)
            feat = {
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": props
            }
            features.append(feat)

        csv_rows.append(props)

    # Save GeoJSON
    out_geo = Path(output_geojson)
    out_geo.parent.mkdir(parents=True, exist_ok=True)
    
    # Filter for VALID ground truth
    valid_features = [f for f in features if f["properties"]["status"] == "VALID"]
    
    geojson_data = {
        "type": "FeatureCollection",
        "name": "tier2_cladiri_usamv",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}
        },
        "features": valid_features
    }
    out_geo.write_text(json.dumps(geojson_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Saved {len(valid_features)} VALID buildings to {output_geojson}")

    # Also save complete collection with both valid and rejected
    all_geo_path = out_geo.parent / "tier2_all_candidates_usamv.geojson"
    all_geojson_data = {
        "type": "FeatureCollection",
        "name": "tier2_all_candidates_usamv",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:EPSG::3844"}
        },
        "features": features
    }
    all_geo_path.write_text(json.dumps(all_geojson_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Saved all {len(features)} building candidates to {all_geo_path}")

    # Save CSV
    out_csv = Path(output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(csv_rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    print(f"[OK] Saved {len(df)} records to {output_csv}")


if __name__ == "__main__":
    extract_buildings(
        html_path="workspace/reviews/catalog_cladiri_ortofoto.html",
        output_geojson="data/ground_truth/tier2_cladiri_usamv.geojson",
        output_csv="data/ground_truth/usamv_180_features.csv"
    )
