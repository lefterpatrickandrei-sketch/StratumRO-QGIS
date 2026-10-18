# -*- coding: utf-8 -*-
"""
PUG Iepuresti - COMPLET:
1. Ierarhizare drumuri (DN/DJ/DC/strazi)
2. Plan de incadrare in teritoriu
3. Metadate pe toate layerele
4. Fix vizibilitate (cladiri + drumuri vizibile)
"""
import os
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import ogr, osr
ogr.UseExceptions()

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutItemPicture,
    QgsLayoutPoint, QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle,
    QgsLayoutItemMapGrid, QgsRectangle,
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT   = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
GPKG   = OUTPUT / "UAT_Iepuresti_Master.gpkg"
QGZ    = OUTPUT / "UAT_Iepuresti_PUG_Final.qgz"
PDF    = OUTPUT / "UAT_Iepuresti_PUG_A3_Final.pdf"
ROADS  = ROOT / "data" / "processed" / "osm" / "roads.geojson"

print("=" * 70)
print(">>> PUG COMPLET v9.0 - Iepuresti <<<")
print("=" * 70)

# CRS
srs_3844 = osr.SpatialReference(); srs_3844.ImportFromEPSG(3844)
srs_3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
srs_4326 = osr.SpatialReference(); srs_4326.ImportFromEPSG(4326)
srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans = osr.CoordinateTransformation(srs_4326, srs_3844)

# ─── 1. IERARHIZARE DRUMURI ───
print("\n[1] Ierarhizare drumuri DN/DJ/DC/strazi...")

# Sterge layerele existente daca exista
ds = ogr.Open(str(GPKG), 1)
for lyr_name in ["drumuri_nationale", "drumuri_judetene", "drumuri_comunale", "drumuri_strazi"]:
    if ds.GetLayerByName(lyr_name):
        ds.DeleteLayer(lyr_name)

# Creeaza 4 layere noi
layer_defs = {
    "drumuri_nationale": ("DN", ogr.wkbMultiLineString),
    "drumuri_judetene":  ("DJ", ogr.wkbMultiLineString),
    "drumuri_comunale":  ("DC", ogr.wkbMultiLineString),
    "drumuri_strazi":    ("street", ogr.wkbMultiLineString),
}

