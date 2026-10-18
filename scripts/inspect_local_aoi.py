"""StratumRO - inspect the local AOI candidate datasets before any external fetch.

Read-only. Reports CRS, extent, feature count and identity evidence so that the
mission never assumes a local file belongs to the AOI just because it exists.

Run with the QGIS Python runtime:
    . scripts\\qgis_env.ps1
    python scripts\\inspect_local_aoi.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [
    ROOT / "data" / "ground_truth" / "osm_buildings_aoi.geojson",
    ROOT / "data" / "ground_truth" / "tier1_teren.geojson",
    ROOT / "data" / "ground_truth" / "tier2_extended_gt.geojson",
    ROOT / "datasets",
    ROOT / "data",
]

try:
    from osgeo import ogr, osr  # noqa: F401
    HAVE_GDAL = True
except Exception:
    HAVE_GDAL = False


def describe_vector(path):
    ds = ogr.Open(str(path))
    if ds is None:
        return {"file": str(path), "readable": False}
    layer = ds.GetLayer(0)
    srs = layer.GetSpatialRef()
    auth = None
    if srs is not None:
        auth = srs.GetAuthorityName(None), srs.GetAuthorityCode(None)
    extent = layer.GetExtent()
    rec = {
        "file": str(path.relative_to(ROOT)),
        "readable": True,
        "driver": ds.GetDriver().GetName() if ds.GetDriver() else None,
        "layer": layer.GetName(),
        "geometry_type": ogr.GeometryTypeToName(layer.GetGeomType()),
        "feature_count": layer.GetFeatureCount(),
        "crs_authority": auth,
        "extent": extent,
    }
    ds = None
    return rec


out = []
print("=" * 78)
print("LOCAL AOI CANDIDATE INSPECTION")
print("=" * 78)
for cand in CANDIDATES:
    if not cand.exists():
        continue
    if cand.is_dir():
        files = sorted(p for p in cand.rglob("*") if p.is_file())
        print("[dir ] %-52s files=%d" % (str(cand.relative_to(ROOT)), len(files)))
        for f in files[:25]:
            print("         " + str(f.relative_to(ROOT)))
        out.append({"dir": str(cand.relative_to(ROOT)), "file_count": len(files),
                    "sample": [str(f.relative_to(ROOT)) for f in files[:25]]})
        continue
    if cand.suffix.lower() in (".geojson", ".json"):
        rec = describe_vector(cand)
    elif HAVE_GDAL:
        rec = describe_vector(cand)
    else:
        rec = {"file": str(cand.relative_to(ROOT)), "readable": False, "reason": "no GDAL"}
    out.append(rec)
    print(json.dumps(rec, indent=2, default=str))

# explicit AOI identity check against the known Giurgiu Stereo-70 footprint
main = ROOT / "data" / "ground_truth" / "osm_buildings_aoi.geojson"
if main.exists() and HAVE_GDAL:
    rec = describe_vector(main)
    ext = rec.get("extent")
    if ext:
        cx = (ext[0] + ext[1]) / 2.0
        cy = (ext[2] + ext[3]) / 2.0
        print("-" * 78)
        print("AOI CANDIDATE CENTROID (Stereo 70): X=%.1f Y=%.1f" % (cx, cy))
        print("Giurgiu city centre in Stereo 70 is approximately X=391000 Y=586000.")
        in_range = 350000 < cx < 430000 and 550000 < cy < 620000
        print("IDENTITY CHECK: %s" % ("CONSISTENT with Giurgiu" if in_range
                                      else "NOT consistent with Giurgiu - DO NOT ASSUME"))
        print("-" * 78)

dest = ROOT / "workspace" / "UAT_Giurgiu" / "provenance" / "local_aoi_inspection_v01.json"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
print("written: %s" % dest)
