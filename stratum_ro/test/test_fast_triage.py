# -*- coding: utf-8 -*-
"""
test_fast_triage.py - Unit tests for System 1 Fast Triage Engine (<35ms on CPU)
"""

import time
import unittest
from shapely.geometry import box, Polygon

from stratum_ro.ai.fast_triage import FastTriageEngine


class TestFastTriageEngine(unittest.TestCase):

    def setUp(self):
        self.engine = FastTriageEngine()

    def test_sliver_under_8m2_is_rejected(self):
        # 2m x 3m = 6m2 (< 8m2 annex threshold)
        geom = box(400000, 585000, 400002, 585003)
        verdict = self.engine.evaluate_candidate(geom)
        self.assertEqual(verdict.status, "REJECTED")
        self.assertFalse(verdict.escalate_to_vlm)
        self.assertIn("below legal ANCPI annex minimum", verdict.reason)

    def test_extreme_aspect_ratio_is_rejected(self):
        # 1m x 20m = 20m2, aspect ratio = 20.0 (> 7.0)
        geom = box(400000, 585000, 400001, 585020)
        verdict = self.engine.evaluate_candidate(geom)
        self.assertEqual(verdict.status, "REJECTED")
        self.assertIn("aspect ratio", verdict.reason)

    def test_ground_pavement_low_height_is_rejected(self):
        geom = box(400000, 585000, 400010, 585010)
        attrs = {"h_mean": 0.4, "h_max": 0.8}
        verdict = self.engine.evaluate_candidate(geom, attributes=attrs)
        self.assertEqual(verdict.status, "REJECTED")
        self.assertIn("ground-level", verdict.reason)

    def test_clear_detached_building_is_approved(self):
        # 10m x 12m = 120m2, h_mean=4.5m, solid rectangle
        geom = box(400000, 585000, 400010, 585012)
        attrs = {"h_mean": 4.5, "h_max": 6.2, "has_calcan": False}
        verdict = self.engine.evaluate_candidate(geom, attributes=attrs)
        self.assertEqual(verdict.status, "APPROVED")
        self.assertFalse(verdict.escalate_to_vlm)
        self.assertGreaterEqual(verdict.confidence, 0.90)

    def test_party_wall_calcan_escalates_to_vlm(self):
        geom = box(400000, 585000, 400010, 585010)
        attrs = {"h_mean": 4.0, "h_max": 5.5, "has_calcan": True}
        verdict = self.engine.evaluate_candidate(geom, attributes=attrs)
        self.assertEqual(verdict.status, "UNCERTAIN")
        self.assertTrue(verdict.escalate_to_vlm)
        self.assertIn("calcan", verdict.reason)

    def test_triage_latency_under_35ms(self):
        # Benchmark 100 candidate evaluations on CPU
        geoms = [box(400000, 585000, 400000 + i, 585010) for i in range(5, 105)]
        attrs = {"h_mean": 3.5, "h_max": 5.0}

        t0 = time.perf_counter()
        for g in geoms:
            v = self.engine.evaluate_candidate(g, attributes=attrs)
            # Each individual evaluation must be well below 35ms
            self.assertLess(v.latency_ms, 35.0)

        total_elapsed_ms = (time.perf_counter() - t0) * 1000.0
        avg_latency = total_elapsed_ms / len(geoms)
        print(f"\n[BENCHMARK] Fast Triage average latency: {avg_latency:.3f} ms / candidate (Target: < 35.0 ms)")
        self.assertLess(avg_latency, 5.0)  # Pure CPU operations should be < 5ms


if __name__ == "__main__":
    unittest.main()
