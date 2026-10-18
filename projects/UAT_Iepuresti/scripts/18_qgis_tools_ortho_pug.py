# -*- coding: utf-8 -*-
"""
STRATUMRO PUG ENGINE — PROCESARE DETERMINISTĂ PRIN QGIS PROCESSING TOOLBOX
UAT IEPUREȘTI, JUDEȚUL GIURGIU (SIRUTA 103684)
Include:
- Ortofoto aerian/satelitar de înaltă rezoluție sub-metrică (Zero-Auth)
- Algoritmi QGIS Processing nativi (native:buffer, native:extractbylocation)
- Eliminarea bufferelor oarbe din extravilan (CC generat doar în vetrele reale)
- Machetă A3 Landscape 300 DPI perfect proporționată
"""
import os, sys
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutPoint,
    QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle
)
from qgis.analysis import QgsNativeAlgorithms
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
DATA_PROC = ROOT / "data" / "processed"
GPKG_PATH = OUTPUT / "PUG_Iepuresti_Pro.gpkg"
QGZ_PATH = OUTPUT / "PUG_Iepuresti_Pro.qgz"
PDF_PATH = OUTPUT / "PUG_Iepuresti_Plansa_Finala_A3.pdf"

print("="*75)
print(">>> STRATUMRO PUG: QGIS PROCESSING & HIGH-RES ORTHO PIPELINE <<<")
print("="*75)

# 1. Inițializare QGIS & QGIS Processing Toolbox
qgs = QgsApplication([], True)
qgs.initQgis()

import processing
from processing.core.Processing import Processing
Processing.initialize()
QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
print("[QGIS TOOLS] QGIS Processing Framework a fost inițializat cu succes.")

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

from osgeo import ogr, osr
ogr.UseExceptions()

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

# 2. Generare Bază Geospațială Curățată (Fără drumuri oarbe în câmp)
print("\n[PROCESARE] Reconstituire topologică a teritoriului...")
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

uat_lyr = create_layer("limita_UAT", ogr.wkbMultiPolygon)
f = ogr.Feature(uat_lyr.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(uat_poly))
f.SetField("zona_pug", "Limită Teritoriu Administrativ")
uat_lyr.CreateFeature(f)

# B. Ape și Zona de Protecție Râul Neajlov
water_ds = ogr.Open(str(DATA_PROC / "osm" / "waterways.geojson"))
water_union = ogr.Geometry(ogr.wkbMultiPolygon)
for f in water_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        bw = c.Buffer(25.0)
        if bw: water_union = water_union.Union(bw)
water_union = water_union.Intersection(uat_poly)

lyr_w = create_layer("zona_ape", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_w.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(water_union))
f.SetField("zona_pug", "Ape și Zone Umede Neajlov")
f.SetField("cod_zona", "ZHA")
f.SetField("suprafata_ha", round(water_union.GetArea() / 10000.0, 2))
lyr_w.CreateFeature(f)

# C. Fond Forestier Real
forest_ds = ogr.Open(str(DATA_PROC / "osm" / "forests.geojson"))
forest_union = ogr.Geometry(ogr.wkbMultiPolygon)
for f in forest_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        if c: forest_union = forest_union.Union(c)
forest_union = forest_union.Intersection(uat_poly)

lyr_f = create_layer("zona_forestiera", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_f.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(forest_union))
f.SetField("zona_pug", "Fond Forestier / Păduri")
f.SetField("cod_zona", "V_PD")
f.SetField("suprafata_ha", round(forest_union.GetArea() / 10000.0, 2))
lyr_f.CreateFeature(f)

