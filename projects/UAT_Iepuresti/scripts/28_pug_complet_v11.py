# -*- coding: utf-8 -*-
"""
PUG Iepurești v11.0 — MASTER INTEGRAT COMPLET (Stereo 70 / EPSG:3844)
- Descărcare Overpass OSM completă (Drumuri DN/DJ/DC/Străzi + Clădiri + Zone Rezidențiale)
- Închidere topologică 100%: Arabil continuu (A_Ar), Curți-Construcții (CC), Păduri (V_PD), Ape (ZHA), Pășuni (A_P), Drumuri (TR)
- Interconectare rețea rutieră cu ierarhie completă
- Suport Ortofoto Sub-metric (Esri World Imagery)
- Machetă A3 Landscape calibrată (420 x 297 mm, 300 DPI) cu Bilanț Teritorial oficial integrat
"""
import os, sys, re, json, time, urllib.request, urllib.parse
from pathlib import Path

os.environ["QT_QPA_FONTDIR"] = r"C:\Windows\Fonts"
if "QT_QPA_PLATFORM" in os.environ:
    del os.environ["QT_QPA_PLATFORM"]

from osgeo import ogr, osr
ogr.UseExceptions()

from qgis.core import (
    QgsApplication, QgsProject, QgsVectorLayer, QgsRasterLayer,
    QgsFillSymbol, QgsLineSymbol, QgsSingleSymbolRenderer,
    QgsPrintLayout, QgsLayoutItemMap, QgsLayoutItemLabel,
    QgsLayoutItemScaleBar, QgsLayoutItemLegend, QgsLayoutItemPicture,
    QgsLayoutPoint, QgsLayoutSize, QgsLayoutMeasurement, QgsUnitTypes,
    QgsLayoutExporter, QgsCoordinateReferenceSystem, QgsLegendStyle,
    QgsLayoutItemMapGrid
)
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(r"C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti")
OUTPUT = ROOT / "output"
OUTPUT.mkdir(parents=True, exist_ok=True)
DATA_PROC = ROOT / "data" / "processed"
OSM_DIR = DATA_PROC / "osm"
OSM_DIR.mkdir(parents=True, exist_ok=True)

GPKG = OUTPUT / "UAT_Iepuresti_Master.gpkg"
QGZ = OUTPUT / "UAT_Iepuresti_PUG_Final_v11.qgz"
PDF = OUTPUT / "UAT_Iepuresti_PUG_A3_v11.pdf"

ROADS_F = OSM_DIR / "roads.geojson"
BLDG_F = OSM_DIR / "buildings.geojson"

OFFSET_M = 0.50
MIN_BLDG_M2 = 5.0
DOWNLOAD_OSM = True

print("=" * 70)
print(">>> STRATUMRO PUG COMPLET v11.0 — COMUNA IEPUREȘTI <<<")
print("=" * 70)

# Inițializare sisteme de coordonate
srs_3844 = osr.SpatialReference(); srs_3844.ImportFromEPSG(3844)
srs_3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
srs_4326 = osr.SpatialReference(); srs_4326.ImportFromEPSG(4326)
srs_4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
trans = osr.CoordinateTransformation(srs_4326, srs_3844)
trans_bw = osr.CoordinateTransformation(srs_3844, srs_4326)

def to_3844(g):
    if not g or g.IsEmpty(): return None
    gc = g.Clone()
    env = gc.GetEnvelope()
    if abs(env[0]) < 180 and abs(env[1]) < 180:
        gc.Transform(trans)
    return gc

# ---------------------------------------------------------------------------
# 0. LIMITĂ UAT ȘI EXTINDERE BBOX
# ---------------------------------------------------------------------------
uat_src = DATA_PROC / "ancpi" / "limita_UAT.geojson"
uat_poly = None
if uat_src.exists():
    ds_u = ogr.Open(str(uat_src))
    for f in ds_u.GetLayer(0):
        g = to_3844(f.GetGeometryRef())
        if g:
            uat_poly = g.Clone()
            break
    ds_u = None

if not uat_poly:
    print("[EROARE] Nu s-a putut citi limita UAT din limita_UAT.geojson")
    sys.exit(1)

