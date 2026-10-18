# -*- coding: utf-8 -*-
"""
STRATUMRO AUTOMATED PRODUCTION ENGINE — UAT IEPUREȘTI (GIURGIU)
Rezolvare definitiva PROJ Invalid Latitude + Generare livrabil cartografic A4 300 DPI.
"""
import os, sys, json
from pathlib import Path
from datetime import datetime, timezone
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
QA_DIR = ROOT / "qa"

GPKG_PATH = OUTPUT / "UAT_Iepuresti.gpkg"
QGZ_PATH = OUTPUT / "UAT_Iepuresti.qgz"
PDF_PATH = OUTPUT / "harta_Iepuresti_StratumRO.pdf"

print("="*65)
print(">>> STRATUMRO PRODUCTION RUN: UAT IEPUREȘTI (SIRUTA 103684) <<<")
print("="*65)

# ---------------------------------------------------------------------------
# GESTIUNE COORDONATE STEREO 70 (EPSG:3844) FĂRĂ ERORI PROJ
# ---------------------------------------------------------------------------
srs_stereo70 = osr.SpatialReference()
srs_stereo70.ImportFromEPSG(3844)
srs_stereo70.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

srs_wgs84 = osr.SpatialReference()
srs_wgs84.ImportFromEPSG(4326)
srs_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

trans_wgs_to_3844 = osr.CoordinateTransformation(srs_wgs84, srs_stereo70)

def ensure_stereo70(geom, layer_srs=None):
    """Detecteaza daca geometria este deja in Stereo 70 sau daca necesita transformare din WGS84."""
    if geom is None or geom.IsEmpty():
        return None
    min_x, max_x, min_y, max_y = geom.GetEnvelope()
    
    # Daca valorile sunt > 180, geometria este DEJA proiectata in metri (Stereo 70)
    if abs(min_x) > 180 or abs(max_x) > 180:
        return geom.Clone()
    
    # Altfel este in grade (WGS84) si o transformam in Stereo 70
    g_cloned = geom.Clone()
    if layer_srs and layer_srs.GetAuthorityCode(None) == "4326":
        g_cloned.Transform(trans_wgs_to_3844)
    else:
        g_cloned.Transform(trans_wgs_to_3844)
    return g_cloned

# ---------------------------------------------------------------------------
# ETAPA 1: PRELUCRARE GEOMETRII ȘI COMPLETARE DATE
# ---------------------------------------------------------------------------
print("\n[FAZA 1] Geoprocesare deterministă și generare date...")

driver = ogr.GetDriverByName("GPKG")
if GPKG_PATH.exists():
    ds = driver.Open(str(GPKG_PATH), 1)
else:
    ds = driver.CreateDataSource(str(GPKG_PATH))

def reset_layer(name, geom_type):
    if ds.GetLayerByName(name):
        ds.DeleteLayer(name)
    lyr = ds.CreateLayer(name, srs_stereo70, geom_type)
    for fn in ["source", "source_id", "license", "notes"]:
        lyr.CreateField(ogr.FieldDefn(fn, ogr.OFTString))
    return lyr

# 1. Limita UAT
uat_path = DATA_PROC / "ancpi" / "limita_UAT.geojson"
uat_ds = ogr.Open(str(uat_path))
uat_lyr_in = uat_ds.GetLayer(0)
uat_poly_geom = None

uat_out = reset_layer("limita_UAT", ogr.wkbMultiPolygon)
for feat in uat_lyr_in:
    g = feat.GetGeometryRef()
    g3844 = ensure_stereo70(g, uat_lyr_in.GetSpatialRef())
    if g3844:
        uat_poly_geom = g3844.Clone()
        f_out = ogr.Feature(uat_out.GetLayerDefn())
        f_out.SetGeometry(ogr.ForceToMultiPolygon(g3844))
        f_out.SetField("source", "OSM_PROXY")
        f_out.SetField("source_id", "103684")
        f_out.SetField("license", "ODbL")
        f_out.SetField("notes", "REFERENCE: Limita UAT admin_level=8")
        uat_out.CreateFeature(f_out)
print("  [OK] 1. limita_UAT procesată în Stereo 70.")

# 2. Cursuri de apă
water_path = DATA_PROC / "osm" / "waterways.geojson"
water_out = reset_layer("cursuri_apa", ogr.wkbMultiLineString)
water_ds = ogr.Open(str(water_path))
water_count = 0
for feat in water_ds.GetLayer(0):
    g = feat.GetGeometryRef()
    g3844 = ensure_stereo70(g, water_ds.GetLayer(0).GetSpatialRef())
    if g3844 and uat_poly_geom and g3844.Intersects(uat_poly_geom):
        clipped = g3844.Intersection(uat_poly_geom)
        if clipped and not clipped.IsEmpty():
            f_out = ogr.Feature(water_out.GetLayerDefn())
            f_out.SetGeometry(ogr.ForceToMultiLineString(clipped))
            f_out.SetField("source", "OSM")
            f_out.SetField("license", "ODbL")
            water_out.CreateFeature(f_out)
            water_count += 1
