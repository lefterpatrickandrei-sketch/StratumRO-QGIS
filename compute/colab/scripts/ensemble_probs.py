"""Average several probs_roof_edge_corner.tif rasters (same grid) into one ensemble raster.

Single 25-epoch runs of the same recipe differ by up to 0.07 val IoU; averaging members cuts that variance.
Feed the result to scan_roof2d_aoi.py --probs.

    python compute/colab/scripts/ensemble_probs.py --out ens.tif run_a/probs.tif run_b/probs.tif [...]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np


def average(paths: list[Path], out: Path) -> None:
    import rasterio

    acc, profile = None, None
    for p in paths:
        with rasterio.open(p) as src:
            arr = src.read().astype(np.float32)
            if acc is None:
                acc, profile, transform = arr, src.profile, src.transform
            else:
                if src.transform != transform or arr.shape != acc.shape:
                    raise ValueError(f"{p} is not on the grid of {paths[0]}")
                acc += arr
    with rasterio.open(out, "w", **profile) as dst:
        dst.write(np.round(acc / len(paths)).astype(np.uint8))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("probs", type=Path, nargs="+")
    args = ap.parse_args(argv)
    average(args.probs, args.out)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
