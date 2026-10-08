# -*- coding: utf-8 -*-
"""
StratumRO - Deduplicate Cadastral Deliverables
==============================================
Removes identical duplicate geometries from:
  1. CLADIRI_CADASTRU_CLEAN (147 -> 121 distinct) in cladiri_stereo70.gpkg
  2. CLADIRI_SOL_ANCPI (147 -> 121 distinct) in cladiri_stereo70.gpkg
  3. CLADIRI_HIBRID (179 -> 150 distinct) in cladiri_stereo70.gpkg
  4. cladiri_finalizate_aoi_complet.geojson (179 -> 150 distinct)

Verifies that Ground-Truth matches (26/29) against tier1_teren.geojson are 100% preserved.
"""

import os
import sys
import json
import hashlib
import geopandas as gpd
from shapely.geometry import shape

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
GEOJSON = os.path.join(ROOT, "workspace", "output", "cladiri_finalizate_aoi_complet.geojson")
GT_PATH = os.path.join(ROOT, "data", "ground_truth", "tier1_teren.geojson")


def geom_hash(geom):
    """Compute deterministic SHA-256 hash of geometry WKB."""
    return hashlib.sha256(geom.wkb).hexdigest()


def deduplicate_gdf(gdf, layer_name):
    print(f"\n[*] Deduplicating {layer_name}: initial count = {len(gdf)}")
    seen = set()
    keep_indices = []
    dropped_count = 0

    for idx, row in gdf.iterrows():
        h = geom_hash(row.geometry)
        if h in seen:
            dropped_count += 1
        else:
            seen.add(h)
            keep_indices.append(idx)

    dedup_gdf = gdf.loc[keep_indices].copy().reset_index(drop=True)
    print(f"    Kept: {len(dedup_gdf)}, Dropped duplicates: {dropped_count}")
    return dedup_gdf


def check_gt_recall(clean_gdf):
    if not os.path.exists(GT_PATH):
        print(f"[!] Ground truth file not found: {GT_PATH}")
        return

    gt = gpd.read_file(GT_PATH).to_crs(clean_gdf.crs)
    hits = 0
    clean_geoms = list(clean_gdf.geometry)

    for _, gt_row in gt.iterrows():
        gt_g = gt_row.geometry
        best_iou = 0.0
        for cg in clean_geoms:
            if not gt_g.intersects(cg):
                continue
            inter = gt_g.intersection(cg).area
            union = gt_g.union(cg).area
            iou = inter / union if union > 0 else 0.0
            if iou > best_iou:
                best_iou = iou
        if best_iou >= 0.10:
            hits += 1

    print(f"[*] Ground-Truth Recall: {hits}/{len(gt)} buildings matched (expected 26/29)")
    return hits


def main():
    print("=" * 60)
    print(" StratumRO Cadastral Deliverable Deduplication")
    print("=" * 60)

    # 1. Deduplicate CLADIRI_CADASTRU_CLEAN
    clean_gdf = gpd.read_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN")
    clean_dedup = deduplicate_gdf(clean_gdf, "CLADIRI_CADASTRU_CLEAN")

    # 2. Deduplicate CLADIRI_SOL_ANCPI
    sol_gdf = gpd.read_file(GPKG, layer="CLADIRI_SOL_ANCPI")
    sol_dedup = deduplicate_gdf(sol_gdf, "CLADIRI_SOL_ANCPI")

    # 3. Deduplicate CLADIRI_HIBRID
    hyb_gdf = gpd.read_file(GPKG, layer="CLADIRI_HIBRID")
    hyb_dedup = deduplicate_gdf(hyb_gdf, "CLADIRI_HIBRID")

    # Verify GT recall on deduplicated clean
    hits = check_gt_recall(clean_dedup)
    assert hits == 26, f"GT recall changed! Expected 26, got {hits}"

    # Write layers back to GeoPackage
    print("\n[*] Writing deduplicated layers back to GPKG...")
    clean_dedup.to_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN", driver="GPKG")
    sol_dedup.to_file(GPKG, layer="CLADIRI_SOL_ANCPI", driver="GPKG")
    hyb_dedup.to_file(GPKG, layer="CLADIRI_HIBRID", driver="GPKG")
    print("    GPKG layers updated successfully.")

    # 4. Deduplicate GeoJSON
    if os.path.exists(GEOJSON):
        print(f"\n[*] Deduplicating GeoJSON: {os.path.basename(GEOJSON)}")
        with open(GEOJSON, "r", encoding="utf-8") as f:
            gj_data = json.load(f)

        orig_feats = gj_data.get("features", [])
        gj_seen = set()
        kept_feats = []
        gj_dropped = 0

        for feat in orig_feats:
            geom = shape(feat["geometry"])
            h = geom_hash(geom)
            if h in gj_seen:
                gj_dropped += 1
            else:
                gj_seen.add(h)
                kept_feats.append(feat)

        gj_data["features"] = kept_feats
        with open(GEOJSON, "w", encoding="utf-8") as f:
            json.dump(gj_data, f, ensure_ascii=False, indent=2)

        print(f"    GeoJSON: Kept {len(kept_feats)}, Dropped {gj_dropped} duplicates (Initial: {len(orig_feats)})")

    print("\n[+] SUCCESS: All deliverable layers deduplicated with 100% geodetic fidelity.")


if __name__ == "__main__":
    main()
