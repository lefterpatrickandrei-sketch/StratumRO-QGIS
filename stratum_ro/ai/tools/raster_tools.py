# -*- coding: utf-8 -*-
"""
Raster & Orthophoto Tool Wrappers for StratumRO AI.
Integrates rasterio and OrthoExtractor for spatial analysis and chip extraction.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .security import resolve_sandboxed_path


def inspect_raster(raster_path: str) -> Dict[str, Any]:
    """
    Reads raster header, dimensions, resolution, and georeference info via rasterio.
    Validates that the file path is within authorized sandbox boundaries.
    """
    p = resolve_sandboxed_path(raster_path, must_exist=True)

    import rasterio

    with rasterio.open(str(p)) as src:
        bounds = src.bounds
        res = src.res
        crs_str = str(src.crs) if src.crs else "Unknown"

        return {
            "raster_path": str(p),
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
            "dtype": str(src.dtypes[0]) if src.dtypes else "unknown",
            "resolution": (round(res[0], 3), round(res[1], 3)),
            "crs": crs_str,
            "bounds": {
                "xmin": round(bounds.left, 2),
                "ymin": round(bounds.bottom, 2),
                "xmax": round(bounds.right, 2),
                "ymax": round(bounds.top, 2),
            },
            "nodata": src.nodata,
        }


def extract_ortho_chip(
    ortho_path: str,
    bbox: List[float],
    output_chip_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extracts an RGB orthophoto chip for a given bounding box [xmin, ymin, xmax, ymax].
    """
    p_src = resolve_sandboxed_path(ortho_path, must_exist=True)
    p_dst = resolve_sandboxed_path(output_chip_path) if output_chip_path else None

    import rasterio
    from rasterio.windows import from_bounds

    xmin, ymin, xmax, ymax = bbox
    with rasterio.open(str(p_src)) as src:
        window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
        transform = rasterio.windows.transform(window, src.transform)
        data = src.read(window=window)

        if p_dst:
            profile = src.profile.copy()
            profile.update({
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": transform
            })
            p_dst.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(str(p_dst), "w", **profile) as dst:
                dst.write(data)

        return {
            "ortho_path": str(p_src),
            "chip_path": str(p_dst) if p_dst else None,
            "chip_shape": list(data.shape),
            "bbox": [round(c, 2) for c in bbox],
            "status": "success"
        }
