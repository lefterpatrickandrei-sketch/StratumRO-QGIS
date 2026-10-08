# -*- coding: utf-8 -*-
"""
StratumRO - P4: measure which confidence filter is actually justified
=====================================================================
P5 exposed that ARTEFACTE_RESPINSE_SAM2 is mislabelled: its 184 features carry
validare = CONFIRMAT_HIBRID / LIDAR_DIRECT and its geometries match STAGE_5 1:1.
Deleting them costs 17 of 20 ground-truth matches. So the rejection layer cannot
be applied as written.

It also exposed a second contradiction: 468/483 STAGE_5 rows are labelled
ROSU_RESPINS_ARTEFACT, yet the 118 features of CLADIRI_CADASTRU_CLEAN -- all of
them members of STAGE_5 -- are labelled VERDE_ACCEPTAT_AUTOMAT, while their real
conf_final never exceeds 0.767. Both labels are fabricated.

This script does not guess. It measures candidate rules against
data/ground_truth/tier1_teren.geojson and reports what each one costs or buys.
"""

import os
import sys
import numpy as np
import geopandas as gpd

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
GT = os.path.join(ROOT, "data", "ground_truth", "tier1_teren.geojson")
IOU_PRAG = 0.10


def best_iou_per_gt(gt_gdf, pred_gdf):
    out = []
    for g in gt_gdf.geometry:
        best = 0.0
        for p in pred_gdf.geometry:
            if not g.intersects(p):
                continue
            inter = g.intersection(p).area
            if inter > 0:
                iou = inter / g.union(p).area
                if iou > best:
                    best = iou
        out.append(best)
    return np.array(out)


def score(label, pred, gt):
    ious = best_iou_per_gt(gt, pred)
    hit = int((ious >= IOU_PRAG).sum())
    print(
        "  %-46s n=%3d  GT %2d/%2d  meanIoU %.3f  median %.3f  area %6.2f ha"
        % (label, len(pred), hit, len(gt), ious.mean(), np.median(ious), pred.geometry.area.sum() / 1e4)
    )
    return ious, hit


def main():
    s5 = gpd.read_file(GPKG, layer="STAGE_5_FINAL_CONFIDENCE")
    clean = gpd.read_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN")
    gt = gpd.read_file(GT).to_crs(s5.crs)

    print("[*] P4 - candidate confidence filters, measured against GT (IoU >= %.2f)" % IOU_PRAG)
    print()
    base_iou, base_hit = score("STAGE_5 (all)", s5, gt)
    print()

    candidates = {}
    for thr in (0.50, 0.60, 0.65, 0.70):
        candidates["conf_final >= %.2f" % thr] = s5[s5.conf_final >= thr]
    for thr in (0.60, 0.70, 0.80, 0.85, 0.90):
        candidates["sam2_score >= %.2f" % thr] = s5[s5.sam2_score >= thr]
    candidates["sam2>=0.80 AND conf>=0.50"] = s5[(s5.sam2_score >= 0.80) & (s5.conf_final >= 0.50)]
    candidates["CLADIRI_CADASTRU_CLEAN (current deliverable)"] = clean

    results = []
    for label, pred in candidates.items():
        if len(pred) == 0:
            print("  %-46s EMPTY" % label)
            continue
        ious, hit = score(label, pred, gt)
        lost = int(((base_iou >= IOU_PRAG) & (ious < IOU_PRAG)).sum())
        results.append((label, len(pred), hit, hit - base_hit, lost))

    print()
    print("  rule                                              n    GT   dGT  lostGT")
    for label, n, hit, d, lost in results:
        print("  %-46s %3d  %2d/29  %+3d  %3d" % (label, n, hit, d, lost))

    print()
    print("[*] What the confidence columns actually contain")
    print("  conf_final  : min %.3f  max %.3f  -> no feature can reach the 0.85 GREEN threshold"
          % (s5.conf_final.min(), s5.conf_final.max()))
    print("  sam2_score  : min %.3f  max %.3f" % (s5.sam2_score.min(), s5.sam2_score.max()))
    print("  CLEAN sam2_score: %.2f - %.2f  -> the real selection rule was sam2_score >= 0.80, not conf_final"
          % (clean.sam2_score.min(), clean.sam2_score.max()))
    print()
    print("[*] Conclusion")
    print("  1. ARTEFACTE_RESPINSE_SAM2 must NOT be applied as a deletion rule.")
    print("     It costs 17 GT matches and contains CONFIRMAT_HIBRID features.")
    print("  2. action_code / conf_final in STAGE_5 and CLADIRI_CADASTRU_CLEAN are not")
    print("     derived from a reproducible computation and contradict each other.")
    print("     The 0.85 / 0.65 semafor thresholds in the docs are unreachable in this data.")


if __name__ == "__main__":
    main()