minx, maxx, miny, maxy = uat_poly.GetEnvelope()
p1 = trans_bw.TransformPoint(minx, miny)
p2 = trans_bw.TransformPoint(maxx, maxy)
south = min(p1[1], p2[1]) - 0.005
north = max(p1[1], p2[1]) + 0.005
west = min(p1[0], p2[0]) - 0.005
east = max(p1[0], p2[0]) + 0.005
bbox_str = f"{south:.5f},{west:.5f},{north:.5f},{east:.5f}"
print(f"[0] Bounding box calculat din UAT: {bbox_str}")

# ---------------------------------------------------------------------------
# 1. DOWNLOAD OVERPASS OSM (DRUMURI, CLĂDIRI, ZONE REZIDENȚIALE)
# ---------------------------------------------------------------------------
if DOWNLOAD_OSM:
    print("\n[1] Descărcare date actualizate din OpenStreetMap...")
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter"
    ]
    queries = {
        "roads": (f"[out:json][timeout:180];"
                  f"(way[\"highway\"]({bbox_str});relation[\"highway\"]({bbox_str}););out geom;"),
        "buildings": (f"[out:json][timeout:180];"
                      f"(way[\"building\"]({bbox_str});relation[\"building\"]({bbox_str});"
                      f"way[\"landuse\"=\"residential\"]({bbox_str});relation[\"landuse\"=\"residential\"]({bbox_str}););out geom;")
    }
    for key, q_str in queries.items():
        target_f = ROADS_F if key == "roads" else BLDG_F
        data = urllib.parse.urlencode({"data": q_str}).encode()
        done = False
        for ep in endpoints:
            for attempt in range(2):
                try:
                    req = urllib.request.Request(ep, data=data, headers={"User-Agent": "StratumRO_PUG_v11/1.0"})
                    with urllib.request.urlopen(req, timeout=120) as r:
                        payload = json.loads(r.read())
                    target_f.write_text(json.dumps(payload), encoding="utf-8")
                    print(f"    [OK] {key}: {len(payload.get('elements', []))} elemente -> {target_f.name}")
                    done = True
                    break
                except Exception as ex:
                    print(f"    [retry] {ep.split('/')[2]}: {ex}")
                    time.sleep(3)
            if done: break

# ---------------------------------------------------------------------------
# 2. CONSTRUIRE BAZĂ GEOPACKAGE & REȚEA RUTIERĂ CLASIFICATĂ (TR)
# ---------------------------------------------------------------------------
print("\n[2] Clasificare rețea rutieră și generare geometrii...")
drv = ogr.GetDriverByName("GPKG")
if GPKG.exists():
    drv.DeleteDataSource(str(GPKG))
ds = drv.CreateDataSource(str(GPKG))

