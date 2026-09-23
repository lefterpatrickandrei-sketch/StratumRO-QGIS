# -*- coding: utf-8 -*-
"""
StratumRO Domain Layer.
Encapsulates domain-specific geospatial capabilities:
- cadastre_ro: Romanian cadastral workflows, TopoLT DXF, .CP files, PAD tables (ANCPI Ord. 600/2023)
- city_3d: 3D volumetric extrusion, LoD1 models, CityJSON v1.1, RANSAC roof planes
- lidar: Airborne point cloud processing, nDSM generation, height extraction, quality gates
- vision: Optical candidate generation, SAM2 ONNX DirectML inference, mask fusion
- topography: Surface elevation, slope, and terrain capabilities (PARTIAL)
"""

from . import cadastre_ro
from . import city_3d
from . import lidar
from . import vision
from . import topography

__all__ = ["cadastre_ro", "city_3d", "lidar", "vision", "topography"]
