# -*- coding: utf-8 -*-
"""
STRATUMRO — GENERARE PLAN URBANISTIC GENERAL (PUG)
UAT IEPUREȘTI, JUDEȚUL GIURGIU (SIRUTA 103684)
Planșa: Reglementări Urbanistice, Zonificare Funcțională și Servituți
"""
import os, sys, json
from pathlib import Path
from datetime import datetime, timezone

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
from qgis.PyQt.QtCore import Qt

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
DATA_PROC = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
GPKG_PATH = OUTPUT / "PUG_Iepuresti.gpkg"
QGZ_PATH = OUTPUT / "PUG_Iepuresti.qgz"
PDF_PATH = OUTPUT / "PUG_Iepuresti_Reglementari.pdf"

print("="*70)
print(">>> STRATUMRO PUG ENGINE: UAT IEPUREȘTI (SIRUTA 103684) <<<")
print("="*70)

# Sistem de coordonate național Stereo 70 (EPSG:3844)
srs_stereo70 = osr.SpatialReference()
srs_stereo70.ImportFromEPSG(3844)
srs_stereo70.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

srs_wgs84 = osr.SpatialReference()
srs_wgs84.ImportFromEPSG(4326)
srs_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans_to_3844 = osr.CoordinateTransformation(srs_wgs84, srs_stereo70)

def ensure_stereo70(geom):
    """Asigura proiectia corecta in metri Stereo 70."""
    if geom is None or geom.IsEmpty():
        return None
    min_x, max_x, _, _ = geom.GetEnvelope()
    if abs(min_x) > 180 or abs(max_x) > 180:
        return geom.Clone()
    g_c = geom.Clone()
    g_c.Transform(trans_to_3844)
    return g_c

# ---------------------------------------------------------------------------
# 1. BAZA DE DATE GEOGRAFICĂ PUG (GeoPackage OGC)
# ---------------------------------------------------------------------------
print("\n[FAZA 1] Generare straturi vectoriale de reglementare PUG...")
driver = ogr.GetDriverByName("GPKG")
if GPKG_PATH.exists():
    ds = driver.Open(str(GPKG_PATH), 1)
else:
    ds = driver.CreateDataSource(str(GPKG_PATH))

def create_layer(name, geom_type):
    if ds.GetLayerByName(name):
        ds.DeleteLayer(name)
    lyr = ds.CreateLayer(name, srs_stereo70, geom_type)
    for field in ["categorie", "subcategorie", "regim_juridic", "sursa"]:
        lyr.CreateField(ogr.FieldDefn(field, ogr.OFTString))
    return lyr

# A. Limita UAT
uat_ds = ogr.Open(str(DATA_PROC / "ancpi" / "limita_UAT.geojson"))
uat_lyr_out = create_layer("limita_UAT", ogr.wkbMultiPolygon)
uat_geom = None

for f in uat_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g:
        uat_geom = g.Clone()
        out_f = ogr.Feature(uat_lyr_out.GetLayerDefn())
        out_f.SetGeometry(ogr.ForceToMultiPolygon(g))
        out_f.SetField("categorie", "Limită Administrativ-Teritorială")
        out_f.SetField("regim_juridic", "REFERENCE (OSM admin_level=8)")
        uat_lyr_out.CreateFeature(out_f)
print("  [OK] Limită UAT integrată.")

# B. Păduri reale (Fond Forestier)
forest_ds = ogr.Open(str(DATA_PROC / "osm" / "forests.geojson"))
forest_out = create_layer("zona_fond_forestier", ogr.wkbMultiPolygon)
forest_count = 0
for f in forest_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_geom and g.Intersects(uat_geom):
        c = g.Intersection(uat_geom)
        if not c.IsEmpty():
            out_f = ogr.Feature(forest_out.GetLayerDefn())
            out_f.SetGeometry(ogr.ForceToMultiPolygon(c))
            out_f.SetField("categorie", "Zonă Spații Verzi și Păduri")
            out_f.SetField("subcategorie", "Fond Forestier Existent")
            forest_out.CreateFeature(out_f)
            forest_count += 1
