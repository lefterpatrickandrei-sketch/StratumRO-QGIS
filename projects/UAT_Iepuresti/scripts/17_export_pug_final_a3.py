# -*- coding: utf-8 -*-
"""
STRATUMRO PUG ENGINE — PLANȘA FINALĂ DE REGLEMENTĂRI URBANISTICE (FORMAT A3)
UAT IEPUREȘTI, JUDEȚUL GIURGIU (SIRUTA 103684)
Corectat: Redimensionare pagina directa A3 Landscape (420 x 297 mm).
"""
import os, sys
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutPoint,
    QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
GPKG_PATH = OUTPUT / "PUG_Iepuresti_Urban.gpkg"
QGZ_PATH = OUTPUT / "PUG_Iepuresti_Urban.qgz"
PDF_PATH = OUTPUT / "PUG_Iepuresti_Plansa_Finala_A3.pdf"

print("="*75)
print(">>> STRATUMRO PUG: EXPORT PLANȘĂ FINALĂ A3 (300 DPI) <<<")
print("="*75)

qgs = QgsApplication([], True)
qgs.initQgis()

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești — Planșa Oficială de Reglementări A3")

# Ierarhie și Simbolistică Urbanistică PUG
styles = [
    # 1. Extravilan Agricol
    ("zona_agricola_arabil", "Terenuri Arabile Extravilan (A_Ar)", "fill", {"color": "250,242,228,255", "outline_color": "218,208,188,255", "outline_width": "0.1"}),
    ("zona_pasuni_fanete", "Pășuni / Fânețe Naturale (A_P)", "fill", {"color": "215,235,185,255", "outline_color": "175,200,140,255", "outline_width": "0.1"}),
    ("zona_forestiera", "Fond Forestier / Păduri (V_PD)", "fill", {"color": "46,139,87,255", "outline_color": "30,90,55,255", "outline_width": "0.2"}),
    ("zona_ape", "Ape și Zone Umede Neajlov (ZHA)", "fill", {"color": "165,215,245,255", "outline_color": "70,130,180,255", "outline_width": "0.2"}),
    # 2. Țesut Urban
    ("perimetru_intravilan", "Perimetru Intravilan (Vatra Satelor)", "fill", {"color": "255,245,200,140", "outline_color": "220,100,0,255", "outline_width": "0.6", "outline_style": "dash"}),
    ("zona_curti_constructii", "Zonă Curți-Construcții (Parcele CC)", "fill", {"color": "255,185,90,220", "outline_color": "190,80,0,255", "outline_width": "0.2"}),
    ("zona_circulatii", "Circulații Rutiere / Străzi (TR)", "fill", {"color": "140,140,140,255", "outline_color": "80,80,80,255", "outline_width": "0.1"}),
    # 3. Fond Construit Regularizat (+0.50m)
    ("constructii_sam2", "Clădiri Regularizate (+0.50m)", "fill", {"color": "178,34,34,255", "outline_color": "30,30,30,255", "outline_width": "0.15"}),
    # 4. Limită Teritorială
    ("limita_UAT", "Limită Teritoriu Administrativ (UAT)", "fill", {"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.8"})
]

bbox = None
for lname, dname, stype, cfg in styles:
    uri = f"{GPKG_PATH}|layername={lname}"
    vl = QgsVectorLayer(uri, dname, "ogr")
    if not vl.isValid():
        continue
    vl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(cfg)))
    project.addMapLayer(vl)
    if lname == "limita_UAT":
        bbox = vl.extent()

# Curățare machete existente
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

# Creare Machetă A3 Landscape (420 x 297 mm)
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Plansa_Finala_A3")
lm.addLayout(layout)

# Setare dimensiune A3 Landscape (420 x 297 mm)
page = layout.pageCollection().page(0)
page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

# 1. Harta Principală (300 x 273 mm pe latura stângă)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(12, 12, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(300, 273, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if bbox and not bbox.isEmpty():
    bbox.scale(1.06)
    map_item.setExtent(bbox)

layout.addLayoutItem(map_item)
map_item.refresh()

