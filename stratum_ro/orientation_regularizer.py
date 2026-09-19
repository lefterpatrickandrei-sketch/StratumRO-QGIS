# -*- coding: utf-8 -*-
"""
StratumRO Orientation-Aware Regularizer
======================================
Dominant-orientation-aware regularization for Romanian cadastral footprints.

Workflow:
1. Estimate dominant facade orientation angle theta via minimum rotated rectangle.
2. Rotate polygon by -theta to align principal axis with local Cartesian grid.
3. Apply orthogonal edge snapping and simplification in local frame.
4. Rotate back by +theta.
5. Validate topological integrity and area preservation.
Preserves non-orthogonal features when buildings deviate significantly from 90° layouts.
"""

import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import rotate
from shapely.validation import make_valid
from stratum_ro.vectorizer import compute_orthogonality_ratio, CadastralVectorizer


class OrientationAwareRegularizer:
    """
    Cadastral regularizer that aligns with the building's physical dominant axis before orthogonalization.
    """

    def __init__(
        self,
        tolerance_m: float = 0.65,
        min_ortho_ratio: float = 0.45,
        max_area_change_pct: float = 20.0
    ):
        self.tolerance_m = tolerance_m
        self.min_ortho_ratio = min_ortho_ratio
        self.max_area_change_pct = max_area_change_pct
        self.cad_vectorizer = CadastralVectorizer(crs="EPSG:3844")

    @staticmethod
    def get_dominant_angle(poly: Polygon) -> float:
        """
        Calculates the dominant orientation angle (in degrees) of a polygon
        from its minimum rotated bounding box.
        """
        mrr = poly.minimum_rotated_rectangle
        coords = list(mrr.exterior.coords)[:-1]

        if len(coords) < 4:
            return 0.0

        # Find the longest edge
        max_len = 0.0
        best_angle = 0.0

        for i in range(len(coords)):
            p1 = coords[i]
            p2 = coords[(i + 1) % len(coords)]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = np.sqrt(dx * dx + dy * dy)

            if length > max_len:
                max_len = length
                angle_rad = np.arctan2(dy, dx)
                best_angle = np.degrees(angle_rad)

        # Normalize angle to [-45, 45]
        angle = best_angle % 90.0
        if angle > 45.0:
            angle -= 90.0
        elif angle < -45.0:
            angle += 90.0

        return float(angle)

    def regularize_polygon(self, raw_poly: Polygon) -> dict:
        """
        Regularizes a single polygon using dominant orientation alignment.

        Parameters
        ----------
        raw_poly : Polygon
            Input raw polygon.

        Returns
        -------
        dict
            Dict containing regularized geometry, dominant_angle, ortho_ratio_raw,
            ortho_ratio_reg, and area_change_pct.
        """
        if raw_poly is None or raw_poly.is_empty:
            return None

        raw_poly = make_valid(raw_poly)
        if isinstance(raw_poly, MultiPolygon):
            raw_poly = max(raw_poly.geoms, key=lambda p: p.area)

        orig_area = float(raw_poly.area)
        orig_ortho = compute_orthogonality_ratio(raw_poly)

        # 1. Compute dominant angle
        dom_angle = self.get_dominant_angle(raw_poly)
        centroid = raw_poly.centroid

        # 2. Rotate to local aligned coordinate system
        rotated_poly = rotate(raw_poly, -dom_angle, origin=centroid)

        # 3. Regularize in aligned frame
        aligned_reg = self.cad_vectorizer.clean_cad_polygon(rotated_poly, tolerance=self.tolerance_m)
        if aligned_reg is None or aligned_reg.is_empty or aligned_reg.area < 10.0:
            aligned_reg = rotated_poly

        # 4. Rotate back to Stereo 70
        final_poly = rotate(aligned_reg, dom_angle, origin=centroid)
        final_poly = make_valid(final_poly)
        if isinstance(final_poly, MultiPolygon):
            final_poly = max(final_poly.geoms, key=lambda p: p.area)

        # 5. Quality control: ensure area didn't distort excessively
        final_area = float(final_poly.area)
        area_diff_pct = abs(final_area - orig_area) / orig_area * 100.0
        final_ortho = compute_orthogonality_ratio(final_poly)

        # If regularizer caused massive area distortion (>20%), keep raw geometry
        if area_diff_pct > self.max_area_change_pct:
            final_poly = raw_poly
            final_ortho = orig_ortho
            final_area = orig_area

        v_raw = len(raw_poly.exterior.coords) - 1
        v_reg = len(final_poly.exterior.coords) - 1

        return {
            "geometry": final_poly,
            "dominant_angle_deg": round(dom_angle, 2),
            "ortho_ratio_raw": round(orig_ortho, 3),
            "ortho_ratio_reg": round(final_ortho, 3),
            "raw_area_m2": round(orig_area, 2),
            "reg_area_m2": round(final_area, 2),
            "area_change_pct": round(area_diff_pct, 2),
            "vertex_count_raw": v_raw,
            "vertex_count_reg": v_reg,
            "is_canonical_rect": (v_reg == 4 and final_ortho >= 0.85)
        }
