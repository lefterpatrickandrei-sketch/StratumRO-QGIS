# -*- coding: utf-8 -*-
"""
3D Volumetric Extrusion (LoD1) & Roof Geometry Reconstruction (LoD2) for StratumRO.

LEGACY COMPATIBILITY FORWARDER
==============================
Canonical implementation has moved to:
    stratum_ro.domain.city_3d.builder (Volumetric3DBuilder)

This module is retained strictly for backward compatibility with existing QGIS
plugins, legacy tools, and automated tests. All symbols are forwarded directly
from the canonical domain implementation without duplication of algorithmic logic.
"""

from stratum_ro.domain.city_3d.builder import (
    Volumetric3DBuilder,
    _extract_polygons,
)

__all__ = [
    "Volumetric3DBuilder",
    "_extract_polygons",
]
