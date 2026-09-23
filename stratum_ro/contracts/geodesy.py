# -*- coding: utf-8 -*-
"""
StratumRO — Geodetic & Coordinate Reference System Contracts (Phase 2)
Strict geodetic interfaces enforcing deterministic coordinate computation.
Zero LLM authority over coordinate calculations.
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Protocol, Tuple, runtime_checkable, Any


class AxisOrder(str, Enum):
    EASTING_NORTHING = "Easting_Northing"   # Standard Cartesian GIS / PROJ convention: (E, N)
    NORTHING_EASTING = "Northing_Easting"   # Romanian Cadastral ANCPI convention: (X=Nord, Y=Est)


@dataclass(frozen=True)
class CRSMetadata:
    """
    Formal metadata specification for any Coordinate Reference System.
    """
    crs_id: str                      # e.g., "EPSG:3844"
    epsg_code: int                   # e.g., 3844
    name: str                        # e.g., "Pulkovo 1942(58) / Stereo 70"
    datum: str                       # e.g., "Dealul Piscului 1970"
    ellipsoid: str                   # e.g., "Krasovsky 1940"
    projection: str                  # e.g., "Stereographic 1970"
    units: str                       # e.g., "metre"
    axis_order: AxisOrder            # Standard PROJ vs ANCPI CAD convention


@runtime_checkable
class ICRSManager(Protocol):
    """
    Contract for managing and validating coordinate reference systems.
    """
    def get_metadata(self, crs_id: str) -> CRSMetadata:
        """Retrieves authoritative geodetic metadata for a CRS."""
        ...

    def validate_crs(self, crs_id: str) -> bool:
        """Validates if a CRS is recognized and supported by the platform."""
        ...


@runtime_checkable
class ITransformer(Protocol):
    """
    Contract for deterministic coordinate transformations.
    MUST delegate exclusively to proven geodetic engines (PROJ/pyproj/TransdatRO).
    LLMs are strictly forbidden from performing numerical transformations.
    """
    @property
    def source_crs(self) -> str:
        ...

    @property
    def target_crs(self) -> str:
        ...

    def transform_point(self, x: float, y: float, z: float = 0.0) -> Tuple[float, float, float]:
        """Transforms a single 3D point between source and target CRS."""
        ...

    def transform_coordinates(self, coordinates: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Transforms a sequence of 2D coordinates."""
        ...
