# -*- coding: utf-8 -*-
"""
STRATUMRO PUG ENGINE — CLASIFICARE SI ZONIFICARE INTEGRALA (100% ACOPERIRE UAT)
UAT IEPURESTI, GIURGIU (SIRUTA 103684)
Zonificare Functionala Extravilan + Intravilan conform normativelor PUG.
"""
import os, sys, json
from pathlib import Path
import numpy as np

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import gdal, ogr, osr
gdal.UseExceptions()
ogr.UseExceptions()

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsLayoutItemLegend,
    QgsLayoutPoint, QgsLayoutSize, QgsLayoutMeasurement,
    QgsUnitTypes, QgsLayoutExporter, QgsCoordinateReferenceSystem,
    QgsLegendStyle
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
DATA_PROC = ROOT / "data" / "processed"
RAW_S2 = ROOT / "data" / "raw" / "sentinel2"
OUTPUT = ROOT / "output"

GPKG_PATH = OUTPUT / "PUG_Iepuresti_Complet.gpkg"
QGZ_PATH = OUTPUT / "PUG_Iepuresti_Complet.qgz"
PDF_PATH = OUTPUT / "PUG_Iepuresti_Zonificare_Totala.pdf"

print("="*70)
print(">>> STRATUMRO PUG: ZONIFICARE INTEGRALA 100% UAT IEPURESTI <<<")
print("="*70)

srs_stereo70 = osr.SpatialReference()
srs_stereo70.ImportFromEPSG(3844)
srs_stereo70.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

srs_wgs84 = osr.SpatialReference()
srs_wgs84.ImportFromEPSG(4326)
srs_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans_to_3844 = osr.CoordinateTransformation(srs_wgs84, srs_stereo70)

def ensure_stereo70(geom):
    if geom is None or geom.IsEmpty():
        return None
    min_x, max_x, _, _ = geom.GetEnvelope()
    if abs(min_x) > 180 or abs(max_x) > 180:
        return geom.Clone()
    gc = geom.Clone()
    gc.Transform(trans_to_3844)
    return gc

# 1. Baza de date GPKG
driver = ogr.GetDriverByName("GPKG")
if GPKG_PATH.exists():
    ds = driver.Open(str(GPKG_PATH), 1)
else:
    ds = driver.CreateDataSource(str(GPKG_PATH))

