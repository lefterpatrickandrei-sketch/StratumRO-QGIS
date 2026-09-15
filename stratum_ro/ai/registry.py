# -*- coding: utf-8 -*-
"""
Provider Registry for StratumRO AI.
Maintains a dynamic catalog of model providers and capability mappings,
supporting auto-discovery and health inspection.
"""

from typing import Any, Dict, List, Optional
from .providers.base import BaseAIProvider, ProviderCapability
from .providers.local_provider import LocalProvider
from .providers.nvidia_nim_provider import NvidiaNIMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.ollama_provider import OllamaProvider


class ProviderRegistry:
    """
    Central registry for active AI providers.
    """

    def __init__(self, auto_register: bool = True):
        self._providers: Dict[str, BaseAIProvider] = {}
        if auto_register:
            self.register_defaults()

    def register_defaults(self):
        """Registers the standard suite of StratumRO providers."""
        # 1. Local deterministic mock (always available)
        self.register(LocalProvider())

        # 2. NVIDIA NIM (reads key from .env / env var)
        self.register(NvidiaNIMProvider())

        # 3. OpenAI Platform (reads key from env var)
        self.register(OpenAIProvider())

        # 4. Ollama (local daemon)
        self.register(OllamaProvider())

    def register(self, provider: BaseAIProvider):
        """Registers a provider instance."""
        self._providers[provider.name] = provider

    def get(self, name: str) -> Optional[BaseAIProvider]:
        """Gets a provider by name."""
        return self._providers.get(name)

    def list_all(self) -> List[BaseAIProvider]:
        """Lists all registered providers."""
        return list(self._providers.values())

    def list_available(self) -> List[BaseAIProvider]:
        """Lists providers that are currently active and available."""
        return [p for p in self._providers.values() if p.is_available()]

    def find_by_capability(self, capability: ProviderCapability) -> List[BaseAIProvider]:
        """Returns all available providers offering the requested capability."""
        return [
            p for p in self.list_available()
            if capability in p.capabilities()
        ]

    def get_status_summary(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a structured dictionary of provider availability and models,
        designed for display in QGIS DockWidget and audit logs.
        """
        summary = {}
        for name, provider in self._providers.items():
            avail = provider.is_available()
            summary[name] = {
                "available": avail,
                "capabilities": [c.value for c in provider.capabilities()],
                "models": provider.list_models() if avail else [],
            }
        return summary
