"""Consensus training labels from independent sources (agent-built, never owner verdicts).

Positives (CONSENSUS_3SRC): an auto-pipeline roof hypothesis (REST ROOF_HYPOTHESES_ORTHO90) outside the
owner review that (1) a loop proposal matches with IoU >= 0.75, (2) LiDAR confirms as elevated (nDSM median
>= 2.5 m and >= 70 % of cells >= 2 m) and (3) whose matching proposal passed all six V1..V6 gates. The label
is the intersection of hypothesis and proposal; the rest of both stays ignore (255).

Tree negatives: nDSM >= 2.5 m with foliage colour (summer ExG or autumn warm texture) farther than 1.5 m from
any known candidate - they target the "outline slides onto the tree crown" failure.

Writes <out>/consensus_labels.gpkg (layers consensus_positive, tree_negative). The dataset builder burns them
with --consensus. Inference stays RGB-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from roof2d_data import rasterize  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
REST = REPO_ROOT / "workspace/reviews/auto_unvectorized_20261018/auto_unvectorized_orthogonal.gpkg"
REVIEW = REPO_ROOT / "workspace/reviews/opera_review_deduplicated_20261029.gpkg"


def ndsm_stats(poly, ndsm, ndsm_t):
    m = rasterize([poly], ndsm_t, ndsm.shape, all_touched=True)
    v = ndsm[m & np.isfinite(ndsm)]
    if v.size < 4:
        return None, None
    return float(np.median(v)), float(np.mean(v >= 2.0))


def foliage(rgb: np.ndarray) -> np.ndarray:
    r, g, b = (rgb[..., i].astype(np.float32) for i in range(3))
    exg = 2 * g - r - b
    autumn = (r > g * 0.95) & (g > b * 1.15) & (r > 60) & (r < 210) & ((r - b) > 35)
    return (exg > 18) | autumn


def build(proposals: Path, data: Path, ndsm_path: Path, out: Path) -> dict:
    import geopandas as gpd
    import rasterio
    from rasterio.warp import Resampling, reproject
    from scipy import ndimage
    from shapely.strtree import STRtree

    out.mkdir(parents=True, exist_ok=True)
    with rasterio.open(ndsm_path) as src:
        ndsm, ndsm_t = src.read(1).astype(np.float32), src.transform
    props = gpd.read_file(proposals, layer="proposals_all")
    rest = gpd.read_file(REST, layer="ROOF_HYPOTHESES_ORTHO90").to_crs("EPSG:3844")
    review = [g for lyr in ("1_ADMIS_FORME_BUNE_2D", "2_AJUSTARI_REPARATE_V1_V6", "3_AJUSTARI_TINTA_LOOP_A100",
                            "4_MUTILATE_SI_ELIMINATE_AUDIT") for g in gpd.read_file(REVIEW, layer=lyr).geometry]
    rtree, ptree = STRtree(review), STRtree(list(props.geometry))

    positives, reasons = [], {"in_review": 0, "no_model_match": 0, "not_elevated": 0, "v1_v6_fail": 0, "kept": 0}
    for _, h in rest.iterrows():
        g = h.geometry
        if any(review[i].intersection(g).area > 0.2 * g.area for i in rtree.query(g)):
            reasons["in_review"] += 1
            continue
        best, best_iou = None, 0.0
        for k in ptree.query(g):
            p = props.geometry.iloc[k]
            iou = p.intersection(g).area / max(p.union(g).area, 1e-6)
            if iou > best_iou:
                best, best_iou = k, iou
        if best is None or best_iou < 0.75:
            reasons["no_model_match"] += 1
            continue
        med, frac = ndsm_stats(g, ndsm, ndsm_t)
        if med is None or med < 2.5 or frac < 0.7:
            reasons["not_elevated"] += 1
            continue
        if int(props.all_six_passed.iloc[best]) != 1:
            reasons["v1_v6_fail"] += 1
            continue
        inter = g.intersection(props.geometry.iloc[best])
        if inter.geom_type != "Polygon":
            inter = max(inter.geoms, key=lambda x: x.area)
        positives.append({"candidate_id": h.candidate_id, "proposal_id": props.proposal_id.iloc[best],
                          "iou_model": round(best_iou, 3), "ndsm_median_m": round(med, 2),
                          "status": "CONSENSUS_3SRC_NOT_OWNER", "geometry": inter})
        reasons["kept"] += 1

    # tree negatives on the 1 m nDSM grid: tall + foliage colour, away from every candidate
    with rasterio.open(data / "aoi_rgb.tif") as src:
        rgb_1m = np.zeros((3,) + ndsm.shape, dtype=np.uint8)
        reproject(src.read(), rgb_1m, src_transform=src.transform, src_crs=src.crs, dst_transform=ndsm_t,
                  dst_crs="EPSG:3844", resampling=Resampling.average)
    rgb_1m = np.moveaxis(rgb_1m, 0, -1)
    known = review + list(rest.geometry) + list(props.geometry)
    near = rasterize([g.buffer(1.5) for g in known], ndsm_t, ndsm.shape, all_touched=True)
    tree = np.isfinite(ndsm) & (ndsm >= 2.5) & foliage(rgb_1m) & ~near & (rgb_1m.max(axis=2) > 0)
    tree = ndimage.binary_opening(tree, iterations=1)
    from rasterio.features import shapes
    from shapely.geometry import shape

    tree_polys = [shape(s) for s, v in shapes(tree.astype(np.uint8), mask=tree, transform=ndsm_t) if v == 1]
    tree_polys = [p for p in tree_polys if p.area >= 4.0]

    gpkg = out / "consensus_labels.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    pos = gpd.GeoDataFrame(positives, geometry="geometry", crs="EPSG:3844") if positives else \
        gpd.GeoDataFrame({"candidate_id": []}, geometry=gpd.GeoSeries([], crs="EPSG:3844"))
    pos.to_file(gpkg, layer="consensus_positive", driver="GPKG")
    gpd.GeoDataFrame({"status": ["TREE_NEGATIVE_NDSM_FOLIAGE"] * len(tree_polys)},
                     geometry=gpd.GeoSeries(tree_polys, crs="EPSG:3844")).to_file(gpkg, layer="tree_negative", driver="GPKG")
    report = {"source_proposals": str(proposals), "rest_hypotheses": len(rest), "filter": reasons,
              "tree_negative_polygons": len(tree_polys), "tree_negative_m2": round(sum(p.area for p in tree_polys), 1)}
    (out / "consensus_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--proposals", type=Path, required=True, help="scan roof2d_proposals_epsg3844.gpkg")
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    args = ap.parse_args(argv)
    print(json.dumps(build(args.proposals, args.data, args.ndsm, args.out), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
