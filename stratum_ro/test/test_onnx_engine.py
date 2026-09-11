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

    def test_exported_sam2_decoder_session(self):
        import os
        onnx_path = "models/sam2/sam2_decoder.onnx"
        if os.path.exists(onnx_path) and HAS_ONNX:
            engine = ONNXSegmentationEngine(decoder_onnx_path=onnx_path)
            self.assertIsNotNone(engine.decoder_session)
            inputs = [inp.name for inp in engine.decoder_session.get_inputs()]
            self.assertIn("image_embeddings", inputs)
            self.assertIn("point_coords", inputs)
            self.assertIn("point_labels", inputs)


if __name__ == "__main__":
    unittest.main()
