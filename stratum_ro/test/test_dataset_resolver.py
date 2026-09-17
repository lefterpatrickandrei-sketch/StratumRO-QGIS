# -*- coding: utf-8 -*-
"""
Unit tests for CanonicalDatasetResolver.
Validates dataset discovery, priority order, SHA256 computation, and metadata extraction.
"""

import os
import unittest
from stratum_ro.dataset_resolver import CanonicalDatasetResolver, DatasetMetadata


class TestCanonicalDatasetResolver(unittest.TestCase):

    def setUp(self):
        self.resolver = CanonicalDatasetResolver()

    def test_compute_sha256(self):
        # Create a small temp file and test hashing
        import tempfile
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"StratumRO Test Data for SHA256")
            temp_path = f.name

        try:
            sha = CanonicalDatasetResolver.compute_sha256(temp_path)
            self.assertEqual(len(sha), 64)
            # Verify deterministic hash
            import hashlib
            expected = hashlib.sha256(b"StratumRO Test Data for SHA256").hexdigest()
            self.assertEqual(sha, expected)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_resolve_real_datasets(self):
        datasets = self.resolver.resolve_all()
        self.assertIn("lidar", datasets)
        self.assertIn("dtm", datasets)
        self.assertIn("orthophoto", datasets)
        self.assertIn("ground_truth", datasets)
        self.assertIn("sam2_model", datasets)

        # In current Windows desktop environment, real datasets exist
        gt = datasets["ground_truth"]
        self.assertTrue(gt.exists)
        self.assertEqual(gt.crs, "EPSG:3844")
        self.assertGreater(gt.file_size, 0)
        self.assertEqual(len(gt.sha256), 64)

        sam2 = datasets["sam2_model"]
        self.assertTrue(sam2.exists)
        self.assertGreater(sam2.file_size, 100_000_000)

    def test_ui_override_priority(self):
        # When UI path is explicitly provided and valid, it takes priority (conf=1.0)
        gt_meta = self.resolver.resolve_ground_truth(ui_path="data/ground_truth/tier1_teren.geojson")
        self.assertEqual(gt_meta.source, "ui")
        self.assertEqual(gt_meta.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
