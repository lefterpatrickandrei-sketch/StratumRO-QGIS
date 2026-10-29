# -*- coding: utf-8 -*-
"""
StratumRO — Phase 1: 2D Roof Dataset Builder (RGB-Only, Generalizable to Any Zone/UAT)
======================================================================================
Builds the deduplicated, hierarchical 2D roof training dataset from:
  - workspace/reviews/opera_review_deduplicated_20261029.gpkg (EPSG:3844)
  - workspace/reviews/catalog_cladiri_ortofoto.html & ortho_chips/*.jpg

Hierarchical Pixel Label Encoding (Zero-Contamination Guarantee):
  - 1   = Positive 2D Roof (`1_ADMIS_FORME_BUNE_2D` + `2_AJUSTARI_REPARATE_V1_V6`)
  - 0   = Background + Verified Non-Overlapping Hard Negatives (`4_MUTILATE_SI_ELIMINATE_AUDIT`)
  - 255 = `ignore_index` on `3_AJUSTARI_TINTA_LOOP_A100` (incomplete roofs awaiting SAM 2.1
          reprompting) AND black `NoData` border pixels (`RGB <= 15`), so incomplete masks
          never teach the network to cut roofs in half.

Also generates multi-task structural supervision targets per chip:
  - `roof_mask`:   uint8 (0, 1, 255)
  - `edge_mask`:   uint8 (0, 1) — 3px boundary & eave line band for crisp 90°/45° edges
  - `corner_mask`: uint8 (0, 1) — 5px disks at roof vertices for L/U/T & rectangular corners
  - `manifest_2d_roofs.json`: spatial train/val split + `a100_reprompt_targets` queue in EPSG:3844.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw
from shapely import wkb
from shapely.geometry import Polygon

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_gpkg_geom(blob: bytes) -> Optional[Polygon]:
    if not blob or len(blob) < 8 or blob[:2] != b"GP":
        return None
    flags = blob[3]
    env_type = (flags >> 1) & 7
    env_sizes = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}
    wkb_offset = 8 + env_sizes.get(env_type, 0)
    geom = wkb.loads(blob[wkb_offset:])
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda g: g.area)
    return geom if isinstance(geom, Polygon) else None


def build_multitask_masks_for_chip(
    rgb: np.ndarray,
    roof_px: List[List[float]],
    verdict_category: str,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Constructs (roof_mask, edge_mask, corner_mask) for a single RGB chip:
      - verdict_category in ("ADMIS", "REPAIRED"):
          interior = 1, background = 0, NoData black border = 255
          edge_mask = 1 along 3px contour, corner_mask = 1 at 5px vertex disks
      - verdict_category == "AJUSTARE_TINTA_A100":
          polygon region + 16px dilation = 255 (ignore_index during segmentation loss,
          queued for SAM 2.1 multi-box reprompting)
      - verdict_category in ("MUTILAT", "ELIMINAT"):
          entire chip (except NoData black border) = 0 (explicit hard negative)
    """
    h, w = rgb.shape[:2]
    roof_mask = np.zeros((h, w), dtype=np.uint8)
    edge_mask = np.zeros((h, w), dtype=np.uint8)
    corner_mask = np.zeros((h, w), dtype=np.uint8)

    pts = [(float(p[0]), float(p[1])) for p in roof_px] if roof_px and len(roof_px) >= 3 else []

    if verdict_category in ("ADMIS", "REPAIRED") and len(pts) >= 3:
        pil_roof = Image.new("L", (w, h), 0)
        ImageDraw.Draw(pil_roof).polygon(pts, fill=1, outline=1)
        roof_mask = np.array(pil_roof, dtype=np.uint8)

        pil_edge = Image.new("L", (w, h), 0)
        ImageDraw.Draw(pil_edge).line(pts + [pts[0]], fill=1, width=3)
        edge_mask = np.array(pil_edge, dtype=np.uint8)

        pil_corner = Image.new("L", (w, h), 0)
        d_corner = ImageDraw.Draw(pil_corner)
        for px, py in pts[:-1]:
            d_corner.ellipse([px - 3, py - 3, px + 3, py + 3], fill=1)
        corner_mask = np.array(pil_corner, dtype=np.uint8)

    elif verdict_category == "AJUSTARE_TINTA_A100" and len(pts) >= 3:
        pil_ignore = Image.new("L", (w, h), 0)
        d_ig = ImageDraw.Draw(pil_ignore)
        d_ig.polygon(pts, fill=255, outline=255)
        d_ig.line(pts + [pts[0]], fill=255, width=24)
        roof_mask = np.array(pil_ignore, dtype=np.uint8)

    elif verdict_category in ("MUTILAT", "ELIMINAT"):
        # Hard negative: all valid pixels are 0 (background / non-building)
        roof_mask[:, :] = 0

    # Mask out black NoData border pixels with ignore_index = 255
    nodata_px = np.sum(rgb.astype(np.int32), axis=2) <= 15
    roof_mask[nodata_px] = 255
    edge_mask[nodata_px] = 0
    corner_mask[nodata_px] = 0

    return roof_mask, edge_mask, corner_mask


