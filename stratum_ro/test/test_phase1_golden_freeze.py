# -*- coding: utf-8 -*-
"""
StratumRO — Phase 1 Golden Baseline & Scientific Freeze Test Suite
Authoritative regression verification for frozen Ground Truth,
production module immutability, vectorizer determinism, and benchmark constants.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import json
import hashlib
import unittest
from shapely.geometry import shape, Polygon
from stratum_ro.vectorizer import CadastralVectorizer

BASELINE_DIR = os.path.join(PROJECT_ROOT, "workspace", "baseline")


class TestPhase1GoldenFreeze(unittest.TestCase):
    """
    Test suite verifying that no scientific drift or unauthorized code mutation
    occurs relative to the Phase 1 Golden Baseline.
    """

    @classmethod
    def setUpClass(cls):
        cls.gt_manifest_path = os.path.join(BASELINE_DIR, "manifest_ground_truth.json")
        cls.mod_manifest_path = os.path.join(BASELINE_DIR, "manifest_critical_modules.json")
        cls.geom_baseline_path = os.path.join(BASELINE_DIR, "golden_geometry_baseline.json")
        cls.metrics_baseline_path = os.path.join(BASELINE_DIR, "golden_metrics_baseline.json")
        
        with open(cls.gt_manifest_path, "r", encoding="utf-8") as f:
            cls.gt_manifest = json.load(f)
        with open(cls.mod_manifest_path, "r", encoding="utf-8") as f:
            cls.mod_manifest = json.load(f)
        with open(cls.geom_baseline_path, "r", encoding="utf-8") as f:
            cls.geom_baseline = json.load(f)
        with open(cls.metrics_baseline_path, "r", encoding="utf-8") as f:
            cls.metrics_baseline = json.load(f)
            
        cls.vec = CadastralVectorizer(crs="EPSG:3844")

    def _hash_file(self, rel_path: str) -> str:
        full_path = os.path.join(PROJECT_ROOT, rel_path.replace("/", os.sep))
        self.assertTrue(os.path.exists(full_path), f"File missing: {rel_path}")
        with open(full_path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_01_ground_truth_hashes_immutable(self):
        """Verifies that all 14 Ground Truth & reference datasets match their frozen SHA-256 hashes."""
        for rel_path, expected in self.gt_manifest.items():
            actual_hash = self._hash_file(rel_path)
            self.assertEqual(
                actual_hash,
                expected["sha256"],
                f"Ground Truth file corrupted or altered: {rel_path}"
            )

    def test_02_critical_production_modules_immutable(self):
        """Verifies that all 23 critical production modules (or their canonical domain targets) match frozen SHA-256 hashes."""
        canonical_domain_map = {
            "stratum_ro/volumetric_3d.py": "stratum_ro/domain/city_3d/builder.py",
        }
        for rel_path, expected in self.mod_manifest.items():
            target_path = canonical_domain_map.get(rel_path, rel_path)
            actual_hash = self._hash_file(target_path)
            self.assertEqual(
                actual_hash,
                expected["sha256"],
                f"Production code unexpectedly mutated: {target_path}"
            )
            # If migrated, also verify the forwarder at root exists
            if rel_path in canonical_domain_map:
                self.assertTrue(os.path.exists(os.path.join(PROJECT_ROOT, rel_path.replace("/", os.sep))))

    def test_03_vectorizer_determinism_and_golden_cases(self):
        """Verifies bit-for-bit determinism and geometric consistency on canonical regularizer cases."""
        canon_cases = {
            "CANON_RECT_AXIS": Polygon([(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]),
            "CANON_RECT_ROTATED": Polygon([(0.0, 0.0), (8.66, 5.0), (5.66, 10.196), (-3.0, 5.196)]),
            "CANON_L_SHAPE": Polygon([(0, 0), (10, 0), (10, 4), (4, 4), (4, 8), (0, 8)])
        }
        
        expected_cases = {c["case_name"]: c for c in self.geom_baseline["canonical_regularizer_cases"]}
        
        for name, poly in canon_cases.items():
            # Run twice to test determinism
            out1 = self.vec.clean_cad_polygon(poly, tolerance=0.7)
            out2 = self.vec.clean_cad_polygon(poly, tolerance=0.7)
            
            # Determinism check
            self.assertTrue(out1.equals_exact(out2, 1e-9), f"Non-deterministic regularizer on {name}")
            self.assertEqual(out1.area, out2.area, f"Area non-deterministic on {name}")
            
            # Match with golden baseline
            exp = expected_cases[name]
            self.assertEqual(len(out1.exterior.coords), exp["vertex_count"])
            self.assertAlmostEqual(out1.area, exp["area_m2"], places=4)
            self.assertTrue(out1.is_valid)

    def test_04_usamv_true_positive_geometry_freeze(self):
        """Verifies that the 4 USAMV TP building geometries match the frozen baseline areas and properties."""
        exp9_path = os.path.join(PROJECT_ROOT, "workspace", "phase3", "predictions", "EXP_009_integrated_pipeline_reg.geojson")
        self.assertTrue(os.path.exists(exp9_path), "EXP_009 prediction file missing")
        
        with open(exp9_path, "r", encoding="utf-8") as f:
            pred_data = json.load(f)
            
        tp_baseline_lookup = {b["prediction_feature_index"]: b for b in self.geom_baseline["usamv_true_positive_buildings"]}
        self.assertEqual(len(tp_baseline_lookup), 4, "Expected exactly 4 TP buildings in baseline")
        
        for p_idx, exp_b in tp_baseline_lookup.items():
            feat = pred_data["features"][p_idx]
            poly = shape(feat["geometry"])
            
            self.assertTrue(poly.is_valid)
            self.assertEqual(len(poly.exterior.coords), exp_b["vertex_count"])
            self.assertAlmostEqual(poly.area, exp_b["area_m2_raw"], places=4)
            self.assertAlmostEqual(poly.length, exp_b["perimeter_m_raw"], places=4)
            self.assertAlmostEqual(poly.centroid.x, exp_b["centroid"][0], places=4)
            self.assertAlmostEqual(poly.centroid.y, exp_b["centroid"][1], places=4)

    def test_05_phase3_recall_and_metrics_freeze(self):
        """Verifies that the authoritative Cluj–USAMV E9 benchmark metrics are frozen and immutable."""
        summary = self.metrics_baseline["authoritative_e9_summary"]
        self.assertEqual(summary["predictions_count"], 26)
        self.assertEqual(summary["true_positives"], 4)
        self.assertEqual(summary["false_positives"], 22)
        self.assertEqual(summary["false_negatives"], 61)
        self.assertAlmostEqual(summary["precision"], 0.1538, places=4)
        self.assertAlmostEqual(summary["recall"], 0.0615, places=4)
        self.assertAlmostEqual(summary["f1_score"], 0.0879, places=4)
        self.assertAlmostEqual(summary["mean_iou"], 0.6659, places=4)
        self.assertAlmostEqual(summary["rmse_2d_meters"], 3.04, places=2)


if __name__ == "__main__":
    unittest.main()
