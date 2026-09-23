# -*- coding: utf-8 -*-
"""
StratumRO — Core Point Cloud: Generic LAS/LAZ Reader & Filtering (Phase 3)
Pure-Python point cloud utilities wrapping laspy.
Agnostic of cadastral interpretations. Zero QGIS dependencies.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Dict, List, Any
import numpy as np
import laspy


@dataclass(frozen=True)
class PointCloudMetadata:
    """Standard metadata container for airborne/terrestrial LiDAR point clouds."""
    point_count: int
    crs: str
    bounds: Tuple[float, float, float, float]  # min_x, min_y, max_x, max_y
    min_z: float
    max_z: float
    scale: Tuple[float, float, float]
    offset: Tuple[float, float, float]
    point_format: int


class CorePointCloudReader:
    """
    Generic point cloud processor providing spatial windowing and class filtering.
    """

    def get_metadata(self, las_path: str) -> PointCloudMetadata:
        """Reads LAS/LAZ header without loading full point cloud into RAM."""
        with laspy.open(las_path) as reader:
            hdr = reader.header
            crs_str = "EPSG:3844"  # Default fallback
            try:
                if hdr.parse_crs():
                    crs_str = str(hdr.parse_crs().to_string())
            except Exception:
                pass

            return PointCloudMetadata(
                point_count=hdr.point_count,
                crs=crs_str,
                bounds=(hdr.min[0], hdr.min[1], hdr.max[0], hdr.max[1]),
                min_z=float(hdr.min[2]),
                max_z=float(hdr.max[2]),
                scale=(float(hdr.scales[0]), float(hdr.scales[1]), float(hdr.scales[2])),
                offset=(float(hdr.offsets[0]), float(hdr.offsets[1]), float(hdr.offsets[2])),
                point_format=int(hdr.point_format.id)
            )

    def read_points(
        self,
        las_path: str,
        bounds: Optional[Tuple[float, float, float, float]] = None
    ) -> Dict[str, np.ndarray]:
        """
        Reads point attributes with optional 2D bounding box clipping.
        Returns dict with numpy arrays for 'x', 'y', 'z', 'classification', 'intensity'.
        """
        las = laspy.read(las_path)
        x = np.asarray(las.x)
        y = np.asarray(las.y)
        z = np.asarray(las.z)
        cls = np.asarray(las.classification) if hasattr(las, "classification") else np.zeros_like(x, dtype=np.uint8)
        intensity = np.asarray(las.intensity) if hasattr(las, "intensity") else np.zeros_like(x, dtype=np.uint16)

        if bounds is not None:
            min_x, min_y, max_x, max_y = bounds
            mask = (x >= min_x) & (x <= max_x) & (y >= min_y) & (y <= max_y)
            return {
                "x": x[mask],
                "y": y[mask],
                "z": z[mask],
                "classification": cls[mask],
                "intensity": intensity[mask]
            }

        return {
            "x": x,
            "y": y,
            "z": z,
            "classification": cls,
            "intensity": intensity
        }

    def filter_by_classification(
        self,
        points: Dict[str, np.ndarray],
        target_classes: List[int]
    ) -> Dict[str, np.ndarray]:
        """
        Filters points array by ASPRS classification codes (e.g. 2=Ground, 6=Building).
        """
        cls_arr = points.get("classification")
        if cls_arr is None:
            return points
        
        mask = np.isin(cls_arr, target_classes)
        return {k: v[mask] for k, v in points.items()}
