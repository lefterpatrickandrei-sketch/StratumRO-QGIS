"""Whole-AOI 2D roof scan: sliding-window inference -> instances -> polygons -> V1..V6 -> metrics.

Every polygon is a PROPOSAL (status PENDING_OWNER_REVIEW). Nothing here sets ADMIS.

    python compute/colab/scripts/scan_roof2d_aoi.py --data workspace/colab_2d_roof_dataset_v3 \
        --ckpt <run>/best.pt --out <run>/scan
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

from roof2d_data import IMAGENET_MEAN, IMAGENET_STD, SPLIT_TRAIN, SPLIT_VAL, rasterize  # noqa: E402

GPKG_REVIEW = REPO_ROOT / "workspace/reviews/opera_review_deduplicated_20261029.gpkg"


def predict_aoi(model, rgb: np.ndarray, device: str, tile: int = 512, overlap: int = 128, batch: int = 8) -> np.ndarray:
    """(3, H, W) float16 sigmoid probabilities with linear-ramp blending and h-flip TTA."""
    import torch

    h, w = rgb.shape[:2]
    step = tile - overlap
    ramp = np.minimum(np.arange(tile) + 1, np.arange(tile)[::-1] + 1).astype(np.float32)
    weight = np.minimum(np.minimum(ramp, overlap)[:, None], np.minimum(ramp, overlap)[None, :])
    acc = np.zeros((3, h, w), dtype=np.float32)
    wsum = np.zeros((h, w), dtype=np.float32)
    origins = [(r, c) for r in range(0, max(h - overlap, 1), step) for c in range(0, max(w - overlap, 1), step)]
    dtype = torch.bfloat16 if device == "cuda" and torch.cuda.is_bf16_supported() else torch.float16
    model.eval()
    todo = []

    def flush():
        x = np.stack([t[2] for t in todo])
        with torch.no_grad(), torch.autocast(device, dtype=dtype, enabled=device == "cuda"):
            xt = torch.from_numpy(x).to(device)
            p = torch.sigmoid(model(xt).float())
            p = 0.5 * (p + torch.flip(torch.sigmoid(model(torch.flip(xt, dims=[3])).float()), dims=[3]))
        p = p.cpu().numpy()
        for (r, c, _), pi in zip(todo, p):
            hh, ww = min(tile, h - r), min(tile, w - c)
            acc[:, r : r + hh, c : c + ww] += pi[:, :hh, :ww] * weight[:hh, :ww]
            wsum[r : r + hh, c : c + ww] += weight[:hh, :ww]
        todo.clear()

    for r, c in origins:
        win = np.zeros((tile, tile, 3), dtype=np.uint8)
        part = rgb[r : r + tile, c : c + tile]
        win[: part.shape[0], : part.shape[1]] = part
        if win.max() == 0:
            continue
        x = ((win.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD).transpose(2, 0, 1)
        todo.append((r, c, x.astype(np.float32)))
        if len(todo) == batch:
            flush()
    if todo:
        flush()
    out = acc / np.maximum(wsum, 1e-6)
    out[:, rgb.max(axis=2) == 0] = 0.0
    return out.astype(np.float16)


def vectorize(roof_p: np.ndarray, edge_p: np.ndarray, transform, thr: float = 0.45, min_area_m2: float = 12.0,
              edge_thr: float = 0.25):
    """Split touching roofs on the outline head, grow seeds back over the roof mask, trace outlines.

    Returns a list of (shapely Polygon in EPSG:3844, mean roof probability).
    """
    import cv2
    from scipy import ndimage
    from shapely.geometry import Polygon

    px_area = abs(transform.a * transform.e)
    roof = roof_p > thr
    comps, _ = ndimage.label(roof)
    out = []
    for sl in ndimage.find_objects(comps):
        if sl is None:
            continue
        sub_roof = roof[sl] & (comps[sl] > 0)
        if sub_roof.sum() * px_area < min_area_m2:
            continue
        seeds, n = ndimage.label(sub_roof & (edge_p[sl] < edge_thr))
        if n > 1:
            sizes = ndimage.sum(np.ones_like(seeds), seeds, index=np.arange(1, n + 1))
            for k, s in enumerate(sizes, start=1):
                if s * px_area < 2.0:
                    seeds[seeds == k] = 0
            _, (ri, ci) = ndimage.distance_transform_edt(seeds == 0, return_indices=True)
            inst = np.where(sub_roof, seeds[ri, ci], 0)
        else:
            inst = sub_roof.astype(np.int32)
        r0, c0 = sl[0].start, sl[1].start
        for k in np.unique(inst[inst > 0]):
            m = (inst == k).astype(np.uint8)
            if m.sum() * px_area < min_area_m2:
                continue
            contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnt = max(contours, key=cv2.contourArea)
            if len(cnt) < 3:
                continue
            pts = [transform * (c0 + float(x) + 0.5, r0 + float(y) + 0.5) for x, y in cnt[:, 0, :]]
            poly = Polygon(pts).buffer(0)
            if poly.geom_type != "Polygon":
                poly = max(poly.geoms, key=lambda g: g.area)
            if poly.area >= min_area_m2:
                out.append((poly, float(roof_p[sl][m.astype(bool)].mean())))
    return out


def snap_rectilinear(poly, simplify_m: float = 0.5):
    """Strict 90-degree outline in the polygon's dominant (MRR) frame, or None.

    Each simplified edge is classed horizontal / vertical in the rotated frame; runs of one class merge into
    a single line at their length-weighted mean offset; consecutive lines intersect into the new corners.
    Used when orthogonalize_cad keeps a model blob on its curved-shape branch.
    """
    import math

    from shapely.affinity import rotate
    from shapely.geometry import Polygon

    mrr = np.asarray(poly.minimum_rotated_rectangle.exterior.coords)
    d = mrr[1] - mrr[0]
    ang = math.degrees(math.atan2(d[1], d[0]))
    c = poly.centroid
    rp = rotate(poly, -ang, origin=c).simplify(simplify_m, preserve_topology=True)
    if rp.geom_type != "Polygon" or rp.is_empty:
        return None
    pts = np.asarray(rp.exterior.coords)[:-1]
    lines = []  # (cls, offset, weight); cls 0 = horizontal (y const), 1 = vertical (x const)
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        dx, dy = b - a
        length = math.hypot(dx, dy)
        if length < 1e-6:
            continue
        cls = 0 if abs(dx) >= abs(dy) else 1
        off = (a[1] + b[1]) / 2 if cls == 0 else (a[0] + b[0]) / 2
        if lines and lines[-1][0] == cls:
            pc, po, pw = lines[-1]
            lines[-1] = (cls, (po * pw + off * length) / (pw + length), pw + length)
        else:
            lines.append((cls, off, length))
    def merge_same_class(ls):
        out = []
        for cls, off, w in ls:
            if out and out[-1][0] == cls:
                pc, po, pw = out[-1]
                out[-1] = (cls, (po * pw + off * w) / (pw + w), pw + w)
            else:
                out.append((cls, off, w))
        if len(out) > 1 and out[0][0] == out[-1][0]:
            (c0, o0, w0), (c1, o1, w1) = out[0], out.pop()
            out[0] = (c0, (o0 * w0 + o1 * w1) / (w0 + w1), w0 + w1)
        return out

    lines = merge_same_class(lines)
    while len(lines) % 2 and len(lines) > 4:  # a diagonal run left an odd cycle: drop the shortest line
        lines.pop(int(np.argmin([w for _, _, w in lines])))
        lines = merge_same_class(lines)
    if len(lines) < 4 or len(lines) % 2:
        return None
    corners = []
    for i in range(len(lines)):
        l1, l2 = lines[i], lines[(i + 1) % len(lines)]
        corners.append((l2[1], l1[1]) if l1[0] == 0 else (l1[1], l2[1]))
    out = Polygon(corners)
    if not out.is_valid or out.is_empty:
        return None
    return rotate(out, ang, origin=c)


def regularize(poly):
    """simplify(0.6 m) -> orthogonalize_cad; jagged results try snap_rectilinear, then the MRR."""
    from shapely.geometry import Polygon

    from stratum_ro.core.geometry.regularizer import compute_orthogonality_ratio, orthogonalize_cad

    simple = poly.simplify(0.6, preserve_topology=True)
    if not simple.is_valid or simple.is_empty:
        simple = poly
    reg = orthogonalize_cad(simple)
    if reg is None or reg.is_empty or not reg.is_valid or not isinstance(reg, Polygon):
        reg = simple
    reg = Polygon(reg.exterior.coords)
    if compute_orthogonality_ratio(reg) < 0.95 or len(reg.exterior.coords) - 1 > 16:
        rect = snap_rectilinear(poly)
        if rect is not None and len(rect.exterior.coords) - 1 <= 16 and \
                poly.intersection(rect).area / max(poly.union(rect).area, 1e-6) >= 0.80:
            return Polygon(rect.exterior.coords)
        mrr = poly.minimum_rotated_rectangle
        if poly.intersection(mrr).area / max(poly.union(mrr).area, 1e-6) >= 0.75:
            return Polygon(mrr.exterior.coords)
        for simp in (1.0, 1.5):  # coarser squaring before giving up on a jagged blob
            rect = snap_rectilinear(poly, simplify_m=simp)
            if rect is not None and len(rect.exterior.coords) - 1 <= 12 and \
                    poly.intersection(rect).area / max(poly.union(rect).area, 1e-6) >= 0.60:
                return Polygon(rect.exterior.coords)
    return reg


def resolve_overlaps(items, min_keep: float = 0.5, min_area_m2: float = 12.0):
    """Planar partition: walk proposals by descending probability, clip each by the ones already kept.

    ``items`` is a list of (polygon, prob). A proposal that keeps less than ``min_keep`` of its area (or less
    than ``min_area_m2``) is dropped as a double vectorization. Returns (kept [(poly, prob, clipped)], dropped).
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    order = sorted(range(len(items)), key=lambda k: -items[k][1])
    tree = STRtree([g for g, _ in items]) if items else None
    kept, dropped, kept_geoms = [], 0, {}
    for k in order:
        g, prob = items[k]
        near = [kept_geoms[j] for j in (tree.query(g) if tree else []) if j in kept_geoms]
        clipped = False
        if near:
            blocker = unary_union(near)
            if g.intersection(blocker).area > 0.05:
                rest = g.difference(blocker.buffer(0.02))
                if rest.geom_type != "Polygon":
                    rest = max(getattr(rest, "geoms", [Polygon()]), key=lambda x: x.area)
                if rest.is_empty or rest.area < max(min_area_m2, min_keep * g.area):
                    dropped += 1
                    continue
                g, clipped = Polygon(rest.exterior.coords).simplify(0.05), True
                reg = regularize(g)  # re-square the cut, unless that re-enters the stronger neighbour
                if reg.is_valid and reg.intersection(blocker).area < 0.25:
                    g = reg
        kept_geoms[k] = g
        kept.append((g, prob, clipped))
    return kept, dropped


