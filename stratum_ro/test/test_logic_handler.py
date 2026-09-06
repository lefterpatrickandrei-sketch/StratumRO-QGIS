# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO Logic Handler and Fallback Orchestrator.
"""

import unittest
from stratum_ro.logic_handler import extract_json_from_llm, StratumOrchestrator
from stratum_ro.orchestrator import request_segmentation_plan, get_mock_segmentation_plan


class TestStratumROLogicHandler(unittest.TestCase):

    def test_extract_json_clean(self):
        raw = '{"project_name": "Test", "crs": "EPSG:3844", "geometry": {}, "administrative": {"siruta_code": 100}}'
        data = extract_json_from_llm(raw)
        self.assertIsNotNone(data)
        self.assertEqual(data.get("project_name"), "Test")

    def test_extract_json_markdown_wrapper(self):
        raw = """Here is the segmentation plan:
```json
{
    "project_name": "WrapTest",
    "crs": "EPSG:3844",
    "geometry": {
        "type": "Polygon",
        "coordinates": [[[26.0, 44.0], [26.1, 44.0], [26.1, 44.1], [26.0, 44.1], [26.0, 44.0]]]
    },
    "administrative": {"siruta_code": 26573}
}
```
Hope this helps!"""
        data = extract_json_from_llm(raw)
        self.assertIsNotNone(data)
        self.assertEqual(data.get("project_name"), "WrapTest")
        self.assertEqual(data.get("administrative", {}).get("siruta_code"), 26573)

    def test_extract_json_invalid(self):
        data = extract_json_from_llm("No JSON here, just plain text")
        self.assertIsNone(data)

    def test_orchestrator_validation(self):
        valid_payload = {
            "project_name": "Demo",
            "crs": "EPSG:3844",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[26.0, 44.0], [26.1, 44.0], [26.1, 44.1], [26.0, 44.1], [26.0, 44.0]]]
            },
            "administrative": {"siruta_code": 12345}
        }
        orch = StratumOrchestrator(valid_payload)
        self.assertTrue(orch.is_valid())
        self.assertTrue(orch.validate_plan())
        self.assertEqual(orch.get_siruta_code(), 12345)
        self.assertTrue(orch.get_geometry_wkt().startswith("POLYGON(("))

    def test_orchestrator_invalid_crs(self):
        invalid_payload = {
            "project_name": "Demo",
            "crs": "EPSG:4326",  # WGS84 instead of Stereo70
            "geometry": {},
            "administrative": {"siruta_code": 12345}
        }
        orch = StratumOrchestrator(invalid_payload)
        self.assertFalse(orch.validate_plan())

    def test_mock_fallback_request(self):
        # Test forced mock fallback
        mock_chain = [{"name": "local_mock_engine", "timeout": 0.1}]
        orch, model_used = request_segmentation_plan(26573, "MockTest", chain=mock_chain)
        self.assertTrue(orch.validate_plan())
        self.assertEqual(orch.get_siruta_code(), 26573)
        self.assertEqual(model_used, "local_mock_engine")


if __name__ == '__main__':
    unittest.main()
