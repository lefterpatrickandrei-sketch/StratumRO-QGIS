# -*- coding: utf-8 -*-
"""
StratumRO FastMCP Server (MD 3).
Exposes StratumRO deterministic geospatial engines to Antigravity agents
via the Model Context Protocol (MCP), enforcing sandboxed filesystem access,
strict permission classes (ALLOW / SAFE_WRITE / ASK / DENY), and CRS integrity.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastmcp import FastMCP

# Ensure repository root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from stratum_ro.ai.tools.project_tools import (
    get_workspace_context,
    get_aoi,
    list_layers,
    inspect_layer,
)
from stratum_ro.ai.tools.lidar_tools import inspect_lidar, generate_ndsm
from stratum_ro.ai.tools.raster_tools import inspect_raster, extract_ortho_chip
from stratum_ro.ai.tools.segmentation_tools import run_sam2_segmentation, inspect_mask
from stratum_ro.ai.tools.vector_tools import (
    regularize_footprints,
    apply_eave_offset,
    create_planar_partition,
    export_gpkg_layer,
    export_cityjson_lod1,
)
from stratum_ro.ai.tools.cadastral_tools import (
    validate_topology,
    validate_ancpi,
    create_preview,
    commit_to_project,
    export_topolt_cad,
    export_cp_file,
)
from stratum_ro.ai.tools.evaluation_tools import compare_ground_truth
from stratum_ro.ai.context import get_context_snapshot, get_default_context_engine
from stratum_ro.ai.memory.session import SessionMemory

mcp = FastMCP("StratumRO")


# =============================================================================
# 1. Project & QGIS Context Tools (Section 8) — ALLOW
# =============================================================================

@mcp.tool(name="project.get_context")
def tool_get_context() -> Dict[str, Any]:
    """Inspects active StratumRO workspace metadata, CRS (EPSG:3844), vertical datum, and hardware status."""
    return get_workspace_context(base_dir=str(root_dir))


@mcp.tool(name="project.get_aoi")
def tool_get_aoi(layer_path: Optional[str] = None, format: str = "wkt") -> Dict[str, Any]:
    """Retrieves current map canvas extent or selected polygon in Stereo 70 (EPSG:3844)."""
    return get_aoi(layer_path=layer_path, format=format)


@mcp.tool(name="layers.list")
def tool_list_layers(subpath: str = "") -> Dict[str, Any]:
    """Lists available vector, raster, and LiDAR layers in the active workspace."""
    return list_layers(subpath=subpath)


@mcp.tool(name="layers.inspect")
def tool_inspect_layer(layer_path: str) -> Dict[str, Any]:
    """Returns attribute schema, feature count, CRS, geometry type, and bounds of a layer."""
    return inspect_layer(layer_path=layer_path)


# =============================================================================
# 2. Raster & LiDAR Tools (Sections 10 & 11) — ALLOW & SAFE_WRITE
# =============================================================================

@mcp.tool(name="raster.inspect")
def tool_inspect_raster(raster_path: str) -> Dict[str, Any]:
    """Reads header, dimensions, resolution, bands, dtype, and georeference of an orthophoto or DTM."""
    return inspect_raster(raster_path=raster_path)


@mcp.tool(name="raster.extract_chip")
def tool_extract_ortho_chip(
    ortho_path: str,
    bbox: List[float],
    output_chip_path: Optional[str] = None
) -> Dict[str, Any]:
    """Extracts an RGB orthophoto chip for a given bounding box [xmin, ymin, xmax, ymax]."""
    return extract_ortho_chip(ortho_path=ortho_path, bbox=bbox, output_chip_path=output_chip_path)


@mcp.tool(name="lidar.inspect")
def tool_inspect_lidar(laz_path: str) -> Dict[str, Any]:
    """Reads point count, bounds, and density of a LiDAR (.laz/.las) point cloud without loading full data."""
    return inspect_lidar(laz_path=laz_path)


@mcp.tool(name="lidar.generate_ndsm")
def tool_generate_ndsm(
    laz_path: str,
    dtm_path: str,
    output_ndsm_path: Optional[str] = None,
    resolution_m: float = 1.0
) -> Dict[str, Any]:
    """Derives normalized Digital Surface Model (nDSM) and candidate grids via LidarProcessor."""
    return generate_ndsm(
        laz_path=laz_path,
        dtm_path=dtm_path,
        output_ndsm_path=output_ndsm_path,
        resolution_m=resolution_m
    )


# =============================================================================
# 3. Segmentation Tools (Sections 12 & 13) — ALLOW & SAFE_WRITE
# =============================================================================

@mcp.tool(name="segmentation.run_sam2")
def tool_run_sam2(
    ortho_chip_path: str,
    candidate_prompts: List[Dict[str, Any]],
    checkpoint_path: Optional[str] = None,
    device: str = "auto",
    aoi_bbox: Optional[List[float]] = None
) -> Dict[str, Any]:
    """Executes Meta SAM2 inference on orthophoto chips using LiDAR centroid/box prompts."""
    return run_sam2_segmentation(
        ortho_chip_path=ortho_chip_path,
        candidate_prompts=candidate_prompts,
        checkpoint_path=checkpoint_path,
        device=device,
        aoi_bbox=aoi_bbox
    )


@mcp.tool(name="segmentation.inspect_mask")
def tool_inspect_mask(mask_geometry: Dict[str, Any]) -> Dict[str, Any]:
    """Calculates mask area, perimeter, edge compactness, and bounding box."""
    return inspect_mask(mask_geometry=mask_geometry)


# =============================================================================
# 4. Vector Regularization & Partitioning (Section 14) — SAFE_WRITE
# =============================================================================

@mcp.tool(name="vector.regularize")
def tool_regularize(
    polygons: List[Dict[str, Any]],
    tolerance: float = 0.5,
    mrr_trigger: float = 0.70
) -> Dict[str, Any]:
    """Applies 90° orthogonal regularization: canonical 4-vertex rectangle fitting or adaptive regularization."""
    return regularize_footprints(polygons=polygons, tolerance=tolerance, mrr_trigger=mrr_trigger)


@mcp.tool(name="vector.apply_eave_offset")
def tool_apply_eave_offset(
    polygons: List[Dict[str, Any]],
    offset_m: float = -0.40
) -> Dict[str, Any]:
    """Applies eave retraction offset (default -0.40m) to generate ANCPI ground footprints."""
    return apply_eave_offset(polygons=polygons, offset_m=offset_m)


@mcp.tool(name="vector.planar_partition")
def tool_planar_partition(
    buildings: List[Dict[str, Any]],
    sector_boundary: Dict[str, Any],
    simplification_m: float = 12.0
) -> Dict[str, Any]:
    """Eliminates overlaps and computes continuous 100% planar partition for parcel sector."""
    return create_planar_partition(
        buildings=buildings,
        sector_boundary=sector_boundary,
        simplification_m=simplification_m
    )


# =============================================================================
# 5. Geodetic & Cadastral Validation (Sections 15, 16, 17) — ALLOW
# =============================================================================

@mcp.tool(name="geometry.validate_topology")
def tool_validate_topology(polygons: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Checks self-intersections, duplicate vertices, invalid rings, and sliver gaps."""
    return validate_topology(polygons=polygons)


