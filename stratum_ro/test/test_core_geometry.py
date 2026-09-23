# -*- coding: utf-8 -*-
"""
Unit tests for stratum_ro/core/geometry package.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
from shapely.geometry import Polygon

from stratum_ro.contracts.geometry import IGeometryEngine
from stratum_ro.core.geometry import (
    CoreGeometryEngine,
    orthogonalize_cad,
    compute_iou,
    compute_hausdorff,
    compute_boundary_rmse,
    compute_centroid_shift
)


class TestCoreGeometry(unittest.TestCase):

    def setUp(self):
        self.engine = CoreGeometryEngine()

    def test_protocol_conformance(self):
        self.assertIsInstance(self.engine, IGeometryEngine)

    def test_regularize_rectangle(self):
        poly = Polygon([(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)])
        out = self.engine.regularize_90(poly, tolerance=0.5)
        self.assertTrue(out.is_valid)
        self.assertAlmostEqual(out.area, 60.0, places=2)

    def test_metrics_calculation(self):
        p1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        p2 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        p3 = Polygon([(5, 0), (15, 0), (15, 10), (5, 10)])

        iou_perf = compute_iou(p1, p2)
        self.assertAlmostEqual(iou_perf, 1.0, places=4)

        iou_half = compute_iou(p1, p3)
        self.assertAlmostEqual(iou_half, 50.0 / 150.0, places=4)

        h_dist = compute_hausdorff(p1, p3)
        self.assertAlmostEqual(h_dist, 5.0, places=2)

        centroid_shift = compute_centroid_shift(p1, p3)
        self.assertAlmostEqual(centroid_shift, 5.0, places=2)

    def test_planar_partition(self):
        # Overlapping squares
        p1 = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        p2 = Polygon([(5, 0), (15, 0), (15, 10), (5, 10)])
        parts = self.engine.build_planar_partition([p1, p2])
        self.assertGreaterEqual(len(parts), 2)
        # Partitions should be disjoint
        for i in range(len(parts)):
            for j in range(i + 1, len(parts)):
                inter = parts[i].intersection(parts[j]).area
                self.assertAlmostEqual(inter, 0.0, places=3)


if __name__ == "__main__":
    unittest.main()
