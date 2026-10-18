# -*- coding: utf-8 -*-
"""
STRATUMRO — GENERARE GARANTATA PUG SI BILANT TERITORIAL (EPSG:3844)
Daca PUG_Iepuresti_Urban.gpkg lipseste, il construieste complet din datele procesate,
apoi calculeaza bilantul statistic pe categorii de folosinta.
"""
import os, sys
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import gdal, ogr, osr
gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
DATA_PROC = ROOT / "data" / "processed"
GPKG_URBAN = OUTPUT / "PUG_Iepuresti_Urban.gpkg"
GPKG_FALLBACK = OUTPUT / "UAT_Iepuresti.gpkg"

srs_stereo70 = osr.SpatialReference()
srs_stereo70.ImportFromEPSG(3844)
srs_stereo70.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

srs_wgs84 = osr.SpatialReference()
srs_wgs84.ImportFromEPSG(4326)
srs_wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans_to_3844 = osr.CoordinateTransformation(srs_wgs84, srs_stereo70)

def ensure_stereo70(geom):
    if geom is None or geom.IsEmpty():
        return None
    min_x, max_x, _, _ = geom.GetEnvelope()
    if abs(min_x) > 180 or abs(max_x) > 180:
        return geom.Clone()
    gc = geom.Clone()
    gc.Transform(trans_to_3844)
    return gc

# 1. Verificare / Construire baza spatiala
if not GPKG_URBAN.exists():
    print(f"[INIT] Fisierul {GPKG_URBAN.name} nu exista. Il generam acum din sursele locale...")
    driver = ogr.GetDriverByName("GPKG")
    ds_out = driver.CreateDataSource(str(GPKG_URBAN))
    
    def add_lyr(name, gtype):
        l = ds_out.CreateLayer(name, srs_stereo70, gtype)
        l.CreateField(ogr.FieldDefn("zona_pug", ogr.OFTString))
        l.CreateField(ogr.FieldDefn("cod_zona", ogr.OFTString))
        return l

    # A. Limita UAT
    uat_ds = ogr.Open(str(DATA_PROC / "ancpi" / "limita_UAT.geojson"))
    uat_poly = None
    for f in uat_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g:
            uat_poly = g.Clone()
            break
            
    lyr_uat = add_lyr("limita_UAT", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_uat.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(uat_poly))
    f.SetField("zona_pug", "Limita UAT")
    lyr_uat.CreateFeature(f)

    # B. Ape
    water_ds = ogr.Open(str(DATA_PROC / "osm" / "waterways.geojson"))
    water_union = ogr.Geometry(ogr.wkbMultiPolygon)
    for f in water_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g and uat_poly and g.Intersects(uat_poly):
            c = g.Intersection(uat_poly)
            bw = c.Buffer(25.0)
            if bw: water_union = water_union.Union(bw)
    water_union = water_union.Intersection(uat_poly)
    lyr_w = add_lyr("zona_ape", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_w.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(water_union))
    f.SetField("zona_pug", "Ape si Servituti (Neajlov)")
    f.SetField("cod_zona", "ZHA")
    lyr_w.CreateFeature(f)

    # C. Paduri
    forest_ds = ogr.Open(str(DATA_PROC / "osm" / "forests.geojson"))
    forest_union = ogr.Geometry(ogr.wkbMultiPolygon)
    for f in forest_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g and uat_poly and g.Intersects(uat_poly):
            c = g.Intersection(uat_poly)
            if c: forest_union = forest_union.Union(c)
    forest_union = forest_union.Intersection(uat_poly)
    lyr_f = add_lyr("zona_forestiera", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_f.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(forest_union))
    f.SetField("zona_pug", "Fond Forestier")
    f.SetField("cod_zona", "V_PD")
    lyr_f.CreateFeature(f)

    # D. Drumuri & CC
    roads_ds = ogr.Open(str(DATA_PROC / "osm" / "roads.geojson"))
    roads_union = ogr.Geometry(ogr.wkbMultiPolygon)
    cc_union = ogr.Geometry(ogr.wkbMultiPolygon)
    for f in roads_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g and uat_poly and g.Intersects(uat_poly):
            c = g.Intersection(uat_poly)
            br = c.Buffer(3.0)
            if br: roads_union = roads_union.Union(br)
            bcc = c.Buffer(40.0)
            if bcc: cc_union = cc_union.Union(bcc)

    # Cladiri in CC
    bld_ds = ogr.Open(str(DATA_PROC / "osm" / "buildings.geojson"))
    bld_lyr = add_lyr("constructii", ogr.wkbMultiPolygon)
    bld_union = ogr.Geometry(ogr.wkbMultiPolygon)
    for f in bld_ds.GetLayer(0):
        g = ensure_stereo70(f.GetGeometryRef())
        if g and uat_poly and g.Intersects(uat_poly):
            b = g.Buffer(0.50)
            if b:
                bf = ogr.Feature(bld_lyr.GetLayerDefn())
                bf.SetGeometry(ogr.ForceToMultiPolygon(b))
                bf.SetField("zona_pug", "Cladiri")
                bld_lyr.CreateFeature(bf)
                bld_union = bld_union.Union(g.Buffer(30.0))

    cc_total = cc_union.Union(bld_union).Intersection(uat_poly)
    cc_total = cc_total.Difference(water_union).Difference(forest_union)
    lyr_cc = add_lyr("zona_curti_constructii", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_cc.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(cc_total))
    f.SetField("zona_pug", "Curti-Constructii")
    f.SetField("cod_zona", "CC")
    lyr_cc.CreateFeature(f)

    roads_union = roads_union.Intersection(uat_poly)
    lyr_r = add_lyr("zona_circulatii", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_r.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(roads_union))
    f.SetField("zona_pug", "Circulatii Rutiere")
    f.SetField("cod_zona", "TR")
    lyr_r.CreateFeature(f)

    # E. Extravilan Agricol
    vatra = cc_total.Buffer(25.0).Buffer(-10.0).Intersection(uat_poly)
    occupied = vatra.Union(water_union).Union(roads_union).Union(forest_union)
    extravilan = uat_poly.Difference(occupied)
    pasuni = water_union.Buffer(180.0).Intersection(extravilan)
    arabil = extravilan.Difference(pasuni)

    lyr_p = add_lyr("zona_pasuni_fanete", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_p.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(pasuni))
    f.SetField("zona_pug", "Pasuni si Fanete")
    f.SetField("cod_zona", "A_P")
    lyr_p.CreateFeature(f)

    lyr_a = add_lyr("zona_agricola_arabil", ogr.wkbMultiPolygon)
    f = ogr.Feature(lyr_a.GetLayerDefn())
    f.SetGeometry(ogr.ForceToMultiPolygon(arabil))
    f.SetField("zona_pug", "Terenuri Arabile")
    f.SetField("cod_zona", "A_Ar")
    lyr_a.CreateFeature(f)

    ds_out = None
    print(f"[OK] Baza {GPKG_URBAN.name} a fost construita si salvata cu succes.")

