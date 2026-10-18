# -*- coding: utf-8 -*-
"""Automatizare completa Layout QGIS G7: fonturi native Windows, compozitie A4 300 DPI."""
import os, sys
from pathlib import Path

# Indicam direct folderul de fonturi catre runtime-ul Qt
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from qgis.core import (
    QgsApplication, QgsProject, QgsPrintLayout,
    QgsLayoutItemMap, QgsLayoutItemLabel, QgsLayoutItemScaleBar,
    QgsLayoutItemLegend, QgsLayoutPoint, QgsLayoutSize,
    QgsUnitTypes, QgsLayoutExporter, QgsCoordinateReferenceSystem
)
from qgis.PyQt.QtGui import QColor, QFont

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT / "harta_Iepuresti.pdf"

# Initializam aplicatia cu suport GUI activ pentru acces la engine-ul nativ de fonturi Windows
qgs = QgsApplication([], True)
qgs.initQgis()

project = QgsProject.instance()
if not project.read(str(QGZ_PATH)):
    print(f"Eroare: Nu s-a putut citi proiectul {QGZ_PATH}")
    sys.exit(1)

# Curatam machetele vechi pentru a evita suprapunerea elementelor
layout_manager = project.layoutManager()
for l in layout_manager.layouts():
    layout_manager.removeLayout(l)

# Creare macheta noua A4 Landscape (297 x 210 mm)
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Automatizare_G7_Iepuresti")
layout_manager.addLayout(layout)

# Identificare strat limita pentru incadrare
uat_layer = None
for lyr in project.mapLayers().values():
    if "limita_uat" in lyr.name().lower():
        uat_layer = lyr
        break

# 1. Harta principala (stanga)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(205, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeColor(QColor(80, 80, 80))
map_item.setFrameStrokeWidth(QgsLayoutSize(0.3, QgsUnitTypes.LayoutMillimeters))

if uat_layer and uat_layer.featureCount() > 0:
    extent = uat_layer.extent()
    extent.scale(1.06)
    map_item.setExtent(extent)

layout.addLayoutItem(map_item)

# 2. Titlu Harta
title = QgsLayoutItemLabel(layout)
title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU (SIRUTA 103684)")
font_title = QFont("Arial", 13)
font_title.setBold(True)
title.setFont(font_title)
title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(205, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

# 3. Scara Grafica (ancorata in coltul hartii cu scut protector alb)
scalebar = QgsLayoutItemScaleBar(layout)
scalebar.setStyle("Single Box")
scalebar.setLinkedMap(map_item)
scalebar.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
scalebar.setNumberOfSegments(3)
scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
scalebar.setUnitLabel(" km")
scalebar.setFont(QFont("Arial", 8))
scalebar.setBackgroundEnabled(True)
scalebar.setBackgroundColor(QColor(255, 255, 255, 230))
scalebar.setFrameEnabled(True)
scalebar.setFrameStrokeWidth(QgsLayoutSize(0.2, QgsUnitTypes.LayoutMillimeters))
scalebar.attemptMove(QgsLayoutPoint(14, 184, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(scalebar)

# 4. Panou Lateral Dreapta: Legenda
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ")
legend.setStyleFont(QgsLayoutItemLegend.Title, QFont("Arial", 10, QFont.Bold))
legend.setStyleFont(QgsLayoutItemLegend.Subgroup, QFont("Arial", 8, QFont.Bold))
legend.setStyleFont(QgsLayoutItemLegend.Item, QFont("Arial", 8))
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutSize(0.3, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(220, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(67, 95, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 5. Panou Lateral Dreapta: Cartus Tehnic
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "PARAMETRI TEHNICI:\n"
    "• Proiecție: Stereo 70 (EPSG:3844)\n"
    "• Sursă date: OpenStreetMap (ODbL)\n"
    "• Construcții: Buffer +0.50m (GEOS)\n"
    "• Drumuri: Ampriză 6.0m (GEOS)\n\n"
    "AVIZ DE CONFORMITATE (I5):\n"
    "Limita administrativă este REFERENCE\n"
    "(proxy OSM admin_level=8). Nu are\n"
    "valoare de graniță cadastrală ANCPI.\n"
    "Imobile/intravilan: DATA GAP."
)
font_cartus = QFont("Arial", 7)
cartus.setFont(font_cartus)
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutSize(0.3, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(220, 118, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(67, 82, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

# Salvare macheta in proiectul QGIS
project.write()

# 6. Export PDF la 300 DPI
exporter = QgsLayoutExporter(layout)
pdf_settings = QgsLayoutExporter.PdfExportSettings()
pdf_settings.dpi = 300
pdf_settings.rasterizeWholeImage = False  # Textul ramane vectorial, clar si cautabil

result = exporter.exportToPdf(str(PDF_PATH), pdf_settings)

if result == QgsLayoutExporter.Success:
    print(f"[OK] Automatizarea a reusit! Fisier generat: {PDF_PATH}")
else:
    print(f"[EROARE] Exportul PDF a esuat cu codul: {result}")

qgs.exitQgis()
