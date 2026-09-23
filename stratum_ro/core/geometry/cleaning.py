# -*- coding: utf-8 -*-
"""
StratumRO — Core Geometry Engine & Cleaning (Phase 3)
Concrete implementation of the IGeometryEngine contract.
Pure-Python, deterministic, agnostic of country-specific cadastre rules.
"""

from typing import Tuple, List, Optional
from shapely.geometry import Polygon
from shapely.ops import unary_union, polygonize
from shapely.validation import explain_validity, make_valid

from stratum_ro.contracts.geometry import IGeometryEngine
from stratum_ro.core.geometry.regularizer import orthogonalize_cad, remove_acute_spikes, _extract_largest_polygon
from stratum_ro.core.geometry.metrics import compute_hausdorff, compute_boundary_rmse


class CoreGeometryEngine(IGeometryEngine):
    """
    Standard implementation of IGeometryEngine for 2D computational geometry.
    """

    def regularize_90(self, polygon: Polygon, tolerance: float = 0.5) -> Polygon:
        """Regularizes polygon edges to 90 degrees."""
        clean_poly = _extract_largest_polygon(polygon)
        if clean_poly is None or clean_poly.is_empty:
            return polygon
        spikeless = remove_acute_spikes(clean_poly)
        return orthogonalize_cad(spikeless, tolerance=tolerance)

    def fit_canonical_rectangle(self, polygon: Polygon) -> Polygon:
        """Fits minimum rotated bounding rectangle."""
        if polygon is None or polygon.is_empty:
            return polygon
        return polygon.minimum_rotated_rectangle

    def validate_topology(self, polygon: Polygon) -> Tuple[bool, str]:
        """Validates GEOS topology and returns (is_valid, reason)."""
        if polygon is None or polygon.is_empty:
            return (False, "Empty or None geometry")
        if polygon.is_valid:
            return (True, "Valid geometry")
        return (False, explain_validity(polygon))

    def compute_area(self, polygon: Polygon) -> float:
        """Computes analytical polygon area."""
        if polygon is None or polygon.is_empty:
            return 0.0
        return float(polygon.area)

    def compute_perimeter(self, polygon: Polygon) -> float:
        """Computes polygon exterior perimeter."""
        if polygon is None or polygon.is_empty:
            return 0.0
        return float(polygon.length)

    def compute_hausdorff_distance(self, geom1: Polygon, geom2: Polygon) -> float:
        """Computes bidirectional Hausdorff distance with densification."""
        return compute_hausdorff(geom1, geom2)

    def compute_boundary_rmse(self, candidate: Polygon, reference: Polygon, sample_step_m: float = 0.2) -> float:
        """Computes Boundary RMSE between candidate and reference."""
        return compute_boundary_rmse(candidate, reference, sample_step_m=sample_step_m)

    def build_planar_partition(self, polygons: List[Polygon]) -> List[Polygon]:
        """
        Builds a planar partition from overlapping polygons using GEOS unary_union.
        Eliminates overlaps by resolving intersections into disjoint polygon partitions.
        """
        if not polygons:
            return []
        valid_polys = [p for p in polygons if p is not None and p.is_valid and not p.is_empty]
        if not valid_polys:
            return []
        
        # Unary union of all boundaries polygonized to form disjoint faces
        boundaries = [p.boundary for p in valid_polys]
        merged_lines = unary_union(boundaries)
        partitioned = list(polygonize(merged_lines))
        return [p for p in partitioned if p.is_valid and p.area > 1.0]