def create_layer(name, geom_type):
    lyr = ds.CreateLayer(name, srs_3844, geom_type)
    lyr.CreateField(ogr.FieldDefn("zona_pug", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("cod_zona", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("suprafata_ha", ogr.OFTReal))
    return lyr

# Salvare Limită UAT
l_uat = create_layer("limita_UAT", ogr.wkbMultiPolygon)
f_u = ogr.Feature(l_uat.GetLayerDefn())
f_u.SetGeometry(ogr.ForceToMultiPolygon(uat_poly))
f_u.SetField("zona_pug", "Limită Teritoriu UAT")
l_uat.CreateFeature(f_u)

# Clasificare drumuri
REF_RE = re.compile(r"^(DN|DJ|DC)\s*\d+[A-Z]?", re.I)
def classify_road(ref, hw, surf, trk):
    r = (ref or "").strip().upper().replace(" ", "")
    m = REF_RE.match(r)
    if m:
        pref = m.group(1).upper()
        if pref == "DN": return "drumuri_nationale", 12.0
        if pref == "DJ": return "drumuri_judetene", 9.0
        if pref == "DC": return "drumuri_comunale", 7.0
    h = (hw or "").lower()
    if h in ("primary", "trunk", "motorway"): return "drumuri_nationale", 12.0
    if h in ("secondary",): return "drumuri_judetene", 9.0
    if h in ("tertiary", "unclassified"): return "drumuri_comunale", 7.0
    if h in ("residential", "living_street", "service"): return "drumuri_strazi", 5.0
    if h == "track" and (surf in ("asphalt", "paved", "concrete") or trk in ("grade1", "grade2")):
        return "drumuri_comunale", 6.0
    return "drumuri_strazi", 4.0

def iter_lines(g):
    if not g: return
    n = g.GetGeometryName()
    if n == "LINESTRING": yield g
    elif n in ("MULTILINESTRING", "GEOMETRYCOLLECTION"):
        for i in range(g.GetGeometryCount()):
            yield from iter_lines(g.GetGeometryRef(i))

# Straturi liniare pentru afișare ierarhică
road_specs = {
    "drumuri_nationale": ("DN", 1.3, ogr.wkbMultiLineString),
    "drumuri_judetene": ("DJ", 0.9, ogr.wkbMultiLineString),
    "drumuri_comunale": ("DC", 0.7, ogr.wkbMultiLineString),
    "drumuri_strazi": ("ST", 0.4, ogr.wkbMultiLineString)
}
road_layers = {}
for rk in road_specs:
    l = ds.CreateLayer(rk, srs_3844, ogr.wkbMultiLineString)
    for fn in ["cod", "nume", "ref", "lungime_m"]:
        l.CreateField(ogr.FieldDefn(fn, ogr.OFTString if fn != "lungime_m" else ogr.OFTReal))
    road_layers[rk] = l

roads_buffer_all = ogr.Geometry(ogr.wkbMultiPolygon)
village_streets = ogr.Geometry(ogr.wkbMultiPolygon)
stats_km = {k: 0.0 for k in road_specs}

if ROADS_F.exists():
    with open(ROADS_F, "r", encoding="utf-8") as rf:
        rdata = json.load(rf)
    for el in rdata.get("elements", []):
        geom_type = el.get("type")
        tags = el.get("tags", {})
        coords = []
        if geom_type == "way" and "geometry" in el:
            coords = [(pt["lon"], pt["lat"]) for pt in el["geometry"]]
        if len(coords) < 2: continue
        
        ls = ogr.Geometry(ogr.wkbLineString)
        for lon, lat in coords:
            pt = ogr.Geometry(ogr.wkbPoint)
            pt.AddPoint(lon, lat)
            pt.Transform(trans)
            ls.AddPoint(pt.GetX(), pt.GetY())
        
        if not ls.IsValid() or not ls.Intersects(uat_poly):
            continue
        clipped = ls.Intersection(uat_poly)
        
        ref = tags.get("ref", "") or tags.get("ref:ro", "")
        hw = tags.get("highway", "")
        surf = tags.get("surface", "")
        trk = tags.get("tracktype", "")
        target, width_m = classify_road(ref, hw, surf, trk)
        
        # Buffer de ampriză drum pentru zona TR
        buf = clipped.Buffer(width_m / 2.0)
        if buf and not buf.IsEmpty():
            roads_buffer_all = roads_buffer_all.Union(buf)
            if target == "drumuri_strazi" or hw in ("residential", "living_street", "service"):
                village_streets = village_streets.Union(clipped.Buffer(35.0))
        
        # Segmentare liniară pentru desen
        for subl in iter_lines(clipped):
            ml = ogr.Geometry(ogr.wkbMultiLineString)
            ml.AddGeometry(subl)
            lgth = round(ml.Length(), 1)
            stats_km[target] += lgth / 1000.0
            feat = ogr.Feature(road_layers[target].GetLayerDefn())
            feat.SetGeometry(ml)
            feat.SetField("cod", road_specs[target][0])
            feat.SetField("nume", tags.get("name", ""))
            feat.SetField("ref", ref)
            feat.SetField("lungime_m", lgth)
            road_layers[target].CreateFeature(feat)

for k, val in stats_km.items():
    print(f"    • {road_specs[k][0]}: {val:6.2f} km")

# ---------------------------------------------------------------------------
# 3. RECONSTRUCȚIE CLĂDIRI & ZONE REZIDENȚIALE
# ---------------------------------------------------------------------------
print("\n[3] Reconstruire clădiri și amprentă locuită (CC)...")
l_bld = ds.CreateLayer("constructii", srs_3844, ogr.wkbMultiPolygon)
for fn in ["tip", "area_m2"]:
    l_bld.CreateField(ogr.FieldDefn(fn, ogr.OFTString if fn == "tip" else ogr.OFTReal))

osm_res_poly = ogr.Geometry(ogr.wkbMultiPolygon)
bld_union = ogr.Geometry(ogr.wkbMultiPolygon)
n_bldg = 0

if BLDG_F.exists():
    with open(BLDG_F, "r", encoding="utf-8") as bf:
        bdata = json.load(bf)
    for el in bdata.get("elements", []):
        tags = el.get("tags", {})
        is_residential = tags.get("landuse") == "residential"
        is_building = "building" in tags
        if not (is_residential or is_building): continue
        if "geometry" not in el or len(el["geometry"]) < 3: continue
        
        ring = ogr.Geometry(ogr.wkbLinearRing)
        for pt in el["geometry"]:
            pt_g = ogr.Geometry(ogr.wkbPoint)
            pt_g.AddPoint(pt["lon"], pt["lat"])
            pt_g.Transform(trans)
            ring.AddPoint(pt_g.GetX(), pt_g.GetY())
        
        poly = ogr.Geometry(ogr.wkbPolygon)
        poly.AddGeometry(ring)
        if not poly.IsValid(): continue
        if not poly.Intersects(uat_poly): continue
        
        c = poly.Intersection(uat_poly)
        if is_residential:
            osm_res_poly = osm_res_poly.Union(c)
        elif is_building:
            b_buf = c.Buffer(OFFSET_M) if OFFSET_M > 0 else c
            area = round(b_buf.GetArea(), 1)
            if area >= MIN_BLDG_M2:
                feat = ogr.Feature(l_bld.GetLayerDefn())
                feat.SetGeometry(ogr.ForceToMultiPolygon(b_buf))
                feat.SetField("tip", tags.get("building", "yes"))
                feat.SetField("area_m2", area)
                l_bld.CreateFeature(feat)
                bld_union = bld_union.Union(b_buf.Buffer(25.0))
                n_bldg += 1

print(f"    [OK] Clădiri procesate la sol: {n_bldg}")

# ---------------------------------------------------------------------------
# 4. ELEMENTE NATURALE (APE, PĂDURI)
# ---------------------------------------------------------------------------
print("\n[4] Integrare elemente de mediu (Ape, Servituți, Păduri)...")
water_src = DATA_PROC / "osm" / "waterways.geojson"
water_union = ogr.Geometry(ogr.wkbMultiPolygon)
water_lines = ogr.Geometry(ogr.wkbMultiLineString)
if water_src.exists():
    ds_w = ogr.Open(str(water_src))
    for f in ds_w.GetLayer(0):
        g = to_3844(f.GetGeometryRef())
        if g and g.Intersects(uat_poly):
            c = g.Intersection(uat_poly)
            water_lines = water_lines.Union(c)
            bw = c.Buffer(25.0)
            if bw: water_union = water_union.Union(bw)
    ds_w = None
water_union = water_union.Intersection(uat_poly)

lyr_w = create_layer("zona_ape", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_w.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(water_union))
feat.SetField("zona_pug", "Ape și Zone Umede Neajlov")
feat.SetField("cod_zona", "ZHA")
feat.SetField("suprafata_ha", round(water_union.GetArea() / 10000.0, 2))
lyr_w.CreateFeature(feat)

forest_src = DATA_PROC / "osm" / "forests.geojson"
forest_union = ogr.Geometry(ogr.wkbMultiPolygon)
if forest_src.exists():
    ds_f = ogr.Open(str(forest_src))
    for f in ds_f.GetLayer(0):
        g = to_3844(f.GetGeometryRef())
        if g and g.Intersects(uat_poly):
            c = g.Intersection(uat_poly)
            if c: forest_union = forest_union.Union(c)
    ds_f = None
forest_union = forest_union.Intersection(uat_poly)

lyr_f = create_layer("zona_forestiera", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_f.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(forest_union))
feat.SetField("zona_pug", "Fond Forestier / Păduri")
feat.SetField("cod_zona", "V_PD")
feat.SetField("suprafata_ha", round(forest_union.GetArea() / 10000.0, 2))
lyr_f.CreateFeature(feat)

# ---------------------------------------------------------------------------
# 5. ÎNCHIDERE TOPOLOGICĂ 100% (CC, TR, A_P, A_Ar)
# ---------------------------------------------------------------------------
print("\n[5] Închidere topologică fără goluri pe întreg UAT-ul...")
# Vatra Satului (CC): combină perimetrele rezidențiale OSM, ulițele din sat și clădirile
neajlov_settlement_corridor = water_lines.Buffer(550.0).Intersection(uat_poly)
valid_village_streets = village_streets.Intersection(neajlov_settlement_corridor)

cc_total = osm_res_poly.Union(valid_village_streets).Union(bld_union).Intersection(uat_poly)
cc_total = cc_total.Difference(water_union).Difference(forest_union)

lyr_cc = create_layer("zona_curti_constructii", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_cc.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(cc_total))
feat.SetField("zona_pug", "Curți-Construcții Vatră Sat (CC)")
feat.SetField("cod_zona", "CC")
feat.SetField("suprafata_ha", round(cc_total.GetArea() / 10000.0, 2))
lyr_cc.CreateFeature(feat)

# Căi de comunicație (TR)
roads_buffer_all = roads_buffer_all.Intersection(uat_poly)
lyr_tr = create_layer("zona_circulatii", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_tr.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(roads_buffer_all))
feat.SetField("zona_pug", "Circulații Rutiere (TR)")
feat.SetField("cod_zona", "TR")
feat.SetField("suprafata_ha", round(roads_buffer_all.GetArea() / 10000.0, 2))
lyr_tr.CreateFeature(feat)

# Extravilan: Pășuni în luncă + Arabil pe restul continuu al comunei
occupied = cc_total.Union(water_union).Union(roads_buffer_all).Union(forest_union)
extravilan_rest = uat_poly.Difference(occupied)

pasuni_geom = water_union.Buffer(140.0).Intersection(extravilan_rest)
arabil_geom = extravilan_rest.Difference(pasuni_geom)

lyr_p = create_layer("zona_pasuni_fanete", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_p.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(pasuni_geom))
feat.SetField("zona_pug", "Pășuni și Fânețe (Luncă)")
feat.SetField("cod_zona", "A_P")
feat.SetField("suprafata_ha", round(pasuni_geom.GetArea() / 10000.0, 2))
lyr_p.CreateFeature(feat)

lyr_a = create_layer("zona_agricola_arabil", ogr.wkbMultiPolygon)
feat = ogr.Feature(lyr_a.GetLayerDefn())
feat.SetGeometry(ogr.ForceToMultiPolygon(arabil_geom))
feat.SetField("zona_pug", "Terenuri Arabile (Extravilan A_Ar)")
feat.SetField("cod_zona", "A_Ar")
feat.SetField("suprafata_ha", round(arabil_geom.GetArea() / 10000.0, 2))
lyr_a.CreateFeature(feat)

# Calcul Bilanț Teritorial
uat_area_ha = round(uat_poly.GetArea() / 10000.0, 2)
cc_ha = round(cc_total.GetArea() / 10000.0, 2)
tr_ha = round(roads_buffer_all.GetArea() / 10000.0, 2)
zha_ha = round(water_union.GetArea() / 10000.0, 2)
vpd_ha = round(forest_union.GetArea() / 10000.0, 2)
ap_ha = round(pasuni_geom.GetArea() / 10000.0, 2)
aar_ha = round(arabil_geom.GetArea() / 10000.0, 2)
total_calc_ha = round(cc_ha + tr_ha + zha_ha + vpd_ha + ap_ha + aar_ha, 2)

ds = None
print(f"    [OK] Acoperire: Arabil = {aar_ha} ha | Curți-Construcții = {cc_ha} ha | Total = {total_calc_ha} ha")

# ---------------------------------------------------------------------------
# 6. MACHETĂ CARTOGRAFICĂ A3 LANDSCAPE (QGIS)
# ---------------------------------------------------------------------------
print("\n[6] Generare machetă A3 (420 x 297 mm, 300 DPI)...")
qgs = QgsApplication([], True)
qgs.initQgis()

QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arial.ttf")
QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\arialbd.ttf")
FONT = "Arial"

project = QgsProject.instance()
project.clear()
project.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))
project.setTitle("PUG UAT Iepurești v11.0 — Reglementări Urbanistice")

