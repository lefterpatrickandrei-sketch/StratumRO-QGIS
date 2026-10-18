# -*- coding: utf-8 -*-
"""G3: public Sentinel-2 discovery, native-grid AOI COG downloads, and GDAL checks.
Run only with python-qgis.bat. All writes are contained in this project.
"""
import sys, os, json, logging, hashlib, time
from pathlib import Path
from datetime import datetime, timezone
import numpy  # Preserve the QGIS NumPy ABI before loading project dependencies.
from osgeo import gdal, ogr, osr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data/cache/g3_python"))
import requests
import pystac_client
import planetary_computer
from dateutil.relativedelta import relativedelta
from pystac_client.stac_api_io import StacApiIO
from urllib3.util.retry import Retry

gdal.UseExceptions()
ogr.UseExceptions()
os.environ["QT_QPA_PLATFORM"] = "offscreen"
API = "https://planetarycomputer.microsoft.com/api/stac/v1"
BANDS = ["B04", "B03", "B02", "B08"]
STATE = ROOT / "state/state.json"
PROV = ROOT / "provenance"
RAW = ROOT / "data/raw/sentinel2"
QA = ROOT / "qa/03_raster_validation.json"

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def stamp():
    return datetime.now(timezone.utc).isoformat()

def safe_error(exc):
    # Requests exceptions can contain temporary SAS credentials.
    return str(exc).split("?")[0][:600]

def aoi_geometry():
    path = ROOT / "data/processed/ancpi/limita_UAT.geojson"
    ds = ogr.Open(str(path))
    if ds is None:
        raise RuntimeError("Missing OSM reference boundary")
    layer = ds.GetLayer(0)
    if layer.GetFeatureCount() != 1:
        raise RuntimeError("Expected exactly one UAT reference geometry")
    feature = layer.GetNextFeature()
    geom = feature.GetGeometryRef().Clone()
    if geom.IsEmpty() or not geom.IsValid():
        raise RuntimeError("UAT reference geometry is empty or invalid")
    src = layer.GetSpatialRef().Clone()
    src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    geom.Transform(osr.CoordinateTransformation(src, dst))
    extent = geom.GetEnvelope()
    return geom, [extent[0], extent[2], extent[1], extent[3]]

def validate_raster(path, aoi):
    ds = gdal.Open(str(path))
    if ds is None or ds.RasterCount != 1:
        raise RuntimeError("Not a single-band readable raster: " + path.name)
    gt = ds.GetGeoTransform()
    srs = ds.GetSpatialRef()
    if not srs or not srs.IsProjected():
        raise RuntimeError("Raster CRS missing or not projected")
    if abs(gt[1] - 10) > 1e-6 or abs(gt[5] + 10) > 1e-6 or gt[2] or gt[4]:
        raise RuntimeError("Unexpected band resolution or rotated grid")
    if ds.GetMetadataItem("LAYOUT", "IMAGE_STRUCTURE") != "COG":
        raise RuntimeError("GDAL did not identify COG layout")
    target = srs.Clone()
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    source = osr.SpatialReference()
    source.ImportFromEPSG(4326)
    source.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    local_aoi = aoi.Clone()
    local_aoi.Transform(osr.CoordinateTransformation(source, target))
    x0, x1, y0, y1 = local_aoi.GetEnvelope()
    if not (gt[0] <= x0 and x1 <= gt[0] + ds.RasterXSize * gt[1]
            and gt[3] + ds.RasterYSize * gt[5] <= y0 and y1 <= gt[3]):
        raise RuntimeError("Band does not cover the reference UAT")
    band = ds.GetRasterBand(1)
    # Full checksum forces GDAL to decode the complete raster.
    checksum = band.Checksum()
    # A true AOI cutline checks that the UAT is not entirely nodata.
    subset = gdal.Warp("", ds, format="MEM", dstSRS="EPSG:3844",
                       cutlineDSName=str(ROOT / "data/processed/ancpi/limita_UAT.geojson"),
                       cropToCutline=True, xRes=10, yRes=10,
                       resampleAlg="near", dstNodata=0)
    stats = subset.GetRasterBand(1).GetStatistics(False, True)
    if stats is None or stats[1] <= 0:
        raise RuntimeError("No valid imagery in UAT")
    valid_pct = subset.GetRasterBand(1).GetMetadataItem("STATISTICS_VALID_PERCENT")
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
    result = {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size,
              "sha256": sha.hexdigest(), "crs": srs.GetAuthorityName(None) + ":" + srs.GetAuthorityCode(None),
              "size": [ds.RasterXSize, ds.RasterYSize], "geotransform": list(gt),
              "resolution_m": [gt[1], abs(gt[5])], "nodata": band.GetNoDataValue(),
              "dtype": gdal.GetDataTypeName(band.DataType), "layout": "COG",
              "overviews": band.GetOverviewCount(), "full_decode_checksum": checksum,
              "aoi_bbox_valid_pixel_percent": valid_pct,
              "aoi_stats": stats, "covers_reference_uat": True,
              "evidence_class": "MEASURED"}
    ds = subset = None
    return result