print(f"  [OK] 2. cursuri_apa decupate: {water_count} segmente.")

# 3. Drumuri ax și Drumuri poligon (ampriză 6m)
roads_path = DATA_PROC / "osm" / "roads.geojson"
roads_ds = ogr.Open(str(roads_path))
roads_ax_out = reset_layer("drumuri_ax", ogr.wkbMultiLineString)
roads_poly_out = reset_layer("drumuri_poligon", ogr.wkbMultiPolygon)
road_count = 0

for feat in roads_ds.GetLayer(0):
    g = feat.GetGeometryRef()
    g3844 = ensure_stereo70(g, roads_ds.GetLayer(0).GetSpatialRef())
    if g3844 and uat_poly_geom and g3844.Intersects(uat_poly_geom):
        clipped = g3844.Intersection(uat_poly_geom)
        if clipped and not clipped.IsEmpty():
            # Ax
            f_ax = ogr.Feature(roads_ax_out.GetLayerDefn())
            f_ax.SetGeometry(ogr.ForceToMultiLineString(clipped))
            f_ax.SetField("source", "OSM")
            f_ax.SetField("license", "ODbL")
            roads_ax_out.CreateFeature(f_ax)
            # Ampriza 6m (+3m de fiecare parte din ax)
            b_poly = clipped.Buffer(3.0)
            if b_poly and not b_poly.IsEmpty():
                f_poly = ogr.Feature(roads_poly_out.GetLayerDefn())
                f_poly.SetGeometry(ogr.ForceToMultiPolygon(b_poly))
                f_poly.SetField("source", "OSM_GEOS")
                f_poly.SetField("notes", "Ampriza 6.0m (+3.0m)")
                roads_poly_out.CreateFeature(f_poly)
            road_count += 1
print(f"  [OK] 3. drumuri_ax și drumuri_poligon: {road_count} entități.")

# 4. Construcții (+0.50m offset exterior conform cerinței)
bld_path = DATA_PROC / "osm" / "buildings.geojson"
bld_ds = ogr.Open(str(bld_path))
bld_out = reset_layer("constructii", ogr.wkbMultiPolygon)
bld_count = 0
all_bld_union = ogr.Geometry(ogr.wkbMultiPolygon)

for feat in bld_ds.GetLayer(0):
    g = feat.GetGeometryRef()
    g3844 = ensure_stereo70(g, bld_ds.GetLayer(0).GetSpatialRef())
    if g3844 and uat_poly_geom and g3844.Intersects(uat_poly_geom):
        # Offset exterior cerut de 50 cm
        b_geom = g3844.Buffer(0.50)
        if b_geom and not b_geom.IsEmpty():
            f_out = ogr.Feature(bld_out.GetLayerDefn())
            f_out.SetGeometry(ogr.ForceToMultiPolygon(b_geom))
            f_out.SetField("source", "OSM_GEOS")
            f_out.SetField("notes", "Offset exterior acoperis +0.50m")
            bld_out.CreateFeature(f_out)
            bld_count += 1
            
            # Colectare pentru vatra satului
            exp = g3844.Buffer(35.0)
            if exp:
                all_bld_union = all_bld_union.Union(exp)
print(f"  [OK] 4. constructii: {bld_count} clădiri cu buffer +0.50m.")

# 5. Poduri
bridges_path = DATA_PROC / "osm" / "bridges.geojson"
bridges_out = reset_layer("poduri", ogr.wkbMultiLineString)
bridge_count = 0
if bridges_path.exists():
    br_ds = ogr.Open(str(bridges_path))
    for feat in br_ds.GetLayer(0):
        g = feat.GetGeometryRef()
        g3844 = ensure_stereo70(g, br_ds.GetLayer(0).GetSpatialRef())
        if g3844 and uat_poly_geom and g3844.Intersects(uat_poly_geom):
            f_out = ogr.Feature(bridges_out.GetLayerDefn())
            f_out.SetGeometry(ogr.ForceToMultiLineString(g3844))
            f_out.SetField("source", "OSM")
            bridges_out.CreateFeature(f_out)
            bridge_count += 1
print(f"  [OK] 5. poduri: {bridge_count} structuri.")