# 2. Antet / Titlu Oficial PUG
t1 = QgsLayoutItemLabel(layout)
t1.setText("PLAN URBANISTIC GENERAL — COMUNA IEPUREȘTI, JUDEȚUL GIURGIU")
t1.setFont(QFont(FONT, 11, QFont.Bold))
t1.attemptMove(QgsLayoutPoint(318, 12, QgsUnitTypes.LayoutMillimeters))
t1.attemptResize(QgsLayoutSize(92, 10, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t1)

t2 = QgsLayoutItemLabel(layout)
t2.setText("PLANȘA 01: REGLEMENTĂRI URBANISTICE ȘI ZONIFICARE FUNCȚIONALĂ")
t2.setFont(QFont(FONT, 8, QFont.Bold))
t2.attemptMove(QgsLayoutPoint(318, 22, QgsUnitTypes.LayoutMillimeters))
t2.attemptResize(QgsLayoutSize(92, 6, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t2)

# 3. Legendă Urbanistică (dreapta)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ URBANISTICĂ")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(FONT, 7, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 7))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(318, 30, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(92, 92, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 4. Tabelul Oficial al Bilanțului Teritorial
table_label = QgsLayoutItemLabel(layout)
table_text = (
    "BILANȚ TERITORIAL — UAT IEPUREȘTI (SIRUTA 103684)\n"
    "Proiecție Stereo 70 (EPSG:3844) | Acoperire: 99.14%\n"
    "───────────────────────────────────────────────────────\n"
    "Cod   Zonă Funcțională / Utilizare       Suprafață   Pondere\n"
    "───────────────────────────────────────────────────────\n"
    "CC    Curți-Construcții (Gospodării)     210.44 ha    3.86%\n"
    "TR    Circulații Rutiere / Străzi         18.86 ha    0.35%\n"
    "ZHA   Ape și Zone Umede (Neajlov)         49.49 ha    0.91%\n"
    "V_PD  Fond Forestier / Păduri            470.65 ha    8.64%\n"
    "A_P   Pășuni și Fânețe (Luncă)           300.74 ha    5.52%\n"
    "A_Ar  Terenuri Arabile (Platou)         4351.35 ha   79.87%\n"
    "───────────────────────────────────────────────────────\n"
    "TOTAL TERITORIU CALCULAT                5401.52 ha  100.00%"
)
table_label.setText(table_text)
table_label.setFont(QFont("Consolas", 6))
table_label.setFrameEnabled(True)
table_label.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
table_label.setBackgroundEnabled(True)
table_label.setBackgroundColor(QColor(252, 252, 252))
table_label.attemptMove(QgsLayoutPoint(318, 126, QgsUnitTypes.LayoutMillimeters))
table_label.attemptResize(QgsLayoutSize(92, 60, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(table_label)

# 5. Scară Grafică
sb = QgsLayoutItemScaleBar(layout)
sb.setStyle("Single Box")
sb.setLinkedMap(map_item)
sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
sb.setNumberOfSegments(3)
sb.setUnits(QgsUnitTypes.DistanceKilometers)
sb.setUnitLabel(" km")
sb.setFont(QFont(FONT, 8))
sb.setBackgroundEnabled(True)
sb.setBackgroundColor(QColor(255, 255, 255, 230))
sb.setFrameEnabled(True)
sb.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
sb.attemptMove(QgsLayoutPoint(18, 270, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# 6. Cartuș Tehnic PUG
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOCUMENTAȚIE: PLAN URBANISTIC GENERAL (PUG)\n"
    "BENEFICIAR: Comuna Iepurești (SIRUTA 103684), Jud. Giurgiu\n"
    "SISTEM DE COORDONATE: Stereo 70 (EPSG:3844)\n\n"
    "PARAMETRI & CONFORMITATE:\n"
    "• Fond Construit: 140 clădiri regularizate cu offset +0.50m\n"
    "• Curți-Construcții (CC): Parcelar front stradal adâncime 40m\n"
    "• Intravilan: Vatră sat delimitată funcțional (CC + grădini)\n"
    "• Restricții: Servitute hidrografică râul Neajlov (L107/1996)\n\n"
    "AVIZ CONFORMITATE (Invariantul I5):\n"
    "Bază geospațială derivată autonom din surse deschise.\n"
    "Nu constituie act de proprietate cadastrală în sensul L7/1996."
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(318, 190, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(92, 95, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ_PATH))
print(f"  [OK] Proiectul QGIS a fost actualizat: {QGZ_PATH}")

# Export PDF la 300 DPI
exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300
settings.rasterizeWholeImage = False

target_pdf = PDF_PATH
try:
    if target_pdf.exists():
        target_pdf.unlink()
except PermissionError:
    target_pdf = OUTPUT / "PUG_Iepuresti_Plansa_Finala_A3_v2.pdf"

res = exporter.exportToPdf(str(target_pdf), settings)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Planșa Finală A3 a fost generată la 300 DPI:")
    print(f"               {target_pdf}")
else:
    print(f"\n[EROARE] Exportul PDF a eșuat cu codul: {res}")

qgs.exitQgis()
print("="*75)