def chip_for(poly, rgb: np.ndarray, transform, margin_m: float = 6.0):
    """RGB chip around a polygon, polygon in chip pixels, chip extent (minx, miny, maxx, maxy) and chip transform."""
    from rasterio.transform import Affine

    minx, miny, maxx, maxy = poly.buffer(margin_m).bounds
    inv = ~transform
    c0, r0 = inv * (minx, maxy)
    c1, r1 = inv * (maxx, miny)
    h, w = rgb.shape[:2]
    c0, r0 = max(int(np.floor(c0)), 0), max(int(np.floor(r0)), 0)
    c1, r1 = min(int(np.ceil(c1)), w), min(int(np.ceil(r1)), h)
    chip = rgb[r0:r1, c0:c1]
    px = [[(inv * xy)[0] - c0, (inv * xy)[1] - r0] for xy in poly.exterior.coords]
    ext_minx, ext_maxy = transform * (c0, r0)
    ext_maxx, ext_miny = transform * (c1, r1)
    return chip, px, [ext_minx, ext_miny, ext_maxx, ext_maxy], transform * Affine.translation(c0, r0)


def angle_stats(polys) -> dict:
    """Share of vertices whose interior angle is within 5 deg of 90/45/135/270 multiples of 45."""
    good = total = 0
    for p in polys:
        c = np.asarray(p.exterior.coords)[:-1]
        n = len(c)
        for i in range(n):
            v1, v2 = c[i] - c[i - 1], c[(i + 1) % n] - c[i]
            l1, l2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if l1 < 1e-6 or l2 < 1e-6:
                continue
            turn = np.degrees(np.arccos(np.clip(np.dot(v1, v2) / (l1 * l2), -1, 1)))
            total += 1
            good += int(min(abs(turn - 45), abs(turn - 90)) <= 5.0)
    return {"vertices": total, "ortho_45_90_share": round(good / max(total, 1), 4)}


