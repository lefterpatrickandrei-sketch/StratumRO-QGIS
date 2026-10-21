# -*- coding: utf-8 -*-
"""
test_pug_order_904_2023.py - Tests for PUG Order 904/2023 & CATUC 2026 Compliance

Validates:
1. Article 8: Simple geometry rules.
2. Article 9(1): Functional zoning topology (no overlaps, no gaps against boundary).
3. Legal citations in PugProductGenerator (Law 169/2026 - CATUC, Order 904/2023).
"""

import unittest
import geopandas as gpd
from shapely.geometry import box, Polygon

from stratum_ro.pug_topology import Order904TopologyAuditor
from stratum_ro.pug_product import PugProductGenerator


class TestPugOrder904Topology(unittest.TestCase):

    def setUp(self):
        self.auditor = Order904TopologyAuditor(tolerance_m2=0.01)

    def test_functional_zoning_adjacent_polygons_pass_without_overlap(self):
        # Two adjacent zoning tiles sharing a border at x=100
        z1 = box(0, 0, 100, 100)
        z2 = box(100, 0, 200, 100)
        gdf = gpd.GeoDataFrame({"geometry": [z1, z2]}, crs="EPSG:3844")

        res = self.auditor.check_functional_zoning_no_overlaps(gdf)
        self.assertTrue(res.passed)
        self.assertEqual(res.defect_count, 0)
        self.assertEqual(res.defect_area_m2, 0.0)

    def test_functional_zoning_overlapping_polygons_fail(self):
        # Two overlapping zoning tiles (overlap of 10m x 100m = 1000m2)
        z1 = box(0, 0, 110, 100)
        z2 = box(100, 0, 200, 100)
        gdf = gpd.GeoDataFrame({"geometry": [z1, z2]}, crs="EPSG:3844")

        res = self.auditor.check_functional_zoning_no_overlaps(gdf)
        self.assertFalse(res.passed)
        self.assertEqual(res.defect_count, 1)
        self.assertAlmostEqual(res.defect_area_m2, 1000.0, places=1)

    def test_boundary_coverage_complete_passes(self):
        # Boundary 0..200, 0..100 covered by two 100x100 tiles
        boundary = box(0, 0, 200, 100)
        z1 = box(0, 0, 100, 100)
        z2 = box(100, 0, 200, 100)
        gdf = gpd.GeoDataFrame({"geometry": [z1, z2]}, crs="EPSG:3844")

        res = self.auditor.check_boundary_coverage(gdf, boundary)
        self.assertTrue(res.passed)
        self.assertEqual(res.defect_count, 0)

    def test_boundary_coverage_with_gap_fails(self):
        # Boundary 0..200, 0..100, but tiles only cover 0..90 and 110..200 (20m gap in middle)
        boundary = box(0, 0, 200, 100)
        z1 = box(0, 0, 90, 100)
        z2 = box(110, 0, 200, 100)
        gdf = gpd.GeoDataFrame({"geometry": [z1, z2]}, crs="EPSG:3844")

        res = self.auditor.check_boundary_coverage(gdf, boundary)
        self.assertFalse(res.passed)
        self.assertGreater(res.defect_count, 0)
        self.assertAlmostEqual(res.defect_area_m2, 2000.0, places=1)

    def test_pug_product_generator_citations_conform_to_2026_code(self):
        # Ensure PugProductGenerator legal references include CATUC Law 169/2026
        gen = PugProductGenerator(crs="EPSG:3844")
        self.assertEqual(gen.crs, "EPSG:3844")
        # Check module docstring
        import stratum_ro.pug_product as pp
        self.assertIn("169/2026", pp.__doc__)
        self.assertIn("904/2023", pp.__doc__)


if __name__ == "__main__":
    unittest.main()
