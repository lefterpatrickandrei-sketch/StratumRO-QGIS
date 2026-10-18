"""StratumRO - G2 live source discovery + capability probe for UAT Giurgiu.

Attempts each source from the mission spec section 6.1 LIVE, in order, and records
reachability / auth / payload. Writes a machine-readable result file.

Run with the QGIS Python runtime:
    . scripts\\qgis_env.ps1
    python scripts\\discover_sources.py
"""
import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "workspace" / "UAT_Giurgiu" / "provenance"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "source_discovery_v01.json"

TIMEOUT = 15
UA = "StratumRO/2.0 (GIS production run)"

# UAT Giurgiu (Municipiul Giurgiu, judetul Giurgiu, SIRUTA 100521)
AOI_BBOX_WGS84 = (25.9050, 43.8600, 26.0200, 43.9300)  # lon_min, lat_min, lon_max, lat_max

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE


def probe(name, url, method="GET", body=None, accept=None, note="", data_budget=200000):
    """Single live probe. Records reachability, auth requirement, payload size, error."""
    rec = {
        "source": name,
        "endpoint_tested": url,
        "method": method,
        "reachable": "N",
        "auth_required": "N",
        "http_status": None,
        "content_type": None,
        "bytes_received": 0,
        "error": None,
        "note": note,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    headers = {"User-Agent": UA}
    if accept:
        headers["Accept"] = accept
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
            rec["http_status"] = resp.status
            rec["content_type"] = resp.headers.get("Content-Type")
            chunk = resp.read(data_budget)
            rec["bytes_received"] = len(chunk)
            rec["reachable"] = "Y"
            if resp.status in (401, 403):
                rec["auth_required"] = "Y"
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["reachable"] = "Y" if e.code < 500 else "N"
        if e.code in (401, 403):
            rec["auth_required"] = "Y"
        rec["error"] = "HTTPError %s" % e.code
        try:
            rec["bytes_received"] = len(e.read(2000))
        except Exception:
            pass
    except Exception as e:
        rec["error"] = "%s: %s" % (type(e).__name__, e)
    return rec


results = []

# ---------------------------------------------------------------- 1. ANCPI
results.append(probe(
    "ANCPI_GEOPORTAL_WMS_CAPABILITIES",
    "https://geoportal.ancpi.ro/geoserver/wms?service=WMS&request=GetCapabilities&version=1.3.0",
    note="ANCPI GeoServer WMS GetCapabilities",
))
results.append(probe(
    "ANCPI_GEOPORTAL_ROOT",
    "https://geoportal.ancpi.ro/",
    note="ANCPI geoportal landing page (reachability / redirect shape)",
))

# ---------------------------------------------------------------- 2. INSPIRE
results.append(probe(
    "INSPIRE_GEOPORTAL_RO",
    "https://geoportal.gov.ro/",
    note="National INSPIRE geoportal",
))
results.append(probe(
    "INSPIRE_GEOPORTAL_RO_OGC",
    "https://geoportal.gov.ro/geoserver/wms?service=WMS&request=GetCapabilities&version=1.3.0",
    note="Romanian INSPIRE geoportal OGC service probe",
))

# ---------------------------------------------------------------- 3. Primaria Giurgiu
results.append(probe(
    "PRIMARIA_GIURGIU_PUG",
    "https://www.primariagiurgiu.ro/",
    note="Municipal PUG / urbanism documents (intravilan source)",
))

# ---------------------------------------------------------------- 4. OSM
overpass_q = '[out:json][timeout:60];rel["admin_level"="8"]["name"~"Giurgiu",i];out tags center;'
body = urllib.parse.urlencode({"data": overpass_q}).encode("utf-8")
results.append(probe(
    "OSM_OVERPASS_ADMIN",
    "https://overpass-api.de/api/interpreter",
    method="POST", body=body,
    note="OSM relation admin_level=8 name~Giurgiu (AOI candidate geometry source)",
))
results.append(probe(
    "OSM_GEOFABRIK_RO_PBF_HEAD",
    "https://download.geofabrik.de/europe/romania-latest.osm.pbf",
    method="HEAD",
    note="Geofabrik Romania PBF extract (roads/hydro/forest/buildings candidates)",
))
results.append(probe(
    "OSM_NOMINATIM_AOI",
    "https://nominatim.openstreetmap.org/search?"
    + urllib.parse.urlencode({"q": "Municipiul Giurgiu, Romania", "format": "json",
                              "polygon_geojson": 1, "limit": 1}),
    note="Nominatim AOI polygon lookup",
))

# ---------------------------------------------------------------- 5. Eurostat GISCO
results.append(probe(
    "EUROSTAT_GISCO_LAU_HEAD",
    "https://gisco-services.ec.europa.eu/distribution/v2/lau/download/LAU_RG_01M_2021_4326.geojson",
    method="HEAD",
    note="Eurostat GISCO LAU (limita_UAT fallback)",
))

# ---------------------------------------------------------------- 6. Esri World Imagery
results.append(probe(
    "ESRI_WORLD_IMAGERY_TILE",
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/17/44955/74914",
    note="Esri World Imagery XYZ tile probe (license check required before derivatives)",
))
results.append(probe(
    "ESRI_WORLD_IMAGERY_METADATA",
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer?f=json",
    note="Esri World Imagery service metadata (copyright text / license)",
))

# ---------------------------------------------------------------- 7. Copernicus / MPC
results.append(probe(
    "MPC_STAC_ROOT",
    "https://planetarycomputer.microsoft.com/api/stac/v1/",
    note="Microsoft Planetary Computer STAC (no key, no account)",
))
results.append(probe(
    "MPC_STAC_SENTINEL2_COLLECTION",
    "https://planetarycomputer.microsoft.com/api/stac/v1/collections/sentinel-2-l2a",
    note="Planetary Computer Sentinel-2 L2A collection",
))


# ------------------------------------------------- MPC STAC search over the AOI
mpc_search = json.dumps({
    "collections": ["sentinel-2-l2a"],
    "bbox": list(AOI_BBOX_WGS84),
    "limit": 3,
    "query": {"eo:cloud_cover": {"lt": 20}},
}).encode("utf-8")
mpc_rec = {
    "source": "MPC_STAC_SEARCH_S2",
    "endpoint_tested": "https://planetarycomputer.microsoft.com/api/stac/v1/search",
    "method": "POST",
    "reachable": "N",
    "auth_required": "N",
    "http_status": None,
    "content_type": None,
    "bytes_received": 0,
    "error": None,
    "note": "Sentinel-2 STAC search over the AOI bbox (<20 pct cloud)",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
}
try:
    req = urllib.request.Request(
        "https://planetarycomputer.microsoft.com/api/stac/v1/search",
        data=mpc_search,
        headers={"Content-Type": "application/json", "User-Agent": UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as resp:
        raw = resp.read(400000)
        mpc_rec["http_status"] = resp.status
        mpc_rec["content_type"] = resp.headers.get("Content-Type")
        mpc_rec["bytes_received"] = len(raw)
        mpc_rec["reachable"] = "Y"
        try:
            parsed = json.loads(raw.decode("utf-8"))
            items = parsed.get("features", [])
            mpc_rec["items_found"] = len(items)
            if items:
                mpc_rec["first_item_id"] = items[0].get("id")
                mpc_rec["first_item_datetime"] = items[0]["properties"].get("datetime")
                assets = items[0].get("assets", {})
                visual = assets.get("visual") or assets.get("rendered_preview")
                if visual:
                    mpc_rec["visual_cog_href"] = visual.get("href")
        except Exception as e:
            mpc_rec["error"] = "parse: %s" % e
except urllib.error.HTTPError as e:
    mpc_rec["http_status"] = e.code
    mpc_rec["auth_required"] = "Y" if e.code in (401, 403) else "N"
    mpc_rec["error"] = "HTTPError %s" % e.code
except Exception as e:
    mpc_rec["error"] = "%s: %s" % (type(e).__name__, e)
results.append(mpc_rec)

# ---------------------------------------------------------------- local disk sweep
local_hits = []
for pat in ("*.tif", "*.tiff", "*.jp2", "*.gpkg", "*.geojson", "*.shp", "*.las", "*.laz", "*.osm.pbf"):
    for p in ROOT.rglob(pat):
        try:
            local_hits.append(str(p.relative_to(ROOT)))
        except ValueError:
            local_hits.append(str(p))
results.append({
    "source": "LOCAL_DISK_INDEX",
    "endpoint_tested": str(ROOT),
    "method": "rglob",
    "reachable": "Y",
    "auth_required": "N",
    "note": "local raster/vector index (mirrors the Everything/rg sweep required by the spec)",
    "files_found": len(local_hits),
    "sample": local_hits[:80],
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
})

# ---------------------------------------------------------------- report
summary = {
    "run": "G2_live_source_discovery",
    "aoi_bbox_wgs84": list(AOI_BBOX_WGS84),
    "aoi_name": "Municipiul Giurgiu, judetul Giurgiu, Romania",
    "python": sys.version,
    "results": results,
}
OUT_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print("=" * 78)
print("G2 LIVE SOURCE DISCOVERY -> %s" % OUT_FILE)
print("=" * 78)
for r in results:
    extra = ""
    if r.get("source") == "MPC_STAC_SEARCH_S2":
        extra = " items=%s" % r.get("items_found")
    if r.get("source") == "LOCAL_DISK_INDEX":
        extra = " files=%s" % r.get("files_found")
    err = r.get("error") or ""
    print("%-4s %-42s http=%-6s auth=%s%s %s" % (
        r.get("reachable"), r["source"][:42], r.get("http_status"),
        r.get("auth_required"), extra, ("ERR=" + str(err)[:56]) if err else ""))
print("=" * 78)

