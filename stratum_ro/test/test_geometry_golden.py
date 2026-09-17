# -*- coding: utf-8 -*-
"""
StratumRO — Golden Regression Test Suite (Phase 1B)
Deterministic geometric regression tests for building typologies,
failure modes, and semantic preservation.

NOTE: All thresholds in this file are ENGINEERING PROPOSALS — NOT NORMATIVE,
derived from geometric error bounds (GSD, sagitta, Hausdorff) unless an official
ANCPI norm article is explicitly cited.
"""

import unittest
import math
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from stratum_ro.vectorizer import (
    CadastralVectorizer,
    orthogonalize_cad,
    _extract_largest_polygon
)
from stratum_ro.geometric_reconstruction_v2 import AdaptiveContourReconstructor


def count_reflex_corners(poly: Polygon, tol_deg: float = 15.0) -> int:
    """
    Counts interior angles close to 270 degrees (reflex/reentrant corners)
    on a simple polygon with CCW exterior ring.
    Interior angle = pi - turning_angle.
    For a 270 deg interior corner, turning_angle ~ -90 deg.
    """
    if poly is None or poly.is_empty:
        return 0
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return 0
    reflex_count = 0
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        u = p_curr - p_prev
        v = p_next - p_curr
        cross = u[0] * v[1] - u[1] * v[0]
        dot = u[0] * v[0] + u[1] * v[1]
        turning = math.atan2(cross, dot)
        interior = math.pi - turning
        int_deg = math.degrees(interior) % 360.0
        if abs(int_deg - 270.0) <= tol_deg:
            reflex_count += 1
    return reflex_count


def has_diagonal_edges(poly: Polygon) -> bool:
    """
    Checks if an axis-aligned polygon has non-axis-aligned (diagonal) edges.
    """
    if poly is None or poly.is_empty:
        return False
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 3:
        return False
    for i in range(n):
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        dx = abs(p2[0] - p1[0])
        dy = abs(p2[1] - p1[1])
        if dx > 1e-3 and dy > 1e-3:
            return True
    return False


