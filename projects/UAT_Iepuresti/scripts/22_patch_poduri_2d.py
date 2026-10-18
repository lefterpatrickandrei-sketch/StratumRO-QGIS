# -*- coding: utf-8 -*-
"""
PATCH: Adaugă poduri + fix 3D→2D în GPKG PUG Iepurești
"""
import os
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"

from osgeo import ogr, osr
ogr.UseExceptions()

ROOT     = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT   = ROOT / "output"
DATA_PROC = ROOT / "data" / "processed"
SRC_GPKG = OUTPUT / "PUG_Iepuresti_Vatra_Finala.gpkg"
DST_GPKG = OUTPUT / "UAT_Iepuresti_Master.gpkg"
BRIDGES  = DATA_PROC / "osm" / "bridges.geojson"

print("=" * 70)
print(">>> PATCH: poduri + fix 3D->2D <<<")
print("=" * 70)

# CRS
srs_3844 = osr.SpatialReference(); srs_3844.ImportFromEPSG(3844)
srs_3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
srs_4326 = osr.SpatialReference(); srs_4326.ImportFromEPSG(4326)
srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans = osr.CoordinateTransformation(srs_4326, srs_3844)

def to_2d(g):
    """Forțează geometrie 2D."""
    if g is None: return None
    c = g.Clone()
    c.SetCoordinateDimension(2)
    if c.GetGeometryCount() > 0:
        for i in range(c.GetGeometryCount()):
            sub = c.GetGeometryRef(i)
            if sub:
                sub.SetCoordinateDimension(2)
    return c

# 1. Copiem GPKG sursă
if DST_GPKG.exists():
    DST_GPKG.unlink()
print(f"[1] Copiez {SRC_GPKG.name} → {DST_GPKG.name}")

import shutil
shutil.copy(str(SRC_GPKG), str(DST_GPKG))

ds = ogr.Open(str(DST_GPKG), 1)  # update mode
if ds is None:
    print("[EROARE] Nu pot deschide GPKG destinație.")
    exit(1)

# 2. Fix 3D→2D pe layerele afectate
print("[2] Convertez 3D → 2D pe 3 layere...")
fix_layers = ["zona_curti_constructii", "zona_pasuni_fanete", "zona_agricola_arabil"]

for lname in fix_layers:
    lyr = ds.GetLayerByName(lname)
    if lyr is None:
        print(f"    [!] Lipsă: {lname}")
        continue
    n_fixed = 0
    lyr.ResetReading()
    for feat in lyr:
        g = feat.GetGeometryRef()
        if g and g.GetCoordinateDimension() == 3:
            g2 = to_2d(g)
            feat.SetGeometry(g2)
            lyr.SetFeature(feat)
            n_fixed += 1
    print(f"    [OK] {lname}: {n_fixed} features convertite 2D")

# 3. Adaugă layerul poduri
print("[3] Adaug layer 'poduri' din bridges.geojson...")

# Șterge dacă există deja
if ds.GetLayerByName("poduri"):
    ds.DeleteLayer("poduri")

lyr_pod = ds.CreateLayer("poduri", srs_3844, ogr.wkbMultiLineString)
lyr_pod.CreateField(ogr.FieldDefn("zona_pug", ogr.OFTString))
lyr_pod.CreateField(ogr.FieldDefn("cod_zona", ogr.OFTString))

if BRIDGES.exists():
    br_ds = ogr.Open(str(BRIDGES))
    n = 0
    for f in br_ds.GetLayer(0):
        g = f.GetGeometryRef()
        if g is None: continue
        gc = g.Clone()
        # Dacă e WGS84, transformă
        min_x, max_x, _, _ = gc.GetEnvelope()
        if abs(min_x) < 180 and abs(max_x) < 180:
            gc.Transform(trans)
        # Forțează MultiLineString
        if gc.GetGeometryName() == "LINESTRING":
            ml = ogr.Geometry(ogr.wkbMultiLineString)
            ml.AddGeometry(gc)
            gc = ml
        elif gc.GetGeometryName() != "MULTILINESTRING":
            continue
        
        feat = ogr.Feature(lyr_pod.GetLayerDefn())
        feat.SetGeometry(gc)
        feat.SetField("zona_pug", "Poduri")
        feat.SetField("cod_zona", "BR")
        lyr_pod.CreateFeature(feat)
        n += 1
    print(f"    [OK] {n} poduri adăugate")
else:
    print(f"    [WARN] {BRIDGES} lipsește — layerul 'poduri' rămâne gol")

ds = None

# 4. Verificare finală
print("[4] Verificare finală:")
verify = ogr.Open(str(DST_GPKG))
for i in range(verify.GetLayerCount()):
    lyr = verify.GetLayerByIndex(i)
    geom_name = ogr.GeometryTypeToName(lyr.GetGeomType())
    print(f"    {i+1}: {lyr.GetName()} ({geom_name}) - {lyr.GetFeatureCount()} features")
verify = None

print("=" * 70)
print(f"[SUCCES] GPKG master: {DST_GPKG}")
print("=" * 70)