# -*- coding: utf-8 -*-
"""
StratumRO — Domain Pack Architecture Contracts (Phase 2)
Defines the base abstraction for specialized domain plugins
(e.g., Romanian Cadastre, Topography, 3D City).
Zero dependency on QGIS or any specific UI.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from stratum_ro.contracts.geo import CommonGeoObject


class DomainMaturity(str, Enum):
    MATURE = "MATURE"              # Production code, real data, unit tests, validated use cases
    PARTIAL = "PARTIAL"            # Functional algorithms, limited benchmark coverage
    EXPERIMENTAL = "EXPERIMENTAL"  # Prototype / R&D stage
    FUTURE = "FUTURE"              # Roadmap concept, no code on disk


@dataclass(frozen=True)
class DomainCapability:
    """
    Formal declaration of a functional capability provided by a Domain Pack.
    """
    capability_name: str
    description: str
    input_types: List[str]
    output_types: List[str]
    is_deterministic: bool
    requires_ai_assistance: bool
    required_packages: List[str] = field(default_factory=list)


class BaseDomainPack(ABC):
    """
    Abstract Base Class for all StratumRO Domain Packs.
    A Domain Pack bundles domain-specific standards, layers, workflows,
    and validation rules without polluting the universal Core.
    """

    @property
    @abstractmethod
    def domain_id(self) -> str:
        """Unique identifier (e.g. 'cadastre_ro', 'topography', 'city_3d')."""
        ...

    @property
    @abstractmethod
    def domain_name(self) -> str:
        """Human-readable name."""
        ...

    @property
    @abstractmethod
    def maturity(self) -> DomainMaturity:
        """Declared maturity level."""
        ...

    @abstractmethod
    def list_capabilities(self) -> List[DomainCapability]:
        """Returns the list of capabilities exposed by this Domain Pack."""
        ...

    @abstractmethod
    def execute_capability(self, capability_name: str, inputs: Any, **params: Any) -> Any:
        """Executes a declared domain capability."""
        ...

    @abstractmethod
    def validate_deliverable(self, deliverable: Any) -> Dict[str, Any]:
        """Validates deliverable against domain-specific regulatory rules."""
        ...
