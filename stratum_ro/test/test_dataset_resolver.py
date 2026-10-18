# -*- coding: utf-8 -*-
"""
Unit tests for CanonicalDatasetResolver.
Validates dataset discovery, priority order, SHA256 computation, and metadata extraction.
"""

import os
import tempfile
import unittest
from unittest.mock import patch
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

    def test_resolve_missing_datasets_is_explicit(self):
        # A clean CI checkout has no workstation-specific imagery or model weights.
        # Exercise the resolver's missing-data contract without inspecting local disks.
        with patch.object(self.resolver, "_find_first_existing", return_value=("", "missing", 0.0)):
            datasets = self.resolver.resolve_all()
        self.assertIn("lidar", datasets)
        self.assertIn("dtm", datasets)
        self.assertIn("orthophoto", datasets)
        self.assertIn("ground_truth", datasets)
        self.assertIn("sam2_model", datasets)

        for name, metadata in datasets.items():
            with self.subTest(dataset=name):
                self.assertIsInstance(metadata, DatasetMetadata)
                self.assertFalse(metadata.exists)
                self.assertFalse(metadata.readable)
                self.assertEqual(metadata.source, "missing")
                self.assertEqual(metadata.confidence, 0.0)
                self.assertEqual(metadata.sha256, "")

    def test_explicit_ground_truth_and_model_file_metadata(self):
        # The tracked GT is real reference data. The tiny model file is only a
        # metadata fixture: this test does not claim to validate SAM2 weights.
        gt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                               "data", "ground_truth", "tier1_teren.geojson")
        gt = self.resolver.resolve_ground_truth(ui_path=gt_path)
        self.assertTrue(gt.exists)
        self.assertEqual(gt.crs, "EPSG:3844")
        self.assertGreater(gt.file_size, 0)
        self.assertEqual(len(gt.sha256), 64)
        self.assertEqual(gt.source, "ui")
        with tempfile.NamedTemporaryFile("wb", suffix=".pt", delete=False) as stream:
            stream.write(b"model metadata fixture, not inference weights")
            model_path = stream.name
        try:
            sam2 = self.resolver.resolve_sam2_model(ui_path=model_path)
            self.assertTrue(sam2.exists)
            self.assertTrue(sam2.readable)
            self.assertEqual(sam2.source, "ui")
            self.assertEqual(sam2.confidence, 1.0)
            self.assertEqual(sam2.file_size, os.path.getsize(model_path))
            self.assertEqual(sam2.sha256, self.resolver.compute_sha256(model_path))
        finally:
            os.remove(model_path)

    def test_ui_override_priority(self):
        # When UI path is explicitly provided and valid, it takes priority (conf=1.0)
        gt_meta = self.resolver.resolve_ground_truth(ui_path="data/ground_truth/tier1_teren.geojson")
        self.assertEqual(gt_meta.source, "ui")
        self.assertEqual(gt_meta.confidence, 1.0)


if __name__ == "__main__":
    unittest.main()
