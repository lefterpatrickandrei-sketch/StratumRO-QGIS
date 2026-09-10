# -*- coding: utf-8 -*-
"""
Unit tests for ONNX Runtime Inference Engine.
"""

import unittest
import numpy as np
from stratum_ro.onnx_engine import (
    ONNXSegmentationEngine,
    get_available_onnx_providers,
    get_preferred_provider,
    HAS_ONNX
)


class TestONNXEngine(unittest.TestCase):

    def test_onnx_availability(self):
        self.assertTrue(HAS_ONNX)
        providers = get_available_onnx_providers()
        self.assertIsInstance(providers, list)
        self.assertIn("CPUExecutionProvider", providers)

    def test_preferred_provider(self):
        pref = get_preferred_provider()
        self.assertIn(pref, ["DmlExecutionProvider", "CUDAExecutionProvider", "CPUExecutionProvider"])

    def test_engine_initialization_and_prediction(self):
        engine = ONNXSegmentationEngine()
        self.assertIsNotNone(engine.provider_name)

        dummy_img = np.zeros((256, 256, 3), dtype=np.uint8)
        dt = engine.set_image(dummy_img)
        self.assertGreaterEqual(dt, 0.0)

        poly = engine.predict_mask_box((390500.0, 585800.0, 390520.0, 585815.0))
        self.assertIsNotNone(poly)
        self.assertEqual(poly.geom_type, "Polygon")
        self.assertAlmostEqual(poly.area, 300.0, places=1)


if __name__ == "__main__":
    unittest.main()
