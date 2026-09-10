# -*- coding: utf-8 -*-
"""
StratumRO — Nucleu de Evaluare și Validare Geodezică Cantitativă
================================================================
Calculează metrici matematice obiective între contururile de referință (Ground Truth)
și predicțiile generate de pipeline-ul hibrid (LiDAR + SAM2 + Regularizare):
  - IoU (Indicele Jaccard)
  - Distanța Hausdorff Bidirecțională (densificată nativ prin GEOS C++)
  - Boundary RMSE (Root Mean Square Error pe eșantionare continuă de contur)
  - Dislocare centroid, deviație unghiulară și erori de arie/perimetru
  - Clasificare de conformitate: CONFORM_ANCPI / ACCEPTABIL_PUG / REJECT

Standarde de conformitate:
  - ANCPI Ordinul 600/2023 (Toleranță planimetrică intravilan <= 0.10 m)
  - MDLPA Ordinul 904/2023 & Legea 350/2001 (Toleranță PUG <= 0.30 m)
"""

import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import time
import math
import json
import argparse
import datetime
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
import shapely
from shapely.geometry import Polygon, MultiPolygon, Point, LineString, box
from shapely.ops import unary_union
from shapely.validation import make_valid
import geopandas as gpd
import yaml
import scipy.stats


# =====================================================================
# 1. STRUCTURI DE DATE (DATACLASSES)
# =====================================================================

@dataclass
class BuildingEvaluationResult:
    """Rezultatul evaluării detaliate pentru o pereche Referință - Predicție."""
    ref_id: str
    pred_id: str
    matched: bool
    iou: float = 0.0
    hausdorff_m: float = 0.0
    boundary_rmse_m: float = 0.0
    centroid_disp_m: float = 0.0
    area_ref_m2: float = 0.0
    area_pred_m2: float = 0.0
    area_error_m2: float = 0.0
    area_error_pct: float = 0.0
    perimeter_ref_m: float = 0.0
    perimeter_pred_m: float = 0.0
    mean_angle_dev_deg: float = 0.0
    compliance_tier: str = "REJECT"  # "CONFORM_ANCPI", "ACCEPTABIL_PUG", "REJECT"
    error_flags: List[str] = field(default_factory=list)
    svg_data: Optional[str] = None


@dataclass
class DatasetEvaluationSummary:
    """Sinteză statistică globală pe întregul dataset evaluat."""
    timestamp: str
    crs: str
    elapsed_time_s: float
    min_iou_match: float
    total_references: int
    total_predictions: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    # Clasificare topologică a segmentării
    matching_1_to_1_count: int
    oversegmented_count: int
    undersegmented_count: int
    suspect_unmapped_merge_count: int = 0
    # Acoperire spațială & Analiză Common AOI
    common_aoi_area_ha: float = 0.0
    refs_in_aoi_count: int = 0
    refs_outside_aoi_count: int = 0
    precision_aoi: float = 0.0
    recall_aoi: float = 0.0
    f1_score_aoi: float = 0.0
    # Profiling tehnic al motorului
    spatial_filter_time_ms: float = 0.0
    detailed_metrics_time_ms: float = 0.0
    # Indicatori statistici agregați global (toate perechile asociate)
    mean_iou: float = 0.0
    median_iou: float = 0.0
    std_iou: float = 0.0
    ci95_iou: List[float] = field(default_factory=lambda: [0.0, 0.0])
    p25_iou: float = 0.0
    p75_iou: float = 0.0
    mean_hausdorff_m: float = 0.0
    median_hausdorff_m: float = 0.0
    std_hausdorff_m: float = 0.0
    ci95_hausdorff_m: List[float] = field(default_factory=lambda: [0.0, 0.0])
    mean_boundary_rmse_m: float = 0.0
    median_boundary_rmse_m: float = 0.0
    std_boundary_rmse_m: float = 0.0
    ci95_boundary_rmse_m: List[float] = field(default_factory=lambda: [0.0, 0.0])
    mean_centroid_disp_m: float = 0.0
    mean_abs_area_error_pct: float = 0.0
    median_abs_area_error_pct: float = 0.0
    # Indicatori statistici exclusiv pe subsetul curat 1:1 (fără split/merge/asimetrii)
    clean_1_to_1_count: int = 0
    clean_mean_iou: float = 0.0
    clean_median_iou: float = 0.0
    clean_std_iou: float = 0.0
    clean_ci95_iou: List[float] = field(default_factory=lambda: [0.0, 0.0])
    clean_mean_boundary_rmse_m: float = 0.0
    clean_median_boundary_rmse_m: float = 0.0
    clean_std_boundary_rmse_m: float = 0.0
    clean_ci95_boundary_rmse_m: List[float] = field(default_factory=lambda: [0.0, 0.0])
    clean_mean_hausdorff_m: float = 0.0
    clean_median_hausdorff_m: float = 0.0
    clean_std_hausdorff_m: float = 0.0
    clean_ci95_hausdorff_m: List[float] = field(default_factory=lambda: [0.0, 0.0])
    # Raport conformitate porți de calitate internă
    ancpi_conform_count: int = 0
    pug_acceptable_count: int = 0
    rejected_count: int = 0
    ancpi_compliance_rate_pct: float = 0.0
    pug_compliance_rate_pct: float = 0.0
    building_results: List[BuildingEvaluationResult] = field(default_factory=list)


def compute_ci95(values: List[float]) -> List[float]:
    """
    Calculează intervalul de încredere 95% pentru o serie de măsurători continue
    folosind distribuția Student-t cu (n - 1) grade de libertate.
    """
    n = len(values)
    if n < 2:
        val = round(float(values[0]), 3) if n == 1 else 0.0
        return [val, val]
    mean = float(np.mean(values))
    std = float(np.std(values, ddof=1))
    if std == 0.0 or math.isnan(std):
        return [round(mean, 3), round(mean, 3)]
    sem = std / math.sqrt(n)
    try:
        t_crit = float(scipy.stats.t.ppf(0.975, df=n - 1))
    except Exception:
        t_table = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}
        t_crit = t_table.get(n - 1, 1.960 if n > 30 else 2.1)
    margin = t_crit * sem
    return [round(max(0.0, mean - margin), 3), round(mean + margin, 3)]


# =====================================================================
# 2. METRICI MATEMATICE FUNDAMENTALE
# =====================================================================

