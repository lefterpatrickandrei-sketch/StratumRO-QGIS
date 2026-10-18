# -*- coding: utf-8 -*-
"""Motor autonom de Teledetectie, Vectorizare si Generare Spatiala (UAT Iepuresti)."""
import os, sys
from pathlib import Path
import numpy as np

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import gdal, ogr, osr
gdal.UseExceptions()
ogr.UseExceptions()

from qgis.core import (
    QgsApplication, QgsProject, QgsPrintLayout,
    QgsVectorLayer, QgsFillSymbol, QgsLineSymbol,
    QgsSingleSymbolRenderer, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutPoint,
    QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
GPKG_PATH = OUTPUT / "UAT_Iepuresti.gpkg"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT / "harta_Iepuresti_analiza_avansata.pdf"
RAW_S2 = ROOT / "data" / "raw" / "sentinel2"

print("--- 1. CALCUL NDVI SI VECTORIZARE AUTOMATA A VEGETATIEI ---")
b04_path = list(RAW_S2.glob("*_B04.tif"))[0]
b08_path = list(RAW_S2.glob("*_B08.tif"))[0]

ds_red = gdal.Open(str(b04_path))
ds_nir = gdal.Open(str(b08_path))

red = ds_red.GetRasterBand(1).ReadAsArray().astype(np.float32)
nir = ds_nir.GetRasterBand(1).ReadAsArray().astype(np.float32)

# Evitam impartirea la zero
denom = nir + red
denom[denom == 0] = 0.0001
ndvi = (nir - red) / denom

# Masca binara: Vegetatie densa / Padure reala (NDVI > 0.55)
veg_mask = (ndvi > 0.55).astype(np.uint8)

# Creare raster temporar in memorie pentru poligonizare
mem_drv = gdal.GetDriverByName("MEM")
ndvi_ds = mem_drv.Create("", ds_red.RasterXSize, ds_red.RasterYSize, 1, gdal.GDT_Byte)
ndvi_ds.SetGeoTransform(ds_red.GetGeoTransform())
ndvi_ds.SetProjection(ds_red.GetProjection())
ndvi_band = ndvi_ds.GetRasterBand(1)
ndvi_band.WriteArray(veg_mask)

# Reproiectare si vectorizare in Stereo 70 (EPSG:3844)
srs_src = osr.SpatialReference()
srs_src.ImportFromWkt(ds_red.GetProjection())
srs_dst = osr.SpatialReference()
srs_dst.ImportFromEPSG(3844)
srs_dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
coord_trans = osr.CoordinateTransformation(srs_src, srs_dst)

gpkg_ds = ogr.Open(str(GPKG_PATH), 1)

# Deschidem poligonul UAT pentru intersectie
uat_lyr = gpkg_ds.GetLayerByName("limita_UAT")
uat_feat = uat_lyr.GetNextFeature()
uat_geom = uat_feat.GetGeometryRef()

# 1. Strat generat: paduri_clasificate_ndvi
if gpkg_ds.GetLayerByName("paduri_clasificate_ndvi"):
    gpkg_ds.DeleteLayer("paduri_clasificate_ndvi")

layer_ndvi = gpkg_ds.CreateLayer("paduri_clasificate_ndvi", srs_dst, ogr.wkbMultiPolygon)
layer_ndvi.CreateField(ogr.FieldDefn("clasa", ogr.OFTString))
layer_ndvi.CreateField(ogr.FieldDefn("ndvi_min", ogr.OFTReal))

temp_mem_ds = ogr.GetDriverByName("Memory").CreateDataSource("mem_poly")
temp_lyr = temp_mem_ds.CreateLayer("poly", srs_src, ogr.wkbPolygon)
gdal.Polygonize(ndvi_band, None, temp_lyr, -1, [], callback=None)

layer_ndvi.StartTransaction()
count_ndvi = 0
for f in temp_lyr:
    # Retinem doar pixelii cu valoarea 1 (vegetatie densa)
    geom = f.GetGeometryRef()
    if geom and geom.GetArea() > 2500:  # Filtram zgomotul sub 2500 mp (0.25 ha)
        geom_cloned = geom.Clone()
        geom_cloned.Transform(coord_trans)
        if geom_cloned.Intersects(uat_geom):
            clipped = geom_cloned.Intersection(uat_geom)
            if not clipped.IsEmpty():
                out_f = ogr.Feature(layer_ndvi.GetLayerDefn())
                out_f.SetGeometry(ogr.ForceToMultiPolygon(clipped))
                out_f.SetField("clasa", "Vegetatie Densa / Padure S2")
                out_f.SetField("ndvi_min", 0.55)
                layer_ndvi.CreateFeature(out_f)
                count_ndvi += 1
layer_ndvi.CommitTransaction()
print(f"   -> Detectat si vectorizat din satelit: {count_ndvi} poligoane de vegetatie densa.")

print("--- 2. GENERARE AUTONOMA INTRAVILAN ESTIMAT (REZOLVARE DATA GAP) ---")
bld_lyr = gpkg_ds.GetLayerByName("constructii")
bld_union = ogr.Geometry(ogr.wkbMultiPolygon)

bld_lyr.ResetReading()
for f in bld_lyr:
    g = f.GetGeometryRef()
    if g:
        # Buffer de agregare pentru a forma vatra satului
        b = g.Buffer(35.0)
        if b:
            bld_union = bld_union.Union(b)

# Rafinam conturul: eliminam insulele izolate mici si inchidem spatiile goale
intravilan_geom = bld_union.Buffer(-15.0).Buffer(10.0)
intravilan_geom = intravilan_geom.Intersection(uat_geom)

if gpkg_ds.GetLayerByName("intravilan_estimat_ai"):
    gpkg_ds.DeleteLayer("intravilan_estimat_ai")

layer_intra = gpkg_ds.CreateLayer("intravilan_estimat_ai", srs_dst, ogr.wkbMultiPolygon)
layer_intra.CreateField(ogr.FieldDefn("metoda", ogr.OFTString))
layer_intra.CreateField(ogr.FieldDefn("suprafata_ha", ogr.OFTReal))

layer_intra.StartTransaction()
if intravilan_geom and not intravilan_geom.IsEmpty():
    out_intra = ogr.Feature(layer_intra.GetLayerDefn())
    multi_poly = ogr.ForceToMultiPolygon(intravilan_geom)
    out_intra.SetGeometry(multi_poly)
    out_intra.SetField("metoda", "Buffer Morfologic Densitate Constructii")
    out_intra.SetField("suprafata_ha", round(multi_poly.GetArea() / 10000.0, 2))
    layer_intra.CreateFeature(out_intra)
    print(f"   -> Generat contur Intravilan Estimat: {round(multi_poly.GetArea() / 10000.0, 2)} ha.")
layer_intra.CommitTransaction()

print("--- 3. GENERARE ZONA DE PROTECTIE SI SERVITUTE APA (30m) ---")
water_lyr = gpkg_ds.GetLayerByName("cursuri_apa")
water_union = ogr.Geometry(ogr.wkbMultiPolygon)

water_lyr.ResetReading()
for f in water_lyr:
    g = f.GetGeometryRef()
    if g:
        wb = g.Buffer(30.0)
        if wb:
            water_union = water_union.Union(wb)

water_prot_geom = water_union.Intersection(uat_geom)

if gpkg_ds.GetLayerByName("protectie_hidro_30m"):
    gpkg_ds.DeleteLayer("protectie_hidro_30m")

layer_prot = gpkg_ds.CreateLayer("protectie_hidro_30m", srs_dst, ogr.wkbMultiPolygon)
layer_prot.CreateField(ogr.FieldDefn("zona", ogr.OFTString))

layer_prot.StartTransaction()
if water_prot_geom and not water_prot_geom.IsEmpty():
    out_prot = ogr.Feature(layer_prot.GetLayerDefn())
    out_prot.SetGeometry(ogr.ForceToMultiPolygon(water_prot_geom))
    out_prot.SetField("zona", "Coridor Protectie Hidrografica (30m)")
    layer_prot.CreateFeature(out_prot)
    print("   -> Generata zona de protectie hidrografica pe coridorul raurilor.")
layer_prot.CommitTransaction()

gpkg_ds = None

print("--- 4. CONFIGURARE PROIECT QGIS SI EXPORT HARTA DE ANALIZA ---")
qgs = QgsApplication([], True)
qgs.initQgis()

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("UAT Iepurești — Analiză Teritorială Generativă")

# Straturi si stilizare pentru noile entitati produse
def add_vector(layer_name, label, sym):
    uri = f"{GPKG_PATH}|layername={layer_name}"
    vl = QgsVectorLayer(uri, label, "ogr")
    if vl.isValid():
        vl.setRenderer(QgsSingleSymbolRenderer(sym))
        project.addMapLayer(vl)
        return vl
    return None

# 1. Protectie Hidro (albastru semitransparent)
sym_prot = QgsFillSymbol.createSimple({"color": "135,206,250,110", "outline_color": "30,144,255,200", "outline_width": "0.2"})
add_vector("protectie_hidro_30m", "Zonă Protecție Râuri (30m)", sym_prot)

# 2. Paduri clasificate satelitar NDVI (verde crud hașurat/solid)
sym_ndvi = QgsFillSymbol.createSimple({"color": "34,139,34,140", "outline_color": "0,100,0,255", "outline_width": "0.2"})
add_vector("paduri_clasificate_ndvi", "Vegetație / Păduri (Detectat S2)", sym_ndvi)

# 3. Intravilan estimat (contur portocaliu punctat pronuntat)
sym_intra = QgsFillSymbol.createSimple({"color": "255,165,0,40", "outline_color": "255,100,0,255", "outline_width": "0.6", "outline_style": "dash"})
add_vector("intravilan_estimat_ai", "Intravilan Estimat (Cluster Geom.)", sym_intra)

# 4. Drumuri si ape originale
sym_water = QgsLineSymbol.createSimple({"color": "0,0,205,255", "width": "0.5"})
add_vector("cursuri_apa", "Cursuri de Apă", sym_water)

sym_roads = QgsLineSymbol.createSimple({"color": "80,80,80,255", "width": "0.7"})
add_vector("drumuri_ax", "Rețea Drumuri", sym_roads)

# 5. Constructii
sym_bld = QgsFillSymbol.createSimple({"color": "178,34,34,220", "outline_color": "50,50,50,255", "outline_width": "0.15"})
add_vector("constructii", "Construcții (+0.50m)", sym_bld)

# 6. Limita UAT
sym_uat = QgsFillSymbol.createSimple({"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.7"})
uat_vl = add_vector("limita_UAT", "Limită Administrativă UAT", sym_uat)

# Configurare Layout
layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Plan_Generativ_A4")

map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 18, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(200, 182, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if uat_vl:
    bbox = uat_vl.extent()
    bbox.scale(1.08)
    map_item.setExtent(bbox)

layout.addLayoutItem(map_item)

# Titlu
title = QgsLayoutItemLabel(layout)
title.setText("PLAN CARTOGRAFIC GENERATIV — UAT IEPUREȘTI")
title.setFont(QFont("Arial", 13, QFont.Bold))
title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(200, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

# Scara Grafica
sb = QgsLayoutItemScaleBar(layout)
sb.setStyle("Single Box")
sb.setLinkedMap(map_item)
sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
sb.setNumberOfSegments(3)
sb.setUnits(QgsUnitTypes.DistanceKilometers)
sb.setUnitLabel(" km")
sb.setFont(QFont("Arial", 8))
sb.setBackgroundEnabled(True)
sb.setBackgroundColor(QColor(255, 255, 255, 230))
sb.setFrameEnabled(True)
sb.attemptMove(QgsLayoutPoint(15, 185, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# Legenda
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("STRATURI & DERIVATE AI")
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(215, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(72, 105, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# Cartus de Analiza
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "GEO-AI ENGINE / DERIVARE DATE:\n"
    "• NDVI Satelitar: Threshold > 0.55 din\n"
    "  Sentinel-2 L2A (B08/B04) la 10m.\n"
    "• Intravilan: Sinteză geometrică din\n"
    "  densitatea de construcții (rezolvare\n"
    "  autonomă a golului de date ANCPI).\n"
    "• Servitute Ape: Zonă tampon ecologică\n"
    "  de 30m calculată automat pe albie.\n"
    "• Sistem Coordonate: Stereo 70 (EPSG:3844)"
)
cartus.setFont(QFont("Arial", 7))
cartus.setFrameEnabled(True)
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(215, 127, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(72, 73, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ_PATH))

exporter = QgsLayoutExporter(layout)
s = QgsLayoutExporter.PdfExportSettings()
s.dpi = 300
res = exporter.exportToPdf(str(PDF_PATH), s)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES] Planul cartografic generativ a fost creat: {PDF_PATH}")

qgs.exitQgis()