class TestGeometryGolden(unittest.TestCase):
    """
    Golden Regression Dataset (12 Core Typologies + 5 Specific Failure Tests)
    """

    def setUp(self):
        self.vec = CadastralVectorizer(crs="EPSG:3844")
        self.reconstructor = AdaptiveContourReconstructor(gsd_m=0.15)

    # =========================================================================
    # GOLDEN 01: Simple Rectangle (Axis-aligned)
    # =========================================================================
    def test_01_rectangle_axis_aligned(self):
        gt = Polygon([(0, 0), (10, 0), (10, 6), (0, 6)])
        out = self.vec.clean_cad_polygon(gt, tolerance=0.7)
        self.assertTrue(out.is_valid)
        self.assertEqual(len(out.exterior.coords) - 1, 4)
        self.assertAlmostEqual(out.area, 60.0, places=2)
        iou = gt.intersection(out).area / gt.union(out).area
        self.assertGreaterEqual(iou, 0.99)

    # =========================================================================
    # GOLDEN 02: Rotated Rectangle
    # =========================================================================
    def test_02_rectangle_rotated(self):
        from shapely.affinity import rotate
        gt_base = Polygon([(0, 0), (10, 0), (10, 6), (0, 6)])
        gt = rotate(gt_base, 30.0, origin=(5, 3))
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        self.assertAlmostEqual(out.area, 60.0, delta=1.0)
        iou = gt.intersection(out).area / gt.union(out).area
        self.assertGreaterEqual(iou, 0.95)

    # =========================================================================
    # GOLDEN 03: L-Shape
    # =========================================================================
    def test_03_l_shape(self):
        gt = Polygon([(0, 0), (10, 0), (10, 4), (4, 4), (4, 10), (0, 10)])
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        self.assertEqual(len(out.exterior.coords) - 1, 6)
        self.assertAlmostEqual(out.area, 64.0, places=1)
        self.assertEqual(count_reflex_corners(out), 1)
        self.assertFalse(has_diagonal_edges(out))

    # =========================================================================
    # GOLDEN 04: T-Shape
    # =========================================================================
    def test_04_t_shape(self):
        gt = Polygon([(0, 4), (4, 4), (4, 0), (8, 0), (8, 4), (12, 4), (12, 8), (0, 8)])
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        self.assertEqual(len(out.exterior.coords) - 1, 8)
        self.assertAlmostEqual(out.area, 64.0, places=1)
        self.assertEqual(count_reflex_corners(out), 2)
        self.assertFalse(has_diagonal_edges(out))

    # =========================================================================
    # GOLDEN 05: Cross Shape
    # =========================================================================
    def test_05_cross_shape(self):
        gt = Polygon([
            (4, 0), (8, 0), (8, 4), (12, 4), (12, 8), (8, 8),
            (8, 12), (4, 12), (4, 8), (0, 8), (0, 4), (4, 4)
        ])
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        self.assertEqual(count_reflex_corners(out), 4)
        self.assertAlmostEqual(out.area, 80.0, delta=1.5)

    # =========================================================================
    # GOLDEN 06: Narrow Wing (Structural Preservation)
    # =========================================================================
    def test_06_narrow_wing(self):
        # Building with a narrow wing (width = 1.0m, length = 6m)
        gt = Polygon([(0, 0), (10, 0), (10, 4), (1, 4), (1, 10), (0, 10)])
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        self.assertEqual(count_reflex_corners(out), 1)
        self.assertAlmostEqual(out.area, 46.0, delta=1.0)

    # =========================================================================
    # GOLDEN 07: Small Architectural Protrusion (e.g. 0.5m doorway)
    # =========================================================================
    def test_07_small_architectural_protrusion(self):
        # 10x6 rectangle with a 0.50m x 0.50m protrusion
        gt = Polygon([(0, 0), (10, 0), (10, 6), (6, 6), (6, 6.5), (5.5, 6.5), (5.5, 6), (0, 6)])
        out = self.vec.clean_cad_polygon(gt, tolerance=0.7)
        self.assertTrue(out.is_valid)
        # In baseline, this FAILS because clean_cad_polygon removes edges < 0.6m!
        self.assertEqual(len(out.exterior.coords) - 1, 8, "Protrusion of 0.5m must be preserved!")
        self.assertGreater(out.area, 60.0)

    # =========================================================================
    # GOLDEN 08: Curved Facade
    # =========================================================================
    def test_08_curved_facade(self):
        angles = np.linspace(0, np.pi / 2, 16)
        arc_pts = [(10.0 + 4.0 * np.cos(a), 4.0 * np.sin(a)) for a in angles]
        gt_pts = [(0, 0)] + arc_pts + [(0, 4)]
        gt = Polygon(gt_pts)
        res = self.reconstructor.classify_and_reconstruct(gt)
        out = res["geometry"]
        self.assertTrue(out.is_valid)
        # Must not be collapsed to a naive 3-4 vertex triangle/box
        self.assertGreaterEqual(len(out.exterior.coords) - 1, 6)

    # =========================================================================
    # GOLDEN 09: Church + Semicircular Apse
    # =========================================================================
    def test_09_church_semicircular_apse(self):
        angles = np.linspace(-np.pi / 2, np.pi / 2, 20)
        apse_pts = [(12.0 + 3.0 * np.cos(a), 3.0 + 3.0 * np.sin(a)) for a in angles]
        church_pts = [(0, 0), (12, 0)] + apse_pts + [(12, 6), (0, 6)]
        gt = Polygon(church_pts)
        out = self.vec.clean_cad_polygon(gt, tolerance=0.7)
        self.assertTrue(out.is_valid)
        # In baseline, this FAILS because clean_cad_polygon collapses the apse to 4 vertices!
        self.assertGreater(len(out.exterior.coords) - 1, 4, "Church apse must NOT be collapsed to a 4-vertex rectangle!")
        h_dist = gt.hausdorff_distance(out)
        self.assertLessEqual(h_dist, 0.35, f"Hausdorff distance too large: {h_dist:.3f}m")

    # =========================================================================
    # GOLDEN 10: Rasterized Building (Pixel Staircase Reduction)
    # =========================================================================
    def test_10_rasterized_building(self):
        from rasterio.transform import from_origin
        from rasterio.features import rasterize, shapes
        from shapely.affinity import rotate
        gsd = 0.15
        tr = from_origin(0.0, 20.0, gsd, gsd)
        rect_rot = rotate(Polygon([(5, 5), (15, 5), (15, 11), (5, 11)]), 30.0, origin=(10, 8))
        mask = rasterize([(rect_rot, 1)], out_shape=(150, 150), transform=tr, fill=0, dtype=np.uint8)
        raw_polys = [Polygon(shape(geom).exterior.coords) for geom, val in shapes(mask, mask=(mask == 1), transform=tr) if val == 1]
        raw_poly = max(raw_polys, key=lambda p: p.area)
        self.assertGreater(len(raw_poly.exterior.coords) - 1, 100, "Raw raster should have pixel staircase (>100 verts)")
        out = self.vec.clean_cad_polygon(raw_poly, tolerance=0.7)
        self.assertTrue(out.is_valid)
        self.assertLessEqual(len(out.exterior.coords) - 1, 8, "Staircase must be regularized to CAD vertices (<=8)")

    # =========================================================================
    # GOLDEN 11: Connected Multi-Body (Wing Preservation through Pipeline)
    # =========================================================================
    def test_11_connected_multi_body(self):
        # Main body 20x10 + corridor 0.7m + secondary annex 8x8
        compound = Polygon([
            (0, 0), (20, 0), (20, 10), (10.7, 10),
            (10.7, 15), (18, 15), (18, 23), (10, 23), (10, 15), (10.0, 10), (0, 10)
        ])
        # Run through format_hybrid_buildings with eave retraction 0.40m
        raw_cand = [{"geometry": compound, "sam2_score": 0.9, "mean_h": 4.5, "max_h": 6.0}]
        formatted = self.vec.format_hybrid_buildings(raw_cand, eave_offset_m=0.40)
        self.assertTrue(len(formatted) >= 1)
        total_sol_area = sum(f.get("area_sol_m2", f["geometry"].area) for f in formatted)
        # In baseline, the secondary wing (51.84 m2) is LOST due to _extract_largest_polygon(p_sol_cand)!
        # Initial area after buffer was ~228 m2; baseline keeps only ~176.64 m2!
        self.assertGreater(total_sol_area, 200.0, f"Secondary wing was amputated! Retained only {total_sol_area:.2f} m2")

    # =========================================================================
    # GOLDEN 12: Adjacent Buildings (Calcan Boundary Preservation)
    # =========================================================================
    def test_12_adjacent_buildings_calcan(self):
        b1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        b2 = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
        # Both are strictly valid and touch along x=10
        raw_cands = [
            {"geometry": b1, "sam2_score": 0.9, "mean_h": 5.0, "max_h": 6.0},
            {"geometry": b2, "sam2_score": 0.9, "mean_h": 5.0, "max_h": 6.0}
        ]
        res = self.vec.format_hybrid_buildings(raw_cands, eave_offset_m=0.0)
        self.assertEqual(len(res), 2)
        # Verify 0 overlap between adjacent buildings
        inter = res[0]["geometry"].intersection(res[1]["geometry"])
        self.assertAlmostEqual(inter.area, 0.0, places=3)

    # =========================================================================
    # EXPLICIT DEFECT REPRODUCTION TESTS (A through E)
    # =========================================================================

    def test_defect_A_d_less_06_removes_protrusion(self):
        """
        Reproduces Defect A: `clean_cad_polygon` deletes real architectural
        protrusions whose edges are < 0.6m.
        """
        notch_poly = Polygon([(0, 0), (10, 0), (10, 6), (6, 6), (6, 6.5), (5.5, 6.5), (5.5, 6), (0, 6)])
        cleaned = self.vec.clean_cad_polygon(notch_poly, tolerance=0.7)
        # Expected baseline failure: currently it removes the notch and outputs 4 vertices
        self.assertEqual(
            len(cleaned.exterior.coords) - 1, 8,
            "EXPECTED BASELINE FAILURE: `d < 0.6` rule deletes the 0.5m protrusion!"
        )

    def test_defect_B_buildingregulariser_t_shape_diagonal(self):
        """
        Reproduces Defect B: `clean_cad_polygon` via `buildingregulariser`
        introduces diagonal cuts on concave T-shape.
        """
        t_poly = Polygon([(0, 4), (4, 4), (4, 0), (8, 0), (8, 4), (12, 4), (12, 8), (0, 8)])
        cleaned = self.vec.clean_cad_polygon(t_poly, tolerance=0.7)
        has_diag = has_diagonal_edges(cleaned)
        self.assertFalse(
            has_diag,
            "EXPECTED BASELINE FAILURE: `buildingregulariser` introduced diagonal edges on T-shape!"
        )
        self.assertAlmostEqual(cleaned.area, 64.0, delta=1.0, msg="Area was distorted by regulariser!")

    def test_defect_C_negative_eave_buffer_collapse(self):
        """
        Reproduces Defect C: `buffer(-0.4)` collapses narrow corridors/wings <= 0.8m.
        """
        bar_06 = Polygon([(0, 0), (10, 0), (10, 0.6), (0, 0.6)])
        b_res = bar_06.buffer(-0.4, join_style=2)
        # Demonstrates that 0.6m bar completely collapses to empty
        self.assertTrue(b_res.is_empty, "0.6m bar collapses to empty under 0.4m buffer")
        self.assertEqual(b_res.area, 0.0)

    def test_defect_D_wing_loss_extract_largest_polygon(self):
        """
        Reproduces Defect D: `_extract_largest_polygon` discards secondary wings.
        """
        compound = Polygon([
            (0, 0), (20, 0), (20, 10), (10.7, 10),
            (10.7, 15), (18, 15), (18, 23), (10, 23), (10, 15), (10.0, 10), (0, 10)
        ])
        buf_cand = compound.buffer(-0.4, join_style=2)
        self.assertTrue(isinstance(buf_cand, MultiPolygon), "Buffer splits compound building into MultiPolygon")
        self.assertEqual(len(buf_cand.geoms), 2)
        largest = _extract_largest_polygon(buf_cand)
        lost_area = buf_cand.area - largest.area
        self.assertGreater(lost_area, 40.0, "Demonstrates >40 m2 wing lost by largest-polygon selection")

    def test_defect_E_curved_apse_destroyed_to_box(self):
        """
        Reproduces Defect E: `clean_cad_polygon` squares a curved church apse to a 4-vertex rectangle.
        """
        angles = np.linspace(-np.pi / 2, np.pi / 2, 20)
        apse_pts = [(12.0 + 3.0 * np.cos(a), 3.0 + 3.0 * np.sin(a)) for a in angles]
        church_pts = [(0, 0), (12, 0)] + apse_pts + [(12, 6), (0, 6)]
        church = Polygon(church_pts)
        cleaned = self.vec.clean_cad_polygon(church, tolerance=0.7)
        # Expected baseline failure: clean_cad_polygon turns it into a 4-vertex rectangle
        self.assertGreater(
            len(cleaned.exterior.coords) - 1, 4,
            "EXPECTED BASELINE FAILURE: Church apse is squared into a 4-vertex box!"
        )


if __name__ == "__main__":
    unittest.main()