def ensure_valid_polygon(geom) -> Optional[Polygon]:
    """Validează și convertește geometria într-un poligon valid unic."""
    if geom is None or geom.is_empty:
        return None
    if not geom.is_valid:
        geom = make_valid(geom)
    if geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        valid_subs = [p for p in geom.geoms if isinstance(p, Polygon) and p.area > 1.0]
        if valid_subs:
            return max(valid_subs, key=lambda p: p.area)
    return None


def compute_iou(geom_pred: Polygon, geom_ref: Polygon) -> float:
    """
    Calculează Intersection-over-Union (Indicele Jaccard).
    IoU = Area(P ∩ R) / Area(P ∪ R)
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return 0.0
    try:
        inter = geom_pred.intersection(geom_ref).area
        union = geom_pred.union(geom_ref).area
        if union <= 1e-9:
            return 0.0
        return float(np.clip(inter / union, 0.0, 1.0))
    except Exception:
        return 0.0


def compute_hausdorff(geom_pred: Polygon, geom_ref: Polygon, densify: float = 0.10) -> float:
    """
    Calculează distanța Hausdorff bidirecțională cu densificare continuă a laturilor.
    d_H(P, R) = max( sup_{x∈P} inf_{y∈R} ||x - y||, sup_{y∈R} inf_{x∈P} ||x - y|| )
    
    Notă metodologică privind pasul de densificare (densify=0.10 m):
      Muchia este eșantionată la fracțiuni de 10 cm prin nucleul GEOS C++ (Shapely 2.0).
      Deformările sau ondulațiile geometrice cu lungime de undă sub 10 cm sunt filtrate
      de pasul de eșantionare, oferind o evaluare robustă anti-zgomot.
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return float("inf")
    try:
        return float(shapely.hausdorff_distance(geom_pred, geom_ref, densify=densify))
    except Exception:
        return float(shapely.hausdorff_distance(geom_pred, geom_ref))


def sample_points_along_boundary(poly, step_m: float = 0.20) -> List[Tuple[float, float]]:
    """Eșantionează noduri de-a lungul perimetrului exterior la pas regulat (suportă Polygon și MultiPolygon)."""
    if poly is None or poly.is_empty:
        return []
    
    geoms = poly.geoms if hasattr(poly, "geoms") else [poly]
    pts = []
    for g in geoms:
        if not hasattr(g, "exterior") or g.exterior is None:
            continue
        boundary = g.exterior
        length = boundary.length
        if length <= 0:
            continue
        num_samples = max(4, int(math.ceil(length / step_m)))
        distances = np.linspace(0, length, num_samples, endpoint=False)
        for d in distances:
            pt = boundary.interpolate(d)
            pts.append((pt.x, pt.y))
    return pts


def compute_boundary_rmse(geom_pred, geom_ref, sample_step_m: float = 0.20) -> float:
    """
    Calculează Boundary RMSE bidirecțional simetric prin eșantionare continuă:
    RMSE = sqrt( 1/(N_p + N_r) * ( Σ dist(p_i, ∂R)^2 + Σ dist(r_j, ∂P)^2 ) )
    Suportă atât corpuri unitare (Polygon), cât și complexe multipart (MultiPolygon).
    """
    if geom_pred is None or geom_ref is None or geom_pred.is_empty or geom_ref.is_empty:
        return float("inf")

    pred_pts = sample_points_along_boundary(geom_pred, sample_step_m)
    ref_pts = sample_points_along_boundary(geom_ref, sample_step_m)

    if not pred_pts or not ref_pts:
        return float("inf")

    ref_boundary = geom_ref.boundary
    pred_boundary = geom_pred.boundary

    sq_errors = []
    for px, py in pred_pts:
        d = ref_boundary.distance(Point(px, py))
        sq_errors.append(d ** 2)

    for rx, ry in ref_pts:
        d = pred_boundary.distance(Point(rx, ry))
        sq_errors.append(d ** 2)

    return float(math.sqrt(sum(sq_errors) / len(sq_errors)))


def compute_angular_deviation(poly: Polygon) -> float:
    """
    Măsoară deviația unghiulară medie a laturilor față de unghiuri drepte (90° / 180° / 270°).
    Deviație = (1/N) * Σ |(unghi mod 90°)|
    O valoare de 0.0° înseamnă ortogonalitate geometrică perfectă Manhattan.
    """
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 3:
        return 0.0

    deviations = []
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])

        v1 = p_prev - p_curr
        v2 = p_next - p_curr
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 > 0.1 and norm2 > 0.1:
            cos_a = np.dot(v1, v2) / (norm1 * norm2)
            angle_deg = np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))
            # Cât deviază unghiul față de cel mai apropiat multiplu de 90°
            rem = angle_deg % 90.0
            dev = min(rem, 90.0 - rem)
            deviations.append(dev)

    return float(np.mean(deviations)) if deviations else 0.0


def compute_shape_metrics(geom_pred: Polygon, geom_ref: Polygon) -> Dict[str, float]:
    """Calculează setul complet de indicatori de formă și dislocare spațială."""
    area_p = round(float(geom_pred.area), 2)
    area_r = round(float(geom_ref.area), 2)
    perim_p = round(float(geom_pred.length), 2)
    perim_r = round(float(geom_ref.length), 2)

    area_err_m2 = round(area_p - area_r, 2)
    area_err_pct = round((area_err_m2 / area_r * 100.0), 2) if area_r > 0 else 0.0

    c_pred = geom_pred.centroid
    c_ref = geom_ref.centroid
    centroid_disp = round(float(c_pred.distance(c_ref)), 3)
    angle_dev = round(compute_angular_deviation(geom_pred), 2)

    return {
        "area_ref_m2": area_r,
        "area_pred_m2": area_p,
        "area_error_m2": area_err_m2,
        "area_error_pct": area_err_pct,
        "perimeter_ref_m": perim_r,
        "perimeter_pred_m": perim_p,
        "centroid_disp_m": centroid_disp,
        "mean_angle_dev_deg": angle_dev
    }


# =====================================================================
# 3. GENERATOR DE VIZUALIZARE SVG EMBEDDED
# =====================================================================