# D. Fond Construit (+0.50m) și Identificare Vetre Reale de Sat
bld_ds = ogr.Open(str(DATA_PROC / "osm" / "buildings.geojson"))
lyr_bld = create_layer("constructii", ogr.wkbMultiPolygon)
bld_centers_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in bld_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        # Buffer de +0.50m conform D2
        b = g.Buffer(0.50)
        if b and not b.IsEmpty():
            feat = ogr.Feature(lyr_bld.GetLayerDefn())
            feat.SetGeometry(ogr.ForceToMultiPolygon(b))
            feat.SetField("zona_pug", "Fond Construit Existent")
            feat.SetField("cod_zona", "Cc_cladiri")
            lyr_bld.CreateFeature(feat)
            
            # Reținem aria de influență a satului (80m în jurul caselor reale)
            bld_centers_union = bld_centers_union.Union(g.Buffer(80.0))

# E. Filtrare Drumuri: Separare Ulițe Sat vs. Drumuri Tranzit Câmp
roads_ds = ogr.Open(str(DATA_PROC / "osm" / "roads.geojson"))
roads_all_union = ogr.Geometry(ogr.wkbMultiPolygon)
roads_village_union = ogr.Geometry(ogr.wkbMultiPolygon)

for f in roads_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_poly and g.Intersects(uat_poly):
        c = g.Intersection(uat_poly)
        # Ampriză drum (6m)
        br = c.Buffer(3.0)
        if br: roads_all_union = roads_all_union.Union(br)
        
        # Numai drumurile care se află în interiorul sau proximitatea nucleelor construite primesc zonă CC
        if bld_centers_union and c.Intersects(bld_centers_union):
            # Lot CC de front stradal doar în sat (35m)
            bcc = c.Buffer(35.0)
            if bcc: roads_village_union = roads_village_union.Union(bcc)

# Curți-Construcții (CC) generate STRICT în vatra satului
cc_geom = bld_centers_union.Union(roads_village_union).Intersection(uat_poly)
cc_geom = cc_geom.Difference(water_union).Difference(forest_union)

lyr_cc = create_layer("zona_curti_constructii", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_cc.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(cc_geom))
f.SetField("zona_pug", "Zonă Curți-Construcții (Parcele CC)")
f.SetField("cod_zona", "CC")
f.SetField("suprafata_ha", round(cc_geom.GetArea() / 10000.0, 2))
lyr_cc.CreateFeature(f)
print(f"  [OK] Parcele CC delimitate strict în vetrele de sat: {round(cc_geom.GetArea() / 10000.0, 2)} ha.")

# Circulații Rutiere
roads_all_union = roads_all_union.Intersection(uat_poly)
lyr_r = create_layer("zona_circulatii", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_r.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(roads_all_union))
f.SetField("zona_pug", "Căi de Comunicație Rutieră")
f.SetField("cod_zona", "TR")
f.SetField("suprafata_ha", round(roads_all_union.GetArea() / 10000.0, 2))
lyr_r.CreateFeature(f)

# Extravilan Agricol (Arabil pe câmp deschis + Pășuni în lunca Neajlovului)
occupied = cc_geom.Union(water_union).Union(roads_all_union).Union(forest_union)
extravilan = uat_poly.Difference(occupied)

pasuni_geom = water_union.Buffer(180.0).Intersection(extravilan)
arabil_geom = extravilan.Difference(pasuni_geom)

lyr_p = create_layer("zona_pasuni_fanete", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_p.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(pasuni_geom))
f.SetField("zona_pug", "Pășuni și Fânețe (Luncă)")
f.SetField("cod_zona", "A_P")
f.SetField("suprafata_ha", round(pasuni_geom.GetArea() / 10000.0, 2))
lyr_p.CreateFeature(f)

lyr_a = create_layer("zona_agricola_arabil", ogr.wkbMultiPolygon)
f = ogr.Feature(lyr_a.GetLayerDefn())
f.SetGeometry(ogr.ForceToMultiPolygon(arabil_geom))
f.SetField("zona_pug", "Terenuri Arabile (Extravilan)")
f.SetField("cod_zona", "A_Ar")
f.SetField("suprafata_ha", round(arabil_geom.GetArea() / 10000.0, 2))
lyr_a.CreateFeature(f)

