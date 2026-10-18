# -*- coding: utf-8 -*-
"""
Unit test for orthogonalize_cad: ensures L-shaped polygons with jagged
pixel steps are regularized to 90-degree orthogonal corners without
being forcefully collapsed into a bounding box (MRR).
"""
import unittest
from shapely.geometry import Polygon
from stratum_ro.core.geometry.regularizer import (
    orthogonalize_cad,
    compute_orthogonality_ratio,
    count_macro_reflex_corners,
)


class TestOrthogonalizeLShape(unittest.TestCase):
    def test_l_shaped_jagged_mask_preserves_wings(self):
        # Construct an L-shape with small 0.20m staircase steps along the edges
        # Base L: (0,0) -> (10,0) -> (10,4) -> (4,4) -> (4,10) -> (0,10)
        # Adding diagonal micro-steps
        pts = [
            (0.0, 0.0), (2.0, 0.05), (5.0, 0.0), (10.0, 0.0),
            (10.0, 2.0), (9.95, 4.0),
            (8.0, 4.05), (6.0, 3.95), (4.0, 4.0),
            (4.05, 7.0), (3.95, 10.0),
            (2.0, 10.05), (0.0, 10.0),
            (0.05, 5.0), (0.0, 0.0)
        ]
        raw_poly = Polygon(pts)
        self.assertTrue(raw_poly.is_valid)

        # Raw mask has reflex corner
        self.assertGreaterEqual(count_macro_reflex_corners(raw_poly, min_edge_len=0.60), 1)

        # Regularize
        reg_poly = orthogonalize_cad(raw_poly, tolerance=0.5)
        self.assertTrue(reg_poly.is_valid)

        # 1. Must NOT be a 4-vertex bounding box
        v_count = len(reg_poly.exterior.coords) - 1
        self.assertGreater(v_count, 4, f"L-shape was erroneously collapsed into {v_count} vertices!")

        # 2. Must preserve the reflex corner
        reflex = count_macro_reflex_corners(reg_poly, min_edge_len=0.50)
        self.assertGreaterEqual(reflex, 1, "Reflex corner was destroyed!")

        # 3. Orthogonality ratio must be high
        ortho = compute_orthogonality_ratio(reg_poly)
        self.assertGreaterEqual(ortho, 0.85, f"Orthogonality ratio {ortho:.2f} is below 0.85")

        # 4. Hausdorff shift must be low (< 0.85m)
        h_dist = raw_poly.hausdorff_distance(reg_poly)
        self.assertLessEqual(h_dist, 0.85, f"Hausdorff shift {h_dist:.2f}m is too large")


if __name__ == "__main__":
    unittest.main()