def generate_building_svg(geom_pred: Polygon, geom_ref: Polygon, width: int = 240, height: int = 200) -> str:
    """Generează un fragment SVG autonom care suprapune Referința și Predicția."""
    try:
        combined_bounds = unary_union([geom_pred, geom_ref]).bounds
        minx, miny, maxx, maxy = combined_bounds
        dx = maxx - minx
        dy = maxy - miny
        
        # Păstrăm proporțiile cu o margine (padding) de 15%
        pad = max(dx, dy) * 0.15
        minx -= pad
        maxx += pad
        miny -= pad
        maxy += pad
        dx = maxx - minx
        dy = maxy - miny

        if dx <= 0 or dy <= 0:
            return ""

        def to_svg_coords(coords):
            pts = []
            for x, y in coords:
                sx = ((x - minx) / dx) * (width - 20) + 10
                sy = (height - 20) - ((y - miny) / dy) * (height - 20) + 10
                pts.append(f"{sx:.1f},{sy:.1f}")
            return " ".join(pts)

        ref_svg_pts = to_svg_coords(list(geom_ref.exterior.coords))
        pred_svg_pts = to_svg_coords(list(geom_pred.exterior.coords))

        svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" class="bldg-svg">
  <rect width="100%" height="100%" fill="#1a1d24" rx="6"/>
  <!-- Referinta Ground Truth (Albastru) -->
  <polygon points="{ref_svg_pts}" fill="rgba(33, 150, 243, 0.25)" stroke="#2196F3" stroke-width="2" stroke-dasharray="3,2"/>
  <!-- Predictie AI Hibrid (Portocaliu) -->
  <polygon points="{pred_svg_pts}" fill="rgba(255, 87, 34, 0.3)" stroke="#FF5722" stroke-width="2"/>
