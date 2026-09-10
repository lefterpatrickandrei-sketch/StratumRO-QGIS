# -*- coding: utf-8 -*-
"""
StratumRO — Modul de Ablație Experimentală & Analiză Multi-Configurație (Poarta 4)
================================================================================
Evaluează impactul incremental al fiecărui subsistem din pipeline conform cerințelor brief-ului:
  - Configurația A: Doar LiDAR nDSM (fără SAM 2, fără regularizare)
  - Configurația B: Doar SAM 2 optic (fără constrângeri de înălțime LiDAR)
  - Configurația C: Fuziune Hibridă LiDAR + SAM 2 ne-regularizată
  - Configurația D: Fuziune Hibridă + Regularizare CAD (Ortogonalizare 90° Manhattan)
  - Configurația E: Fuziune Hibridă + Regularizare + Retragere Streașină (-0.40m Sol ANCPI)

Generează matricea comparativă a indicatorilor IoU, Boundary RMSE, Hausdorff și Latență.
"""

import os
import sys
sys.path.insert(0, os.path.abspath('.'))
import time
from typing import Dict, Any, List
import numpy as np
import geopandas as gpd
from shapely.affinity import translate

from engine.evaluation import evaluate_dataset, DatasetEvaluationSummary


def run_ablation_matrix(
    pred_gpkg_path: str,
    ref_gt_path: str,
    shift_compensation: bool = True
) -> Dict[str, Any]:
    """
    Rulează matricea completă de ablație (Configurațiile A-E) și sintetizează performanța.
    """
    if not os.path.exists(pred_gpkg_path):
        raise FileNotFoundError(f"Lipsește fișierul de predicții: {pred_gpkg_path}")
    if not os.path.exists(ref_gt_path):
        raise FileNotFoundError(f"Lipsește fișierul de referință: {ref_gt_path}")

    gdf_ref = gpd.read_file(ref_gt_path)

    # Dacă se solicită compensarea biasului de datum WGS84->Stereo70 al OSM (+0.16m X, +2.78m Y)
    if shift_compensation:
        gdf_ref = gdf_ref.copy()
        gdf_ref.geometry = gdf_ref.geometry.apply(lambda g: translate(g, xoff=-0.16, yoff=-2.78))

    configs = [
        {"id": "Config A", "name": "Doar LiDAR nDSM", "layer": "CONFIG_A_LIDAR_ONLY", "eave_offset": 0.0},
        {"id": "Config B", "name": "Doar SAM 2 Optic", "layer": "CONFIG_B_SAM2_OPTIC_ONLY", "eave_offset": 0.0},
        {"id": "Config C", "name": "Hibrid Ne-regularizat", "layer": "CONFIG_C_HYBRID_RAW", "eave_offset": 0.0},
        {"id": "Config D", "name": "Hibrid + Regularizare 90°", "layer": "CONFIG_D_HYBRID_REGULARIZED", "eave_offset": 0.0},
        {"id": "Config E", "name": "Hibrid + Regularizare + Streașină", "layer": "CONFIG_E_HYBRID_REG_EAVE", "eave_offset": -0.40},
    ]

    results = []

    import pyogrio
    available_layers = pyogrio.list_layers(pred_gpkg_path)[:, 0]

    for cfg in configs:
        layer = cfg["layer"]
        if layer not in available_layers:
            raise ValueError(f"Stratul {layer} nu exista in {pred_gpkg_path}!")
        gdf_pred = gpd.read_file(pred_gpkg_path, layer=layer)

        t0 = time.perf_counter()
        summary = evaluate_dataset(gdf_pred, gdf_ref, min_iou_match=0.25)
        elapsed_s = time.perf_counter() - t0

        results.append({
            "config_id": cfg["id"],
            "config_name": cfg["name"],
            "layer_used": layer if layer in available_layers else "CLADIRI_HIBRID (simulat)",
            "true_positives": summary.true_positives,
            "false_positives": summary.false_positives,
            "false_negatives": summary.false_negatives,
            "clean_count": summary.clean_1_to_1_count,
            "clean_mean_iou": round(summary.clean_mean_iou, 3),
            "clean_mean_rmse_m": round(summary.clean_mean_boundary_rmse_m, 3),
            "clean_mean_hausdorff_m": round(summary.clean_mean_hausdorff_m, 3),
            "eval_time_ms": round(elapsed_s * 1000.0, 1)
        })

    return {
        "shift_compensated": shift_compensation,
        "configurations": results
    }


if __name__ == "__main__":
    pred_path = "workspace/output/ablation_layers.gpkg"
    ref_path = "data/ground_truth/tier4_osm_diagnostic_cluj.geojson"
    if os.path.exists(pred_path) and os.path.exists(ref_path):
        res = run_ablation_matrix(pred_path, ref_path, shift_compensation=True)
        print("=== MATRICEA DE ABLAȚIE (POARTA 4) ===")
        for r in res["configurations"]:
            print(f"{r['config_id']} ({r['config_name']:32s}) | IoU: {r['clean_mean_iou']:.3f} | RMSE: {r['clean_mean_rmse_m']:.3f} m | HD: {r['clean_mean_hausdorff_m']:.3f} m")
