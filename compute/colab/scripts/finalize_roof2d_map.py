"""One clean 2D building layer for the whole AOI, built from the owner review plus the loop proposals.

Each step answers one root cause found by audit_roof2d_map.py on 2026-10-31 (see docs/LOOP_FINAL_2D_*.md):
  E1 unify            owner ADMIS geometry wins; a proposal that duplicates it is dropped, a partial one clipped.
                      Owner AJUSTARE targets are replaced by their best proposal (IoU >= 0.3) or kept as INCERT.
  E3 false positives  image evidence only (VLM, vegetation, NoData strip, model probability); LiDAR may confirm
                      a building but never rejects one (new houses are missing from the older LiDAR).
  E4 tree occlusion   a notch of the oriented rectangle, or a strip beyond an edge, is added when it is covered by
                      foliage AND LiDAR shows roof height there (|h - roof| <= 1.5 m); courtyards are ground, so
                      real L/U/T shapes stay.
  E5 fragments        a small piece (< 30 m2) touching a building at the same LiDAR roof height joins it.
  E2 topology         zero-overlap planar partition, priority owner > ADMIS_PROPUS > INCERT.
  E6 roof type        LiDAR profile (flat / shed / gable / hip, R2 of plane models on the 1 m nDSM) where LiDAR
                      covers the roof, the VLM label elsewhere; tip_sursa says which.
Owner ADMIS outlines only get edge snapping up to 0.45 m (flag geom_ajustata_agent); owner_verdict is copied.

    python compute/colab/scripts/finalize_roof2d_map.py --out workspace/reviews/cladiri_2d_final_rN_epsg3844.gpkg
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from build_consensus_labels import foliage  # noqa: E402
from roof2d_data import rasterize  # noqa: E402
from scan_roof2d_aoi import angle_stats, regularize, snap_rectilinear  # noqa: E402
from vlm_merge_finish import ROOF_RO, ndsm_attrs, snap_edges  # noqa: E402

REVIEW = REPO_ROOT / "workspace/reviews/opera_review_deduplicated_20261029.gpkg"
PRIORITY = {"ADMIS": 3, "ADMIS_PROPUS": 2, "INCERT": 1}


# ----------------------------------------------------------------------------------------------- rasters
class Grids:
    """Orthophoto, vegetation mask and nDSM resampled to the 0.15 m grid (NaN = no LiDAR)."""

    def __init__(self, data: Path, ndsm_path: Path, probs: Path | None):
        import rasterio
        from rasterio.warp import Resampling, reproject

        with rasterio.open(data / "aoi_rgb.tif") as src:
            self.rgb, self.t = np.moveaxis(src.read(), 0, -1), src.transform
        self.shape = self.rgb.shape[:2]
        self.veg = foliage(self.rgb)
        self.nodata = self.rgb.max(axis=2) == 0
        self.h = np.full(self.shape, np.nan, dtype=np.float32)
        with rasterio.open(ndsm_path) as src:
            reproject(src.read(1).astype(np.float32), self.h, src_transform=src.transform, src_crs=src.crs,
                      dst_transform=self.t, dst_crs="EPSG:3844", resampling=Resampling.nearest, dst_nodata=np.nan)
            self.ndsm, self.ndsm_t = src.read(1).astype(np.float32), src.transform
        # LiDAR roughness (3x3 std on the 1 m nDSM): roofs are planar (owner roofs median 0.46 m), crowns are not
        # (tree polygons median 1.01 m); separates a hidden roof from a crown of the same height
        import cv2

        mu = cv2.blur(self.ndsm, (3, 3))
        rough = np.sqrt(np.maximum(cv2.blur(self.ndsm * self.ndsm, (3, 3)) - mu * mu, 0.0)).astype(np.float32)
        self.rough = np.full(self.shape, np.nan, dtype=np.float32)
        reproject(rough, self.rough, src_transform=self.ndsm_t, src_crs="EPSG:3844", dst_transform=self.t,
                  dst_crs="EPSG:3844", resampling=Resampling.nearest, dst_nodata=np.nan)
        self.edge = self.roof = None
        if probs is not None:
            with rasterio.open(probs) as src:
                self.roof = src.read(1).astype(np.float32) / 255.0
                self.edge = src.read(2).astype(np.float32) / 255.0

    def mask(self, geom):
        """(boolean mask, window slices) for a geometry on the 0.15 m grid."""
        from rasterio.transform import Affine

        minx, miny, maxx, maxy = geom.bounds
        c0, r0 = ~self.t * (minx, maxy)
        c1, r1 = ~self.t * (maxx, miny)
        c0, r0 = max(int(math.floor(c0)), 0), max(int(math.floor(r0)), 0)
        c1, r1 = min(int(math.ceil(c1)) + 1, self.shape[1]), min(int(math.ceil(r1)) + 1, self.shape[0])
        if c1 <= c0 or r1 <= r0:
            return np.zeros((0, 0), bool), (slice(0, 0), slice(0, 0))
        win = (slice(r0, r1), slice(c0, c1))
        return rasterize([geom], self.t * Affine.translation(c0, r0), (r1 - r0, c1 - c0)), win

    def frac(self, layer, geom) -> float:
        m, w = self.mask(geom)
        return float(layer[w][m].mean()) if m.any() else 0.0

    def heights(self, geom) -> np.ndarray:
        m, w = self.mask(geom)
        v = self.h[w][m]
        return v[np.isfinite(v)]

    def smooth(self, geom) -> bool:
        """LiDAR surface under geom is planar like a roof (median 3x3 std < 0.8 m)."""
        m, w = self.mask(geom)
        v = self.rough[w][m]
        v = v[np.isfinite(v)]
        return v.size >= 5 and float(np.median(v)) < 0.8


# ----------------------------------------------------------------------------------------------- E4
def roof_height(g: Grids, poly) -> float | None:
    v = g.heights(poly.buffer(-0.5) if not poly.buffer(-0.5).is_empty else poly)
    v = v[v >= 2.0]
    return float(np.median(v)) if v.size >= 20 else None


def occluded_ok(g: Grids, region, roof_h: float, others, small_corner: bool = False) -> bool:
    """Region hidden by a crown with a roof plausibly underneath, and not another building.

    Tier A: LiDAR shows roof height there (|h - roof| <= 1.5 m on >= 40 %).
    Tier B (small_corner only): the crown is taller than the roof, so LiDAR hits leaves, not tiles; accepted only
    for a corner bite <= 12 % of the oriented rectangle, because a real L/U courtyard is larger and is ground.
    """
    if region.is_empty or region.area < 1.0 or any(region.intersection(o).area > 0.1 * region.area for o in others):
        return False
    v = g.heights(region)
    if v.size < 10:
        return False
    veg, elevated = g.frac(g.veg, region), float((v >= 2.0).mean())
    if veg >= 0.5 and elevated >= 0.7 and float((np.abs(v - roof_h) <= 1.5).mean()) >= 0.4 and g.smooth(region):
        return True
    return small_corner and veg >= 0.6 and elevated >= 0.8 and float(np.median(v)) >= roof_h + 1.0


def complete_occluded(g: Grids, poly, others, max_extend_m: float = 5.0):
    """Fill crown-covered notches of the oriented rectangle and extend edges under crowns (step 0.5 m).

    Returns (polygon, added m2). Without LiDAR roof height nothing is added (no evidence, no corner).
    """
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    roof_h = roof_height(g, poly)
    if roof_h is None:
        return poly, 0.0
    parts = [poly]
    mrr = poly.minimum_rotated_rectangle
    notch = mrr.difference(poly)
    for n in getattr(notch, "geoms", [notch]):
        if occluded_ok(g, n, roof_h, others, small_corner=n.area <= 0.12 * mrr.area):
            parts.append(n)
    cur = unary_union(parts)
    cur = cur if cur.geom_type == "Polygon" else max(cur.geoms, key=lambda x: x.area)
    box = np.asarray(cur.minimum_rotated_rectangle.exterior.coords)[:-1]
    for i in range(4):  # strips beyond each side of the rectangle
        a, b = box[i], box[(i + 1) % 4]
        d = b - a
        length = float(np.hypot(*d))
        if length < 2.0:
            continue
        centre = box.mean(axis=0)
        normal = np.array([d[1], -d[0]]) / length
        if np.dot((a + b) / 2 - centre, normal) < 0:
            normal = -normal
        grown = 0.0
        while grown < max_extend_m:
            strip = Polygon([a + normal * grown, b + normal * grown, b + normal * (grown + 0.5), a + normal * (grown + 0.5)])
            if not occluded_ok(g, strip, roof_h, others):
                break
            grown += 0.5
        if grown > 0:
            parts.append(Polygon([a, b, b + normal * grown, a + normal * grown]))
    out = unary_union(parts)
    out = out if out.geom_type == "Polygon" else max(out.geoms, key=lambda x: x.area)
    added = out.area - poly.area
    if added < 1.0:
        return poly, 0.0
    sq = snap_rectilinear(out) or regularize(out)
    sq = sq if sq is not None and sq.is_valid else out
    return Polygon(sq.exterior.coords), round(added, 2)


def dominant_angle(poly) -> float:
    """Building orientation (deg, mod 90) from the length-weighted histogram of its edge directions."""
    c = np.asarray(poly.exterior.coords)
    d = np.diff(c, axis=0)
    lengths = np.hypot(d[:, 0], d[:, 1])
    ang = np.degrees(np.arctan2(d[:, 1], d[:, 0])) % 90.0
    hist = np.zeros(90)
    for a, w in zip(ang, lengths):
        for k in range(-2, 3):  # +-2 deg smoothing
            hist[int(round(a + k)) % 90] += w
    return float(np.argmax(hist))


def rectilinear_from_evidence(g: Grids, poly, others, cell: float = 0.25, close_m: float = 1.0):
    """Manhattan outline rebuilt from image evidence in the building frame (E4 + overshoot + diagonals).

    Cells = visible roof (ensemble roof probability >= 0.5) near the proposal, plus tall-crown cells
    (vegetation and nDSM >= 2.5 m) that touch the roof and lie inside the visible roof's extent in the building
    frame: hidden corners are filled, the outline cannot run off under a park. Closing/opening by 1 m removes
    steps shorter than the ANCPI 1 m edge; tracing pixel borders gives exact 90-degree edges.
    Returns (polygon, added m2 under crowns) or (poly, 0.0) when the evidence disagrees with the proposal.
    """
    from rasterio.features import shapes
    from rasterio.transform import Affine
    from scipy import ndimage
    from shapely import contains_xy
    from shapely.affinity import rotate
    from shapely.geometry import Polygon, shape

    if g.roof is None:
        return poly, 0.0
    theta = dominant_angle(poly)
    c = poly.centroid
    rp = rotate(poly, -theta, origin=c)
    minx, miny, maxx, maxy = rp.buffer(3.0).bounds
    ncol, nrow = int(math.ceil((maxx - minx) / cell)), int(math.ceil((maxy - miny) / cell))
    gt = Affine(cell, 0, minx, 0, -cell, maxy)  # rotated-frame grid
    cols, rows = np.meshgrid(np.arange(ncol) + 0.5, np.arange(nrow) + 0.5)
    fx, fy = minx + cols * cell, maxy - rows * cell
    t = math.radians(theta)
    wx = c.x + (fx - c.x) * math.cos(t) - (fy - c.y) * math.sin(t)  # back to the world frame
    wy = c.y + (fx - c.x) * math.sin(t) + (fy - c.y) * math.cos(t)
    pc, pr = ~g.t * (wx, wy)
    pr, pc = np.clip(pr.astype(int), 0, g.shape[0] - 1), np.clip(pc.astype(int), 0, g.shape[1] - 1)
    roof = g.roof[pr, pc] >= 0.5
    crown = g.veg[pr, pc] & (np.nan_to_num(g.h[pr, pc]) >= 2.5)
    near = contains_xy(poly.buffer(1.5), wx, wy)
    blocked = np.zeros_like(near)
    for o in others:
        blocked |= contains_xy(o, wx, wy)
    seed = roof & near & ~blocked
    lab, n = ndimage.label(seed)
    if n == 0:
        return poly, 0.0
    inside = contains_xy(poly, wx, wy)
    k = int(np.argmax(ndimage.sum(inside, lab, index=np.arange(1, n + 1)))) + 1
    body = lab == k
    rr, cc = np.nonzero(body)
    box = np.zeros_like(body)
    box[rr.min() : rr.max() + 1, cc.min() : cc.max() + 1] = True
    crown_ok = crown & box & ~blocked
    clab, _ = ndimage.label(crown_ok)
    touching = np.unique(clab[ndimage.binary_dilation(body, iterations=2) & (clab > 0)])
    # each crown patch is judged on its own (R2: between the wings of an L/T building the frame box holds
    # courtyard trees): tier A LiDAR at roof height, tier B small bite under a taller crown
    hb = np.nan_to_num(g.h[pr, pc])
    roof_h = float(np.median(hb[body & (hb >= 2.0)])) if (body & (hb >= 2.0)).sum() >= 20 else None
    keep_ids = []
    # tier B only for simple buildings (<= 8 vertices) and capped at 12 % of the visible roof in total: dozens of
    # small crown patches around a large complex are courtyards and gardens, not one hidden corner (R2D_00177).
    # (A convex-hull test was tried and rejected: it covers only half of a bitten rectangle corner.)
    simple = len(poly.exterior.coords) - 1 <= 8
    budget_b = 0.12 * body.sum()
    for k_id in touching[touching > 0]:
        patch = clab == k_id
        if roof_h is None:
            break
        hp = hb[patch]
        rp = g.rough[pr, pc][patch]
        rp = rp[np.isfinite(rp)]
        tier_a = float((np.abs(hp - roof_h) <= 1.5).mean()) >= 0.4 and rp.size >= 5 and float(np.median(rp)) < 0.8
        tier_b = simple and patch.sum() <= budget_b and float(np.median(hp)) >= roof_h + 1.0
        if tier_a and patch.sum() <= 0.25 * body.sum():
            keep_ids.append(k_id)
        elif tier_b:
            keep_ids.append(k_id)
            budget_b -= patch.sum()
    filled = body | np.isin(clab, keep_ids)
    s = max(1, int(round(close_m / cell)))
    st = np.ones((s, s), bool)
    filled = ndimage.binary_opening(ndimage.binary_closing(filled, st), st)
    filled = ndimage.binary_fill_holes(filled)
    lab2, n2 = ndimage.label(filled)
    if n2 == 0:
        return poly, 0.0
    big = lab2 == (int(np.argmax(ndimage.sum(filled, lab2, index=np.arange(1, n2 + 1)))) + 1)
    parts = [shape(geom) for geom, v in shapes(big.astype(np.uint8), mask=big, transform=gt) if v == 1]
    if not parts:
        return poly, 0.0
    out = max(parts, key=lambda q: q.area)
    out = Polygon(out.exterior.coords).simplify(0.01)
    # a blob edge that is not parallel to the frame traces as a 0.25 m staircase; merge it into H/V lines
    for simp in (0.5, 0.75, 1.0):
        sq = snap_rectilinear(out, simplify_m=simp)
        if sq is not None and sq.is_valid and sq.intersection(out).area / max(sq.union(out).area, 1e-6) >= 0.9:
            out = Polygon(sq.exterior.coords)
            break
    else:
        return poly, 0.0
    out = rotate(out, theta, origin=c)
    if not out.is_valid or out.is_empty:
        return poly, 0.0
    iou = out.intersection(poly).area / max(out.union(poly).area, 1e-6)
    if iou < 0.6 or not 0.7 <= out.area / poly.area <= 1.4:
        return poly, 0.0
    added = float((crown_ok & big & ~body).sum() * cell * cell)
    return out, round(added, 2)


# ----------------------------------------------------------------------------------------------- E6
def lidar_roof_shape(g: Grids, poly) -> str | None:
    """FLAT / SHED / GABLE / HIP from the 1 m nDSM inside the roof, or None when LiDAR cannot tell.

    Planes tested in the oriented-rectangle frame (u long axis, v short axis): gable h ~ distance to the long
    sides (or to the short sides when the ridge runs across), hip h ~ min of both, shed h ~ signed v or u.
    """
    inner = poly.buffer(-0.5)
    if inner.is_empty:
        return None
    ys, xs = np.nonzero(rasterize([inner], g.ndsm_t, g.ndsm.shape))
    if xs.size < 12:
        return None
    h = g.ndsm[ys, xs]
    keep = np.isfinite(h) & (h >= 1.0)
    if keep.mean() < 0.7:
        return None
    xs, ys, h = xs[keep], ys[keep], h[keep]
    if np.percentile(h, 90) - np.percentile(h, 10) < 0.8:
        return "FLAT"
    if len(poly.exterior.coords) - 1 > 4:
        return None
    wx, wy = g.ndsm_t * (xs + 0.5, ys + 0.5)
    box = np.asarray(poly.minimum_rotated_rectangle.exterior.coords)[:-1]
    e1, e2 = box[1] - box[0], box[2] - box[1]
    if np.hypot(*e1) < np.hypot(*e2):
        e1, e2 = e2, e1
    ul, vl = np.hypot(*e1), np.hypot(*e2)
    c = box.mean(axis=0)
    u = (np.column_stack([wx, wy]) - c) @ (e1 / ul)
    v = (np.column_stack([wx, wy]) - c) @ (e2 / vl)
    du, dv = ul / 2 - np.abs(u), vl / 2 - np.abs(v)

    def r2(x):
        a = np.column_stack([np.ones_like(x), x])
        res = np.linalg.lstsq(a, h, rcond=None)[1]
        tot = float(((h - h.mean()) ** 2).sum())
        return 1 - float(res[0]) / tot if res.size and tot > 0 else 0.0

    fits = {"GABLE": max(r2(dv), r2(du)), "HIP": r2(np.minimum(du, dv)), "SHED": max(r2(v), r2(u))}
    best = max(fits, key=fits.get)
    if fits[best] < 0.45:
        return None
    if best == "HIP" and fits["HIP"] < fits["GABLE"] + 0.05:
        best = "GABLE"
    return best


def remove_micro_edges(poly, min_edge: float = 1.0, avoid=None):
    """Collapse edges shorter than min_edge onto their midpoint (or an end), then drop collinear vertices.

    A 0.3 m step on a 10 m wall turns into a 1.7 deg kink, inside the 5 deg orthogonality tolerance.
    With ``avoid`` (the higher-priority neighbours) the collapse point is chosen so the outline does not
    re-enter them; otherwise clipping and cleaning would recreate the step forever.
    """
    from shapely.geometry import Polygon

    pts = [np.asarray(p, float) for p in list(poly.exterior.coords)[:-1]]
    changed = True
    while changed and len(pts) > 4:
        changed = False
        lens = [np.hypot(*(pts[(i + 1) % len(pts)] - pts[i])) for i in range(len(pts))]
        i = int(np.argmin(lens))
        if lens[i] < min_edge:
            j = (i + 1) % len(pts)
            done = False
            for target in ((pts[i] + pts[j]) / 2, pts[i], pts[j]):
                trial = [p for k, p in enumerate(pts) if k != j]
                trial[i if i < j else i - 1] = target
                tp = Polygon(trial)
                if tp.is_valid and (avoid is None or tp.intersection(avoid).area < 0.01):
                    pts, done = trial, True
                    break
            if not done:
                break
            changed = True
        k = 0
        while k < len(pts) and len(pts) > 4:  # collinear vertices
            a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
            cross = abs((b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0])
            if cross < 1e-6 * max(np.hypot(*(b - a)) * np.hypot(*(c - b)), 1e-9) * 100:
                del pts[k]
                changed = True
            else:
                k += 1
    out = Polygon(pts)
    if not out.is_valid or abs(out.area - poly.area) > 0.05 * poly.area:
        return poly
    return out


# ----------------------------------------------------------------------------------------------- E2
def partition(rows: list[dict]) -> int:
    """Clip every building by all higher-priority ones (in place). Returns how many were dropped."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely.strtree import STRtree

    order = sorted(range(len(rows)), key=lambda i: (-PRIORITY[rows[i]["stare"]], -rows[i]["score"]))
    tree = STRtree([r["geometry"] for r in rows])
    done, dropped = {}, 0
    for i in order:
        geom = rows[i]["geometry"]
        near = [done[j] for j in tree.query(geom.buffer(0.1)) if j in done]
        if near:
            blocker = unary_union(near)
            inter = geom.intersection(blocker).area
            if rows[i]["stare"] == "ADMIS" and 0.0 < inter <= 1.0:
                # owner vs owner sliver (the review itself has 14 such pairs, most < 1 m2): cutting it would
                # put a 0.05 m step into an owner outline; keep the owner geometry and report it instead
                rows[i]["suprapunere_proprietar_m2"] = round(inter, 3)
                inter = 0.0
            if inter > 0.0:
                rest = geom.difference(blocker)
                if rest.geom_type != "Polygon":
                    rest = max(getattr(rest, "geoms", [Polygon()]), key=lambda x: x.area)
                if rest.is_empty or rest.area < max(8.0, 0.4 * geom.area):
                    rows[i]["drop"] = "SUPRAPUNERE_DUBLURA"
                    dropped += 1
                    continue
                geom = remove_micro_edges(Polygon(rest.exterior.coords).simplify(0.05), avoid=blocker)
                # the cut edge follows the neighbour's frame; re-square it in this building's own frame,
                # shrinking (never growing into the neighbour) when the frames differ
                sq = snap_rectilinear(geom, simplify_m=0.5)
                if sq is not None and sq.is_valid:
                    sq = sq.difference(blocker)
                    sq = sq if sq.geom_type == "Polygon" else max(getattr(sq, "geoms", [Polygon()]), key=lambda x: x.area)
                    if not sq.is_empty and sq.area >= 0.9 * geom.area and len(sq.exterior.coords) <= len(geom.exterior.coords) + 2:
                        geom = Polygon(sq.exterior.coords)
                # the cut can still leave a sub-metre step where the two frames meet: collapse it inward
                # (``avoid`` keeps the outline out of the neighbour), keep the step when that slants a wall
                cleaned = remove_micro_edges(geom, avoid=blocker)
                if angle_stats([cleaned])["ortho_45_90_share"] >= angle_stats([geom])["ortho_45_90_share"]:
                    geom = cleaned
                rows[i]["clipped"] = True
        rows[i]["geometry"] = geom
        done[i] = geom
    return dropped


