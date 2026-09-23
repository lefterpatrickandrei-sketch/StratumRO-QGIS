# -*- coding: utf-8 -*-
"""
StratumRO — Common Geospatial Object & Processing Contracts (Phase 2)
Universal data models and processor interfaces agnostic of any specific client or UI.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from enum import Enum


@dataclass
class Coordinate2D:
    x: float
    y: float

    def as_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Coordinate3D:
    x: float
    y: float
    z: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)


@dataclass
class BoundingBox:
    min_x: float
    min_y: float
    max_x: float
    max_y: float
    min_z: Optional[float] = None
    max_z: Optional[float] = None

    def as_bounds(self) -> tuple[float, float, float, float]:
        return (self.min_x, self.min_y, self.max_x, self.max_y)


@dataclass
class CommonGeoObject:
    """
    Universal geospatial entity contract.
    Decouples raw vector/raster representation from specific GIS formats.
    """
    id: str
    geometry: Any  # GeoJSON-compatible dict or Shapely geometry object
    crs: str  # EPSG code string, e.g. "EPSG:3844"
    attributes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    provenance_id: Optional[str] = None

    @property
    def is_3d(self) -> bool:
        if hasattr(self.geometry, "has_z"):
            return bool(self.geometry.has_z)
        return False


@runtime_checkable
class IGeoProcessor(Protocol):
    """
    Abstract contract for any deterministic geospatial processor.
    """
    @property
    def processor_id(self) -> str:
        ...

    @property
    def supported_crs(self) -> List[str]:
        ...

    def process(self, geo_object: CommonGeoObject, **params: Any) -> CommonGeoObject:
        """
        Executes deterministic geospatial processing on a CommonGeoObject.
        """
        ...
