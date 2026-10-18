# cursuri_apa + paduri — from local hydro/landuse reference geojson
import json
import time
from pathlib import Path
from osgeo import ogr, osr, gdal

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
REF = WS / "data" / "reference"
OUT = WS / "data" / "output"
GPKG = OUT / "UAT_Giurgiu.gpkg"

S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

gpkg = ogr.Open(str(GPKG), update=1)

# ============================================================================
# cursuri_apa
# ============================================================================
hydro_candidates = [
    (REF / "tier1_primary_29.geojson", "tier1_hydro"),
    (REF / "tier2_additional_121.geojson", "tier2_hydro"),
]
lyr = gpkg.CreateLayer("cursuri_apa", S3844, geom_type=ogr.wkbMultiLineString)
lyr.CreateField(ogr.FieldDefn("waterway", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("name", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("source", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
ddef = lyr.GetLayerDefn()
lyr.StartTransaction()
n_out = 0
for path, tag in hydro_candidates:
    if not path.exists():
        continue
    ds = ogr.Open(str(path))
    l = ds.GetLayerByIndex(0)
    for feat in l:
        geom = feat.GetGeometryRef().Clone()
        geom.AssignSpatialReference(S3844)
        if geom.GetGeometryType() == ogr.wkbLineString:
            geom = ogr.ForceToMultiLineString(geom)
        out = ogr.Feature(ddef)
        ww_idx = feat.GetFieldIndex("waterway")
        name_idx = feat.GetFieldIndex("name")
        out.SetField("waterway", str(feat.GetField(ww_idx) if ww_idx >= 0 else "")[:40])
        out.SetField("name", str(feat.GetField(name_idx) if name_idx >= 0 else "")[:120])
        out.SetField("source", tag + " (local reference)")
        out.SetField("crs_epsg", 3844)
        out.SetField("crs_units", "m")
        out.SetGeometry(geom)
        lyr.CreateFeature(out)
        n_out += 1
    ds = None
lyr.CommitTransaction()
print("cursuri_apa: %d features (local reference)" % n_out)

# ============================================================================
# paduri
# ============================================================================
forest_candidates = [
    (REF / "tier1_primary_29.geojson", "tier1_landuse"),
    (REF / "tier2_additional_121.geojson", "tier2_landuse"),
]
lyr = gpkg.CreateLayer("paduri", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("landuse", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("natural", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("source", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
ddef = lyr.GetLayerDefn()
lyr.StartTransaction()
n_out = 0
for path, tag in forest_candidates:
    if not path.exists():
        continue
    ds = ogr.Open(str(path))
    l = ds.GetLayerByIndex(0)
    for feat in l:
        tg = feat.items()
        if "landuse" not in tg and "natural" not in tg:
            continue
        geom = feat.GetGeometryRef().Clone()
        geom.AssignSpatialReference(S3844)
        if geom.GetGeometryType() == ogr.wkbPolygon:
            geom = ogr.ForceToMultiPolygon(geom)
        out = ogr.Feature(ddef)
        out.SetField("landuse", str(tg.get("landuse", ""))[:40])
        out.SetField("natural", str(tg.get("natural", ""))[:40])
        out.SetField("source", tag + " (local reference)")
        out.SetField("crs_epsg", 3844)
        out.SetField("crs_units", "m")
        out.SetGeometry(geom)
        lyr.CreateFeature(out)
        n_out += 1
    ds = None
lyr.CommitTransaction()
print("paduri: %d features (local reference)" % n_out)

gpkg = None
print("done")