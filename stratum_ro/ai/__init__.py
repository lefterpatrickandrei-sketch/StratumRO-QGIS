# -*- coding: utf-8 -*-
"""
StratumRO AI Orchestration Subsystem.
Implements a provider-independent AI control plane and capability router,
enabling multi-model execution (NVIDIA NIM, OpenAI, Claude, Ollama, Local)
without compromising deterministic geodetic and cadastral operations.
"""

from .providers.base import BaseAIProvider, ProviderCapability, ProviderResponse
from .registry import ProviderRegistry, CapabilityMatch
from .router import AIRouter, TaskType
from .task_spec import TaskSpec, RiskTolerance, DeliverableType

__all__ = [
    "BaseAIProvider",
    "ProviderCapability",
    "ProviderResponse",
    "ProviderRegistry",
    "CapabilityMatch",
    "AIRouter",
    "TaskType",
    "TaskSpec",
    "RiskTolerance",
    "DeliverableType",
]

