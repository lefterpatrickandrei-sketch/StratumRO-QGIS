# -*- coding: utf-8 -*-
"""
StratumRO — Romanian Cadastral Domain Contracts (Phase 2)
Encapsulates all specifications under ANCPI Ordinul nr. 600/2023,
TopoLT CAD layer conventions, PAD coordinate tables, and .CP file formatting.
Isolated strictly from universal Core.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Protocol, Tuple, runtime_checkable
from shapely.geometry import Polygon


class TopoLTLayer(str, Enum):
    CONSTRUCTION_MAIN = "1CC"       # Main residential / commercial construction
    CONSTRUCTION_ANNEX = "2CC"      # Secondary annexes / sheds
    PROPERTY_BOUNDARY = "CP"        # Cadastral parcel limit
    VERTICES = "VARFURI"            # Point markers on polygon vertices
    POINT_NUMBERS = "NUMERE_PCT"    # Text labels with cadastral point IDs


@dataclass(frozen=True)
class CadastralPoint:
    """
    Cadastral point formatted strictly to Romanian geodetic conventions.
    X = Nord (Northing), Y = Est (Easting) in Stereo 70.
    """
    point_id: str
    x_nord: float
    y_est: float
    z_elevation: float = 0.0
    code: str = "PCT_CONTUR"
    description: str = ""

    def as_pad_row(self) -> Tuple[str, str, str]:
        """Returns row for PAD coordinate table: (Nr. Punct, X [Nord], Y [Est])."""
        return (self.point_id, f"{self.x_nord:.2f}", f"{self.y_est:.2f}")


@dataclass
class PADTableSpec:
    """
    Specification for Plan de Amplasament și Delimitare (PAD) coordinate table.
    """
    imobil_id: str
    points: List[CadastralPoint] = field(default_factory=list)
    computed_area_m2: float = 0.0
    measured_area_m2: float = 0.0
    parcel_category: str = "CC"     # Curți-Construcții
    destination: str = "Intravilan"

    @property
    def point_count(self) -> int:
        return len(self.points)


@dataclass
class CPInterchangeSpec:
    """
    Specification for ANCPI e-Terra .CP ASCII interchange file.
    """
    header_siruta: str
    imobil_identifier: str
    points: List[CadastralPoint]
    construction_points: List[CadastralPoint] = field(default_factory=list)
    area_cadastrala: float = 0.0


@runtime_checkable
class ICadastralExporter(Protocol):
    """
    Contract for exporting CAD and official cadastral interchange files.
    """
    def export_dxf(self, polygon: Polygon, output_path: str, is_annex: bool = False) -> str:
        """Exports DXF with TopoLT layers (1CC/2CC, CP, VARFURI, NUMERE_PCT)."""
        ...

    def export_cp(self, pad_spec: PADTableSpec, output_path: str) -> str:
        """Exports ANCPI standard .CP interchange text file."""
        ...
