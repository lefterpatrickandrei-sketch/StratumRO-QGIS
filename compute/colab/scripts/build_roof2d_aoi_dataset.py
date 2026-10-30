"""Build the georeferenced Phase 1 2D roof dataset (AOI mosaic + partial labels) in EPSG:3844.

Replaces the per-chip catalog masks of build_2d_roof_dataset.py for training: those label every
unreviewed neighbour roof inside a chip as background and map chip pixels to metres with the building
bbox instead of the chip extent. Here everything shares the orthophoto grid (0.15 m), see roof2d_data.py
for the label policy.

    python compute/colab/scripts/build_roof2d_aoi_dataset.py            # defaults below
Outputs (out-dir): aoi_rgb.tif, label_{roof,edge,corner,contact}.tif, split.tif, manifest.json
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof2d_data import IGNORE, SPLIT_TRAIN, SPLIT_VAL, build_label_rasters, rasterize, sha256_file, split_raster  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
GPKG_LAYERS = {
    "positive": "1_ADMIS_FORME_BUNE_2D",
    "repaired": "2_AJUSTARI_REPARATE_V1_V6",
    "target": "3_AJUSTARI_TINTA_LOOP_A100",
    "negative": "4_MUTILATE_SI_ELIMINATE_AUDIT",
}


def catalog_polygons(html_path: Path) -> list:
    """All 242 Opera GX catalog candidates (EPSG:3844 s70_points) as shapely polygons."""
    from shapely.geometry import Polygon

    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"const BUILDINGS = (\[.*?\]);\s*\n", text, re.S)
    if not m:
        raise RuntimeError(f"BUILDINGS array not found in {html_path}")
    out = []
    for b in json.loads(m.group(1)):
        pts = [(p["x"], p["y"]) for p in b.get("s70_points", [])]
        if len(pts) >= 3:
            poly = Polygon(pts).buffer(0)
            if not poly.is_empty:
                out.append(poly)
    return out


def ground_mask(ndsm_path: Path, transform, shape, threshold_m: float = 1.0, erode_m: float = 2.0) -> np.ndarray:
    """nDSM < threshold, resampled to the orthophoto grid and eroded (relief displacement, eave overhang)."""
    import rasterio
    from rasterio.warp import Resampling, reproject
    from scipy import ndimage

    ndsm = np.full(shape, np.nan, dtype=np.float32)
    with rasterio.open(ndsm_path) as src:
        reproject(
            src.read(1).astype(np.float32), ndsm, src_transform=src.transform, src_crs=src.crs,
            dst_transform=transform, dst_crs="EPSG:3844", resampling=Resampling.bilinear, dst_nodata=np.nan,
        )
    ground = np.isfinite(ndsm) & (ndsm < threshold_m)
    radius = int(round(erode_m / abs(transform.a)))
    yy, xx = np.ogrid[-radius : radius + 1, -radius : radius + 1]
    return ndimage.binary_erosion(ground, structure=(xx * xx + yy * yy) <= radius * radius)


def build(tiles: list[Path], gpkg: Path, html: Path, ndsm: Path | None, out_dir: Path, val_min_y: float,
          consensus: Path | None = None) -> dict:
    import geopandas as gpd
    import rasterio
    from rasterio.merge import merge

    out_dir.mkdir(parents=True, exist_ok=True)
    srcs = [rasterio.open(p) for p in tiles]
    mosaic, transform = merge(srcs, nodata=0)
    crs = srcs[0].crs
    for s in srcs:
        s.close()
    if str(crs) != "EPSG:3844":
        raise ValueError(f"orthophoto CRS must be EPSG:3844, got {crs}")
    rgb = np.moveaxis(mosaic[:3], 0, -1).astype(np.uint8)
    shape = rgb.shape[:2]

    layers = {k: list(gpd.read_file(gpkg, layer=v).to_crs("EPSG:3844").geometry) for k, v in GPKG_LAYERS.items()}
    layers = {k: [g if g.geom_type == "Polygon" else max(g.geoms, key=lambda p: p.area) for g in v] for k, v in layers.items()}
    positives = layers["positive"]
    known = positives + layers["repaired"] + layers["target"] + layers["negative"]
    others = [c for c in catalog_polygons(html) if not any(c.intersection(k).area > 0.5 * c.area for k in known)]
    ignore = layers["repaired"] + layers["target"] + others
    ground = ground_mask(ndsm, transform, shape) if ndsm else None

    roof, edge, corner, contact = build_label_rasters(rgb, transform, positives, layers["negative"], ignore, ground)
    extra = {"consensus_positive": 0, "tree_negative": 0}
    if consensus is not None:  # agent-built labels (build_consensus_labels.py): only fill pixels still 255
        cpos = list(gpd.read_file(consensus, layer="consensus_positive").geometry)
        tneg = list(gpd.read_file(consensus, layer="tree_negative").geometry)
        free = roof == IGNORE
        if tneg:
            roof[free & rasterize(tneg, transform, shape)] = 0
        if cpos:
            roof[(roof == IGNORE) & rasterize(cpos, transform, shape)] = 1
        extra = {"consensus_positive": len(cpos), "tree_negative": len(tneg)}
    split = split_raster(transform, shape, val_min_y)
    roof_train = roof.copy()
    roof_train[split != SPLIT_TRAIN] = IGNORE  # what training is allowed to see

    profile = dict(driver="GTiff", height=shape[0], width=shape[1], crs="EPSG:3844", transform=transform,
                   compress="deflate", tiled=True, blockxsize=512, blockysize=512)
    files = {
        "aoi_rgb.tif": np.moveaxis(rgb, -1, 0),
        "label_roof.tif": roof[None],
        "label_edge.tif": edge[None],
        "label_corner.tif": corner[None],
        "label_contact.tif": contact[None],
        "split.tif": split[None],
    }
    for name, arr in files.items():
        with rasterio.open(out_dir / name, "w", count=arr.shape[0], dtype="uint8", **profile) as dst:
            dst.write(arr)

    def centroid_split(polys):
        return {
            "train": sum(1 for p in polys if p.centroid.y <= val_min_y - 15),
            "val": sum(1 for p in polys if p.centroid.y >= val_min_y + 15),
        }

    px = float(abs(transform.a))
    manifest = {
        "schema_version": "3.0.0-phase1-2d-rgb-aoi",
        "crs": "EPSG:3844",
        "gsd_m": round(px, 4),
        "input_channels": ["R", "G", "B"],
        "uses_lidar_heights_as_input": False,
        "lidar_ndsm_used_for_labels": bool(ndsm),
        "label_policy": "1=owner ADMIS; 0=owner hard negatives + 0.3..1.2m ring outside ADMIS + nDSM<1m ground "
                        "(eroded 2m, >1m from any candidate); 255=everything else incl. AJUSTARE, heuristic repairs, "
                        "other catalog candidates, NoData, split buffer",
        "split": {"rule": "north/south on Stereo70 Y", "val_min_y": val_min_y, "buffer_m": 30.0},
        "shape_hw": list(shape),
        "transform": list(transform)[:6],
        "sources": {
            "tiles": [str(p.relative_to(REPO_ROOT)).replace("\\", "/") for p in tiles],
            "gpkg": str(gpkg.relative_to(REPO_ROOT)).replace("\\", "/"),
            "gpkg_sha256": sha256_file(gpkg),
            "catalog_html": str(html.relative_to(REPO_ROOT)).replace("\\", "/"),
            "ndsm": str(ndsm.relative_to(REPO_ROOT)).replace("\\", "/") if ndsm else None,
            "consensus": str(consensus) if consensus else None,
        },
        "counts": {
            "positives_admis": len(positives),
            "positives_by_split": centroid_split(positives),
            "targets_ajustare": len(layers["target"]),
            "targets_by_split": centroid_split(layers["target"]),
            "repaired_ignored": len(layers["repaired"]),
            "hard_negatives": len(layers["negative"]),
            "other_catalog_ignored": len(others),
            "agent_consensus_labels": extra,
        },
        "pixel_fractions": {
            "roof_1": round(float(np.mean(roof == 1)), 4),
            "contact_1": round(float(np.mean(contact == 1)), 5),
            "roof_0": round(float(np.mean(roof == 0)), 4),
            "ignore_255": round(float(np.mean(roof == IGNORE)), 4),
            "train_known": round(float(np.mean(roof_train != IGNORE)), 4),
            "val_known": round(float(np.mean((roof != IGNORE) & (split == SPLIT_VAL))), 4),
        },
        "files": {name: {"sha256": sha256_file(out_dir / name)} for name in files},
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles-glob", default=str(REPO_ROOT / "workspace/output/cache_tile_Cluj-?-?.tif"))
    ap.add_argument("--gpkg", type=Path, default=REPO_ROOT / "workspace/reviews/opera_review_deduplicated_20261029.gpkg")
    ap.add_argument("--html", type=Path, default=REPO_ROOT / "workspace/reviews/catalog_cladiri_ortofoto.html")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--no-ndsm", action="store_true", help="skip LiDAR ground negatives (RGB-only UATs)")
    ap.add_argument("--consensus", type=Path, help="consensus_labels.gpkg from build_consensus_labels.py")
    ap.add_argument("--val-min-y", type=float, default=585650.0)
    ap.add_argument("--out-dir", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    args = ap.parse_args(argv)
    tiles = sorted(Path(p) for p in glob.glob(args.tiles_glob))
    if not tiles:
        print(f"no tiles match {args.tiles_glob}", file=sys.stderr)
        return 1
    m = build(tiles, args.gpkg, args.html, None if args.no_ndsm else args.ndsm, args.out_dir, args.val_min_y,
              args.consensus)
    print(json.dumps({k: m[k] for k in ("shape_hw", "counts", "pixel_fractions")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
