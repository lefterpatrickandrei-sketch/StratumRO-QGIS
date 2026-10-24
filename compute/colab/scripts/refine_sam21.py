"""Batch SAM 2.1 Tiny refinement of candidate masks, for a Colab GPU VM.

STATUS: scaffolded, NOT run. Output masks are PROPOSALS, never approvals.

Pattern (SAM 2 README): one ``set_image`` per tile, then ONE batched ``predict(box=Nx4)`` with all
candidate boxes of that tile, ``multimask_output=False``; free GPU memory between tiles.
SAM is RGB-only: it has no nDSM input. Evaluate refined vs. unrefined IoU on the held-out set before
trusting it (SAM can over-smooth gabled roof planes).

On the VM:
    pip install git+https://github.com/facebookresearch/sam2.git rasterio scipy
    # weights (verify the URL against the sam2 README checkpoints table before first use):
    wget https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
    python refine_sam21.py --tiles DIR --candidates DIR --out DIR --checkpoint sam2.1_hiera_tiny.pt
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

MODEL_CFG = "configs/sam2.1/sam2.1_hiera_t.yaml"


def mask_to_boxes(mask: np.ndarray, min_area_px: int = 40) -> np.ndarray:
    """Binary (H,W) mask -> (N,4) float32 boxes [x0, y0, x1, y1] (pixel coords), one per component."""
    from scipy import ndimage

    labels, n = ndimage.label(mask > 0)
    boxes = []
    for sl, idx in zip(ndimage.find_objects(labels), range(1, n + 1)):
        if sl is None:
            continue
        ys, xs = sl
        if int((labels[sl] == idx).sum()) < min_area_px:
            continue
        boxes.append([xs.start, ys.start, xs.stop - 1, ys.stop - 1])
    return np.asarray(boxes, dtype=np.float32).reshape(-1, 4)


def load_progress(path: Path) -> set[str]:
    return set(json.loads(path.read_text())["done"]) if path.is_file() else set()


def save_progress(path: Path, done: set[str]) -> None:
    path.write_text(json.dumps({"done": sorted(done)}), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles", required=True)
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--checkpoint", default="sam2.1_hiera_tiny.pt")
    ap.add_argument("--min-area-px", type=int, default=40)
    args = ap.parse_args(argv)

    import rasterio
    import torch
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor

    out = Path(args.out)
    (out / "masks").mkdir(parents=True, exist_ok=True)
    progress_path = out / "progress.json"
    done = load_progress(progress_path)  # resume: skip finished tiles

    predictor = SAM2ImagePredictor(build_sam2(MODEL_CFG, args.checkpoint, device="cuda"))
    stats = []
    for tile_path in sorted(Path(args.tiles).glob("*.tif")):
        tid = tile_path.stem
        cand_path = Path(args.candidates) / f"{tid}.npy"
        if tid in done or not cand_path.is_file():
            continue
        t0 = time.time()
        torch.cuda.reset_peak_memory_stats()
        with rasterio.open(tile_path) as src:
            rgb = np.moveaxis(src.read([1, 2, 3]), 0, -1).astype(np.uint8)
        boxes = mask_to_boxes(np.load(cand_path), args.min_area_px)
        if len(boxes):
            with torch.inference_mode(), torch.autocast("cuda", dtype=torch.bfloat16):
                predictor.set_image(rgb)
                masks, scores, _ = predictor.predict(box=boxes, multimask_output=False)
            masks = np.asarray(masks).reshape(len(boxes), *rgb.shape[:2]) > 0
            np.savez_compressed(out / "masks" / f"{tid}.npz", masks=masks, scores=np.asarray(scores).ravel(), boxes=boxes)
        predictor.reset_predictor()
        torch.cuda.empty_cache()
        stats.append({
            "tile": tid, "boxes": int(len(boxes)), "seconds": round(time.time() - t0, 2),
            "peak_vram_mib": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        })
        done.add(tid)
        save_progress(progress_path, done)
        print(stats[-1], flush=True)

    (out / "metrics.json").write_text(json.dumps({
        "job": "refine_sam21", "status": "PROPOSAL_NOT_ACCEPTED", "tiles": stats,
        "note": "Peak VRAM is measured per tile; no official SAM 2.1 Tiny VRAM figure exists.",
    }, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
