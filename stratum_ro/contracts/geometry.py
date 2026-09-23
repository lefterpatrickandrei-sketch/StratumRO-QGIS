# -*- coding: utf-8 -*-
"""
StratumRO — Computational Geometry & Topology Contracts (Phase 2)
Generic mathematical contracts for polygon regularization, snapping,
simplification, and geodetic evaluation metrics.
"""

from typing import Any, Protocol, Tuple, runtime_checkable
from shapely.geometry import Polygon


@runtime_checkable
class IGeometryEngine(Protocol):
    """
    Contract for generic 2D computational geometry and topology operations.
    Agnostic of specific country cadastral laws.
    """
    def regularize_90(self, polygon: Polygon, tolerance: float = 0.5) -> Polygon:
        """
        Regularizes building footprint edges to orthogonal (90°) angles.
        """
        ...

    def fit_canonical_rectangle(self, polygon: Polygon) -> Polygon:
        """
        Fits minimum rotated bounding box / canonical 4-vertex rectangle.
        """
        ...

    def validate_topology(self, polygon: Polygon) -> Tuple[bool, str]:
        """
        Validates GEOS topology (self-intersection, ring orientation, validity).
        Returns (is_valid, error_reason).
        """
        ...

    def compute_area(self, polygon: Polygon) -> float:
        """Computes analytical 2D area (Gauss / Shoelace formula)."""
        ...

    def compute_perimeter(self, polygon: Polygon) -> float:
        """Computes boundary perimeter length in metric units."""
        ...

    def compute_hausdorff_distance(self, geom1: Polygon, geom2: Polygon) -> float:
        """Computes discrete Hausdorff distance between two geometries."""
        ...

    def compute_boundary_rmse(self, candidate: Polygon, reference: Polygon, sample_step_m: float = 0.2) -> float:
        """Computes Root Mean Square Error along the boundary contours."""
        ...