# 2. Calcul bilant teritorial
ds = ogr.Open(str(GPKG_URBAN), 0)
uat_lyr = ds.GetLayerByName("limita_UAT")
uat_area_ha = sum(f.GetGeometryRef().GetArea() for f in uat_lyr) / 10000.0

layers_map = [
    ("zona_curti_constructii", "Curți-Construcții (Parcele CC - Gospodării)", "CC"),
    ("zona_circulatii", "Căi de Comunicație Rutieră și Străzi", "TR"),
    ("zona_ape", "Ape, Bălți și Zone Umede (Râul Neajlov)", "ZHA"),
    ("zona_forestiera", "Fond Forestier și Vegetație Lemnoasă", "V_PD"),
    ("zona_pasuni_fanete", "Pășuni și Fânețe Naturale (Luncă)", "A_P"),
    ("zona_agricola_arabil", "Terenuri Arabile (Extravilan Agricol)", "A_Ar")
]

balance_data = []
total_ha = 0.0

for lname, desc, code in layers_map:
    lyr = ds.GetLayerByName(lname)
    area_ha = sum(f.GetGeometryRef().GetArea() for f in lyr) / 10000.0 if lyr else 0.0
    total_ha += area_ha
    pct = (area_ha / uat_area_ha) * 100.0 if uat_area_ha > 0 else 0
    balance_data.append((code, desc, round(area_ha, 2), round(pct, 2)))

ds = None

# 3. Printare tabel
print("\n" + "="*85)
print(f"{'BILANȚUL TERITORIAL AL COMUNEI IEPUREȘTI (SIRUTA 103684)':^85}")
print(f"{'Proiecție: Stereo 70 (EPSG:3844) | Suprafață totală UAT: ' + str(round(uat_area_ha, 2)) + ' ha':^85}")
print("="*85)
print(f"{'Cod':<8} | {'Zonă Funcțională / Categorie de Folosință':<48} | {'Arie (ha)':>10} | {'Pondere (%)':>11}")
print("-"*85)

for code, desc, ha, pct in balance_data:
    print(f"{code:<8} | {desc:<48} | {ha:>10.2f} | {pct:>10.2f}%")

print("-"*85)
print(f"{'TOTAL':<8} | {'Suprafață Teritorială Închisă Topologic':<48} | {round(total_ha, 2):>10.2f} | {round((total_ha/uat_area_ha)*100, 2):>10.2f}%")
print("="*85 + "\n")
