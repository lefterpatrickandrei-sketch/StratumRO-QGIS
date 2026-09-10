# -*- coding: utf-8 -*-
"""
Create Styled QGIS Project for Visual Inspection of Orthophoto vs. Cadastre vs. AI
==================================================================================
Generates StratumRO_Inspectie_Vizuala.qgz with:
  1. Ortofoto Cluj USAMV RGB (10 cm GSD)
  2. Cadastru Teren (Ground Truth - 29 cladiri pure) [Contur Albastru Punctat]
  3. Predictii AI Hibride (CLADIRI_HIBRID) [Contur Portocaliu Plin + Fill Transparent]
  4. nDSM LiDAR (Inaltime cladiri)
"""

import os
import sys

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsRasterLayer,
    QgsVectorLayer,
    QgsCoordinateReferenceSystem,
    QgsSingleSymbolRenderer,
    QgsFillSymbol,
    QgsSimpleFillSymbolLayer,
    QgsPalLayerSettings,
    QgsVectorLayerSimpleLabeling,
    QgsTextFormat,
    QgsTextBufferSettings,
    QgsRectangle
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

# Initialize QGIS Application headless
qgs = QgsApplication([], False)
qgs.initQgis()

project = QgsProject.instance()
project.clear()
project.setTitle("StratumRO — Inspecție Vizuală Ortofoto vs. Cadastru vs. AI")
crs_3844 = QgsCoordinateReferenceSystem("EPSG:3844")
project.setCrs(crs_3844)

base_dir = os.path.abspath(".")

# 1. Add Ortofoto RGB Raster
ortho_path = os.path.join(base_dir, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")
if os.path.exists(ortho_path):
    ortho_layer = QgsRasterLayer(ortho_path, "1. Ortofoto Aerian RGB (10 cm GSD)", "gdal")
    if ortho_layer.isValid():
        project.addMapLayer(ortho_layer)
        print("[+] Adaugat layer: Ortofoto RGB")
    else:
        print("[-] Eroare la incarcarea Ortofoto RGB")

# 2. Add nDSM LiDAR Raster (Hidden by default, useful for 3D checks)
ndsm_path = os.path.join(base_dir, "workspace", "output", "ndsm_stereo70.tif")
if os.path.exists(ndsm_path):
    ndsm_layer = QgsRasterLayer(ndsm_path, "2. Înălțime LiDAR nDSM (H > 2.5m)", "gdal")
    if ndsm_layer.isValid():
        project.addMapLayer(ndsm_layer)
        # Uncheck by default so ortho is visible
        project.layerTreeRoot().findLayer(ndsm_layer.id()).setItemVisibilityChecked(False)
        print("[+] Adaugat layer: nDSM LiDAR")

# 3. Add AI Predictions (CLADIRI_HIBRID)
pred_gpkg = os.path.join(base_dir, "workspace", "output", "cladiri_stereo70.gpkg")
pred_uri = f"{pred_gpkg}|layername=CLADIRI_HIBRID"
pred_layer = QgsVectorLayer(pred_uri, "3. Predicții AI Hibrid (StratumRO SAM 2 + LiDAR)", "ogr")

if pred_layer.isValid():
    # Style: Orange border, semi-transparent fill
    sym = QgsFillSymbol.createSimple({
        'color': '255,109,0,30',           # Portocaliu foarte transparent
        'outline_color': '255,109,0,255',   # Portocaliu aprins
        'outline_width': '0.7',             # 0.7 mm
        'outline_style': 'solid'
    })
    pred_layer.setRenderer(QgsSingleSymbolRenderer(sym))

    # Labeling: AI #ID
    text_format = QgsTextFormat()
    text_format.setSize(8.5)
    text_format.setColor(QColor(255, 109, 0))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.2)
    buffer.setColor(QColor(255, 255, 255))
    text_format.setBuffer(buffer)

    settings = QgsPalLayerSettings()
    settings.fieldName = "'AI #' || to_string(id)"
    settings.setFormat(text_format)
    pred_layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    pred_layer.setLabelsEnabled(True)

    project.addMapLayer(pred_layer)
    print("[+] Adaugat layer: Predicții AI (CLADIRI_HIBRID)")

# 4. Add Ground Truth (29 Cadastral Buildings)
gt_path = os.path.join(base_dir, "data", "ground_truth", "tier1_teren.geojson")
gt_layer = QgsVectorLayer(gt_path, "4. Cadastru Teren (Ground Truth - 29 Clădiri)", "ogr")

if gt_layer.isValid():
    # Style: Cyan / Neon Blue, dashed outline, transparent fill
    sym_gt = QgsFillSymbol.createSimple({
        'color': '0,0,0,0',                 # 100% transparent
        'outline_color': '0,229,255,255',   # Cyan / Neon Blue
        'outline_width': '0.9',             # 0.9 mm (mai gros, vizibil pe orto)
        'outline_style': 'dash'             # Linie intrerupta
    })
    gt_layer.setRenderer(QgsSingleSymbolRenderer(sym_gt))

    # Labeling: REF_ID
    text_format_gt = QgsTextFormat()
    text_format_gt.setSize(9.0)
    text_format_gt.setColor(QColor(0, 229, 255))
    f = text_format_gt.font()
    f.setBold(True)
    text_format_gt.setFont(f)
    buffer_gt = QgsTextBufferSettings()
    buffer_gt.setEnabled(True)
    buffer_gt.setSize(1.2)
    buffer_gt.setColor(QColor(0, 0, 0))
    text_format_gt.setBuffer(buffer_gt)

    settings_gt = QgsPalLayerSettings()
    settings_gt.fieldName = "id || '\n(' || to_string(round(area_m2, 0)) || ' m²)'"
    settings_gt.setFormat(text_format_gt)
    gt_layer.setLabeling(QgsVectorLayerSimpleLabeling(settings_gt))
    gt_layer.setLabelsEnabled(True)

    project.addMapLayer(gt_layer)
    print("[+] Adaugat layer: Cadastru Teren (Ground Truth)")

# Save Project
out_qgz = os.path.join(base_dir, "StratumRO_Inspectie_Vizuala.qgz")
project.write(out_qgz)
print(f"[+] Proiect QGIS salvat cu succes în: {out_qgz}")

qgs.exitQgis()
