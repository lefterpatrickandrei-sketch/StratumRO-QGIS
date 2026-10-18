# -*- coding: utf-8 -*-
import os, sys
from qgis.core import (
    QgsApplication, QgsProject, QgsMapSettings, QgsMapRendererParallelJob,
    QgsCoordinateReferenceSystem, QgsRectangle, QgsRasterLayer, QgsVectorLayer,
    QgsFillSymbol, QgsSimpleFillSymbolLayer, QgsLineSymbol
)
from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor

qgs = QgsApplication([], False)
qgs.initQgis()

project = QgsProject.instance()
project.read('StratumRO_Inspectie_Vizuala.qgz')

# Get orthophoto
l_ortho = [l for l in project.mapLayers().values() if l.name().startswith("1.")][0]

gpkg_path = os.path.abspath(r"workspace\output\cladiri_stereo70.gpkg")

# 1. Clean Cadastral Buildings Layer
l_clean = QgsVectorLayer(f"{gpkg_path}|layername=CLADIRI_CADASTRU_CLEAN", "Cladiri Sigure ANCPI", "ogr")
sym_bldg = QgsFillSymbol.createSimple({
    "color": "0,210,255,140",       # semi-transparent cyan
    "outline_color": "0,230,255,255", # bright cyan border
    "outline_width": "0.45",
    "outline_style": "solid"
})
l_clean.renderer().setSymbol(sym_bldg)

# 2. Safe Margin Boundary Layer (STROKE ONLY, NO FILL)
l_margin = QgsVectorLayer(f"{gpkg_path}|layername=MARGINE_SIGURANTA_ORTOFOTO", "Limita Safe Margin", "ogr")
sym_margin = QgsFillSymbol.createSimple({
    "style": "no",                   # transparent fill
    "outline_color": "255,200,0,255", # yellow border
    "outline_width": "0.6",
    "outline_style": "dash"
})
l_margin.renderer().setSymbol(sym_margin)

# Configure map settings covering ENTIRE campus
settings = QgsMapSettings()
settings.setLayers([l_clean, l_margin, l_ortho])
settings.setDestinationCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# FULL CAMPUS EXTENT with slight margin
extent = QgsRectangle(390450.0, 584800.0, 391620.0, 585920.0)
settings.setExtent(extent)
settings.setOutputSize(QSize(2800, 2800))

job = QgsMapRendererParallelJob(settings)
job.start()
job.waitForFinished()

img = job.renderedImage()
out_file = os.path.abspath(r"workspace\output\inspectie_ortofoto_complet_safe_margin.png")
img.save(out_file, "PNG")
print(f"[+] Full orthophoto render with professional symbology saved to: {out_file}")
qgs.exitQgis()