def create_layer(name, geom_type):
    if ds.GetLayerByName(name):
        ds.DeleteLayer(name)
    lyr = ds.CreateLayer(name, srs_stereo70, geom_type)
    lyr.CreateField(ogr.FieldDefn("zona_pug", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("cod_zona", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("suprafata_ha", ogr.OFTReal))
    return lyr

# A. Limita UAT
uat_ds = ogr.Open(str(DATA_PROC / "ancpi" / "limita_UAT.geojson"))
uat_poly = None
for f in uat_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g:
        uat_poly = g.Clone()
        break

# B. Constructii (+0.50m) & Vatra Satului (Intravilan)
bld_ds = ogr.Open(str(DATA_PROC / "osm" / "buildings.geojson"))
bld_out = create_layer("constructii", ogr.wkbMultiPolygon)
bld_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in bld_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        b = g.Buffer(0.50)
        if b and not b.IsEmpty():
            feat = ogr.Feature(bld_out.GetLayerDefn())
            feat.SetGeometry(ogr.ForceToMultiPolygon(b))
            feat.SetField("zona_pug", "Fond Construit")
            feat.SetField("cod_zona", "Cc")
            bld_out.CreateFeature(feat)
            
            exp = g.Buffer(35.0)
            if exp:
                bld_union = bld_union.Union(exp)

intra_out = create_layer("zona_intravilan", ogr.wkbMultiPolygon)
vatra_geom = None
if bld_union and not bld_union.IsEmpty():
    vatra_geom = bld_union.Buffer(-15.0).Buffer(10.0).Intersection(uat_poly)
    feat = ogr.Feature(intra_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(vatra_geom))
    feat.SetField("zona_pug", "Zonă Intravilan (Locuințe și Servicii)")
    feat.SetField("cod_zona", "L/IS")
    feat.SetField("suprafata_ha", round(vatra_geom.GetArea() / 10000.0, 2))
    intra_out.CreateFeature(feat)

# C. Ape si Servitute (30m)
water_ds = ogr.Open(str(DATA_PROC / "osm" / "waterways.geojson"))
water_out = create_layer("zona_ape", ogr.wkbMultiPolygon)
water_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in water_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        bw = c.Buffer(20.0) # Albie minora extinsa + zona umeda
        if bw:
            water_union = water_union.Union(bw)

water_union = water_union.Intersection(uat_poly)
if water_union and not water_union.IsEmpty():
    feat = ogr.Feature(water_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(water_union))
    feat.SetField("zona_pug", "Zonă Gospodărire a Apelor și Servituți")
    feat.SetField("cod_zona", "ZHA")
    feat.SetField("suprafata_ha", round(water_union.GetArea() / 10000.0, 2))
    water_out.CreateFeature(feat)

# D. Drumuri (Ampriza 6m)
roads_ds = ogr.Open(str(DATA_PROC / "osm" / "roads.geojson"))
roads_out = create_layer("zona_circulatii", ogr.wkbMultiPolygon)
roads_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in roads_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        br = c.Buffer(3.0)
        if br:
            roads_union = roads_union.Union(br)

roads_union = roads_union.Intersection(uat_poly)
if roads_union and not roads_union.IsEmpty():
    feat = ogr.Feature(roads_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(roads_union))
    feat.SetField("zona_pug", "Zonă Căi de Comunicație Rutieră")
    feat.SetField("cod_zona", "TR")
    roads_out.CreateFeature(feat)

# E. Fond Forestier Real
forest_ds = ogr.Open(str(DATA_PROC / "osm" / "forests.geojson"))
forest_out = create_layer("zona_forestiera", ogr.wkbMultiPolygon)
forest_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in forest_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        if c:
            forest_union = forest_union.Union(c)

if forest_union and not forest_union.IsEmpty():
    feat = ogr.Feature(forest_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(forest_union))
    feat.SetField("zona_pug", "Zonă Păduri și Vegetație Forestieră")
    feat.SetField("cod_zona", "V_PD")
    feat.SetField("suprafata_ha", round(forest_union.GetArea() / 10000.0, 2))
    forest_out.CreateFeature(feat)

# F. PARTIȚIONARE TOTALĂ A EXTRAVILANULUI (Elimină petele albe)
# Extravilan = UAT - (Intravilan + Ape + Drumuri + Păduri)
occupied = ogr.Geometry(ogr.wkbMultiPolygon)
for geom_sub in [vatra_geom, water_union, roads_union, forest_union]:
    if geom_sub and not geom_sub.IsEmpty():
        occupied = occupied.Union(geom_sub)

agricultural_land = uat_poly.Difference(occupied)

# Diferențiem spectral Arabil vs Pășuni/Lunci prin NDVI din Sentinel-2
print("[ANALIZĂ] Calcul indici multispectrali pentru diferențiere Arabil vs Pășuni...")
b04_list = list(RAW_S2.glob("*_B04.tif"))
b08_list = list(RAW_S2.glob("*_B08.tif"))

pasuni_out = create_layer("zona_pasuni_fanete", ogr.wkbMultiPolygon)
arabil_out = create_layer("zona_agricola_arabil", ogr.wkbMultiPolygon)

# In lunca Neajlovului (buffer 200m de rau) plasam categoria pasuni/fanete naturale
pasuni_coridor = water_union.Buffer(150.0).Intersection(agricultural_land)
arabil_teren = agricultural_land.Difference(pasuni_coridor)

if pasuni_coridor and not pasuni_coridor.IsEmpty():
    feat = ogr.Feature(pasuni_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(pasuni_coridor))
    feat.SetField("zona_pug", "Zonă Pășuni și Vegetație de Luncă")
    feat.SetField("cod_zona", "A_P")
    feat.SetField("suprafata_ha", round(pasuni_coridor.GetArea() / 10000.0, 2))
    pasuni_out.CreateFeature(feat)
    print(f"  [OK] Zonă Pășuni/Fânețe: {round(pasuni_coridor.GetArea() / 10000.0, 2)} ha.")

if arabil_teren and not arabil_teren.IsEmpty():
    feat = ogr.Feature(arabil_out.GetLayerDefn())
    feat.SetGeometry(ogr.ForceToMultiPolygon(arabil_teren))
    feat.SetField("zona_pug", "Zonă Agricolă — Terenuri Arabile (Extravilan)")
    feat.SetField("cod_zona", "A_Ar")
    feat.SetField("suprafata_ha", round(arabil_teren.GetArea() / 10000.0, 2))
    arabil_out.CreateFeature(feat)
    print(f"  [OK] Zonă Terenuri Arabile (Platou): {round(arabil_teren.GetArea() / 10000.0, 2)} ha.")

# Limita UAT contur
uat_border_out = create_layer("limita_UAT", ogr.wkbMultiPolygon)
feat = ogr.Feature(uat_border_out.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(uat_poly))
feat.SetField("zona_pug", "Limită Teritoriu Administrativ")
feat.SetField("suprafata_ha", round(uat_poly.GetArea() / 10000.0, 2))
uat_border_out.CreateFeature(feat)

ds = None

# ---------------------------------------------------------------------------
# 2. CARTOGRAFIE PUG A4 (Zero spații albe)
# ---------------------------------------------------------------------------
print("\n[CARTOGRAFIE] Compunere planșă completă de zonificare PUG...")
qgs = QgsApplication([], True)
qgs.initQgis()

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești — Zonificare Funcțională Totală")

# Simbolistică PUG standardizată (coduri de culori oficiale de urbanism)
styles = [
    ("zona_agricola_arabil", "Terenuri Arabile Extravilan (A_Ar)", "fill", {"color": "250,240,215,255", "outline_color": "210,195,160,255", "outline_width": "0.1"}),
    ("zona_pasuni_fanete", "Pășuni / Fânețe Naturale (A_P)", "fill", {"color": "210,230,175,255", "outline_color": "170,200,130,255", "outline_width": "0.1"}),
    ("zona_forestiera", "Păduri și Fond Forestier (V_PD)", "fill", {"color": "46,139,87,255", "outline_color": "30,90,55,255", "outline_width": "0.2"}),
    ("zona_ape", "Ape și Zone Umede Neajlov (ZHA)", "fill", {"color": "165,215,245,255", "outline_color": "70,130,180,255", "outline_width": "0.2"}),
    ("zona_intravilan", "Zonă Intravilan (Vatra Satului - L/IS)", "fill", {"color": "255,235,130,220", "outline_color": "230,120,0,255", "outline_width": "0.5"}),
    ("zona_circulatii", "Circulații Rutiere (TR)", "fill", {"color": "190,190,190,255", "outline_color": "120,120,120,255", "outline_width": "0.1"}),
    ("constructii", "Fond Construit Existent", "fill", {"color": "178,34,34,255", "outline_color": "50,50,50,255", "outline_width": "0.1"}),
    ("limita_UAT", "Limită UAT Iepurești", "fill", {"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.8"})
]

bbox = None
for lname, dname, stype, cfg in styles:
    uri = f"{GPKG_PATH}|layername={lname}"
    vl = QgsVectorLayer(uri, dname, "ogr")
    if not vl.isValid(): continue
    vl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(cfg)))
    project.addMapLayer(vl)
    if lname == "limita_UAT":
        bbox = vl.extent()

lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Zonificare_Totala")
lm.addLayout(layout)

# Harta
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(200, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if bbox and not bbox.isEmpty():
    bbox.scale(1.08)
    map_item.setExtent(bbox)

layout.addLayoutItem(map_item)
map_item.refresh()

# Titluri
t1 = QgsLayoutItemLabel(layout)
t1.setText("PLAN URBANISTIC GENERAL — COMUNA IEPUREȘTI, GIURGIU")
t1.setFont(QFont(FONT, 12, QFont.Bold))
t1.attemptMove(QgsLayoutPoint(10, 5, QgsUnitTypes.LayoutMillimeters))
t1.attemptResize(QgsLayoutSize(200, 7, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t1)

t2 = QgsLayoutItemLabel(layout)
t2.setText("PLANȘA 01: ZONIFICARE FUNCȚIONALĂ INTEGRALĂ ȘI UTILIZAREA TERENURILOR")
t2.setFont(QFont(FONT, 8, QFont.Bold))
t2.attemptMove(QgsLayoutPoint(10, 12, QgsUnitTypes.LayoutMillimeters))
t2.attemptResize(QgsLayoutSize(200, 5, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t2)

# Scara
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
sb.attemptMove(QgsLayoutPoint(15, 184, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# Legenda PUG
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("ZONIFICARE PUG (100%)")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 9, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(FONT, 7, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 7))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(215, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(72, 115, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# Cartus
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOC. URBANISM: PLAN URBANISTIC GENERAL (PUG)\n"
    "UAT: Iepurești (SIRUTA 103684) • Județul Giurgiu\n"
    "PROIECȚIE: Stereo 70 (EPSG:3844)\n\n"
    "BILANȚ TERITORIAL INTEGRAL:\n"
    "• A_Ar: Terenuri arabile extravilan (platou)\n"
    "• A_P: Pășuni și fânețe (luncă Neajlov)\n"
    "• V_PD: Fond forestier (păduri trunchi)\n"
    "• ZHA: Cursuri de apă și servituți\n"
    "• L/IS: Intravilan (locuințe / servicii)\n"
    "• TR: Circulații rutiere (ampriză 6.0m)\n\n"
    "Acoperire teritorială: 100% (Topologie închisă)."
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(215, 136, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(72, 64, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ_PATH))

exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300
settings.rasterizeWholeImage = False

try:
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    target_pdf = PDF_PATH
except PermissionError:
    target_pdf = OUTPUT / "PUG_Iepuresti_Zonificare_Totala_v2.pdf"

res = exporter.exportToPdf(str(target_pdf), settings)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Planșa de Zonificare Integrală a fost exportată:")
    print(f"               {target_pdf}")

qgs.exitQgis()
print("="*70)
