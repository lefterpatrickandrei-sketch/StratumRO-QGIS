# -*- coding: utf-8 -*-
"""
Ground Truth Evaluation Tool Wrappers for StratumRO AI (MD 3 Section 17).
Interfaces engine/evaluation.py to compute rigorous spatial metrics:
IoU, Hausdorff distance, boundary RMSE, and Wilson score confidence intervals.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .security import resolve_sandboxed_path


def compare_ground_truth(
    pred_path: str,
    gt_path: str = "data/ground_truth/tier1_teren.geojson",
    output_report_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Evaluates building predictions against ground-truth cadastral reference polygons.
    Computes IoU, 95% Hausdorff distance, Boundary RMSE, and Wilson score CI.

    CRITICAL GUARDRAIL (MD 3 Section 17):
    Mathematical segmentation evaluation metrics are NOT proof of legal geodetic
    cadastral survey accuracy on the ground.
    """
    p_pred = resolve_sandboxed_path(pred_path, must_exist=True)
    p_gt = resolve_sandboxed_path(gt_path, must_exist=True)

    from engine.evaluation import evaluate_dataset
    import geopandas as gpd

    gdf_pred = gpd.read_file(str(p_pred))
    gdf_ref = gpd.read_file(str(p_gt))

    # Run core evaluation
    summary = evaluate_dataset(
        gdf_pred=gdf_pred,
        gdf_ref=gdf_ref,
        min_iou_match=0.50
    )

    # Format structured result
    res = {
        "status": "success",
        "reference_file": p_gt.name,
        "prediction_file": p_pred.name,
        "total_references": summary.total_references,
        "total_predictions": summary.total_predictions,
        "true_positives": summary.true_positives,
        "false_positives": summary.false_positives,
        "false_negatives": summary.false_negatives,
        "precision": round(summary.precision, 4),
        "recall": round(summary.recall, 4),
        "f1_score": round(summary.f1_score, 4),
        "metrics": {
            "mean_iou": round(summary.mean_iou, 4),
            "mean_hausdorff_m": round(summary.mean_hausdorff_m, 4),
            "mean_boundary_rmse_m": round(summary.mean_boundary_rmse_m, 4),
            "mean_centroid_shift_m": round(summary.mean_centroid_disp_m, 4),
            "ancpi_conform_count": summary.ancpi_conform_count,
            "pug_acceptable_count": summary.pug_acceptable_count,
            "rejected_count": summary.rejected_count,
            "ancpi_compliance_rate_pct": summary.ancpi_compliance_rate_pct,
        },
        "geodetic_disclaimer": (
            "DEFENSIBLE POSITIONING: These metrics evaluate mathematical overlap and contour agreement "
            "against 2D reference vectors. They DO NOT constitute or replace physical terrestrial survey "
            "coordinates (Total Station / GNSS RTK) required for legal registration under ANCPI Ordinul 600/2023."
        )
    }

    if output_report_path:
        out_p = resolve_sandboxed_path(output_report_path)
        import json
        with open(out_p, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        res["saved_report_path"] = str(out_p)

    return res
