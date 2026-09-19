# -*- coding: utf-8 -*-
"""
Unit tests for Phase 3 modular components:
- CandidateGenerator
- MultimodalVegetationFilter
- PromptGenerator
- MaskFusionEngine
- OrientationAwareRegularizer
"""

import unittest
import numpy as np
from shapely.geometry import Polygon, box

from stratum_ro.candidate_generator import CandidateGenerator
from stratum_ro.vegetation_filter import MultimodalVegetationFilter
from stratum_ro.prompt_generator import PromptGenerator
from stratum_ro.mask_fusion import MaskFusionEngine
from stratum_ro.orientation_regularizer import OrientationAwareRegularizer


class TestPhase3Modules(unittest.TestCase):

    def test_candidate_generator_synthetic(self):
        gen = CandidateGenerator(height_threshold=2.5, min_area_m2=25.0, morphology="closing_3x3", pixel_size_m=1.0)
        # Create 100x100 raster with a 10x10 building (100 m2) with height 6.0m
        ndsm = np.zeros((100, 100), dtype=np.float32)
        ndsm[20:30, 20:30] = 6.0
        # Small noise blob of 2x2 (4 m2) with height 3.0m (should be filtered out < 25m2)
        ndsm[50:52, 50:52] = 3.0

        cands = gen.generate_candidates(ndsm)
        self.assertEqual(len(cands), 1)
        self.assertEqual(cands[0]["cand_id"], "CAND_001")
        self.assertAlmostEqual(cands[0]["area_m2"], 100.0, places=1)
        self.assertAlmostEqual(cands[0]["mean_h"], 6.0, places=1)
        self.assertEqual(cands[0]["bbox_px"], [20, 20, 30, 30])

    def test_vegetation_filter_exg(self):
        # Create a green image patch (vegetation) vs a grey roof patch
        green_img = np.zeros((3, 50, 50), dtype=np.uint8)
        green_img[0, :, :] = 40   # R
        green_img[1, :, :] = 160  # G
        green_img[2, :, :] = 50   # B

        roof_img = np.zeros((3, 50, 50), dtype=np.uint8)
        roof_img[0, :, :] = 130  # R
        roof_img[1, :, :] = 125  # G
        roof_img[2, :, :] = 120  # B

        exg_green = MultimodalVegetationFilter.compute_exg(green_img)
        exg_roof = MultimodalVegetationFilter.compute_exg(roof_img)

        self.assertGreater(float(np.mean(exg_green)), 0.15)
        self.assertLess(float(np.mean(exg_roof)), 0.05)

        v_filter = MultimodalVegetationFilter()
        cand = {"bbox_px": [10, 10, 40, 40], "slice": (slice(10, 40), slice(10, 40)), "std_h": 2.5}
        ndsm = np.ones((50, 50), dtype=np.float32) * 5.0

        eval_veg = v_filter.evaluate_candidate(cand, green_img, ndsm)
        self.assertTrue(eval_veg["is_vegetation"])

        eval_roof = v_filter.evaluate_candidate(cand, roof_img, ndsm)
        self.assertFalse(eval_roof["is_vegetation"])

    def test_prompt_generator_strategies(self):
        p_gen = PromptGenerator()
        cand = {"bbox_px": [100, 200, 150, 300], "center_px": [125, 250]}

        # Strategy A: Point only
        p_pt = p_gen.generate_prompt(cand, strategy="point_center")
        self.assertIsNone(p_pt["box"])
        self.assertEqual(len(p_pt["point_coords"]), 1)
        self.assertEqual(p_pt["point_labels"][0], 1)

        # Strategy B: Box only
        p_bx = p_gen.generate_prompt(cand, strategy="box_only")
        self.assertIsNotNone(p_bx["box"])
        self.assertIsNone(p_bx["point_coords"])

        # Strategy C: Box and multipoint
        p_multi = p_gen.generate_prompt(cand, strategy="box_and_multipoint")
        self.assertIsNotNone(p_multi["box"])
        self.assertEqual(len(p_multi["point_coords"]), 5)
        self.assertTrue(np.all(p_multi["point_labels"] == 1))

        # Strategy D: Pos and neg
        p_posneg = p_gen.generate_prompt(cand, strategy="box_pos_neg")
        self.assertEqual(len(p_posneg["point_coords"]), 5)
        self.assertEqual(p_posneg["point_labels"][0], 1)
        self.assertTrue(np.all(p_posneg["point_labels"][1:] == 0))

    def test_mask_fusion_engine(self):
        fusion = MaskFusionEngine(iou_merge_threshold=0.20)
        # Create two overlapping polygons representing adjacent wings of the same complex
        p1 = box(10, 10, 30, 30)
        p2 = box(25, 10, 45, 30)  # overlaps p1 from x=25 to 30

        preds = [
            {"pred_id": "P1", "cand_id": "C1", "sam2_score": 0.9, "geometry": p1},
            {"pred_id": "P2", "cand_id": "C2", "sam2_score": 0.85, "geometry": p2}
        ]

        fused = fusion.fuse_overlapping_predictions(preds)
        self.assertEqual(len(fused), 1)
        self.assertEqual(fused[0]["fused_from_count"], 2)
        self.assertAlmostEqual(fused[0]["geometry"].area, 35 * 20, delta=2.0)

    def test_orientation_regularizer(self):
        reg = OrientationAwareRegularizer(tolerance_m=0.5)
        # Create a rotated rectangle (30x10) rotated by 30 degrees
        from shapely.affinity import rotate
        base_rect = box(0, 0, 30, 10)
        rotated_rect = rotate(base_rect, 30.0, origin=(15, 5))

        # Dominant angle should be approximately 30°
        dom_angle = reg.get_dominant_angle(rotated_rect)
        self.assertAlmostEqual(abs(dom_angle), 30.0, delta=1.0)

        res = reg.regularize_polygon(rotated_rect)
        self.assertIsNotNone(res)
        self.assertAlmostEqual(res["reg_area_m2"], 300.0, delta=10.0)
        self.assertGreaterEqual(res["ortho_ratio_reg"], 0.80)


if __name__ == "__main__":
    unittest.main()