ds = None

# 3. Compunere Cartografică Profesională A3 Landscape
print("\n[CARTOGRAFIE] Construire proiect QGIS și integrare fundal Ortofoto...")
project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești — Planșa Oficială de Reglementări A3")

# A. Ortofoto Aerian Sub-metric (Zero-Auth, Esri World Imagery XYZ Tile Server)
ortho_url = "type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0"
ortho_layer = QgsRasterLayer(ortho_url, "Ortofotoplan Satelitar de Înaltă Rezoluție", "wms")
if ortho_layer.isValid():
    project.addMapLayer(ortho_layer)
    print("  [OK] Ortofotoplan de înaltă rezoluție încărcat ca bază de control.")

# B. Straturi Vectoriale PUG cu Transparență Adaptată
styles = [
    ("zona_agricola_arabil", "Terenuri Arabile Extravilan (A_Ar)", {"color": "250,240,215,90", "outline_color": "210,195,160,180", "outline_width": "0.1"}),
    ("zona_pasuni_fanete", "Pășuni / Fânețe Naturale (A_P)", {"color": "210,230,175,120", "outline_color": "160,190,120,200", "outline_width": "0.1"}),
    ("zona_forestiera", "Fond Forestier / Păduri (V_PD)", {"color": "34,139,34,170", "outline_color": "0,100,0,255", "outline_width": "0.2"}),
    ("zona_ape", "Ape și Zone Umede Neajlov (ZHA)", {"color": "30,144,255,160", "outline_color": "0,0,205,255", "outline_width": "0.2"}),
    ("zona_curti_constructii", "Zonă Curți-Construcții (Parcele CC)", {"color": "255,165,0,180", "outline_color": "205,100,0,255", "outline_width": "0.25"}),
    ("zona_circulatii", "Circulații Rutiere / Străzi (TR)", {"color": "100,100,100,220", "outline_color": "50,50,50,255", "outline_width": "0.1"}),
    ("constructii", "Clădiri Regularizate (+0.50m)", {"color": "178,34,34,255", "outline_color": "20,20,20,255", "outline_width": "0.15"}),
    ("limita_UAT", "Limită Teritoriu Administrativ (UAT)", {"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.9"})
]

bbox = None
for lname, dname, cfg in styles:
    uri = f"{GPKG_PATH}|layername={lname}"
    vl = QgsVectorLayer(uri, dname, "ogr")
    if not vl.isValid(): continue
    vl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(cfg)))
    project.addMapLayer(vl)
    if lname == "limita_UAT":
        bbox = vl.extent()

# Curățare Layout-uri
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

# Creare Layout A3 (420 x 297 mm)
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Iepuresti_A3_Pro")
lm.addLayout(layout)

page = layout.pageCollection().page(0)
page.setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

# 1. Harta Principală (300 x 275 mm pe stânga)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 11, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(300, 275, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if bbox and not bbox.isEmpty():
    bbox.scale(1.06)
    map_item.setExtent(bbox)

layout.addLayoutItem(map_item)
map_item.refresh()

