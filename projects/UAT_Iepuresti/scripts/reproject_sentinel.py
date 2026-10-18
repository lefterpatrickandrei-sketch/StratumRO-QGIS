# -*- coding: utf-8 -*-
"""Reproiecteaza Sentinel-2 RGB direct in EPSG:3844 cu contrast optimizat."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from osgeo import gdal
gdal.UseExceptions()

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
RAW_S2 = ROOT / "data" / "raw" / "sentinel2"
OUTPUT = ROOT / "output"
WARPED_RGB = OUTPUT / "sentinel2_stereo70_rgb.tif"

b04 = list(RAW_S2.glob("*_B04.tif"))[0]
b03 = list(RAW_S2.glob("*_B03.tif"))[0]
b02 = list(RAW_S2.glob("*_B02.tif"))[0]

# 1. Creeaza VRT RGB in coordonate sursa
vrt = gdal.BuildVRT("", [str(b04), str(b03), str(b02)], separate=True)

# 2. Reproiecteaza direct in EPSG:3844 pentru aliniere la proiect
gdal.Warp(
    str(WARPED_RGB),
    vrt,
    dstSRS="EPSG:3844",
    xRes=10,
    yRes=10,
    resampleAlg="bilinear"
)
vrt = None
print("Raster reproiectat cu succes in EPSG:3844:", WARPED_RGB)
