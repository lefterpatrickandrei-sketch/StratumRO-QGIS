"""Does any delivered footprint actually sit on vegetation instead of a roof?

Visual inspection of 06_qgis_zoom_cluster_margin.png suggested some footprints in
the lower-right quadrant may cover grass rather than roof. This measures it:
for every CLADIRI_CADASTRU_CLEAN polygon, sample the ortho inside the footprint
and compute the vegetation index NDVI = (G-R)/(G+R).

Roof tiles, asphalt and concrete have near-zero or negative NDVI. Grass and tree
canopies are strongly positive (> 0.15). A footprint whose mean NDVI is above
the vegetation threshold is a candidate false positive.

Run: venv\\Scripts\\python.exe tools\\check_footprints_on_vegetation.py
"""
import os
import sys

import numpy as np
import rasterio
from rasterio.windows import from_bounds, Window

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import geopandas as gpd  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402

GPKG = os.path.join(ROOT, "workspace", "output", "cladiri_stereo70.gpkg")
ORTHO = os.path.join(ROOT, "workspace", "output", "ortofoto_cluj_usamv_rgb.vrt")

VEG_THRESHOLD = 0.15   # NDVI above this = vegetation
FLAT_FRACTION = 0.60  # share of pixels that must look vegetated to flag


def main():
    gdf = gpd.read_file(GPKG, layer="CLADIRI_CADASTRU_CLEAN")
    src = rasterio.open(ORTHO)
    nodata = src.nodata
    H, W = src.height, src.width
    print("ortho: %dx%d px, res=%.3f m, crs=%s, nodata=%s"
          % (W, H, src.res[0], src.crs.to_string(), nodata))
    # The AOI is ~110 ha, so the whole raster fits comfortably in memory.
    # Reading once avoids per-feature VRT window-offset bugs.
    R = src.read(1).astype("int32")
    G = src.read(2).astype("int32")
    T = src.transform

    def px_of(geom):
        from rasterio.transform import rowcol
        xs, ys = geom.exterior.coords.xy
        rr, cc = rowcol(T, xs, ys)
        return min(rr), max(rr), min(cc), max(cc)

    rows = []
    for i, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        r0, r1, c0, c1 = px_of(geom)
        r0 = max(r0, 0); c0 = max(c0, 0); r1 = min(r1, H); c1 = min(c1, W)
        if r1 - r0 < 3 or c1 - c0 < 3:
            rows.append((row.get("id"), 0, 0.0, 0.0, -1.0, -1.0, -1.0))
            continue
        sh, sw = r1 - r0, c1 - c0
        win = Window(c0, r0, sw, sh)
        t = src.window_transform(win)
        sub_r = R[r0:r1, c0:c1]
        sub_g = G[r0:r1, c0:c1]
        try:
            mask = geometry_mask([geom], out_shape=(sh, sw), transform=t, invert=True)
        except Exception:
            continue
        if nodata is not None:
            mask &= (sub_r != nodata) & (sub_g != nodata)
        n = int(mask.sum())
        if n < 20:
            rows.append((row.get("id"), n, 0.0, 0.0, -1.0, -1.0, -1.0))
            continue
        r = sub_r[mask].astype("float64")
        g = sub_g[mask].astype("float64")
        ndvi = (g - r) / np.maximum(g + r, 1.0)
        veg = float((ndvi > VEG_THRESHOLD).mean())
        rows.append((row.get("id"), n, float(ndvi.mean()), float(np.median(ndvi)),
                     veg, float(r.mean()), float(g.mean())))

    rows = [r for r in rows if r[4] >= 0.0]
    rows.sort(key=lambda x: -x[4])
    n_tot = len(rows)
    flagged = [r for r in rows if r[4] >= FLAT_FRACTION]

    print("=== FOOTPRINT VEGETATION CHECK (NDVI inside each delivered polygon) ===")
    print("threshold: NDVI > %.2f counts as vegetation; flag if >= %.0f%% of pixels"
          % (VEG_THRESHOLD, FLAT_FRACTION * 100))
    print("footprints measured: %d" % n_tot)
    print("")
    print("%-6s %-6s %-8s %-8s %-7s %-7s %-7s" %
          ("id", "px", "meanNDVI", "medNDVI", "vegFrac", "meanR", "meanG"))
    for r in rows[:20]:
        print("%-6s %-6d %-8.3f %-8.3f %-7.2f %-7.1f %-7.1f" % r)
    print("")
    print("FLAGGED as mostly-vegetation: %d / %d  (%.1f%%)"
          % (len(flagged), n_tot, 100.0 * len(flagged) / max(n_tot, 1)))
    print("flagged ids: %s" % [r[0] for r in flagged])
    print("")
    mf = np.array([r[4] for r in rows])
    print("vegFrac across all footprints: min=%.3f median=%.3f mean=%.3f max=%.3f"
          % (mf.min(), np.median(mf), mf.mean(), mf.max()))

    src.close()
    out = os.path.join(ROOT, "workspace", "output", "footprint_vegetation_check.csv")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("id,npix,mean_ndvi,median_ndvi,veg_fraction,mean_r,mean_g\n")
        for r in rows:
            fh.write("%s,%d,%.4f,%.4f,%.4f,%.1f,%.1f\n" % r)
    print("\ncsv -> %s" % out)


if __name__ == "__main__":
    main()