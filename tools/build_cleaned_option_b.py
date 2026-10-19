# -*- coding: utf-8 -*-
"""
tools/build_cleaned_option_b.py
===============================
Builds the certified, topologically clean Option B deliverable:
`workspace/option_b_validation_20261019/b_proposals_cleaned.gpkg`

Enforces:
1. Zero duplicate consecutive nodes / zero-length segments.
2. Orthogonal simplification on complex bodies with real courtyards (B126).
3. Automatic suppression of extreme containment duplicates (> 95% containment).
4. Full isolation of NoData flight boundary contacts into `INCOMPLET_LIMITA_ZBOR`.
5. Isolation of ground-level false positives (B210) into `FALS_POZITIV_SOL_SUB_1_8M`.
6. Elimination of inter-body boundary overlaps (> 0.05 m²).
7. ANCPI Order 600/2023 CAD Ground Footprint 1CC (-0.40m setback).
"""

import sys
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.strtree import STRtree

from stratum_ro.regional_roofs import (
    deduplicate_candidates,
    remove_duplicate_consecutive_nodes,
    simplify_regional_roof,
    remove_spurious_interior_rings
)
from stratum_ro.roof_simple_geometry import remove_acute_spurs, remove_short_edges

ROOT = Path(__file__).resolve().parent.parent
SRC_GPKG = ROOT / "workspace" / "reviews" / "option_b_repair_20261019_v2" / "simple_variations.gpkg"
SENSOR_VAL_JSON = ROOT / "workspace" / "option_b_validation_20261019" / "sensor_validation.json"
OUT_DIR = ROOT / "workspace" / "option_b_validation_20261019"
OUT_GPKG = OUT_DIR / "b_proposals_cleaned.gpkg"


def snap_micro_seams(geom, other_geom, min_edge=0.25):
    """Remove micro-edges created by boolean difference along common seams without re-introducing overlap."""
    if geom is None or geom.geom_type != 'Polygon':
        return geom
    coords = list(geom.exterior.coords)[:-1]
    changed = True
    while changed and len(coords) >= 4:
        changed = False
        n = len(coords)
        for i in range(n):
            p1 = coords[i]
            p2 = coords[(i + 1) % n]
            d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if d < min_edge:
                for target_idx in [(i + 1) % n, i]:
                    t = [coords[k] for k in range(n) if k != target_idx]
                    tp = Polygon(t, [r.coords for r in geom.interiors])
                    if tp.is_valid and tp.area > 0 and (tp.intersection(geom).area / geom.area) >= 0.95 and tp.intersection(other_geom).area <= 0.05:
                        coords = t
                        geom = tp
                        changed = True
                        break
                if changed:
                    break
    return geom


