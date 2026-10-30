"""Phase 1 2D roof data: AOI orthophoto mosaic + partial-label rasters, all on one EPSG:3844 grid.

The model input is RGB only, so weights can run on any UAT that has an orthophoto. LiDAR nDSM is
used here only as a *training-label* source for confident ground negatives; it is never a model input.

Roof label raster (uint8):
  1   owner ADMIS polygons (layer 1_ADMIS_FORME_BUNE_2D).
  0   owner hard negatives (layer 4, never over a positive), a 0.3..1.2 m ring outside ADMIS roofs,
      and LiDAR ground (nDSM < 1 m, eroded 2 m) away from every known candidate.
  255 everything else (ignore_index): AJUSTARE targets (layer 3), heuristic repairs (layer 2, no owner
      verdict yet), other catalog candidates, unreviewed area, orthophoto NoData, split buffer.

Edge / corner rasters are 1 on ADMIS outlines (~0.3 m band) / vertices (~0.45 m disks), else 0. They are
only supervised where the roof label is not 255.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

IGNORE = 255
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
SPLIT_TRAIN, SPLIT_VAL, SPLIT_BUFFER = 0, 1, 2


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rasterize(geoms, transform, shape, all_touched: bool = False) -> np.ndarray:
    """Boolean (H, W) mask of shapely geometries on the grid."""
    from rasterio.features import rasterize as rio_rasterize

    geoms = [g for g in geoms if g is not None and not g.is_empty]
    if not geoms:
        return np.zeros(shape, dtype=bool)
    return rio_rasterize(
        [(g, 1) for g in geoms], out_shape=shape, transform=transform, fill=0, dtype="uint8", all_touched=all_touched
    ).astype(bool)


def corner_points(poly, min_turn_deg: float = 20.0) -> list[tuple[float, float]]:
    """Vertices of a polygon exterior where the outline turns by at least ``min_turn_deg``."""
    coords = np.asarray(poly.exterior.coords)[:-1]
    out = []
    n = len(coords)
    for i in range(n):
        a, b, c = coords[i - 1], coords[i], coords[(i + 1) % n]
        v1, v2 = b - a, c - b
        l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if l1 < 1e-6 or l2 < 1e-6:
            continue
        turn = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (l1 * l2), -1.0, 1.0)))
        if turn >= min_turn_deg:
            out.append((float(b[0]), float(b[1])))
    return out


def build_label_rasters(
    rgb: np.ndarray,
    transform,
    positives: list,
    negatives: list,
    ignore: list,
    ground: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (roof, edge, corner) uint8 rasters for the partial-label policy in the module docstring.

    positives / negatives / ignore are shapely polygons in the grid CRS (metres). ``ground`` is an optional
    boolean raster of confident ground pixels (already eroded) on the same grid.
    """
    from shapely.geometry import Point
    from shapely.ops import unary_union

    shape = rgb.shape[:2]
    roof = np.full(shape, IGNORE, dtype=np.uint8)
    known = unary_union([g for g in positives + negatives + ignore if g is not None and not g.is_empty])

    if ground is not None:
        near_candidate = np.zeros(shape, dtype=bool)
        if not known.is_empty:
            near_candidate = rasterize([known.buffer(1.0)], transform, shape, all_touched=True)
        roof[ground & ~near_candidate] = 0
    pos_union = unary_union(positives) if positives else None
    if pos_union is not None and not pos_union.is_empty:
        roof[rasterize([pos_union.buffer(1.2).difference(pos_union.buffer(0.3))], transform, shape)] = 0
    if negatives:
        roof[rasterize(negatives, transform, shape)] = 0
    if ignore:
        roof[rasterize([g.buffer(1.0) for g in ignore], transform, shape, all_touched=True)] = IGNORE
    if positives:
        roof[rasterize(positives, transform, shape)] = 1

    edge = np.zeros(shape, dtype=np.uint8)
    corner = np.zeros(shape, dtype=np.uint8)
    if positives:
        edge[rasterize([p.exterior.buffer(0.18) for p in positives], transform, shape, all_touched=True)] = 1
        pts = [Point(xy).buffer(0.45) for p in positives for xy in corner_points(p)]
        corner[rasterize(pts, transform, shape, all_touched=True)] = 1

    nodata = rgb.astype(np.int32).sum(axis=2) <= 15
    roof[nodata] = IGNORE
    edge[nodata] = 0
    corner[nodata] = 0
    return roof, edge, corner


def split_raster(transform, shape, val_min_y: float, buffer_m: float = 30.0) -> np.ndarray:
    """North/south spatial split: rows north of ``val_min_y + buffer/2`` are val, a buffer band is excluded."""
    rows = np.arange(shape[0])
    y = transform.f + (rows + 0.5) * transform.e
    col = np.full(shape[0], SPLIT_BUFFER, dtype=np.uint8)
    col[y >= val_min_y + buffer_m / 2] = SPLIT_VAL
    col[y <= val_min_y - buffer_m / 2] = SPLIT_TRAIN
    return np.repeat(col[:, None], shape[1], axis=1)


