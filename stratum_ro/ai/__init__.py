# -*- coding: utf-8 -*-
"""
StratumRO AI Orchestration Subsystem.
Implements a provider-independent AI control plane and capability router,
enabling multi-model execution (NVIDIA NIM, OpenAI, Claude, Ollama, Local)
without compromising deterministic geodetic and cadastral operations.
"""

from .providers.base import BaseAIProvider, ProviderCapability, ProviderResponse
from .registry import ProviderRegistry
from .router import AIRouter, TaskType

__all__ = [
    "BaseAIProvider",
    "ProviderCapability",
    "ProviderResponse",
    "ProviderRegistry",
    "AIRouter",
    "TaskType",
]
