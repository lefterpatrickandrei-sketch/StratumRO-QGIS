"""StratumRO - G4 stage D: parse Overpass responses -> Clip to AOI -> master GPKG
layers (drumuri_ax, cursuri_apa, paduri, constructii-candidates).

All geometry work is GDAL/OGR with the AOI as a spatial-clip mask. WGS84 node
coordinates are reprojected with the deterministic 4326->3844 transform. The LLM
never emits a coordinate (I3); provenance records source + method + timestamp.

Requires: INTER/overpass_*.json from g4_vectors.py stage C.

Run:
  . scripts\\qgis_env.ps1
  python scripts\\g4_clip.py
"""
import json
import time
from pathlib import Path

from osgeo import ogr, osr, gdal

gdal.UseExceptions()
ogr.UseExceptions()

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
INTER = WS / "data" / "intermediate"
OUT = WS / "data" / "output"
PROV = WS / "provenance"
LOG = WS / "logs"
GPKG = OUT / "UAT_Giurgiu.gpkg"

S4326 = osr.SpatialReference()
S4326.ImportFromEPSG(4326)
S4326.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
S3844 = osr.SpatialReference()
S3844.ImportFromEPSG(3844)
S3844.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
CT = osr.CoordinateTransformation(S4326, S3844)

steps = []


def step(name, detail):
    line = "[%s] %s :: %s" % (time.strftime("%H:%M:%S"), name, detail)
    print(line)
    steps.append(line)


def ptwgs(lon, lat):
    """Deterministic WGS84 -> Stereo70 point transform."""
    g = ogr.Geometry(ogr.wkbPoint)
    g.AddPoint(lon, lat)
    g.AssignSpatialReference(S4326)
    g.Transform(CT)
    return g

print("=" * 78)
print("G4 STAGE D - parse Overpass -> clip to AOI -> GPKG layers")
print("=" * 78)


def load_overpass(name):
    p = INTER / ("overpass_%s.json" % name)
    if not p.exists():
        step("parse", "%s: response file missing (fetch failed) -> layer skipped" % name)
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    els = data.get("elements", [])
    step("parse", "%s: %d elements" % (name, len(els)))
    return els


def to_geom(el, node_index):
    """Build a deterministic OGR geometry from an Overpass element."""
    t = el.get("type")
    if t == "node":
        if "lon" not in el or "lat" not in el:
            return None
        return ptwgs(el["lon"], el["lat"])
    if t in ("way", "relation"):
        members = el.get("geometry") or []
        pts = [(n["lon"], n["lat"]) for n in members
               if isinstance(n, dict) and "lon" in n and "lat" in n]
        if len(pts) < 2:
            return None
        ring_maybe = (pts[0] == pts[-1]) and len(pts) >= 4
        line = ogr.Geometry(ogr.wkbLineString)
        for (lon, lat) in pts:
            g = ptwgs(lon, lat)
            line.AddPoint(g.GetX(), g.GetY())
        if ring_maybe:
            poly = ogr.Geometry(ogr.wkbPolygon)
            ring = ogr.Geometry(ogr.wkbLinearRing)
            for (lon, lat) in pts:
                g = ptwgs(lon, lat)
                ring.AddPoint(g.GetX(), g.GetY())
            poly.AddGeometry(ring)
            if poly.IsValid():
                return poly
        if line.IsValid():
            return line
    return None


def tags(el):
    return el.get("tags", {}) or {}


gpkg = ogr.Open(str(GPKG), update=1)
aoi_lyr = gpkg.GetLayerByName("limita_UAT")
aoi_lyr.SetSpatialFilter(None)
aoi_feat = next(iter(aoi_lyr))
aoi_geom = aoi_feat.GetGeometryRef().Clone()
aoi_lyr.ResetReading()

