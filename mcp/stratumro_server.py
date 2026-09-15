# -*- coding: utf-8 -*-
"""
StratumRO FastMCP Server.
Exposes StratumRO deterministic geospatial engines to Antigravity agents
via the Model Context Protocol (MCP).
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

# Ensure repository root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from stratum_ro.ai.tools.project_tools import get_workspace_context
from stratum_ro.ai.tools.lidar_tools import inspect_lidar
from stratum_ro.ai.tools.raster_tools import inspect_raster
from stratum_ro.ai.tools.vector_tools import regularize_footprints, apply_eave_offset
from stratum_ro.ai.tools.cadastral_tools import validate_topology, export_topolt_cad, export_cp_file

mcp = FastMCP("StratumRO")


@mcp.tool()
def get_context() -> Dict[str, Any]:
    """Inspects active StratumRO workspace metadata, CRS (EPSG:3844), and hardware status."""
    return get_workspace_context(base_dir=str(root_dir))


@mcp.tool()
def inspect_lidar_file(laz_path: str) -> Dict[str, Any]:
    """Reads point count, bounds, and density of a LiDAR (.laz/.las) point cloud."""
    return inspect_lidar(laz_path)


@mcp.tool()
def inspect_raster_file(raster_path: str) -> Dict[str, Any]:
    """Reads dimensions, bands, resolution, and georeference of an orthophoto or DTM."""
    return inspect_raster(raster_path)


@mcp.tool()
def check_topology(polygons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validates topological soundness of building footprints (self-intersections, slivers)."""
    return validate_topology(polygons)


@mcp.tool()
def regularize_geometry(polygons: List[Dict[str, Any]], mrr_trigger: float = 0.70) -> Dict[str, Any]:
    """Applies 90-degree orthogonal regularization (canonical rectangle or adaptive)."""
    return regularize_footprints(polygons, mrr_trigger=mrr_trigger)


@mcp.tool()
def apply_eave_offset_m(polygons: List[Dict[str, Any]], offset_m: float = -0.40) -> Dict[str, Any]:
    """Applies eave retraction offset (-0.40m) to generate ANCPI ground footprints."""
    return apply_eave_offset(polygons, offset_m=offset_m)


@mcp.tool()
def export_dxf(output_path: str, buildings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Exports buildings to TopoLT-standard AutoCAD DXF with PAD coordinate tables."""
    return export_topolt_cad(output_path, buildings=buildings)


@mcp.tool()
def export_cp(output_path: str, parcel_id: str, points: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Exports .CP coordinate interchange file conforming to ANCPI eTerra."""
    return export_cp_file(output_path, parcel_id=parcel_id, points=points)


if __name__ == "__main__":
    mcp.run()
