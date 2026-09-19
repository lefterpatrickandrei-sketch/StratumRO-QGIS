# -*- coding: utf-8 -*-
"""
Provider Registry for StratumRO AI.
Maintains a dynamic catalog of model providers and capability mappings,
supporting auto-discovery and health inspection.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from .providers.base import BaseAIProvider, ProviderCapability
from .providers.local_provider import LocalProvider
from .providers.nvidia_nim_provider import NvidiaNIMProvider
from .providers.openai_provider import OpenAIProvider
from .providers.ollama_provider import OllamaProvider
from .providers.union_alpha_provider import UnionAlphaProvider


@dataclass
class CapabilityMatch:
    """Resolved provider mapping for a specific capability requirement."""
    provider: BaseAIProvider
    capability: ProviderCapability
    is_fallback: bool
    rationale: str



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

        # 2. Union Alpha (256k large-context frontier reasoning via OpenRouter)
        self.register(UnionAlphaProvider())

        # 3. NVIDIA NIM (reads key from .env / env var)
        self.register(NvidiaNIMProvider())

        # 4. OpenAI Platform (reads key from env var)
        self.register(OpenAIProvider())

        # 5. Ollama (local daemon)
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

    def resolve_provider(
        self,
        required_capability: ProviderCapability,
        preferred_provider: Optional[str] = None,
        allow_fallback: bool = True,
    ) -> Optional[CapabilityMatch]:
        """
        Resolves the optimal provider for a requested capability, respecting
        preferred choice, live health/availability, and fallback hierarchy.
        """
        # 1. Check preferred provider first if specified
        if preferred_provider:
            p = self.get(preferred_provider)
            if p and p.is_available() and required_capability in p.capabilities():
                return CapabilityMatch(
                    provider=p,
                    capability=required_capability,
                    is_fallback=False,
                    rationale=f"Preferred provider '{preferred_provider}' is available and matched.",
                )

        # 2. Find all candidates offering capability
        candidates = self.find_by_capability(required_capability)
        if not candidates:
            # Fallback to local deterministic mock if permitted
            if allow_fallback:
                local_mock = self.get("local_mock")
                if local_mock:
                    return CapabilityMatch(
                        provider=local_mock,
                        capability=required_capability,
                        is_fallback=True,
                        rationale="All specialized providers unavailable; routed to air-gapped local mock.",
                    )
            return None

        # Return first available candidate
        matched = candidates[0]
        return CapabilityMatch(
            provider=matched,
            capability=required_capability,
            is_fallback=False,
            rationale=f"Resolved active candidate '{matched.name}' matching capability '{required_capability.value}'.",
        )

