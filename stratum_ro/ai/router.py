# -*- coding: utf-8 -*-
"""
Task Routing Engine for StratumRO AI.
Enforces geodetic integrity by routing mathematical and CAD tasks to deterministic
engines, while routing reasoning/planning to optimal AI providers with automatic fallback.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from .providers.base import BaseAIProvider, ProviderCapability, ProviderResponse
from .registry import ProviderRegistry


class TaskType(str, Enum):
    # Pure deterministic operations — LLMs are strictly forbidden
    GEOMETRY = "geometry"
    COORDINATE_TRANSFORM = "coordinate_transform"
    TOPOLOGY_VALIDATION = "topology_validation"
    CAD_EXPORT = "cad_export"
    NDSM_EXTRACTION = "ndsm_extraction"

    # Optical and deep learning models
    OPTICAL_SEGMENTATION = "optical_segmentation"

    # Reasoning, planning, and diagnosis
    PLANNING = "planning"
    FAILURE_DIAGNOSIS = "failure_diagnosis"
    USER_INTERPRETATION = "user_interpretation"


class ExecutionMode(str, Enum):
    AUTO = "auto"
    LOCAL_ONLY = "local_only"
    HYBRID = "hybrid"
    CLOUD_PREFERRED = "cloud_preferred"


@dataclass
class RoutingDecision:
    task_type: TaskType
    execution_target: str  # "deterministic_engine", "local_sam2", "provider:<name>"
    is_llm_task: bool
    rationale: str
    provider: Optional[BaseAIProvider] = None


class AIRouter:
    """
    Capability-based router directing geodetic and AI tasks to their optimal execution path.
    """

    DETERMINISTIC_TASKS = {
        TaskType.GEOMETRY,
        TaskType.COORDINATE_TRANSFORM,
        TaskType.TOPOLOGY_VALIDATION,
        TaskType.CAD_EXPORT,
        TaskType.NDSM_EXTRACTION,
    }

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self.registry = registry or ProviderRegistry()

    def route_task(
        self,
        task_type: TaskType,
        mode: ExecutionMode = ExecutionMode.AUTO
    ) -> RoutingDecision:
        """
        Determines the execution target and provider for a given task type.
        """
        # 1. Deterministic tasks MUST bypass LLMs completely
        if task_type in self.DETERMINISTIC_TASKS:
            return RoutingDecision(
                task_type=task_type,
                execution_target="deterministic_engine",
                is_llm_task=False,
                rationale=f"Task {task_type.value} requires exact mathematical/geodetic computation. LLM routing prohibited.",
                provider=None
            )

        # 2. Local segmentation uses SAM2 / ONNX
        if task_type == TaskType.OPTICAL_SEGMENTATION:
            return RoutingDecision(
                task_type=task_type,
                execution_target="local_sam2",
                is_llm_task=False,
                rationale="Building segmentation routed to local Meta SAM2 Hiera / ONNX Runtime engine.",
                provider=None
            )

        # 3. Reasoning / Planning / Diagnosis tasks
        req_cap = ProviderCapability.PLANNING
        if task_type == TaskType.FAILURE_DIAGNOSIS:
            req_cap = ProviderCapability.VISION

        # Check mode constraints
        if mode == ExecutionMode.LOCAL_ONLY:
            # Check Ollama first, then Local Mock
            ollama = self.registry.get("ollama")
            if ollama and ollama.is_available():
                return RoutingDecision(
                    task_type=task_type,
                    execution_target="provider:ollama",
                    is_llm_task=True,
                    rationale="LOCAL_ONLY mode: routed to local Ollama daemon.",
                    provider=ollama
                )
            local_mock = self.registry.get("local_mock")
            return RoutingDecision(
                task_type=task_type,
                execution_target="provider:local_mock",
                is_llm_task=True,
                rationale="LOCAL_ONLY mode: routed to local deterministic mock provider.",
                provider=local_mock
            )

        # AUTO or HYBRID / CLOUD_PREFERRED sequence
        # Priority order: Union Alpha (frontier reasoning) -> OpenAI -> NVIDIA NIM -> Ollama -> Local Mock
        candidate_names = ["union_alpha", "openai", "nvidia_nim", "ollama", "local_mock"]
        if mode == ExecutionMode.HYBRID:
            # In hybrid mode, prefer NVIDIA NIM for vision, Union Alpha / OpenAI for planning
            if task_type == TaskType.FAILURE_DIAGNOSIS:
                candidate_names = ["nvidia_nim", "union_alpha", "openai", "ollama", "local_mock"]


        for name in candidate_names:
            p = self.registry.get(name)
            if p and p.is_available() and req_cap in p.capabilities():
                return RoutingDecision(
                    task_type=task_type,
                    execution_target=f"provider:{name}",
                    is_llm_task=True,
                    rationale=f"Selected active provider '{name}' for capability '{req_cap.value}'.",
                    provider=p
                )

        # Fallback to local mock if none matched
        mock_p = self.registry.get("local_mock")
        return RoutingDecision(
            task_type=task_type,
            execution_target="provider:local_mock",
            is_llm_task=True,
            rationale="All external providers offline or unavailable. Routed to local mock fallback.",
            provider=mock_p
        )

    def execute_with_fallback(
        self,
        task_type: TaskType,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        mode: ExecutionMode = ExecutionMode.AUTO,
        timeout: float = 10.0,
        **kwargs
    ) -> ProviderResponse:
        """
        Executes a reasoning task across the fallback chain, ensuring zero unhandled exceptions.
        """
        decision = self.route_task(task_type, mode=mode)
        if not decision.is_llm_task or decision.provider is None:
            return ProviderResponse(
                content="",
                model_name="none",
                provider_name="none",
                status="failed",
                error=f"Task {task_type.value} is not an LLM task."
            )

        # Primary attempt
        resp = decision.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            context=context,
            timeout=timeout,
            **kwargs
        )
        if resp.is_ok():
            return resp

        # Fallback cascade if primary fails
        fallback_order = ["nvidia_nim", "ollama", "local_mock"]
        for fb_name in fallback_order:
            if fb_name == decision.provider.name:
                continue
            fb_provider = self.registry.get(fb_name)
            if fb_provider and fb_provider.is_available():
                fb_resp = fb_provider.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    context=context,
                    timeout=timeout,
                    **kwargs
                )
                if fb_resp.is_ok():
                    fb_resp.status = "fallback"
                    return fb_resp

        # Final guarantee
        local_mock = self.registry.get("local_mock")
        if local_mock:
            return local_mock.generate(prompt=prompt, context=context)

        return resp