def normalize_rgb(rgb_float01: np.ndarray) -> np.ndarray:
    """(H, W, 3) float in [0, 1] -> (3, H, W) ImageNet-normalized float32."""
    return ((rgb_float01 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1).astype(np.float32)


def augment_photometric(rgb01: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Seasonal / lighting / sensor augmentation on (H, W, 3) float [0, 1]. NoData black stays black."""
    nodata = rgb01.sum(axis=2) <= 15 / 255.0
    x = rgb01.copy()
    x = x * rng.uniform(0.9, 1.1, size=3).astype(np.float32)  # white balance
    if rng.random() < 0.35:  # autumn: push green foliage towards yellow / rust
        a = float(rng.uniform(0.3, 0.9))
        green = (x[..., 1] > x[..., 0]) & (x[..., 1] > x[..., 2])
        x[..., 0] = np.where(green, x[..., 0] + a * (x[..., 1] - x[..., 0]) * 1.2, x[..., 0])
        x[..., 1] = np.where(green, x[..., 1] * (1 - 0.15 * a), x[..., 1])
    gray = x.mean(axis=2, keepdims=True)
    x = gray + (x - gray) * float(rng.uniform(0.6, 1.4))  # saturation
    x = (x - 0.5) * float(rng.uniform(0.75, 1.25)) + 0.5 + float(rng.uniform(-0.12, 0.12))
    x = np.clip(x, 0.0, 1.0) ** float(rng.uniform(0.7, 1.4))
    if rng.random() < 0.4:  # hard cast shadow
        import cv2

        h, w = x.shape[:2]
        pts = (rng.random((4, 2)) * [w, h]).astype(np.int32)
        m = np.zeros((h, w), dtype=np.uint8)
        cv2.fillConvexPoly(m, cv2.convexHull(pts), 1)
        x[m.astype(bool)] *= float(rng.uniform(0.45, 0.75))
    if rng.random() < 0.2:
        import cv2

        x = cv2.GaussianBlur(x, (0, 0), float(rng.uniform(0.5, 1.2)))
    if rng.random() < 0.3:
        x = x + rng.normal(0.0, float(rng.uniform(0.01, 0.03)), size=x.shape).astype(np.float32)
    x = np.clip(x, 0.0, 1.0).astype(np.float32)
    x[nodata] = 0.0
    return x


def sample_crop(
    rgb: np.ndarray,
    labels: np.ndarray,
    center_rc: tuple[int, int],
    out_size: int,
    scale: float,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Crop ``out_size*scale`` source px around ``center_rc`` and resize to ``out_size``.

    scale > 1 simulates a coarser GSD (e.g. 1.67 turns 0.15 m into 0.25 m), < 1 a finer one.
    labels is (C, H, W) uint8 and is resized with nearest neighbour. Out-of-AOI pixels are NoData/IGNORE.
    Returns rgb float [0, 1] (S, S, 3) and labels (C, S, S). Applies rot90/flip when rng is given.
    """
    import cv2

    side = max(8, int(round(out_size * scale)))
    r0, c0 = int(center_rc[0]) - side // 2, int(center_rc[1]) - side // 2
    h, w = rgb.shape[:2]
    rr0, cc0, rr1, cc1 = max(r0, 0), max(c0, 0), min(r0 + side, h), min(c0 + side, w)
    img = np.zeros((side, side, 3), dtype=np.uint8)
    lab = np.full((labels.shape[0], side, side), IGNORE, dtype=np.uint8)
    lab[1:] = 0
    if rr1 > rr0 and cc1 > cc0:
        img[rr0 - r0 : rr1 - r0, cc0 - c0 : cc1 - c0] = rgb[rr0:rr1, cc0:cc1]
        lab[:, rr0 - r0 : rr1 - r0, cc0 - c0 : cc1 - c0] = labels[:, rr0:rr1, cc0:cc1]
    if side != out_size:
        img = cv2.resize(img, (out_size, out_size), interpolation=cv2.INTER_AREA if scale > 1 else cv2.INTER_LINEAR)
        lab = np.stack([cv2.resize(l, (out_size, out_size), interpolation=cv2.INTER_NEAREST) for l in lab])
    if rng is not None:
        k = int(rng.integers(0, 4))
        img, lab = np.rot90(img, k, axes=(0, 1)), np.rot90(lab, k, axes=(1, 2))
        if rng.random() < 0.5:
            img, lab = img[:, ::-1], lab[:, :, ::-1]
    return np.ascontiguousarray(img).astype(np.float32) / 255.0, np.ascontiguousarray(lab)


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))
