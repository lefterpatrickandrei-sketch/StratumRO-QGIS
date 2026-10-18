# -*- coding: utf-8 -*-
"""Refactorizare cartografica avansata: decupare la UAT, mascare satelit, legenda, scara si layout profesional."""
import os, sys, json
from datetime import datetime, timezone
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from osgeo import gdal, ogr
gdal.UseExceptions()
ogr.UseExceptions()

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSimpleFillSymbolLayer, QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer, QgsPrintLayout, QgsLayoutItemMap,
    QgsLayoutItemLabel, QgsLayoutItemScaleBar, QgsLayoutItemLegend,
    QgsLayoutPoint, QgsLayoutSize, QgsUnitTypes, QgsLayoutExporter,
    QgsCoordinateReferenceSystem
)
from qgis.PyQt.QtGui import QColor, QFont

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
DATA_PROC = ROOT / "data" / "processed"
GPKG_PATH = OUTPUT / "UAT_Iepuresti.gpkg"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT / "harta_Iepuresti.pdf"
S2_WARPED = OUTPUT / "sentinel2_stereo70_rgb.tif"
S2_MASKED = OUTPUT / "sentinel2_uat_masked.tif"

print("1. Decupare geometrica vectori la poligonul limita_UAT...")
ds = ogr.Open(str(GPKG_PATH), 1)
uat_lyr = ds.GetLayerByName("limita_UAT")
uat_feat = uat_lyr.GetNextFeature()
uat_geom = uat_feat.GetGeometryRef().Clone()

layers_to_clip = ["constructii", "drumuri_poligon", "drumuri_ax", "cursuri_apa", "paduri", "poduri"]

for lyr_name in layers_to_clip:
    lyr = ds.GetLayerByName(lyr_name)
    if lyr is None: continue
    
    target_type = ogr.GT_Flatten(lyr.GetLayerDefn().GetGeomType())
    features_to_keep = []
    lyr.ResetReading()
    
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom and geom.Intersects(uat_geom):
            clipped = geom.Intersection(uat_geom)
            if clipped and not clipped.IsEmpty():
                # Pastrare coerenta tip geometrie
                c_type = ogr.GT_Flatten(clipped.GetGeometryType())
                if target_type in (ogr.wkbMultiPolygon, ogr.wkbPolygon) and c_type in (ogr.wkbPolygon, ogr.wkbMultiPolygon):
                    clipped = ogr.ForceToMultiPolygon(clipped)
                elif target_type in (ogr.wkbMultiLineString, ogr.wkbLineString) and c_type in (ogr.wkbLineString, ogr.wkbMultiLineString):
                    clipped = ogr.ForceToMultiLineString(clipped)
                
                new_f = ogr.Feature(lyr.GetLayerDefn())
                new_f.SetGeometry(clipped)
                for i in range(feat.GetFieldCount()):
                    new_f.SetField(i, feat.GetField(i))
                features_to_keep.append(new_f)

    lyr.StartTransaction()
    for fid in [f.GetFID() for f in lyr]:
        lyr.DeleteFeature(fid)
    for nf in features_to_keep:
        lyr.CreateFeature(nf)
    lyr.CommitTransaction()
    print(f"   -> Stratul {lyr_name}: {len(features_to_keep)} entitati decupate strict pe UAT.")

ds = None

print("2. Mascare imagine Sentinel-2 pe conturul UAT...")
if S2_WARPED.exists():
    gdal.Warp(
        str(S2_MASKED),
        str(S2_WARPED),
        cutlineDSName=str(DATA_PROC / "ancpi" / "limita_UAT.geojson"),
        cropToCutline=True,
        dstNodata=0
    )
    print("   -> Imagine Sentinel-2 decupata pe masca UAT cu succes.")

print("3. Configurare proiect si simbolizare avansata in QGIS...")
qgs = QgsApplication([], False)
qgs.initQgis()

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("UAT Iepurești (Giurgiu) — Plan Cartografic")

# Incarcare raster Sentinel-2 decupat (daca exista) la baza
if S2_MASKED.exists():
    rlayer = QgsRasterLayer(str(S2_MASKED), "Imagine Satelitară Sentinel-2 (RGB)")
    if rlayer.isValid():
        project.addMapLayer(rlayer)