print(f"  [OK] Fond forestier real: {forest_count} corpuri de pădure (eliminat zgomot agricol).")

# C. Construcții (+0.50m) și sinteză Vatră Sat (Intravilan)
bld_ds = ogr.Open(str(DATA_PROC / "osm" / "buildings.geojson"))
bld_out = create_layer("constructii", ogr.wkbMultiPolygon)
bld_union = ogr.Geometry(ogr.wkbMultiPolygon)
bld_count = 0

for f in bld_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_geom and g.Intersects(uat_geom):
        b = g.Buffer(0.50)
        if b and not b.IsEmpty():
            out_f = ogr.Feature(bld_out.GetLayerDefn())
            out_f.SetGeometry(ogr.ForceToMultiPolygon(b))
            out_f.SetField("categorie", "Fond Construit")
            out_f.SetField("subcategorie", "Acoperiș + Offset 0.50m")
            bld_out.CreateFeature(out_f)
            bld_count += 1
            
            # Colectare nuclee construite
            exp = g.Buffer(35.0)
            if exp:
                bld_union = bld_union.Union(exp)
print(f"  [OK] Fond construit: {bld_count} clădiri reglementate.")

# D. Intravilan Propus / Vatra Satului
intra_out = create_layer("limita_intravilan", ogr.wkbMultiPolygon)
if bld_union and not bld_union.IsEmpty():
    vatra = bld_union.Buffer(-15.0).Buffer(10.0).Intersection(uat_geom)
    if not vatra.IsEmpty():
        out_f = ogr.Feature(intra_out.GetLayerDefn())
        out_f.SetGeometry(ogr.ForceToMultiPolygon(vatra))
        out_f.SetField("categorie", "Zonă Intravilan (Vatra Satului)")
        out_f.SetField("regim_juridic", "Delimitare funcțională PUG")
        intra_out.CreateFeature(out_f)
        ha = round(vatra.GetArea() / 10000.0, 2)
        print(f"  [OK] Intravilan funcțional sintetizat: {ha} ha.")

# E. Cursuri de apă și Servitute Hidrografică (30m - Legea Apelor 107/1996)
water_ds = ogr.Open(str(DATA_PROC / "osm" / "waterways.geojson"))
water_out = create_layer("cursuri_apa", ogr.wkbMultiLineString)
serv_out = create_layer("zona_protectie_ape", ogr.wkbMultiPolygon)

for f in water_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_geom and g.Intersects(uat_geom):
        c = g.Intersection(uat_geom)
        if not c.IsEmpty():
            # Ax râu
            out_w = ogr.Feature(water_out.GetLayerDefn())
            out_w.SetGeometry(ogr.ForceToMultiLineString(c))
            out_w.SetField("categorie", "Rețea Hidrografică")
            water_out.CreateFeature(out_w)
            # Servitute 30m
            b_water = c.Buffer(30.0).Intersection(uat_geom)
            if not b_water.IsEmpty():
                out_s = ogr.Feature(serv_out.GetLayerDefn())
                out_s.SetGeometry(ogr.ForceToMultiPolygon(b_water))
                out_s.SetField("categorie", "Zonă de Protecție Sanitară și Servitute")
                out_s.SetField("regim_juridic", "Non-Aedificandi (Legea 107/1996)")
                serv_out.CreateFeature(out_s)
print("  [OK] Rețea hidrografică și servitute de apă (30m) calculate.")

# F. Drumuri (Ampriză 6m și Axe)
roads_ds = ogr.Open(str(DATA_PROC / "osm" / "roads.geojson"))
roads_ax_out = create_layer("drumuri_ax", ogr.wkbMultiLineString)
roads_poly_out = create_layer("drumuri_ampriza", ogr.wkbMultiPolygon)

