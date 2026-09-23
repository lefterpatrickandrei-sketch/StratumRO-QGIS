# -*- coding: utf-8 -*-
"""
Integration test suite for the extracted stratum_ro/core package.
Verifies all 5 subsystems and proves pure-Python isolation (zero QGIS dependencies).
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
import numpy as np
from shapely.geometry import Polygon

import stratum_ro.core as core


class TestCoreIntegration(unittest.TestCase):

    def test_01_zero_qgis_import_isolation(self):
        """Proves that stratum_ro.core never imports QGIS or PyQt GUI modules."""
        imported_modules = list(sys.modules.keys())
        qgis_imports = [m for m in imported_modules if m.startswith("qgis") or m.startswith("PyQt5.QtWebKit")]
        self.assertEqual(len(qgis_imports), 0, f"QGIS leaked into pure Core: {qgis_imports}")

    def test_02_geometry_subsystem(self):
        engine = core.CoreGeometryEngine()
        poly = Polygon([(0, 0), (10, 0), (10, 5), (0, 5)])
        out = engine.regularize_90(poly)
        self.assertTrue(out.is_valid)
        self.assertAlmostEqual(out.area, 50.0, places=2)

    def test_03_geodesy_subsystem(self):
        crs_mgr = core.CoreCRSManager()
        meta = crs_mgr.get_metadata("EPSG:3844")
        self.assertEqual(meta.ellipsoid, "Krasovsky 1940")

        tr = core.CoreTransformer("EPSG:4326", "EPSG:3844")
        tx, ty, tz = tr.transform_point(23.585, 46.766)
        self.assertGreater(tx, 380000.0)
        self.assertGreater(ty, 570000.0)

    def test_04_qa_qc_subsystem(self):
        val = core.CoreGeometryValidator()
        poly = Polygon([(0, 0), (10, 0), (10, 5), (0, 5)])
        rep = val.validate(poly)
        self.assertTrue(rep.is_valid)

    def test_05_raster_subsystem_difference(self):
        reader = core.CoreRasterReader()
        arr_a = np.array([[10.0, 15.0], [20.0, 25.0]], dtype=np.float32)
        arr_b = np.array([[2.0, 5.0], [10.0, 15.0]], dtype=np.float32)
        diff = reader.compute_difference(arr_a, arr_b)
        expected = np.array([[8.0, 10.0], [10.0, 10.0]], dtype=np.float32)
        np.testing.assert_array_almost_equal(diff, expected)

    def test_06_pointcloud_subsystem_filtering(self):
        reader = core.CorePointCloudReader()
        pts = {
            "x": np.array([1.0, 2.0, 3.0, 4.0]),
            "y": np.array([1.0, 2.0, 3.0, 4.0]),
            "z": np.array([10.0, 12.0, 15.0, 20.0]),
            "classification": np.array([2, 2, 6, 1])  # 2=Ground, 6=Building
        }
        filtered = reader.filter_by_classification(pts, target_classes=[6])
        self.assertEqual(len(filtered["x"]), 1)
        self.assertEqual(filtered["classification"][0], 6)


if __name__ == "__main__":
    unittest.main()
