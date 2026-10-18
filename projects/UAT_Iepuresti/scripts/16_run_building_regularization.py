# -*- coding: utf-8 -*-
"""
STRATUMRO — GEOMETRIC REGULARIZATION PIPELINE (EPSG:3844)
Procesează contururile acoperișurilor, elimină zgomotul de noduri (Douglas-Peucker)
și aplică offsetul exterior normativ de +0.50m conform Deciziei D2 și Invariantului I3.
"""
import os, sys
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import ogr, osr
ogr.UseExceptions()

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
GPKG_PATH = OUTPUT / "PUG_Iepuresti_Urban.gpkg"

print("="*75)
print(">>> STRATUMRO: REGULARIZARE CLĂDIRI & OFFSET +0.50M (EPSG:3844) <<<")
print("="*75)

srs_stereo70 = osr.SpatialReference()
srs_stereo70.ImportFromEPSG(3844)
srs_stereo70.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

ds = ogr.Open(str(GPKG_PATH), 1)

# Verificare / Recreare strat constructii_sam2
if ds.GetLayerByName("constructii_sam2"):
    ds.DeleteLayer("constructii_sam2")

out_lyr = ds.CreateLayer("constructii_sam2", srs_stereo70, ogr.wkbMultiPolygon)
out_lyr.CreateField(ogr.FieldDefn("tip_obiect", ogr.OFTString))
out_lyr.CreateField(ogr.FieldDefn("metoda", ogr.OFTString))
out_lyr.CreateField(ogr.FieldDefn("arie_sol_mp", ogr.OFTReal))
out_lyr.CreateField(ogr.FieldDefn("offset_ext_m", ogr.OFTReal))

bld_src = ds.GetLayerByName("constructii")
count = 0
total_area = 0.0

out_lyr.StartTransaction()
for feat in bld_src:
    geom = feat.GetGeometryRef()
    if geom and not geom.IsEmpty():
        # 1. Simplificare geometrica Douglas-Peucker pentru alinierea muchiilor
        simplified = geom.Simplify(0.20)
        
        # 2. Offset exterior normativ de +0.50 m (perete/streasină conform D2)
        buffered = simplified.Buffer(0.50)
        
        if buffered and not buffered.IsEmpty() and buffered.IsValid():
            area = round(buffered.GetArea(), 2)
            total_area += area
            
            out_f = ogr.Feature(out_lyr.GetLayerDefn())
            out_f.SetGeometry(ogr.ForceToMultiPolygon(buffered))
            out_f.SetField("tip_obiect", "Acoperiș regularizat (Amprentă sol)")
            out_f.SetField("metoda", "Douglas-Peucker + GEOS Metric Buffer")
            out_f.SetField("arie_sol_mp", area)
            out_f.SetField("offset_ext_m", 0.50)
            out_lyr.CreateFeature(out_f)
            count += 1

out_lyr.CommitTransaction()
ds = None

print(f"\n[SUCCES] Stratul 'constructii_sam2' a fost salvat în {GPKG_PATH.name}:")
print(f"  • Total clădiri regularizate: {count}")
print(f"  • Suprafață construită la sol: {round(total_area / 10000.0, 2)} ha ({round(total_area, 1)} mp)")
print(f"  • Offset exterior aplicat: +0.50 m (Stereo 70 / EPSG:3844)")
print("="*75)
