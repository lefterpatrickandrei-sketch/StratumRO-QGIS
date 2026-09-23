# -*- coding: utf-8 -*-
import sys
from osgeo import ogr

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

path = r"C:\Users\lefpa\Downloads\GIS_UAT_Iepuresti\RAN_Romania_National_Complet.gpkg"
ds = ogr.Open(path)
if not ds:
    print("Cannot open RAN_Romania_National_Complet.gpkg")
else:
    print(f"Layers in {path}:")
    for i in range(ds.GetLayerCount()):
        lyr = ds.GetLayerByIndex(i)
        print(f" - {lyr.GetName()}: {lyr.GetFeatureCount()} features, geom={ogr.GeometryTypeToName(lyr.GetGeomType())}")
        fields = [lyr.GetLayerDefn().GetFieldDefn(j).GetName() for j in range(lyr.GetLayerDefn().GetFieldCount())]
        print(f"   Fields: {fields[:10]}")
        sample = lyr.GetNextFeature()
        if sample:
            print(f"   Sample: {sample.items()}")
