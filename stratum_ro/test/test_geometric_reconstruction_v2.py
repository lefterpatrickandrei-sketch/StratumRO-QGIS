# -*- coding: utf-8 -*-
"""
Unit Tests for Building Extraction Quality V2
=============================================
Tests:
  1. GSD-dependent morphological mask cleanup.
  2. Adaptive 4-tier classification (OBB, Manhattan L/U/T, Complex, Atypical Oblique).
  3. L-shape concavity preservation (no flattening into rectangles).
  4. Non-destructive oblique preservation.
  5. Active LiDAR 3D facade step evaluation.
  6. Multi-factor confidence score & traffic light (Green, Yellow, Red).
"""

import unittest
import numpy as np
from shapely.geometry import Polygon, box
import rasterio
from rasterio.transform import from_origin

from stratum_ro.geometric_reconstruction_v2 import AdaptiveContourReconstructor
from stratum_ro.lidar_quality_gate import LidarQualityGate


class TestGeometricReconstructionV2(unittest.TestCase):

    def setUp(self):
        self.reconstructor = AdaptiveContourReconstructor(gsd_m=0.15)
        self.quality_gate = LidarQualityGate(min_wall_drop_m=1.8, min_bldg_height_m=2.5)

    def test_clean_binary_mask(self):
        # 50x50 mask with a small 2x2 hole inside and a 1-pixel spike outside
        mask = np.zeros((50, 50), dtype=np.uint8)
        mask[10:40, 10:40] = 1
        mask[20:22, 20:22] = 0  # interior skylight hole
        mask[8:10, 15] = 1       # thin exterior fringe

        cleaned = self.reconstructor.clean_binary_mask(mask, close_m=0.45, open_m=0.30)
        # Hole should be filled
        self.assertEqual(cleaned[20, 20], 1)
        # Thin fringe should be removed
        self.assertEqual(cleaned[8, 15], 0)

    def test_class_a_obb_reconstruction(self):
        # Simple rectangle 20m x 10m in Stereo 70 coordinates
        poly_rect = Polygon([(100, 100), (120, 100), (120, 110), (100, 110), (100, 100)])
        res = self.reconstructor.classify_and_reconstruct(poly_rect)

        self.assertEqual(res["clasa_forma"], "DREPTUNGHI_OBB")
        self.assertEqual(res["num_vertices"], 4)
        self.assertAlmostEqual(res["geometry"].area, 200.0, places=1)

    def test_class_b_l_shaped_reconstruction_preserves_concavity(self):
        # L-shaped building: 30x20 with 10x10 cutout (Area = 500 m2)
        p1 = box(100, 100, 130, 110)  # base 30x10
        p2 = box(100, 110, 110, 120)  # vertical wing 10x10
        l_shape = p1.union(p2)

        res = self.reconstructor.classify_and_reconstruct(l_shape)

        self.assertEqual(res["clasa_forma"], "MANHATTAN_LUT")
        # Geometry MUST NOT be replaced with a full bounding box (area 600 m2)
        rec_poly = res["geometry"]
        self.assertTrue(rec_poly.area < 550.0, "L-shape was erroneously flattened into a full bounding box!")
        self.assertGreater(res["ortho_ratio"], 0.70)

    def test_class_d_oblique_preservation(self):
        # Trapezoid with an oblique street-front facade at ~65 degrees
        oblique_poly = Polygon([(100, 100), (125, 100), (115, 120), (100, 120), (100, 100)])
        res = self.reconstructor.classify_and_reconstruct(oblique_poly)

        self.assertEqual(res["clasa_forma"], "ATIPIC_OBLIC")
        # Should retain non-destructive smooth simplification
        self.assertAlmostEqual(res["geometry"].area, oblique_poly.area, delta=5.0)

    def test_lidar_quality_gate_facade_step(self):
        # Create a synthetic nDSM: building area is 5.0m, background is 0.0m
        ndsm = np.zeros((100, 100), dtype=np.float32)
        # Transform: 1 pixel = 0.5m, origin at (100, 200)
        tr = from_origin(100.0, 200.0, 0.5, 0.5)

        # Building from col 20 to 60 (x: 110 to 130), row 20 to 60 (y: 190 to 170)
        ndsm[20:60, 20:60] = 5.2

        bldg_poly = Polygon([(110, 170), (130, 170), (130, 190), (110, 190), (110, 170)])
        step_res = self.quality_gate.evaluate_facade_height_steps(bldg_poly, ndsm, tr)

        self.assertGreaterEqual(step_res["step_valid_ratio"], 0.80)
        self.assertGreaterEqual(step_res["mean_step_m"], 4.0)

    def test_composite_confidence_scoring(self):
        # High quality case
        ndsm = np.zeros((100, 100), dtype=np.float32)
        tr = from_origin(100.0, 200.0, 0.5, 0.5)
        ndsm[20:60, 20:60] = 6.0
        bldg_poly = Polygon([(110, 170), (130, 170), (130, 190), (110, 190), (110, 170)])

        res_green = self.quality_gate.compute_composite_confidence(
            poly=bldg_poly,
            sam2_score=0.92,
            ndsm_array=ndsm,
            transform=tr,
            ortho_contrast=45.0
        )

        self.assertGreaterEqual(res_green["conf_final"], 0.85)
        self.assertEqual(res_green["action_code"], "VERDE_ACCEPTAT_AUTOMAT")

        # Low quality / ground artifact case (Z = 0.5m, low SAM score)
        ndsm_low = np.zeros((100, 100), dtype=np.float32)
        ndsm_low[20:60, 20:60] = 0.8
        res_red = self.quality_gate.compute_composite_confidence(
            poly=bldg_poly,
            sam2_score=0.40,
            ndsm_array=ndsm_low,
            transform=tr,
            ortho_contrast=10.0
        )

        self.assertLess(res_red["conf_final"], 0.65)
        self.assertEqual(res_red["action_code"], "ROSU_RESPINS_ARTEFACT")

    def test_format_hybrid_buildings_with_quality_v2(self):
        from stratum_ro.vectorizer import CadastralVectorizer
        import tempfile
        import os

        vec = CadastralVectorizer(crs="EPSG:3844")

        # Two building proposals: one rectangle, one L-shaped
        p_rect = box(100, 100, 120, 110)
        p_l = box(140, 100, 160, 110).union(box(140, 110, 148, 120))

        candidates = [
            {"geometry": p_rect, "sam2_score": 0.90, "mean_h": 6.5, "max_h": 7.0, "status": "CONFIRMAT_HIBRID"},
            {"geometry": p_l, "sam2_score": 0.88, "mean_h": 5.0, "max_h": 6.2, "status": "CONFIRMAT_HIBRID"}
        ]

        feats = vec.format_hybrid_buildings(
            candidates,
            use_quality_v2=True,
            record_intermediate_stages=True
        )

        self.assertEqual(len(feats), 2)
        # Check that V2 attributes are present
        for f in feats:
            self.assertIn("clasa_forma", f)
            self.assertIn("conf_final", f)
            self.assertIn("action_code", f)
            self.assertIn("step_valid_pct", f)
            self.assertIn("std_acoperis", f)

        # Check that intermediate stages are recorded
        self.assertIn("STAGE_1_RAW_CONTOUR", vec.last_intermediate_stages)
        self.assertIn("STAGE_5_FINAL_CONFIDENCE", vec.last_intermediate_stages)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_gpkg = os.path.join(tmpdir, "test_stages.gpkg")
            vec.save_intermediate_stages_to_gpkg(tmp_gpkg)
            self.assertTrue(os.path.exists(tmp_gpkg))


if __name__ == "__main__":
    unittest.main()
