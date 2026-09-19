# -*- coding: utf-8 -*-
"""
Rasterize LiDAR point classes (Class 6: Building, Classes 3,4,5: Vegetation)
into a 2-band 1m GeoTIFF aligned with the active orthophoto extent.
"""

import os
import laspy
import numpy as np
import rasterio
from rasterio.transform import from_origin

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ORTHO_PATH = os.path.join(PROJECT_ROOT, "workspace", "e2e", "04_orthophoto", "active_ortho_crop.tif")
LAZ_PATH = r"C:\Users\lefpa\Desktop\date\Z_VladP\Comparatie\LAZ\NorPuncte_St70_S42.laz"
OUT_TIF = os.path.join(PROJECT_ROOT, "workspace", "phase3", "derived", "cluj_lidar_classes_1m.tif")


def rasterize_lidar_classes():
    print(f"[*] Reading orthophoto bounds: {ORTHO_PATH}")
    with rasterio.open(ORTHO_PATH) as src:
        bounds = src.bounds
        crs = src.crs

    res = 1.0
    width = int(np.ceil((bounds.right - bounds.left) / res))
    height = int(np.ceil((bounds.top - bounds.bottom) / res))
    transform = from_origin(bounds.left, bounds.top, res, res)

    print(f"[*] Loading LiDAR points from: {LAZ_PATH}")
    with laspy.open(LAZ_PATH) as fh:
        las = fh.read()
        x = np.asarray(las.x, dtype=np.float64)
        y = np.asarray(las.y, dtype=np.float64)
        cls = np.asarray(las.classification, dtype=np.uint8)

    # Filter to AOI
    mask = (x >= bounds.left) & (x <= bounds.right) & (y >= bounds.bottom) & (y <= bounds.top)
    x_aoi = x[mask]
    y_aoi = y[mask]
    cls_aoi = cls[mask]
    print(f"    Points in AOI: {len(x_aoi)}")

    cols = ((x_aoi - bounds.left) / res).astype(int)
    rows = ((bounds.top - y_aoi) / res).astype(int)
    valid = (cols >= 0) & (cols < width) & (rows >= 0) & (rows < height)

    cols = cols[valid]
    rows = rows[valid]
    cls_aoi = cls_aoi[valid]

    bldg_grid = np.zeros((height, width), dtype=np.int16)
    veg_grid = np.zeros((height, width), dtype=np.int16)

    for r, c, cl in zip(rows, cols, cls_aoi):
        if cl == 6:
            bldg_grid[r, c] += 1
        elif cl in (3, 4, 5):
            veg_grid[r, c] += 1

    print(f"    Building points rasterized: {np.sum(bldg_grid)}")
    print(f"    Vegetation points rasterized: {np.sum(veg_grid)}")

    os.makedirs(os.path.dirname(OUT_TIF), exist_ok=True)
    with rasterio.open(
        OUT_TIF,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=2,
        dtype=rasterio.int16,
        crs=crs,
        transform=transform,
        compress="lzw"
    ) as dst:
        dst.write(bldg_grid, 1)
        dst.set_band_description(1, "ASPRS_Class_6_Building_Count")
        dst.write(veg_grid, 2)
        dst.set_band_description(2, "ASPRS_Class_3_4_5_Vegetation_Count")

    print(f"[+] Saved rasterized LiDAR classes: {OUT_TIF}")


if __name__ == "__main__":
    rasterize_lidar_classes()
