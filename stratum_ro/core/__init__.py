# -*- coding: utf-8 -*-
"""
StratumRO — Universal Core Scientific & Geospatial Package (Phase 3)
Pure-Python, deterministic geomatics, geometry, geodesy, and quality assurance.
Zero QGIS GUI dependencies. Zero AI/LLM dependencies.
"""

from stratum_ro.core.geometry import (
    CoreGeometryEngine,
    orthogonalize_cad,
    compute_iou,
    compute_hausdorff,
    compute_boundary_rmse,
    compute_centroid_shift,
)
from stratum_ro.core.geodesy import (
    CoreCRSManager,
    CoreTransformer,
)
from stratum_ro.core.qa_qc import (
    CoreGeometryValidator,
)
from stratum_ro.core.raster import (
    RasterMetadata,
    CoreRasterReader,
)
from stratum_ro.core.pointcloud import (
    PointCloudMetadata,
    CorePointCloudReader,
)

__all__ = [
    "CoreGeometryEngine",
    "orthogonalize_cad",
    "compute_iou",
    "compute_hausdorff",
    "compute_boundary_rmse",
    "compute_centroid_shift",
    "CoreCRSManager",
    "CoreTransformer",
    "CoreGeometryValidator",
    "RasterMetadata",
    "CoreRasterReader",
    "PointCloudMetadata",
    "CorePointCloudReader",
]
