# -*- coding: utf-8 -*-
"""
StratumRO - P2: diagnose the destructive safe-margin filter
==========================================================
tools/apply_safe_margin_full_ortho.py:61 does
    if raw_footprint.geom_type == 'MultiPolygon':
        raw_footprint = max(raw_footprint.geoms, key=lambda p: p.area)
so when the orthophoto VRT is assembled from several flight strips, every strip
except the largest one is thrown away. Buildings standing on a valid, fully
photographed strip are then declared unsafe and deleted from the deliverable.

This script measures the footprint before and after that reduction and counts
how many of the 61 rejected buildings are actually deep inside valid imagery.
"""

import os
import sys
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.features
from shapely.geometry import shape
from shapely.ops import unary_union

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VRT = os.path.join(ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
GT = os.path.join(ROOT, "data", "ground_truth", "tier1_teren.geojson")
MIN_AREA = 5000.0


def main():
    print("[*] P2 - safe margin diagnosis")
    with rasterio.open(VRT) as src:
        scale = 10
        data = src.read(out_shape=(src.count, src.height // scale, src.width // scale))
        mask = (np.sum(data, axis=0) > 15).astype(np.uint8)
        aff = src.transform * src.transform.scale(scale, scale)
        geoms = []
        for geom_dict, val in rasterio.features.shapes(mask, transform=aff):
            if val == 1:
                g = shape(geom_dict)
                if g.area > MIN_AREA:
                    geoms.append(g)
        total_px = src.count, src.height, src.width
        raster_bounds = tuple(src.bounds)
    print("    raster: %d bands %dx%d px, bounds %s" % (total_px[0], total_px[1], total_px[2], [round(b) for b in raster_bounds]))

    raw = unary_union(geoms)
    parts = list(raw.geoms) if raw.geom_type == "MultiPolygon" else [raw]
    parts = sorted(parts, key=lambda p: p.area, reverse=True)
    print()
    print("    valid-image polygons found: %d" % len(parts))
    for i, p in enumerate(parts[:12]):
        print("      #%-2d %12.1f m2  = %6.3f ha  (%.1f%% of union)" % (i + 1, p.area, p.area / 1e4, 100 * p.area / raw.area))

    union_area = raw.area
    biggest = parts[0]
    print()
    print("    UNION of all strips : %12.1f m2 = %.3f ha" % (union_area, union_area / 1e4))
    print("    LARGEST strip only  : %12.1f m2 = %.3f ha" % (biggest.area, biggest.area / 1e4))
    print("    THROWN AWAY         : %12.1f m2 = %.3f ha  (%.1f%% of valid imagery)"
          % (union_area - biggest.area, (union_area - biggest.area) / 1e4, 100 * (union_area - biggest.area) / union_area))

    for buf in (-10.0,):
        sm_all = raw.simplify(2.0, preserve_topology=True).buffer(buf, join_style=2).simplify(1.5, preserve_topology=True)
        sm_one = biggest.simplify(2.0, preserve_topology=True).buffer(buf, join_style=2).simplify(1.5, preserve_topology=True)
        print()
        print("    safe margin %.1f m : union-based %.3f ha   largest-only-based %.3f ha   lost %.3f ha"
              % (buf, sm_all.area / 1e4, sm_one.area / 1e4, (sm_all.area - sm_one.area) / 1e4))

    print()
    print("[*] How the rejected buildings relate to valid imagery")
    elim = gpd.read_file(GPKG, layer="CLADIRI_ELIMINATE_MARGINE_UNSAFE")
    hyb = gpd.read_file(GPKG, layer="CLADIRI_HIBRID")
    gt = gpd.read_file(GT).to_crs(hyb.crs)

    deep_union = 0
    deep_big = 0
    for g in elim.geometry:
        if raw.contains(g):
            deep_union += 1
        if biggest.contains(g):
            deep_big += 1
    print("    CLADIRI_ELIMINATE_MARGINE_UNSAFE : %d" % len(elim))
    print("      fully inside the UNION of all strips : %d" % deep_union)
    print("      fully inside the LARGEST strip only  : %d" % deep_big)

    sm_one = biggest.simplify(2.0, preserve_topology=True).buffer(-10.0, join_style=2).simplify(1.5, preserve_topology=True)
    sm_all = raw.simplify(2.0, preserve_topology=True).buffer(-10.0, join_style=2).simplify(1.5, preserve_topology=True)
    print()
    print("[*] Effect on the deliverable set (HYBRID = 179 candidates)")
    for label, sm in (("largest-strip-only (current code)", sm_one), ("union-of-all-strips (fixed)", sm_all)):
        kept = [g for g in hyb.geometry if sm.contains(g)]
        kept_g = gpd.GeoDataFrame(geometry=kept, crs=hyb.crs)
        ious = []
        for g in gt.geometry:
            best = 0.0
            for p in kept_g.geometry:
                if g.intersects(p):
                    inter = g.intersection(p).area
                    if inter > 0:
                        best = max(best, inter / g.union(p).area)
            ious.append(best)
        ious = np.array(ious)
        print("    %-32s kept %3d  GT %2d/29  meanIoU %.3f  area %6.2f ha"
              % (label, len(kept), int((ious >= 0.10).sum()), ious.mean(), kept_g.area.sum() / 1e4))


if __name__ == "__main__":
    main()