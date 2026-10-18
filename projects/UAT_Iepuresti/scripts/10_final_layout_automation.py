# -*- coding: utf-8 -*-
"""Automatizare completa G7: generare directa PDF A4 300 DPI (UAT Iepuresti)."""
import os, sys
from pathlib import Path

# Asiguram accesul la fonturile de sistem
os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
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

# 1. Initializare QGIS
qgs = QgsApplication([], True)
qgs.initQgis()

# 2. Incarcare font Arial
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
font_name = "Arial"

project = QgsProject.instance()
if not project.read(str(QGZ_PATH)):
    print(f"[EROARE] Nu s-a putut deschide proiectul {QGZ_PATH}")
    sys.exit(1)

# Curatare machete existente
layout_manager = project.layoutManager()
for l in layout_manager.layouts():
    layout_manager.removeLayout(l)

# 3. Creare Layout A4 Landscape (297 x 210 mm)
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Automatizare_G7_Final")
layout_manager.addLayout(layout)

# Identificare strat limita UAT pentru incadrarea bounding-box
uat_layer = None
for lyr in project.mapLayers().values():
    if "limita_uat" in lyr.name().lower() or "limita uat" in lyr.name().lower():
        uat_layer = lyr
        break

# 4. Harta Principala (Stanga: 200 x 182 mm)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(200, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeColor(QColor(80, 80, 80))
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))

# Setam explicit sistemul de coordonate Stereo 70
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Incadrare pe limita UAT (fara verificarea featureCount care returna -1)
if uat_layer is not None and not uat_layer.extent().isEmpty():
    bbox = uat_layer.extent()
    bbox.scale(1.08)  # Margine de 8% in jurul comunei
    map_item.setExtent(bbox)
else:
    print("[AVERTISMENT] Stratul limita_UAT nu a furnizat un extent valid!")

layout.addLayoutItem(map_item)
map_item.refresh()

# 5. Titlu Harta
title = QgsLayoutItemLabel(layout)
title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU (SIRUTA 103684)")
f_title = QFont(font_name, 13, QFont.Bold)
title.setFont(f_title)
title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(200, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

# 6. Scara Grafica (ancorata in coltul stanga-jos al hartii)
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
scalebar.attemptMove(QgsLayoutPoint(15, 185, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(scalebar)

# 7. Panou Lateral Dreapta: Legenda
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
legend.attemptMove(QgsLayoutPoint(215, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(72, 98, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 8. Panou Lateral Dreapta: Cartus Tehnic
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "PARAMETRI TEHNICI:\n"
    "• Proiecție: Stereo 70 (EPSG:3844)\n"
    "• Sursă date: OpenStreetMap (ODbL)\n"
    "• Construcții: Buffer +0.50m (GEOS)\n"
    "• Drumuri: Ampriză 6.0m (GEOS)\n\n"
    "CONFORMITATE CARTOGRAFICĂ (I5):\n"
    "Limita administrativă este REFERENCE\n"
    "(proxy OSM admin_level=8). Nu are\n"
    "valoare de graniță cadastrală ANCPI.\n"
    "Imobile/intravilan: DATA GAP."
)
cartus.setFont(QFont(font_name, 7))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(215, 120, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(72, 80, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

# Salvare proiect cu macheta integrata
project.write()

# 9. Export PDF la 300 DPI
exporter = QgsLayoutExporter(layout)
pdf_settings = QgsLayoutExporter.PdfExportSettings()
pdf_settings.dpi = 300
pdf_settings.rasterizeWholeImage = False

# Daca fisierul este deschis in browser, exportam intr-un nume neblocat
try:
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    target_pdf = PDF_PATH
except PermissionError:
    target_pdf = OUTPUT / "harta_Iepuresti_export.pdf"
    print(f"[INFO] Fisierul original era deschis. Salvam in: {target_pdf.name}")

res = exporter.exportToPdf(str(target_pdf), pdf_settings)

if res == QgsLayoutExporter.Success:
    print(f"[SUCCES] Harta a fost generata complet: {target_pdf}")
else:
    print(f"[EROARE] Exportul a esuat cu codul: {res}")

qgs.exitQgis()
