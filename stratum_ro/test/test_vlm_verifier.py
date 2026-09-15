# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO VLM Verifier & Semantic Building Audit.
Validates multimodal prompt assembly, image cropping, ANCPI 600/2023 classifications,
deterministic heuristic fallbacks, and tool wrappers.
"""

import os
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from PIL import Image
from shapely.geometry import Polygon, box

from stratum_ro.ai.vlm_verifier import (
    VLMVerifier,
    VLMVerificationResult,
    crop_building_chip,
    encode_chip_base64,
    build_cadastral_prompt,
)
from stratum_ro.ai.providers.base import BaseAIProvider, ProviderCapability, ProviderResponse
from stratum_ro.ai.tools.vlm_tools import vlm_verify_single_building_tool


class MockMultimodalProvider(BaseAIProvider):
    def __init__(self, response_json=None):
        super().__init__(name="mock_vlm")
        self.response_json = response_json or {
            "is_real_building": True,
            "ancpi_code": "1CC",
            "typology": "Construcție Principală (Locuință)",
            "confidence": 0.96,
            "verdict": "APPROVED",
            "roof_type": "în 2 ape",
            "eave_visible": True,
            "has_calcan": False,
            "vegetation_occlusion": False,
            "reasoning": "Acoperiș în 2 ape vizibil clar, streașină bine delimitată."
        }

    def is_available(self) -> bool:
        return True

    def capabilities(self):
        return [ProviderCapability.VISION, ProviderCapability.REASONING]

    def list_models(self):
        return ["mock-vlm-v1"]

    def generate(self, prompt, system_prompt=None, context=None, model=None, timeout=10.0, **kwargs):
        import json
        raw = json.dumps(self.response_json)
        return ProviderResponse(
            content=raw,
            model_name="mock-vlm-v1",
            provider_name=self.name,
            status="success",
            duration_sec=0.05,
            parsed_json=self.response_json
        )


class TestVLMVerifier(unittest.TestCase):

    def setUp(self):
        self.poly_house = Polygon([(0, 0), (10, 0), (10, 8), (0, 8), (0, 0)])  # 80 mp
        self.poly_annex = Polygon([(0, 0), (5, 0), (5, 4), (0, 4), (0, 0)])    # 20 mp
        self.poly_tiny = Polygon([(0, 0), (1.5, 0), (1.5, 1.5), (0, 1.5), (0, 0)])  # 2.25 mp

    def test_encode_chip_base64(self):
        img = Image.new("RGB", (64, 64), color=(200, 100, 50))
        b64 = encode_chip_base64(img)
        self.assertIsInstance(b64, str)
        self.assertTrue(len(b64) > 100)

    def test_build_cadastral_prompt(self):
        sys_p, usr_p = build_cadastral_prompt("bldg_test_1", 85.5, 38.0, ndsm_height_m=6.5)
        self.assertIn("ANCPI", sys_p)
        self.assertIn("600/2023", sys_p)
        self.assertIn("1CC", usr_p)
        self.assertIn("2CC", usr_p)
        self.assertIn("bldg_test_1", usr_p)
        self.assertIn("85.5 mp", usr_p)
        self.assertIn("6.5 m", usr_p)

    def test_heuristic_fallback_small_noise(self):
        verifier = VLMVerifier(fallback_to_heuristic=True)
        res = verifier.verify_building(
            polygon=self.poly_tiny,
            ortho_path="non_existent_file.tif",
            building_id="bldg_noise",
            ndsm_height_m=1.2
        )
        self.assertEqual(res.building_id, "bldg_noise")
        self.assertFalse(res.is_real_building)
        self.assertEqual(res.ancpi_code, "FALSE_POSITIVE")
        self.assertEqual(res.verdict, "REJECTED")
        self.assertIn("heuristic_fallback", res.provider_used)

    def test_heuristic_fallback_annex(self):
        verifier = VLMVerifier(fallback_to_heuristic=True)
        res = verifier.verify_building(
            polygon=self.poly_annex,
            ortho_path="non_existent_file.tif",
            building_id="bldg_annex",
            ndsm_height_m=3.2
        )
        self.assertEqual(res.building_id, "bldg_annex")
        self.assertTrue(res.is_real_building)
        self.assertEqual(res.ancpi_code, "2CC")
        self.assertEqual(res.verdict, "APPROVED")
        self.assertIn("Anexă", res.typology)

    def test_heuristic_fallback_residential(self):
        verifier = VLMVerifier(fallback_to_heuristic=True)
        res = verifier.verify_building(
            polygon=self.poly_house,
            ortho_path="non_existent_file.tif",
            building_id="bldg_house",
            ndsm_height_m=7.0
        )
        self.assertEqual(res.building_id, "bldg_house")
        self.assertTrue(res.is_real_building)
        self.assertEqual(res.ancpi_code, "1CC")
        self.assertEqual(res.verdict, "APPROVED")
        self.assertGreaterEqual(res.confidence, 0.90)

    def test_vlm_with_mock_provider(self):
        mock_prov = MockMultimodalProvider()
        verifier = VLMVerifier(provider=mock_prov)

        # Mock crop_building_chip so it doesn't need a real raster file
        fake_chip = Image.new("RGB", (128, 128), (150, 80, 40))
        with patch("stratum_ro.ai.vlm_verifier.crop_building_chip", return_value=fake_chip):
            res = verifier.verify_building(
                polygon=self.poly_house,
                ortho_path="dummy_path.vrt",
                building_id="bldg_mock_01"
            )

        self.assertEqual(res.building_id, "bldg_mock_01")
        self.assertTrue(res.is_real_building)
        self.assertEqual(res.ancpi_code, "1CC")
        self.assertEqual(res.verdict, "APPROVED")
        self.assertEqual(res.roof_type, "în 2 ape")
        self.assertTrue(res.eave_visible)
        self.assertIn("mock_vlm", res.provider_used)

    def test_vlm_single_building_tool(self):
        wkt_poly = "POLYGON ((0 0, 10 0, 10 10, 0 10, 0 0))"
        out = vlm_verify_single_building_tool(
            geometry_wkt=wkt_poly,
            ortho_path="dummy.tif",
            building_id="tool_bldg_1",
            ndsm_height_m=5.5
        )
        self.assertEqual(out["status"], "success")
        res = out["result"]
        self.assertEqual(res["building_id"], "tool_bldg_1")
        self.assertEqual(res["ancpi_code"], "1CC")
        self.assertEqual(res["verdict"], "APPROVED")

    def test_vlm_empty_geometry(self):
        verifier = VLMVerifier()
        res = verifier.verify_building(
            polygon=Polygon(),
            ortho_path="dummy.tif",
            building_id="bldg_empty"
        )
        self.assertFalse(res.is_real_building)
        self.assertEqual(res.verdict, "REJECTED")


if __name__ == "__main__":
    unittest.main()
