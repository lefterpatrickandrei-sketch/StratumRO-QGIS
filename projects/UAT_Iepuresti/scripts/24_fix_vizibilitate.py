# -*- coding: utf-8 -*-
"""
Fix vizibilitate: cladiri deasupra CC, drumuri distincte
"""
import os
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutItemPicture,
    QgsLayoutPoint, QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle,
    QgsLayoutItemMapGrid,
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT   = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
GPKG   = OUTPUT / "UAT_Iepuresti_Master.gpkg"
QGZ    = OUTPUT / "UAT_Iepuresti_PUG_Final.qgz"
PDF    = OUTPUT / "UAT_Iepuresti_PUG_A3_Final.pdf"

print(">>> FIX VIZIBILITATE <<<")
qgs = QgsApplication([], True)
qgs.initQgis()
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Ortofoto
ortho_url = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
             "World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0")
ortho = QgsRasterLayer(ortho_url, "Ortofoto (Esri)", "wms")
if ortho.isValid():
    project.addMapLayer(ortho)

# ─── ORDINE DE LA JOS LA SUS (strat peste strat) ───
# IMPORTANT: ce e ultimul adăugat = cel mai de sus în render

order = [
    # (nume_layer, nume_afisat, tip, config)
    ("zona_agricola_arabil",    "Terenuri Arabile (A_Ar)",  "poly",
        {"color":"252,243,222,100","outline_color":"220,205,175,140","outline_width":"0.05"}),

    ("zona_pasuni_fanete",      "Pășuni / Fânețe (A_P)",    "poly",
        {"color":"215,235,180,120","outline_color":"165,195,125,160","outline_width":"0.05"}),

    ("zona_forestiera",         "Fond Forestier (V_PD)",    "poly",
        {"color":"34,139,34,150","outline_color":"0,100,0,255","outline_width":"0.2"}),

    ("zona_ape",                "Ape / Zone Umede (ZHA)",   "poly",
        {"color":"30,144,255,160","outline_color":"0,0,205,255","outline_width":"0.2"}),

    # CC SUB clădiri
    ("zona_curti_constructii",  "Curți-Construcții (CC)",   "poly",
        {"color":"255,215,140,100","outline_color":"200,150,60,180","outline_width":"0.1"}),

    # DRUMURI - culoare distinctă, mai lat
    ("zona_circulatii",         "Circulații Rutiere (TR)",  "poly",
        {"color":"70,70,70,200","outline_color":"20,20,20,255","outline_width":"0.15"}),

    # CLĂDIRI DEASUPRA CC - ROȘU APRINS
    ("constructii",             "Clădiri (+0.50m)",         "poly",
        {"color":"220,20,20,255","outline_color":"80,0,0,255","outline_width":"0.2"}),

    # PODURI - linii
    ("poduri",                  "Poduri",                    "line",
        {"color":"0,0,0,255","width":"0.5"}),

    # LIMITA UAT - ultima, sus de tot
    ("limita_UAT",              "Limită UAT",                "poly",
        {"color":"0,0,0,0","outline_color":"0,0,0,255","outline_width":"0.9"}),
]

added = []
for lname, dname, tip, cfg in order:
    vl = QgsVectorLayer(f"{GPKG}|layername={lname}", dname, "ogr")
    if not vl.isValid():
        print(f"  [!] Lipsă: {lname}")
        continue
    if vl.featureCount() == 0:
        print(f"  [-] Gol: {lname}")
        continue
    if tip == "poly":
        sym = QgsFillSymbol.createSimple(cfg)
    else:
        sym = QgsLineSymbol.createSimple(cfg)
    vl.setRenderer(QgsSingleSymbolRenderer(sym))
    project.addMapLayer(vl)
    added.append(vl)
    print(f"  [OK] {dname}: {vl.featureCount()} features")

# ─── LAYOUT A3 ───
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Iepuresti_A3_Final_v2")
lm.addLayout(layout)

page = layout.pageCollection().page(0)
page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(300, 277, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.4, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

for vl in added:
    if vl.name() == "Limită UAT":
        ext = vl.extent()
        ext.scale(1.08)
        map_item.zoomToExtent(ext)
        break
layout.addLayoutItem(map_item)

# Grid
grid = map_item.grid()
grid.setEnabled(True)
grid.setStyle(QgsLayoutItemMapGrid.Solid)
grid.setIntervalX(1000)
grid.setIntervalY(1000)
grid.setAnnotationEnabled(True)
grid.setAnnotationPrecision(0)
grid.setAnnotationFont(QFont(FONT, 6))
grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)

# Nord
north = QgsLayoutItemPicture(layout)
north.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
north.attemptMove(QgsLayoutPoint(285, 15, QgsUnitTypes.LayoutMillimeters))
north.attemptResize(QgsLayoutSize(18, 18, QgsUnitTypes.LayoutMillimeters))
north.setFrameEnabled(True)
north.setBackgroundColor(QColor(255, 255, 255, 230))
layout.addLayoutItem(north)