for f in roads_ds.GetLayer(0):
    g = ensure_stereo70(f.GetGeometryRef())
    if g and uat_geom and g.Intersects(uat_geom):
        c = g.Intersection(uat_geom)
        if not c.IsEmpty():
            out_ax = ogr.Feature(roads_ax_out.GetLayerDefn())
            out_ax.SetGeometry(ogr.ForceToMultiLineString(c))
            out_ax.SetField("categorie", "Circulații Rutiere")
            roads_ax_out.CreateFeature(out_ax)
            
            b_road = c.Buffer(3.0)
            if not b_road.IsEmpty():
                out_p = ogr.Feature(roads_poly_out.GetLayerDefn())
                out_p.SetGeometry(ogr.ForceToMultiPolygon(b_road))
                out_p.SetField("categorie", "Ampriză Străzi (Profil 6m)")
                roads_poly_out.CreateFeature(out_p)
print("  [OK] Rețea de căi de comunicație și amprize generate.")

# G. Poduri
bridges_path = DATA_PROC / "osm" / "bridges.geojson"
bridges_out = create_layer("poduri", ogr.wkbMultiLineString)
if bridges_path.exists():
    br_ds = ogr.Open(str(bridges_path))
    for f in br_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g and uat_geom and g.Intersects(uat_geom):
            out_b = ogr.Feature(bridges_out.GetLayerDefn())
            out_b.SetGeometry(ogr.ForceToMultiLineString(g))
            out_b.SetField("categorie", "Lucrări de Artă (Poduri)")
            bridges_out.CreateFeature(out_b)
print("  [OK] Lucrări de artă (poduri) integrate.")

ds = None

# ---------------------------------------------------------------------------
# 2. CARTOGRAFIE & REGLEMENTĂRI URBANISTICE (QGIS LAYOUT A4)
# ---------------------------------------------------------------------------
print("\n[FAZA 2] Configurare planșă cartografică PUG la standard de tipar...")
qgs = QgsApplication([], True)
qgs.initQgis()

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești — Reglementări Urbanistice")

# Stilizare normativă PUG
layers_style = [
    ("zona_fond_forestier", "Fond Forestier / Păduri", "fill", {"color": "34,139,34,160", "outline_color": "0,100,0,255", "outline_width": "0.2"}),
    ("zona_protectie_ape", "Zonă Servitute Ape (30m - Non-Aedificandi)", "fill", {"color": "176,224,230,120", "outline_color": "70,130,180,255", "outline_width": "0.3", "outline_style": "dash"}),
    ("limita_intravilan", "Zonă Intravilan (Vatra Satului)", "fill", {"color": "255,215,0,40", "outline_color": "255,140,0,255", "outline_width": "0.6", "outline_style": "dash"}),
    ("drumuri_ampriza", "Ampriză Circulații Rutiere (6m)", "fill", {"color": "211,211,211,220", "outline_color": "128,128,128,255", "outline_width": "0.1"}),
    ("constructii", "Fond Construit Existent (+0.50m)", "fill", {"color": "165,42,42,230", "outline_color": "30,30,30,255", "outline_width": "0.15"}),
    ("cursuri_apa", "Rețea Hidrografică (Râul Neajlov)", "line", {"color": "0,119,190,255", "width": "0.6"}),
    ("drumuri_ax", "Ax Drumuri Publice", "line", {"color": "60,60,60,255", "width": "0.5"}),
    ("poduri", "Poduri / Pasaje", "bridge", {}),
    ("limita_UAT", "Limită Teritoriu Administrativ (UAT)", "fill", {"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.8"})
]

