# -*- coding: utf-8 -*-
"""
StratumRO — Core Geometry Package
"""

from stratum_ro.core.geometry.regularizer import (
    _extract_largest_polygon,
    remove_acute_spikes,
    count_macro_reflex_corners,
    compute_orthogonality_ratio,
    orthogonalize_cad,
)
from stratum_ro.core.geometry.metrics import (
    ensure_valid_polygon,
    compute_iou,
    compute_hausdorff,
    compute_boundary_rmse,
    compute_centroid_shift,
    compute_angular_deviation,
)
from stratum_ro.core.geometry.cleaning import CoreGeometryEngine

__all__ = [
    "_extract_largest_polygon",
    "remove_acute_spikes",
    "count_macro_reflex_corners",
    "compute_orthogonality_ratio",
    "orthogonalize_cad",
    "ensure_valid_polygon",
    "compute_iou",
    "compute_hausdorff",
    "compute_boundary_rmse",
    "compute_centroid_shift",
    "compute_angular_deviation",
    "CoreGeometryEngine",
]
