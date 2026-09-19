# -*- coding: utf-8 -*-
"""
StratumRO — Task Specification Module (Phase 4 Foundation).
Formalizes the inputs, geospatial constraints, required capabilities, deliverables,
and risk tolerance for any execution workflow within the StratumRO platform.
Enforces ANCPI Ordinul nr. 600/2023 compliance and Stereo 70 (EPSG:3844) CRS integrity.
"""

import json
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class RiskTolerance(str, Enum):
    LOW = "LOW"        # Strict validation gates, all mutations require explicit human review
    MEDIUM = "MEDIUM"  # Automatic preview generation, human gate on official cadastral export
    HIGH = "HIGH"      # Fully automated batch processing / experimental simulation


class DeliverableType(str, Enum):
    DXF = "dxf"                # TopoLT CAD layer format (1CC, 2CC, CP, VARFURI)
    CP = "cp"                  # ANCPI e-Terra ASCII coordinate exchange format
    PAD_TABLE = "pad_table"    # Official PAD coordinate table with Stereo 70 X, Y
    GPKG = "gpkg"              # OGC GeoPackage vector layer (2D or MultiPolygonZ)
    CITYJSON = "cityjson"      # OGC CityJSON v1.1 LoD1 3D building models
    GEOJSON = "geojson"        # Standard GeoJSON vector footprints
    REPORT = "report"          # Markdown / JSON geodetic evaluation dossier


@dataclass
class TaskSpec:
    """
    Authoritative specification for an executable StratumRO workflow task.
    Decouples task declaration from the execution engine and provider selection.
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Cadastral Workflow Task"
    description: str = ""
    target_crs: str = "EPSG:3844"
    aoi_bounds: Optional[Tuple[float, float, float, float]] = None  # (minx, miny, maxx, maxy) in Stereo 70
    required_capabilities: List[str] = field(default_factory=list)
    inputs: Dict[str, str] = field(default_factory=dict)  # e.g., {"ortho": "path/to/ortho.tif", "lidar": "path/to/pts.laz"}
    deliverables: List[str] = field(default_factory=lambda: [DeliverableType.GPKG.value, DeliverableType.DXF.value])
    risk_tolerance: str = RiskTolerance.LOW.value
    parameters: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def validate(self, check_file_existence: bool = False) -> Tuple[bool, List[str]]:
        """
        Validates the TaskSpec for geodetic and structural integrity.
        
        Args:
            check_file_existence: If True, checks whether paths in `inputs` exist on disk.
            
        Returns:
            Tuple of (is_valid: bool, error_messages: List[str])
        """
        errors: List[str] = []

        # 1. CRS Enforcement — Must be Stereo 70 (EPSG:3844)
        normalized_crs = self.target_crs.strip().upper()
        if normalized_crs not in ("EPSG:3844", "3844", "PROJCS[\"PULKOVO 1942(58) / STEREO70\",GEOGCS[\"PULKOVO 1942(58)\",DATUM[\"PULKOVO_1942_58\",SPHEROID[\"KRASSOWSKY 1940\",6378245,298.3,AUTHORITY[\"EPSG\",\"7024\"]],AUTHORITY[\"EPSG\",\"6179\"]],PRIMEM[\"GREENWICH\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"DEGREE\",0.0174532925199433,AUTHORITY[\"EPSG\",\"9122\"]],AUTHORITY[\"EPSG\",\"4179\"]],PROJECTION[\"OBLIQUE_STEREOGRAPHIC\"],PARAMETER[\"LATITUDE_OF_ORIGIN\",46],PARAMETER[\"CENTRAL_MERIDIAN\",25],PARAMETER[\"SCALE_FACTOR\",0.99975],PARAMETER[\"FALSE_EASTING\",500000],PARAMETER[\"FALSE_NORTHING\",500000],UNIT[\"METRE\",1,AUTHORITY[\"EPSG\",\"9001\"]],AXIS[\"NORTHING\",NORTH],AXIS[\"EASTING\",EAST],AUTHORITY[\"EPSG\",\"3844\"]]"):
            if not normalized_crs.endswith("3844"):
                errors.append(f"Invalid target CRS: '{self.target_crs}'. StratumRO strictly requires Stereo 70 (EPSG:3844).")

        # 2. AOI Bounding Box Validation
        if self.aoi_bounds is not None:
            if not isinstance(self.aoi_bounds, (tuple, list)) or len(self.aoi_bounds) != 4:
                errors.append(f"aoi_bounds must be a 4-element tuple (minx, miny, maxx, maxy), got {type(self.aoi_bounds)}.")
            else:
                minx, miny, maxx, maxy = self.aoi_bounds
                if minx >= maxx or miny >= maxy:
                    errors.append(f"Invalid bounding box: min coordinates ({minx}, {miny}) must be strictly less than max ({maxx}, {maxy}).")
                # Plausibility check for Romania Stereo 70 bounding envelope:
                # Easting: ~200,000 to ~850,000 | Northing: ~200,000 to ~750,000
                if not (150000 <= minx <= 900000 and 150000 <= miny <= 800000):
                    errors.append(f"Bounding box coordinates ({minx}, {miny}) fall outside Romania Stereo 70 valid geographic domain.")

        # 3. Risk Tolerance Validation
        valid_risks = {r.value for r in RiskTolerance}
        if self.risk_tolerance.upper() not in valid_risks:
            errors.append(f"Invalid risk_tolerance '{self.risk_tolerance}'. Must be one of {valid_risks}.")

        # 4. Optional Input File Existence Check
        if check_file_existence:
            for key, path_str in self.inputs.items():
                p = Path(path_str)
                if not p.exists():
                    errors.append(f"Input '{key}' specifies non-existent path: {path_str}")

        return (len(errors) == 0, errors)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes TaskSpec to a standard Python dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskSpec":
        """Instantiates a TaskSpec from a dictionary, tolerating extra keys."""
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        # Ensure aoi_bounds is tuple if list
        if "aoi_bounds" in filtered and filtered["aoi_bounds"] is not None:
            filtered["aoi_bounds"] = tuple(filtered["aoi_bounds"])
        return cls(**filtered)

    def to_json(self, indent: int = 2) -> str:
        """Serializes TaskSpec to a formatted JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> "TaskSpec":
        """Instantiates a TaskSpec from a JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
