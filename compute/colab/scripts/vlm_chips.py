"""Render orthophoto chips for the VLM assistant (local, no GPU) and find unvectorized building candidates.

Chips: crop around a polygon (+6 m), upscale 2x (0.075 m/px, at most 768 px), draw the outline in magenta.
Sets:
  owner      owner-reviewed polygons (ADMIS / AJUSTARE targets / hard negatives) - VLM calibration only
  proposal   loop proposals (final GPKG)
  candidate  elevated (nDSM >= 2.5 m), non-foliage blobs >= 15 m2 that no proposal or review polygon covers;
             outlined from the ensemble roof probability (>= 0.25) or, failing that, the nDSM blob

Only pixels go to the VM (no coordinates). Writes <out>/chips/*.png, <out>/chips_manifest.json and
<out>/candidates_epsg3844.gpkg.
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
from scan_roof2d_aoi import chip_for, regularize  # noqa: E402

REVIEW = REPO_ROOT / "workspace/reviews/opera_review_deduplicated_20261029.gpkg"
OWNER_LAYERS = {"1_ADMIS_FORME_BUNE_2D": "ADMIS", "3_AJUSTARI_TINTA_LOOP_A100": "AJUSTARE",
                "4_MUTILATE_SI_ELIMINATE_AUDIT": "ELIMINAT"}


def render_chip(poly, rgb, transform, path: Path, max_px: int = 768) -> None:
    import cv2

    chip, px, _, _ = chip_for(poly, rgb, transform, margin_m=6.0)
    s = min(2.0, max_px / max(chip.shape[:2]))
    img = cv2.resize(np.ascontiguousarray(chip), (max(1, int(chip.shape[1] * s)), max(1, int(chip.shape[0] * s))),
                     interpolation=cv2.INTER_CUBIC)
    pts = np.round(np.asarray(px) * s).astype(np.int32)
    cv2.polylines(img, [pts], True, (255, 0, 255), 2)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))


def find_candidates(rgb, transform, probs_roof, ndsm, ndsm_t, covered, min_m2: float = 15.0):
    """Elevated non-foliage blobs on the 1 m nDSM grid that nothing covers yet, outlined at 0.15 m."""
    import rasterio
    from rasterio.features import shapes
    from rasterio.warp import Resampling, reproject
    from scipy import ndimage
    from shapely.geometry import shape

    rgb_1m = np.zeros((3,) + ndsm.shape, dtype=np.uint8)
    reproject(np.moveaxis(rgb, -1, 0), rgb_1m, src_transform=transform, src_crs="EPSG:3844", dst_transform=ndsm_t,
              dst_crs="EPSG:3844", resampling=Resampling.average)
    rgb_1m = np.moveaxis(rgb_1m, 0, -1)
    near = rasterize([g.buffer(1.0) for g in covered], ndsm_t, ndsm.shape, all_touched=True)
    elevated = np.isfinite(ndsm) & (ndsm >= 2.5) & ~foliage(rgb_1m) & ~near & (rgb_1m.max(axis=2) > 0)
    elevated = ndimage.binary_opening(elevated, iterations=1)
    blobs = [shape(s) for s, v in shapes(elevated.astype(np.uint8), mask=elevated, transform=ndsm_t) if v == 1]
    out = []
    for b in blobs:
        if b.area < min_m2:
            continue
        win = b.buffer(2.0)
        _, _, _, chip_t = chip_for(win, rgb, transform, margin_m=0.0)
        chip_p, _, _, _ = chip_for(win, probs_roof[..., None].repeat(3, axis=2), transform, margin_m=0.0)
        mask = chip_p[..., 0] >= 64  # ensemble roof prob >= 0.25 (uint8 / 255)
        poly, source = None, "ndsm_blob"
        if mask.sum() * abs(transform.a * transform.e) >= min_m2:
            lab, n = ndimage.label(mask)
            k = int(np.argmax(ndimage.sum(mask, lab, index=np.arange(1, n + 1)))) + 1
            parts = [shape(s) for s, v in shapes((lab == k).astype(np.uint8), mask=lab == k, transform=chip_t) if v == 1]
            if parts:
                cand = max(parts, key=lambda g: g.area)
                if cand.intersection(b).area > 0.3 * b.area:
                    poly, source = cand, "roof_prob_0.25"
        if poly is None:
            poly = b
        reg = regularize(poly.buffer(0))
        if reg.is_valid and reg.area >= min_m2 and not any(reg.intersection(c).area > 0.3 * reg.area for c in covered):
            out.append((reg, source))
    return out


def build(final_gpkg: Path, data: Path, probs: Path, ndsm_path: Path, out: Path) -> dict:
    import geopandas as gpd
    import rasterio

    (out / "chips").mkdir(parents=True, exist_ok=True)
    with rasterio.open(data / "aoi_rgb.tif") as src:
        rgb, transform = np.moveaxis(src.read(), 0, -1), src.transform
    with rasterio.open(probs) as src:
        probs_roof = src.read(1)
    with rasterio.open(ndsm_path) as src:
        ndsm, ndsm_t = src.read(1).astype(np.float32), src.transform

    manifest = []
    for layer, verdict in OWNER_LAYERS.items():
        for _, r in gpd.read_file(REVIEW, layer=layer).iterrows():
            cid = "owner_" + r.building_id.replace(":", "_")
            render_chip(r.geometry, rgb, transform, out / "chips" / f"{cid}.png")
            manifest.append({"id": cid, "set": "owner", "owner_verdict": verdict, "ref": r.building_id})
    props = gpd.read_file(final_gpkg, layer="proposals_all")
    for _, r in props.iterrows():
        cid = "prop_" + r.proposal_id
        render_chip(r.geometry, rgb, transform, out / "chips" / f"{cid}.png")
        manifest.append({"id": cid, "set": "proposal", "ref": r.proposal_id})

    covered = list(props.geometry) + [g for layer in list(OWNER_LAYERS) + ["2_AJUSTARI_REPARATE_V1_V6"]
                                      for g in gpd.read_file(REVIEW, layer=layer).geometry]
    cands = find_candidates(rgb, transform, probs_roof, ndsm, ndsm_t, covered)
    rows = []
    for i, (g, source) in enumerate(cands):
        cid = f"cand_{i:04d}"
        render_chip(g, rgb, transform, out / "chips" / f"{cid}.png")
        manifest.append({"id": cid, "set": "candidate", "ref": cid})
        rows.append({"candidate_id": cid, "outline_source": source, "geometry": g})
    gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3844").to_file(out / "candidates_epsg3844.gpkg",
                                                                        layer="candidates", driver="GPKG")
    (out / "chips_manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    counts = {s: sum(1 for m in manifest if m["set"] == s) for s in ("owner", "proposal", "candidate")}
    return {"chips": len(manifest), **counts}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--final", type=Path, default=REPO_ROOT / "workspace/reviews/final_2d_roofs_loopq4_epsg3844.gpkg")
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    ap.add_argument("--probs", type=Path, default=REPO_ROOT / "workspace/colab_runs/loop_q/ens_b1_b3r_l3.tif")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    print(json.dumps(build(args.final, args.data, args.probs, args.ndsm, args.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
