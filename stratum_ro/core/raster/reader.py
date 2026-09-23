# -*- coding: utf-8 -*-
"""
StratumRO — Core Raster: Generic I/O & Windowed Slicing (Phase 3)
Pure-Python, deterministic raster reader wrapping rasterio.
Agnostic of specific building or vegetation models. Zero QGIS dependencies.
"""

from dataclasses import dataclass
from typing import Tuple, Optional, Any, Dict
import numpy as np
import rasterio
from rasterio.windows import from_bounds


@dataclass(frozen=True)
class RasterMetadata:
    """Standard metadata container for any single/multi-band geospatial raster."""
    width: int
    height: int
    count: int
    crs: str
    bounds: Tuple[float, float, float, float]
    resolution: Tuple[float, float]
    nodata: Optional[float]
    dtype: str


class CoreRasterReader:
    """
    Generic raster reader providing windowed reading and difference calculations.
    """

    def get_metadata(self, raster_path: str) -> RasterMetadata:
        """Extracts spatial metadata from raster header without loading pixels into memory."""
        with rasterio.open(raster_path) as src:
            res = src.res
            return RasterMetadata(
                width=src.width,
                height=src.height,
                count=src.count,
                crs=str(src.crs),
                bounds=(src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top),
                resolution=(float(res[0]), float(res[1])),
                nodata=src.nodata,
                dtype=str(src.dtypes[0])
            )

    def read_window(
        self,
        raster_path: str,
        bounds: Tuple[float, float, float, float],
        band: int = 1
    ) -> Tuple[np.ndarray, Any]:
        """
        Reads a spatial sub-window defined by geographic/projected bounds.
        Returns (pixel_array, window_affine_transform).
        """
        with rasterio.open(raster_path) as src:
            left, bottom, right, top = bounds
            win = from_bounds(left, bottom, right, top, src.transform)
            data = src.read(band, window=win)
            win_transform = src.window_transform(win)
            return data, win_transform

    def compute_difference(
        self,
        array_a: np.ndarray,
        array_b: np.ndarray,
        nodata_val: float = -9999.0
    ) -> np.ndarray:
        """
        Computes cell-by-cell difference: array_a - array_b.
        Handles nodata masks safely.
        """
        if array_a.shape != array_b.shape:
            raise ValueError(f"Array shape mismatch: {array_a.shape} vs {array_b.shape}")
        
        valid_mask = (array_a != nodata_val) & (array_b != nodata_val) & ~np.isnan(array_a) & ~np.isnan(array_b)
        diff = np.full(array_a.shape, nodata_val, dtype=np.float32)
        diff[valid_mask] = array_a[valid_mask] - array_b[valid_mask]
        return diff