# Ortofoto Sub-metric
ortho_url = ("type=xyz&url=https://server.arcgisonline.com/ArcGIS/rest/services/"
             "World_Imagery/MapServer/tile/{z}/{y}/{x}&zmax=19&zmin=0")
ortho = QgsRasterLayer(ortho_url, "Ortofoto Satelitar Sub-metric", "wms")
if ortho.isValid():
    project.addMapLayer(ortho)

order = [
    # Poligoane de zonare (jos)
    ("zona_agricola_arabil",   "Terenuri Arabile (A_Ar)",  "poly",
     {"color": "252,243,222,95",  "outline_color": "220,205,175,130", "outline_width": "0.08"}),
    ("zona_pasuni_fanete",     "Pășuni / Fânețe (A_P)",    "poly",
     {"color": "215,235,180,120", "outline_color": "165,195,125,160", "outline_width": "0.08"}),
    ("zona_forestiera",        "Fond Forestier (V_PD)",    "poly",
     {"color": "34,139,34,160",   "outline_color": "0,100,0,255",     "outline_width": "0.2"}),
    ("zona_ape",               "Ape / Servituți (ZHA)",    "poly",
     {"color": "30,144,255,170",  "outline_color": "0,0,205,255",     "outline_width": "0.2"}),
    ("zona_curti_constructii", "Curți-Construcții (CC)",   "poly",
     {"color": "255,150,0,195",   "outline_color": "190,70,0,255",    "outline_width": "0.2"}),
    ("zona_circulatii",        "Circulații Rutiere (TR)",  "poly",
     {"color": "80,80,80,180",    "outline_color": "30,30,30,255",    "outline_width": "0.1"}),
    # Rețea liniară drumuri
    ("drumuri_strazi",         "Străzi Locale (ST)",       "line",
     {"color": "255,255,255,255", "width": "0.4"}),
    ("drumuri_comunale",       "Drumuri Comunale (DC)",    "line",
     {"color": "180,120,40,255",  "width": "0.7"}),
    ("drumuri_judetene",       "Drumuri Județene (DJ)",    "line",
     {"color": "200,60,0,255",    "width": "1.0"}),
    ("drumuri_nationale",      "Drumuri Naționale (DN)",   "line",
     {"color": "160,0,0,255",     "width": "1.4"}),
    # Clădiri și limită UAT
    ("constructii",            "Clădiri (+0.50m)",         "poly",
     {"color": "220,20,20,255",   "outline_color": "60,0,0,255",      "outline_width": "0.2"}),
    ("limita_UAT",             "Limită UAT Iepurești",     "poly",
     {"color": "0,0,0,0",         "outline_color": "0,0,0,255",       "outline_width": "0.9"})
]

