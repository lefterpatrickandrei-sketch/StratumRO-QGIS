# -*- coding: utf-8 -*-
"""
tools/scan_map_for_defects.py
==============================
Scans all 141 active building proposals in Option B across the entire map
and detects all systematic geometric defects:
1. Non-orthogonal / chamfered corners (deviation from 90°/180° by > 15°).
2. Fragment / sliver / low-area artifacts (< 60 m² or fill_ratio < 0.65).
3. Excess node complexity (> 8 nodes on residential roofs).
4. Short edges (< 1.0 m) caused by raster pixelation.
5. Inward cutouts / equipment notches (like B039).
"""

import sys
import json
from pathlib import Path
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parent.parent
GPKG = ROOT / "workspace" / "option_b_validation_20261019" / "b_proposals_cleaned.gpkg"
OUT_REPORT = ROOT / "workspace" / "option_b_validation_20261019" / "map_geometric_defects.json"

def get_angles(poly):
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    angles = []
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        v1 = p_prev - p_curr
        v2 = p_next - p_curr
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            continue
        cos_ang = np.clip(np.dot(v1, v2) / (norm1 * norm2), -1.0, 1.0)
        ang_deg = np.degrees(np.arccos(cos_ang))
        angles.append(ang_deg)
    return angles

def scan_map():
    gdf = gpd.read_file(GPKG, layer="B_ROOF_PROPOSALS")
    print(f"[*] Total propuneri active analizate pe toata harta: {len(gdf)}")

    non_ortho_cases = []
    sliver_cases = []
    complex_cases = []
    short_edge_cases = []
    notched_cases = []

    for _, r in gdf.iterrows():
        cid = r["candidate_id"]
        g = r.geometry
        if g.geom_type != "Polygon":
            continue
        coords = list(g.exterior.coords)[:-1]
        n_nodes = len(coords)
        area = g.area

        # 1. Non-orthogonal angles
        angles = get_angles(g)
        bad_angles = [a for a in angles if abs(a - 90.0) > 15.0 and abs(a - 270.0) > 15.0]
        if bad_angles:
            non_ortho_cases.append({
                "candidate_id": cid,
                "area_m2": round(area, 2),
                "nodes": n_nodes,
                "bad_angles_count": len(bad_angles),
                "bad_angles": [round(a, 1) for a in bad_angles]
            })

        # 2. Slivers / small fragments
        rect = g.minimum_rotated_rectangle
        rect_area = rect.area
        fill_ratio = area / rect_area if rect_area > 0 else 0
        if area < 60.0 or fill_ratio < 0.65:
            sliver_cases.append({
                "candidate_id": cid,
                "area_m2": round(area, 2),
                "fill_ratio": round(fill_ratio, 3),
                "is_small": area < 60.0
            })

        # 3. High node count (> 8 nodes)
        if n_nodes > 8:
            complex_cases.append({
                "candidate_id": cid,
                "area_m2": round(area, 2),
                "nodes": n_nodes
            })

        # 4. Short edges (< 1.0m)
        short_edges = []
        for i in range(len(coords)):
            p1 = np.array(coords[i])
            p2 = np.array(coords[(i + 1) % len(coords)])
            d = np.linalg.norm(p2 - p1)
            if d < 1.0:
                short_edges.append(round(d, 2))
        if short_edges:
            short_edge_cases.append({
                "candidate_id": cid,
                "short_edges_count": len(short_edges),
                "short_edges": short_edges
            })

        # 5. Notched / cutout roofs (convex hull comparison)
        chull = g.convex_hull
        hull_ratio = area / chull.area if chull.area > 0 else 1.0
        # If hull ratio is below 0.85 on a building with > 6 nodes, it has big cutouts
        if hull_ratio < 0.85 and n_nodes >= 6:
            notched_cases.append({
                "candidate_id": cid,
                "area_m2": round(area, 2),
                "hull_ratio": round(hull_ratio, 3),
                "nodes": n_nodes
            })

    report = {
        "total_proposals": len(gdf),
        "summary": {
            "non_orthogonal_corners_count": len(non_ortho_cases),
            "fragments_and_slivers_count": len(sliver_cases),
            "high_complexity_nodes_count": len(complex_cases),
            "short_edges_count": len(short_edge_cases),
            "notched_roofs_count": len(notched_cases)
        },
        "non_orthogonal_cases": non_ortho_cases,
        "sliver_cases": sliver_cases,
        "complex_cases": complex_cases,
        "short_edge_cases": short_edge_cases,
        "notched_cases": notched_cases
    }

    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("=" * 70)
    print(">>> STRATUMRO: REZULTATE SCANARE DEFECTE PE TOATA HARTA <<<")
    print("=" * 70)
    print(f"[*] Total cladiri analizate: {len(gdf)}")
    print(f"[1] Colțuri teșite / unghiuri non-ortogonale: {len(non_ortho_cases)} clădiri")
    print(f"[2] Fragmente parazite / slivere mici (<60mp / alungite): {len(sliver_cases)} clădiri")
    print(f"[3] Complexitate excesivă (>8 noduri pe acoperiș): {len(complex_cases)} clădiri")
    print(f"[4] Muchii scurte din pixelare (<1.0m): {len(short_edge_cases)} clădiri")
    print(f"[5] Acoperișuri decupate / ocolire echipamente (scobite): {len(notched_cases)} clădiri")
    print("=" * 70)
    print(f"[*] Raport complet salvat in: {OUT_REPORT}")

if __name__ == "__main__":
    scan_map()