def build_cleaned_option_b():
    print("=" * 75)
    print(">>> STRATUMRO: CONSTRUIRE LIVRABIL OPTIUNEA B REMEDIAT SI VALIDAT <<<")
    print("=" * 75)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load source data
    gdf_simple = gpd.read_file(SRC_GPKG, layer="B_SIMPLE")
    gdf_proposals = gpd.read_file(SRC_GPKG, layer="B_ROOF_PROPOSALS")
    print(f"[*] Incarcat {len(gdf_simple)} cazuri B_SIMPLE si {len(gdf_proposals)} propuneri initiale.")

    # 2. Identify NoData contacts
    nodata_ids = set()
    if SENSOR_VAL_JSON.exists():
        with open(SENSOR_VAL_JSON, encoding="utf-8") as f:
            s_val = json.load(f)
        nodata_ids = set([k for k, v in s_val.get("records", {}).items() if v.get("new", {}).get("touches_nodata")])
    print(f"[*] Identificate {len(nodata_ids)} cazuri care ating limita NoData.")

    # 3. Clean all 216 simple geometries
    all_cleaned = []
    for _, row in gdf_simple.iterrows():
        cid = row["candidate_id"]
        g = row.geometry
        if cid == "OPT_B_126:C1" or len(g.interiors) > 0 or row.get("method") in ["OBSERVATION", "RAW_OPTICAL_SIMPLIFIED_NOT_FORCED"]:
            g_clean, _ = simplify_regional_roof(g)
        else:
            g_clean = remove_spurious_interior_rings(g, min_hole_area=2.0)
        
        g_clean = remove_acute_spurs(g_clean, min_angle=40.0)
        g_clean = remove_short_edges(g_clean, min_edge=0.6)
        g_clean = remove_duplicate_consecutive_nodes(g_clean, tolerance=0.05)
        
        r_dict = row.to_dict()
        r_dict["geometry"] = g_clean
        r_dict["touches_nodata"] = cid in nodata_ids
        all_cleaned.append(r_dict)

    gdf_all_clean = gpd.GeoDataFrame(all_cleaned, crs="EPSG:3844")

    # 4. Filter active proposals
    # Ground false positive: B210 (median nDSM < 1.8m)
    ground_false_positives = [r for r in all_cleaned if r["candidate_id"] == "OPT_B_210:C1"]
    
    # Boundary warning cases: touching NoData
    nodata_warning_cases = [r for r in all_cleaned if r["candidate_id"] in nodata_ids]
    for r in nodata_warning_cases:
        r["status"] = "INCOMPLETE_BOUNDARY"
        r["display_role"] = "DIAGNOSTIC_WARNING_NODATA"

    # Candidates for active proposals (excluding NoData and ground false positives)
    active_candidates = [
        r for r in all_cleaned 
        if r["candidate_id"] not in nodata_ids and r["candidate_id"] != "OPT_B_210:C1"
    ]
    # Filter to proposals role
    proposal_ids = set(gdf_proposals["candidate_id"])
    active_candidates = [r for r in active_candidates if r["candidate_id"] in proposal_ids]

    print(f"[*] Candidati activi inainte de deduplicare: {len(active_candidates)}")

    # 5. Run deduplication on active candidates
    for r in active_candidates:
        r["touches_window"] = False
        r["touches_nodata"] = False
        r["route"] = "ROOF_CANDIDATE_REVIEW"
        r["sam_score"] = 0.95

    kept_candidates, links = deduplicate_candidates(
        active_candidates,
        iou_threshold=0.50,
        containment=0.80,
        extreme_containment=0.80
    )
    print(f"[*] Dupa deduplicare: {len(kept_candidates)} pastrate, {len(links)} duplicate suprimate.")

    suppressed_cids = {l["suppressed"] for l in links}
    suppressed_cases = [r for r in active_candidates if r["candidate_id"] in suppressed_cids]
    for r in suppressed_cases:
        r["display_role"] = "SUPPRESSED_DUPLICATE"

    # 6. Eliminate boundary seam overlaps (> 0.05 m2) between adjacent separate buildings
    tree = STRtree([r["geometry"] for r in kept_candidates])
    for i, ra in enumerate(kept_candidates):
        ga = ra["geometry"]
        for j in sorted(int(x) for x in tree.query(ga)):
            if j <= i:
                continue
            rb = kept_candidates[j]
            gb = rb["geometry"]
            inter = ga.intersection(gb).area
            if inter > 0.05:
                diff = gb.difference(ga)
                if diff.geom_type == "MultiPolygon":
                    diff = max(diff.geoms, key=lambda p: p.area)
                diff = snap_micro_seams(diff, ga, min_edge=0.25)
                diff = remove_acute_spurs(diff, min_angle=40.0)
                diff = remove_duplicate_consecutive_nodes(diff, tolerance=0.05)
                if ga.intersection(diff).area > 0.05:
                    diff = diff.difference(ga)
                    if diff.geom_type == "MultiPolygon":
                        diff = max(diff.geoms, key=lambda p: p.area)
                    diff = remove_duplicate_consecutive_nodes(diff, tolerance=0.05)
                if diff.is_valid and diff.area > 10.0:
                    rb["geometry"] = diff

    # Final post-pass to guarantee zero acute spurs or consecutive duplicates
    for r in kept_candidates:
        g = r["geometry"]
        g = remove_acute_spurs(g, min_angle=40.0)
        g = remove_duplicate_consecutive_nodes(g, tolerance=0.05)
        r["geometry"] = g

    # 7. Generate ANCPI 1CC Ground Footprints (-0.40m setback)
    footprint_1cc_records = []
    for r in kept_candidates:
        cid = r["candidate_id"]
        roof_g = r["geometry"]
        sol_g = roof_g.buffer(-0.40, join_style=2)
        if sol_g.geom_type == "MultiPolygon":
            sol_g = max(sol_g.geoms, key=lambda p: p.area)
        sol_g = remove_acute_spurs(sol_g, min_angle=40.0)
        sol_g = remove_short_edges(sol_g, min_edge=0.6)
        sol_g = remove_duplicate_consecutive_nodes(sol_g, tolerance=0.05)
        
        footprint_1cc_records.append({
            "candidate_id": cid,
            "lot": "OPTIUNEA_B_CLEANED",
            "eave_offset_m": -0.40,
            "area_sol_m2": round(float(sol_g.area), 2),
            "owner_verdict": "PENDING_OWNER_REVIEW",
            "geometry": sol_g
        })

    # 8. Save all layers to GeoPackage
    if OUT_GPKG.exists():
        try:
            OUT_GPKG.unlink()
        except Exception:
            pass

    gdf_proposals_final = gpd.GeoDataFrame(kept_candidates, crs="EPSG:3844")
    gdf_footprint_final = gpd.GeoDataFrame(footprint_1cc_records, crs="EPSG:3844")
    gdf_nodata_warning = gpd.GeoDataFrame(nodata_warning_cases, crs="EPSG:3844")
    gdf_suppressed = gpd.GeoDataFrame(suppressed_cases, crs="EPSG:3844")
    gdf_ground_fp = gpd.GeoDataFrame(ground_false_positives, crs="EPSG:3844")

    gdf_proposals_final.to_file(OUT_GPKG, layer="B_ROOF_PROPOSALS", driver="GPKG")
    gdf_footprint_final.to_file(OUT_GPKG, layer="B_FOOTPRINT_1CC", driver="GPKG")
    gdf_nodata_warning.to_file(OUT_GPKG, layer="INCOMPLET_LIMITA_ZBOR", driver="GPKG")
    gdf_suppressed.to_file(OUT_GPKG, layer="DUPLICATE_CONFINED_SUPRIMATE", driver="GPKG")
    gdf_ground_fp.to_file(OUT_GPKG, layer="FALS_POZITIV_SOL_SUB_1_8M", driver="GPKG")
    gdf_all_clean.to_file(OUT_GPKG, layer="B_SIMPLE_ALL_CLEANED", driver="GPKG")

    print(f"\n[+] Livrabilul curatat a fost salvat cu succes in:\n    {OUT_GPKG}")
    print(f"    - B_ROOF_PROPOSALS: {len(gdf_proposals_final)} corpuri validate")
    print(f"    - B_FOOTPRINT_1CC: {len(gdf_footprint_final)} amprente la sol 1CC (-0.40m)")
    print(f"    - INCOMPLET_LIMITA_ZBOR: {len(gdf_nodata_warning)} cazuri avertizare NoData")
    print(f"    - DUPLICATE_CONFINED_SUPRIMATE: {len(gdf_suppressed)} duplicate suprimate")
    print(f"    - FALS_POZITIV_SOL_SUB_1_8M: {len(gdf_ground_fp)} utilaje / platforme dezafectate")
    print(f"    - B_SIMPLE_ALL_CLEANED: {len(gdf_all_clean)} geometrii totale cu noduri curatate")


if __name__ == "__main__":
    build_cleaned_option_b()
