# -*- coding: utf-8 -*-
"""
Authentic SAM 2 Inference & Benchmark Pipeline for Cluj Development AOI
=======================================================================
Phase 2 Evidence-First Execution:
1. Generates building candidates strictly from LiDAR nDSM (h >= 2.5m, Area >= 25m2).
2. Runs Meta SAM 2 Hiera on GPU using optical orthophoto pixels.
3. Vectorizes and saves RAW AI PREDICTIONS (no regularization).
4. Runs deterministic 90° cadastral regularization and saves REGULARIZED PREDICTIONS.
5. Computes quantitative benchmark metrics against deduplicated Ground Truth.
ZERO Ground Truth leakage into the inference path.
"""

import os
import sys
import time
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import reproject, Resampling
import geopandas as gpd
from shapely.geometry import shape, box, Polygon, MultiPolygon
from shapely.validation import make_valid
import torch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from stratum_ro.vectorizer import CadastralVectorizer, compute_orthogonality_ratio
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

ORTHO_PATH = os.path.join(PROJECT_ROOT, "workspace", "e2e", "04_orthophoto", "active_ortho_crop.tif")
NDSM_PATH = os.path.join(PROJECT_ROOT, "workspace", "derived", "cluj_ndsm_1m.tif")
REF_PATH = os.path.join(PROJECT_ROOT, "data", "derived_reference", "cluj_combined_unique_150.geojson")
OUT_RAW_PATH = os.path.join(PROJECT_ROOT, "workspace", "predictions", "cluj_raw_sam2_predictions.geojson")
OUT_REG_PATH = os.path.join(PROJECT_ROOT, "workspace", "predictions", "cluj_regularized_predictions.geojson")
METRICS_JSON_PATH = os.path.join(PROJECT_ROOT, "reports", "cluj", "sam2_cluj_benchmark_metrics.json")