# Scară
sb = QgsLayoutItemScaleBar(layout)
sb.setStyle("Single Box")
sb.setLinkedMap(map_item)
sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
sb.setNumberOfSegments(3)
sb.setUnits(QgsUnitTypes.DistanceKilometers)
sb.setUnitLabel(" km")
sb.setFont(QFont(FONT, 8))
sb.setBackgroundEnabled(True)
sb.setBackgroundColor(QColor(255, 255, 255, 235))
sb.setFrameEnabled(True)
sb.attemptMove(QgsLayoutPoint(15, 278, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# Panou dreapta
XP, WP = 318, 94

title = QgsLayoutItemLabel(layout)
title.setText("PLAN URBANISTIC GENERAL\nCOMUNA IEPUREȘTI, JUD. GIURGIU")
title.setFont(QFont(FONT, 11, QFont.Bold))
title.setHAlign(1)
title.setBackgroundEnabled(True)
title.setBackgroundColor(QColor(240, 240, 240, 255))
title.setFrameEnabled(True)
title.attemptMove(QgsLayoutPoint(XP, 10, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(WP, 14, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

sub = QgsLayoutItemLabel(layout)
sub.setText("PLANȘA 01 — REGLEMENTĂRI URBANISTICE")
sub.setFont(QFont(FONT, 8, QFont.Bold))
sub.setHAlign(1)
sub.setBackgroundEnabled(True)
sub.setBackgroundColor(QColor(250, 250, 250, 255))
sub.setFrameEnabled(True)
sub.attemptMove(QgsLayoutPoint(XP, 26, QgsUnitTypes.LayoutMillimeters))
sub.attemptResize(QgsLayoutSize(WP, 7, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sub)

# Legendă - ordine inversă (sus în legendă = sus în hartă)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ")
legend.setAutoUpdateModel(False)
root = legend.model().rootGroup()
root.clear()
for vl in reversed(added):
    root.addLayer(vl)
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 6))
except Exception:
    pass
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255, 240))
legend.attemptMove(QgsLayoutPoint(XP, 35, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(WP, 85, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# Atribuiri
attr = QgsLayoutItemLabel(layout)
attr.setText(
    "SURSE DATE:\n"
    "• OpenStreetMap (© OSM, ODbL)\n"
    "• ANCPI / INSPIRE (limită proxy)\n"
    "• Esri World Imagery (fundal)\n"
    "• StratumRO PUG Engine v7.2"
)
attr.setFont(QFont(FONT, 6))
attr.setFrameEnabled(True)
attr.setBackgroundEnabled(True)
attr.setBackgroundColor(QColor(248, 248, 248, 240))
attr.attemptMove(QgsLayoutPoint(XP, 122, QgsUnitTypes.LayoutMillimeters))
attr.attemptResize(QgsLayoutSize(WP, 20, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(attr)

# Bilanț
tbl = QgsLayoutItemLabel(layout)
tbl.setText(
    "BILANȚ TERITORIAL\n"
    "─────────────────────────────────\n"
    "Cod   Zonă funcțională        ha     %\n"
    "─────────────────────────────────\n"
    "CC    Curți-Construcții     552.58  10.14\n"
    "TR    Circulații           138.86   2.55\n"
    "ZHA   Ape / Zone umede      49.49   0.91\n"
    "V_PD  Fond forestier       470.65   8.64\n"
    "A_P   Pășuni / Fânețe      238.08   4.37\n"
    "A_Ar  Arabil              4115.43  75.39\n"
    "─────────────────────────────────\n"
    "TOTAL                    5465.47 100.00"
)
tbl.setFont(QFont("Consolas", 6))
tbl.setFrameEnabled(True)
tbl.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
tbl.setBackgroundEnabled(True)
tbl.setBackgroundColor(QColor(255, 255, 255, 245))
tbl.attemptMove(QgsLayoutPoint(XP, 144, QgsUnitTypes.LayoutMillimeters))
tbl.attemptResize(QgsLayoutSize(WP, 68, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(tbl)

# Cartuș
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOCUMENTAȚIE: PUG\n"
    "Beneficiar: Comuna Iepurești\n"
    "SIRUTA: 103684 | Jud. Giurgiu\n"
    "Proiecție: Stereo 70 (EPSG:3844)\n"
    "\n"
    "PARAMETRI:\n"
    "• Acoperire topologică: 100%\n"
    "• Offset construcții: +0.50 m\n"
    "• Poduri: 20 segmente OSM\n"
    "• Clădiri: 140 entități\n"
    "\n"
    "VERSIUNE: v7.2\n"
    "DATA: 22.09.2026"
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250, 245))
cartus.attemptMove(QgsLayoutPoint(XP, 214, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(WP, 73, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ))

exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300

if PDF.exists():
    try: PDF.unlink()
    except PermissionError:
        PDF = OUTPUT / "UAT_Iepuresti_PUG_A3_Final_v2.pdf"

res = exporter.exportToPdf(str(PDF), settings)
if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES] {PDF}")
else:
    print(f"\n[EROARE] Cod {res}")

qgs.exitQgis()