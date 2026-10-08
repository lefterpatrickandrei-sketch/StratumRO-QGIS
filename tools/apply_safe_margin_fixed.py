# -*- coding: utf-8 -*-
"""
StratumRO - P2 fix: rebuild the safe-margin filter without destroying buildings
==========================================================================
Two bugs in tools/apply_safe_margin_full_ortho.py, both measured:

BUG A  buffer(-10.0, join_style=2) uses a MITRE join. At the concave corners of
       the flight footprint a mitred offset shoots far further inward than 10 m.
       Measured loss 72.335 m2 against the 38.143 m2 implied by the 3.814 m
       perimeter: 1.9x the area it should have removed.

BUG B  The footprint carries 204 interior rings (nodata gaps totalling 2.164 m2).
       A negative buffer grows every hole outward by 10 m, so buildings standing
       on valid imagery were rejected for sitting next to a nodata gap.

FIX  fill the interior rings, then erode the outer boundary with a ROUND join.
     The margin keeps its intended purpose - no building is delivered if it
     touches the edge of the photographed area - without inventing losses.

Measured against data/ground_truth/tier1_teren.geojson (IoU >= 0.10):
     current code : 118 kept, GT 24/29, meanIoU 0.779, 5.34 ha
     this fix     : 147 kept, GT 26/29, meanIoU 0.830, 6.33 ha

Writes a new tool and updates the three affected layers. The GeoPackage is
backed up by the caller before running.
"""

import os
import sys
import csv
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.features
from shapely.geometry import shape, Polygon
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
CSV_OUT = os.path.join(ROOT, "workspace", "output", "p2_safe_margin_decisions.csv")

MARGIN_M = -10.0
IOU_PRAG = 0.10
MIN_PATCH_AREA = 5000.0
EAVE_OFFSET_M = 0.40


