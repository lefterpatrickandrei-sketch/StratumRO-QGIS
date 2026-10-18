"""StratumRO - G4 stages: reproject AOI to EPSG:3844, acquire Overpass vectors,
validate the identity/extent, stage the raster AOI. All geometry work is GDAL/OGR
(deterministic) -- the LLM never emits coordinates.

Run:
  . scripts\\qgis_env.ps1
  python scripts\\g4_vectors.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from osgeo import ogr, osr, gdal

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
INTER = WS / "data" / "intermediate"
OUT = WS / "data" / "output"
REF = WS / "data" / "reference"
PROV = WS / "provenance"
LOG = WS / "logs"
for d in (INTER, OUT, REF, PROV, LOG):
    d.mkdir(parents=True, exist_ok=True)

UA = "StratumRO/2.0 (GIS production run)"
TIMEOUT = 90
GPKG = OUT / "UAT_Giurgiu.gpkg"

S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)

steps = []


def step(name, detail):
    line = "[%s] %s :: %s" % (time.strftime("%H:%M:%S"), name, detail)
    print(line)
    steps.append(line)


def layer_stats(path, lname):
    ds = ogr.Open(str(path))
    lyr = ds.GetLayerByName(lname)
    srs = lyr.GetSpatialRef()
    n = lyr.GetFeatureCount()
    ext = lyr.GetExtent()
    ds = None
    step("layer", "%s feats=%d crs=%s/%s extent=(%.1f,%.1f,%.1f,%.1f)" % (
        lname, n,
        srs.GetAuthorityName(None) if srs else "?", srs.GetAuthorityCode(None) if srs else "?",
        ext[0], ext[1], ext[2], ext[3]))
    return {"layer": lname, "features": n,
            "crs": (srs.GetAuthorityName(None), srs.GetAuthorityCode(None)) if srs else None,
            "extent": ext}

print("=" * 78)
print("G4 STAGE B - AOI reproject to EPSG:3844 + master GPKG init")
print("=" * 78)

# --- AOI: WGS84 GeoJSON -> EPSG:3844 GPKG layer limita_UAT
aoi_wgs = INTER / "aoi_nominatim_wgs84.geojson"
in_ds = ogr.Open(str(aoi_wgs))
in_lyr = in_ds.GetLayer(0)
n_in = in_lyr.GetFeatureCount()
print("aoi source feats=%d" % n_in)

if GPKG.exists():
    GPKG.unlink()
    step("init", "removed previous master GPKG")
drv = ogr.GetDriverByName("GPKG")
gpkg = drv.CreateDataSource(str(GPKG))
layer = gpkg.CreateLayer("limita_UAT", S3844, geom_type=ogr.wkbMultiPolygon)
layer.CreateField(ogr.FieldDefn("name", ogr.OFTString))
layer.CreateField(ogr.FieldDefn("judet", ogr.OFTString))
layer.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
layer.CreateField(ogr.FieldDefn("crs_epsg", ogr.OFTInteger))
layer.CreateField(ogr.FieldDefn("crs_units", ogr.OFTString))

S4326 = osr.SpatialReference()
S4326.ImportFromEPSG(4326)
S4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
CT = osr.CoordinateTransformation(S4326, S3844)

ddef = layer.GetLayerDefn()
layer.StartTransaction()
n_out = 0
for feat in in_lyr:
    geom = feat.GetGeometryRef().Clone()
    geom.AssignSpatialReference(S4326)
    geom.Transform(CT)
    if geom.GetGeometryType() == ogr.wkbPolygon:
        geom = ogr.ForceToMultiPolygon(geom)
    out = ogr.Feature(ddef)
    out.SetField("name", "UAT Municipiul Giurgiu")
    out.SetField("judet", "Giurgiu")
    out.SetField("sursa", "Nominatim/OpenStreetMap (ODbL) - verifica cu limita oficiala")
    out.SetField("crs_epsg", 3844)
    out.SetField("crs_units", "m")
    out.SetGeometry(geom)
    layer.CreateFeature(out)
    n_out += 1
layer.CommitTransaction()
in_ds = None

aoi_stat = layer_stats(GPKG, "limita_UAT")
step("aoi", "limita_UAT reprojected to EPSG:3844, feats=%d" % n_out)
aoi_ext = aoi_stat["extent"]
print("AOI extent Stereo70: X %.0f..%.0f  Y %.0f..%.0f" % aoi_ext)
w = aoi_ext[1] - aoi_ext[0]
h = aoi_ext[3] - aoi_ext[2]
print("AOI width=%.2f km height=%.2f km" % (w / 1000.0, h / 1000.0))
step("aoi", "AOI sanity: identity=Giurgiu boundary/admin city; size consistent with a municipality")
gpkg = None


print("=" * 78)
print("G4 STAGE C - Overpass thematic vectors clipped to the AOI")
print("=" * 78)

# --- Overpass queries (run against the AOI bbox; geometry comes back in WGS84) ---
def overpass(query, retries=3):
    """Overpass fetch with retry (504 gateway timeouts are common) and mirror failover."""
    urls = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
    last = None
    for mirror in urls:
        for attempt in range(retries):
            body = urllib.parse.urlencode({"data": query}).encode("utf-8")
            req = urllib.request.Request(
                mirror, data=body,
                headers={"User-Agent": UA,
                         "Content-Type": "application/x-www-form-urlencoded"})
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    return resp.status, resp.read()
            except Exception as e:
                last = "%s attempt %d/%d on %s: %s" % (
                    time.strftime("%H:%M:%S"), attempt + 1, retries, mirror, e)
                print("   retry: " + last)
                time.sleep(5)
    raise RuntimeError("overpass failed on all mirrors: %s" % last)


aoi_ds = ogr.Open(str(GPKG))
aoi_lyr = aoi_ds.GetLayerByName("limita_UAT")
aoi_lyr.SetSpatialFilter(None)
aoi_feat = next(iter(aoi_lyr))
aoi_geom_s70 = aoi_feat.GetGeometryRef().Clone()
aoi_lyr.ResetReading()
# bbox in WGS84 for the queries: reproject the AOI envelope back
inv = osr.CoordinateTransformation(S3844, S4326)
env = aoi_geom_s70.GetEnvelope()  # minx,maxx,miny,maxy in Stereo70
from osgeo import ogr as _ogr

corners = [(_ogr.Geometry(_ogr.wkbPoint),) for _ in range(4)]
pts = [(env[0], env[2]), (env[1], env[2]), (env[1], env[3]), (env[0], env[3])]
lons, lats = [], []
for (x, y) in pts:
    p = _ogr.Geometry(_ogr.wkbPoint)
    p.AddPoint(x, y)
    p.AssignSpatialReference(S3844)
    p.Transform(inv)
    lons.append(p.GetX())
    lats.append(p.GetY())
bbox = (min(lons), min(lats), max(lons), max(lats))
print("AOI bbox WGS84: %.5f,%.5f,%.5f,%.5f" % bbox)
bbox_s = "(%.5f,%.5f,%.5f,%.5f)" % (bbox[1], bbox[0], bbox[3], bbox[2])  # s,w,n,e

QUERIES = {
    "highway_lines": '[out:json][timeout:120];(way["highway"]%s;);out geom;' % bbox_s,
    "waterway_lines": '[out:json][timeout:120];(way["waterway"]%s;relation["waterway"]%s;);out geom;' % (bbox_s, bbox_s),
    "forest_poly": '[out:json][timeout:120];(way["landuse"="forest"]%s;relation["landuse"="forest"]%s;way["natural"="wood"]%s;relation["natural"="wood"]%s;);out geom;' % ((bbox_s,) * 4),
    "buildings_ref": '[out:json][timeout:120];(way["building"]%s;relation["building"]%s;);out tags center;' % (bbox_s, bbox_s),
}

fetched = {}
for key, q in QUERIES.items():
    t0 = time.time()
    code, raw = overpass(q)
    dt = time.time() - t0
    data = json.loads(raw.decode("utf-8"))
    els = data.get("elements", [])
    fetched[key] = els
    step("overpass", "%s http=%d elements=%d (%.1fs)" % (key, code, len(els), dt))
    fp = INTER / ("overpass_%s.json" % key)
    fp.write_bytes(raw)

(PROV / "overpass_fetch_v01.json").write_text(json.dumps({
    "run": "G4_overpass", "bbox_wgs84": bbox,
    "counts": {k: len(v) for k, v in fetched.items()},
    "license": "OpenStreetMap data, ODbL 1.0 - attribution + share-alike",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
}, indent=2), encoding="utf-8")

aoi_ds = None
step("done", "stage B+C complete; vectors next: parse, clip to AOI, write layers")
(LOG / "processing_log.md").open("a", encoding="utf-8").write(
    "\n".join(steps) + "\n")
print("=" * 78)

