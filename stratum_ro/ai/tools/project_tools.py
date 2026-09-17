# -*- coding: utf-8 -*-
"""
Project & Workspace Context Tool Wrappers for StratumRO AI.
Inspects active workspace files, CRS parameters, and GPU hardware.
"""

import os
from pathlib import Path
from typing import Any, Dict


import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .security import resolve_sandboxed_path


def get_workspace_context(base_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns environment metadata: CRS (EPSG:3844), vertical datum, directory status,
    and detected hardware acceleration without exposing secrets or raw environment variables.
    """
    p_base = resolve_sandboxed_path(base_dir) if base_dir else resolve_sandboxed_path(".")

    # Hardware detection (safe)
    gpu_available = False
    device_name = "CPU"
    try:
        import torch
        if torch.cuda.is_available():
            gpu_available = True
            device_name = torch.cuda.get_device_name(0)
    except Exception:
        pass

    # Inspect key directories
    ws_output = p_base / "workspace" / "output"
    gt_dir = p_base / "data" / "ground_truth"
    data_dir = p_base / "data"

    available_rasters = []
    if data_dir.exists():
        available_rasters = [
            str(p.relative_to(p_base))
            for p in data_dir.glob("**/*.tif")
        ][:5]

    available_lidar = []
    if data_dir.exists():
        available_lidar = [
            str(p.relative_to(p_base))
            for p in list(data_dir.glob("**/*.laz")) + list(data_dir.glob("**/*.las"))
        ][:5]

    return {
        "base_directory": str(p_base),
        "crs": "EPSG:3844",
        "vertical_datum": "EPSG:5781",
        "crs_description": "Stereo 70 (EPSG:3844)",
        "vertical_datum_description": "Marea Neagră 1975 (EPSG:5781)",
        "hardware": {
            "gpu_available": gpu_available,
            "device": device_name,
            "os": os.name
        },
        "directories": {
            "workspace_output_exists": ws_output.exists(),
            "ground_truth_exists": gt_dir.exists(),
        },
        "available_sources": {
            "sample_rasters": available_rasters,
            "sample_lidar": available_lidar,
        },
        "status": "ready"
    }


def get_aoi(layer_path: Optional[str] = None, format: str = "wkt") -> Dict[str, Any]:
    """
    Retrieves the active Area of Interest (AOI) extent or polygon in Stereo 70 (EPSG:3844).
    If layer_path is provided, derives bounds from the specified vector layer.
    """
    if layer_path:
        p = resolve_sandboxed_path(layer_path, must_exist=True)
        import geopandas as gpd
        gdf = gpd.read_file(p)
        bounds = gdf.total_bounds  # [minx, miny, maxx, maxy]
        crs_str = str(gdf.crs) if gdf.crs else "EPSG:3844"
    else:
        # Default active test sector: USAMV Cluj-Napoca (Stereo 70)
        bounds = [391500.0, 584500.0, 392500.0, 585500.0]
        crs_str = "EPSG:3844"

    minx, miny, maxx, maxy = bounds
    wkt_box = f"POLYGON(({minx} {miny}, {maxx} {miny}, {maxx} {maxy}, {minx} {maxy}, {minx} {miny}))"

    return {
        "status": "success",
        "crs": crs_str,
        "bbox": [round(float(c), 3) for c in bounds],
        "format": format,
        "aoi": wkt_box if format.lower() == "wkt" else {
            "minx": minx, "miny": miny, "maxx": maxx, "maxy": maxy
        }
    }


def list_layers(subpath: str = "") -> Dict[str, Any]:
    """
    Lists available vector, raster, and point cloud layers within the workspace/data sandbox.
    """
    base = resolve_sandboxed_path(subpath)
    layers = []

    valid_exts = {".geojson", ".gpkg", ".shp", ".tif", ".laz", ".las", ".dxf"}

    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in valid_exts:
            # Skip hidden git or temporary files
            if any(part.startswith(".") for part in p.parts):
                continue
            layers.append({
                "name": p.name,
                "relative_path": str(p.relative_to(resolve_sandboxed_path("."))),
                "size_kb": round(p.stat().st_size / 1024.0, 1),
                "type": p.suffix.lower().replace(".", "")
            })

    return {
        "status": "success",
        "layer_count": len(layers),
        "layers": layers
    }


def inspect_layer(layer_path: str) -> Dict[str, Any]:
    """
    Returns the schema, feature count, geometry type, CRS, and bounds for a vector or raster layer.
    """
    p = resolve_sandboxed_path(layer_path, must_exist=True)
    suffix = p.suffix.lower()

    if suffix in {".tif", ".tiff"}:
        from .raster_tools import inspect_raster
        return inspect_raster(str(p))

    if suffix in {".laz", ".las"}:
        from .lidar_tools import inspect_lidar
        return inspect_lidar(str(p))

    # Vector layer via geopandas
    import geopandas as gpd
    gdf = gpd.read_file(p)
    b = gdf.total_bounds if len(gdf) > 0 else [0, 0, 0, 0]

    return {
        "status": "success",
        "layer_path": str(p),
        "feature_count": len(gdf),
        "geometry_type": str(gdf.geometry.geom_type.iloc[0]) if len(gdf) > 0 else "None",
        "crs": str(gdf.crs) if gdf.crs else "EPSG:3844",
        "columns": [c for c in gdf.columns if c != "geometry"],
        "bounds": {
            "minx": round(float(b[0]), 3),
            "miny": round(float(b[1]), 3),
            "maxx": round(float(b[2]), 3),
            "maxy": round(float(b[3]), 3)
        }
    }
