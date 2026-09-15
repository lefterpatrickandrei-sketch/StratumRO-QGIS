# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Tool Wrappers.
Verifies topology validation, 90° regularization, eave retraction,
CAD/CP exports, and workspace context tools.
"""

import os
import shutil
import tempfile
import unittest
from shapely.geometry import Polygon, mapping

from stratum_ro.ai.tools.cadastral_tools import export_cp_file, export_topolt_cad, validate_topology
from stratum_ro.ai.tools.project_tools import get_workspace_context
from stratum_ro.ai.tools.segmentation_tools import run_sam2_segmentation
from stratum_ro.ai.tools.vector_tools import apply_eave_offset, create_planar_partition, regularize_footprints


class TestAITools(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_workspace_context(self):
        ctx = get_workspace_context()
        self.assertEqual(ctx["crs"], "EPSG:3844")
        self.assertEqual(ctx["vertical_datum"], "EPSG:5781")
        self.assertIn("hardware", ctx)
        self.assertEqual(ctx["status"], "ready")

    def test_validate_topology_clean_and_invalid(self):
        # 1. Clean valid square
        sq = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        res_clean = validate_topology([mapping(sq)])
        self.assertTrue(res_clean["is_all_valid"])
        self.assertEqual(res_clean["valid_count"], 1)

        # 2. Invalid self-intersecting bowtie polygon
        bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10), (0, 0)])
        res_invalid = validate_topology([mapping(bowtie)])
        self.assertFalse(res_invalid["is_all_valid"])
        self.assertEqual(res_invalid["invalid_count"], 1)

        # 3. Sliver polygon (area < 1m2)
        sliver = Polygon([(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1), (0, 0)])
        res_sliver = validate_topology([mapping(sliver)])
        self.assertFalse(res_sliver["is_all_valid"])

    def test_regularize_footprints(self):
        # Slightly noisy rectangle
        noisy = Polygon([(0.05, 0), (10.02, 0.08), (9.95, 8.01), (0.01, 7.95), (0.05, 0)])
        res = regularize_footprints([mapping(noisy)], mrr_trigger=0.70)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_polygons"], 1)
        self.assertGreaterEqual(res["canonical_rectangles_count"], 1)

    def test_apply_eave_offset(self):
        sq = Polygon([(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)])
        res = apply_eave_offset([mapping(sq)], offset_m=-0.40)
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["offset_applied_m"], -0.40)

        # Retracted polygon should have smaller area: (10 - 0.8)^2 = 9.2^2 = 84.64
        from shapely.geometry import shape
        retracted_geom = shape(res["polygons"][0])
        self.assertAlmostEqual(retracted_geom.area, 84.64, delta=0.5)

    def test_create_planar_partition(self):
        sector = Polygon([(0, 0), (50, 0), (50, 50), (0, 50), (0, 0)])
        bldg = Polygon([(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)])
        res = create_planar_partition([mapping(bldg)], mapping(sector))

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["total_sector_area_m2"], 2500.0)
        self.assertEqual(res["buildings_area_m2"], 100.0)
        self.assertEqual(res["unclassified_area_m2"], 2400.0)

    def test_export_topolt_cad_and_cp(self):
        bldg = Polygon([(100, 100), (120, 100), (120, 115), (100, 115), (100, 100)])
        dxf_out = os.path.join(self.temp_dir, "test_cad.dxf")
        cp_out = os.path.join(self.temp_dir, "test_cad.cp")

        # CAD DXF Export
        res_dxf = export_topolt_cad(dxf_out, buildings=[mapping(bldg)])
        self.assertEqual(res_dxf["status"], "success")
        self.assertTrue(os.path.isfile(dxf_out))
        self.assertGreater(res_dxf["file_size_kb"], 0.0)

        # CP Export
        pts = [
            {"nr": 1, "x": 434741.51, "y": 571142.19, "z": 345.2},
            {"nr": 2, "x": 434755.20, "y": 571142.19, "z": 345.1}
        ]
        res_cp = export_cp_file(cp_out, parcel_id="123456", points=pts)
        self.assertEqual(res_cp["status"], "success")
        self.assertTrue(os.path.isfile(cp_out))

    def test_run_sam2_segmentation_mock_resilience(self):
        prompts = [{"point": [10.0, 15.0]}, {"box": [5.0, 5.0, 25.0, 25.0]}]
        res = run_sam2_segmentation("dummy_ortho.tif", candidate_prompts=prompts)
        self.assertIn(res["status"], ["success", "fallback"])
        self.assertEqual(res["building_count"], 2)


if __name__ == "__main__":
    unittest.main()
