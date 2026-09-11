# -*- coding: utf-8 -*-
"""
Render LiDAR nDSM with Pseudocolor Shader and Cadastral Overlays
==============================================================
Produces docs/assets/inspectie_lidar_ndsm.jpg showing elevation profile
and AI building extraction.
"""

import os
import sys
from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsColorRampShader,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsMapSettings,
    QgsMapRendererParallelJob,
    QgsRectangle
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize

qgs = QgsApplication([], False)
qgs.initQgis()

base_dir = os.path.abspath(".")
ndsm_path = os.path.join(base_dir, "workspace", "output", "ndsm_stereo70.tif")
pred_path = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg") + "|layername=CLADIRI_HIBRID"
gt_path = os.path.join(base_dir, "data", "ground_truth", "tier1_teren.geojson")

# 1. Raster layer
r_layer = QgsRasterLayer(ndsm_path, "LiDAR nDSM", "gdal")
if not r_layer.isValid():
    print("[-] Failed to load nDSM raster")
    sys.exit(1)

# Color ramp shader for nDSM (0 to 25m)
fcn = QgsColorRampShader()
fcn.setColorRampType(QgsColorRampShader.Interpolated)
items = [
    QgsColorRampShader.ColorRampItem(0.0, QColor(15, 15, 25, 255), "0m - Ground"),
    QgsColorRampShader.ColorRampItem(2.5, QColor(30, 60, 120, 255), "2.5m - Vegetation"),
    QgsColorRampShader.ColorRampItem(5.0, QColor(20, 140, 160, 255), "5m - Single story"),
    QgsColorRampShader.ColorRampItem(10.0, QColor(220, 180, 40, 255), "10m - 2-3 stories"),
    QgsColorRampShader.ColorRampItem(18.0, QColor(220, 70, 20, 255), "18m - Tall buildings"),
    QgsColorRampShader.ColorRampItem(30.0, QColor(255, 255, 255, 255), "30m+ - High rise")
]
fcn.setColorRampItemList(items)
shader = QgsRasterShader()
shader.setRasterShaderFunction(fcn)
pseudo_renderer = QgsSingleBandPseudoColorRenderer(r_layer.dataProvider(), 1, shader)
r_layer.setRenderer(pseudo_renderer)

# 2. AI predictions layer
pred_layer = QgsVectorLayer(pred_path, "AI Pred", "ogr")
sym_pred = QgsFillSymbol.createSimple({
    "color": "255,109,0,30",
    "outline_color": "255,140,0,255",
    "outline_width": "0.8",
    "outline_style": "solid"
})
pred_layer.setRenderer(QgsSingleSymbolRenderer(sym_pred))

# 3. Ground truth layer
gt_layer = QgsVectorLayer(gt_path, "Ground Truth", "ogr")
sym_gt = QgsFillSymbol.createSimple({
    "color": "0,0,0,0",
    "outline_color": "0,255,255,255",
    "outline_width": "0.9",
    "outline_style": "dash"
})
gt_layer.setRenderer(QgsSingleSymbolRenderer(sym_gt))

# Settings
settings = QgsMapSettings()
settings.setLayers([gt_layer, pred_layer, r_layer])
settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Dynamic AOI extent from LIMITA_SECTOR_CADASTRAL (P2.3)
limita_path = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg") + "|layername=LIMITA_SECTOR_CADASTRAL"
limita_layer = QgsVectorLayer(limita_path, "Limita Sector", "ogr")
if limita_layer.isValid() and not limita_layer.extent().isEmpty():
    bbox = limita_layer.extent()
    print(f"[+] Loaded dynamic extent from LIMITA_SECTOR_CADASTRAL: {bbox.toString()}")
else:
    import warnings
    warnings.warn("LIMITA_SECTOR_CADASTRAL not found or empty. Using fallback hardcoded extent.")
    bbox = QgsRectangle(390620.0, 585350.0, 391180.0, 585780.0)

settings.setExtent(bbox)
settings.setOutputSize(QSize(2400, 1840))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()

img = job.renderedImage()
out_jpg = os.path.abspath("docs/assets/inspectie_lidar_ndsm.jpg")
os.makedirs(os.path.dirname(out_jpg), exist_ok=True)
img.save(out_jpg, "JPEG", 90)
print(f"[+] Rendered LiDAR nDSM inspection map to: {out_jpg}")

qgs.exitQgis()
