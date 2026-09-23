# -*- coding: utf-8 -*-
"""
StratumRO — Core Computational Geometry: Evaluation Metrics (Phase 3)
Pure-Python, deterministic spatial metrics: IoU, Hausdorff, Boundary RMSE, Centroid Shift.
Zero QGIS dependencies. Zero AI/LLM dependencies.
"""

import math
from typing import List, Tuple, Optional
import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.validation import make_valid


def ensure_valid_polygon(geom) -> Optional[Polygon]:
    """Validates and converts geometry into a single valid Polygon."""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        valid_subs = [p for p in geom.geoms if isinstance(p, Polygon) and p.area > 1.0]
        if valid_subs:
            return max(valid_subs, key=lambda p: p.area)
    return None


def compute_iou(geom_pred: Polygon, geom_ref: Polygon) -> float:
    """
    Computes Intersection-over-Union (Jaccard Index).
    IoU = Area(P ∩ R) / Area(P ∪ R)
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return 0.0
    try:
        inter = geom_pred.intersection(geom_ref).area
        union = geom_pred.union(geom_ref).area
        if union <= 1e-9:
            return 0.0
        return float(np.clip(inter / union, 0.0, 1.0))
    except Exception:
        return 0.0


def compute_hausdorff(geom_pred: Polygon, geom_ref: Polygon, densify: float = 0.10) -> float:
    """
    Computes bidirectional Hausdorff distance with edge densification (GEOS C++).
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return float("inf")
    try:
        return float(shapely.hausdorff_distance(geom_pred, geom_ref, densify=densify))
    except Exception:
        return float(shapely.hausdorff_distance(geom_pred, geom_ref))


def sample_points_along_boundary(poly, step_m: float = 0.20) -> List[Tuple[float, float]]:
    """Samples points regularly along the exterior boundary."""
    if poly is None or poly.is_empty:
        return []
    geoms = poly.geoms if hasattr(poly, "geoms") else [poly]
    pts = []
    for g in geoms:
        if not hasattr(g, "exterior") or g.exterior is None:
            continue
        boundary = g.exterior
        length = boundary.length
        if length <= 0:
            continue
        num_samples = max(4, int(math.ceil(length / step_m)))
        distances = np.linspace(0, length, num_samples, endpoint=False)
        for d in distances:
            pt = boundary.interpolate(d)
            pts.append((pt.x, pt.y))
    return pts


def compute_boundary_rmse(geom_pred, geom_ref, sample_step_m: float = 0.20) -> float:
    """
    Computes symmetric Boundary RMSE via continuous contour sampling.
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return float("inf")

    pred_pts = sample_points_along_boundary(geom_pred, sample_step_m)
    ref_pts = sample_points_along_boundary(geom_ref, sample_step_m)

    if not pred_pts or not ref_pts:
        return float("inf")

    ref_boundary = geom_ref.boundary
    pred_boundary = geom_pred.boundary

    sq_errors = []
    for px, py in pred_pts:
        d = ref_boundary.distance(Point(px, py))
        sq_errors.append(d ** 2)

    for rx, ry in ref_pts:
        d = pred_boundary.distance(Point(rx, ry))
        sq_errors.append(d ** 2)

    return float(math.sqrt(sum(sq_errors) / len(sq_errors)))


def compute_centroid_shift(geom_pred: Polygon, geom_ref: Polygon) -> float:
    """
    Computes Euclidean distance between centroids of prediction and reference.
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return float("inf")
    return float(geom_pred.centroid.distance(geom_ref.centroid))


def compute_angular_deviation(poly: Polygon) -> float:
    """
    Measures mean angular deviation of polygon edges relative to orthogonal angles (90° / 180° / 270°).
    """
    if poly is None or poly.is_empty:
        return 0.0
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 3:
        return 0.0
    devs = []
    for i in range(n):
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length > 0.10:
            deg = math.degrees(math.atan2(dy, dx)) % 90.0
            dev = min(deg, 90.0 - deg)
            devs.append(dev)
    return float(np.mean(devs)) if devs else 0.0
