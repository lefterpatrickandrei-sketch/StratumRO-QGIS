# -*- coding: utf-8 -*-
"""
test_edge_and_multipolygon_geometry.py - Tests for MultiPolygon edge verification
and minimum edge tolerance handling in ANCPI cadastral tools.
"""

import unittest
from shapely.geometry import Polygon, MultiPolygon, box

from stratum_ro.ai.tools.cadastral_tools import validate_ancpi


class TestEdgeAndMultiPolygonGeometry(unittest.TestCase):

    def test_multipolygon_with_valid_edges_passes(self):
        # Two boxes with 5m x 5m edges (both well above 0.5m)
        p1 = box(400000, 585000, 400005, 585005)
        p2 = box(400010, 585000, 400015, 585005)
        mp = MultiPolygon([p1, p2])

        res = validate_ancpi([mp])
        self.assertEqual(res["checks"]["min_edge_1m"]["passed"], 1)
        self.assertEqual(res["checks"]["min_edge_1m"]["failed"], 0)
        self.assertTrue(res["passed"])

    def test_multipolygon_with_micro_edge_in_annex_fails(self):
        # Main building (10m x 10m) + micro annex with 0.3m edge
        main_bld = box(400000, 585000, 400010, 585010)
        # Annex with a 0.3m micro-facet
        annex_coords = [
            (400015.0, 585000.0),
            (400015.3, 585000.0),  # 0.3m micro-edge!
            (400015.3, 585005.0),
            (400015.0, 585005.0),
            (400015.0, 585000.0),
        ]
        annex = Polygon(annex_coords)
        mp = MultiPolygon([main_bld, annex])

        res = validate_ancpi([mp])
        self.assertEqual(res["checks"]["min_edge_1m"]["failed"], 1)
        self.assertEqual(res["checks"]["min_edge_1m"]["passed"], 0)
        self.assertTrue(any("micro-edges" in w for w in res["warnings"]))

    def test_exact_edge_threshold_0_5m(self):
        # Edge of exactly 0.49m fails
        poly_049 = Polygon([
            (400000.0, 585000.0),
            (400000.49, 585000.0),
            (400000.49, 585010.0),
            (400000.0, 585010.0),
            (400000.0, 585000.0),
        ])
        res_049 = validate_ancpi([poly_049])
        self.assertEqual(res_049["checks"]["min_edge_1m"]["failed"], 1)

        # Edge of exactly 0.50m passes
        poly_050 = Polygon([
            (400000.0, 585000.0),
            (400000.50, 585000.0),
            (400000.50, 585010.0),
            (400000.0, 585010.0),
            (400000.0, 585000.0),
        ])
        res_050 = validate_ancpi([poly_050])
        self.assertEqual(res_050["checks"]["min_edge_1m"]["passed"], 1)


if __name__ == "__main__":
    unittest.main()
