# Update hydro and forest layers with DATA GAP entries (no local ref, Overpass failed)
import json
import time
from pathlib import Path
from osgeo import ogr, osr, gdal

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
OUT = WS / "data" / "output"
GPKG = OUT / "UAT_Giurgiu.gpkg"

S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

gpkg = ogr.Open(str(GPKG), update=1)

# Remove empty cursuri_apa and paduri layers if they exist
for lname in ["cursuri_apa", "paduri"]:
    for i in range(gpkg.GetLayerCount()):
        if gpkg.GetLayerByIndex(i).GetName() == lname:
            gpkg.DeleteLayer(i)
            print("Removed empty layer:", lname)
            break

# ============================================================================
# cursuri_apa — DATA GAP (D5/D6/D8)
# ============================================================================
lyr = gpkg.CreateLayer("cursuri_apa", S3844, geom_type=ogr.wkbMultiLineString)
lyr.CreateField(ogr.FieldDefn("status", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("note", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
feat = ogr.Feature(lyr.GetLayerDefn())
feat.SetField("status", "DATA_GAP")
feat.SetField("note", "No local hydro reference found; Overpass API fetch failed (504 gateway timeout). No public PUG/GIS source available.")
feat.SetField("crs_epsg", 3844)
feat.SetField("crs_units", "m")
lyr.CreateFeature(feat)
lyr = None
print("cursuri_apa: DATA_GAP recorded (no local ref, Overpass failed)")

# ============================================================================
# paduri — DATA GAP (D5/D6/D8)
# ============================================================================
lyr = gpkg.CreateLayer("paduri", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("status", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("note", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
feat = ogr.Feature(lyr.GetLayerDefn())
feat.SetField("status", "DATA_GAP")
feat.SetField("note", "No local forest/landuse reference found; Overpass API fetch failed (504 gateway timeout). No public PUG/GIS source available.")
feat.SetField("crs_epsg", 3844)
feat.SetField("crs_units", "m")
lyr.CreateFeature(feat)
lyr = None
print("paduri: DATA_GAP recorded (no local ref, Overpass failed)")

gpkg = None
print("DATA GAP entries recorded for cursuri_apa and paduri")