def iou_against(ref, preds, tree):
    """IoU of ``ref`` with the union of predictions that mostly lie on it."""
    from shapely.ops import unary_union

    hits = [preds[i] for i in tree.query(ref) if preds[i].intersection(ref).area > 0.3 * min(preds[i].area, ref.area)]
    if not hits:
        return 0.0, None
    u = unary_union(hits)
    return float(u.intersection(ref).area / max(u.union(ref).area, 1e-6)), hits


def scan(data_dir: Path, ckpt: Path | None, out: Path, thr: float = 0.45, pseudo_min_prob: float = 0.75,
         probs_path: Path | None = None, edge_thr: float = 0.25) -> dict:
    import geopandas as gpd
    import rasterio
    import torch
    from shapely.strtree import STRtree

    from stratum_ro.core.qa_qc.simultaneous_2d_validator import evaluate_building_simultaneously
    from train_roof2d import build_model

    out.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    with rasterio.open(data_dir / "aoi_rgb.tif") as src:
        rgb = np.moveaxis(src.read(), 0, -1)
        transform, profile = src.transform, src.profile
    split = rasterio.open(data_dir / "split.tif").read(1)
    if probs_path is not None:  # re-vectorize a saved probability raster, no GPU needed
        with rasterio.open(probs_path) as src:
            probs = src.read().astype(np.float32) / 255.0
    else:
        state = torch.load(ckpt, map_location=device)
        model = build_model(pretrained=False, arch=state.get("arch", "resnet34")).to(device)
        model.load_state_dict(state["model"])
        probs = predict_aoi(model, rgb, device)
        prof1 = {**profile, "count": 3, "dtype": "uint8"}
        with rasterio.open(out / "probs_roof_edge_corner.tif", "w", **prof1) as dst:
            dst.write((probs.astype(np.float32) * 255).round().astype(np.uint8))

    owner_roof = rasterio.open(data_dir / "label_roof.tif").read(1)
    painted = probs[0] > thr
    fp_known = float((painted & (owner_roof == 0)).sum() / max(painted.sum(), 1))
    roof_share = float(painted.mean())
    raw = vectorize(probs[0].astype(np.float32), probs[1].astype(np.float32), transform, thr, edge_thr=edge_thr)
    resolved, n_dropped = resolve_overlaps([(regularize(p), prob) for p, prob in raw])
    records = []
    for i, (poly, prob, clipped) in enumerate(resolved):
        poly_raw = poly
        chip, px, ext, chip_t = chip_for(poly, rgb, transform)
        touches = bool((rasterize([poly.buffer(1.0)], chip_t, chip.shape[:2], all_touched=True) & (chip.max(axis=2) == 0)).any())
        rep = evaluate_building_simultaneously(
            building_id=f"R2D_{i:05d}", raw_verdict="AJUSTARE_CONTUR", rgb=chip, roof_px=px, poly_s70=poly,
            bounds_s70=ext, touches_nodata_flag=int(touches), auto_repair=True,
        )
        final = rep.repaired_polygon_s70 or poly
        records.append({"id": f"R2D_{i:05d}", "poly_raw": poly_raw, "geometry": final, "mean_prob": prob, "rep": rep,
                        "repaired": rep.repaired_polygon_s70 is not None, "clipped": clipped})

    # V1..V6 auto-repairs (MRR corner completion) may re-grow into a stronger neighbour: undo those repairs
    rtree = STRtree([r["geometry"] for r in records]) if records else None
    for k in sorted(range(len(records)), key=lambda k: -records[k]["mean_prob"]):
        r = records[k]
        if r["repaired"] and any(j != k and records[j]["mean_prob"] >= r["mean_prob"]
                                 and r["geometry"].intersection(records[j]["geometry"]).area >= 0.25
                                 for j in rtree.query(r["geometry"])):
            r["geometry"], r["repaired"] = r["poly_raw"], False

    # V6: planar overlap against higher-probability proposals
    order = sorted(range(len(records)), key=lambda k: -records[k]["mean_prob"])
    rank_of = {k: rank for rank, k in enumerate(order)}
    geoms = [r["geometry"] for r in records]
    tree = STRtree(geoms) if geoms else None
    for rank, k in enumerate(order):
        g = geoms[k]
        stronger = [j for j in (tree.query(g) if tree else []) if j != k and rank_of[j] < rank]
        ov = sum(g.intersection(geoms[j]).area for j in stronger)
        records[k]["v6_overlap_m2"] = round(float(ov), 2)
        records[k]["v6_pass"] = ov < 0.25
    for r in records:
        r["all_six"] = bool(r["rep"].all_six_passed and r["v6_pass"])
        c = r["geometry"].centroid
        row = int((~transform * (c.x, c.y))[1])
        r["split"] = {SPLIT_TRAIN: "train", SPLIT_VAL: "val"}.get(int(split[min(max(row, 0), split.shape[0] - 1), 0]), "buffer")

    layers = {k: gpd.read_file(GPKG_REVIEW, layer=v).to_crs("EPSG:3844") for k, v in {
        "admis": "1_ADMIS_FORME_BUNE_2D", "repaired": "2_AJUSTARI_REPARATE_V1_V6",
        "target": "3_AJUSTARI_TINTA_LOOP_A100", "negative": "4_MUTILATE_SI_ELIMINATE_AUDIT"}.items()}
    preds = [r["geometry"] for r in records]
    ptree = STRtree(preds)

    vmin = json.loads((data_dir / "manifest.json").read_text())["split"]["val_min_y"]

    def split_of(g):
        y = g.centroid.y
        return "val" if y >= vmin + 15 else ("train" if y <= vmin - 15 else "buffer")

    admis_rows = []
    for _, a in layers["admis"].iterrows():
        iou, _ = iou_against(a.geometry, preds, ptree)
        admis_rows.append({"building_id": a.building_id, "split": split_of(a.geometry), "iou": round(iou, 4)})

    target_rows = []
    for _, t in layers["target"].iterrows():
        cand = [k for k in ptree.query(t.geometry) if preds[k].intersection(t.geometry).area > 0]
        best = max(cand, key=lambda k: preds[k].intersection(t.geometry).area, default=None)
        target_rows.append({
            "building_id": t.building_id, "split": split_of(t.geometry),
            "match": records[best]["id"] if best is not None else None,
            "all_six": bool(records[best]["all_six"]) if best is not None else False,
            "iou_with_before": round(preds[best].intersection(t.geometry).area / preds[best].union(t.geometry).area, 4) if best is not None else 0.0,
            "area_before_m2": round(t.geometry.area, 1), "area_after_m2": round(preds[best].area, 1) if best is not None else 0.0,
            "summary": " | ".join(f"{k[:2]}={'OK' if g.passed else 'X'}" for k, g in records[best]["rep"].gates.items()) if best is not None else "NOT_DETECTED",
        })
    fp_neg = sum(1 for _, n in layers["negative"].iterrows()
                 if any(preds[k].intersection(n.geometry).area > 0.3 * n.geometry.area for k in ptree.query(n.geometry)))
    known = list(layers["admis"].geometry) + list(layers["repaired"].geometry) + list(layers["target"].geometry) + list(layers["negative"].geometry)
    ktree = STRtree(known)
    for r in records:
        r["is_new"] = not any(known[k].intersection(r["geometry"]).area > 0.2 * r["geometry"].area for k in ktree.query(r["geometry"]))

    def summarize(rows, split_name):
        v = [x["iou"] for x in rows if x["split"] == split_name]
        return {"n": len(v), "mean_iou": round(float(np.mean(v)), 4) if v else None,
                "median_iou": round(float(np.median(v)), 4) if v else None,
                "share_iou_ge_0_90": round(float(np.mean(np.array(v) >= 0.9)), 4) if v else None,
                "detected_iou_ge_0_50": round(float(np.mean(np.array(v) >= 0.5)), 4) if v else None}

    metrics = {
        "status": "PROPOSAL_PENDING_OWNER_REVIEW",
        "params": {"roof_thr": thr, "edge_thr": edge_thr, "probs_from_file": str(probs_path) if probs_path else None},
        "proposals": len(records),
        "roof_pixel_share_of_aoi": round(roof_share, 4),
        "roof_pixels_on_known_background": round(fp_known, 4),
        "dropped_double_vectorizations": n_dropped,
        "clipped_by_stronger_neighbour": sum(r["clipped"] for r in records),
        "all_six_passed": sum(r["all_six"] for r in records),
        "gate_pass_rates": {g: round(float(np.mean([r["rep"].gates[g].passed for r in records])), 4)
                            for g in (records[0]["rep"].gates if records else {})},
        "v6_overlapping_proposals": sum(not r["v6_pass"] for r in records),
        "v5_nodata_touching_proposals": sum(r["rep"].gates["V5_ANTI_ARTIFACT_NODATA"].details.get("touches_nodata_flag", 0) for r in records),
        "angles": angle_stats([r["geometry"] for r in records]),
        "admis_iou_val": summarize(admis_rows, "val"),
        "admis_iou_train_seen": summarize(admis_rows, "train"),
        "targets_detected": sum(t["match"] is not None for t in target_rows),
        "targets_all_six": sum(t["all_six"] for t in target_rows),
        "hard_negatives_hit": fp_neg,
        "new_proposals_not_in_review": sum(r["is_new"] for r in records),
        "new_proposals_all_six": sum(r["is_new"] and r["all_six"] for r in records),
    }

    rows = [{
        "proposal_id": r["id"], "status": "PENDING_OWNER_REVIEW", "split": r["split"],
        "mean_roof_prob": round(r["mean_prob"], 4), "all_six_passed": int(r["all_six"]),
        "v1_to_v6_confidence": round(r["rep"].composite_confidence, 4), "auto_repaired": int(r["repaired"]),
        "v6_overlap_m2": r["v6_overlap_m2"], "is_new_vs_review": int(r["is_new"]),
        "nodes": len(r["geometry"].exterior.coords) - 1, "area_m2": round(r["geometry"].area, 2),
        "audit_summary": " | ".join(f"{k}={'OK' if g.passed else 'FAIL'}({g.score:.2f})" for k, g in r["rep"].gates.items()),
        "geometry": r["geometry"],
    } for r in records]
    gdf = (gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3844") if rows
           else gpd.GeoDataFrame({"proposal_id": []}, geometry=gpd.GeoSeries([], crs="EPSG:3844")))
    gpkg = out / "roof2d_proposals_epsg3844.gpkg"
    if gpkg.exists():
        gpkg.unlink()
    gdf.to_file(gpkg, layer="proposals_all", driver="GPKG")
    if len(gdf):
        gdf[gdf.all_six_passed == 1].to_file(gpkg, layer="proposals_v1_v6_passed", driver="GPKG")
        gdf[gdf.is_new_vs_review == 1].to_file(gpkg, layer="proposals_new_vs_review", driver="GPKG")

    pseudo = [r["geometry"] for r in records if r["all_six"] and r["mean_prob"] >= pseudo_min_prob]
    with rasterio.open(out / "pseudo_roofs.tif", "w", **{**profile, "count": 1, "dtype": "uint8"}) as dst:
        dst.write(rasterize(pseudo, transform, rgb.shape[:2]).astype(np.uint8)[None])
    metrics["pseudo_roofs"] = len(pseudo)

    (out / "scan_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (out / "targets_before_after.json").write_text(json.dumps(target_rows, indent=2), encoding="utf-8")
    (out / "admis_iou.json").write_text(json.dumps(admis_rows, indent=2), encoding="utf-8")
    render_target_sheet(rgb, transform, layers["target"], {r["id"]: r for r in records}, target_rows, out / "sheet_targets_before_after.jpg")
    return metrics


def render_target_sheet(rgb, transform, targets, by_id, target_rows, path: Path, cell: int = 300, cols: int = 6):
    """Contact sheet: before (red, owner AJUSTARE polygon) vs after (green, loop proposal)."""
    import cv2

    cells = []
    for (_, t), row in zip(targets.iterrows(), target_rows):
        chip, px_before, _, _ = chip_for(t.geometry, rgb, transform, margin_m=8.0)
        img = cv2.cvtColor(np.ascontiguousarray(chip), cv2.COLOR_RGB2BGR)
        cv2.polylines(img, [np.round(px_before).astype(np.int32)], True, (0, 0, 255), 2)
        if row["match"]:
            g = by_id[row["match"]]["geometry"]
            inv = ~transform
            minx, _, _, maxy = t.geometry.buffer(8.0).bounds
            c0, r0 = inv * (minx, maxy)
            c0, r0 = max(int(np.floor(c0)), 0), max(int(np.floor(r0)), 0)
            pa = np.array([[(inv * xy)[0] - c0, (inv * xy)[1] - r0] for xy in g.exterior.coords])
            cv2.polylines(img, [np.round(pa).astype(np.int32)], True, (0, 255, 0), 2)
        s = cell / max(img.shape[:2])
        img = cv2.resize(img, (max(1, int(img.shape[1] * s)), max(1, int(img.shape[0] * s))))
        canvas = np.full((cell + 34, cell, 3), 255, np.uint8)
        canvas[: img.shape[0], : img.shape[1]] = img
        color = (0, 140, 0) if row["all_six"] else (0, 0, 200)
        cv2.putText(canvas, row["building_id"], (4, cell + 13), cv2.FONT_HERSHEY_SIMPLEX, 0.42, color, 1)
        cv2.putText(canvas, f"IoU0={row['iou_with_before']:.2f} {'V1-6 OK' if row['all_six'] else row['summary'][:34]}",
                    (4, cell + 29), cv2.FONT_HERSHEY_SIMPLEX, 0.34, color, 1)
        cells.append(canvas)
    if not cells:
        return
    while len(cells) % cols:
        cells.append(np.full_like(cells[0], 255))
    grid = np.vstack([np.hstack(cells[i : i + cols]) for i in range(0, len(cells), cols)])
    cv2.imwrite(str(path), grid, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--ckpt", type=Path)
    ap.add_argument("--probs", type=Path, help="saved probs_roof_edge_corner.tif instead of running the model")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--thr", type=float, default=0.45)
    ap.add_argument("--edge-thr", type=float, default=0.25)
    args = ap.parse_args(argv)
    if not args.ckpt and not args.probs:
        ap.error("--ckpt or --probs is required")
    print(json.dumps(scan(args.data, args.ckpt, args.out, args.thr, probs_path=args.probs, edge_thr=args.edge_thr), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
