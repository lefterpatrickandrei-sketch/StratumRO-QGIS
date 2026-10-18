# -*- coding: utf-8 -*-
"""Creeaza compozit RGB Sentinel-2 (B04, B03, B02) si il adauga in proiectul QGIS."""
import os, sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from pathlib import Path
from osgeo import gdal
from qgis.core import QgsApplication, QgsProject, QgsRasterLayer

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
RAW_S2 = ROOT / "data" / "raw" / "sentinel2"
OUTPUT = ROOT / "output"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
RGB_PATH = OUTPUT / "sentinel2_rgb_iepuresti.tif"

# Identificare fisiere benzi G3
b04 = list(RAW_S2.glob("*_B04.tif"))[0]
b03 = list(RAW_S2.glob("*_B03.tif"))[0]
b02 = list(RAW_S2.glob("*_B02.tif"))[0]

# Construire VRT virtual RGB si export GeoTIFF
vrt_options = gdal.BuildVRTOptions(separate=True)
vrt = gdal.BuildVRT("", [str(b04), str(b03), str(b02)], options=vrt_options)
gdal.Translate(str(RGB_PATH), vrt)
vrt = None

# Incarcare in proiectul QGIS la baza listei
qgs = QgsApplication([], False)
qgs.initQgis()
project = QgsProject.instance()
project.read(str(QGZ_PATH))

raster_layer = QgsRasterLayer(str(RGB_PATH), "Sentinel-2 L2A (RGB)")
if raster_layer.isValid():
    project.addMapLayer(raster_layer, False)
    root_group = project.layerTreeRoot()
    root_group.addLayer(raster_layer)  # Adaugat la final (sub toate straturile vectoriale)
    project.write(str(QGZ_PATH))
    print("Compozit RGB Sentinel-2 creat si integrat la baza proiectului.")

qgs.exitQgis()
