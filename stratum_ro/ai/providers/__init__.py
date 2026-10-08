# -*- coding: utf-8 -*-
"""
StratumRO AI Providers.
Defines base interfaces and concrete implementations for model providers:
NVIDIA NIM, OpenAI, Ollama, and Local deterministic mock.
"""

from .base import BaseAIProvider, ProviderCapability, ProviderResponse
from .nvidia_nim_provider import NvidiaNIMProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .local_provider import LocalProvider
from .union_alpha_provider import UnionAlphaProvider
from .anthropic_provider import AnthropicProvider
from .gemini_provider import GeminiProvider

__all__ = [
    "BaseAIProvider",
    "ProviderCapability",
    "ProviderResponse",
    "NvidiaNIMProvider",
    "OpenAIProvider",
    "OllamaProvider",
    "LocalProvider",
    "UnionAlphaProvider",
    "AnthropicProvider",
    "GeminiProvider",
]