</svg>"""
        return svg
    except Exception:
        return ""


# =====================================================================
# 4. MOTORUL DE EVALUARE PE DATASET
# =====================================================================

def evaluate_dataset(
    gdf_pred: gpd.GeoDataFrame,
    gdf_ref: gpd.GeoDataFrame,
    config: Optional[Dict[str, Any]] = None,
    min_iou_match: Optional[float] = None
) -> DatasetEvaluationSummary:
    """
    Evaluează setul de predicții împotriva setului de referință (Ground Truth).
    Realizează asocierea spațială 1:1, identifică supra/sub-segmentarea și
    clasifică fiecare corp de clădire conform toleranțelor ANCPI și PUG.
    """
    t0 = time.time()
    if config is None:
        config = {}

    eval_cfg = config.get("evaluation", {})
    matching_iou_min = min_iou_match if min_iou_match is not None else eval_cfg.get("matching_iou_min", 0.30)
    hausdorff_densify = eval_cfg.get("hausdorff_densify_step_m", 0.10)
    boundary_sample_step = eval_cfg.get("boundary_sample_step_m", 0.20)

    tols = eval_cfg.get("tolerances", {})
    ancpi_tol = tols.get("ancpi_cadastre", {"max_boundary_rmse_m": 0.10, "min_iou": 0.85, "max_area_error_pct": 5.0})
    pug_tol = tols.get("pug_urbanism", {"max_boundary_rmse_m": 0.30, "min_iou": 0.70, "max_area_error_pct": 10.0})

    # Forțare CRS Stereo 70
    target_crs = eval_cfg.get("crs", "EPSG:3844")
    if gdf_pred.crs is not None and str(gdf_pred.crs) != target_crs:
        gdf_pred = gdf_pred.to_crs(target_crs)
    if gdf_ref.crs is not None and str(gdf_ref.crs) != target_crs:
        gdf_ref = gdf_ref.to_crs(target_crs)

    # Determinare Arie Comună de Interes (Common AOI)
    box_pred = box(*gdf_pred.total_bounds) if len(gdf_pred) > 0 else box(0, 0, 0, 0)
    box_ref = box(*gdf_ref.total_bounds) if len(gdf_ref) > 0 else box(0, 0, 0, 0)
    common_aoi = box_pred.intersection(box_ref) if (len(gdf_pred) > 0 and len(gdf_ref) > 0) else box(0, 0, 0, 0)
    common_aoi_ha = round(float(common_aoi.area / 10000.0), 2) if not common_aoi.is_empty else 0.0

    # Validare geometrii
    valid_refs = []
    refs_in_aoi_count = 0
    refs_outside_aoi_count = 0
    for idx, row in gdf_ref.iterrows():
        p = ensure_valid_polygon(row.geometry)
        if p is not None and p.area >= 5.0:
            in_aoi = (not common_aoi.is_empty) and (p.intersects(common_aoi) or p.centroid.within(common_aoi))
            if in_aoi:
                refs_in_aoi_count += 1
            else:
                refs_outside_aoi_count += 1
            rid = str(row.get("id", row.get("id_cladire", f"REF_{idx+1:03d}")))
            valid_refs.append({"id": rid, "geometry": p, "row": row, "in_aoi": in_aoi})

    valid_preds = []
    for idx, row in gdf_pred.iterrows():
        p = ensure_valid_polygon(row.geometry)
        if p is not None and p.area >= 5.0:
            pid = str(row.get("id", row.get("cod_cladire", f"PRED_{idx+1:03d}")))
            valid_preds.append({"id": pid, "geometry": p, "row": row})

    # Analiză de topologie a segmentării (Matching Matrix) cu profiling
    t_start_spatial = time.perf_counter()
    pred_candidates_per_ref = {r_idx: [] for r_idx in range(len(valid_refs))}
    ref_candidates_per_pred = {p_idx: [] for p_idx in range(len(valid_preds))}

    for r_idx, ref in enumerate(valid_refs):
        r_geom = ref["geometry"]
        for p_idx, pred in enumerate(valid_preds):
            p_geom = pred["geometry"]
            if r_geom.intersects(p_geom):
                iou_val = compute_iou(p_geom, r_geom)
                inter_area = r_geom.intersection(p_geom).area
                if iou_val >= matching_iou_min or (inter_area >= 10.0 and iou_val >= 0.10):
                    pred_candidates_per_ref[r_idx].append((p_idx, iou_val, inter_area))
                    ref_candidates_per_pred[p_idx].append((r_idx, iou_val, inter_area))

    spatial_filter_time_ms = round((time.perf_counter() - t_start_spatial) * 1000.0, 2)

    oversegmented_count = sum(1 for r_idx, preds in pred_candidates_per_ref.items() if len(preds) > 1)
    undersegmented_count = sum(1 for p_idx, refs in ref_candidates_per_pred.items() if len(refs) > 1)
    matching_1_to_1_count = sum(
        1 for r_idx, preds in pred_candidates_per_ref.items()
        if len(preds) == 1 and len(ref_candidates_per_pred[preds[0][0]]) == 1 and preds[0][1] >= matching_iou_min
    )

    # Spatial matching & calcul metrici detaliate
    t_start_metrics = time.perf_counter()
    used_preds = set()
    building_results: List[BuildingEvaluationResult] = []
    suspect_unmapped_merge_count = 0

    for r_idx, ref in enumerate(valid_refs):
        r_id = ref["id"]
        r_geom = ref["geometry"]
        in_aoi = ref["in_aoi"]
        candidates = pred_candidates_per_ref[r_idx]

        if not candidates:
            # False Negative (Clădire de referință complet ratată sau în afara AOI)
            err_flags = ["FALSE_NEGATIVE_OUTSIDE_AOI"] if not in_aoi else ["FALSE_NEGATIVE_RATATA"]
            res = BuildingEvaluationResult(
                ref_id=r_id,
                pred_id="NONE (IN AFARA AOI)" if not in_aoi else "NONE (RATATA)",
                matched=False,
                area_ref_m2=round(float(r_geom.area), 2),
                compliance_tier="REJECT",
                error_flags=err_flags
            )
            building_results.append(res)
            continue

        # Sortare descrescătoare după IoU
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_p_idx, best_iou, best_inter_area = candidates[0]
        best_pred = valid_preds[best_p_idx]
        best_p_id = best_pred["id"]
        best_p_geom = best_pred["geometry"]
        used_preds.add(best_p_idx)

        error_flags = []
        if len(candidates) > 1:
            error_flags.append("SUPRA_SEGMENTARE_SPLIT")
        if len(ref_candidates_per_pred[best_p_idx]) > 1:
            error_flags.append("SUB_SEGMENTARE_MERGED")
        elif best_p_geom.area > 1.8 * r_geom.area and best_iou < matching_iou_min and (best_inter_area / r_geom.area) > 0.50:
            error_flags.append("SUSPECT_UNMAPPED_MERGE")
            suspect_unmapped_merge_count += 1

        # Calcul metrici geometrice detaliate
        h_dist = compute_hausdorff(best_p_geom, r_geom, densify=hausdorff_densify)
        b_rmse = compute_boundary_rmse(best_p_geom, r_geom, sample_step_m=boundary_sample_step)
        shape_stats = compute_shape_metrics(best_p_geom, r_geom)
        svg_preview = generate_building_svg(best_p_geom, r_geom)

        # Clasificare decizională
        is_ancpi = (
            b_rmse <= ancpi_tol["max_boundary_rmse_m"] and
            best_iou >= ancpi_tol["min_iou"] and
            abs(shape_stats["area_error_pct"]) <= ancpi_tol["max_area_error_pct"]
        )
        is_pug = (
            b_rmse <= pug_tol["max_boundary_rmse_m"] and
            best_iou >= pug_tol["min_iou"] and
            abs(shape_stats["area_error_pct"]) <= pug_tol["max_area_error_pct"]
        )

        if is_ancpi:
            tier = "CONFORM_ANCPI"
        elif is_pug:
            tier = "ACCEPTABIL_PUG"
        else:
            tier = "REJECT"
            if b_rmse > pug_tol["max_boundary_rmse_m"]:
                error_flags.append("ERORE_CONTUR_MARE")
            if abs(shape_stats["area_error_pct"]) > pug_tol["max_area_error_pct"]:
                error_flags.append("ERORE_ARIE_MARE")

        res = BuildingEvaluationResult(
            ref_id=r_id,
            pred_id=best_p_id,
            matched=True,
            iou=round(best_iou, 4),
            hausdorff_m=round(h_dist, 3),
            boundary_rmse_m=round(b_rmse, 3),
            centroid_disp_m=shape_stats["centroid_disp_m"],
            area_ref_m2=shape_stats["area_ref_m2"],
            area_pred_m2=shape_stats["area_pred_m2"],
            area_error_m2=shape_stats["area_error_m2"],
            area_error_pct=shape_stats["area_error_pct"],
            perimeter_ref_m=shape_stats["perimeter_ref_m"],
            perimeter_pred_m=shape_stats["perimeter_pred_m"],
            mean_angle_dev_deg=shape_stats["mean_angle_dev_deg"],
            compliance_tier=tier,
            error_flags=error_flags,
            svg_data=svg_preview
        )
        building_results.append(res)

    detailed_metrics_time_ms = round((time.perf_counter() - t_start_metrics) * 1000.0, 2)

    # Identificare False Positives (Predicții fără referință corespondentă)
    unmatched_preds_count = 0
    for p_idx, pred in enumerate(valid_preds):
        if p_idx not in used_preds:
            unmatched_preds_count += 1
            p_geom = pred["geometry"]
            res = BuildingEvaluationResult(
                ref_id="NONE (ARTEFACT)",
                pred_id=pred["id"],
                matched=False,
                area_pred_m2=round(float(p_geom.area), 2),
                compliance_tier="REJECT",
                error_flags=["FALSE_POSITIVE_ARTEFACT"]
            )
            building_results.append(res)

    # Agregare metrici globale și detecție
    tp = sum(1 for r in building_results if r.matched and r.iou >= matching_iou_min)
    fn = sum(1 for r in building_results if not r.matched and not r.ref_id.startswith("NONE"))
    fp = unmatched_preds_count

    precision = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
    recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
    f1 = round(2 * precision * recall / (precision + recall), 4) if (precision + recall) > 0 else 0.0

    # Metrici calculate doar în cadrul Common AOI
    fn_aoi = sum(1 for r in building_results if not r.matched and "FALSE_NEGATIVE_RATATA" in r.error_flags)
    precision_aoi = precision
    recall_aoi = round(tp / (tp + fn_aoi), 4) if (tp + fn_aoi) > 0 else 0.0
    f1_aoi = round(2 * precision_aoi * recall_aoi / (precision_aoi + recall_aoi), 4) if (precision_aoi + recall_aoi) > 0 else 0.0

    # Dispersie statistică globală (toate perechile asociate)
    matched_results = [r for r in building_results if r.matched]
    ious = [r.iou for r in matched_results]
    rmses = [r.boundary_rmse_m for r in matched_results]
    haus = [r.hausdorff_m for r in matched_results]
    disps = [r.centroid_disp_m for r in matched_results]
    area_errs = [abs(r.area_error_pct) for r in matched_results]

    mean_iou = round(float(np.mean(ious)), 4) if ious else 0.0
    median_iou = round(float(np.median(ious)), 4) if ious else 0.0
    std_iou = round(float(np.std(ious, ddof=1)), 4) if len(ious) > 1 else 0.0
    ci95_iou = compute_ci95(ious)
    p25_iou = round(float(np.percentile(ious, 25)), 4) if ious else 0.0
    p75_iou = round(float(np.percentile(ious, 75)), 4) if ious else 0.0

    mean_h = round(float(np.mean(haus)), 3) if haus else 0.0
    median_h = round(float(np.median(haus)), 3) if haus else 0.0
    std_h = round(float(np.std(haus, ddof=1)), 3) if len(haus) > 1 else 0.0
    ci95_h = compute_ci95(haus)

    mean_rmse = round(float(np.mean(rmses)), 3) if rmses else 0.0
    median_rmse = round(float(np.median(rmses)), 3) if rmses else 0.0
    std_rmse = round(float(np.std(rmses, ddof=1)), 3) if len(rmses) > 1 else 0.0
    ci95_rmse = compute_ci95(rmses)

    mean_disp = round(float(np.mean(disps)), 3) if disps else 0.0
    mean_area_err = round(float(np.mean(area_errs)), 2) if area_errs else 0.0
    median_area_err = round(float(np.median(area_errs)), 2) if area_errs else 0.0

    # Indicatori statistici exclusiv pe subsetul curat 1:1 (fără anomalii de split/merge/asimetrie)
    clean_results = [
        r for r in building_results
        if r.matched and r.iou >= matching_iou_min and not (
            "SUPRA_SEGMENTARE_SPLIT" in r.error_flags or
            "SUB_SEGMENTARE_MERGED" in r.error_flags or
            "SUSPECT_UNMAPPED_MERGE" in r.error_flags
        )
    ]
    clean_ious = [r.iou for r in clean_results]
    clean_rmses = [r.boundary_rmse_m for r in clean_results]
    clean_haus = [r.hausdorff_m for r in clean_results]

    clean_1_to_1_count = len(clean_results)
    clean_mean_iou = round(float(np.mean(clean_ious)), 4) if clean_ious else 0.0
    clean_med_iou = round(float(np.median(clean_ious)), 4) if clean_ious else 0.0
    clean_std_iou = round(float(np.std(clean_ious, ddof=1)), 4) if len(clean_ious) > 1 else 0.0
    clean_ci_iou = compute_ci95(clean_ious)

    clean_mean_rmse = round(float(np.mean(clean_rmses)), 3) if clean_rmses else 0.0
    clean_med_rmse = round(float(np.median(clean_rmses)), 3) if clean_rmses else 0.0
    clean_std_rmse = round(float(np.std(clean_rmses, ddof=1)), 3) if len(clean_rmses) > 1 else 0.0
    clean_ci_rmse = compute_ci95(clean_rmses)

    clean_mean_h = round(float(np.mean(clean_haus)), 3) if clean_haus else 0.0
    clean_med_h = round(float(np.median(clean_haus)), 3) if clean_haus else 0.0
    clean_std_h = round(float(np.std(clean_haus, ddof=1)), 3) if len(clean_haus) > 1 else 0.0
    clean_ci_h = compute_ci95(clean_haus)

    ancpi_count = sum(1 for r in building_results if r.compliance_tier == "CONFORM_ANCPI")
    pug_count = sum(1 for r in building_results if r.compliance_tier == "ACCEPTABIL_PUG")
    reject_count = sum(1 for r in building_results if r.compliance_tier == "REJECT")

    tot_refs = len(valid_refs)
    ancpi_rate = round((ancpi_count / tot_refs * 100.0), 1) if tot_refs > 0 else 0.0
    pug_rate = round(((ancpi_count + pug_count) / tot_refs * 100.0), 1) if tot_refs > 0 else 0.0
    elapsed_time = round(time.time() - t0, 3)

    return DatasetEvaluationSummary(
        timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        crs=target_crs,
        elapsed_time_s=elapsed_time,
        min_iou_match=matching_iou_min,
        total_references=tot_refs,
        total_predictions=len(valid_preds),
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1_score=f1,
        matching_1_to_1_count=matching_1_to_1_count,
        oversegmented_count=oversegmented_count,
        undersegmented_count=undersegmented_count,
        suspect_unmapped_merge_count=suspect_unmapped_merge_count,
        common_aoi_area_ha=common_aoi_ha,
        refs_in_aoi_count=refs_in_aoi_count,
        refs_outside_aoi_count=refs_outside_aoi_count,
        precision_aoi=precision_aoi,
        recall_aoi=recall_aoi,
        f1_score_aoi=f1_aoi,
        spatial_filter_time_ms=spatial_filter_time_ms,
        detailed_metrics_time_ms=detailed_metrics_time_ms,
        mean_iou=mean_iou,
        median_iou=median_iou,
        std_iou=std_iou,
        ci95_iou=ci95_iou,
        p25_iou=p25_iou,
        p75_iou=p75_iou,
        mean_hausdorff_m=mean_h,
        median_hausdorff_m=median_h,
        std_hausdorff_m=std_h,
        ci95_hausdorff_m=ci95_h,
        mean_boundary_rmse_m=mean_rmse,
        median_boundary_rmse_m=median_rmse,
        std_boundary_rmse_m=std_rmse,
        ci95_boundary_rmse_m=ci95_rmse,
        mean_centroid_disp_m=mean_disp,
        mean_abs_area_error_pct=mean_area_err,
        median_abs_area_error_pct=median_area_err,
        clean_1_to_1_count=clean_1_to_1_count,
        clean_mean_iou=clean_mean_iou,
        clean_median_iou=clean_med_iou,
        clean_std_iou=clean_std_iou,
        clean_ci95_iou=clean_ci_iou,
        clean_mean_boundary_rmse_m=clean_mean_rmse,
        clean_median_boundary_rmse_m=clean_med_rmse,
        clean_std_boundary_rmse_m=clean_std_rmse,
        clean_ci95_boundary_rmse_m=clean_ci_rmse,
        clean_mean_hausdorff_m=clean_mean_h,
        clean_median_hausdorff_m=clean_med_h,
        clean_std_hausdorff_m=clean_std_h,
        clean_ci95_hausdorff_m=clean_ci_h,
        ancpi_conform_count=ancpi_count,
        pug_acceptable_count=pug_count,
        rejected_count=reject_count,
        ancpi_compliance_rate_pct=ancpi_rate,
        pug_compliance_rate_pct=pug_rate,
        building_results=building_results
    )


# =====================================================================
# 5. GENERARE RAPOARTE (JSON, CSV, HTML VIZUAL)
# =====================================================================

def export_evaluation_reports(summary: DatasetEvaluationSummary, output_dir: str, prefix: str = "eval"):
    """Salvează raportul complet în formatele JSON, CSV și HTML vizual interactiv."""
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    # 1. Export JSON
    json_path = out_p / f"{prefix}_summary.json"
    data_dict = asdict(summary)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_dict, f, indent=2, ensure_ascii=False)

    # 2. Export CSV
    csv_path = out_p / f"{prefix}_buildings.csv"
    with open(csv_path, "w", encoding="utf-8") as f:
        headers = [
            "ref_id", "pred_id", "matched", "iou", "boundary_rmse_m", "hausdorff_m",
            "centroid_disp_m", "area_ref_m2", "area_pred_m2", "area_error_m2",
            "area_error_pct", "perimeter_ref_m", "perimeter_pred_m",
            "mean_angle_dev_deg", "compliance_tier", "error_flags"
        ]
        f.write(",".join(headers) + "\n")
        for b in summary.building_results:
            flags = ";".join(b.error_flags) if b.error_flags else "NONE"
            row = [
                b.ref_id, b.pred_id, str(b.matched), f"{b.iou:.4f}",
                f"{b.boundary_rmse_m:.3f}", f"{b.hausdorff_m:.3f}", f"{b.centroid_disp_m:.3f}",
                f"{b.area_ref_m2:.2f}", f"{b.area_pred_m2:.2f}", f"{b.area_error_m2:.2f}",
                f"{b.area_error_pct:.2f}", f"{b.perimeter_ref_m:.2f}", f"{b.perimeter_pred_m:.2f}",
                f"{b.mean_angle_dev_deg:.2f}", b.compliance_tier, f'"{flags}"'
            ]
            f.write(",".join(row) + "\n")

    # 3. Export HTML Vizual Standalone
    html_path = out_p / f"{prefix}_report.html"
    html_content = generate_html_report(summary)
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"\n[+] Rapoarte de evaluare generate cu succes în: {output_dir}")
    print(f"    - JSON: {json_path.name}")
    print(f"    - CSV:  {csv_path.name}")
    print(f"    - HTML: {html_path.name} (Deschideți în browser pentru inspecție vizuală)")


def generate_html_report(summary: DatasetEvaluationSummary) -> str:
    """Construiește un raport HTML complet autonom, stilat pentru analiză de precizie cadastrală."""
    cards_html = []
    for b in summary.building_results:
        tier_class = "badge-ancpi" if b.compliance_tier == "CONFORM_ANCPI" else (
            "badge-pug" if b.compliance_tier == "ACCEPTABIL_PUG" else "badge-reject"
        )
        flags_html = " ".join(f'<span class="flag-tag">{f}</span>' for f in b.error_flags) if b.error_flags else '<span class="flag-clean">Fără anomalii</span>'
        svg_box = b.svg_data if b.svg_data else '<div class="no-svg">Fără geometrie pereche</div>'

        card = f"""
        <div class="card">
          <div class="card-header">
            <div>
              <span class="ref-title">{b.ref_id}</span>
              <span class="pred-title">vs {b.pred_id}</span>
            </div>
            <span class="badge {tier_class}">{b.compliance_tier}</span>
          </div>
          <div class="card-body">
            <div class="svg-container">
              {svg_box}
            </div>
            <div class="metrics-grid">
              <div class="metric-item">
                <span class="m-label">IoU</span>
                <span class="m-val">{b.iou:.3f}</span>
              </div>
              <div class="metric-item">
                <span class="m-label">Boundary RMSE</span>
                <span class="m-val">{b.boundary_rmse_m:.3f} m</span>
              </div>
              <div class="metric-item">
                <span class="m-label">Hausdorff</span>
                <span class="m-val">{b.hausdorff_m:.3f} m</span>
              </div>
              <div class="metric-item">
                <span class="m-label">Dislocare Centroid</span>
                <span class="m-val">{b.centroid_disp_m:.3f} m</span>
              </div>
              <div class="metric-item">
                <span class="m-label">Arie Ref / Pred</span>
                <span class="m-val">{b.area_ref_m2:.1f} / {b.area_pred_m2:.1f} m²</span>
              </div>
              <div class="metric-item">
                <span class="m-label">Eroare Arie</span>
                <span class="m-val">{b.area_error_pct:+.1f} %</span>
              </div>
            </div>
            <div class="flags-box">
              {flags_html}
            </div>
          </div>
        </div>
        """
        cards_html.append(card)

    cards_block = "\n".join(cards_html)

    html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
  <meta charset="UTF-8">
  <title>StratumRO — Raport de Validare Geodezică & Urbanistică</title>
  <style>
    :root {{
      --bg: #0f1117;
      --card-bg: #181b22;
      --border: #282d37;
      --text: #e1e4ea;
      --text-muted: #8b949e;
      --accent-blue: #2196F3;
      --accent-green: #4CAF50;
      --accent-orange: #FF9800;
      --accent-red: #F44336;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 24px;
    }}
    .header-panel {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 20px 24px;
      margin-bottom: 24px;
    }}
    h1 {{ margin: 0 0 8px 0; font-size: 24px; font-weight: 600; }}
    .subtitle {{ color: var(--text-muted); font-size: 14px; }}
    .stats-dashboard {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }}
    .stat-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      text-align: center;
    }}
    .stat-val {{ font-size: 24px; font-weight: 700; margin: 4px 0; }}
    .stat-label {{ font-size: 12px; color: var(--text-muted); text-transform: uppercase; }}
    .legend-bar {{
      display: flex;
      gap: 16px;
      margin-bottom: 24px;
      align-items: center;
      background: var(--card-bg);
      padding: 12px 20px;
      border-radius: 6px;
      border: 1px solid var(--border);
      font-size: 13px;
    }}
    .legend-item {{ display: flex; align-items: center; gap: 8px; }}
    .legend-color {{ width: 14px; height: 14px; border-radius: 3px; }}
    .cards-container {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 20px;
    }}
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }}
    .card-header {{
      background: #1f232b;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
    }}
    .ref-title {{ font-weight: 700; font-size: 15px; }}
    .pred-title {{ color: var(--text-muted); font-size: 13px; margin-left: 6px; }}
    .badge {{
      font-size: 11px;
      font-weight: 700;
      padding: 4px 8px;
      border-radius: 4px;
      letter-spacing: 0.5px;
    }}
    .badge-ancpi {{ background: rgba(76, 175, 80, 0.2); color: #4CAF50; border: 1px solid #4CAF50; }}
    .badge-pug {{ background: rgba(255, 152, 0, 0.2); color: #FF9800; border: 1px solid #FF9800; }}
    .badge-reject {{ background: rgba(244, 67, 54, 0.2); color: #F44336; border: 1px solid #F44336; }}
    .card-body {{ padding: 16px; flex-grow: 1; display: flex; flex-direction: column; gap: 12px; }}
    .svg-container {{
      display: flex;
      justify-content: center;
      align-items: center;
      background: #121419;
      border-radius: 6px;
      padding: 8px;
    }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      font-size: 13px;
    }}
    .metric-item {{
      display: flex;
      justify-content: space-between;
      background: #14161d;
      padding: 6px 10px;
      border-radius: 4px;
    }}
    .m-label {{ color: var(--text-muted); }}
    .m-val {{ font-weight: 600; }}
    .flags-box {{ margin-top: auto; padding-top: 8px; }}
    .flag-tag {{
      background: rgba(244, 67, 54, 0.15);
      color: #ff8a80;
      font-size: 11px;
      padding: 2px 6px;
      border-radius: 3px;
      margin-right: 4px;
    }}
    .flag-clean {{ font-size: 11px; color: var(--text-muted); }}
  </style>
</head>
<body>
  <div class="header-panel">
    <h1>🏛️ StratumRO — Raport de Validare Geodezică & Urbanism</h1>
    <div class="subtitle">
      Generat la: {summary.timestamp} | Proiecție: {summary.crs} | Eșantioane evaluate: {summary.total_references} clădiri
    </div>
  </div>

  <div class="stats-dashboard">
    <div class="stat-card">
      <div class="stat-label">Poartă Internă Tier A (≤10cm)</div>
      <div class="stat-val" style="color: #4CAF50;">{summary.ancpi_compliance_rate_pct}%</div>
      <div class="subtitle">{summary.ancpi_conform_count} din {summary.total_references} clădiri</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Poartă Internă Tier B (≤30cm)</div>
      <div class="stat-val" style="color: #FF9800;">{summary.pug_compliance_rate_pct}%</div>
      <div class="subtitle">{summary.ancpi_conform_count + summary.pug_acceptable_count} acceptabile</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Subset 1:1 Curat (IoU)</div>
      <div class="stat-val">{summary.clean_mean_iou:.3f}</div>
      <div class="subtitle">95% CI: [{summary.clean_ci95_iou[0]:.2f}, {summary.clean_ci95_iou[1]:.2f}]</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Subset 1:1 Boundary RMSE</div>
      <div class="stat-val">{summary.clean_mean_boundary_rmse_m:.3f} m</div>
      <div class="subtitle">95% CI: [{summary.clean_ci95_boundary_rmse_m[0]:.2f}m, {summary.clean_ci95_boundary_rmse_m[1]:.2f}m]</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Subset 1:1 Hausdorff</div>
      <div class="stat-val">{summary.clean_mean_hausdorff_m:.3f} m</div>
      <div class="subtitle">95% CI: [{summary.clean_ci95_hausdorff_m[0]:.2f}m, {summary.clean_ci95_hausdorff_m[1]:.2f}m]</div>
    </div>
    <div class="stat-card">
      <div class="stat-label">Detecție în Common AOI</div>
      <div class="stat-val">{summary.f1_score_aoi:.2f}</div>
      <div class="subtitle">P: {summary.precision_aoi:.2f} | R: {summary.recall_aoi:.2f}</div>
    </div>
  </div>

  <div class="legend-bar">
    <span style="font-weight: 600;">Legendă Grafică:</span>
    <div class="legend-item">
      <div class="legend-color" style="background: #2196F3; border: 1px dashed #fff;"></div>
      <span>Referință Ground Truth (Albastru)</span>
    </div>
    <div class="legend-item">
      <div class="legend-color" style="background: #FF5722;"></div>
      <span>Predicție AI Hibrid (Portocaliu)</span>
    </div>
    <div class="legend-item" style="margin-left: auto;">
      <span style="color: var(--text-muted);">Standarde: ANCPI Ord. 600/2023 & MDLPA Ord. 904/2023</span>
    </div>
  </div>

  <div class="cards-container">
    {cards_block}
  </div>
</body>
</html>
"""
    return html


