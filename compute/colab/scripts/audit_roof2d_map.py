"""Whole-map audit of a 2D roof layer: numeric evidence for the six validation forms, per building.

Every polygon gets the measurements below; flags name the error class so root causes can be counted over
the whole AOI (not over a few hand-picked views) and contact sheets per class feed the visual check (V1).

  V2 under-segmentation   cont_frac: share of a 0.3..1.2 m outer ring that is NOT foliage, NOT another
                          building and sits within 1 m of the roof's LiDAR height  -> roof continues outside
  V3 tree occlusion       occl_frac: share of outline samples with a tall crown 0.6 m outside (crown_on_outline)
  V4 shape                ortho_share (vertices within 5 deg of 45/90), min_edge_m, nodes
  V5 artefact / semantic  nodata_frac (1 m buffer), foliage_frac inside, lidar_cov, elev_frac (nDSM >= 2 m),
                          ndsm_median_m
  V6 topology             overlap_m2 with other polygons, touching neighbours (shared border >= 1.5 m)

Flags: OVERLAP, FP_GROUND (LiDAR says low), FP_VEG (mostly foliage), NODATA_EDGE, OCCLUDED, UNDERSEG,
FRAGMENT (small piece glued to a neighbour), NONORTHO.

    python compute/colab/scripts/audit_roof2d_map.py --layer <gpkg>|<layer> --out <dir> [--sheets]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from build_consensus_labels import foliage  # noqa: E402
from roof2d_data import rasterize  # noqa: E402
from scan_roof2d_aoi import angle_stats, chip_for  # noqa: E402

FLAG_ORDER = ["OVERLAP", "FP_GROUND", "FP_VEG", "NODATA_EDGE", "OCCLUDED", "UNDERSEG", "FRAGMENT", "NONORTHO"]


def _window(geom, transform, shape):
    """Pixel window (r0, c0, r1, c1) and window transform covering geom on a grid."""
    from rasterio.transform import Affine

    minx, miny, maxx, maxy = geom.bounds
    c0, r0 = ~transform * (minx, maxy)
    c1, r1 = ~transform * (maxx, miny)
    c0, r0 = max(int(np.floor(c0)), 0), max(int(np.floor(r0)), 0)
    c1, r1 = min(int(np.ceil(c1)) + 1, shape[1]), min(int(np.ceil(r1)) + 1, shape[0])
    return r0, c0, r1, c1, transform * Affine.translation(c0, r0)


def crown_on_outline(poly, fol, h, wt, step: float = 0.3, out_m: float = 0.6) -> float:
    """Share of outline samples whose point 0.6 m outside is a tall crown (vegetation and nDSM >= 2.5 m).

    A crown touching or covering the eave there means the true corner may be hidden; a crown 3 m away does not
    count (the ring-based measure of R0/R1 flagged every building with a tree nearby).
    """
    from shapely.geometry.polygon import orient

    coords = np.asarray(orient(poly, 1.0).exterior.coords)
    inv = ~wt
    hits = total = 0
    for a, b in zip(coords[:-1], coords[1:]):
        d = b - a
        length = float(np.hypot(*d))
        if length < 1e-6:
            continue
        normal = np.array([d[1], -d[0]]) / length  # outward for a counter-clockwise ring
        for t in np.arange(step / 2, length, step):
            x, y = a + d * (t / length) + normal * out_m
            c, r = inv * (x, y)
            r, c = int(r), int(c)
            if 0 <= r < fol.shape[0] and 0 <= c < fol.shape[1]:
                total += 1
                hits += bool(fol[r, c] and h[r, c] >= 2.5)
    return hits / max(total, 1)


def measure(poly, others, rgb, transform, ndsm_up, nodata):
    """Measurements for one polygon. ndsm_up is the nDSM resampled to the orthophoto grid (NaN = no LiDAR)."""
    from shapely.ops import unary_union

    ring = poly.buffer(1.2).difference(poly.buffer(0.3))
    area = poly.buffer(1.3)
    r0, c0, r1, c1, wt = _window(area, transform, rgb.shape[:2])
    if r1 <= r0 or c1 <= c0:
        return None
    shp = (r1 - r0, c1 - c0)
    inside = rasterize([poly], wt, shp)
    ringm = rasterize([ring], wt, shp)
    other = rasterize(others, wt, shp) if others else np.zeros(shp, bool)
    win_rgb = rgb[r0:r1, c0:c1]
    fol = foliage(win_rgb)
    nd = ndsm_up[r0:r1, c0:c1]
    has = np.isfinite(nd)
    nodata_near = nodata[r0:r1, c0:c1] & rasterize([poly.buffer(1.0)], wt, shp, all_touched=True)

    cov = float(has[inside].mean()) if inside.any() else 0.0
    inner = inside & has
    med = float(np.nanmedian(nd[inner])) if inner.any() else np.nan
    elev = float((nd[inner] >= 2.0).mean()) if inner.any() else np.nan
    ring_free = ringm & ~other
    cont = 0.0
    if ring_free.any() and np.isfinite(med) and med >= 2.0:
        cont = float((~fol & has & (np.abs(np.nan_to_num(nd) - med) <= 1.0))[ring_free].mean())
    occl = crown_on_outline(poly, fol, np.nan_to_num(nd), wt)
    ang = angle_stats([poly])
    coords = np.asarray(poly.exterior.coords)
    edges = np.hypot(*np.diff(coords, axis=0).T)
    return {
        "area_m2": round(poly.area, 2), "nodes": len(coords) - 1, "ortho_share": ang["ortho_45_90_share"],
        "min_edge_m": round(float(edges.min()), 2),
        "nodata_frac": round(float(nodata_near.sum() / max(rasterize([poly.buffer(1.0)], wt, shp).sum(), 1)), 3),
        "foliage_frac": round(float(fol[inside].mean()) if inside.any() else 0.0, 3),
        "lidar_cov": round(cov, 3), "elev_frac": None if np.isnan(elev) else round(elev, 3),
        "ndsm_median_m": None if np.isnan(med) else round(med, 2),
        "occl_frac": round(occl, 3), "cont_frac": round(cont, 3),
    }


def flags_for(m: dict, overlap: float, touching: int) -> list[str]:
    f = []
    if overlap > 0.01:
        f.append("OVERLAP")
    if m["lidar_cov"] >= 0.5 and m["elev_frac"] is not None and m["elev_frac"] < 0.4:
        f.append("FP_GROUND")
    if m["foliage_frac"] >= 0.5:
        f.append("FP_VEG")
    if m["nodata_frac"] >= 0.15:
        f.append("NODATA_EDGE")
    if m["occl_frac"] >= 0.25:
        f.append("OCCLUDED")
    if m["cont_frac"] >= 0.3:
        f.append("UNDERSEG")
    if touching and m["area_m2"] < 25:
        f.append("FRAGMENT")
    if m["ortho_share"] < 0.99:
        f.append("NONORTHO")
    return f


def audit(gdf, data: Path, ndsm_path: Path, id_field: str) -> list[dict]:
    import rasterio
    from rasterio.warp import Resampling, reproject
    from shapely.strtree import STRtree

    with rasterio.open(data / "aoi_rgb.tif") as src:
        rgb, transform = np.moveaxis(src.read(), 0, -1), src.transform
    ndsm_up = np.full(rgb.shape[:2], np.nan, dtype=np.float32)
    with rasterio.open(ndsm_path) as src:
        reproject(src.read(1).astype(np.float32), ndsm_up, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs="EPSG:3844", resampling=Resampling.nearest, dst_nodata=np.nan)
    nodata = rgb.max(axis=2) == 0
    geoms = list(gdf.geometry)
    tree = STRtree(geoms)
    rows = []
    for i, g in enumerate(geoms):
        near = [k for k in tree.query(g.buffer(1.5)) if k != i]
        others = [geoms[k] for k in near]
        overlap = sum(g.intersection(o).area for o in others)
        touching = sum(1 for o in others if g.buffer(0.3).intersection(o.buffer(0.3)).length > 0 and
                       g.buffer(0.3).intersection(o.buffer(0.3)).area > 0.6 * 1.5 * 0.3)
        m = measure(g, others, rgb, transform, ndsm_up, nodata)
        if m is None:
            continue
        m.update({"id": str(gdf[id_field].iloc[i]), "overlap_m2": round(overlap, 3), "touching": touching})
        m["flags"] = flags_for(m, overlap, touching)
        rows.append(m)
    return rows


def contact_sheet(gdf, rows, flag, rgb, transform, path: Path, id_field: str, n: int = 48, cols: int = 8):
    """Chips of up to n polygons carrying `flag`: polygon cyan, neighbours thin white."""
    import cv2

    picks = [r for r in rows if flag in r["flags"]][:n]
    by_id = {str(v): k for k, v in enumerate(gdf[id_field])}
    geoms = list(gdf.geometry)
    cells = []
    for r in picks:
        g = geoms[by_id[r["id"]]]
        chip, px, _, ct = chip_for(g, rgb, transform, margin_m=5.0)
        img = cv2.cvtColor(np.ascontiguousarray(chip), cv2.COLOR_RGB2BGR)
        inv = ~ct
        for o in geoms:
            if o is not g and o.intersects(g.buffer(5.0)):
                pts = np.array([inv * xy for xy in o.exterior.coords])
                cv2.polylines(img, [np.round(pts).astype(np.int32)], True, (255, 255, 255), 1)
        cv2.polylines(img, [np.round(np.asarray(px)).astype(np.int32)], True, (255, 255, 0), 2)
        s = 220 / max(img.shape[:2])
        img = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))))
        cell = np.full((240, 220, 3), 255, np.uint8)
        cell[: img.shape[0], : img.shape[1]] = img
        cv2.putText(cell, r["id"][-14:], (2, 236), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 0, 0), 1)
        cells.append(cell)
    if not cells:
        return 0
    while len(cells) % cols:
        cells.append(np.full_like(cells[0], 255))
    grid = np.vstack([np.hstack(cells[i : i + cols]) for i in range(0, len(cells), cols)])
    cv2.imwrite(str(path), grid, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return len(picks)


STATE_BGR = {"ADMIS": (255, 120, 0), "ADMIS_PROPUS": (0, 230, 255), "INCERT": (255, 0, 255)}


def review_sheets(gdf, rows, rgb, transform, out_dir: Path, id_field: str, per_sheet: int = 40, cols: int = 8):
    """V1 review of every building, north to south: outline coloured by state (blue owner ADMIS, yellow
    ADMIS_PROPUS, magenta INCERT), neighbours thin white, caption = sheet index, id and flags."""
    import cv2

    geoms = list(gdf.geometry)
    by_id = {str(v): k for k, v in enumerate(gdf[id_field])}
    order = sorted(rows, key=lambda r: (-round(geoms[by_id[r["id"]]].centroid.y / 60), geoms[by_id[r["id"]]].centroid.x))
    index = []
    for s in range(0, len(order), per_sheet):
        cells = []
        for n, r in enumerate(order[s : s + per_sheet]):
            k = by_id[r["id"]]
            g = geoms[k]
            chip, px, _, ct = chip_for(g, rgb, transform, margin_m=5.0)
            img = cv2.cvtColor(np.ascontiguousarray(chip), cv2.COLOR_RGB2BGR)
            inv = ~ct
            for o in geoms:
                if o is not g and o.intersects(g.buffer(5.0)):
                    pts = np.array([inv * xy for xy in o.exterior.coords])
                    cv2.polylines(img, [np.round(pts).astype(np.int32)], True, (255, 255, 255), 1)
            state = str(gdf["stare"].iloc[k]) if "stare" in gdf.columns else "INCERT"
            cv2.polylines(img, [np.round(np.asarray(px)).astype(np.int32)], True, STATE_BGR.get(state, (0, 0, 255)), 2)
            sc = 210 / max(img.shape[:2])
            img = cv2.resize(img, (max(1, int(img.shape[1] * sc)), max(1, int(img.shape[0] * sc))))
            cell = np.full((246, 210, 3), 255, np.uint8)
            cell[: img.shape[0], : img.shape[1]] = img
            tag = f"{s // per_sheet}.{n} {r['id'][-13:]}"
            cv2.putText(cell, tag, (2, 224), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 0, 0), 1)
            cv2.putText(cell, ",".join(f[:4] for f in r["flags"])[:34], (2, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 0, 200), 1)
            cells.append(cell)
            index.append({"sheet": s // per_sheet, "cell": n, "id": r["id"], "state": state, "flags": r["flags"]})
        while len(cells) % cols:
            cells.append(np.full_like(cells[0], 255))
        grid = np.vstack([np.hstack(cells[i : i + cols]) for i in range(0, len(cells), cols)])
        cv2.imwrite(str(out_dir / f"review_{s // per_sheet:02d}.jpg"), grid, [cv2.IMWRITE_JPEG_QUALITY, 88])
    (out_dir / "review_index.json").write_text(json.dumps(index, indent=1), encoding="utf-8")
    return len(index)


def main(argv: list[str] | None = None) -> int:
    import geopandas as gpd
    import rasterio

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--layer", required=True, help="path.gpkg|layer")
    ap.add_argument("--id-field", default="proposal_id")
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sheets", action="store_true")
    args = ap.parse_args(argv)
    path, layer = args.layer.split("|")
    gdf = gpd.read_file(path, layer=layer)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = audit(gdf, args.data, args.ndsm, args.id_field)
    summary = {"buildings": len(rows), "flag_counts": {f: sum(f in r["flags"] for r in rows) for f in FLAG_ORDER},
               "clean": sum(1 for r in rows if not r["flags"]),
               "overlap_total_m2": round(sum(r["overlap_m2"] for r in rows) / 2, 2)}
    (args.out / "audit_rows.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    (args.out / "audit_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.sheets:
        with rasterio.open(args.data / "aoi_rgb.tif") as src:
            rgb, transform = np.moveaxis(src.read(), 0, -1), src.transform
        for f in FLAG_ORDER:
            contact_sheet(gdf, rows, f, rgb, transform, args.out / f"sheet_{f}.jpg", args.id_field)
        review_sheets(gdf, rows, rgb, transform, args.out, args.id_field)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
