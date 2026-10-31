"""Meta/WRI high-resolution canopy height from RGB on the whole AOI, measured against our LiDAR nDSM (Colab A100).

Question answered: can an RGB-only canopy height model replace LiDAR for the tree-occlusion evidence, so the
2D roof pipeline runs on UATs without LiDAR?

Models (facebookresearch/HighResCanopyHeight, Apache-2.0, public checkpoints):
  sat    SSLhuge_satellite.pth on GPU, Meta normalisation only (their normtype 0, satellite path)
  aerial compressed_SSLhuge_aerial.pth (int8, CPU) with the RNet quantile normalisation (their normtype 2)
Each is run at 0.5 m and 0.3 m ground sampling (the AOI is 0.15 m), 256 px tiles, 32 px overlap.

Metrics against LiDAR (nDSM resampled to the model grid; trees = foliage colour & nDSM >= 2.5 m):
  tree MAE / bias / Pearson r, mean height on ground (nDSM < 0.5 m, not foliage) and on owner ADMIS roofs,
  and the tall-vegetation mask (foliage & CHM >= 2.5 m) vs the LiDAR tree mask (precision / recall / IoU),
  next to the colour-only baseline (foliage alone).

    python meta_canopy_eval.py --data <dataset_v3 dir> --ndsm <cluj_ndsm_1m.tif> --gpkg <review gpkg> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_consensus_labels import foliage  # noqa: E402
from roof2d_data import rasterize  # noqa: E402

BASE = "https://dataforgood-fb-data.s3.amazonaws.com/forests/v1/models/saved_checkpoints/"
MEAN, STD = (0.420, 0.411, 0.296), (0.213, 0.156, 0.143)


def fetch(hrch: Path) -> None:
    if not (hrch / "models").is_dir():
        subprocess.run(["git", "clone", "-q", "https://github.com/facebookresearch/HighResCanopyHeight", str(hrch)], check=True)
    for f in ("SSLhuge_satellite.pth", "compressed_SSLhuge_aerial.pth", "aerial_normalization_quantiles_predictor.ckpt"):
        if not (hrch / f).is_file():
            subprocess.run(["wget", "-q", "-O", str(hrch / f), BASE + f], check=True)


def load_models(hrch: Path):
    import torch

    sys.path.insert(0, str(hrch))
    os.chdir(hrch)  # inference.py imports local modules relative to the repo
    from inference import SSLModule
    from models.regressor import RNet

    sat = SSLModule(ssl_path=str(hrch / "SSLhuge_satellite.pth")).to("cuda").eval()
    aerial = SSLModule(ssl_path=str(hrch / "compressed_SSLhuge_aerial.pth")).eval()
    ck = torch.load(hrch / "aerial_normalization_quantiles_predictor.ckpt", map_location="cpu")["state_dict"]
    ck = {k.replace("backbone.", ""): v for k, v in ck.items()}
    rnet = RNet(n_classes=6).eval()
    rnet.load_state_dict(ck)
    return sat, aerial, rnet


def predict(model, rgb01: np.ndarray, device: str, rnet=None, tile: int = 256, overlap: int = 32) -> np.ndarray:
    """CHM (metres) for an (H, W, 3) float image, tiles blended by averaging."""
    import torch
    import torchvision.transforms as T

    norm = T.Normalize(MEAN, STD)
    h, w = rgb01.shape[:2]
    acc, cnt = np.zeros((h, w), np.float32), np.zeros((h, w), np.float32)
    step = tile - overlap
    for r in range(0, max(h - overlap, 1), step):
        for c in range(0, max(w - overlap, 1), step):
            part = np.zeros((tile, tile, 3), np.float32)
            src = rgb01[r : r + tile, c : c + tile]
            part[: src.shape[0], : src.shape[1]] = src
            if part.max() == 0:
                continue
            x = torch.from_numpy(part).permute(2, 0, 1).float()
            if rnet is not None:  # normtype 2: map this tile's 5/95 % quantiles onto predicted satellite ones
                q = rnet(x[None]).detach()[0]
                for i in range(3):
                    p5, p95 = np.percentile(x[i].numpy(), 5), np.percentile(x[i].numpy(), 95)
                    x[i] = (x[i] - p5) * ((q[3 + i] - q[i]) / max(p95 - p5, 1e-6)) + q[i]
            with torch.no_grad():
                y = model(norm(x)[None].to(device)).float().relu().cpu().numpy()[0, 0]
            hh, ww = min(tile, h - r), min(tile, w - c)
            acc[r : r + hh, c : c + ww] += y[:hh, :ww]
            cnt[r : r + hh, c : c + ww] += 1
    out = acc / np.maximum(cnt, 1)
    out[rgb01.max(axis=2) == 0] = np.nan
    return out


def evaluate(chm, rgb_u8, ndsm, roofs_mask) -> dict:
    fol = foliage(rgb_u8)
    valid = np.isfinite(chm) & np.isfinite(ndsm) & (rgb_u8.max(axis=2) > 0)
    tree = valid & fol & (ndsm >= 2.5)
    ground = valid & ~fol & (ndsm < 0.5)
    roof = valid & roofs_mask
    tall = valid & fol & (chm >= 2.5)
    lidar_tree = tree

    def prf(pred, ref):
        tp = float((pred & ref).sum())
        return {"precision": round(tp / max(pred.sum(), 1), 3), "recall": round(tp / max(ref.sum(), 1), 3),
                "iou": round(tp / max((pred | ref).sum(), 1), 3)}

    d = chm[tree] - ndsm[tree]
    return {
        "tree_px": int(tree.sum()),
        "tree_mae_m": round(float(np.abs(d).mean()), 2), "tree_bias_m": round(float(d.mean()), 2),
        "tree_pearson_r": round(float(np.corrcoef(chm[tree], ndsm[tree])[0, 1]), 3),
        "ground_mean_chm_m": round(float(chm[ground].mean()), 2),
        "owner_roof_mean_chm_m": round(float(chm[roof].mean()), 2) if roof.any() else None,
        "tall_veg_from_rgb_vs_lidar_trees": prf(tall, lidar_tree),
        "colour_only_baseline_vs_lidar_trees": prf(valid & fol, lidar_tree),
    }


def main(argv: list[str] | None = None) -> int:
    import cv2
    import geopandas as gpd
    import rasterio
    from rasterio.transform import Affine
    from rasterio.warp import Resampling, reproject

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--ndsm", type=Path, required=True)
    ap.add_argument("--gpkg", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--hrch", type=Path, default=Path("/content/hrch"))
    ap.add_argument("--gsds", default="0.5,0.3")
    args = ap.parse_args(argv)
    data, out, ndsm_p, gpkg = args.data.resolve(), args.out.resolve(), args.ndsm.resolve(), args.gpkg.resolve()
    out.mkdir(parents=True, exist_ok=True)
    fetch(args.hrch)
    sat, aerial, rnet = load_models(args.hrch)
    with rasterio.open(data / "aoi_rgb.tif") as src:
        rgb, t0 = np.moveaxis(src.read(), 0, -1), src.transform
    roofs = list(gpd.read_file(gpkg, layer="1_ADMIS_FORME_BUNE_2D").geometry.buffer(-0.7))
    report = {"source": "facebookresearch/HighResCanopyHeight (Apache-2.0)", "runs": {}}
    for gsd in [float(v) for v in args.gsds.split(",")]:
        f = abs(t0.a) / gsd
        small = cv2.resize(rgb, (int(rgb.shape[1] * f), int(rgb.shape[0] * f)), interpolation=cv2.INTER_AREA)
        t = t0 * Affine.scale(1 / f)
        nd = np.full(small.shape[:2], np.nan, np.float32)
        with rasterio.open(ndsm_p) as src:
            reproject(src.read(1).astype(np.float32), nd, src_transform=src.transform, src_crs=src.crs, dst_transform=t,
                      dst_crs="EPSG:3844", resampling=Resampling.average, dst_nodata=np.nan)
        rmask = rasterize([g for g in roofs if not g.is_empty], t, small.shape[:2])
        rgb01 = small.astype(np.float32) / 255.0
        for name, model, dev, rn in (("sat", sat, "cuda", None), ("aerial", aerial, "cpu", rnet)):
            t1 = time.time()
            chm = predict(model, rgb01, dev, rn)
            m = evaluate(chm, small, nd, rmask)
            m["seconds"] = round(time.time() - t1, 1)
            key = f"{name}_{gsd:.2f}m"
            report["runs"][key] = m
            print(key, json.dumps(m), flush=True)
            prof = dict(driver="GTiff", height=chm.shape[0], width=chm.shape[1], count=1, dtype="float32",
                        crs="EPSG:3844", transform=t, compress="deflate", nodata=np.nan)
            with rasterio.open(out / f"chm_{key}.tif", "w", **prof) as dst:
                dst.write(chm[None])
    (out / "canopy_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
