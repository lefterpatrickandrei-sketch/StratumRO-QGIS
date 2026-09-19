# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO TaskSpec and Capability Resolution (Phase 4 Foundation).
Verifies strict CRS enforcement (EPSG:3844), bounding box validation within Romania,
risk tolerance parsing, serialization roundtrips, and ProviderRegistry capability resolution.
"""

import json
import tempfile
import unittest
from pathlib import Path

from stratum_ro.ai.task_spec import TaskSpec, RiskTolerance, DeliverableType
from stratum_ro.ai.registry import ProviderRegistry, CapabilityMatch
from stratum_ro.ai.providers.base import ProviderCapability


class TestTaskSpec(unittest.TestCase):

    def test_default_task_spec(self):
        """Default TaskSpec should be valid and configure Stereo 70 with LOW risk."""
        spec = TaskSpec()
        self.assertEqual(spec.target_crs, "EPSG:3844")
        self.assertEqual(spec.risk_tolerance, RiskTolerance.LOW.value)
        self.assertIn(DeliverableType.GPKG.value, spec.deliverables)
        self.assertIn(DeliverableType.DXF.value, spec.deliverables)
        self.assertTrue(len(spec.task_id) > 10)

        is_valid, errors = spec.validate()
        self.assertTrue(is_valid, f"Default spec failed validation: {errors}")
        self.assertEqual(len(errors), 0)

    def test_stereo70_crs_enforcement(self):
        """Non-Stereo 70 CRS must fail geodetic validation."""
        spec = TaskSpec(target_crs="EPSG:4326")
        is_valid, errors = spec.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Stereo 70" in err for err in errors))

        # Valid variant format
        spec_valid = TaskSpec(target_crs="3844")
        is_valid, errors = spec_valid.validate()
        self.assertTrue(is_valid)

    def test_aoi_bounds_validation(self):
        """Bounding box must be 4 numbers in Romania Stereo 70 geographic domain."""
        # Valid Cluj-Napoca / Feleacu area in Stereo 70
        valid_spec = TaskSpec(aoi_bounds=(390000.0, 580000.0, 395000.0, 585000.0))
        is_valid, errors = valid_spec.validate()
        self.assertTrue(is_valid, f"Valid Cluj bounds failed: {errors}")

        # Inverted coords (minx >= maxx)
        inverted_spec = TaskSpec(aoi_bounds=(400000.0, 580000.0, 390000.0, 585000.0))
        is_valid, errors = inverted_spec.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid bounding box" in err for err in errors))

        # Outside Romania domain (e.g. WGS84 degrees accidentally passed)
        wgs_spec = TaskSpec(aoi_bounds=(23.5, 46.7, 23.6, 46.8))
        is_valid, errors = wgs_spec.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("outside Romania Stereo 70" in err for err in errors))

    def test_risk_tolerance_validation(self):
        """Risk tolerance must belong to RiskTolerance enum values."""
        spec = TaskSpec(risk_tolerance="INVALID_RISK")
        is_valid, errors = spec.validate()
        self.assertFalse(is_valid)
        self.assertTrue(any("Invalid risk_tolerance" in err for err in errors))

        for risk in [RiskTolerance.LOW, RiskTolerance.MEDIUM, RiskTolerance.HIGH]:
            spec_ok = TaskSpec(risk_tolerance=risk.value)
            is_valid, errors = spec_ok.validate()
            self.assertTrue(is_valid)

    def test_input_file_existence_check(self):
        """Input check verifies files exist when requested."""
        with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tf:
            temp_path = tf.name

        try:
            spec = TaskSpec(inputs={
                "ortho": temp_path,
                "missing_lidar": "c:/non_existent_folder_xyz/missing.laz"
            })
            # Default validate() does not check files
            is_valid, errors = spec.validate(check_file_existence=False)
            self.assertTrue(is_valid)

            # Explicit check flag catches missing file
            is_valid, errors = spec.validate(check_file_existence=True)
            self.assertFalse(is_valid)
            self.assertEqual(len(errors), 1)
            self.assertIn("missing_lidar", errors[0])
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_serialization_roundtrip(self):
        """TaskSpec must cleanly serialize to/from dict and JSON."""
        spec = TaskSpec(
            name="Test Cadastral Task",
            description="Extraction in Feleacu",
            target_crs="EPSG:3844",
            aoi_bounds=(391000.0, 581000.0, 392000.0, 582000.0),
            deliverables=[DeliverableType.DXF.value, DeliverableType.PAD_TABLE.value],
            risk_tolerance=RiskTolerance.MEDIUM.value,
            parameters={"regularize": True, "tolerance_m": 0.05}
        )

        # Dict roundtrip
        data = spec.to_dict()
        spec_from_dict = TaskSpec.from_dict(data)
        self.assertEqual(spec.name, spec_from_dict.name)
        self.assertEqual(spec.aoi_bounds, spec_from_dict.aoi_bounds)
        self.assertEqual(spec.parameters, spec_from_dict.parameters)

        # JSON roundtrip
        json_str = spec.to_json()
        spec_from_json = TaskSpec.from_json(json_str)
        self.assertEqual(spec.task_id, spec_from_json.task_id)
        self.assertEqual(spec.deliverables, spec_from_json.deliverables)
        self.assertEqual(spec.aoi_bounds, spec_from_json.aoi_bounds)


class TestCapabilityResolution(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry(auto_register=True)

    def test_resolve_preferred_provider(self):
        """Resolving a preferred available provider returns direct match."""
        match = self.registry.resolve_provider(
            required_capability=ProviderCapability.PLANNING,
            preferred_provider="local_mock"
        )
        self.assertIsNotNone(match)
        self.assertIsInstance(match, CapabilityMatch)
        self.assertEqual(match.provider.name, "local_mock")
        self.assertFalse(match.is_fallback)

    def test_resolve_capability_candidates(self):
        """Resolving general capability returns an available provider offering it."""
        match = self.registry.resolve_provider(
            required_capability=ProviderCapability.PLANNING
        )
        self.assertIsNotNone(match)
        self.assertIn(ProviderCapability.PLANNING, match.provider.capabilities())

    def test_fallback_to_local_mock(self):
        """When a capability has no active specialized provider, fallback resolves to local_mock."""
        # Query a capability not in any cloud provider (or test fallback explicitly)
        reg = ProviderRegistry(auto_register=False)
        from stratum_ro.ai.providers.local_provider import LocalProvider
        reg.register(LocalProvider())

        # local_mock has LOCAL_INFERENCE, PLANNING, REASONING (does NOT have VISION)
        # Test a capability not supported by local_mock directly:
        match_none = reg.resolve_provider(
            required_capability=ProviderCapability.VISION,
            allow_fallback=False
        )
        self.assertIsNone(match_none)

        # With fallback permitted:
        match_fb = reg.resolve_provider(
            required_capability=ProviderCapability.VISION,
            allow_fallback=True
        )
        self.assertIsNotNone(match_fb)
        self.assertTrue(match_fb.is_fallback)
        self.assertEqual(match_fb.provider.name, "local_mock")


if __name__ == "__main__":
    unittest.main()