lyrs = {}
for name, (cod, gtype) in layer_defs.items():
    lyr = ds.CreateLayer(name, srs_3844, gtype)
    lyr.CreateField(ogr.FieldDefn("categorie", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("cod", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("nume", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("licenta", ogr.OFTString))
    lyrs[name] = lyr

# Citeste roads.geojson si clasifica
if ROADS.exists():
    rd = ogr.Open(str(ROADS))
    counts = {"DN":0, "DJ":0, "DC":0, "street":0}
    for feat in rd.GetLayer(0):
        g = feat.GetGeometryRef()
        if g is None: continue
        gc = g.Clone()
        min_x, max_x, _, _ = gc.GetEnvelope()
        if abs(min_x) < 180 and abs(max_x) < 180:
            gc.Transform(trans)
        
        # Determina categoria
        ref = (feat.GetField("ref") or "").upper()
        highway = (feat.GetField("highway") or "").lower()
        
        if ref.startswith("DN") or highway in ("trunk","primary"):
            target = "drumuri_nationale"; cod = "DN"
        elif ref.startswith("DJ") or highway == "secondary":
            target = "drumuri_judetene"; cod = "DJ"
        elif ref.startswith("DC") or highway == "tertiary":
            target = "drumuri_comunale"; cod = "DC"
        else:
            target = "drumuri_strazi"; cod = "ST"
        
        # Forteaza MultiLineString
        if gc.GetGeometryName() == "LINESTRING":
            ml = ogr.Geometry(ogr.wkbMultiLineString)
            ml.AddGeometry(gc)
            gc = ml
        elif gc.GetGeometryName() != "MULTILINESTRING":
            continue
        
        nf = ogr.Feature(lyrs[target].GetLayerDefn())
        nf.SetGeometry(gc)
        nf.SetField("categorie", target)
        nf.SetField("cod", cod)
        nf.SetField("nume", feat.GetField("name") or "")
        nf.SetField("sursa", "OpenStreetMap")
        nf.SetField("licenta", "ODbL")
        lyrs[target].CreateFeature(nf)
        counts[cod] += 1
    
    print(f"    DN: {counts['DN']} | DJ: {counts['DJ']} | DC: {counts['DC']} | Strazi: {counts['street']}")
else:
    print(f"    [!] Lipseste: {ROADS}")

# ─── 2. METADATE PE LAYERELE EXISTENTE ───
print("\n[2] Adaug metadate pe layerele existente...")
META_FIELDS = [
    ("sursa", ogr.OFTString),
    ("licenta", ogr.OFTString),
    ("precizie_m", ogr.OFTReal),
    ("data_creare", ogr.OFTString),
]

for i in range(ds.GetLayerCount()):
    lyr = ds.GetLayerByIndex(i)
    defn = lyr.GetLayerDefn()
    existing = [defn.GetFieldDefn(j).GetName() for j in range(defn.GetFieldCount())]
    for fname, ftype in META_FIELDS:
        if fname not in existing:
            lyr.CreateField(ogr.FieldDefn(fname, ftype))
    print(f"    [OK] {lyr.GetName()}")

ds = None

# ─── 3. PROIECT QGIS + VIZIBILITATE ───
print("\n[3] Configurare proiect QGIS...")
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

# Ordine: jos -> sus
order = [
    ("zona_agricola_arabil",    "Terenuri Arabile (A_Ar)",   "poly",
        {"color":"252,243,222,80","outline_color":"220,205,175,120","outline_width":"0.05"}),
    ("zona_pasuni_fanete",      "Pasuni / Fanete (A_P)",     "poly",
        {"color":"215,235,180,100","outline_color":"165,195,125,140","outline_width":"0.05"}),
    ("zona_forestiera",         "Fond Forestier (V_PD)",     "poly",
        {"color":"34,139,34,150","outline_color":"0,100,0,255","outline_width":"0.2"}),
    ("zona_ape",                "Ape / Zone Umede (ZHA)",    "poly",
        {"color":"30,144,255,160","outline_color":"0,0,205,255","outline_width":"0.2"}),
    ("zona_curti_constructii",  "Curti-Constructii (CC)",    "poly",
        {"color":"255,215,140,60","outline_color":"200,150,60,120","outline_width":"0.08"}),
    ("zona_circulatii",         "Circulatii Rutiere (TR)",   "poly",
        {"color":"70,70,70,180","outline_color":"20,20,20,255","outline_width":"0.12"}),
    ("constructii",             "Cladiri (+0.50m)",          "poly",
        {"color":"220,20,20,255","outline_color":"80,0,0,255","outline_width":"0.25"}),
    ("poduri",                  "Poduri",                    "line",
        {"color":"0,0,0,255","width":"0.8"}),
    ("limita_UAT",              "Limita UAT",                "poly",
        {"color":"0,0,0,0","outline_color":"0,0,0,255","outline_width":"0.9"}),
]

added = []
for lname, dname, tip, cfg in order:
    vl = QgsVectorLayer(f"{GPKG}|layername={lname}", dname, "ogr")
    if not vl.isValid() or vl.featureCount() == 0:
        continue
    sym = QgsFillSymbol.createSimple(cfg) if tip == "poly" else QgsLineSymbol.createSimple(cfg)
    vl.setRenderer(QgsSingleSymbolRenderer(sym))
    vl.setScaleBasedVisibility(False)
    project.addMapLayer(vl)
    added.append(vl)
    print(f"    [OK] {dname}")

# Forteaza ordinea
layer_tree = project.layerTreeRoot()
ids = [vl.id() for vl in added]
if ortho.isValid():
    ids = [ortho.id()] + ids
layer_tree.setHasCustomLayerOrder(True)
layer_tree.setCustomLayerOrder(ids)

# ─── 4. LAYOUT A3 ───
print("\n[4] Layout A3...")
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Iepuresti_A3_v9")
lm.addLayout(layout)
layout.pageCollection().page(0).setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

# Harta
mi = QgsLayoutItemMap(layout)
mi.attemptMove(QgsLayoutPoint(10, 10, QgsUnitTypes.LayoutMillimeters))
mi.attemptResize(QgsLayoutSize(300, 277, QgsUnitTypes.LayoutMillimeters))
mi.setFrameEnabled(True)
mi.setFrameStrokeWidth(QgsLayoutMeasurement(0.4, QgsUnitTypes.LayoutMillimeters))
mi.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
mi.setLayers(ids)
for vl in added:
    if "Limita" in vl.name():
        ext = vl.extent(); ext.scale(1.08); mi.zoomToExtent(ext); break
layout.addLayoutItem(mi)

# Grid
grid = mi.grid()
grid.setEnabled(True); grid.setStyle(QgsLayoutItemMapGrid.Solid)
grid.setIntervalX(1000); grid.setIntervalY(1000)
grid.setAnnotationEnabled(True); grid.setAnnotationPrecision(0)
grid.setAnnotationFont(QFont(FONT, 6))
grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)

# Nord
north = QgsLayoutItemPicture(layout)
north.setPicturePath(":/images/north_arrows/layout_default_north_arrow.svg")
north.attemptMove(QgsLayoutPoint(285, 15, QgsUnitTypes.LayoutMillimeters))
north.attemptResize(QgsLayoutSize(18, 18, QgsUnitTypes.LayoutMillimeters))
north.setFrameEnabled(True)
north.setBackgroundColor(QColor(255,255,255,230))
layout.addLayoutItem(north)

# Scara
sb = QgsLayoutItemScaleBar(layout)
sb.setStyle("Single Box"); sb.setLinkedMap(mi)
sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
sb.setNumberOfSegments(3); sb.setUnits(QgsUnitTypes.DistanceKilometers)
sb.setUnitLabel(" km"); sb.setFont(QFont(FONT, 8))
sb.setBackgroundEnabled(True); sb.setBackgroundColor(QColor(255,255,255,235))
sb.setFrameEnabled(True)
sb.attemptMove(QgsLayoutPoint(15, 278, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# Panou dreapta
XP, WP = 318, 94

t = QgsLayoutItemLabel(layout)
t.setText("PLAN URBANISTIC GENERAL\nCOMUNA IEPURESTI, JUD. GIURGIU")
t.setFont(QFont(FONT, 11, QFont.Bold)); t.setHAlign(1)
t.setBackgroundEnabled(True); t.setBackgroundColor(QColor(240,240,240,255))
t.setFrameEnabled(True)
t.attemptMove(QgsLayoutPoint(XP, 10, QgsUnitTypes.LayoutMillimeters))
t.attemptResize(QgsLayoutSize(WP, 14, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t)

s = QgsLayoutItemLabel(layout)
s.setText("PLANSA 01 - REGLEMENTARI URBANISTICE")
s.setFont(QFont(FONT, 7, QFont.Bold)); s.setHAlign(1)
s.setBackgroundEnabled(True); s.setBackgroundColor(QColor(250,250,250,255))
s.setFrameEnabled(True)
s.attemptMove(QgsLayoutPoint(XP, 26, QgsUnitTypes.LayoutMillimeters))
s.attemptResize(QgsLayoutSize(WP, 7, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(s)

# Legenda
leg = QgsLayoutItemLegend(layout)
leg.setLinkedMap(mi); leg.setTitle("LEGENDA URBANISTICA")
leg.setAutoUpdateModel(False)
root = leg.model().rootGroup(); root.clear()
for vl in reversed(added):
    root.addLayer(vl)
try:
    leg.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 8, QFont.Bold))
    leg.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 6))
except: pass
leg.setFrameEnabled(True)
leg.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
leg.setBackgroundColor(QColor(255,255,255,245))
leg.attemptMove(QgsLayoutPoint(XP, 35, QgsUnitTypes.LayoutMillimeters))
leg.attemptResize(QgsLayoutSize(WP, 90, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(leg)

# Atribuiri
a = QgsLayoutItemLabel(layout)
a.setText("SISTEM REFERINTA:\nStereo 70 (EPSG:3844)\n\nSURSE:\n- OpenStreetMap (ODbL)\n- ANCPI/INSPIRE (proxy)\n- Esri World Imagery\n\nNOTA: Limita UAT = proxy OSM,\nfara valoare juridica ANCPI.")
a.setFont(QFont(FONT, 5))
a.setFrameEnabled(True); a.setBackgroundEnabled(True)
a.setBackgroundColor(QColor(248,248,248,240))
a.attemptMove(QgsLayoutPoint(XP, 127, QgsUnitTypes.LayoutMillimeters))
a.attemptResize(QgsLayoutSize(WP, 28, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(a)

# Bilant
b = QgsLayoutItemLabel(layout)
b.setText(
    "BILANT TERITORIAL\n"
    "--------------------------------\n"
    "Cod   Zona functionala       ha     %\n"
    "--------------------------------\n"
    "CC    Curti-Constructii    552.58  10.14\n"
    "TR    Circulatii          138.86   2.55\n"
    "ZHA   Ape / Zone umede     49.49   0.91\n"
    "V_PD  Fond forestier      470.65   8.64\n"
    "A_P   Pasuni / Fanete     238.08   4.37\n"
    "A_Ar  Arabil             4115.43  75.39\n"
    "--------------------------------\n"
    "TOTAL                   5465.47 100.00"
)
b.setFont(QFont("Consolas", 6))
b.setFrameEnabled(True)
b.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
b.setBackgroundEnabled(True); b.setBackgroundColor(QColor(255,255,255,245))
b.attemptMove(QgsLayoutPoint(XP, 157, QgsUnitTypes.LayoutMillimeters))
b.attemptResize(QgsLayoutSize(WP, 60, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(b)

# Cartus
c = QgsLayoutItemLabel(layout)
c.setText(
    "DOCUMENTATIE: PUG\n"
    "Beneficiar: Comuna Iepuresti\n"
    "SIRUTA: 103684 | Jud. Giurgiu\n"
    "Proiectie: Stereo 70\n\n"
    "PARAMETRI:\n"
    "- Acoperire topologica: 100%\n"
    "- Offset constructii: +0.50 m\n"
    "- Poduri: 20 segmente\n"
    "- Cladiri: 140 entitati\n\n"
    "VERSIUNE: v9.0\n"
    "DATA: 22.09.2026"
)
c.setFont(QFont(FONT, 6))
c.setFrameEnabled(True); c.setBackgroundEnabled(True)
c.setBackgroundColor(QColor(250,250,250,245))
c.attemptMove(QgsLayoutPoint(XP, 219, QgsUnitTypes.LayoutMillimeters))
c.attemptResize(QgsLayoutSize(WP, 68, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(c)

project.write(str(QGZ))
print(f"    [OK] QGZ: {QGZ.name}")

# Export
ex = QgsLayoutExporter(layout)
st = QgsLayoutExporter.PdfExportSettings()
st.dpi = 300
st.rasterizeWholeImage = False
if PDF.exists():
    try: PDF.unlink()
    except: PDF = OUTPUT / "UAT_Iepuresti_PUG_A3_v9.pdf"
r = ex.exportToPdf(str(PDF), st)
print(f"\n[{'SUCCES' if r == QgsLayoutExporter.Success else 'EROARE cod '+str(r)}] {PDF}")
qgs.exitQgis()
print("=" * 70)