bbox_target = None
for lname, dname, stype, cfg in layers_style:
    uri = f"{GPKG_PATH}|layername={lname}"
    vl = QgsVectorLayer(uri, dname, "ogr")
    if not vl.isValid(): continue
    
    if stype == "bridge":
        sym = QgsLineSymbol()
        sl1 = QgsSimpleLineSymbolLayer(QColor(0, 0, 0), 2.0)
        sl2 = QgsSimpleLineSymbolLayer(QColor(255, 255, 255), 1.2)
        sym.changeSymbolLayer(0, sl1)
        sym.appendSymbolLayer(sl2)
        vl.setRenderer(QgsSingleSymbolRenderer(sym))
    elif stype == "fill":
        vl.setRenderer(QgsSingleSymbolRenderer(QgsFillSymbol.createSimple(cfg)))
    elif stype == "line":
        vl.setRenderer(QgsSingleSymbolRenderer(QgsLineSymbol.createSimple(cfg)))
        
    project.addMapLayer(vl)
    if lname == "limita_UAT":
        bbox_target = vl.extent()

# Curatare layout-uri
lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Planșa_PUG_A4")
lm.addLayout(layout)

# 1. Hartă principală
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(200, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if bbox_target and not bbox_target.isEmpty():
    bbox_target.scale(1.08)
    map_item.setExtent(bbox_target)

layout.addLayoutItem(map_item)
map_item.refresh()

# 2. Titlu Oficial PUG
title = QgsLayoutItemLabel(layout)
title.setText("PLAN URBANISTIC GENERAL — COMUNA IEPUREȘTI, JUD. GIURGIU")
title.setFont(QFont(FONT, 12, QFont.Bold))
title.attemptMove(QgsLayoutPoint(10, 5, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(200, 7, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

subtitle = QgsLayoutItemLabel(layout)
subtitle.setText("PLANȘA 02: REGLEMENTĂRI URBANISTICE, ZONIFICARE ȘI SERVITUȚI")
subtitle.setFont(QFont(FONT, 8, QFont.Bold))
subtitle.attemptMove(QgsLayoutPoint(10, 12, QgsUnitTypes.LayoutMillimeters))
subtitle.attemptResize(QgsLayoutSize(200, 5, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(subtitle)

# 3. Scară grafică
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
sb.attemptMove(QgsLayoutPoint(15, 184, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# 4. Legendă PUG
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ URBANISTICĂ")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 9, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(FONT, 7, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 7))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(215, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(72, 110, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 5. Cartuș Tehnic de Urbanism
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOC. URBANISM: PLAN URBANISTIC GENERAL (PUG)\n"
    "BENEFICIAR: Comuna Iepurești (SIRUTA 103684)\n"
    "PROIECȚIE: Stereo 70 (EPSG:3844)\n\n"
    "REGLEMENTĂRI APLICATE:\n"
    "• Intravilan: Vatră sat delimitată funcțional\n"
    "• Ape: Servitute 30m Non-Aedificandi (L107/1996)\n"
    "• Clădiri: Contur cu offset exterior +0.50m\n"
    "• Circulații: Ampriză drumuri profil 6.0m\n"
    "• Fond forestier: Corpuri de pădure reale OSM\n\n"
    "NOTĂ: Bază geospațială generată automat.\n"
    "Nu ține loc de planșă avizată de comisia de urbanism."
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(215, 131, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(72, 69, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ_PATH))
print(f"  [OK] Proiect PUG salvat: {QGZ_PATH}")

# Export PDF 300 DPI
exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300
settings.rasterizeWholeImage = False

try:
    if PDF_PATH.exists():
        PDF_PATH.unlink()
    target_pdf = PDF_PATH
except PermissionError:
    target_pdf = OUTPUT / "PUG_Iepuresti_Reglementari_v2.pdf"

res = exporter.exportToPdf(str(target_pdf), settings)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Planșa PUG a fost exportată la standard de tipar:")
    print(f"               {target_pdf}")
else:
    print(f"\n[EROARE] Exportul PDF a eșuat: {res}")

qgs.exitQgis()
print("="*70)
