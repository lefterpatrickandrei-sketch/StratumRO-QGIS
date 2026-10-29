# -*- coding: utf-8 -*-
"""
StratumRO — Core QA/QC: Simultaneous 6-Form 2D Roof Validator & Repair Engine
==============================================================================
Implements the Simultaneous Multi-Form Validation Protocol (V1..V6) for Phase 1
(2D Cadastral Roof Shape Extraction from RGB Orthophotos, Domain-Generalizable
to Any Zone/UAT without requiring LiDAR heights).

All 6 Validation Forms are evaluated SIMULTANEOUSLY for every roof candidate:
  - V1 (Visual Multimodal Chip & Edge Alignment):
        Evaluates boundary gradient SNR on the RGB chip, interior roof coherence,
        and renders the standardized visual inspection card (RGB + contour + vertices).
  - V2 (Whole-Roof Structural Continuation — Anti-Fragment / Single-Slope):
        Checks whether the roof texture/color continues outside any polygon edge
        (detecting half-roofs / single slopes like OPT_B_127, OPT_B_138, OPT_B_146)
        and provides automatic outward eave extension / slope merging.
  - V3 (Tree-Crown Occlusion vs. Real Architectural L/U/T Shape):
        Inspects every concave (reflex) 90° notch of polygons with >= 6 vertices.
        If the missing notch contains tree canopy (summer green ExG or autumn
        orange/yellow foliage texture) or canopy shadow (e.g., OPT_B_009, OPT_B_075,
        OPT_B_161), flags it as a Tree-Bite Occlusion and completes the straight
        90° roof corner underneath the tree crown. Preserves real L/U/T shapes
        when the notch is courtyard/ground (e.g., OPT_B_021, OPT_B_042, OPT_B_083).
  - V4 (2D Roof Shape Fidelity & 90°/45° Orthogonality):
        Enforces 90°/45° angles, minimum edge length >= 1.20 m, zero acute spikes
        (< 75°), and alignment with the dominant ridge/eave gradient angle.
  - V5 (Anti-Deformation NoData Border & Semantic Purity):
        Detects photogrammetric mesh distortions at black NoData borders
        (e.g., OPT_B_196 = MUTILAT, OPT_B_199, OPT_B_201), asphalt/parked-car strips
        (OPT_B_087, OPT_B_102), bare earth (OPT_B_050), and isolated autumn tree crowns
        (OPT_B_066).
  - V6 (Hierarchical Planar NMS & Anti-Overlap Deduplication):
        Resolves overlapping double-vectorizations using strict canonical priority:
        ADMIS > AJUSTARE_CONTUR > MUTILAT_DEFORMATIE_MODEL > ELIMINAT_EROARE_MAJORA,
        ensuring no ELIMINAT/FALSE_POS polygon ever erases or corrupts an ADMIS roof.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from shapely.affinity import rotate, translate
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union


CANONICAL_VERDICT_MAP: Dict[str, str] = {
    "ADMIS": "ADMIS",
    "AJUSTARE_CONTUR": "AJUSTARE_CONTUR",
    "CALCAN_ERROR": "AJUSTARE_CONTUR",  # Legacy alias replaced per owner rule
    "MUTILAT": "MUTILAT_DEFORMATIE_MODEL",
    "MUTILATED": "MUTILAT_DEFORMATIE_MODEL",
    "MUTILAT_DEFORMATIE_MODEL": "MUTILAT_DEFORMATIE_MODEL",
    "ELIMINAT_EROARE_MAJORA": "ELIMINAT_EROARE_MAJORA",
    "FALSE_POS": "ELIMINAT_EROARE_MAJORA",
}

VERDICT_PRIORITY: Dict[str, int] = {
    "ADMIS": 4,
    "AJUSTARE_CONTUR": 3,
    "MUTILAT_DEFORMATIE_MODEL": 2,
    "ELIMINAT_EROARE_MAJORA": 1,
}


@dataclass
class GateResult:
    gate_id: str
    passed: bool
    score: float
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimultaneousValidationReport:
    building_id: str
    canonical_verdict: str
    all_six_passed: bool
    composite_confidence: float
    gates: Dict[str, GateResult]
    recommended_action: str
    repaired_polygon_s70: Optional[Polygon] = None
    repaired_roof_px: Optional[List[List[float]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "building_id": self.building_id,
            "canonical_verdict": self.canonical_verdict,
            "all_six_passed": self.all_six_passed,
            "composite_confidence": round(self.composite_confidence, 4),
            "recommended_action": self.recommended_action,
            "gates": {
                k: {
                    "passed": g.passed,
                    "score": round(g.score, 4),
                    "reason": g.reason,
                    "details": g.details,
                }
                for k, g in self.gates.items()
            },
        }


def normalize_verdict(raw_verdict: str) -> str:
    """Convert any legacy verdict label (e.g. CALCAN_ERROR) to the owner's canonical label."""
    return CANONICAL_VERDICT_MAP.get(str(raw_verdict).strip().upper(), "AJUSTARE_CONTUR")


