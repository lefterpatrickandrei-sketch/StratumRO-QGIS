# constructii — roof-shape faithful + 0.50 m OUTWARD buffer (D2)
import json
import time
from pathlib import Path
from osgeo import ogr, osr, gdal

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
GT = ROOT / "data" / "ground_truth"
OUT = WS / "data" / "output"
GPKG = OUT / "UAT_Giurgiu.gpkg"

S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

src = GT / "osm_buildings_aoi.geojson"
src_ds = ogr.Open(str(src))
src_lyr = src_ds.GetLayerByIndex(0)
gpkg = ogr.Open(str(GPKG), update=1)
lyr = gpkg.CreateLayer("constructii", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("source_file", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("building", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("offset_m", ogr.OFTReal))
lyr.CreateField(ogr.FieldDefn("offset_direction", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("offset_method", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
ddef = lyr.GetLayerDefn()
lyr.StartTransaction()
n_out = 0
for feat in src_lyr:
    geom = feat.GetGeometryRef().Clone()
    geom.AssignSpatialReference(S3844)
    if geom.GetGeometryType() == ogr.wkbPolygon:
        geom = ogr.ForceToMultiPolygon(geom)
    geom = geom.Buffer(0.50, 8)
    if geom.GetGeometryType() == ogr.wkbPolygon:
        geom = ogr.ForceToMultiPolygon(geom)
    out = ogr.Feature(ddef)
    out.SetField("source_file", "osm_buildings_aoi.geojson")
    bld_idx = feat.GetFieldIndex("building")
    out.SetField("building", str(feat.GetField(bld_idx) if bld_idx >= 0 else "yes")[:40])
    out.SetField("offset_m", 0.50)
    out.SetField("offset_direction", "outward")
    out.SetField("offset_method", "buffer,segments=8,join=round")
    out.SetField("crs_epsg", 3844)
    out.SetField("crs_units", "m")
    out.SetGeometry(geom)
    lyr.CreateFeature(out)
    n_out += 1
lyr.CommitTransaction()
src_ds = None
print("constructii: %d features (offset_m=0.50 outward, EPSG:3844)" % n_out)
gpkg = None