# Stilizare vectori conform specificatiei G7
styles = {
    "paduri": {"type": "fill", "color": "46,139,87,140", "border": "0,100,0,255", "width": "0.3"},
    "drumuri_poligon": {"type": "fill", "color": "220,220,220,180", "border": "128,128,128,255", "width": "0.15"},
    "constructii": {"type": "fill", "color": "178,34,34,220", "border": "0,0,0,255", "width": "0.2"},
    "cursuri_apa": {"type": "line", "color": "30,144,255,255", "width": "0.6"},
    "drumuri_ax": {"type": "line", "color": "50,50,50,255", "width": "0.8"},
    "limita_UAT": {"type": "fill", "color": "0,0,0,0", "border": "0,0,0,255", "width": "0.6"}
}

order = ["paduri", "drumuri_poligon", "constructii", "cursuri_apa", "drumuri_ax", "poduri", "limita_UAT"]
extent_layer = None

for name in order:
    uri = f"{GPKG_PATH}|layername={name}"
    vlayer = QgsVectorLayer(uri, name.replace("_", " ").title(), "ogr")
    if not vlayer.isValid(): continue
    
    if name == "poduri":
        sym = QgsLineSymbol()
        sl1 = QgsSimpleLineSymbolLayer(QColor(0, 0, 0), 2.0)
        sl2 = QgsSimpleLineSymbolLayer(QColor(255, 255, 255), 1.2)
        sym.changeSymbolLayer(0, sl1)
        sym.appendSymbolLayer(sl2)
        vlayer.setRenderer(QgsSingleSymbolRenderer(sym))
    elif name in styles:
        st = styles[name]
        if st["type"] == "fill":
            sym = QgsFillSymbol.createSimple({"color": st["color"], "outline_color": st["border"], "outline_width": st["width"]})
        else:
            sym = QgsLineSymbol.createSimple({"color": st["color"], "width": st["width"]})
        vlayer.setRenderer(QgsSingleSymbolRenderer(sym))
        
    project.addMapLayer(vlayer)
    if name == "limita_UAT":
        extent_layer = vlayer

project.write(str(QGZ_PATH))

print("4. Generare macheta A4 300 DPI (Titlu, Legenda, Scara, Cartus)...")
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Harta_Oficiala_A4")

# Harta centrala
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 22, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(210, 178, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)

if extent_layer and extent_layer.featureCount() > 0:
    bbox = extent_layer.extent()
    bbox.scale(1.06)
    map_item.setExtent(bbox)

layout.addLayoutItem(map_item)

# Scara Grafica
scalebar = QgsLayoutItemScaleBar(layout)
scalebar.setStyle("Single Box")
scalebar.setLinkedMap(map_item)
scalebar.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
scalebar.setNumberOfSegments(3)
scalebar.setUnits(QgsUnitTypes.DistanceKilometers)
scalebar.setUnitLabel("km")
scalebar.attemptMove(QgsLayoutPoint(15, 185, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(scalebar)

# Legenda
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("Legendă")
legend.setAutoUpdateModel(True)
legend.attemptMove(QgsLayoutPoint(225, 22, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(62, 100, QgsUnitTypes.LayoutMillimeters))
legend.setFrameEnabled(True)
layout.addLayoutItem(legend)

# Titlu
title = QgsLayoutItemLabel(layout)
title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU")
f = QFont("Arial", 14, QFont.Bold)
title.setFont(f)
title.attemptMove(QgsLayoutPoint(10, 5, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(277, 8, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

# Cartus tehnic / Provenienta
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "SIRUTA: 103684 • Sistem de coordonate: EPSG:3844 (Stereo 70)\n"
    "Surse: OpenStreetMap (ODbL), Copernicus Sentinel-2 L2A\n"
    "Construcții: Buffer +0.50m (GEOS)\n"
    "NOTĂ DE CONFORMITATE: Limita administrativă este REFERENCE (OSM Proxy).\n"
    "Nu reprezintă o graniță cadastrală legală oficială ANCPI."
)
fc = QFont("Arial", 7)
cartus.setFont(fc)
cartus.attemptMove(QgsLayoutPoint(225, 130, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(62, 70, QgsUnitTypes.LayoutMillimeters))
cartus.setFrameEnabled(True)
layout.addLayoutItem(cartus)

# Export PDF
exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300
res = exporter.exportToPdf(str(PDF_PATH), settings)

if res == QgsLayoutExporter.Success:
    print(f"-> Succes! Harta A4 300 DPI generata la: {PDF_PATH}")
else:
    print(f"-> Eroare la exportul PDF: cod {res}")

qgs.exitQgis()
print("Actualizare cartografica finalizata.")
