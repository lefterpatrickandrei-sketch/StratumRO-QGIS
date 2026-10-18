"""StratumRO - UAT Giurgiu G4 stage A: AOI polygon acquisition (limita_UAT).

Sources, in order of authority:
  1. Nominal OSM Nominatim polygon (fetched live in G2, stored in
     provenance/source_discovery_v01.json).
  2. Overpass admin relation (also live in G2).

Both go into data/intermediate as WGS84, then are reprojected to EPSG:3844
(limita_UAT). Nominatim data are ODbL -> attribution + share-alike pending.

Run:
  . scripts\\qgis_env.ps1
  python scripts\\g4_aoi.py
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WS = ROOT / "workspace" / "UAT_Giurgiu"
INTER = WS / "data" / "intermediate"
PROV = WS / "provenance"
for d in (INTER, PROV):
    d.mkdir(parents=True, exist_ok=True)

UA = "StratumRO/2.0 (GIS production run)"
TIMEOUT = 60


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.status, resp.read()


print("=" * 78)
print("G4 STAGE A - AOI acquisition (limita_UAT candidate)")
print("=" * 78)

# --- Nominatim (fresh fetch, not the truncated G2 probe) ---
params = urllib.parse.urlencode({
    "q": "Municipiul Giurgiu, Romania",
    "format": "geojson",
    "polygon_geojson": 1,
    "limit": 5,
})
status, raw = fetch("https://nominatim.openstreetmap.org/search?" + params)
print("nominatim http=%s bytes=%d" % (status, len(raw)))
data = json.loads(raw.decode("utf-8"))
polys = [f for f in data.get("features", [])
         if f["geometry"]["type"] in ("Polygon", "MultiPolygon")]
print("candidates: %d (polygon/MultiPolygon)" % len(polys))
for f in polys:
    p = f.get("properties", {})
    print("  - display=%s category=%s type=%s addresstype=%s" % (
        p.get("display_name"), p.get("category"), p.get("type"), p.get("addresstype")))

chosen = None
for f in polys:  # prefer the city boundary itself
    p = f.get("properties", {})
    if p.get("category") == "boundary" and p.get("type") == "administrative":
        chosen = f
        break
chosen = chosen or polys[0]
props = chosen.get("properties", {})
print("chosen: %s" % props.get("display_name"))

out_wgs = INTER / "aoi_nominatim_wgs84.geojson"
out_wgs.write_text(json.dumps({
    "type": "FeatureCollection",
    "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
    "features": [chosen],
}, ensure_ascii=False), encoding="utf-8")
print("written: %s" % out_wgs)

meta = {
    "run": "G4_aoi",
    "source": "Nominatim (OpenStreetMap data, ODbL 1.0)",
    "endpoint": "https://nominatim.openstreetmap.org/search",
    "query": "Municipiul Giurgiu, Romania",
    "category": props.get("category"),
    "type": props.get("type"),
    "addresstype": props.get("addresstype"),
    "display_name": props.get("display_name"),
    "place_id": props.get("place_id"),
    "osm_type": props.get("osm_type"),
    "osm_id": props.get("osm_id"),
    "license_note": "ODbL - attribution + share-alike required; recorded for provenance.json",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
}
(PROV / "aoi_acquisition_v01.json").write_text(
    json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print("written: provenance/aoi_acquisition_v01.json")
print("=" * 78)
