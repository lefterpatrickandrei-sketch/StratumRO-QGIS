# -*- coding: utf-8 -*-
"""Deterministic regression tests for the current validate_ancpi behavior.

These tests record implementation behavior, not legal compliance. In particular,
the API receives bare geometries (no CRS metadata), and its edge docstring and
implementation intentionally differ; see docs/ANCPI_ORDIN_600_TRACEABILITY.md.
"""

import sys
import unittest
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, box, mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stratum_ro.ai.tools.cadastral_tools import validate_ancpi


class TestAncpiValidationCurrentBehavior(unittest.TestCase):
    @staticmethod
    def rect(area, x=400000.0, y=585000.0):
        return box(x, y, x + area, y + 1.0)

    def validate(self, geom):
        return validate_ancpi([geom])

    def test_area_threshold_boundaries(self):
        cases = ((7.9, "min_area_annex_8m2", "failed"),
                 (8.0, "min_area_annex_8m2", "passed"),
                 (44.9, "min_area_annex_8m2", "passed"),
                 (45.0, "min_area_main_45m2", "passed"))
        for area, key, outcome in cases:
            with self.subTest(area=area):
                result = self.validate(self.rect(area))
                self.assertEqual(result["checks"][key][outcome], 1)

    def test_edge_boundaries_and_docstring_discrepancy(self):
        # Source docstring claims >=1.0 m; code actually rejects only <0.5 m.
        for edge, should_pass in ((0.49, False), (0.50, True), (0.75, True), (1.0, True)):
            with self.subTest(edge=edge):
                result = self.validate(box(400000, 585000, 400000 + edge, 585010))
                check = result["checks"]["min_edge_1m"]
                self.assertEqual(check["passed"], int(should_pass))
                self.assertEqual(check["failed"], int(not should_pass))

    def test_centroid_inside_bounds_even_when_vertices_are_outside(self):
        for geom in (box(149999, 585000, 150001, 585010),
                     box(400000, 199999, 400010, 200001)):
            with self.subTest(bounds=geom.bounds):
                result = self.validate(geom)
                self.assertEqual(result["checks"]["stereo70_bounds"]["passed"], 1)
                self.assertTrue(result["passed"])

    def test_raw_geometry_api_has_no_crs_argument_or_crs_check(self):
        geom = mapping(box(400000, 585000, 400010, 585010))
        # Raw GeoJSON-like geometry is treated as coordinates; CRS cannot be
        # supplied, and the result reports EPSG:3844 without verifying it.
        result = validate_ancpi([geom])
        self.assertEqual(result["evidence"]["crs"], "EPSG:3844")
        self.assertEqual(result["checks"]["stereo70_bounds"]["passed"], 1)

    def test_empty_geometry_is_failed_without_check_counts(self):
        result = self.validate(Polygon())
        self.assertEqual(result["failed_count"], 1)
        self.assertIn("empty geometry", result["warnings"][0])
        for values in result["checks"].values():
            self.assertEqual(values, {"passed": 0, "failed": 0})

    def test_multipolygon_only_uses_area_and_centroid_checks(self):
        geom = MultiPolygon([box(400000, 585000, 400005, 585005),
                             box(400010, 585000, 400015, 585005)])
        result = self.validate(geom)
        self.assertEqual(result["checks"]["min_area_main_45m2"]["passed"], 1)
        # MultiPolygon has no exterior, so edge check is counted as passed.
        self.assertEqual(result["checks"]["min_edge_1m"]["passed"], 1)

    def test_self_intersection_is_not_checked_by_validate_ancpi(self):
        # Unequal lobes retain >=45 m2 Shapely area despite self-crossing.
        bowtie = Polygon([(400000, 585000), (400020, 585020),
                          (400000, 585020), (400010, 585000),
                          (400000, 585000)])
        self.assertFalse(bowtie.is_valid)
        result = self.validate(bowtie)
        self.assertEqual(result["checks"]["min_area_main_45m2"]["passed"], 1)
        self.assertEqual(result["failed_count"], 0)
        self.assertTrue(result["passed"])


if __name__ == "__main__":
    unittest.main()