def prepare_rgb_2d_tensor(rgb: np.ndarray) -> np.ndarray:
    """
    Normalizes an (H, W, 3) uint8 RGB orthophoto chip into a (3, H, W) float32 tensor in [0, 1].
    Strictly 3-channel RGB (zero LiDAR nDSM coupling) so the model generalizes to any zone/UAT.
    """
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"Expected (H, W, 3) RGB array, got {rgb.shape}")
    chw = np.transpose(rgb.astype(np.float32) / 255.0, (2, 0, 1))
    return np.clip(chw, 0.0, 1.0)


def build_dataset(
    gpkg_path: Path,
    html_path: Path,
    out_dir: Path,
) -> Dict[str, Any]:
    """
    Builds the complete 2D roof training dataset and manifest in `out_dir`.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("rgb", "roof_mask", "edge_mask", "corner_mask"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    html_text = html_path.read_text(encoding="utf-8")
    m = re.search(r"const BUILDINGS = (\[.*?\]);\s*\n", html_text, re.S)
    if not m:
        raise RuntimeError("Could not parse BUILDINGS from catalog_cladiri_ortofoto.html")
    buildings_html = {b["id"]: b for b in json.loads(m.group(1))}

    conn = sqlite3.connect(str(gpkg_path))
    cur = conn.cursor()

    layer_map = [
        ("1_ADMIS_FORME_BUNE_2D", "ADMIS"),
        ("2_AJUSTARI_REPARATE_V1_V6", "REPAIRED"),
        ("3_AJUSTARI_TINTA_LOOP_A100", "AJUSTARE_TINTA_A100"),
        ("4_MUTILATE_SI_ELIMINATE_AUDIT", "ELIMINAT"),
    ]

    tiles_manifest: List[Dict[str, Any]] = []
    reprompt_queue: List[Dict[str, Any]] = []

    for tbl_name, cat in layer_map:
        rows = cur.execute(
            f'SELECT building_id, canonical_verdict, geom, v1_to_v6_confidence FROM "{tbl_name}"'
        ).fetchall()
        for bid, canon_v, blob, conf in rows:
            poly = parse_gpkg_geom(blob)
            if poly is None:
                continue
            b_meta = buildings_html.get(bid)
            if not b_meta or not b_meta.get("chip_img"):
                continue
            chip_src = REPO_ROOT / "workspace" / "reviews" / b_meta["chip_img"]
            if not chip_src.is_file():
                continue

            rgb = np.array(Image.open(chip_src).convert("RGB"))
            roof_px = b_meta.get("roof_px", [])

            # If this building was repaired in layer 2, project its repaired world polygon to chip pixels
            if cat == "REPAIRED" and len(roof_px) >= 3:
                orig_bounds = Polygon(
                    [(pt["x"], pt["y"]) for pt in b_meta.get("s70_points", [])]
                ).bounds if len(b_meta.get("s70_points", [])) >= 3 else poly.bounds
                minx, miny, maxx, maxy = orig_bounds
                pts_arr = np.array(roof_px, dtype=np.float64)
                px_min, py_min = pts_arr.min(axis=0)
                px_max, py_max = pts_arr.max(axis=0)
                if (maxx - minx) > 1e-3 and (maxy - miny) > 1e-3:
                    sx = (px_max - px_min) / (maxx - minx)
                    sy = (py_max - py_min) / (maxy - miny)
                    x0 = minx - px_min / sx
                    y0 = maxy + py_min / sy
                    roof_px = [
                        [round((wx - x0) * sx, 1), round((y0 - wy) * sy, 1)]
                        for wx, wy in poly.exterior.coords
                    ]

            r_mask, e_mask, c_mask = build_multitask_masks_for_chip(rgb, roof_px, cat)

            safe_id = bid.replace(":", "_")
            rgb_rel = f"rgb/{safe_id}.png"
            rmask_rel = f"roof_mask/{safe_id}.png"
            emask_rel = f"edge_mask/{safe_id}.png"
            cmask_rel = f"corner_mask/{safe_id}.png"

            Image.fromarray(rgb).save(out_dir / rgb_rel)
            Image.fromarray(r_mask).save(out_dir / rmask_rel)
            Image.fromarray(e_mask * 255).save(out_dir / emask_rel)
            Image.fromarray(c_mask * 255).save(out_dir / cmask_rel)

            minx, miny, maxx, maxy = [round(float(v), 3) for v in poly.bounds]
            # Deterministic spatial split: North/South split in Stereo 70 Y coordinate
            split = "val" if miny > 585650.0 else "train"

            tile_entry = {
                "id": bid,
                "safe_id": safe_id,
                "category": cat,
                "canonical_verdict": canon_v,
                "split": split,
                "crs": "EPSG:3844",
                "bounds_s70": [minx, miny, maxx, maxy],
                "area_m2": round(float(poly.area), 2),
                "v1_to_v6_confidence": round(float(conf), 3),
                "rgb": rgb_rel,
                "roof_mask": rmask_rel,
                "edge_mask": emask_rel,
                "corner_mask": cmask_rel,
                "rgb_sha256": sha256_file(out_dir / rgb_rel),
                "roof_mask_sha256": sha256_file(out_dir / rmask_rel),
                "roof_px": roof_px,
            }
            tiles_manifest.append(tile_entry)

            if cat == "AJUSTARE_TINTA_A100":
                reprompt_queue.append(tile_entry)

    conn.close()

    manifest = {
        "schema_version": "2.0.0-phase1-2d-rgb",
        "phase": "Phase 1 — 2D Cadastral Roof Shape Extraction (RGB-Only, Any Zone/UAT)",
        "crs": "EPSG:3844",
        "input_channels": ["R", "G", "B"],
        "uses_lidar_heights": False,
        "phase2_3d_lod_ready": True,
        "total_tiles": len(tiles_manifest),
        "counts_by_category": {
            "ADMIS": sum(1 for t in tiles_manifest if t["category"] == "ADMIS"),
            "REPAIRED": sum(1 for t in tiles_manifest if t["category"] == "REPAIRED"),
            "AJUSTARE_TINTA_A100": len(reprompt_queue),
            "ELIMINAT_HARD_NEGATIVE": sum(1 for t in tiles_manifest if t["category"] == "ELIMINAT"),
        },
        "a100_reprompt_targets": [t["id"] for t in reprompt_queue],
        "tiles": tiles_manifest,
    }

    manifest_path = out_dir / "manifest_2d_roofs.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gpkg",
        type=Path,
        default=REPO_ROOT / "workspace" / "reviews" / "opera_review_deduplicated_20261029.gpkg",
    )
    parser.add_argument(
        "--html",
        type=Path,
        default=REPO_ROOT / "workspace" / "reviews" / "catalog_cladiri_ortofoto.html",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "workspace" / "colab_2d_roof_dataset",
    )
    args = parser.parse_args(argv)
    manifest = build_dataset(args.gpkg, args.html, args.out_dir)
    print(
        f"[build_2d_roof_dataset] Built {manifest['total_tiles']} tiles in {args.out_dir} "
        f"(CRS={manifest['crs']}, counts={manifest['counts_by_category']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
