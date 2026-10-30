"""SAM 2.1 boundary refinement of 2D roof proposals, measured against owner ADMIS roofs.

For every proposal of a scan GeoPackage: crop the orthophoto around it, prompt SAM 2.1 with the proposal
box and one positive point inside it (no ground truth is used), keep the SAM mask closest to the proposal,
vectorize + regularize it, and accept it only when it stays close to the proposal (IoU >= --min-agree)
and does not lower the V1 edge score. The report compares val ADMIS IoU before / after.

Every output polygon stays PENDING_OWNER_REVIEW.

    python compute/colab/scripts/sam21_roof_refine.py --data workspace/colab_2d_roof_dataset_v3 \
        --proposals <scan>/roof2d_proposals_epsg3844.gpkg --checkpoint models/sam2/sam2.1_hiera_large.pt --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from roof2d_data import rasterize  # noqa: E402
from scan_roof2d_aoi import GPKG_REVIEW, chip_for, iou_against, regularize  # noqa: E402

CONFIGS = {"large": "configs/sam2.1/sam2.1_hiera_l.yaml", "base_plus": "configs/sam2.1/sam2.1_hiera_b+.yaml",
           "small": "configs/sam2.1/sam2.1_hiera_s.yaml", "tiny": "configs/sam2.1/sam2.1_hiera_t.yaml"}


def mask_to_polygon(mask: np.ndarray, chip_t):
    """Largest outer contour of a boolean chip mask as a world polygon (or None)."""
    import cv2
    from shapely.geometry import Polygon

    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    cnt = max(contours, key=cv2.contourArea)
    if len(cnt) < 3:
        return None
    poly = Polygon([chip_t * (float(x) + 0.5, float(y) + 0.5) for x, y in cnt[:, 0, :]]).buffer(0)
    if poly.geom_type != "Polygon":
        poly = max(poly.geoms, key=lambda g: g.area)
    return poly if not poly.is_empty else None


def refine(data: Path, proposals: Path, checkpoint: Path, out: Path, size: str = "large",
           min_agree: float = 0.6, val_min_y: float | None = None) -> dict:
    import geopandas as gpd
    import rasterio
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    from shapely.strtree import STRtree

    from stratum_ro.core.qa_qc.simultaneous_2d_validator import validate_v1_visual_chip

    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    predictor = SAM2ImagePredictor(build_sam2(CONFIGS[size], str(checkpoint), device=device))
    with rasterio.open(data / "aoi_rgb.tif") as src:
        rgb = np.moveaxis(src.read(), 0, -1)
        transform = src.transform
    props = gpd.read_file(proposals, layer="proposals_all")
    vmin = val_min_y if val_min_y is not None else json.loads((data / "manifest.json").read_text())["split"]["val_min_y"]

    refined, decisions = [], []
    with torch.inference_mode(), torch.autocast(device, dtype=torch.bfloat16, enabled=device == "cuda"):
        for _, row in props.iterrows():
            g = row.geometry
            chip, px, _, chip_t = chip_for(g, rgb, transform, margin_m=6.0)
            if chip.shape[0] < 16 or chip.shape[1] < 16:
                refined.append(g)
                decisions.append("chip_too_small")
                continue
            pxa = np.asarray(px)
            box = np.array([pxa[:, 0].min(), pxa[:, 1].min(), pxa[:, 0].max(), pxa[:, 1].max()], dtype=np.float32)
            rp = g.representative_point()
            pt = np.array([[(~chip_t * (rp.x, rp.y))[0], (~chip_t * (rp.x, rp.y))[1]]], dtype=np.float32)
            predictor.set_image(np.ascontiguousarray(chip))
            masks, scores, _ = predictor.predict(point_coords=pt, point_labels=np.array([1]), box=box,
                                                 multimask_output=True)
            prop_mask = rasterize([g], chip_t, chip.shape[:2])
            ious = [(m.astype(bool) & prop_mask).sum() / max((m.astype(bool) | prop_mask).sum(), 1) for m in masks]
            best = int(np.argmax(ious))
            cand = mask_to_polygon(masks[best].astype(bool), chip_t)
            if cand is None or ious[best] < min_agree:
                refined.append(g)
                decisions.append("kept_model_disagree")
                continue
            cand = regularize(cand)
            v1_old = validate_v1_visual_chip(chip, [tuple(p) for p in px]).score
            v1_new = validate_v1_visual_chip(chip, [((~chip_t * xy)[0], (~chip_t * xy)[1]) for xy in cand.exterior.coords]).score
            if v1_new + 1e-6 < v1_old:
                refined.append(g)
                decisions.append("kept_model_v1")
            else:
                refined.append(cand)
                decisions.append("sam")

    adm = gpd.read_file(GPKG_REVIEW, layer="1_ADMIS_FORME_BUNE_2D").to_crs("EPSG:3844")
    val = [a for a in adm.geometry if a.centroid.y >= vmin + 15]
    before, after = list(props.geometry), refined
    t0, t1 = STRtree(before), STRtree(after)
    iou0 = [iou_against(a, before, t0)[0] for a in val]
    iou1 = [iou_against(a, after, t1)[0] for a in val]
    report = {
        "status": "PROPOSAL_PENDING_OWNER_REVIEW",
        "sam": size, "checkpoint": str(checkpoint), "min_agree": min_agree,
        "decisions": {k: decisions.count(k) for k in sorted(set(decisions))},
        "val_n": len(val),
        "val_mean_iou_model": round(float(np.mean(iou0)), 4), "val_mean_iou_sam": round(float(np.mean(iou1)), 4),
        "val_median_iou_model": round(float(np.median(iou0)), 4), "val_median_iou_sam": round(float(np.median(iou1)), 4),
        "val_share_ge_0_90_model": round(float(np.mean(np.array(iou0) >= 0.9)), 4),
        "val_share_ge_0_90_sam": round(float(np.mean(np.array(iou1) >= 0.9)), 4),
        "per_building": [{"iou_model": round(a, 4), "iou_sam": round(b, 4)} for a, b in zip(iou0, iou1)],
    }
    gdf = props.copy()
    gdf["geometry"] = refined
    gdf["sam_decision"] = decisions
    gdf.to_file(out / "roof2d_sam21_refined_epsg3844.gpkg", layer="proposals_sam21", driver="GPKG")
    (out / "sam21_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--proposals", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--size", choices=sorted(CONFIGS), default="large")
    ap.add_argument("--min-agree", type=float, default=0.6)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    r = refine(args.data, args.proposals, args.checkpoint, args.out, args.size, args.min_agree)
    print(json.dumps({k: v for k, v in r.items() if k != "per_building"}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