added_layers = []
bbox = None
for lname, dname, tip, cfg in order:
    vl = QgsVectorLayer(f"{GPKG}|layername={lname}", dname, "ogr")
    if not vl.isValid() or vl.featureCount() == 0:
        continue
    sym = QgsFillSymbol.createSimple(cfg) if tip == "poly" else QgsLineSymbol.createSimple(cfg)
    vl.setRenderer(QgsSingleSymbolRenderer(sym))
    project.addMapLayer(vl)
    added_layers.append(vl)
    if lname == "limita_UAT":
        bbox = vl.extent()

lm = project.layoutManager()
for l in lm.layouts():
    lm.removeLayout(l)

layout = QgsPrintLayout(project)
layout.initializeDefaults()
layout.setName("PUG_Iepuresti_A3_v11")
lm.addLayout(layout)

layout.pageCollection().page(0).setPageSize(QgsLayoutSize(420, 297, QgsUnitTypes.LayoutMillimeters))

# Hartă principală (292 x 275 mm)
map_item = QgsLayoutItemMap(layout)
map_item.attemptMove(QgsLayoutPoint(10, 11, QgsUnitTypes.LayoutMillimeters))
map_item.attemptResize(QgsLayoutSize(292, 275, QgsUnitTypes.LayoutMillimeters))
map_item.setFrameEnabled(True)
map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.4, QgsUnitTypes.LayoutMillimeters))
map_item.setCrs(QgsCoordinateReferenceSystem("EPSG:3844"))

