# drumuri_poligon — highway polygons from OSM via 5m buffer from drumuri_ax centerlines
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
ax_lyr = gpkg.GetLayerByName("drumuri_ax")
lyr = gpkg.CreateLayer("drumuri_poligon", S3844, geom_type=ogr.wkbMultiPolygon)
lyr.CreateField(ogr.FieldDefn("highway", ogr.OFTString))
lyr.CreateField(ogr.FieldDefn("source", ogr.OFTString))
ddef = lyr.GetLayerDefn()
lyr.StartTransaction()
n_out = 0
for feat in ax_lyr:
    geom = feat.GetGeometryRef().Clone()
    if geom.IsEmpty():
        continue
    poly = geom.Buffer(5.0, 8)
    if poly.IsEmpty():
        continue
    out = ogr.Feature(ddef)
    hw_idx = feat.GetFieldIndex("highway")
    out.SetField("highway", str(feat.GetField(hw_idx) if hw_idx >= 0 else "")[:40])
    out.SetField("source", "derived from drumuri_ax (OSM Overpass) via 5m buffer")
    out.SetGeometry(poly)
    lyr.CreateFeature(out)
    n_out += 1
lyr.CommitTransaction()
ax_lyr = None
gpkg = None
print("drumuri_poligon: %d features (5m buffer from centerlines)" % n_out)