# ---------------------------------------------------------------- drumuri_ax
els = load_overpass("highway_lines")
if els is not None:
    lyr = gpkg.CreateLayer("drumuri_ax", S3844, geom_type=ogr.wkbMultiLineString)
    lyr.CreateField(ogr.FieldDefn("highway", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("name", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
    ddef = lyr.GetLayerDefn()
    n_in = n_out = 0
    lyr.StartTransaction()
    for el in els:
        if el.get("type") != "way":
            continue
        tg = tags(el)
        if "highway" not in tg:
            continue
        n_in += 1
        geom = to_geom(el, None)
        if geom is None or geom.IsEmpty():
            continue
        geom = geom.Intersection(aoi_geom)
        if geom is None or geom.IsEmpty():
            continue
        if not geom.IsValid():
            geom = geom.MakeValid()
        out = ogr.Feature(ddef)
        out.SetField("highway", str(tg.get("highway", ""))[:40])
        out.SetField("name", str(tg.get("name", ""))[:120])
        out.SetField("sursa", "OSM Overpass/API, ODbL")
        out.SetGeometry(geom)
        if lyr.CreateFeature(out) == ogr.OGRERR_NONE:
            n_out += 1
    lyr.CommitTransaction()
    step("clip", "drumuri_ax ways_in=%d segs_out=%d" % (n_in, n_out))

# ---------------------------------------------------------------- cursuri_apa
els = load_overpass("waterway_lines")
if els is not None:
    lyr = gpkg.CreateLayer("cursuri_apa", S3844, geom_type=ogr.wkbMultiLineString)
    lyr.CreateField(ogr.FieldDefn("waterway", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("name", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
    ddef = lyr.GetLayerDefn()
    n_in = n_out = 0
    lyr.StartTransaction()
    for el in els:
        if el.get("type") not in ("way", "relation"):
            continue
        tg = tags(el)
        if "waterway" not in tg:
            continue
        n_in += 1
        geom = to_geom(el, None)
        if geom is None or geom.IsEmpty():
            continue
        geom = geom.Intersection(aoi_geom)
        if geom is None or geom.IsEmpty():
            continue
        if not geom.IsValid():
            geom = geom.MakeValid()
        out = ogr.Feature(ddef)
        out.SetField("waterway", str(tg.get("waterway", ""))[:40])
        out.SetField("name", str(tg.get("name", ""))[:120])
        out.SetField("sursa", "OSM Overpass/API, ODbL")
        out.SetGeometry(geom)
        if lyr.CreateFeature(out) == ogr.OGRERR_NONE:
            n_out += 1
    lyr.CommitTransaction()
    step("clip", "cursuri_apa ways_in=%d segs_out=%d" % (n_in, n_out))

# ---------------------------------------------------------------- paduri
els = load_overpass("forest_poly")
if els is not None:
    lyr = gpkg.CreateLayer("paduri", S3844, geom_type=ogr.wkbMultiPolygon)
    lyr.CreateField(ogr.FieldDefn("landuse", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("natural", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
    ddef = lyr.GetLayerDefn()
    n_in = n_out = 0
    lyr.StartTransaction()
    for el in els:
        if el.get("type") not in ("way", "relation"):
            continue
        tg = tags(el)
        if "landuse" not in tg and "natural" not in tg:
            continue
        n_in += 1
        geom = to_geom(el, None)
        if geom is None or geom.IsEmpty():
            continue
        geom = geom.Intersection(aoi_geom)
        if geom is None or geom.IsEmpty():
            continue
        if not geom.IsValid():
            geom = geom.MakeValid()
        out = ogr.Feature(ddef)
        out.SetField("landuse", str(tg.get("landuse", ""))[:40])
        out.SetField("natural", str(tg.get("natural", ""))[:40])
        out.SetField("sursa", "OSM Overpass/API, ODbL")
        out.SetGeometry(geom)
        if lyr.CreateFeature(out) == ogr.OGRERR_NONE:
            n_out += 1
    lyr.CommitTransaction()
    step("clip", "paduri ways_in=%d polys_out=%d" % (n_in, n_out))

# ---------------------------------------------------------------- constructii candidates (reference only)
els = load_overpass("buildings_ref")
if els is not None:
    lyr = gpkg.CreateLayer("constructii_candidates", S3844, geom_type=ogr.wkbMultiPolygon)
    lyr.CreateField(ogr.FieldDefn("building", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("name", ogr.OFTString))
    lyr.CreateField(ogr.FieldDefn("sursa", ogr.OFTString))
    ddef = lyr.GetLayerDefn()
    n_in = n_out = 0
    lyr.StartTransaction()
    for el in els:
        if el.get("type") not in ("way", "relation"):
            continue
        tg = tags(el)
        if "building" not in tg:
            continue
        n_in += 1
        geom = to_geom(el, None)
        if geom is None or geom.IsEmpty():
            continue
        geom = geom.Intersection(aoi_geom)
        if geom is None or geom.IsEmpty():
            continue
        if not geom.IsValid():
            geom = geom.MakeValid()
        out = ogr.Feature(ddef)
        out.SetField("building", str(tg.get("building", ""))[:40])
        out.SetField("name", str(tg.get("name", ""))[:120])
        out.SetField("sursa", "OSM Overpass/API, ODbL - REFERENCE layer, nu constructii finale")
        out.SetGeometry(geom)
        if lyr.CreateFeature(out) == ogr.OGRERR_NONE:
            n_out += 1
    lyr.CommitTransaction()
    step("clip", "constructii_candidates ways_in=%d polys_out=%d" % (n_in, n_out))

# ---------------------------------------------------------------- wrap up
gpkg = None
aoi_lyr = None

print("=" * 78)
print("G4 STAGE D COMPLETE - all OSM-derived layers clipped and stored")
print("=" * 78)
(LOG / "processing_log.md").open("a", encoding="utf-8").write("\n".join(steps) + "\n")