def run_pipeline():
    start_time = time.time()
    print("=" * 70)
    print("  STRATUMRO PHASE 2 — AUTHENTIC SAM 2 CLUJ INFERENCE PIPELINE")
    print("=" * 70)

    # 1. Load Orthophoto
    print(f"[*] Loading orthophoto: {ORTHO_PATH}")
    with rasterio.open(ORTHO_PATH) as src_ortho:
        ortho_img = src_ortho.read([1, 2, 3])  # (3, H, W)
        ortho_trans = src_ortho.transform
        ortho_crs = src_ortho.crs
        h, w = src_ortho.height, src_ortho.width
        ortho_bounds = src_ortho.bounds

    print(f"    Dimensions: {w} x {h} pixels, Resolution: {src_ortho.res[0]:.3f} m, CRS: {ortho_crs}")
    image_rgb = np.transpose(ortho_img, (1, 2, 0))  # (H, W, 3)

    # 2. Resample nDSM to match Orthophoto crop grid
    print(f"[*] Extracting nDSM candidate layer: {NDSM_PATH}")
    with rasterio.open(NDSM_PATH) as src_ndsm:
        ndsm_crop = np.zeros((h, w), dtype=np.float32)
        reproject(
            source=rasterio.band(src_ndsm, 1),
            destination=ndsm_crop,
            src_transform=src_ndsm.transform,
            src_crs=src_ndsm.crs,
            dst_transform=ortho_trans,
            dst_crs=ortho_crs,
            resampling=Resampling.bilinear
        )

    # 3. Generate Candidates from LiDAR nDSM (h >= 2.5m, area >= 25m2)
    # 25 m2 = 25 / (0.2 * 0.2) = 625 pixels at 0.2m resolution
    height_mask = (ndsm_crop >= 2.5).astype(np.uint8)
    from scipy.ndimage import label, find_objects
    labeled_blobs, num_blobs = label(height_mask)
    print(f"    Raw height blobs detected: {num_blobs}")

    candidates = []
    min_pixels = int(25.0 / (src_ortho.res[0] * src_ortho.res[1]))  # 625 pixels

    slices = find_objects(labeled_blobs)
    for idx, slc in enumerate(slices):
        if slc is None:
            continue
        blob_mask = (labeled_blobs[slc] == (idx + 1))
        pixel_count = int(np.sum(blob_mask))
        if pixel_count < min_pixels:
            continue

        ymin, ymax = slc[0].start, slc[0].stop
        xmin, xmax = slc[1].start, slc[1].stop

        # Centroid in pixels
        y_indices, x_indices = np.where(blob_mask)
        cy = int(ymin + np.mean(y_indices))
        cx = int(xmin + np.mean(x_indices))

        # Height stats
        blob_heights = ndsm_crop[slc][blob_mask]
        mean_h = float(np.mean(blob_heights))
        max_h = float(np.max(blob_heights))

        candidates.append({
            "cand_id": f"CAND_{len(candidates)+1:03d}",
            "bbox_px": [xmin, ymin, xmax, ymax],
            "center_px": [cx, cy],
            "area_m2": pixel_count * (src_ortho.res[0] * src_ortho.res[1]),
            "mean_h": mean_h,
            "max_h": max_h
        })

    print(f"[+] Valid building candidates generated from nDSM: {len(candidates)}")

    # 4. Load Meta SAM 2 Model
    ckpt_path = os.path.join(PROJECT_ROOT, "models", "sam2", "sam2_hiera_tiny.pt")
    cfg_name = "sam2_hiera_t.yaml"
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[*] Loading SAM 2 model ({device}): {ckpt_path}")
    model = build_sam2(cfg_name, ckpt_path, device=device)
    predictor = SAM2ImagePredictor(model)

    print("[*] Setting image embedding in SAM 2 predictor...")
    t0_embed = time.time()
    predictor.set_image(image_rgb)
    print(f"    Image encoded in {time.time() - t0_embed:.2f} s")

    # 5. Execute Real SAM 2 Inference per Candidate
    print(f"[*] Running SAM 2 inference on {len(candidates)} candidates...")
    raw_predictions = []
    vectorizer = CadastralVectorizer(crs="EPSG:3844")

    for cand in candidates:
        bx = np.array(cand["bbox_px"])
        pt = np.array([cand["center_px"]])
        pt_label = np.array([1])

        # Prompt with box + center point
        masks, scores, _ = predictor.predict(
            point_coords=pt,
            point_labels=pt_label,
            box=bx,
            multimask_output=False
        )

        pred_mask = masks[0].astype(np.uint8)
        pred_score = float(scores[0])

        # Vectorize mask to Stereo 70 coordinates
        poly_shapes = list(shapes(pred_mask, mask=(pred_mask == 1), transform=ortho_trans))
        if not poly_shapes:
            continue

        polys = [shape(geom) for geom, val in poly_shapes if val == 1]
        valid_polys = [make_valid(p) for p in polys if p.is_valid or make_valid(p).area > 15.0]
        if not valid_polys:
            continue

        # Keep largest connected polygon
        largest = max(valid_polys, key=lambda p: p.area)
        if isinstance(largest, MultiPolygon):
            largest = max(largest.geoms, key=lambda p: p.area)

        if largest.area < 15.0:
            continue

        raw_predictions.append({
            "pred_id": f"RAW_SAM2_{len(raw_predictions)+1:03d}",
            "cand_id": cand["cand_id"],
            "sam2_score": pred_score,
            "mean_height_m": cand["mean_h"],
            "max_height_m": cand["max_h"],
            "raw_area_m2": float(largest.area),
            "raw_vertex_count": len(largest.exterior.coords) - 1,
            "raw_ortho_ratio": compute_orthogonality_ratio(largest),
            "geometry": largest
        })

    print(f"[+] Successfully segmented {len(raw_predictions)} raw building footprints.")

    # Save RAW predictions
    gdf_raw = gpd.GeoDataFrame(raw_predictions, crs="EPSG:3844")
    os.makedirs(os.path.dirname(OUT_RAW_PATH), exist_ok=True)
    gdf_raw.to_file(OUT_RAW_PATH, driver="GeoJSON")
    print(f"    Saved raw predictions: {OUT_RAW_PATH}")

    # 6. Step 9: Deterministic 90° Cadastral Regularization
    print("[*] Running deterministic 90° cadastral regularization...")
    regularized_predictions = []

    for item in raw_predictions:
        raw_poly = item["geometry"]
        reg_poly = vectorizer.clean_cad_polygon(raw_poly, tolerance=0.7)

        if reg_poly is None or reg_poly.is_empty or reg_poly.area < 15.0:
            reg_poly = raw_poly

        v_count = len(reg_poly.exterior.coords) - 1
        ortho_ratio = compute_orthogonality_ratio(reg_poly)
        is_rect = (v_count == 4 and ortho_ratio >= 0.85)

        regularized_predictions.append({
            "pred_id": f"REG_CAD_{len(regularized_predictions)+1:03d}",
            "raw_pred_id": item["pred_id"],
            "sam2_score": item["sam2_score"],
            "mean_height_m": item["mean_height_m"],
            "max_height_m": item["max_height_m"],
            "reg_area_m2": float(reg_poly.area),
            "vertex_count_raw": item["raw_vertex_count"],
            "vertex_count_reg": v_count,
            "ortho_ratio_raw": item["raw_ortho_ratio"],
            "ortho_ratio_reg": ortho_ratio,
            "is_canonical_rect": is_rect,
            "geometry": reg_poly
        })

    gdf_reg = gpd.GeoDataFrame(regularized_predictions, crs="EPSG:3844")
    gdf_reg.to_file(OUT_REG_PATH, driver="GeoJSON")
    print(f"    Saved regularized predictions: {OUT_REG_PATH}")

    # 7. Step 10: Compute Quantitative Benchmark Metrics vs Ground Truth
    print("[*] Evaluating predictions against Ground Truth...")
    ref_gdf = gpd.read_file(REF_PATH)
    crop_geom = box(ortho_bounds.left, ortho_bounds.bottom, ortho_bounds.right, ortho_bounds.top)
    ref_in_aoi = ref_gdf[ref_gdf.geometry.intersects(crop_geom)].copy()
    print(f"    Reference buildings inside active AOI: {len(ref_in_aoi)}")

    raw_metrics = _evaluate_against_reference(gdf_raw, ref_in_aoi, name="RAW_SAM2")
    reg_metrics = _evaluate_against_reference(gdf_reg, ref_in_aoi, name="REGULARIZED_CAD")

    # Summary report
    summary = {
        "execution_date": "2026-09-19",
        "runtime_seconds": round(time.time() - start_time, 2),
        "device": device,
        "aoi_extent": [ortho_bounds.left, ortho_bounds.bottom, ortho_bounds.right, ortho_bounds.top],
        "candidates_detected": len(candidates),
        "raw_predictions_count": len(raw_predictions),
        "regularized_predictions_count": len(regularized_predictions),
        "reference_buildings_in_aoi": len(ref_in_aoi),
        "raw_metrics": raw_metrics,
        "regularized_metrics": reg_metrics
    }

    with open(METRICS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"[+] Benchmark metrics saved: {METRICS_JSON_PATH}")
    print("\n" + "=" * 70)
    print("  BENCHMARK SUMMARY RESULTS:")
    print("=" * 70)
    print(f"  Candidates generated: {len(candidates)} | Reference in AOI: {len(ref_in_aoi)}")
    print(f"  RAW AI:         TP={raw_metrics['tp']}, FP={raw_metrics['fp']}, FN={raw_metrics['fn']}, Precision={raw_metrics['precision']:.3f}, Recall={raw_metrics['recall']:.3f}, F1={raw_metrics['f1']:.3f}, Mean IoU={raw_metrics['mean_iou']:.3f}")
    print(f"  REGULARIZED:    TP={reg_metrics['tp']}, FP={reg_metrics['fp']}, FN={reg_metrics['fn']}, Precision={reg_metrics['precision']:.3f}, Recall={reg_metrics['recall']:.3f}, F1={reg_metrics['f1']:.3f}, Mean IoU={reg_metrics['mean_iou']:.3f}")
    print(f"  Vertex count reduction: {np.mean([r['vertex_count_raw'] for r in regularized_predictions]):.1f} -> {np.mean([r['vertex_count_reg'] for r in regularized_predictions]):.1f}")
    print(f"  90° Orthogonal ratio:   {np.mean([r['ortho_ratio_raw'] for r in regularized_predictions]):.2f} -> {np.mean([r['ortho_ratio_reg'] for r in regularized_predictions]):.2f}")
    print("=" * 70)


