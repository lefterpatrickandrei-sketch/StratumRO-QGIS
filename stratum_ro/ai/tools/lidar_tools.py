# -*- coding: utf-8 -*-
"""
LiDAR Tool Wrappers for StratumRO AI.
Integrates LidarProcessor and laspy into deterministic tool interfaces.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .security import resolve_sandboxed_path


def inspect_lidar(laz_path: str) -> Dict[str, Any]:
    """
    Reads LiDAR point cloud metadata without loading all points into memory.
    Validates that the file path is within authorized sandbox boundaries.
    """
    p = resolve_sandboxed_path(laz_path, must_exist=True)

    import laspy
    with laspy.open(str(p)) as reader:
        header = reader.header
        count = header.point_count
        mins = header.mins
        maxs = header.maxs
        area_approx = (maxs[0] - mins[0]) * (maxs[1] - mins[1])
        density = round(count / area_approx, 2) if area_approx > 0 else 0.0

        return {
            "laz_path": str(p),
            "point_count": count,
            "bounds": {
                "xmin": round(mins[0], 2),
                "ymin": round(mins[1], 2),
                "zmin": round(mins[2], 2),
                "xmax": round(maxs[0], 2),
                "ymax": round(maxs[1], 2),
                "zmax": round(maxs[2], 2),
            },
            "density_pts_m2": density,
            "crs_projected": "EPSG:3844 (Stereo 70 assumed)"
        }


def generate_ndsm(
    laz_path: str,
    dtm_path: str,
    output_ndsm_path: Optional[str] = None,
    resolution_m: float = 1.0
) -> Dict[str, Any]:
    """
    Generates a normalized Digital Surface Model (nDSM) and extracts multi-category candidates.
    """
    p_laz = resolve_sandboxed_path(laz_path, must_exist=True)
    p_dtm = resolve_sandboxed_path(dtm_path, must_exist=True)
    p_out = resolve_sandboxed_path(output_ndsm_path) if output_ndsm_path else None

    from stratum_ro.lidar_processor import LidarProcessor
    from scipy.ndimage import label

    proc = LidarProcessor(str(p_laz), str(p_dtm))
    lidar_data = proc.process_multicategory(
        output_ndsm_path=str(p_out) if p_out else None,
        resolution=resolution_m
    )

    _, num_main = label(lidar_data["main_buildings_grid"])
    _, num_outb = label(lidar_data["outbuildings_grid"])

    return {
        "output_ndsm_path": output_ndsm_path,
        "main_building_candidates": int(num_main),
        "outbuilding_candidates": int(num_outb),
        "trees_detected": len(lidar_data.get("tree_points", [])),
        "poles_detected": len(lidar_data.get("pole_points", [])),
        "resolution_m": resolution_m,
        "status": "success"
    }