# ----------------------------------------------------------------------------------------------- pipeline
def best_match(geom, cands, tree):
    best, iou = None, 0.0
    for k in tree.query(geom):
        c = cands[k]
        v = c.intersection(geom).area / max(c.union(geom).area, 1e-6)
        if v > iou:
            best, iou = k, v
    return best, iou


def build(vlm_gpkg: Path, data: Path, ndsm: Path, probs: Path, decisions: Path | None) -> tuple[list[dict], dict]:
    import geopandas as gpd
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree

    g = Grids(data, ndsm, probs)
    inv = ~g.t

    def sample_edge(xy):
        c, r = inv * (float(xy[0]), float(xy[1]))
        r, c = int(r), int(c)
        return g.edge[r, c] if 0 <= r < g.shape[0] and 0 <= c < g.shape[1] else 0.0

    props = gpd.read_file(vlm_gpkg, layer="cladiri_2d_toate")
    owner = {k: gpd.read_file(REVIEW, layer=v) for k, v in {
        "admis": "1_ADMIS_FORME_BUNE_2D", "repaired": "2_AJUSTARI_REPARATE_V1_V6",
        "target": "3_AJUSTARI_TINTA_LOOP_A100", "neg": "4_MUTILATE_SI_ELIMINATE_AUDIT"}.items()}
    manual = json.loads(Path(decisions).read_text(encoding="utf-8")) if decisions and Path(decisions).is_file() else {}
    eliminate, force_incert = manual.get("elimina", {}), manual.get("incert", {})
    force_admis, groups = manual.get("admis_propus", {}), manual.get("uneste", {})
    stats = {"manual_decisions": {k: len(manual.get(k, {})) for k in ("elimina", "incert", "admis_propus", "uneste")}}
    pgeoms = list(props.geometry)
    ptree = STRtree(pgeoms)
    used = set()
    rows = []

    # E1: owner ADMIS first, their duplicates removed from the proposals
    for _, a in owner["admis"].iterrows():
        dup = [k for k in ptree.query(a.geometry) if pgeoms[k].intersection(a.geometry).area > 0.3 * pgeoms[k].area]
        used.update(dup)
        # the dropped duplicate still carries the VLM roof-shape advice for this owner roof
        best = max(dup, key=lambda k: pgeoms[k].intersection(a.geometry).area, default=None)
        rows.append({"cladire_id": a.building_id, "sursa": "PROPRIETAR_OPERA", "stare": "ADMIS",
                     "owner_verdict": "ADMIS", "geometry": a.geometry, "score": 2.0,
                     "vlm": None if best is None else props.iloc[best], "prop": None})
    for layer in ("target", "repaired"):  # owner said: real building, contour to adjust
        for _, t in owner[layer].iterrows():
            k, iou = best_match(t.geometry, pgeoms, ptree)
            if k is not None and iou >= 0.3 and k not in used:
                used.add(k)
                p = props.iloc[k]
                rows.append({"cladire_id": t.building_id, "sursa": "PROPUNERE_PE_TINTA_AJUSTARE", "stare": p.stare,
                             "owner_verdict": "AJUSTARE_CONTUR", "geometry": p.geometry, "score": float(p.vlm_admis),
                             "vlm": p, "prop": p.proposal_id})
            else:
                rows.append({"cladire_id": t.building_id, "sursa": "PROPRIETAR_AJUSTARE_NEREZOLVAT", "stare": "INCERT",
                             "owner_verdict": "AJUSTARE_CONTUR", "geometry": t.geometry, "score": 0.0, "vlm": None,
                             "prop": None})
    negs = list(owner["neg"].geometry)
    for k, p in props.iterrows():
        if k in used:
            continue
        if any(p.geometry.intersection(n).area > 0.5 * p.geometry.area for n in negs):
            stats["dropped_owner_negative"] = stats.get("dropped_owner_negative", 0) + 1
            continue
        rows.append({"cladire_id": p.proposal_id, "sursa": p.sursa, "stare": p.stare, "owner_verdict": "PENDING_OWNER_REVIEW",
                     "geometry": p.geometry, "score": float(p.vlm_admis), "vlm": p, "prop": p.proposal_id})

    # E3: image evidence decides; LiDAR only confirms
    kept = []
    for r in rows:
        r["veg_frac"] = round(g.frac(g.veg, r["geometry"]), 3)
        r["nodata_frac"] = round(g.frac(g.nodata, r["geometry"].buffer(1.0)), 3)
        v = g.heights(r["geometry"])
        r["lidar_elev_frac"] = round(float((v >= 2.0).mean()), 3) if v.size else None
        cid = r["cladire_id"]
        if cid in eliminate:
            stats["dropped_manual"] = stats.get("dropped_manual", 0) + 1
            continue
        if cid in force_incert:
            r["stare"], r["decizie_agent"] = "INCERT", "V1: " + force_incert[cid]
        elif cid in force_admis:
            r["stare"], r["decizie_agent"] = "ADMIS_PROPUS", "V1: " + force_admis[cid]
        if r["sursa"].startswith("PROPRIETAR") or cid in force_admis or cid in force_incert:
            kept.append(r)
            continue
        p = r["vlm"]
        reason = None
        width = min(np.hypot(*np.diff(np.asarray(r["geometry"].minimum_rotated_rectangle.exterior.coords)[:3], axis=0).T))
        if p is not None and p.vlm_eliminat >= 0.5:
            reason = "VLM_NU_E_CLADIRE"
        elif r["veg_frac"] >= 0.5:
            reason = "VEGETATIE"
        elif r["nodata_frac"] >= 0.25 and (width < 3.0 or (p is not None and p.vlm_admis < 0.3)):
            reason = "FASIE_NODATA"
        elif r["sursa"].startswith("NOU") and not ((r["lidar_elev_frac"] or 0) >= 0.6 and r["veg_frac"] < 0.3):
            reason = "CANDIDAT_LIDAR_NECONFIRMAT"
        elif p is not None and p.mean_roof_prob is not None and not np.isnan(p.mean_roof_prob) and \
                p.mean_roof_prob < 0.6 and p.vlm_admis < 0.3 and (r["lidar_elev_frac"] or 0) < 0.4:
            reason = "DOVEZI_SLABE"
        if reason:
            stats.setdefault("dropped_fp", {}).setdefault(reason, 0)
            stats["dropped_fp"][reason] += 1
            continue
        kept.append(r)
    rows = kept
    rows = merge_groups(rows, groups, stats)

    # E4 + E5 + snapping on the proposals (owner outlines: snapping <= 0.45 m only)
    geoms = [r["geometry"] for r in rows]
    tree = STRtree(geoms)
    for i, r in enumerate(rows):
        others = [geoms[k] for k in tree.query(r["geometry"].buffer(6)) if k != i]
        r["ocluzie_m2"] = 0.0
        if not r["sursa"].startswith("PROPRIETAR") and not r.get("tip_force"):
            rect, added = rectilinear_from_evidence(g, r["geometry"], others)
            r["rectilinear_evidenta"] = int(rect is not r["geometry"])
            r["geometry"], r["ocluzie_m2"] = rect, added
            if not r["rectilinear_evidenta"]:
                r["geometry"], r["ocluzie_m2"] = complete_occluded(g, r["geometry"], others)
        snapped, shift = snap_edges(r["geometry"], sample_edge,
                                    max_shift=0.45 if r["sursa"].startswith("PROPRIETAR") else 0.9)
        r["geometry"], r["ajustare_m"] = snapped, round(shift, 2)
        r["geom_ajustata_agent"] = int(r["sursa"].startswith("PROPRIETAR") and shift > 0)
    stats["occlusion_completed"] = sum(1 for r in rows if r["ocluzie_m2"] > 0)

    merged = merge_fragments(g, rows)
    stats["fragments_merged"] = merged
    rows = [r for r in rows if not r.get("drop")]
    for r in rows:
        cleaned = remove_micro_edges(r["geometry"])
        if cleaned is not r["geometry"] and angle_stats([cleaned])["ortho_45_90_share"] < \
                angle_stats([r["geometry"]])["ortho_45_90_share"]:
            # collapsing a step onto its midpoint slants two walls; re-square in the building frame instead
            sq = snap_rectilinear(cleaned, simplify_m=0.3)
            if sq is not None and sq.is_valid and sq.intersection(cleaned).area / max(sq.union(cleaned).area, 1e-6) >= 0.95:
                cleaned = Polygon(sq.exterior.coords)
            else:
                cleaned = r["geometry"]  # keep the step: an orthogonal 0.5 m step beats a slanted wall
        r["geometry"] = cleaned
    stats["dropped_overlap"] = partition(rows)
    rows = [r for r in rows if not r.get("drop")]

    # E6 + heights + attributes
    for r in rows:
        shape = "COMPLEX_FORTAT" if r.get("tip_force") else lidar_roof_shape(g, r["geometry"])
        p = r["vlm"]
        if shape == "COMPLEX_FORTAT":
            r["tip_acoperis"], r["tip_sursa"] = r["tip_force"], "UNIRE_VIZUALA"
            r.update(ndsm_attrs(r["geometry"], g.ndsm, g.ndsm_t))
            r["area_m2"] = round(r["geometry"].area, 2)
            continue
        if shape is not None:
            r["tip_acoperis"] = ROOF_RO[shape]
            r["tip_sursa"] = "LIDAR_PROFIL"
        elif p is not None:
            r["tip_acoperis"] = p.tip_acoperis
            r["tip_sursa"] = "VLM"
        else:
            r["tip_acoperis"] = "COMPLEX" if len(r["geometry"].exterior.coords) - 1 > 4 else "NEDETERMINAT"
            r["tip_sursa"] = "FORMA_2D"
        r.update(ndsm_attrs(r["geometry"], g.ndsm, g.ndsm_t))
        r["area_m2"] = round(r["geometry"].area, 2)
    stats["buildings"] = len(rows)
    stats["by_state"] = {s: sum(1 for r in rows if r["stare"] == s) for s in PRIORITY}
    return rows, stats


