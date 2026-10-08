# -*- coding: utf-8 -*-
"""
StratumRO - P1: Recompute real heights from nDSM
=================================================
Replaces the fabricated constant heights (inaltime_max_m=7.8, inaltime_med_m=5.2)
in CLADIRI_CADASTRU_CLEAN with heights actually measured from nDSM_stereo70.tif.

Method (deterministic, no LLM in the computation path):
  - for each building polygon, read the nDSM window covering its bounds
  - mask to the polygon interior only (rasterio.features.geometry_mask)
  - drop nodata / non-finite values
  - height_med = median of interior pixels
  - height_max = 90th percentile of interior pixels (roof plateaus are flat,
                so the 90th percentile is far more robust than the absolute max,
                which is corrupted by single-pixel LiDAR noise)

Outputs:
  workspace/output/heights_before_after.csv
  rewrites CLADIRI_CADASTRU_CLEAN + CLADIRI_SOL_ANCPI in cladiri_stereo70.gpkg
"""

import os
import sys
import csv
import numpy as np
import geopandas as gpd
import rasterio
import rasterio.features

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
NDSM = os.path.join(ROOT, "workspace", "output", "ndsm_stereo70.tif")
CSV_OUT = os.path.join(ROOT, "workspace", "output", "heights_before_after.csv")

CLEAN_LAYER = "CLADIRI_CADASTRU_CLEAN"
SOL_LAYER = "CLADIRI_SOL_ANCPI"


def measure(src, geom):
    """Return (median, p90, npix) of nDSM values inside the polygon."""
    try:
        win = src.window(*geom.bounds)
    except Exception:
        return None, None, 0
    h, w = int(win.height), int(win.width)
    if h < 1 or w < 1 or h > 4000 or w > 4000:
        return None, None, 0
    data = src.read(1, window=win)
    mask = rasterio.features.geometry_mask(
        [geom], out_shape=data.shape, transform=src.window_transform(win), invert=True
    )
    vals = data[mask]
    vals = vals[np.isfinite(vals)]
    if src.nodata is not None:
        vals = vals[vals != src.nodata]
    vals = vals[vals > 0.0]  # 0 == ground level, not a roof
    if vals.size == 0:
        return None, None, 0
    return float(np.median(vals)), float(np.percentile(vals, 90)), int(vals.size)


def main():
    print("[*] P1 - Recompute heights from nDSM")
    src = rasterio.open(NDSM)
    print("    nDSM: crs=%s res=%s shape=%s bounds=%s" % (src.crs, src.res, src.shape, [round(b) for b in src.bounds]))

    gdf = gpd.read_file(GPKG, layer=CLEAN_LAYER)
    geoms = list(gdf.geometry)
    print("    CLADIRI_CADASTRU_CLEAN: %d features" % len(gdf))

    rows = []
    meds, p90s, failed = [], [], 0
    for idx, geom in enumerate(geoms):
        med, p90, npix = measure(src, geom)
        if med is None:
            failed += 1
            med, p90 = np.nan, np.nan
        meds.append(med)
        p90s.append(p90)
        rows.append(
            {
                "id": gdf.iloc[idx]["id"],
                "ref_id": gdf.iloc[idx]["ref_id"],
                "old_inaltime_med_m": gdf.iloc[idx]["inaltime_med_m"],
                "old_inaltime_max_m": gdf.iloc[idx]["inaltime_max_m"],
                "new_inaltime_med_m": round(med, 2) if med == med else "",
                "new_inaltime_max_m": round(p90, 2) if p90 == p90 else "",
                "n_pixels": npix,
            }
        )
    src.close()

    meds = np.array(meds, dtype=float)
    p90s = np.array(p90s, dtype=float)

    with open(CSV_OUT, "w", newline="", encoding="utf-8") as fh:
        wtr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wtr.writeheader()
        wtr.writerows(rows)

    print("    measured: %d, failed: %d" % (len(gdf) - failed, failed))
    ok = ~np.isnan(meds)
    print("    height_med : min %.2f  max %.2f  mean %.2f" % (np.nanmin(meds[ok]), np.nanmax(meds[ok]), np.nanmean(meds[ok])))
    print("    height_max : min %.2f  max %.2f  mean %.2f" % (np.nanmin(p90s[ok]), np.nanmax(p90s[ok]), np.nanmean(p90s[ok])))
    print("    stored before: med 5.20 (const), max 7.80 (const)")
    over = int((p90s[ok] > 7.8).sum())
    print("    buildings whose real roof exceeds the old stored 7.8 m: %d / %d" % (over, int(ok.sum())))

    gdf["inaltime_med_m"] = np.round(meds, 2)
    gdf["inaltime_max_m"] = np.round(p90s, 2)
    gdf.to_file(GPKG, layer=CLEAN_LAYER, driver="GPKG")
    print("    rewrote %s" % CLEAN_LAYER)

    print("[*] Recomputing CLADIRI_SOL_ANCPI from measured heights")
    sol = gpd.read_file(GPKG, layer=SOL_LAYER)
    med_by_id = {int(gdf.iloc[i]["id"]): meds[i] for i in range(len(gdf))}
    p90_by_id = {int(gdf.iloc[i]["id"]): p90s[i] for i in range(len(gdf))}
    if "inaltime_med_m" not in sol.columns:
        sol["inaltime_med_m"] = np.nan
    if "inaltime_max_m" not in sol.columns:
        sol["inaltime_max_m"] = np.nan
    written = 0
    for i, bid in enumerate(list(sol["id"])):
        h = med_by_id.get(int(bid), np.nan)
        hp = p90_by_id.get(int(bid), np.nan)
        if h == h:
            sol.iloc[i, sol.columns.get_loc("inaltime_med_m")] = round(float(h), 2)
            sol.iloc[i, sol.columns.get_loc("inaltime_max_m")] = round(float(hp), 2)
            written += 1
    sol.to_file(GPKG, layer=SOL_LAYER, driver="GPKG")
    print("    heights propagated into %s for %d/%d features" % (SOL_LAYER, written, len(sol)))

    print("[*] DONE -> %s" % os.path.relpath(CSV_OUT, ROOT))


if __name__ == "__main__":
    main()