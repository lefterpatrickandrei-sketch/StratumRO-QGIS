# -*- coding: utf-8 -*-
"""
PUG Layout FINAL — Iepurești
Repară: titlu, legendă populată, layere 2D, poziționare corectă
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

ROOT    = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT  = ROOT / "output"
GPKG    = OUTPUT / "UAT_Iepuresti_Master.gpkg"
QGZ     = OUTPUT / "UAT_Iepuresti_PUG_Final.qgz"
PDF     = OUTPUT / "UAT_Iepuresti_PUG_A3_Final.pdf"

print("=" * 70)
print(">>> PUG LAYOUT FINAL — Iepurești <<<")
print("=" * 70)

qgs = QgsApplication([], True)
qgs.initQgis()
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești — Planșă A3")

# Ortofoto fundal
ortho_url = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
             "World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0")
ortho = QgsRasterLayer(ortho_url, "Ortofoto (Esri)", "wms")
if ortho.isValid():
    project.addMapLayer(ortho)
    print("[OK] Ortofoto încărcată")

# Layere cu stiluri + ordine corectă (jos→sus)
theme = [
    # (layer, display, color, outline, width, opacity)
    ("zona_agricola_arabil",   "Terenuri Arabile (A_Ar)",  "252,243,222,120", "220,205,175,160", "0.1"),
    ("zona_pasuni_fanete",     "Pășuni / Fânețe (A_P)",    "215,235,180,140", "165,195,125,180", "0.1"),
    ("zona_forestiera",        "Fond Forestier (V_PD)",    "34,139,34,180",   "0,100,0,255",     "0.2"),
    ("zona_ape",               "Ape / Zone Umede (ZHA)",   "30,144,255,180",  "0,0,205,255",     "0.2"),
    ("zona_curti_constructii", "Curți-Construcții (CC)",   "255,145,0,200",   "190,70,0,255",    "0.25"),
    ("zona_circulatii",        "Circulații Rutiere (TR)",  "90,90,90,230",    "30,30,30,255",    "0.1"),
    ("constructii",            "Clădiri (+0.50m)",         "178,34,34,255",   "0,0,0,255",       "0.15"),
    ("limita_UAT",             "Limită UAT",               "0,0,0,0",         "0,0,0,255",       "0.9"),
]

added = []
for lname, dname, fill, outline, width in theme:
    vl = QgsVectorLayer(f"{GPKG}|layername={lname}", dname, "ogr")
    if not vl.isValid():
        print(f"  [!] Nu pot încărca: {lname}")
        continue
    sym = QgsFillSymbol.createSimple({
        "color": fill,
        "outline_color": outline,
        "outline_width": width
    })
    vl.setRenderer(QgsSingleSymbolRenderer(sym))
    if vl.featureCount() > 0:
        project.addMapLayer(vl)
        added.append(vl)
        print(f"  [OK] {dname}: {vl.featureCount()} features")

# Poduri — linii
vl_pod = QgsVectorLayer(f"{GPKG}|layername=poduri", "Poduri", "ogr")
if vl_pod.isValid() and vl_pod.featureCount() > 0:
    sym = QgsLineSymbol.createSimple({"color": "0,0,0,255", "width": "0.7"})
    vl_pod.setRenderer(QgsSingleSymbolRenderer(sym))
    project.addMapLayer(vl_pod)
    added.append(vl_pod)
    print(f"  [OK] Poduri: {vl_pod.featureCount()} features")

# ─── LAYOUT A3 LANDSCAPE 420×297 ───
print("\n[LAYOUT] Compunere planșă A3...")
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Iepuresti_A3_Final")
lm.addLayout(layout)

page = layout.pageCollection().page(0)
page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

# HARTĂ — 300 × 275 mm (stânga)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(300, 277, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.4, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

# Zoom pe limita UAT
for vl in added:
    if vl.name() == "Limită UAT":
        ext = vl.extent()
        ext.scale(1.08)
        map_item.zoomToExtent(ext)
        break
layout.addLayoutItem(map_item)

# GRILĂ coordonate
grid = map_item.grid()
grid.setEnabled(True)
grid.setStyle(QgsLayoutItemMapGrid.Solid)
grid.setIntervalX(1000)
grid.setIntervalY(1000)
grid.setAnnotationEnabled(True)
grid.setAnnotationPrecision(0)
grid.setAnnotationFont(QFont(FONT, 6))
grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)
grid.setFramePenSize(0.3)

# INDICATOR NORD
north = QgsLayoutItemPicture(layout)
north.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
north.attemptMove(QgsLayoutPoint(285, 15, QgsUnitTypes.LayoutMillimeters))
north.attemptResize(QgsLayoutSize(18, 18, QgsUnitTypes.LayoutMillimeters))
north.setFrameEnabled(True)
north.setBackgroundColor(QColor(255, 255, 255, 230))
layout.addLayoutItem(north)

# SCARĂ GRAFICĂ
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

# ─── PANOU DREAPTA (x=318, width=94) ───
XP, WP = 318, 94

# TITLU
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

# SUBTITLU
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

# LEGENDĂ — populată corect (ordine inversă = sus in legendă = layer de sus in harta)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ")
legend.setAutoUpdateModel(False)
root = legend.model().rootGroup()
root.clear()
# Ordine inversă pentru aspect corect (limita sus, arabil jos)
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
legend.attemptResize(QgsLayoutSize(WP, 75, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# ATRIBUIRI
attr = QgsLayoutItemLabel(layout)
attr.setText(
    "SURSE DATE:\n"
    "• OpenStreetMap (© OSM, ODbL)\n"
    "• ANCPI / INSPIRE (limită proxy)\n"
    "• Esri World Imagery (fundal)\n"
    "• StratumRO PUG Engine v7.1"
)
attr.setFont(QFont(FONT, 6))
attr.setFrameEnabled(True)
attr.setBackgroundEnabled(True)
attr.setBackgroundColor(QColor(248, 248, 248, 240))
attr.attemptMove(QgsLayoutPoint(XP, 112, QgsUnitTypes.LayoutMillimeters))
attr.attemptResize(QgsLayoutSize(WP, 20, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(attr)

# BILANȚ TERITORIAL
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
tbl.attemptMove(QgsLayoutPoint(XP, 134, QgsUnitTypes.LayoutMillimeters))
tbl.attemptResize(QgsLayoutSize(WP, 68, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(tbl)

# CARTUȘ TEHNIC
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
    "VERSIUNE: v7.1\n"
    "DATA: 22.09.2026"
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250, 245))
cartus.attemptMove(QgsLayoutPoint(XP, 204, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(WP, 83, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ))
print(f"[OK] QGZ salvat: {QGZ.name}")

# EXPORT PDF
print("\n[EXPORT] Generare PDF 300 DPI...")
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
print("=" * 70)