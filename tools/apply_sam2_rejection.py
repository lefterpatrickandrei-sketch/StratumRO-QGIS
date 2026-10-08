# -*- coding: utf-8 -*-
"""
StratumRO - P5: Reject SAM2 artefacts from the deliverable chain
==============================================================
Defect #5: all 184 features of ARTEFACTE_RESPINSE_SAM2 were still present in
STAGE_5_FINAL_CONFIDENCE (184/184 with >50% overlap). The rejection layer was
written but never applied.

This script applies the rejection, then re-measures ground-truth recall so the
removal can be justified or reverted on numbers, not on trust.

Containment rule (deterministic):
  a STAGE_5 feature is dropped when the union of ARTEFACTE_RESPINSE_SAM2 covers
  more than REJECT_COVER of its own area. 50% = the majority of the footprint is
  the rejected artefact, so the feature IS the artefact. A large real building
  that merely touches a rejected shed stays in.

Writes:
  workspace/output/p5_rejected_sam2_applied.csv   per-feature decision trail
  rewrites STAGE_5_FINAL_CONFIDENCE
"""

import os
import sys
import csv
import numpy as np
import geopandas as gpd
from shapely.ops import unary_union

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
GT = os.path.join(ROOT, "data", "ground_truth", "tier1_teren.geojson")
CSV_OUT = os.path.join(ROOT, "workspace", "output", "p5_rejected_sam2_applied.csv")

S5 = "STAGE_5_FINAL_CONFIDENCE"
REJ = "ARTEFACTE_RESPINSE_SAM2"
CLEAN = "CLADIRI_CADASTRU_CLEAN"
REJECT_COVER = 0.50
IOU_PRAG = 0.10


def best_iou_per_gt(gt_gdf, pred_gdf):
    """For every GT building return the IoU of its single best match in pred."""
    out = []
    for _, row in gt_gdf.iterrows():
        g = row.geometry
        best = 0.0
        for p in pred_gdf.geometry:
            if not g.intersects(p):
                continue
            inter = g.intersection(p).area
            if inter <= 0:
                continue
            iou = inter / (g.union(p).area)
            if iou > best:
                best = iou
        out.append(best)
    return np.array(out)


def recall(gt_gdf, pred_gdf, label):
    ious = best_iou_per_gt(gt_gdf, pred_gdf)
    hit = int((ious >= IOU_PRAG).sum())
    print(
        "    %-34s GT matched %2d/%2d  meanIoU %.3f  medianIoU %.3f"
        % (label, hit, len(gt_gdf), ious.mean(), np.median(ious))
    )
    return ious


def main():
    print("[*] P5 - apply SAM2 artefact rejection")
    s5 = gpd.read_file(GPKG, layer=S5)
    rej = gpd.read_file(GPKG, layer=REJ)
    clean = gpd.read_file(GPKG, layer=CLEAN)
    gt = gpd.read_file(GT).to_crs(s5.crs)
    print("    STAGE_5=%d  ARTEFACTE_RESPINSE_SAM2=%d  GT=%d" % (len(s5), len(rej), len(gt)))

    rej_union = unary_union(list(rej.geometry))

    rows = []
    keep_mask = []
    for i, row in s5.iterrows():
        g = row.geometry
        area = g.area
        covered = 0.0
        if g.intersects(rej_union):
            inter = g.intersection(rej_union).area
            if area > 0:
                covered = inter / area
        drop = covered > REJECT_COVER
        keep_mask.append(not drop)
        rows.append(
            {
                "id": row["id"],
                "area_m2": round(area, 2),
                "sam2_score": row.get("sam2_score"),
                "action_code": row.get("action_code"),
                "rejected_cover_frac": round(covered, 4),
                "decision": "DROPPED_REJECTED_SAM2" if drop else "KEPT",
            }
        )

    dropped = [r for r, k in zip(rows, keep_mask) if not k]
    print("    coverage rule: drop when rejected artefacts cover > %.0f%% of the feature" % (REJECT_COVER * 100))
    print("    DROPPED %d / %d   KEPT %d" % (len(dropped), len(s5), len(s5) - len(dropped)))
    if dropped:
        cov = np.array([r["rejected_cover_frac"] for r in dropped])
        ar = np.array([r["area_m2"] for r in dropped])
        print("    dropped coverage_frac: min %.3f  median %.3f  max %.3f" % (cov.min(), np.median(cov), cov.max()))
        print("    dropped area_m2      : min %.1f  median %.1f  max %.1f  sum %.2f ha"
              % (ar.min(), np.median(ar), ar.max(), ar.sum() / 10000.0))

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)

    print("[*] Ground-truth recall check (IoU >= %.2f against tier1_teren.geojson)" % IOU_PRAG)
    recall(gt, s5, "STAGE_5 before rejection")
    s5_new = s5[keep_mask].reset_index(drop=True)
    ious_after = recall(gt, s5_new, "STAGE_5 after rejection")
    recall(gt, clean, "CLADIRI_CADASTRU_CLEAN (deliverable)")

    before = best_iou_per_gt(gt, s5)
    lost = np.where((before >= IOU_PRAG) & (ious_after < IOU_PRAG))[0]
    gained = np.where((before < IOU_PRAG) & (ious_after >= IOU_PRAG))[0]
    print("    GT lost by the removal : %d  %s" % (len(lost), list(lost + 1)))
    print("    GT gained (unexpected) : %d  %s" % (len(gained), list(gained + 1)))

    if len(lost):
        print("[!] REFUSING to write - removal costs ground-truth matches. Investigate first.")
        return 1

    s5_new["rejected_sam2_applied"] = True
    s5_new.to_file(GPKG, layer=S5, driver="GPKG")
    print("    rewrote %s : %d features" % (S5, len(s5_new)))

    still = sum(1 for g in s5_new.geometry if g.intersects(rej_union) and g.intersection(rej_union).area / max(g.area, 1e-9) > 0.5)
    print("    verification: features still >50% covered by rejected artefacts = %d" % still)
    print("[*] DONE -> %s" % os.path.relpath(CSV_OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())