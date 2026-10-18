# -*- coding: utf-8 -*-
"""G0: Initialize output/UAT_Iepuresti.gpkg with 9 empty EPSG:3844 layers."""
import os
import sys
from osgeo import ogr, osr

OUT = os.path.join("output", "UAT_Iepuresti.gpkg")

LAYERS = [
    ("limita_UAT", ogr.wkbPolygon),
    ("limita_intravilan", ogr.wkbPolygon),
    ("imobile_cadastrale", ogr.wkbPolygon),
    ("constructii", ogr.wkbPolygon),
    ("drumuri_poligon", ogr.wkbPolygon),
    ("drumuri_ax", ogr.wkbLineString),
    ("cursuri_apa", ogr.wkbLineString),
    ("paduri", ogr.wkbPolygon),
    ("poduri", ogr.wkbPolygon),
]


def main():
    if os.path.exists(OUT):
        os.remove(OUT)
    drv = ogr.GetDriverByName("GPKG")
    ds = drv.CreateDataSource(OUT)
    if ds is None:
        print("ERROR: could not create %s" % OUT)
        return 1
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3844)
    for name, geom in LAYERS:
        lyr = ds.CreateLayer(name, srs, geom)
        if lyr is None:
            print("ERROR: could not create layer %s" % name)
            return 1
    # also commit spatial_ref_sys / layer styles properly
    ds.FlushCache()
    ds = None
    print("Created %s with %d layers (EPSG:3844)" % (OUT, len(LAYERS)))
    for name, _ in LAYERS:
        print("  - %s" % name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
