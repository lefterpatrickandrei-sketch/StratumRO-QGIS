import glob
from osgeo import ogr

for p in sorted(glob.glob("data/processed/osm/*.geojson")) + ["data/processed/ancpi/limita_UAT.geojson"]:
    ds = ogr.Open(p)
    lyr = ds[0]
    e = lyr.GetExtent()
    print("%s | %d features | extent %.1f %.1f %.1f %.1f" % (p, lyr.GetFeatureCount(), *e))
    ds = None