@mcp.tool(name="cadastral.validate_ancpi")
def tool_validate_ancpi(
    polygons: List[Dict[str, Any]],
    layer_path: Optional[str] = None
) -> Dict[str, Any]:
    """Validates building footprints against ANCPI Ordinul nr. 600/2023 criteria."""
    return validate_ancpi(polygons=polygons, layer_path=layer_path)


@mcp.tool(name="evaluation.compare_ground_truth")
def tool_compare_ground_truth(
    pred_path: str,
    gt_path: str = "data/ground_truth/tier1_teren.geojson",
    output_report_path: Optional[str] = None
) -> Dict[str, Any]:
    """Computes IoU, 95% Hausdorff Distance, Boundary RMSE, and Wilson score CI against reference data."""
    return compare_ground_truth(
        pred_path=pred_path,
        gt_path=gt_path,
        output_report_path=output_report_path
    )


# =============================================================================
# 6. Preview, Approval & Export Tools (Sections 18, 19, 20)
# =============================================================================

@mcp.tool(name="results.create_preview")
def tool_create_preview(
    polygons: List[Dict[str, Any]],
    title: str = "preview_candidates"
) -> Dict[str, Any]:
    """Writes temporary preview footprints to workspace/output/preview/ for visual surveyor inspection."""
    return create_preview(polygons=polygons, title=title)


