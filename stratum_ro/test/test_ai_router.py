# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO AI Router and Registry.
Verifies capability-based routing, deterministic task enforcement (no LLM for math),
mode selection, and fallback execution.
"""

import unittest
from unittest.mock import MagicMock

from stratum_ro.ai.providers.base import (
    BaseAIProvider,
    ProviderCapability,
    ProviderResponse,
)
from stratum_ro.ai.registry import ProviderRegistry
from stratum_ro.ai.router import AIRouter, ExecutionMode, TaskType


class TestAIRouterAndRegistry(unittest.TestCase):

    def setUp(self):
        self.registry = ProviderRegistry(auto_register=True)
        self.router = AIRouter(self.registry)

    def test_registry_default_providers(self):
        providers = self.registry.list_all()
        names = [p.name for p in providers]
        self.assertIn("local_mock", names)
        self.assertIn("nvidia_nim", names)
        self.assertIn("openai", names)
        self.assertIn("ollama", names)

    def test_registry_status_summary(self):
        summary = self.registry.get_status_summary()
        self.assertIn("local_mock", summary)
        self.assertTrue(summary["local_mock"]["available"])
        self.assertIn("planning", summary["local_mock"]["capabilities"])

    def test_deterministic_tasks_bypass_llms(self):
        """Pure GIS/cadastral math must NEVER be routed to an LLM."""
        deterministic_types = [
            TaskType.GEOMETRY,
            TaskType.COORDINATE_TRANSFORM,
            TaskType.TOPOLOGY_VALIDATION,
            TaskType.CAD_EXPORT,
            TaskType.NDSM_EXTRACTION,
        ]

        for t_type in deterministic_types:
            decision = self.router.route_task(t_type)
            self.assertFalse(
                decision.is_llm_task,
                f"Task {t_type} must not be flagged as an LLM task"
            )
            self.assertEqual(
                decision.execution_target,
                "deterministic_engine",
                f"Task {t_type} must target deterministic engine"
            )
            self.assertIsNone(decision.provider)

    def test_optical_segmentation_routing(self):
        """Building segmentation routes to local SAM2/ONNX, not LLM."""
        decision = self.router.route_task(TaskType.OPTICAL_SEGMENTATION)
        self.assertFalse(decision.is_llm_task)
        self.assertEqual(decision.execution_target, "local_sam2")
        self.assertIsNone(decision.provider)

    def test_planning_local_only_mode(self):
        """In LOCAL_ONLY mode, router selects ollama or local_mock."""
        decision = self.router.route_task(
            TaskType.PLANNING,
            mode=ExecutionMode.LOCAL_ONLY
        )
        self.assertTrue(decision.is_llm_task)
        self.assertIn(decision.execution_target, ["provider:ollama", "provider:local_mock"])

    def test_execute_with_fallback_guarantee(self):
        """execute_with_fallback must succeed with local_mock even if providers fail."""
        # Create a mock failing registry
        mock_failing_p = MagicMock(spec=BaseAIProvider)
        mock_failing_p.name = "failing_cloud"
        mock_failing_p.is_available.return_value = True
        mock_failing_p.capabilities.return_value = [ProviderCapability.PLANNING]
        mock_failing_p.generate.return_value = ProviderResponse(
            content="",
            model_name="fail",
            provider_name="failing_cloud",
            status="failed",
            error="Connection timeout"
        )

        reg = ProviderRegistry(auto_register=False)
        reg.register(mock_failing_p)
        from stratum_ro.ai.providers.local_provider import LocalProvider
        reg.register(LocalProvider())

        router = AIRouter(reg)
        resp = router.execute_with_fallback(
            task_type=TaskType.PLANNING,
            prompt="Generate AOI plan",
            context={"siruta_code": 26573}
        )

        self.assertTrue(resp.is_ok())
        self.assertIn(resp.status, ["success", "fallback"])
        self.assertIsNotNone(resp.parsed_json)
        self.assertEqual(resp.parsed_json["administrative"]["siruta_code"], 26573)


if __name__ == "__main__":
    unittest.main()
