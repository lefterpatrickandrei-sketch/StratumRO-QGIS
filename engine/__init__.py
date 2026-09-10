# -*- coding: utf-8 -*-
"""
StratumRO Evaluation & Quantitative Geodetic Verification Engine.
Provides mathematical metrics (IoU, Hausdorff, Boundary RMSE, Shape metrics)
and compliance classification for ANCPI Ordinul 600/2023 and MDLPA Ordinul 904/2023.
"""

from .evaluation import (
    compute_iou,
    compute_hausdorff,
    compute_boundary_rmse,
    compute_shape_metrics,
    evaluate_dataset,
    DatasetEvaluationSummary,
    BuildingEvaluationResult,
)

# Alias for backwards compatibility / ergonomic imports
EvaluationReport = DatasetEvaluationSummary

__all__ = [
    "compute_iou",
    "compute_hausdorff",
    "compute_boundary_rmse",
    "compute_shape_metrics",
    "evaluate_dataset",
    "DatasetEvaluationSummary",
    "BuildingEvaluationResult",
    "EvaluationReport",
]
