# -*- coding: utf-8 -*-
"""Automatizare cartografica definitiva: font nativ Windows si export PDF valid."""
import os, sys
from pathlib import Path

if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from qgis.core import (
    QgsApplication, QgsProject, QgsPrintLayout,
    QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemScaleBar,
    QgsLayoutItemLegend, QgsLayoutPoint, QgsLayoutSize,
    QgsLayoutMeasurement, QgsUnitTypes, QgsLayoutExporter,
    QgsCoordinateReferenceSystem, QgsLegendStyle
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT / "harta_Iepuresti_final.pdf"

qgs = QgsApplication([], True)
qgs.initQgis()

# Injectare font nativ Windows
font_reg = QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
font_bold = QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")

if font_reg != -1:
    families = QFontDatabase.applicationFontFamilies(font_reg)
    font_name = families[0] if families else "Arial"
else:
    font_name = "Arial"

project = QgsProject.instance()
if not project.read(str(QGZ_PATH)):
    print(f"[EROARE] Nu s-a putut deschide proiectul {QGZ_PATH}")
    sys.exit(1)

layout_manager = project.layoutManager()
for l in layout_manager.layouts():
    layout_manager.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Macheta_Finala_G7")
layout_manager.addLayout(layout)

uat_layer = None
for lyr in project.mapLayers().values():
    if "limita_uat" in lyr.name().lower():
        uat_layer = lyr
        break

# 1. Harta principala
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(205, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeColor(QColor(80, 80, 80))
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))

if uat_layer and uat_layer.featureCount() > 0:
    extent = uat_layer.extent()
    extent.scale(1.05)
    map_item.setExtent(extent)

layout.addLayoutItem(map_item)

# 2. Titlu
title = QgsLayoutItemLabel(layout)
title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU (SIRUTA 103684)")
f_title = QFont(font_name, 13)
f_title.setBold(True)
title.setFont(f_title)
title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(205, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

# 3. Scara Grafica
scalebar = QgsLayoutItemScaleBar(layout)
scalebar.setStyle("Single Box")
scalebar.setLinkedMap(map_item)
scalebar.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
scalebar.setNumberOfSegments(3)
scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
scalebar.setUnitLabel(" km")
scalebar.setFont(QFont(font_name, 8))
scalebar.setBackgroundEnabled(True)
scalebar.setBackgroundColor(QColor(255, 255, 255, 230))
scalebar.setFrameEnabled(True)
scalebar.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
scalebar.attemptMove(QgsLayoutPoint(14, 184, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(scalebar)

# 4. Legenda
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(font_name, 10, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(font_name, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(font_name, 8))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(220, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(67, 95, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 5. Cartus tehnic
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "PARAMETRI TEHNICI:\n"
    "• Proiectie: Stereo 70 (EPSG:3844)\n"
    "• Sursa date: OpenStreetMap (ODbL)\n"
    "• Constructii: Buffer +0.50m (GEOS)\n"
    "• Drumuri: Ampriza 6.0m (GEOS)\n\n"
    "CONFORMITATE CARTOGRAFICA (I5):\n"
    "Limita administrativa este REFERENCE\n"
    "(proxy OSM admin_level=8). Nu are\n"
    "valoare de granita cadastrala ANCPI.\n"
    "Imobile/intravilan: DATA GAP."
)
f_cartus = QFont(font_name, 7)
cartus.setFont(f_cartus)
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(220, 118, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(67, 82, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write()

# 6. Export PDF
exporter = QgsLayoutExporter(layout)
pdf_settings = QgsLayoutExporter.PdfExportSettings()
pdf_settings.dpi = 300
pdf_settings.rasterizeWholeImage = False

result = exporter.exportToPdf(str(PDF_PATH), pdf_settings)

if result == QgsLayoutExporter.Success:
    print(f"[OK] Export finalizat cu succes: {PDF_PATH}")
else:
    print(f"[EROARE] Cod eroare export: {result}")

qgs.exitQgis()
