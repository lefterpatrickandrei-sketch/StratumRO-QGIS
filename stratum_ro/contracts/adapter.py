# -*- coding: utf-8 -*-
"""
StratumRO — Client & Legacy Adapter Contracts (Phase 2)
Defines decoupling boundaries between UI/Clients (QGIS, Web, CLI)
and the universal Core/Domain services.
"""

from typing import Any, Dict, List, Protocol, runtime_checkable
from stratum_ro.contracts.geo import CommonGeoObject


@runtime_checkable
class IQgisAdapter(Protocol):
    """
    Contract for QGIS client adapters.
    Ensures QGIS desktop widgets consume Core services through a thin bridge.
    Core NEVER imports QGIS or PyQt directly.
    """
    @property
    def is_qgis_active(self) -> bool:
        """Returns True if running inside an active QGIS application session."""
        ...

    def get_active_layer_features(self) -> List[CommonGeoObject]:
        """Translates current active QGIS layer features into CommonGeoObjects."""
        ...

    def add_features_to_canvas(self, features: List[CommonGeoObject], layer_name: str) -> bool:
        """Renders CommonGeoObjects back onto the active QGIS map canvas."""
        ...


@runtime_checkable
class ILegacyAdapter(Protocol):
    """
    Contract for backward compatibility bridges during architectural migration.
    Ensures existing user scripts and legacy import paths continue to function.
    """
    def forward_call(self, function_name: str, *args: Any, **kwargs: Any) -> Any:
        """Forwards legacy API invocations to the corresponding new Core/Domain engine."""
        ...
