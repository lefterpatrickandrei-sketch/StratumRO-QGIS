# -*- coding: utf-8 -*-
"""
Unit tests for stratum_ro/core/qa_qc package.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
from shapely.geometry import Polygon

from stratum_ro.contracts.validation import IValidator, ValidationSeverity
from stratum_ro.core.qa_qc import CoreGeometryValidator


class TestCoreQAQC(unittest.TestCase):

    def setUp(self):
        self.val = CoreGeometryValidator()

    def test_validator_protocol(self):
        self.assertIsInstance(self.val, IValidator)
        self.assertEqual(self.val.validator_id, "core_geometry_validator_v1")

    def test_valid_polygon_passes_clean(self):
        poly = Polygon([(0, 0), (10, 0), (10, 8), (0, 8)])
        report = self.val.validate(poly)
        self.assertTrue(report.is_valid)
        self.assertFalse(report.has_critical_errors)
        self.assertEqual(len(report.issues), 0)
        self.assertEqual(report.metrics["area_m2"], 80.0)

    def test_self_intersecting_polygon_fails(self):
        # Bowtie / self-intersecting polygon
        bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])
        report = self.val.validate(bowtie)
        self.assertFalse(report.is_valid)
        self.assertTrue(report.has_critical_errors)
        codes = [i.code for i in report.issues]
        self.assertIn("GEOS_INVALID", codes)

    def test_area_threshold_warning(self):
        # Tiny polygon (2 m2)
        tiny = Polygon([(0, 0), (2, 0), (2, 1), (0, 1)])
        report = self.val.validate(tiny, min_area_m2=5.0)
        self.assertTrue(report.is_valid)  # Warnings do not invalidate
        codes = [i.code for i in report.issues]
        self.assertIn("GEOM_AREA_TOO_SMALL", codes)


if __name__ == "__main__":
    unittest.main()