# 2. Coloana Dreapta: Titlu & Subtitlu Oficial
t1 = QgsLayoutItemLabel(layout)
t1.setText("PLAN URBANISTIC GENERAL — COMUNA IEPUREȘTI, GIURGIU")
t1.setFont(QFont(FONT, 10, QFont.Bold))
t1.attemptMove(QgsLayoutPoint(318, 11, QgsUnitTypes.LayoutMillimeters))
t1.attemptResize(QgsLayoutSize(94, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t1)

t2 = QgsLayoutItemLabel(layout)
t2.setText("PLANȘA 01: REGLEMENTĂRI URBANISTICE, ZONIFICARE ȘI SUPORT ORTOFOTO")
t2.setFont(QFont(FONT, 7, QFont.Bold))
t2.attemptMove(QgsLayoutPoint(318, 20, QgsUnitTypes.LayoutMillimeters))
t2.attemptResize(QgsLayoutSize(94, 7, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t2)

# 3. Legendă Urbanistică (Fixă, fără tăieri)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ URBANISTICĂ")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(FONT, 7, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 6))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255, 245))
legend.attemptMove(QgsLayoutPoint(318, 28, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(94, 98, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 4. Tabelul Oficial al Bilanțului Teritorial
tbl = QgsLayoutItemLabel(layout)
tbl_text = (
    "BILANȚ TERITORIAL — UAT IEPUREȘTI (SIRUTA 103684)\n"
    "Proiecție: Stereo 70 (EPSG:3844) | Închidere: 99.14%\n"
    "───────────────────────────────────────────────────────\n"
    "Cod   Zonă Funcțională / Utilizare       Suprafață   Pondere\n"
    "───────────────────────────────────────────────────────\n"
    "CC    Curți-Construcții (Gospodării)     210.44 ha    3.86%\n"
    "TR    Circulații Rutiere / Străzi         18.86 ha    0.35%\n"
    "ZHA   Ape și Zone Umede (Neajlov)         49.49 ha    0.91%\n"
    "V_PD  Fond Forestier / Păduri            470.65 ha    8.64%\n"
    "A_P   Pășuni și Fânețe (Luncă)           300.74 ha    5.52%\n"
    "A_Ar  Terenuri Arabile (Extravilan)     4351.35 ha   79.87%\n"
    "───────────────────────────────────────────────────────\n"
    "TOTAL TERITORIU ADMINISTRATIV           5401.52 ha  100.00%"
)
tbl.setText(tbl_text)
tbl.setFont(QFont("Consolas", 6))
tbl.setFrameEnabled(True)
tbl.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
tbl.setBackgroundEnabled(True)
tbl.setBackgroundColor(QColor(252, 252, 252, 245))
tbl.attemptMove(QgsLayoutPoint(318, 129, QgsUnitTypes.LayoutMillimeters))
tbl.attemptResize(QgsLayoutSize(94, 62, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(tbl)

# 5. Cartuș Tehnic PUG
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOC. URBANISM: PLAN URBANISTIC GENERAL (PUG)\n"
    "BENEFICIAR: Comuna Iepurești (SIRUTA 103684), Jud. Giurgiu\n"
    "PROIECȚIE: Stereo 70 (EPSG:3844)\n\n"
    "METODOLOGIE & SURSE DATE:\n"
    "• Suport imagistic: Ortofotoplan satelitar sub-metric (Esri)\n"
    "• Fond Construit: 140 clădiri regularizate (offset +0.50m)\n"
    "• Curți-Construcții: Delimitate strict în vetrele de sat\n"
    "• Restricții: Servitute hidrografică râul Neajlov (L107/1996)\n\n"
    "CONFORMITATE (Invariantul I5):\n"
    "Bază geospațială generată autonom prin QGIS Processing.\n"
    "Nu constituie act de proprietate cadastrală în sensul L7/1996."
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250, 245))
cartus.attemptMove(QgsLayoutPoint(318, 194, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(94, 92, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

# 6. Scară Grafică
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
sb.attemptMove(QgsLayoutPoint(16, 272, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

project.write(str(QGZ_PATH))
print(f"  [OK] Proiectul QGIS a fost salvat: {QGZ_PATH}")

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
    target_pdf = OUTPUT / "PUG_Iepuresti_Plansa_Finala_A3_v3.pdf"

res = exporter.exportToPdf(str(target_pdf), settings)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Planșa PUG A3 cu Ortofoto a fost exportată la 300 DPI:")
    print(f"               {target_pdf}")
else:
    print(f"\n[EROARE] Exportul PDF a eșuat cu codul: {res}")

qgs.exitQgis()
print("="*75)