# =====================================================================
# 6. INTERFAȚĂ ÎN LINIA DE COMANDĂ (CLI)
# =====================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="StratumRO Evaluation Engine: Verificare precizie geometrică Stereo 70 (EPSG:3844)."
    )
    parser.add_argument("-r", "--reference", required=True, help="Cale fișier Ground Truth (GeoPackage / GeoJSON / Shapefile)")
    parser.add_argument("-p", "--prediction", required=True, help="Cale fișier Predicție AI (GeoPackage / GeoJSON / Shapefile)")
    parser.add_argument("-o", "--output-dir", default="workspace/evaluation_results", help="Folder destinație pentru rapoarte")
    parser.add_argument("-c", "--config", default="config.yaml", help="Cale fișier config.yaml")
    parser.add_argument("--ref-layer", default=None, help="Nume layer pentru fișiere GPKG multi-layer de referință")
    parser.add_argument("--pred-layer", default=None, help="Nume layer pentru fișiere GPKG multi-layer de predicție")
    parser.add_argument("--min-iou-match", type=float, default=None, help="Prag minim IoU pentru împerechere validă (default: 0.30)")
    parser.add_argument("--prefix", default="eval", help="Prefix pentru fișierele de raport generate")
    return parser.parse_args()


def main():
    args = parse_args()
    print("=================================================================")
    print("  STRATUM-RO: NUCLEU DE EVALUARE & VALIDARE GEODEZICA CANTITATIVA")
    print("  Standarde: ANCPI Ordinul 600/2023 & MDLPA Ordinul 904/2023     ")
    print("=================================================================\n")

    # 1. Încărcare config
    cfg = {}
    if os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        print(f"[+] Configurație încărcată din: {args.config}")
    else:
        print(f"[-] Atenție: Fișierul de configurare {args.config} lipsește. Folosim valori implicite.")

    # 2. Încărcare date spațiale
    print(f"Încărcare Referință: {args.reference}")
    if args.ref_layer:
        gdf_ref = gpd.read_file(args.reference, layer=args.ref_layer)
    else:
        gdf_ref = gpd.read_file(args.reference)
    print(f"   -> {len(gdf_ref)} poligoane de referință încărcate.")

    print(f"Încărcare Predicție:  {args.prediction}")
    if args.pred_layer:
        gdf_pred = gpd.read_file(args.prediction, layer=args.pred_layer)
    else:
        gdf_pred = gpd.read_file(args.prediction)
    print(f"   -> {len(gdf_pred)} poligoane de predicție încărcate.")

    # 3. Rulare evaluare matematică
    summary = evaluate_dataset(gdf_pred, gdf_ref, cfg, min_iou_match=args.min_iou_match)

    # 4. Afișare sumar în consolă
    print("\n" + "=" * 75)
    print("               REZULTATE SUMAR EVALUARE GEOMETRICĂ")
    print("=" * 75)
    print("  [ANALIZĂ ACOPERIRE SPAȚIALĂ & COMMON AOI]")
    print(f"    - Arie Comună (AOI Intersection): {summary.common_aoi_area_ha:.1f} ha")
    print(f"    - Clădiri Referință (GT):          {summary.total_references} (în AOI: {summary.refs_in_aoi_count}, în afara AOI: {summary.refs_outside_aoi_count})")
    print(f"    - Clădiri Predicție (AI):          {summary.total_predictions}")
    print(f"    - Detecție în AOI (P / R / F1):    {summary.precision_aoi:.3f} / {summary.recall_aoi:.3f} / {summary.f1_score_aoi:.3f}")
    print(f"    - Detecție Globală (P / R / F1):   {summary.precision:.3f} / {summary.recall:.3f} / {summary.f1_score:.3f}")
    print("-" * 75)
    print("  [MATRICE CLASIFICARE TOPOLOGICĂ]")
    print(f"    - Împerecheri 1:1 curate:          {summary.clean_1_to_1_count}")
    print(f"    - Supra-segmentate (Split 1->2+):  {summary.oversegmented_count} clădiri de referință")
    print(f"    - Sub-segmentate (Merged 2+->1):   {summary.undersegmented_count} corpuri AI")
    print(f"    - Suspect Contopit Ne-digitizat:   {summary.suspect_unmapped_merge_count} corpuri (exces arie >180%)")
    print(f"    - Referințe ratate în AOI (FN):    {summary.false_negatives - summary.refs_outside_aoi_count}")
    print(f"    - Referințe în afara AOI:          {summary.refs_outside_aoi_count} (fără acoperire AI tile)")
    print(f"    - Predicții fără GT (FP):          {summary.false_positives} (clădiri nedigitizate în GT)")
    print("-" * 75)
    print("  [SUBSET ÎMPERECHERI CURATE 1:1 (FĂRĂ ANOMALII TOPOLOGICE)]")
    if summary.clean_1_to_1_count > 0:
        print(f"    - Eșantioane valide: {summary.clean_1_to_1_count} clădiri")
        print(f"    - IoU:           Medie={summary.clean_mean_iou:.3f} (±{summary.clean_std_iou:.3f}) | Mediană={summary.clean_median_iou:.3f} | 95% CI=[{summary.clean_ci95_iou[0]:.3f}, {summary.clean_ci95_iou[1]:.3f}]")
        print(f"    - Boundary RMSE: Medie={summary.clean_mean_boundary_rmse_m:.3f}m (±{summary.clean_std_boundary_rmse_m:.3f}m) | Mediană={summary.clean_median_boundary_rmse_m:.3f}m | 95% CI=[{summary.clean_ci95_boundary_rmse_m[0]:.3f}m, {summary.clean_ci95_boundary_rmse_m[1]:.3f}m]")
        print(f"    - Hausdorff:     Medie={summary.clean_mean_hausdorff_m:.3f}m (±{summary.clean_std_hausdorff_m:.3f}m) | Mediană={summary.clean_median_hausdorff_m:.3f}m | 95% CI=[{summary.clean_ci95_hausdorff_m[0]:.3f}m, {summary.clean_ci95_hausdorff_m[1]:.3f}m]")
    else:
        print("    - Nicio împerechere 1:1 fără anomalii.")
    print("-" * 75)
    print("  [DISPERSIE STATISTICĂ GLOBALĂ (INCLUSIV CORPURI SPLIT/MERGED)]")
    print(f"    - IoU Global:           Medie={summary.mean_iou:.3f} (±{summary.std_iou:.3f}) | Mediană={summary.median_iou:.3f} | 95% CI=[{summary.ci95_iou[0]:.3f}, {summary.ci95_iou[1]:.3f}]")
    print(f"    - Boundary RMSE Global: Medie={summary.mean_boundary_rmse_m:.3f}m (±{summary.std_boundary_rmse_m:.3f}m) | Mediană={summary.median_boundary_rmse_m:.3f}m | 95% CI=[{summary.ci95_boundary_rmse_m[0]:.3f}m, {summary.ci95_boundary_rmse_m[1]:.3f}m]")
    print(f"    - Hausdorff Global:     Medie={summary.mean_hausdorff_m:.3f}m (±{summary.std_hausdorff_m:.3f}m) | Mediană={summary.median_hausdorff_m:.3f}m | 95% CI=[{summary.ci95_hausdorff_m[0]:.3f}m, {summary.ci95_hausdorff_m[1]:.3f}m]")
    print(f"    - Dislocare Centroid:   Medie={summary.mean_centroid_disp_m:.3f}m")
    print(f"    - Eroare Arie Abs:      Medie={summary.mean_abs_area_error_pct:.1f}% | Mediană={summary.median_abs_area_error_pct:.1f}%")
    print("-" * 75)
    print("  [PORȚI INTERNE DE CALITATE]")
    print(f"    - Poartă Internă Tier A (Toleranță planimetrică <=10cm): {summary.ancpi_conform_count}/{summary.total_references} ({summary.ancpi_compliance_rate_pct:.1f}%)")
    print(f"    - Poartă Internă Tier B (Toleranță geometrică PUG <=30cm): {summary.ancpi_conform_count + summary.pug_acceptable_count}/{summary.total_references} ({summary.pug_compliance_rate_pct:.1f}%)")
    print(f"    - Respinse (Neconforme):                                 {summary.rejected_count}")
    print("-" * 75)
    print("  [PERFORMANȚĂ DE CALCUL & PROFILING]")
    print(f"    - Timp filtrare spațială (GEOS C++ BBox / Intersect): {summary.spatial_filter_time_ms:.2f} ms")
    print(f"    - Timp metrici detaliate (Hausdorff 10cm + RMSE):     {summary.detailed_metrics_time_ms:.2f} ms")
    print(f"    - Timp total de calcul:                              {summary.elapsed_time_s:.2f} s")
    print("=" * 75)

    # 5. Salvare rapoarte
    export_evaluation_reports(summary, args.output_dir, prefix=args.prefix)


if __name__ == "__main__":
    main()