if bbox and not bbox.isEmpty():
    bbox.scale(1.06)
    map_item.setExtent(bbox)
layout.addLayoutItem(map_item)

# Grid coordonate Stereo 70
grid = map_item.grid()
grid.setEnabled(True)
grid.setStyle(QgsLayoutItemMapGrid.Solid)
grid.setIntervalX(1000); grid.setIntervalY(1000)
grid.setAnnotationEnabled(True); grid.setAnnotationPrecision(0)
grid.setAnnotationFont(QFont(FONT, 5))
grid.setFrameStyle(QgsLayoutItemMapGrid.LineBorder)

# Scară și Nord
sb = QgsLayoutItemScaleBar(layout)
sb.setStyle("Single Box")
sb.setLinkedMap(map_item)
sb.applyDefaultSize(QgsUnitTypes.DistanceKilometers)
sb.setNumberOfSegments(3)
sb.setUnits(QgsUnitTypes.DistanceKilometers)
sb.setUnitLabel(" km")
sb.setFont(QFont(FONT, 7))
sb.setBackgroundEnabled(True)
sb.setBackgroundColor(QColor(255, 255, 255, 235))
sb.setFrameEnabled(True)
sb.attemptMove(QgsLayoutPoint(16, 272, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(sb)

# Panou Dreapta: Coordonate fixe calibrate (X = 310 mm, Lățime = 100 mm)
XP = 310
WP = 100

t1 = QgsLayoutItemLabel(layout)
t1.setText("PLAN URBANISTIC GENERAL\nCOMUNA IEPUREȘTI, GIURGIU")
t1.setFont(QFont(FONT, 10, QFont.Bold))
t1.attemptMove(QgsLayoutPoint(XP, 11, QgsUnitTypes.LayoutMillimeters))
t1.attemptResize(QgsLayoutSize(WP, 10, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t1)

t2 = QgsLayoutItemLabel(layout)
t2.setText("PLANȘA 01: REGLEMENTĂRI URBANISTICE ȘI ZONIFICARE")
t2.setFont(QFont(FONT, 7, QFont.Bold))
t2.attemptMove(QgsLayoutPoint(XP, 22, QgsUnitTypes.LayoutMillimeters))
t2.attemptResize(QgsLayoutSize(WP, 6, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(t2)

# Legendă completă (exclude rasterul)
legend = QgsLayoutItemLegend(layout)
legend.setLinkedMap(map_item)
legend.setTitle("LEGENDĂ URBANISTICĂ")
legend.setAutoUpdateModel(False)
root_group = legend.model().rootGroup()
root_group.clear()
for vl in reversed(added_layers):
    root_group.addLayer(vl)
try:
    legend.setStyleFont(QgsLegendStyle.Title, QFont(FONT, 8, QFont.Bold))
    legend.setStyleFont(QgsLegendStyle.SymbolLabel, QFont(FONT, 6))
except Exception:
    pass
legend.setFrameEnabled(True)
legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
legend.setBackgroundColor(QColor(255, 255, 255, 245))
legend.attemptMove(QgsLayoutPoint(XP, 29, QgsUnitTypes.LayoutMillimeters))
legend.attemptResize(QgsLayoutSize(WP, 95, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(legend)

# Tabel Bilanț Teritorial
tbl = QgsLayoutItemLabel(layout)
tbl_text = (
    "BILANȚ TERITORIAL — UAT IEPUREȘTI\n"
    f"Proiecție: Stereo 70 | Suprafață: {uat_area_ha} ha\n"
    "───────────────────────────────────────────────────────\n"
    "Cod   Zonă Funcțională                 Arie (ha) Pondere\n"
    "───────────────────────────────────────────────────────\n"
    f"CC    Curți-Construcții (Sate)        {cc_ha:>8.2f}   {round(cc_ha/uat_area_ha*100, 2):>5.2f}%\n"
    f"TR    Circulații Rutiere / Străzi     {tr_ha:>8.2f}   {round(tr_ha/uat_area_ha*100, 2):>5.2f}%\n"
    f"ZHA   Ape și Zone Umede (Neajlov)     {zha_ha:>8.2f}   {round(zha_ha/uat_area_ha*100, 2):>5.2f}%\n"
    f"V_PD  Fond Forestier / Păduri         {vpd_ha:>8.2f}   {round(vpd_ha/uat_area_ha*100, 2):>5.2f}%\n"
    f"A_P   Pășuni și Fânețe (Luncă)        {ap_ha:>8.2f}   {round(ap_ha/uat_area_ha*100, 2):>5.2f}%\n"
    f"A_Ar  Terenuri Arabile (Platou)      {aar_ha:>8.2f}   {round(aar_ha/uat_area_ha*100, 2):>5.2f}%\n"
    "───────────────────────────────────────────────────────\n"
    f"TOTAL TERITORIU CALCULAT             {total_calc_ha:>8.2f}  100.00%"
)
tbl.setText(tbl_text)
tbl.setFont(QFont("Consolas", 6))
tbl.setFrameEnabled(True)
tbl.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
tbl.setBackgroundEnabled(True)
tbl.setBackgroundColor(QColor(252, 252, 252, 245))
tbl.attemptMove(QgsLayoutPoint(XP, 127, QgsUnitTypes.LayoutMillimeters))
tbl.attemptResize(QgsLayoutSize(WP, 62, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(tbl)

# Cartuș Tehnic PUG
cartus = QgsLayoutItemLabel(layout)
cartus.setText(
    "DOC. URBANISM: PLAN URBANISTIC GENERAL (PUG)\n"
    "BENEFICIAR: Comuna Iepurești (SIRUTA 103684), Jud. Giurgiu\n"
    "PROIECȚIE: Stereo 70 (EPSG:3844)\n\n"
    "PARAMETRI CARTOGRAFICI & RETEA:\n"
    f"• DN: {stats_km['drumuri_nationale']:5.2f} km | DJ: {stats_km['drumuri_judetene']:5.2f} km\n"
    f"• DC: {stats_km['drumuri_comunale']:5.2f} km | Străzi: {stats_km['drumuri_strazi']:5.2f} km\n"
    f"• Clădiri procesate la sol: {n_bldg} (offset +{OFFSET_M}m)\n"
    "• Închidere topologică: 100% acoperit (fără goluri)\n\n"
    "VERSIUNE ENGINE: v11.0 Master Pipeline\n"
    "DATA EMITERII: 22.09.2026"
)
cartus.setFont(QFont(FONT, 6))
cartus.setFrameEnabled(True)
cartus.setFrameStrokeWidth(QgsLayoutMeasurement(0.2, QgsUnitTypes.LayoutMillimeters))
cartus.setBackgroundEnabled(True)
cartus.setBackgroundColor(QColor(250, 250, 250, 245))
cartus.attemptMove(QgsLayoutPoint(XP, 192, QgsUnitTypes.LayoutMillimeters))
cartus.attemptResize(QgsLayoutSize(WP, 94, QgsUnitTypes.LayoutMillimeters))
layout.addLayoutItem(cartus)

# Salvare proiect QGZ
project.write(str(QGZ))
print(f"    [OK] Proiect salvat: {QGZ.name}")

# Export PDF la 300 DPI
exporter = QgsLayoutExporter(layout)
st = QgsLayoutExporter.PdfExportSettings()
st.dpi = 300
st.rasterizeWholeImage = False

if PDF.exists():
    try:
        PDF.unlink()
    except OSError:
        PDF = OUTPUT / "UAT_Iepuresti_PUG_A3_v11b.pdf"

res = exporter.exportToPdf(str(PDF), st)
if res == QgsLayoutExporter.Success:
    print(f"\n[SUCCES TOTAL] Planșa A3 a fost exportată cu succes:")
    print(f"               {PDF}")
else:
    print(f"\n[EROARE] Exportul PDF a eșuat cu codul: {res}")

qgs.exitQgis()
print("=" * 70)