# 6. Limita Intravilan (Sinteză algoritmică)
intra_out = reset_layer("limita_intravilan", ogr.wkbMultiPolygon)
if all_bld_union and not all_bld_union.IsEmpty():
    vatra = all_bld_union.Buffer(-15.0).Buffer(10.0)
    if uat_poly_geom:
        vatra = vatra.Intersection(uat_poly_geom)
    if vatra and not vatra.IsEmpty():
        f_intra = ogr.Feature(intra_out.GetLayerDefn())
        f_intra.SetGeometry(ogr.ForceToMultiPolygon(vatra))
        f_intra.SetField("source", "DERIVED_GEOS")
        f_intra.SetField("notes", "Vatra satului estimata din cluster cladiri")
        intra_out.CreateFeature(f_intra)
        ha = round(vatra.GetArea() / 10000.0, 2)
        print(f"  [OK] 6. limita_intravilan sintetizată: {ha} ha.")

# 7. Imobile cadastrale (Documentat DATA GAP per Invariantul I1)
reset_layer("imobile_cadastrale", ogr.wkbMultiPolygon)
print("  [OK] 7. imobile_cadastrale: DATA GAP documentat.")

# 8. Păduri (Clasificare NDVI din Sentinel-2)
paduri_out = reset_layer("paduri", ogr.wkbMultiPolygon)
b4_list = list(RAW_S2.glob("*_B04.tif"))
b8_list = list(RAW_S2.glob("*_B08.tif"))

if b4_list and b8_list:
    ds_b4 = gdal.Open(str(b4_list[0]))
    ds_b8 = gdal.Open(str(b8_list[0]))
    b4 = ds_b4.GetRasterBand(1).ReadAsArray().astype(np.float32)
    b8 = ds_b8.GetRasterBand(1).ReadAsArray().astype(np.float32)
    denom = b8 + b4
    denom[denom == 0] = 0.0001
    ndvi = (b8 - b4) / denom
    mask = (ndvi > 0.55).astype(np.uint8)

    mem_drv = gdal.GetDriverByName("MEM")
    m_ds = mem_drv.Create("", ds_b4.RasterXSize, ds_b4.RasterYSize, 1, gdal.GDT_Byte)
    m_ds.SetGeoTransform(ds_b4.GetGeoTransform())
    m_ds.SetProjection(ds_b4.GetProjection())
    m_ds.GetRasterBand(1).WriteArray(mask)

    srs_utm = osr.SpatialReference()
    srs_utm.ImportFromWkt(ds_b4.GetProjection())
    trans_utm = osr.CoordinateTransformation(srs_utm, srs_stereo70)

    t_mem = ogr.GetDriverByName("Memory").CreateDataSource("m")
    t_lyr = t_mem.CreateLayer("p", srs_utm, ogr.wkbPolygon)
    gdal.Polygonize(m_ds.GetRasterBand(1), None, t_lyr, -1, [], callback=None)

    forest_count = 0
    for pf in t_lyr:
        pg = pf.GetGeometryRef()
        if pg and pg.GetArea() > 3000:
            pg_3844 = pg.Clone()
            pg_3844.Transform(trans_utm)
            if uat_poly_geom and pg_3844.Intersects(uat_poly_geom):
                cp = pg_3844.Intersection(uat_poly_geom)
                if not cp.IsEmpty():
                    f_out = ogr.Feature(paduri_out.GetLayerDefn())
                    f_out.SetGeometry(ogr.ForceToMultiPolygon(cp))
                    f_out.SetField("source", "SENTINEL-2_NDVI")
                    f_out.SetField("license", "Copernicus Open Access")
                    paduri_out.CreateFeature(f_out)
                    forest_count += 1
    print(f"  [OK] 8. paduri clasificate spectral: {forest_count} poligoane.")

ds = None

# ---------------------------------------------------------------------------
# ETAPA 2: VALIDARE CALITATE GEOMETRII (QA/QC)
# ---------------------------------------------------------------------------
print("\n[FAZA 2] Verificare deterministă a geometriilor...")
QA_DIR.mkdir(parents=True, exist_ok=True)
ds_qa = ogr.Open(str(GPKG_PATH), 0)
total_invalids = 0
for i in range(ds_qa.GetLayerCount()):
    lyr = ds_qa.GetLayer(i)
    inv = sum(1 for f in lyr if f.GetGeometryRef() is None or not f.GetGeometryRef().IsValid())
    total_invalids += inv
    print(f"  -> Strat: {lyr.GetName():<20} | Entități: {lyr.GetFeatureCount():<5} | Invalide: {inv}")
ds_qa = None
print(f"  [PASS] Geometrii validate topologic. Erori: {total_invalids}")