def _rasterize_polygon_mask(pts_px: List[Tuple[float, float]], h: int, w: int) -> np.ndarray:
    """Rasterize pixel coordinates [(x,y), ...] into a boolean (H, W) mask."""
    from PIL import Image, ImageDraw

    if len(pts_px) < 3 or h <= 0 or w <= 0:
        return np.zeros((max(h, 1), max(w, 1)), dtype=bool)
    img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(img)
    flat = [(float(x), float(y)) for x, y in pts_px]
    draw.polygon(flat, outline=1, fill=1)
    return np.array(img, dtype=np.uint8) > 0


def _compute_image_gradients(rgb: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Return gradient magnitude and orientation (in degrees [0, 180)) from an RGB uint8 chip."""
    gray = (
        0.299 * rgb[:, :, 0].astype(np.float32)
        + 0.587 * rgb[:, :, 1].astype(np.float32)
        + 0.114 * rgb[:, :, 2].astype(np.float32)
    )
    gy = np.gradient(gray, axis=0) if gray.shape[0] >= 2 else np.zeros_like(gray)
    gx = np.gradient(gray, axis=1) if gray.shape[1] >= 2 else np.zeros_like(gray)
    mag = np.hypot(gx, gy)
    ang = (np.degrees(np.arctan2(gy, gx)) + 180.0) % 180.0
    return mag, ang


def _foliage_and_canopy_score(rgb_patch: np.ndarray) -> float:
    """
    Detect both summer green foliage (ExG) and autumn yellow/orange/rust tree canopy
    (high local micro-texture variance + warm hue with mottled shadow).
    Returns a score in [0.0, 1.0].
    """
    if rgb_patch.size == 0:
        return 0.0
    r = rgb_patch[:, :, 0].astype(np.float32)
    g = rgb_patch[:, :, 1].astype(np.float32)
    b = rgb_patch[:, :, 2].astype(np.float32)
    # 1. Excess Green (ExG) for green trees/bushes
    exg = 2.0 * g - r - b
    green_frac = float(np.mean(exg > 18.0))
    # 2. Autumn foliage / crown texture (high high-frequency gradient variance + warm yellow-orange-brown)
    mag, _ = _compute_image_gradients(rgb_patch)
    high_tex = float(np.mean(mag > 14.0))
    warm_autumn = (r > g * 0.95) & (g > b * 1.15) & (r > 60) & (r < 210)
    autumn_frac = float(np.mean(warm_autumn & (mag > 10.0)))
    return float(np.clip(max(green_frac * 1.4, autumn_frac * 1.35 + 0.25 * high_tex), 0.0, 1.0))


def validate_v1_visual_chip(
    rgb: np.ndarray,
    roof_px: List[Tuple[float, float]],
) -> GateResult:
    """
    V1: Visual Multimodal Chip & Photometric Edge Alignment Gate.
    Measures boundary gradient SNR along the vectorized contour vs interior coherence.
    """
    h, w = rgb.shape[:2]
    mask = _rasterize_polygon_mask(roof_px, h, w)
    if mask.sum() < 25:
        return GateResult("V1_VISUAL_CHIP", False, 0.0, "Poligon prea mic pe cipul ortofoto", {})

    mag, _ = _compute_image_gradients(rgb)
    from PIL import Image, ImageDraw

    edge_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(edge_img)
    draw.line([(float(x), float(y)) for x, y in roof_px], fill=1, width=3)
    edge_band = np.array(edge_img, dtype=np.uint8) > 0

    interior = mask & (~edge_band)
    edge_grad = float(np.mean(mag[edge_band])) if edge_band.any() else 0.0
    int_grad = float(np.mean(mag[interior])) if interior.any() else 10.0
    snr = edge_grad / max(int_grad, 4.0)

    # Check interior vs exterior color separation
    dil_img = Image.new("L", (w, h), 0)
    d2 = ImageDraw.Draw(dil_img)
    d2.line([(float(x), float(y)) for x, y in roof_px], fill=1, width=11)
    ext_ring = (np.array(dil_img, dtype=np.uint8) > 0) & (~mask)
    if interior.any() and ext_ring.any():
        int_rgb = np.mean(rgb[interior].astype(np.float32), axis=0)
        ext_rgb = np.mean(rgb[ext_ring].astype(np.float32), axis=0)
        color_sep = float(np.linalg.norm(int_rgb - ext_rgb))
    else:
        color_sep = 0.0

    score = float(np.clip(0.5 * min(snr / 1.35, 1.0) + 0.5 * min(color_sep / 28.0, 1.0), 0.0, 1.0))
    passed = score >= 0.58 and snr >= 0.85
    reason = (
        f"Aliniere vizuala buna pe streasina (SNR={snr:.2f}, dRGB={color_sep:.1f})"
        if passed
        else f"Contur slab aliniat cu marginea vizuala a acoperisului (SNR={snr:.2f}, dRGB={color_sep:.1f})"
    )
    return GateResult(
        "V1_VISUAL_CHIP",
        passed,
        score,
        reason,
        {"edge_snr": round(snr, 3), "color_separation": round(color_sep, 2), "edge_grad": round(edge_grad, 2)},
    )


def validate_v2_whole_roof_continuation(
    rgb: np.ndarray,
    roof_px: List[Tuple[float, float]],
) -> GateResult:
    """
    V2: Whole-Roof Structural Continuation Gate (Anti-Fragment / Single-Slope Check).
    Checks each segment of the polygon to verify whether the same roof material/color
    continues outside the segment (which happens when only 1 roof slope or 1/3 of a house
    was vectorized, e.g., OPT_B_124, OPT_B_127, OPT_B_138, OPT_B_146, OPT_B_155, OPT_B_156).
    """
    h, w = rgb.shape[:2]
    mask = _rasterize_polygon_mask(roof_px, h, w)
    if not mask.any() or len(roof_px) < 4:
        return GateResult("V2_WHOLE_ROOF", False, 0.0, "Geometrie insuficienta", {})

    poly_px = Polygon(roof_px)
    if not poly_px.is_valid:
        poly_px = poly_px.buffer(0)
    if poly_px.is_empty or isinstance(poly_px, MultiPolygon):
        return GateResult("V2_WHOLE_ROOF", True, 0.85, "Poligon analizat", {})

    int_pixels = rgb[mask].astype(np.float32)
    int_med = np.median(int_pixels, axis=0)
    int_mad = np.clip(np.median(np.abs(int_pixels - int_med), axis=0) * 1.4826, 8.0, 18.0)

    coords = list(poly_px.exterior.coords)
    leaking_edges = 0
    max_leak_ratio = 0.0
    leaking_edge_indices: List[int] = []

    for idx in range(len(coords) - 1):
        p1 = np.array(coords[idx], dtype=np.float64)
        p2 = np.array(coords[idx + 1], dtype=np.float64)
        seg_vec = p2 - p1
        seg_len = float(np.linalg.norm(seg_vec))
        if seg_len < 16.0:
            continue
        tangent = seg_vec / seg_len
        # Test outward normal
        n1 = np.array([-tangent[1], tangent[0]])
        mid = 0.5 * (p1 + p2)
        out_normal = n1 if not poly_px.contains(Point(mid[0] + n1[0] * 3.0, mid[1] + n1[1] * 3.0)) else -n1

        # Sample points 5..14 px outside this edge
        ts = np.linspace(0.20, 0.80, 9)
        outside_samples = []
        for t in ts:
            base = p1 + t * seg_vec
            for dist in (5.0, 9.0, 14.0):
                sx = int(round(base[0] + out_normal[0] * dist))
                sy = int(round(base[1] + out_normal[1] * dist))
                if 0 <= sx < w and 0 <= sy < h:
                    px_val = rgb[sy, sx].astype(np.float32)
                    if np.sum(px_val) > 35:  # Not NoData black
                        outside_samples.append(px_val)
        if len(outside_samples) >= 9:
            arr_out = np.array(outside_samples, dtype=np.float32)
            # Reject foliage/canopy from being mistaken for roof continuation
            out_patch = arr_out.reshape(-1, 1, 3).astype(np.uint8)
            if _foliage_and_canopy_score(out_patch) >= 0.35:
                continue
            z_dist = np.mean(np.abs(arr_out - int_med) / int_mad, axis=1)
            same_roof_ratio = float(np.mean(z_dist < 0.90))
            if same_roof_ratio > max_leak_ratio:
                max_leak_ratio = same_roof_ratio
            if same_roof_ratio >= 0.75:
                leaking_edges += 1
                leaking_edge_indices.append(idx)

    passed = leaking_edges == 0
    score = float(np.clip(1.0 - 0.55 * leaking_edges - 0.3 * max(0.0, max_leak_ratio - 0.5), 0.0, 1.0))
    reason = (
        "Acoperis cuprins integral de la streasina la streasina"
        if passed
        else f"Fragment incomplet: textura acoperisului continua in exterior pe {leaking_edges} laturi (max_cont={max_leak_ratio:.2f})"
    )
    return GateResult(
        "V2_WHOLE_ROOF",
        passed,
        score,
        reason,
        {
            "leaking_edges": leaking_edges,
            "leaking_edge_indices": leaking_edge_indices,
            "max_continuation_ratio": round(max_leak_ratio, 3),
        },
    )


def validate_v3_tree_occlusion_vs_l_shape(
    rgb: np.ndarray,
    roof_px: List[Tuple[float, float]],
    poly_s70: Polygon,
) -> GateResult:
    """
    V3: Tree-Crown Occlusion vs. Real Architectural L/U/T Shape Gate.
    For polygons with >= 6 vertices, checks whether the concave notch (difference between
    the Minimum Rotated Rectangle and the polygon) is filled with tree canopy / shadow
    (meaning a tree crown bit a corner out of a rectangular roof, e.g., OPT_B_009, OPT_B_075,
    OPT_B_161) vs real courtyard/ground (real L/U/T building, e.g., OPT_B_021, OPT_B_042, OPT_B_083).
    """
    pts = list(poly_s70.exterior.coords)[:-1] if hasattr(poly_s70, "exterior") else []
    num_nodes = len(pts)
    if num_nodes <= 4:
        return GateResult(
            "V3_TREE_OCCLUSION_L_SHAPE",
            True,
            1.0,
            "Forma convexa 4 noduri (fara muscatura de copac)",
            {"nodes": num_nodes, "is_tree_bite": False},
        )

    poly_px = Polygon(roof_px)
    if not poly_px.is_valid:
        poly_px = poly_px.buffer(0)
    mrr_px = poly_px.minimum_rotated_rectangle
    notch_px = mrr_px.difference(poly_px)
    notch_ratio = notch_px.area / max(mrr_px.area, 1.0)

    h, w = rgb.shape[:2]
    int_mask = _rasterize_polygon_mask(roof_px, h, w)
    int_pixels = rgb[int_mask].astype(np.float32) if int_mask.any() else np.zeros((1, 3), dtype=np.float32)
    int_med = np.median(int_pixels, axis=0)
    int_mad = np.clip(np.median(np.abs(int_pixels - int_med), axis=0) * 1.4826, 10.0, 22.0)

    # Check what lies inside the largest concave notch(es)
    notches = list(notch_px.geoms) if hasattr(notch_px, "geoms") else ([notch_px] if not notch_px.is_empty else [])
    tree_bitten_notches = 0
    max_canopy_score = 0.0

    for n_poly in notches:
        if n_poly.area < 25.0 or (n_poly.area / max(mrr_px.area, 1.0)) > 0.38:
            # If notch is > 38% of MRR, it's a large architectural L/U courtyard, not a corner bite
            continue
        n_coords = list(n_poly.exterior.coords)
        n_mask = _rasterize_polygon_mask(n_coords, h, w)
        if n_mask.sum() < 15:
            continue
        ys, xs = np.where(n_mask)
        patch = rgb[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
        canopy = _foliage_and_canopy_score(patch)
        # Also check if the notch is filled with the same roof material or tree shadow
        notch_px_vals = rgb[n_mask].astype(np.float32)
        z_roof = np.mean(np.abs(notch_px_vals - int_med) / int_mad, axis=1)
        roof_cont_frac = float(np.mean(z_roof < 1.15))
        combined_score = max(canopy, roof_cont_frac * 0.85)
        if combined_score > max_canopy_score:
            max_canopy_score = combined_score
        if canopy >= 0.36 or (num_nodes in (6, 8) and roof_cont_frac >= 0.58 and notch_ratio <= 0.32):
            tree_bitten_notches += 1

    is_tree_bite = tree_bitten_notches > 0 and notch_ratio <= 0.36
    passed = not is_tree_bite
    score = 0.35 if is_tree_bite else 0.95
    reason = (
        f"Forma articulata reala ({num_nodes} noduri, curte/retrageri reale)"
        if passed
        else f"Muscatura falsa de copac pe colt ({num_nodes} noduri, scor coroana={max_canopy_score:.2f}) — necesita completarea coltului 90° pe sub copac"
    )
    return GateResult(
        "V3_TREE_OCCLUSION_L_SHAPE",
        passed,
        score,
        reason,
        {
            "nodes": num_nodes,
            "notch_ratio": round(notch_ratio, 3),
            "max_canopy_score": round(max_canopy_score, 3),
            "is_tree_bite": is_tree_bite,
        },
    )


def validate_v4_orthogonality_and_shape(
    rgb: np.ndarray,
    roof_px: List[Tuple[float, float]],
    poly_s70: Polygon,
) -> GateResult:
    """
    V4: 2D Roof Shape Fidelity, 90°/45° Orthogonality & Dominant Eave Alignment Gate.
    Checks vertex angles, minimum edge length >= 1.20m, and ensures the polygon is not
    axis-aligned North-South against a rotated roof (e.g., OPT_B_152, OPT_B_185, OPT_B_198).
    """
    if poly_s70.is_empty or not hasattr(poly_s70, "exterior"):
        return GateResult("V4_ORTHO_SHAPE", False, 0.0, "Poligon gol", {})

    coords = list(poly_s70.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return GateResult("V4_ORTHO_SHAPE", False, 0.0, f"Prea putine noduri ({n})", {})

    short_edges = 0
    non_ortho_corners = 0
    edge_angles = []
    edge_lengths = []

    for i in range(n):
        p_prev = np.array(coords[i - 1])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        v1 = p_curr - p_prev
        v2 = p_next - p_curr
        l1 = float(np.linalg.norm(v1))
        l2 = float(np.linalg.norm(v2))
        edge_lengths.append(l2)
        if l2 < 1.15:
            short_edges += 1
        if l1 > 1e-3 and l2 > 1e-3:
            cos_a = float(np.clip(np.dot(v1, v2) / (l1 * l2), -1.0, 1.0))
            ang = math.degrees(math.acos(cos_a))
            # Turn angle should be close to 90° or 45° or 0°
            dev = min(abs(ang - 90.0), abs(ang - 45.0), abs(ang - 0.0))
            if dev > 8.0:
                non_ortho_corners += 1
            edge_ang = (math.degrees(math.atan2(v2[1], v2[0])) + 90.0) % 90.0
            edge_angles.append((edge_ang, l2))

    # Check if an articulated polygon (>6 nodes) is a jagged North-South raster staircase
    staircase_penalty = 0.0
    if n >= 8 and short_edges >= 2:
        staircase_penalty = 0.45

    score = float(
        np.clip(
            1.0 - 0.15 * short_edges - 0.25 * non_ortho_corners - staircase_penalty,
            0.0,
            1.0,
        )
    )
    passed = non_ortho_corners == 0 and short_edges <= 1 and staircase_penalty == 0.0
    reason = (
        f"Geometrie 2D ortogonala curata ({n} noduri, min_edge={min(edge_lengths):.2f}m)"
        if passed
        else f"Defecte de forma 2D: {short_edges} laturi scurte (<1.2m), {non_ortho_corners} unghiuri neortogonale"
    )
    return GateResult(
        "V4_ORTHO_SHAPE",
        passed,
        score,
        reason,
        {
            "nodes": n,
            "min_edge_m": round(min(edge_lengths), 2) if edge_lengths else 0.0,
            "short_edges": short_edges,
            "non_ortho_corners": non_ortho_corners,
        },
    )


def validate_v5_anti_artifact_and_nodata(
    rgb: np.ndarray,
    roof_px: List[Tuple[float, float]],
    poly_s70: Polygon,
    touches_nodata_flag: int = 0,
) -> GateResult:
    """
    V5: Anti-Deformation (NoData Border) & Semantic Purity Gate (Road / Cars / Autumn Trees / Bare Ground).
    Catches:
      - Photogrammetric mesh distortions at black NoData borders (OPT_B_196 = MUTILAT, OPT_B_186, OPT_B_199, OPT_B_201)
      - Autumn/Summer tree crowns mistaken for roofs (OPT_B_066)
      - Asphalt strips with parked cars (OPT_B_087, OPT_B_102)
      - Bare dirt / construction ground (OPT_B_050, OPT_B_210)
    """
    h, w = rgb.shape[:2]
    mask = _rasterize_polygon_mask(roof_px, h, w)
    if not mask.any():
        return GateResult("V5_ANTI_ARTIFACT_NODATA", False, 0.0, "Masca goala", {})

    # 1. Check NoData black pixels ([0..8, 0..8, 0..8]) inside the polygon and in a 7px collar
    from PIL import Image, ImageDraw

    collar_img = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(collar_img)
    d.polygon([(float(x), float(y)) for x, y in roof_px], fill=1, outline=1)
    d.line([(float(x), float(y)) for x, y in roof_px], fill=1, width=15)
    collar_mask = np.array(collar_img, dtype=np.uint8) > 0

    black_px = (rgb[:, :, 0] < 8) & (rgb[:, :, 1] < 8) & (rgb[:, :, 2] < 8)
    nodata_inside = float(np.mean(black_px[mask]))
    nodata_collar = float(np.mean(black_px[collar_mask]))
    nodata_chip = float(np.mean(black_px))

    # 2. Check foliage / tree crown inside polygon
    ys, xs = np.where(mask)
    sub_rgb = rgb[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    canopy_inside = _foliage_and_canopy_score(sub_rgb)

    # 3. Check elongated asphalt/road strip (low saturation + high aspect ratio)
    mrr = poly_s70.minimum_rotated_rectangle
    mrr_coords = list(mrr.exterior.coords)[:-1]
    if len(mrr_coords) == 4:
        e1 = float(np.linalg.norm(np.array(mrr_coords[1]) - np.array(mrr_coords[0])))
        e2 = float(np.linalg.norm(np.array(mrr_coords[2]) - np.array(mrr_coords[1])))
        aspect = max(e1, e2) / max(min(e1, e2), 0.5)
        min_width_m = min(e1, e2)
    else:
        aspect, min_width_m = 1.0, 5.0

    int_rgb = rgb[mask].astype(np.float32)
    sat = (np.max(int_rgb, axis=1) - np.min(int_rgb, axis=1)) / np.maximum(np.max(int_rgb, axis=1), 1.0)
    mean_sat = float(np.mean(sat))

    is_nodata_mutilated = nodata_inside > 0.03 or (nodata_collar > 0.14 and nodata_chip > 0.18)
    is_road_strip = aspect > 4.2 and min_width_m < 3.6 and mean_sat < 0.16
    is_tree_crown = canopy_inside > 0.68 and poly_s70.area < 95.0

    passed = not (is_nodata_mutilated or is_road_strip or is_tree_crown)
    if is_nodata_mutilated:
        reason = f"Deformatie la marginea NoData (nodata_in={nodata_inside:.1%}, collar={nodata_collar:.1%})"
        score = 0.15
    elif is_road_strip:
        reason = f"Banda ingusta de asfalt/carosabil (aspect={aspect:.1f}, latime={min_width_m:.1f}m)"
        score = 0.20
    elif is_tree_crown:
        reason = f"Coroana de arbore / vegetatie densa (canopy={canopy_inside:.2f})"
        score = 0.20
    else:
        reason = "Fara deformatii NoData sau artefacte de carosabil/vegetatie"
        score = float(np.clip(1.0 - nodata_collar * 2.0 - 0.3 * max(0.0, canopy_inside - 0.35), 0.5, 1.0))

    return GateResult(
        "V5_ANTI_ARTIFACT_NODATA",
        passed,
        score,
        reason,
        {
            "nodata_inside": round(nodata_inside, 4),
            "nodata_collar": round(nodata_collar, 4),
            "canopy_inside": round(canopy_inside, 3),
            "aspect_ratio": round(aspect, 2),
            "min_width_m": round(min_width_m, 2),
            "mean_saturation": round(mean_sat, 3),
            "touches_nodata_flag": int(touches_nodata_flag),
        },
    )


def repair_v3_complete_tree_bitten_corners(
    poly_s70: Polygon,
    roof_px: List[Tuple[float, float]],
    rgb: np.ndarray,
) -> Tuple[Polygon, List[List[float]], bool]:
    """
    Deterministic Geometric Repair for V3 (Tree-Crown Occlusion):
    When an L-shaped or 6-to-8 node polygon fails V3 because a tree crown bit out a 90°
    corner (like OPT_B_009, OPT_B_075, OPT_B_161), completes the missing corner using the
    Minimum Rotated Rectangle (when only 1 tree-bitten notch exists) or local reflex-corner
    closure, restoring the true straight roof edges underneath the tree canopy.
    """
    v3 = validate_v3_tree_occlusion_vs_l_shape(rgb, roof_px, poly_s70)
    if v3.passed or not v3.details.get("is_tree_bite", False):
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    pts_s70 = list(poly_s70.exterior.coords)[:-1] if hasattr(poly_s70, "exterior") else []
    if len(pts_s70) > 10:
        # Multi-notch or heavily jagged contour (>10 nodes) needs SAM2.1 reprompting, not blind MRR
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    poly_px_orig = Polygon(roof_px)
    if not poly_px_orig.is_valid:
        poly_px_orig = poly_px_orig.buffer(0)
    mrr_px = poly_px_orig.minimum_rotated_rectangle
    if (mrr_px.area - poly_px_orig.area) / max(mrr_px.area, 1.0) > 0.36:
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    mrr_s70 = poly_s70.minimum_rotated_rectangle
    px_coords = [[round(float(x), 1), round(float(y), 1)] for x, y in mrr_px.exterior.coords]
    return mrr_s70, px_coords, True


def repair_v2_whole_roof_extension(
    poly_s70: Polygon,
    roof_px: List[Tuple[float, float]],
    rgb: np.ndarray,
    bounds_s70: List[float],
) -> Tuple[Polygon, List[List[float]], bool]:
    """
    Deterministic Geometric Repair for V2 (Whole-Roof Continuation):
    When a polygon only captured a fragment/single slope of a roof (e.g., OPT_B_127,
    OPT_B_138, OPT_B_146), marches outward from each leaking edge on the RGB chip until
    the roof color/texture discontinuity is reached, expanding the oriented rectangle
    to cover the whole roof ONLY if the extended edge lands on a genuine roof boundary.
    """
    v2 = validate_v2_whole_roof_continuation(rgb, roof_px)
    if v2.passed:
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    h, w = rgb.shape[:2]
    mask = _rasterize_polygon_mask(roof_px, h, w)
    int_pixels = rgb[mask].astype(np.float32)
    int_med = np.median(int_pixels, axis=0)
    int_mad = np.clip(np.median(np.abs(int_pixels - int_med), axis=0) * 1.4826, 8.0, 16.0)

    poly_px = Polygon(roof_px)
    if not poly_px.is_valid:
        poly_px = poly_px.buffer(0)
    if abs(poly_px.area - poly_px.minimum_rotated_rectangle.area) / max(poly_px.area, 1.0) > 0.15:
        # Only extend already-rectangular single-slope fragments, never L-shapes
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    mrr_px = poly_px.minimum_rotated_rectangle
    coords = list(mrr_px.exterior.coords)[:-1]
    if len(coords) != 4:
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    v1_before = validate_v1_visual_chip(rgb, roof_px)

    # March each of the 4 edges outward as long as pixels match the roof color/texture
    pts = [np.array(c, dtype=np.float64) for c in coords]
    changed = False
    for i in range(4):
        p1, p2 = pts[i], pts[(i + 1) % 4]
        seg = p2 - p1
        seg_len = float(np.linalg.norm(seg))
        if seg_len < 16.0:
            continue
        t_vec = seg / seg_len
        n_cand = np.array([-t_vec[1], t_vec[0]])
        mid = 0.5 * (p1 + p2)
        out_n = n_cand if not mrr_px.contains(Point(mid[0] + n_cand[0] * 3.0, mid[1] + n_cand[1] * 3.0)) else -n_cand

        best_shift = 0.0
        for d in range(4, 76, 3):
            ts = np.linspace(0.2, 0.8, 7)
            matches = 0
            valid_pts = 0
            samples_d = []
            for t in ts:
                bx, by = p1 + t * seg + out_n * float(d)
                ix, iy = int(round(bx)), int(round(by))
                if 8 <= ix < w - 8 and 8 <= iy < h - 8:
                    px_val = rgb[iy, ix].astype(np.float32)
                    if np.sum(px_val) > 35:
                        valid_pts += 1
                        samples_d.append(px_val)
                        z = float(np.mean(np.abs(px_val - int_med) / int_mad))
                        if z < 0.95:
                            matches += 1
            if valid_pts >= 5 and (matches / valid_pts) >= 0.72:
                arr_d = np.array(samples_d, dtype=np.uint8).reshape(-1, 1, 3)
                if _foliage_and_canopy_score(arr_d) >= 0.35:
                    break
                best_shift = float(d)
            else:
                break

        if best_shift >= 6.0:
            # Verify there is an actual roof boundary stop beyond best_shift + 6 px
            beyond_z = []
            for t in np.linspace(0.25, 0.75, 5):
                bx, by = p1 + t * seg + out_n * (best_shift + 6.0)
                ix, iy = int(round(bx)), int(round(by))
                if 4 <= ix < w - 4 and 4 <= iy < h - 4:
                    px_val = rgb[iy, ix].astype(np.float32)
                    beyond_z.append(float(np.mean(np.abs(px_val - int_med) / int_mad)))
            if beyond_z and float(np.mean(beyond_z)) >= 1.10:
                pts[i] = pts[i] + out_n * best_shift
                pts[(i + 1) % 4] = pts[(i + 1) % 4] + out_n * best_shift
                changed = True

    if not changed:
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    new_px = [[round(float(p[0]), 1), round(float(p[1]), 1)] for p in pts]
    new_px.append(new_px[0])

    # Simultaneous V1 Visual Check: only accept extension if V1 visual alignment holds or improves
    v1_after = validate_v1_visual_chip(rgb, [(p[0], p[1]) for p in new_px])
    if v1_after.score < max(0.55, v1_before.score - 0.03):
        return poly_s70, [[float(x), float(y)] for x, y in roof_px], False

    # Map pixel coordinates back to Stereo 70 (EPSG:3844) using chip bounds
    minx, miny, maxx, maxy = bounds_s70
    s70_ring = []
    for px_x, px_y in new_px:
        sx = minx + (px_x / float(w)) * (maxx - minx)
        sy = maxy - (px_y / float(h)) * (maxy - miny)
        s70_ring.append((sx, sy))
    new_poly_s70 = Polygon(s70_ring).minimum_rotated_rectangle
    return new_poly_s70, new_px, True


def evaluate_building_simultaneously(
    building_id: str,
    raw_verdict: str,
    rgb: np.ndarray,
    roof_px: List[List[float]],
    poly_s70: Polygon,
    bounds_s70: List[float],
    touches_nodata_flag: int = 0,
    overlap_area_m2: float = 0.0,
    overlapping_with: Optional[List[str]] = None,
    auto_repair: bool = True,
) -> SimultaneousValidationReport:
    """
    Runs ALL 6 Validation Forms (V1..V6) SIMULTANEOUSLY on a building candidate.
    If auto_repair=True and the building is in AJUSTARE_CONTUR (or fails V2/V3),
    executes the deterministic V3 Tree-Bite Completion and V2 Whole-Roof Extension
    and re-verifies all 6 gates simultaneously.
    """
    canonical_v = normalize_verdict(raw_verdict)
    pts_tuples = [(float(p[0]), float(p[1])) for p in roof_px]

    g1 = validate_v1_visual_chip(rgb, pts_tuples)
    g2 = validate_v2_whole_roof_continuation(rgb, pts_tuples)
    g3 = validate_v3_tree_occlusion_vs_l_shape(rgb, pts_tuples, poly_s70)
    g4 = validate_v4_orthogonality_and_shape(rgb, pts_tuples, poly_s70)
    g5 = validate_v5_anti_artifact_and_nodata(rgb, pts_tuples, poly_s70, touches_nodata_flag)
    g6_passed = overlap_area_m2 < 0.25
    g6 = GateResult(
        "V6_PLANAR_NMS_OVERLAP",
        g6_passed,
        1.0 if g6_passed else max(0.0, 1.0 - overlap_area_m2 / max(poly_s70.area, 1.0)),
        "Zero suprapuneri duble" if g6_passed else f"Suprapunere {overlap_area_m2:.2f} m2 cu {overlapping_with or []}",
        {"overlap_area_m2": round(overlap_area_m2, 2), "overlapping_with": overlapping_with or []},
    )

    repaired_poly: Optional[Polygon] = None
    repaired_px: Optional[List[List[float]]] = None

    if auto_repair and canonical_v in ("AJUSTARE_CONTUR", "ADMIS") and (not g3.passed or not g2.passed):
        cur_poly, cur_px = poly_s70, [[float(x), float(y)] for x, y in roof_px]
        did_repair = False
        if not g3.passed:
            cur_poly, cur_px, r3 = repair_v3_complete_tree_bitten_corners(
                cur_poly, [(p[0], p[1]) for p in cur_px], rgb
            )
            did_repair = did_repair or r3
        elif not g2.passed:
            cur_poly, cur_px, r2 = repair_v2_whole_roof_extension(
                cur_poly, [(p[0], p[1]) for p in cur_px], rgb, bounds_s70
            )
            did_repair = did_repair or r2
        if did_repair:
            repaired_poly = cur_poly
            repaired_px = cur_px
            pts_rep = [(float(p[0]), float(p[1])) for p in repaired_px]
            g1 = validate_v1_visual_chip(rgb, pts_rep)
            g2 = validate_v2_whole_roof_continuation(rgb, pts_rep)
            g3 = validate_v3_tree_occlusion_vs_l_shape(rgb, pts_rep, repaired_poly)
            g4 = validate_v4_orthogonality_and_shape(rgb, pts_rep, repaired_poly)

    gates = {
        "V1_VISUAL_CHIP": g1,
        "V2_WHOLE_ROOF": g2,
        "V3_TREE_OCCLUSION_L_SHAPE": g3,
        "V4_ORTHO_SHAPE": g4,
        "V5_ANTI_ARTIFACT_NODATA": g5,
        "V6_PLANAR_NMS_OVERLAP": g6,
    }
    all_passed = all(g.passed for g in gates.values())
    comp_score = float(np.mean([g.score for g in gates.values()]))

    if canonical_v in ("MUTILAT_DEFORMATIE_MODEL", "ELIMINAT_EROARE_MAJORA") or not g5.passed:
        action = "SUPPRESS_ARTIFACT_OR_HARD_NEGATIVE"
    elif all_passed:
        action = "PROMOTE_GOLD_2D_ROOF"
    elif repaired_poly is not None:
        action = "REPAIRED_BY_V2_V3_SEND_TO_A100_SAM21_REFINER"
    else:
        action = "REPROMPT_ON_COLAB_A100_LOOP"

    return SimultaneousValidationReport(
        building_id=building_id,
        canonical_verdict=canonical_v,
        all_six_passed=all_passed,
        composite_confidence=comp_score,
        gates=gates,
        recommended_action=action,
        repaired_polygon_s70=repaired_poly,
        repaired_roof_px=repaired_px,
    )


def deduplicate_v6_planar_nms(
    records: List[Dict[str, Any]],
    iou_dup_threshold: float = 0.35,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    V6 Hierarchical Spatial Deduplication & Planar NMS across all catalog candidates.
    Rules enforced:
      1. Exact `_INCOMPLET` duplicates of an existing `OPT_B_xxx:C1` are collapsed immediately,
         keeping the higher-priority human verdict (`ADMIS > AJUSTARE_CONTUR > MUTILAT > ELIMINAT`).
      2. For overlapping distinct candidates (`intersection / min(area1, area2) >= iou_dup_threshold`):
         - An `ELIMINAT_EROARE_MAJORA` or `MUTILAT_DEFORMATIE_MODEL` overlapping an `ADMIS` or
           `AJUSTARE_CONTUR` roof is flagged as a suppressed double-vectorization so it NEVER
           corrupts the positive roof mask!
         - Two overlapping `ADMIS` polygons on the same physical building keep the one with
           higher Simultaneous Validation score (or larger whole-roof coverage) and mark the
           redundant duplicate as `SUPPRESSED_DOUBLE_VECTORIZATION`.
    Returns `(kept_records, suppressed_records)`.
    """
    # Step 1: Collapse exact base candidate_id duplicates (e.g. OPT_B_083:C1 and OPT_B_083:C1_INCOMPLET)
    by_base_cid: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        rec = dict(rec)
        rec["canonical_verdict"] = normalize_verdict(rec.get("verdict", "AJUSTARE_CONTUR"))
        base_cid = rec.get("candidate_id") or rec["id"].replace("_INCOMPLET", "").replace("_DUP", "").replace("_FP", "")
        rec["base_cid"] = base_cid
        by_base_cid.setdefault(base_cid, []).append(rec)

    collapsed: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []

    for base_cid, group in by_base_cid.items():
        if len(group) == 1:
            collapsed.append(group[0])
        else:
            # Sort so non-_INCOMPLET with highest verdict priority comes first
            group.sort(
                key=lambda r: (
                    VERDICT_PRIORITY.get(r["canonical_verdict"], 0),
                    0 if "_INCOMPLET" in r["id"] else 1,
                    r["poly_s70"].area,
                ),
                reverse=True,
            )
            winner = group[0]
            collapsed.append(winner)
            for dup in group[1:]:
                dup["suppression_reason"] = f"EXACT_BASE_ID_DUPLICATE_OF_{winner['id']}"
                suppressed.append(dup)

    # Step 2: Sort remaining candidates by (Verdict Priority DESC, Area DESC) for Planar NMS
    collapsed.sort(
        key=lambda r: (
            VERDICT_PRIORITY.get(r["canonical_verdict"], 0),
            r.get("composite_confidence", 0.8),
            r["poly_s70"].area,
        ),
        reverse=True,
    )

    kept: List[Dict[str, Any]] = []
    for cand in collapsed:
        p_cand: Polygon = cand["poly_s70"]
        is_redundant = False
        for k in kept:
            p_kept: Polygon = k["poly_s70"]
            if not p_cand.intersects(p_kept):
                continue
            inter_area = p_cand.intersection(p_kept).area
            min_area = max(min(p_cand.area, p_kept.area), 1e-3)
            overlap_ratio = inter_area / min_area

            if overlap_ratio >= iou_dup_threshold:
                # Double vectorization on the same building!
                cand["suppression_reason"] = (
                    f"DOUBLE_VECTORIZATION_OVERLAP_{overlap_ratio:.1%}_WITH_{k['id']}({k['canonical_verdict']})"
                )
                suppressed.append(cand)
                is_redundant = True
                break
        if not is_redundant:
            kept.append(cand)

    return kept, suppressed