@mcp.tool(name="results.commit_to_project")
def tool_commit_to_project(
    preview_path: str,
    target_layer_path: str = "workspace/output/official_buildings.gpkg",
    approved: bool = False,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """Commits user-approved preview footprints to official project layer (Permission: ASK)."""
    return commit_to_project(
        preview_path=preview_path,
        target_layer_path=target_layer_path,
        approved=approved,
        approval_reason=approval_reason
    )


@mcp.tool(name="export.export_gpkg")
def tool_export_gpkg(
    output_gpkg_path: str,
    polygons: List[Dict[str, Any]],
    layer_name: str = "CLADIRI_SOL_ANCPI",
    crs: str = "EPSG:3844"
) -> Dict[str, Any]:
    """Exports buildings to official OGC GeoPackage in Stereo 70 (EPSG:3844)."""
    return export_gpkg_layer(
        output_gpkg_path=output_gpkg_path,
        polygons=polygons,
        layer_name=layer_name,
        crs=crs
    )


@mcp.tool(name="export.export_topolt_dxf")
def tool_export_topolt_dxf(
    output_dxf_path: str,
    buildings: List[Dict[str, Any]],
    parcels: Optional[List[Dict[str, Any]]] = None,
    approved: bool = False,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """Exports buildings and parcels to TopoLT-standard AutoCAD DXF with PAD coordinate tables (Permission: ASK)."""
    return export_topolt_cad(
        output_dxf_path=output_dxf_path,
        buildings=buildings,
        parcels=parcels,
        approved=approved,
        approval_reason=approval_reason
    )


@mcp.tool(name="export.export_cp")
def tool_export_cp(
    output_cp_path: str,
    parcel_id: str,
    points: List[Dict[str, Any]],
    approved: bool = False,
    approval_reason: str = ""
) -> Dict[str, Any]:
    """Exports .CP coordinate interchange file conforming to ANCPI eTerra (Permission: ASK)."""
    return export_cp_file(
        output_cp_path=output_cp_path,
        parcel_id=parcel_id,
        points=points,
        approved=approved,
        approval_reason=approval_reason
    )


@mcp.tool(name="export.export_cityjson")
def tool_export_cityjson(
    output_cityjson_path: str,
    buildings: List[Dict[str, Any]],
    default_ground_z: float = 345.0,
    epsg_code: int = 3844
) -> Dict[str, Any]:
    """Exports LoD1 solid building shells to OGC CityJSON v1.1 via Volumetric3DBuilder."""
    return export_cityjson_lod1(
        output_cityjson_path=output_cityjson_path,
        buildings=buildings,
        default_ground_z=default_ground_z,
        epsg_code=epsg_code
    )


# =============================================================================
# 7. Context & Session Memory Inspection Tools (MD 4 Section 29) — ALLOW
# =============================================================================

@mcp.tool(name="context.get")
def tool_context_get() -> Dict[str, Any]:
    """Retrieves full cached environmental context snapshot (project, CRS, hardware, inputs, providers)."""
    return get_context_snapshot()


@mcp.tool(name="context.get_aoi")
def tool_context_get_aoi() -> Dict[str, Any]:
    """Retrieves current Area of Interest (AOI) bounding box with identifiable source."""
    return get_default_context_engine().get_aoi_context()


@mcp.tool(name="context.get_layers")
def tool_context_get_layers() -> List[Dict[str, Any]]:
    """Retrieves compact metadata summary for loaded/available vector layers."""
    return get_default_context_engine().get_layers_summary()


@mcp.tool(name="context.get_inputs")
def tool_context_get_inputs() -> Dict[str, Any]:
    """Retrieves metadata headers for candidate orthophotos and LiDAR clouds without loading full data."""
    return get_default_context_engine().get_inputs_metadata()


@mcp.tool(name="memory.get_recent_runs")
def tool_memory_get_recent_runs(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves recent completed/failed tasks across sessions from persistent SQLite memory."""
    mem = SessionMemory()
    return mem.get_recent_runs(limit=limit)


@mcp.tool(name="memory.get_task_history")
def tool_memory_get_task_history(task_id: str) -> List[Dict[str, Any]]:
    """Retrieves detailed execution and retry history for a specific task_id."""
    mem = SessionMemory()
    return mem.get_task_history(task_id=task_id)


@mcp.tool(name="memory.search")
def tool_memory_search(query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Performs structured keyword search across historical tasks, memory entries, and decisions."""
    mem = SessionMemory()
    return mem.search_memory(query=query, category=category)


if __name__ == "__main__":
    mcp.run()


