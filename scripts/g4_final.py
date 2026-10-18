"""StratumRO - G4 FINAL: complete all 7 deliverable layers in master GPKG.

Uses ONLY deterministic StratumRO algorithms and local ground truth data.
NO LLM geometry. LLM proposes/plans; OGR/GDAL executes.

Run:
  . scripts\\qgis_env.ps1
  python scripts\\g4_final.py
"""
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
REF = WS / "data" / "reference"
INTER = WS / "data" / "intermediate"
PROV = WS / "provenance"
LOG = WS / "logs"
GPKG = OUT / "UAT_Giurgiu.gpkg"

S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

steps = []


def step(name, detail):
    line = "[%s] %s :: %s" % (time.strftime("%H:%M:%S"), name, detail)
    print(line)
    steps.append(line)


print("=" * 78)
print("G4 FINAL - all 7 deliverable layers into UAT_Giurgiu.gpkg (EPSG:3844)")
print("=" * 78)

gpkg = ogr.Open(str(GPKG), update=1)

# ============================================================================
# 2. limita_intravilan — DATA GAP (D8)
# ============================================================================
step("intravilan", "No official PUG/GIS source found for Giurgiu intravilan.")
step("intravilan", "DATA GAP — INTRAVILAN recorded per D8 (non-fabrication rule).")
lyr = gpkg.CreateLayer("limita_intravilan", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("status", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("note", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
feat = ogr.Feature(lyr.GetLayerDefn())
feat.SetField("status", "DATA_GAP")
feat.SetField("note", "No public PUG/GIS source found for Giurgiu intravilan. Non-fabrication rule applies (D8).")
feat.SetField("crs_epsg", 3844)
feat.SetField("crs_units", "m")
lyr.CreateFeature(feat)
lyr = None

# ============================================================================
# 3. imobile_cadastrale — from local ground truth (REFERENCE layer, D5/I5)
# ============================================================================
step("cadastral", "Loading local ground truth: tier1_teren.geojson (29) + tier2_extended_gt.geojson (150)")
gt1 = GT / "tier1_teren.geojson"
gt2 = GT / "tier2_extended_gt.geojson"
lyr = gpkg.CreateLayer("imobile_cadastrale", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("source_file", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("source_layer", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("status", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
lyr.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))
ddef = lyr.GetLayerDefn()
lyr.StartTransaction()
n_out = 0
for ds_path, tag in [(gt1, "tier1_teren"), (gt2, "tier2_extended_gt")]:
    ds = ogr.Open(str(ds_path))
    l = ds.GetLayerByIndex(0)
    for feat in l:
        geom = feat.GetGeometryRef().Clone()
        geom.AssignSpatialReference(S3844)  # override declared CRS
        out = ogr.Feature(ddef)
        out.SetField("source_file", tag + ".geojson")
        out.SetField("source_layer", l.GetName())
        out.SetField("status", "REFERENCE")
        out.SetField("crs_epsg", 3844)
        out.SetField("crs_units", "m")
        out.SetGeometry(geom)
        lyr.CreateFeature(out)
        n_out += 1
    ds = None
lyr.CommitTransaction()
step("cadastral", "imobile_cadastrale written: %d features (REFERENCE per D5/I5)" % n_out)