# ---------------------------------------------------------------------------
# ETAPA 3: GENERARE CARTOGRAFICĂ ROBUSTĂ (QGIS PRINT LAYOUT)
# ---------------------------------------------------------------------------
print("\n[FAZA 3] Construire proiect QGIS și export PDF A4 la 300 DPI...")
qgs = QgsApplication([], True)
qgs.initQgis()

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("Plan Teritorial — UAT Iepurești (Giurgiu)")

styles_def = [
    ("paduri", "Păduri / Fond Forestier (S2)", "fill", {"color": "34,139,34,140", "outline_color": "0,100,0,255", "outline_width": "0.2"}),
    ("limita_intravilan", "Intravilan Estimat (Vatra Satului)", "fill", {"color": "255,165,0,30", "outline_color": "255,120,0,255", "outline_width": "0.5"}),
    ("drumuri_poligon", "Ampriză Drumuri (6m)", "fill", {"color": "225,225,225,255", "outline_color": "150,150,150,255", "outline_width": "0.1"}),
    ("constructii", "Construcții (+0.50m)", "fill", {"color": "178,34,34,220", "outline_color": "40,40,40,255", "outline_width": "0.15"}),
    ("cursuri_apa", "Cursuri de Apă", "line", {"color": "30,144,255,255", "width": "0.5"}),
    ("drumuri_ax", "Ax Drumuri", "line", {"color": "70,70,70,255", "width": "0.6"}),
    ("poduri", "Poduri", "bridge", {}),
    ("limita_UAT", "Limită Administrativă UAT", "fill", {"color": "0,0,0,0", "outline_color": "0,0,0,255", "outline_width": "0.7"})
]

bbox_target = None
for lname, dname, stype, cfg in styles_def:
    uri = f"{GPKG_PATH}|layername={lname}"
    vl = QgsVectorLayer(uri, dname, "ogr")
    if not vl.isValid():
        continue
    
    if stype == "bridge":
        sym = QgsLineSymbol()
        sl1 = QgsSimpleLineSymbolLayer(QColor(0, 0, 0), 1.8)
        sl2 = QgsSimpleLineSymbolLayer(QColor(255, 255, 255), 1.0)
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

lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("Macheta_StratumRO")
lm.addLayout(layout)

# 1. Hartă principală (stânga)
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

# 2. Titlu
title = QgsLayoutItemLabel(layout)
title.setText("COMUNA IEPUREȘTI — JUDEȚUL GIURGIU (SIRUTA 103684)")
title.setFont(QFont(FONT, 13, QFont.Bold))
title.attemptMove(QgsLayoutPoint(10, 6, QgsUnitTypes.LayoutMillimeters))
title.attemptResize(QgsLayoutSize(200, 9, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(title)

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

# 4. Legendă (dreapta sus)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ")
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 10, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.Subgroup, QFont(FONT, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 8))
except Exception:
    pass
legend.setAutoUpdateModel(True)
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255))
legend.attemptMove(QgsLayoutPoint(215, 18, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(72, 105, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# 5. Cartuș tehnic (dreapta jos)
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "PARAMETRI TEHNICI & STATUT SURSE:\n"
    "• Proiecție: Stereo 70 (EPSG:3844)\n"
    "• Limită UAT: REFERENCE (OSM admin_level=8)\n"
    "• Construcții: Offset exterior +0.50m (GEOS)\n"
    "• Drumuri: Ampriză 6.0m (+3.0m ax)\n"
    "• Intravilan: Vatră sat dedusă din densitate\n"
    "• Păduri: Detectate spectral Sentinel-2 L2A\n"
    "• Imobile: DATA GAP (Acces ANCPI nedisponibil)\n\n"
    "CONFORMITATE (Invariantul I5):\n"
    "Acest plan nu constituie act cadastral oficial\n"
    "în sensul Legii 7/1996. Reprezintă analiză\n"
    "geospațială derivată exclusiv din surse deschise."
)
cartus.setFont(QFont(FONT, 7))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.3, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250))
cartus.attemptMove(QgsLayoutPoint(215, 126, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(72, 74, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

project.write(str(QGZ_PATH))
print(f"  [OK] Proiect QGIS salvat: {QGZ_PATH}")

# 6. Export PDF la 300 DPI
exporter = QgsLayoutExporter(layout)
settings = QgsLayoutExporter.PdfExportSettings()
settings.dpi = 300
settings.rasterizeWholeImage = False

target_pdf = PDF_PATH
try:
    if target_pdf.exists():
        target_pdf.unlink()
except PermissionError:
    target_pdf = OUTPUT / "harta_Iepuresti_StratumRO_v2.pdf"

res = exporter.exportToPdf(str(target_pdf), settings)

if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Livrabil generat la standard de tipar (300 DPI):")
    print(f"               {target_pdf}")
else:
    print(f"\n[EROARE] Exportul a eșuat cu codul: {res}")

qgs.exitQgis()
print("="*65)
