# -*- coding: utf-8 -*-
"""
StratumRO AI Tool Wrappers.
Exposes clean, deterministic function wrappers around core geodetic engines:
LiDAR, Raster, SAM2 Segmentation, Vectorizer, CAD/TopoLT, and Topology Validation.
"""

from .lidar_tools import inspect_lidar, generate_ndsm
from .raster_tools import inspect_raster, extract_ortho_chip
from .segmentation_tools import run_sam2_segmentation, inspect_mask
from .vector_tools import (
    regularize_footprints,
    apply_eave_offset,
    create_planar_partition,
    export_gpkg_layer,
    export_cityjson_lod1,
)
from .cadastral_tools import (
    validate_topology,
    validate_ancpi,
    create_preview,
    commit_to_project,
    export_topolt_cad,
    export_cp_file,
)
from .project_tools import (
    get_workspace_context,
    get_aoi,
    list_layers,
    inspect_layer,
)
from .evaluation_tools import compare_ground_truth
from .security import resolve_sandboxed_path, check_permission, PermissionClass
from .vlm_tools import (
    vlm_verify_single_building_tool,
    vlm_batch_audit_layer_tool,
    vlm_filter_false_positives_tool,
)

__all__ = [
    "inspect_lidar",
    "generate_ndsm",
    "inspect_raster",
    "extract_ortho_chip",
    "run_sam2_segmentation",
    "inspect_mask",
    "regularize_footprints",
    "apply_eave_offset",
    "create_planar_partition",
    "export_gpkg_layer",
    "export_cityjson_lod1",
    "validate_topology",
    "validate_ancpi",
    "create_preview",
    "commit_to_project",
    "export_topolt_cad",
    "export_cp_file",
    "get_workspace_context",
    "get_aoi",
    "list_layers",
    "inspect_layer",
    "compare_ground_truth",
    "resolve_sandboxed_path",
    "check_permission",
    "PermissionClass",
    "vlm_verify_single_building_tool",
    "vlm_batch_audit_layer_tool",
    "vlm_filter_false_positives_tool",
]