def download(asset, path, aoi):
    import math
    metadata_path = path.with_suffix(".source.json")
    if path.exists() and metadata_path.exists():
        logging.info("Existing AOI COG; will verify: %s", path.name)
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    # HTTP range reads retrieve just the COG blocks intersecting the native-grid window.
    for key, value in {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_MAX_RETRY": "3",
        "GDAL_HTTP_RETRY_DELAY": "2", "GDAL_HTTP_TIMEOUT": "90",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif", "GDAL_PAM_ENABLED": "NO",
        "GDAL_NUM_THREADS": "2"
    }.items():
        gdal.SetConfigOption(key, value)
    source = gdal.Open("/vsicurl/" + planetary_computer.sign(asset.href))
    source_srs = osr.SpatialReference()
    source_srs.ImportFromEPSG(4326)
    source_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    target = source.GetSpatialRef().Clone()
    target.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    native_aoi = aoi.Clone()
    native_aoi.Transform(osr.CoordinateTransformation(source_srs, target))
    x0, x1, y0, y1 = native_aoi.GetEnvelope()
    inverse = gdal.InvGeoTransform(source.GetGeoTransform())
    col0, row0 = gdal.ApplyGeoTransform(inverse, x0, y1)
    col1, row1 = gdal.ApplyGeoTransform(inverse, x1, y0)
    left, top = math.floor(col0) - 1, math.floor(row0) - 1
    right, bottom = math.ceil(col1) + 1, math.ceil(row1) + 1
    if left < 0 or top < 0 or right > source.RasterXSize or bottom > source.RasterYSize:
        raise RuntimeError("AOI exceeds source raster")
    window = [left, top, right - left, bottom - top]
    partial = path.with_suffix(".tif.part")
    logging.info("Reading native pixel window %s for %s", window, path.name)
    output = gdal.Translate(str(partial), source, format="COG", srcWin=window,
                            creationOptions=["COMPRESS=DEFLATE", "BLOCKSIZE=512", "RESAMPLING=NEAREST"])
    if output is None:
        raise RuntimeError("COG extraction failed")
    output = None
    # Exact pixel equality is verified on every pixel of the extracted window.
    expected = source.GetRasterBand(1).ReadRaster(*window)
    check = gdal.Open(str(partial))
    observed = check.GetRasterBand(1).ReadRaster()
    if observed != expected:
        raise RuntimeError("Extracted COG does not preserve source pixels")
    check = source = None
    os.replace(partial, path)
    metadata = {"source_href": asset.href, "source_pixel_window": window,
                "download_mode": "AOI native-grid subset, not full satellite tile",
                "resampling_base_resolution": "NONE", "source_pixels_exact_match": True}
    write_json(metadata_path, metadata)
    logging.info("Extracted %s (%d bytes); exact source pixel equality PASS", path.name, path.stat().st_size)
    return metadata

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    PROV.mkdir(parents=True, exist_ok=True)
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(ROOT / "logs/03_raster_validation.log", encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)])
    state = json.loads(STATE.read_text(encoding="utf-8-sig"))
    if state.get("gate") not in ("G2_complete", "G3_complete"):
        raise RuntimeError("Unexpected gate; refusing to overwrite later work")
    backup = ROOT / "state/state.before_G3.json"
    if not backup.exists():
        write_json(backup, state)
    report = {"started_at": stamp(), "status": "RUNNING", "evidence_class": "MEASURED",
              "esri_world_imagery": {"status": "NOT_USED", "LICENSE_CHECK": "NOT_APPLICABLE"},
              "sam2_status": "DISABLED_FALLBACK",
              "suitability": "10 m imagery is context only; not suitable for cadastral building outlines or 0.50 m accuracy.",
              "files": []}
    try:
        aoi, bbox = aoi_geometry()
        now = datetime.now(timezone.utc)
        start = now - relativedelta(months=6)
        interval = start.strftime("%Y-%m-%dT00:00:00Z") + "/" + now.strftime("%Y-%m-%dT%H:%M:%SZ")
        report.update({"search_interval": interval, "aoi_bbox_wgs84": bbox,
                       "aoi_source": "data/processed/ancpi/limita_UAT.geojson",
                       "aoi_authority": "OSM REFERENCE, not official ANCPI",
                       "selection": "Lowest scene eo:cloud_cover among full-UAT-covering items with all four bands; newest acquisition breaks ties. AOI cloud percentage is not measured."})
        logging.info("Search interval=%s bbox=%s", interval, bbox)
        api = pystac_client.Client.open(API, stac_io=StacApiIO(timeout=60, max_retries=Retry(total=3, backoff_factor=1)))
        collection = api.get_collection("sentinel-2-l2a")
        write_json(PROV / "03_sentinel2_collection.json", collection.to_dict())
        report["license"] = {"status": "KNOWN_TERMS", "name": "Copernicus Sentinel Data Legal Notice",
            "stac_license_literal": collection.license,
            "terms_url": "https://dataspace.copernicus.eu/terms-and-conditions",
            "legal_notice_url": "https://cds.climate.copernicus.eu/licences/ec-sentinel",
            "note": "STAC proprietary is retained verbatim; Sentinel-specific open terms apply, not an assumed CC license."}
        items = list(api.search(collections=["sentinel-2-l2a"], intersects=json.loads(aoi.ExportToJson()),
                                datetime=interval, limit=100, method="POST").items())
        eligible = []
        candidates = []
        for item in items:
            geom = ogr.CreateGeometryFromJson(json.dumps(item.geometry))
            covers = bool(geom and geom.Contains(aoi))
            cloud = item.properties.get("eo:cloud_cover")
            available = all(key in item.assets for key in BANDS)
            ok = covers and available and isinstance(cloud, (float, int)) and 0 <= cloud <= 100
            candidates.append({"id": item.id, "datetime": item.properties.get("datetime"),
                               "scene_cloud_percent": cloud, "covers_uat": covers, "bands_available": available})
            if ok:
                eligible.append(item)
        write_json(PROV / "03_sentinel2_candidates.json", {"query": report, "candidates": candidates})
        report.update({"candidate_count": len(items), "eligible_count": len(eligible)})
        if not eligible:
            raise RuntimeError("DATA GAP: no full-UAT scene with requested bands in the six-month interval")
        eligible.sort(key=lambda i: (i.properties["eo:cloud_cover"], -i.datetime.timestamp(), i.id))
        item = eligible[0]
        report.update({"item_id": item.id, "acquired_at": item.datetime.isoformat(),
                       "scene_cloud_percent": item.properties["eo:cloud_cover"],
                       "attribution": "Contains modified Copernicus Sentinel data [" + str(item.datetime.year) + "]"})
        write_json(PROV / "03_sentinel2_selected_item.json", item.to_dict())
        logging.info("Selected %s, cloud=%s%%, eligible=%d/%d", item.id, report["scene_cloud_percent"], len(eligible), len(items))
        for key in BANDS:
            path = RAW / (item.id + "_AOI_" + key + ".tif")
            logging.info("Processing band %s", key)
            extraction = download(item.assets[key], path, aoi)
            result = validate_raster(path, aoi)
            result.update({"band": key, **extraction})
            report["files"].append(result)
            write_json(QA, report)
            logging.info("Validated %s: COG, %s, 10m, full decode OK", key, result["crs"])
        grids = {(tuple(f["size"]), tuple(f["geotransform"]), f["crs"]) for f in report["files"]}
        if len(grids) != 1:
            raise RuntimeError("Band grids are inconsistent")
        report.update({"status": "COMPLETE", "completed_at": stamp(), "exit_code": 0,
                       "raw_crs_policy": "Native-grid AOI subsets preserve source CRS and pixels; in-memory QA crop transformed with GDAL to EPSG:3844. No master GPKG edits."})
        write_json(QA, report)
        state["gate"] = "G3_complete"
        state["gate_since"] = state["updated_at"] = report["completed_at"]
        state.setdefault("data_sources", {})["sentinel2"] = "OK"
        state["data_gaps"] = [g for g in state.get("data_gaps", []) if g.get("layer") != "sentinel2_bands"]
        state["raster_validation"] = {k: report[k] for k in [
            "status", "item_id", "acquired_at", "scene_cloud_percent", "candidate_count",
            "eligible_count", "search_interval", "aoi_bbox_wgs84", "license",
            "esri_world_imagery", "sam2_status", "suitability"]}
        state["updated"] = state["updated_at"]
        state["raster_validation"]["download_mode"] = "AOI native-grid COG subsets; not full satellite tiles"
        state["raster_validation"]["raw_crs"] = "EPSG:32635"
        state["raster_validation"]["qa_report"] = "qa/03_raster_validation.json"
        state["raster_validation"]["files"] = [f["path"] for f in report["files"]]
        write_json(STATE, state)
        logging.info("G3_complete; state saved")
    except Exception as exc:
        report.update({"status": "FAILED", "error": safe_error(exc), "completed_at": stamp(), "exit_code": 1})
        write_json(QA, report)
        state["updated_at"] = report["completed_at"]
        state["raster_validation"] = {"status": "FAILED", "error": report["error"], "qa_report": "qa/03_raster_validation.json"}
        state.setdefault("data_sources", {})["sentinel2"] = "DATA_GAP"
        gaps = state.setdefault("data_gaps", [])
        gaps[:] = [g for g in gaps if g.get("layer") != "sentinel2_bands"]
        gaps.append({"layer": "sentinel2_bands", "reason": report["error"]})
        write_json(STATE, state)
        logging.error("%s; gate remains %s", report["error"], state["gate"])
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())