def merge_groups(rows: list[dict], groups: dict, stats: dict) -> list[dict]:
    """Visual-review merges: parts of one building (e.g. a chapel split into roof bodies) become one polygon."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union

    by_id = {r["cladire_id"]: r for r in rows}
    for name, ids in groups.items():
        parts = [by_id[i] for i in ids if i in by_id]
        if len(parts) < 2:
            continue
        u = unary_union([p["geometry"].buffer(0.4) for p in parts]).buffer(-0.4)
        u = u if u.geom_type == "Polygon" else max(u.geoms, key=lambda x: x.area)
        keep = parts[0]
        keep["geometry"] = remove_micro_edges(Polygon(u.exterior.coords).simplify(0.2))
        keep["decizie_agent"] = f"V1: unit {name} din {len(parts)} parti ({', '.join(ids)})"
        keep["fragmente_unite"] = len(parts) - 1
        keep["stare"] = max((p["stare"] for p in parts), key=lambda s: PRIORITY[s])
        keep["tip_force"] = "COMPLEX"  # several roof bodies under one building
        for p in parts[1:]:
            p["drop"] = "UNIT_IN_" + keep["cladire_id"]
        stats.setdefault("merged_groups", {})[name] = len(parts)
    return [r for r in rows if not r.get("drop")]


def merge_fragments(g: Grids, rows: list[dict], max_area: float = 30.0, dh: float = 1.0) -> int:
    """E5: a small non-owner piece touching another building at the same roof height joins it."""
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree

    geoms = [r["geometry"] for r in rows]
    tree = STRtree(geoms)
    merged = 0
    for i, r in enumerate(rows):
        if r.get("drop") or r["sursa"].startswith("PROPRIETAR") or r["geometry"].area >= max_area:
            continue
        hi = roof_height(g, r["geometry"])
        if hi is None:
            continue
        best = None
        for k in tree.query(r["geometry"].buffer(0.3)):
            if k == i or rows[k].get("drop") or r["geometry"].distance(rows[k]["geometry"]) > 0.3:
                continue
            hk = roof_height(g, rows[k]["geometry"])
            border = r["geometry"].buffer(0.3).intersection(rows[k]["geometry"].buffer(0.3))
            if hk is not None and abs(hk - hi) <= dh and border.area >= 0.6 and \
                    (best is None or rows[k]["geometry"].area > rows[best]["geometry"].area):
                best = k
        if best is None:
            continue
        u = rows[best]["geometry"].union(r["geometry"].buffer(0.3)).buffer(-0.3)
        u = u if u.geom_type == "Polygon" else max(u.geoms, key=lambda x: x.area)
        sq = snap_rectilinear(u)
        if sq is not None and sq.is_valid and u.intersection(sq).area / max(u.union(sq).area, 1e-6) >= 0.85:
            u = sq
        rows[best]["geometry"] = Polygon(u.exterior.coords)
        rows[best]["fragmente_unite"] = rows[best].get("fragmente_unite", 0) + 1
        if rows[best]["sursa"].startswith("PROPRIETAR"):
            rows[best]["geom_ajustata_agent"] = 1
        r["drop"] = "FRAGMENT_UNIT"
        merged += 1
    return merged


def write(rows: list[dict], out: Path) -> None:
    import geopandas as gpd

    cols = ["cladire_id", "sursa", "stare", "owner_verdict", "tip_acoperis", "tip_sursa", "h_streasina_m",
            "h_coama_m", "h_relief_m", "tip_ndsm", "area_m2", "ajustare_m", "ocluzie_m2", "geom_ajustata_agent",
            "veg_frac", "nodata_frac", "lidar_elev_frac", "score", "rectilinear_evidenta", "suprapunere_proprietar_m2"]
    recs = []
    for r in rows:
        rec = {c: r.get(c) for c in cols}
        rec["vlm_admis"] = None if r["vlm"] is None else float(r["vlm"].vlm_admis)
        rec["fragmente_unite"] = r.get("fragmente_unite", 0)
        rec["decizie_agent"] = r.get("decizie_agent")
        rec["geometry"] = r["geometry"]
        recs.append(rec)
    gdf = gpd.GeoDataFrame(recs, geometry="geometry", crs="EPSG:3844")
    if out.exists():
        out.unlink()
    gdf.to_file(out, layer="cladiri_2d", driver="GPKG")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vlm", type=Path, default=REPO_ROOT / "workspace/reviews/cladiri_2d_vlm_final_epsg3844.gpkg")
    ap.add_argument("--data", type=Path, default=REPO_ROOT / "workspace/colab_2d_roof_dataset_v3")
    ap.add_argument("--ndsm", type=Path, default=REPO_ROOT / "workspace/derived/cluj_ndsm_1m.tif")
    ap.add_argument("--probs", type=Path, default=REPO_ROOT / "workspace/colab_runs/loop_q/ens_b1_b3r_l3.tif")
    ap.add_argument("--decisions", type=Path, help="visual-review JSON: elimina / incert / admis_propus {id: reason}, uneste {name: [ids]}")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args(argv)
    rows, stats = build(args.vlm, args.data, args.ndsm, args.probs, args.decisions)
    write(rows, args.out)
    (args.out.with_suffix(".json")).write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
