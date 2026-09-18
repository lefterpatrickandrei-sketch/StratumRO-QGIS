# -*- coding: utf-8 -*-
"""
Test Full AOI Simplification — 150 Buildings (Tier 2)
=====================================================
Applies 90° cadastral simplification to ALL buildings in the extended
ground truth dataset (tier2_extended_gt.geojson), not just the initial 29.
"""
import os
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
import geopandas as gpd
from tools.generate_clean_cadastral_deliverables import simplify_cadastral_geometry

GT_PATH = os.path.join(PROJECT_ROOT, "data", "ground_truth", "tier2_extended_gt.geojson")

def main():
    t2 = gpd.read_file(GT_PATH)
    print(f"Testing cadastral simplification on ALL {len(t2)} buildings across the entire orthophoto AOI:\n")

    v_before = []
    v_after = []
    rect_count = 0
    area_deltas = []

    for idx, row in t2.iterrows():
        p = row.geometry
        if p is None or p.is_empty:
            continue

        # Handle MultiPolygon — take largest
        if p.geom_type == 'MultiPolygon':
            p = max(p.geoms, key=lambda g: g.area)

        vb = len(p.exterior.coords) - 1
        v_before.append(vb)

        s = simplify_cadastral_geometry(p, tol=0.80)
        va = len(s.exterior.coords) - 1
        v_after.append(va)

        if va == 4:
            rect_count += 1

        area_delta_pct = abs(s.area - p.area) / (p.area + 1e-6) * 100
        area_deltas.append(area_delta_pct)

    n = len(v_after)
    print(f"Total buildings processed: {n}")
    print(f"Mean vertices BEFORE: {np.mean(v_before):.1f}")
    print(f"Mean vertices AFTER:  {np.mean(v_after):.1f}")
    print(f"Vertex reduction:     {(1 - np.mean(v_after)/np.mean(v_before))*100:.1f}%")
    print(f"Canonical 4-vertex rectangles (90°): {rect_count} ({rect_count/n*100:.1f}%)")
    print(f"Mean area change:     {np.mean(area_deltas):.2f}%")
    print(f"Max area change:      {np.max(area_deltas):.2f}%")

    # Pass/fail
    if np.mean(v_after) < 12 and rect_count >= n * 0.5:
        print("\n[PASS] Simplification quality gate met.")
    else:
        print(f"\n[WARN] Quality gate: mean_v={np.mean(v_after):.1f} (target <12), "
              f"rect_pct={rect_count/n*100:.1f}% (target >=50%)")

if __name__ == "__main__":
    main()