def valid_image_footprint():
    """Union of every valid-image patch in the orthophoto, holes filled."""
    with rasterio.open(VRT) as src:
        scale = 10
        data = src.read(out_shape=(src.count, src.height // scale, src.width // scale))
        mask = (np.sum(data, axis=0) > 15).astype(np.uint8)
        aff = src.transform * src.transform.scale(scale, scale)
        geoms = [
            shape(gd)
            for gd, val in rasterio.features.shapes(mask, transform=aff)
            if val == 1 and shape(gd).area > MIN_PATCH_AREA
        ]
    raw = unary_union(geoms)
    if raw.geom_type == "MultiPolygon":
        raw = max(raw.geoms, key=lambda p: p.area)
    simplified = raw.simplify(2.0, preserve_topology=True)
    hole_count = len(simplified.interiors) if simplified.geom_type == "Polygon" else 0
    filled = Polygon(simplified.exterior) if simplified.geom_type == "Polygon" else simplified
    return filled, hole_count


def build_safe_margin(footprint, margin_m):
    """Erode the outer boundary only, with a round join."""
    return footprint.buffer(margin_m, join_style=1)


def recall(gt, pred_geoms):
    ious = []
    for g in gt.geometry:
        best = 0.0
        for p in pred_geoms:
            if g.intersects(p):
                inter = g.intersection(p).area
                if inter > 0:
                    best = max(best, inter / g.union(p).area)
        ious.append(best)
    ious = np.array(ious)
    return ious, int((ious >= IOU_PRAG).sum())


def main():
    print("[*] P2 fix - safe margin without collateral loss")
    footprint, holes = valid_image_footprint()
    print("    footprint after filling %d interior nodata rings: %.3f ha" % (holes, footprint.area / 1e4))

    safe = build_safe_margin(footprint, MARGIN_M)
    print("    safe margin %.1f m (round join): %.3f ha, loss %.3f ha" % (MARGIN_M, safe.area / 1e4, (footprint.area - safe.area) / 1e4))
    print("    perimeter-implied loss for reference: %.3f ha" % (footprint.exterior.length * abs(MARGIN_M) / 1e4))

    hyb = gpd.read_file(GPKG, layer="CLADIRI_HIBRID")
    gt = gpd.read_file(GT).to_crs(hyb.crs)

    old_safe = gpd.read_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN")
    old_elim = gpd.read_file(GPKG, layer="CLADIRI_ELIMINATE_MARGINE_UNSAFE")
    ious_old, hit_old = recall(gt, list(old_safe.geometry))
    print()
    print("[*] ground-truth check (IoU >= %.2f)" % IOU_PRAG)
    print("    before : %d buildings, GT %d/29, meanIoU %.3f" % (len(old_safe), hit_old, ious_old.mean()))

    rows = []
    safe_rows, unsafe_rows = [], []
    for _, row in hyb.iterrows():
        g = row.geometry
        keep = safe.contains(g)
        rec = {
            "id": row["id"],
            "area_m2": round(float(g.area), 2),
            "contains_check": bool(keep),
            "decision": "KEPT_SAFE" if keep else "DROPPED_MARGINE_UNSAFE",
        }
        rows.append(rec)
        if keep:
            safe_rows.append(row)
        else:
            item = dict(row)
            item["status_filtrare"] = "ELIMINAT_MARGINE_ORTOFOTO_UNSAFE"
            item["motiv"] = "Cladire atinge marginea zborului ortofoto (exclusa intentionat)"
            unsafe_rows.append(item)

    gdf_safe = gpd.GeoDataFrame(safe_rows, crs=hyb.crs).reset_index(drop=True)
    gdf_unsafe = gpd.GeoDataFrame(unsafe_rows, crs=hyb.crs).reset_index(drop=True)

    ious_new, hit_new = recall(gt, list(gdf_safe.geometry))
    print("    after  : %d buildings, GT %d/29, meanIoU %.3f" % (len(gdf_safe), hit_new, ious_new.mean()))
    print("    delta  : %+d buildings, %+d GT matches, %+.3f meanIoU"
          % (len(gdf_safe) - len(old_safe), hit_new - hit_old, ious_new.mean() - ious_old.mean()))

    lost = [i + 1 for i in range(len(gt)) if ious_old[i] >= IOU_PRAG > ious_new[i]]
    print("    GT lost by the fix: %d %s" % (len(lost), lost))
    gained = [i + 1 for i in range(len(gt)) if ious_old[i] < IOU_PRAG <= ious_new[i]]
    print("    GT gained by the fix: %d %s" % (len(gained), gained))

    # Recovered vs genuinely unsafe
    recovered = [g for g in old_elim.geometry if safe.contains(g)]
    print("    recovered from the previous elimination: %d of %d" % (len(recovered), len(old_elim)))
    print("    still unsafe on a real footprint edge   : %d" % (len(old_elim) - len(recovered)))

    if lost:
        print("[!] REFUSING to write - the fix costs ground-truth matches.")
        return 1

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)

    gdf_safe["area_m2"] = [round(float(g.area), 2) for g in gdf_safe.geometry]
    gdf_safe["perimeter_m"] = [round(float(g.length), 2) for g in gdf_safe.geometry]
    gdf_safe["is_temporary"] = False
    gdf_safe["structure_type"] = "CONSTRUCTIE_PERMANENTA"
    gdf_safe["category"] = "CLADIRE_CADASTRU_CLEAN"

    sol_rows = []
    for _, row in gdf_safe.iterrows():
        p = row.geometry
        p_sol = p.buffer(-EAVE_OFFSET_M, join_style=1)
        if not p_sol.is_valid or p_sol.is_empty or p_sol.area < 4.0:
            p_sol = p
        elif p_sol.geom_type == "MultiPolygon":
            p_sol = max(p_sol.geoms, key=lambda g: g.area)
        item = dict(row)
        item["category"] = "CLADIRI_SOL_ANCPI"
        item["area_sol_m2"] = round(float(p_sol.area), 2)
        item["eave_offset_m"] = EAVE_OFFSET_M
        item["geometry"] = p_sol
        sol_rows.append(item)
    gdf_sol = gpd.GeoDataFrame(sol_rows, crs=hyb.crs).reset_index(drop=True)

    margin = gpd.GeoDataFrame(
        [{
            "id": 1,
            "name": "LIMITA_SAFE_MARGIN_ORTOFOTO_10M",
            "buffer_m": MARGIN_M,
            "area_m2": round(float(safe.area), 2),
            "join_style": "round",
            "holes_filled": holes,
            "geometry": safe,
        }],
        crs=hyb.crs,
    )

    gdf_safe.to_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN", driver="GPKG")
    gdf_sol.to_file(GPKG, layer="CLADIRI_SOL_ANCPI", driver="GPKG")
    if len(gdf_unsafe):
        gdf_unsafe.to_file(GPKG, layer="CLADIRI_ELIMINATE_MARGINE_UNSAFE", driver="GPKG")
    margin.to_file(GPKG, layer="MARGINE_SIGURANTA_ORTOFOTO", driver="GPKG")
    print("    wrote CLADIRI_CADASTRU_CLEAN=%d, CLADIRI_SOL_ANCPI=%d, ELIMINATE=%d, MARGINE_SIGURANTA_ORTOFOTO"
          % (len(gdf_safe), len(gdf_sol), len(gdf_unsafe)))
    print("[*] DONE -> %s" % os.path.relpath(CSV_OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())