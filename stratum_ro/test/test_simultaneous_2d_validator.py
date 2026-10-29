# -*- coding: utf-8 -*-
"""
Unit tests for Simultaneous 6-Form 2D Roof Validator & Repair Engine (V1..V6).
Tests both synthetic cases and real orthophoto chips from the Opera GX audit.
"""

import unittest
from pathlib import Path
import numpy as np
from PIL import Image
from shapely.geometry import Polygon

from stratum_ro.core.qa_qc.simultaneous_2d_validator import (
    normalize_verdict,
    evaluate_building_simultaneously,
    deduplicate_v6_planar_nms,
    validate_v2_whole_roof_continuation,
    validate_v3_tree_occlusion_vs_l_shape,
    validate_v5_anti_artifact_and_nodata,
    repair_v3_complete_tree_bitten_corners,
)


class TestSimultaneous2DValidator(unittest.TestCase):
    def test_canonical_verdict_terminology(self):
        """Ensure CALCAN_ERROR is permanently mapped to AJUSTARE_CONTUR per owner instruction."""
        self.assertEqual(normalize_verdict("CALCAN_ERROR"), "AJUSTARE_CONTUR")
        self.assertEqual(normalize_verdict("AJUSTARE_CONTUR"), "AJUSTARE_CONTUR")
        self.assertEqual(normalize_verdict("ADMIS"), "ADMIS")
        self.assertEqual(normalize_verdict("MUTILATED"), "MUTILAT_DEFORMATIE_MODEL")
        self.assertEqual(normalize_verdict("FALSE_POS"), "ELIMINAT_EROARE_MAJORA")

    def test_v3_tree_bite_detection_and_completion_on_real_chip_opt_b_009(self):
        """
        OPT_B_009:C1 is a rectangular terracotta roof where an autumn tree crown bit out
        a 6-node L-notch on the southeast edge. V3 must detect the tree bite and complete
        the 4-node rectangle underneath the tree!
        """
        chip_path = Path("workspace/reviews/ortho_chips/OPT_B_009_C1.jpg")
        if not chip_path.is_file():
            self.skipTest("OPT_B_009_C1.jpg not present")
        rgb = np.array(Image.open(chip_path).convert("RGB"))
        roof_px = [
            [99.0, 179.6],
            [53.4, 139.4],
            [129.2, 53.4],
            [165.6, 85.5],
            [117.2, 140.4],
            [126.4, 148.5],
            [99.0, 179.6],
        ]
        poly_s70 = Polygon(
            [
                (391034.776, 585592.424),
                (391027.943, 585598.448),
                (391039.287, 585611.317),
                (391044.744, 585606.506),
                (391037.502, 585598.291),
                (391038.878, 585597.077),
            ]
        )
        v3 = validate_v3_tree_occlusion_vs_l_shape(rgb, [(p[0], p[1]) for p in roof_px], poly_s70)
        self.assertFalse(v3.passed, f"Expected V3 to catch tree bite on OPT_B_009: {v3}")
        self.assertTrue(v3.details["is_tree_bite"])

        rep_poly, rep_px, did_repair = repair_v3_complete_tree_bitten_corners(
            poly_s70, [(p[0], p[1]) for p in roof_px], rgb
        )
        self.assertTrue(did_repair)
        self.assertEqual(len(rep_poly.exterior.coords) - 1, 4)
        self.assertGreater(rep_poly.area, poly_s70.area)

    def test_v5_catches_nodata_border_distortion_opt_b_196(self):
        """OPT_B_196:C1 was marked MUTILATED by owner because it sits on a torn NoData border."""
        chip_path = Path("workspace/reviews/ortho_chips/OPT_B_196_C1.jpg")
        if not chip_path.is_file():
            self.skipTest("OPT_B_196_C1.jpg not present")
        rgb = np.array(Image.open(chip_path).convert("RGB"))
        roof_px = [[53.4, 96.6], [96.6, 65.4], [116.6, 93.1], [73.4, 124.3], [53.4, 96.6]]
        poly_s70 = Polygon([(0, 0), (8, 0), (8, 4.5), (0, 4.5)])
        v5 = validate_v5_anti_artifact_and_nodata(rgb, [(p[0], p[1]) for p in roof_px], poly_s70, touches_nodata_flag=1)
        self.assertFalse(v5.passed, f"Expected V5 to reject NoData border distortion OPT_B_196: {v5}")

    def test_v2_catches_half_roof_fragment_and_extends(self):
        """Synthetic terracotta roof (100x80 px) where initial polygon only covers left half (50x80 px)."""
        rgb = np.full((160, 200, 3), fill_value=60, dtype=np.uint8)  # dark courtyard
        # Draw terracotta roof from x=40..160, y=40..120
        rgb[40:120, 40:160] = np.array([175, 85, 55], dtype=np.uint8)
        # Initial polygon only covers x=42..95, y=42..118 (half roof!)
        half_px = [[42.0, 42.0], [95.0, 42.0], [95.0, 118.0], [42.0, 118.0], [42.0, 42.0]]
        poly_s70 = Polygon([(390004.2, 585011.8), (390009.5, 585011.8), (390009.5, 585004.2), (390004.2, 585004.2)])
        bounds_s70 = [390000.0, 585000.0, 390020.0, 585016.0]

        v2 = validate_v2_whole_roof_continuation(rgb, [(p[0], p[1]) for p in half_px])
        self.assertFalse(v2.passed, "V2 must fail when roof texture continues past the right edge")

        report = evaluate_building_simultaneously(
            "TEST_HALF_ROOF",
            "CALCAN_ERROR",
            rgb,
            half_px,
            poly_s70,
            bounds_s70,
            auto_repair=True,
        )
        self.assertEqual(report.canonical_verdict, "AJUSTARE_CONTUR")
        self.assertIsNotNone(report.repaired_polygon_s70)
        self.assertGreater(report.repaired_polygon_s70.area, poly_s70.area * 1.5)

    def test_v6_hierarchical_deduplication_preserves_admis_over_false_pos(self):
        """
        When an ELIMINAT (FALSE_POS) polygon overlaps an ADMIS polygon on the same building
        (like OPT_B_156 over OPT_B_151), V6 must keep ADMIS and suppress ELIMINAT.
        """
        p_admis = Polygon([(0, 0), (12, 0), (12, 10), (0, 10)])
        p_fp_dup = Polygon([(1, 1), (11, 1), (11, 9), (1, 9)])  # 100% inside p_admis
        p_incomplet = Polygon([(0, 0), (12, 0), (12, 10), (0, 10)])

        records = [
            {"id": "OPT_B_156:C1", "candidate_id": "OPT_B_156:C1", "verdict": "FALSE_POS", "poly_s70": p_fp_dup},
            {"id": "OPT_B_151:C1", "candidate_id": "OPT_B_151:C1", "verdict": "ADMIS", "poly_s70": p_admis},
            {
                "id": "OPT_B_151:C1_INCOMPLET",
                "candidate_id": "OPT_B_151:C1",
                "verdict": "ADMIS",
                "poly_s70": p_incomplet,
            },
        ]
        kept, suppressed = deduplicate_v6_planar_nms(records)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["id"], "OPT_B_151:C1")
        self.assertEqual(kept[0]["canonical_verdict"], "ADMIS")
        self.assertEqual(len(suppressed), 2)


if __name__ == "__main__":
    unittest.main()
