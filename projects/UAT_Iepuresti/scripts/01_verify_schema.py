# -*- coding: utf-8 -*-
"""G1.3: Verify 9 layers in output/UAT_Iepuresti.gpkg; fix poduri to LineString; add provenance fields."""
import os
from osgeo import ogr, osr

GPKG = os.path.join("output", "UAT_Iepuresti.gpkg")

SPEC = [
    ("limita_UAT", ogr.wkbPolygon),
    ("limita_intravilan", ogr.wkbPolygon),
    ("imobile_cadastrale", ogr.wkbPolygon),
    ("constructii", ogr.wkbPolygon),
    ("drumuri_poligon", ogr.wkbPolygon),
    ("drumuri_ax", ogr.wkbLineString),
    ("cursuri_apa", ogr.wkbLineString),
    ("paduri", ogr.wkbPolygon),
    ("poduri", ogr.wkbLineString),
]

FIELDS = [("source", 254), ("source_id", 64), ("license", 64), ("notes", 254)]


def main():
    ds = ogr.Open(GPKG, update=1)
    if ds is None:
        raise SystemExit("cannot open %s" % GPKG)
    names = {ds.GetLayerByIndex(i).GetName(): i for i in range(ds.GetLayerCount())}
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(3844)
    poduri_corrected = False

    for name, geom in SPEC:
        lyr = ds.GetLayerByName(name)
        if lyr is None:
            print("MISSING %s -> creating (%d)" % (name, geom))
            lyr = ds.CreateLayer(name, srs, geom)
            if name == "poduri":
                poduri_corrected = True
        else:
            actual = lyr.GetGeomType()
            if ogr.GT_Flatten(actual) != ogr.GT_Flatten(geom):
                print("WRONG TYPE %s: %s -> deleting, recreating as required type" % (name, actual))
                idx = names[name]
                ds.DeleteLayer(idx)
                lyr = ds.CreateLayer(name, srs, geom)
                if name == "poduri" and geom == ogr.wkbLineString:
                    poduri_corrected = True
            else:
                print("OK %s (geom=%d)" % (name, ogr.GT_Flatten(actual)))
        # add fields if missing
        defn = lyr.GetLayerDefn()
        existing = {defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())}
        for fname, width in FIELDS:
            if fname not in existing:
                fd = ogr.FieldDefn(fname, ogr.OFTString)
                fd.SetWidth(width)
                lyr.CreateField(fd)
                print("  + field %s(%d) on %s" % (fname, width, name))

    ds.FlushCache()
    # final report
    print("--- final schema ---")
    for i in range(ds.GetLayerCount()):
        l = ds.GetLayerByIndex(i)
        print("%d: %s (%s)" % (i + 1, l.GetName(), ogr.GeometryTypeToName(l.GetGeomType())))
    ds = None
    print("PODURI_CORRECTED=%s" % poduri_corrected)


main()
