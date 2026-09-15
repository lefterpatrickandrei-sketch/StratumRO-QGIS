# -*- coding: utf-8 -*-
"""
Raster & Orthophoto Tool Wrappers for StratumRO AI.
Integrates rasterio and OrthoExtractor for spatial analysis and chip extraction.
"""

import os
from typing import Any, Dict, List, Optional


def inspect_raster(raster_path: str) -> Dict[str, Any]:
    """
    Reads raster header, dimensions, resolution, and georeference info via rasterio.
    """
    if not os.path.isfile(raster_path):
        raise FileNotFoundError(f"Raster file not found: {raster_path}")

    import rasterio

    with rasterio.open(raster_path) as src:
        bounds = src.bounds
        res = src.res
        crs_str = str(src.crs) if src.crs else "Unknown"

        return {
            "raster_path": raster_path,
            "width": src.width,
            "height": src.height,
            "band_count": src.count,
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
    if not os.path.isfile(ortho_path):
        raise FileNotFoundError(f"Orthophoto file not found: {ortho_path}")

    import rasterio
    from rasterio.windows import from_bounds

    xmin, ymin, xmax, ymax = bbox
    with rasterio.open(ortho_path) as src:
        window = from_bounds(xmin, ymin, xmax, ymax, src.transform)
        transform = rasterio.windows.transform(window, src.transform)
        data = src.read(window=window)

        if output_chip_path:
            profile = src.profile.copy()
            profile.update({
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": transform
            })
            os.makedirs(os.path.dirname(output_chip_path), exist_ok=True)
            with rasterio.open(output_chip_path, "w", **profile) as dst:
                dst.write(data)

        return {
            "ortho_path": ortho_path,
            "chip_path": output_chip_path,
            "chip_shape": list(data.shape),
            "bbox": [round(c, 2) for c in bbox],
            "status": "success"
        }
