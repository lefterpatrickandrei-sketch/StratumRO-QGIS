"""Pure-numpy helpers for L2a training (no torch, no GPU). Importable and unit-tested locally.

Input contract: each tile is a 4-band GeoTIFF (R, G, B uint8, nDSM metres float) + a 1-band mask,
all in EPSG:3844 on a common grid.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
NDSM_MAX_M = 40.0
REQUIRED_CRS = "EPSG:3844"
SPLITS = ("train", "val", "test")


def prepare_input(rgb_uint8: np.ndarray, ndsm_m: np.ndarray) -> np.ndarray:
    """(H,W,3) uint8 + (H,W) float metres -> (4,H,W) float32.

    RGB uses ImageNet mean/std. nDSM is clipped to 0..40 m, scaled to 0..1, and nodata/NaN becomes 0.
    """
    if rgb_uint8.ndim != 3 or rgb_uint8.shape[2] != 3:
        raise ValueError(f"rgb must be (H,W,3), got {rgb_uint8.shape}")
    if ndsm_m.shape != rgb_uint8.shape[:2]:
        raise ValueError("rgb and ndsm must share one grid (resample before tiling)")
    rgb = (rgb_uint8.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    ndsm = np.nan_to_num(ndsm_m.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
    ndsm = np.clip(ndsm, 0.0, NDSM_MAX_M) / NDSM_MAX_M
    return np.concatenate([rgb.transpose(2, 0, 1), ndsm[None]], axis=0).astype(np.float32)


def augment(x: np.ndarray, mask: np.ndarray, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray]:
    """x (4,H,W), mask (H,W). Geometric ops hit all 4 channels + mask; photometric ops hit RGB only.

    nDSM heights are never jittered.
    """
    k = int(rng.integers(0, 4))
    x, mask = np.rot90(x, k, axes=(1, 2)), np.rot90(mask, k, axes=(0, 1))
    if rng.random() < 0.5:
        x, mask = x[:, :, ::-1], mask[:, ::-1]
    x = np.ascontiguousarray(x).copy()
    mask = np.ascontiguousarray(mask)
    contrast = float(rng.uniform(0.85, 1.15))
    brightness = float(rng.uniform(-0.15, 0.15))
    x[:3] = x[:3] * contrast + brightness  # RGB channels only
    return x, mask


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def bbox_gap(a: list[float], b: list[float]) -> float:
    """Shortest distance (metres) between two (minx, miny, maxx, maxy) boxes; 0 if they touch/overlap."""
    dx = max(a[0] - b[2], b[0] - a[2], 0.0)
    dy = max(a[1] - b[3], b[1] - a[3], 0.0)
    return float((dx * dx + dy * dy) ** 0.5)


def check_split_leakage(tiles: list[dict], buffer_m: float = 30.0) -> list[str]:
    """Tiles in different splits must be at least ``buffer_m`` apart (spatial split, not random tiles)."""
    problems = []
    for i, a in enumerate(tiles):
        for b in tiles[i + 1:]:
            if a["split"] != b["split"] and bbox_gap(a["bounds"], b["bounds"]) < buffer_m:
                problems.append(f"{a['id']}({a['split']}) and {b['id']}({b['split']}) are closer than {buffer_m} m")
    return problems


def validate_manifest(manifest: dict, root: Path | None = None, verify_hashes: bool = False) -> list[str]:
    """Return a list of problems. Checks CRS, split names, unique ids, leakage buffer and (optionally) SHA-256."""
    problems: list[str] = []
    if manifest.get("crs") != REQUIRED_CRS:
        problems.append(f"manifest crs must be {REQUIRED_CRS}, got {manifest.get('crs')!r}")
    tiles = manifest.get("tiles", [])
    if not tiles:
        problems.append("manifest has no tiles")
    ids = [t.get("id") for t in tiles]
    if len(ids) != len(set(ids)):
        problems.append("duplicate tile ids")
    for t in tiles:
        if t.get("split") not in SPLITS:
            problems.append(f"tile {t.get('id')}: split must be one of {SPLITS}")
        if len(t.get("bounds", [])) != 4:
            problems.append(f"tile {t.get('id')}: bounds must be [minx, miny, maxx, maxy]")
    if not problems:
        problems += check_split_leakage(tiles, float(manifest.get("buffer_m", 30.0)))
    if verify_hashes and root is not None:
        for t in tiles:
            for key in ("image", "mask"):
                p = root / t[key]
                if not p.is_file():
                    problems.append(f"missing file: {p}")
                elif sha256_file(p) != t.get(f"{key}_sha256"):
                    problems.append(f"sha256 mismatch: {p}")
    return problems


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
