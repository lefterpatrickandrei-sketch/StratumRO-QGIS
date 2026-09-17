# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Context Engine (MD 4 Sections 4-16, 33-38).
Verifies compact environmental snapshot, CRS breakdown, AOI sources,
hardware detection, raster/LiDAR metadata, provider status, and caching.
"""

import json
import time
import unittest

from stratum_ro.ai.context import (
    ContextEngine,
    ProjectContext,
    detect_hardware_context,
    detect_qgis_context,
    get_context_snapshot,
    invalidate_context_cache
)


class TestAIContextEngine(unittest.TestCase):

    def setUp(self):
        self.engine = ContextEngine(config_path="config.yaml", cache_ttl_sec=30.0)
        self.engine.invalidate()

    def test_detect_hardware_context(self):
        hw = detect_hardware_context()
        self.assertIn("os", hw)
        self.assertIn("cpu_count", hw)
        self.assertGreaterEqual(hw["cpu_count"], 1)
        self.assertIn("gpu_available", hw)
        self.assertIn("cuda_available", hw)
        self.assertIn("directml_available", hw)
        self.assertIsInstance(hw["gpu_available"], bool)

    def test_detect_qgis_context(self):
        qgis_ctx = detect_qgis_context()
        self.assertIn("running", qgis_ctx)
        self.assertIn("version", qgis_ctx)
        self.assertIn("crs", qgis_ctx)

    def test_context_snapshot_structure_and_size(self):
        snap = self.engine.get_snapshot()

        # Check required root sections
        for key in ["project", "crs", "aoi", "inputs", "layers", "hardware", "providers", "collected_at"]:
            self.assertIn(key, snap, f"Missing section: {key}")

        # Size control check (MD 4 Section 15): JSON payload must be compact (< 25 KB)
        dump_bytes = len(json.dumps(snap).encode("utf-8"))
        self.assertLess(dump_bytes, 25600, f"Snapshot too large: {dump_bytes} bytes")

    def test_crs_context_breakdown(self):
        snap = self.engine.get_snapshot()
        crs = snap["crs"]
        self.assertIn("project_crs", crs)
        self.assertIn("vertical_datum", crs)
        self.assertEqual(crs["project_crs"], "EPSG:3844")
        self.assertEqual(crs["vertical_datum"], "EPSG:5781")
        self.assertIn("raster_crs", crs)
        self.assertIn("lidar_crs", crs)

    def test_aoi_context_sources(self):
        # 1. Default active sector
        aoi_default = self.engine.get_aoi_context()
        self.assertEqual(aoi_default["source"], "config_default")
        self.assertEqual(len(aoi_default["bbox"]), 4)

        # 2. Explicit AOI override
        custom_bbox = [390000.0, 580000.0, 391000.0, 581000.0]
        self.engine.set_explicit_aoi(custom_bbox, source="task_input")
        aoi_custom = self.engine.get_aoi_context()
        self.assertEqual(aoi_custom["source"], "task_input")
        self.assertEqual(aoi_custom["bbox"], custom_bbox)

    def test_inputs_metadata_no_array_leak(self):
        inputs = self.engine.get_inputs_metadata()
        self.assertIn("rasters", inputs)
        self.assertIn("lidar", inputs)
        # Ensure only metadata is present, not raw data arrays
        for r in inputs["rasters"]:
            self.assertIn("dimensions", r)
            self.assertIn("bands", r)
            self.assertNotIn("data", r)
            self.assertNotIn("pixels", r)

        for l in inputs["lidar"]:
            self.assertIn("point_count", l)
            self.assertIn("density_pts_m2", l)
            self.assertNotIn("points", l)

    def test_cache_and_invalidation(self):
        self.engine.invalidate()
        t0 = time.perf_counter()
        snap1 = self.engine.get_snapshot()
        dur_cold = time.perf_counter() - t0

        t1 = time.perf_counter()
        snap2 = self.engine.get_snapshot()
        dur_cached = time.perf_counter() - t1

        self.assertEqual(snap1["collected_at"], snap2["collected_at"])
        self.assertLess(dur_cached, dur_cold)

        # Invalidate cache
        self.engine.invalidate()
        snap3 = self.engine.get_snapshot()
        self.assertGreaterEqual(snap3["collected_at"], snap1["collected_at"])

    def test_module_level_helpers(self):
        invalidate_context_cache()
        snap = get_context_snapshot()
        self.assertIn("project", snap)
        self.assertIn("providers", snap)


if __name__ == "__main__":
    unittest.main()