def _evaluate_against_reference(pred_gdf, ref_gdf, iou_thresh=0.5, name="EVAL"):
    """Computes IoU-based detection and geometry metrics against reference."""
    matched_preds = set()
    matched_refs = set()
    ious = []
    dxs, dys, dists = [], [], []

    for p_idx, p_row in pred_gdf.iterrows():
        p_geom = p_row.geometry
        best_iou = 0.0
        best_r_idx = None

        for r_idx, r_row in ref_gdf.iterrows():
            r_geom = r_row.geometry
            if not p_geom.intersects(r_geom):
                continue
            intersection = p_geom.intersection(r_geom).area
            union = p_geom.union(r_geom).area
            if union > 0:
                iou = intersection / union
                if iou > best_iou:
                    best_iou = iou
                    best_r_idx = r_idx

        if best_iou >= iou_thresh:
            matched_preds.add(p_idx)
            matched_refs.add(best_r_idx)
            ious.append(best_iou)

            r_geom = ref_gdf.loc[best_r_idx].geometry
            dx = p_geom.centroid.x - r_geom.centroid.x
            dy = p_geom.centroid.y - r_geom.centroid.y
            dxs.append(dx)
            dys.append(dy)
            dists.append(np.sqrt(dx**2 + dy**2))

    tp = len(matched_refs)
    fp = len(pred_gdf) - len(matched_preds)
    fn = len(ref_gdf) - len(matched_refs)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "name": name,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "mean_iou": float(np.mean(ious)) if ious else 0.0,
        "median_iou": float(np.median(ious)) if ious else 0.0,
        "mean_dx": float(np.mean(dxs)) if dxs else 0.0,
        "mean_dy": float(np.mean(dys)) if dys else 0.0,
        "mae_2d": float(np.mean(dists)) if dists else 0.0,
        "rmse_2d": float(np.sqrt(np.mean(np.array(dists)**2))) if dists else 0.0
    }


if __name__ == "__main__":
    run_pipeline()
