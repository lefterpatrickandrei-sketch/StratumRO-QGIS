# -*- coding: utf-8 -*-
"""
StratumRO — Core Computational Geometry: Orthogonal Regularization (Phase 3)
Pure-Python, deterministic 90-degree orthogonalization and polygon cleanup.
Zero QGIS dependencies. Zero AI/LLM dependencies.
"""

import math
import numpy as np
from typing import Optional, List, Tuple
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.affinity import rotate

try:
    import geopandas as gpd
    from buildingregulariser import regularize_geodataframe
    HAS_REGULARISER = True
except ImportError:
    HAS_REGULARISER = False


def _extract_largest_polygon(geom) -> Optional[Polygon]:
    """Recursively extracts the largest valid Polygon from any geometry collection."""
    if geom is None or geom.is_empty:
        return None
    if isinstance(geom, Polygon):
        return geom
    if isinstance(geom, MultiPolygon):
        return max(geom.geoms, key=lambda g: g.area)
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, Polygon)]
        if polys:
            return max(polys, key=lambda g: g.area)
        for g in geom.geoms:
            sub = _extract_largest_polygon(g)
            if sub is not None:
                return sub
    return None


def remove_acute_spikes(poly: Polygon, min_angle_deg: float = 40.0) -> Polygon:
    """Elimină vârfurile anomale ascuțite (colți / horn-spikes) care ies nenatural din clădiri."""
    poly = _extract_largest_polygon(poly)
    if poly is None or not poly.is_valid or poly.is_empty:
        return poly

    coords = list(poly.exterior.coords)[:-1]
    if len(coords) <= 4:
        return poly

    changed = True
    max_iter = 4
    cur_iter = 0

    while changed and cur_iter < max_iter:
        changed = False
        cur_iter += 1
        n = len(coords)
        if n <= 4:
            break

        filtered = []
        i = 0
        while i < n:
            p_prev = np.array(coords[(i - 1) % n])
            p_curr = np.array(coords[i])
            p_next = np.array(coords[(i + 1) % n])

            v1 = p_prev - p_curr
            v2 = p_next - p_curr
            d1 = np.linalg.norm(v1)
            d2 = np.linalg.norm(v2)

            if d1 > 0.8 and d2 > 0.8:
                cos_a = np.dot(v1, v2) / (d1 * d2)
                angle_deg = np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))
                # Dacă unghiul interior/exterior e extrem de ascuțit (< 40 deg), e un colț parazit
                if angle_deg < min_angle_deg:
                    changed = True
                    i += 1
                    continue
            filtered.append(coords[i])
            i += 1
        coords = filtered

    if len(coords) >= 3:
        coords.append(coords[0])
        new_poly = Polygon(coords)
        if new_poly.is_valid and new_poly.area > 5.0:
            return new_poly
    return poly


def count_macro_reflex_corners(poly: Polygon, min_edge_len: float = 0.35, tol_deg: float = 20.0) -> int:
    """
    Numără unghiurile interioare apropiate de 270° (colțuri reflex/concave)
    formate de laturi cu lungimea >= min_edge_len.
    """
    if poly is None or poly.is_empty:
        return 0
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return 0
    count = 0
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        u = p_curr - p_prev
        v = p_next - p_curr
        d1 = np.linalg.norm(u)
        d2 = np.linalg.norm(v)
        if d1 < min_edge_len or d2 < min_edge_len:
            continue
        cross = u[0] * v[1] - u[1] * v[0]
        dot = u[0] * v[0] + u[1] * v[1]
        turning = math.atan2(cross, dot)
        interior = math.pi - turning
        int_deg = math.degrees(interior) % 360.0
        if abs(int_deg - 270.0) <= tol_deg:
            count += 1
    return count


def compute_orthogonality_ratio(poly: Polygon, min_edge_len: float = 0.20, tol_deg: float = 15.0) -> float:
    """
    Calculează fracțiunea de noduri cu unghiuri interioare de 90° sau 270° (+/- tol_deg).
    """
    if poly is None or poly.is_empty:
        return 0.0
    coords = list(poly.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return 0.0
    ortho_count = 0
    valid_corners = 0
    for i in range(n):
        p_prev = np.array(coords[(i - 1) % n])
        p_curr = np.array(coords[i])
        p_next = np.array(coords[(i + 1) % n])
        u = p_prev - p_curr
        v = p_next - p_curr
        d1 = np.linalg.norm(u)
        d2 = np.linalg.norm(v)
        if d1 < min_edge_len or d2 < min_edge_len:
            continue
        valid_corners += 1
        cos_a = np.clip(np.dot(u, v) / (d1 * d2 + 1e-9), -1.0, 1.0)
        deg = np.degrees(np.arccos(cos_a))
        if abs(deg - 90.0) <= tol_deg:
            ortho_count += 1
    return float(ortho_count / max(valid_corners, 1))


def orthogonalize_cad(poly: Polygon, tolerance: float = 0.7) -> Polygon:
    """
    Ortogonalizează conturul clădirii la unghiuri drepte de 90° folosind algoritmul
    bazat pe unghi dominant / drepte suport și buildingregulariser.
    Garantează unghiuri stricte de 90° fără teșituri diagonale de tip Douglas-Peucker.
    Protejează formele curbate autentice și decroșurile reale de fațadă (L, U, T).
    """
    if not poly.is_valid or poly.is_empty or poly.area < 6.0:
        return poly

    # 0. Dacă poligonul este deja ortogonal (>= 0.95) și are o complexitate rezonabilă, îl păstrăm neatins
    current_ortho = compute_orthogonality_ratio(poly, min_edge_len=0.20)
    if current_ortho >= 0.95 and len(poly.exterior.coords) <= 24:
        return poly

    # 1. Pre-curățare trepte de pixeli și colți ascuțiți
    clean_poly = remove_acute_spikes(poly, min_angle_deg=40.0)
    simp = clean_poly.simplify(0.20, preserve_topology=True)
    if not simp.is_valid or simp.is_empty or simp.area < 6.0:
        simp = clean_poly if clean_poly.is_valid else poly

    # 2. Gardă strictă pentru dreptunghi canonic OBB (4 noduri la 90°)
    # Acceptăm MRR DOAR dacă nu există decroșuri reflex macro și abaterea e minimă
    mrr = simp.minimum_rotated_rectangle
    if mrr.area > 0 and simp.convex_hull.area > 0:
        reflex_corners = count_macro_reflex_corners(simp, min_edge_len=0.60)
        h_dist_mrr = simp.hausdorff_distance(mrr)
        a_diff_mrr = abs(mrr.area - simp.area) / (simp.area + 1e-6)
        if reflex_corners == 0 and h_dist_mrr <= 0.50 and a_diff_mrr <= 0.04:
            return mrr

    # 3. Utilizare Building-Regulariser pe contururi complexe (L, U, T, decroșuri)
    if HAS_REGULARISER:
        for p_thresh in (0.5, 1.0, 1.5, 2.0):
            try:
                temp_gdf = gpd.GeoDataFrame([{"geometry": simp}], crs="EPSG:3844")
                reg_gdf = regularize_geodataframe(
                    temp_gdf,
                    allow_45_degree=False,
                    parallel_threshold=p_thresh,
                    num_cores=1
                )
                reg_poly = reg_gdf.geometry.iloc[0]
                if reg_poly is not None and reg_poly.is_valid and reg_poly.area >= 6.0:
                    o_r = compute_orthogonality_ratio(reg_poly)
                    h_r = simp.hausdorff_distance(reg_poly)
                    a_diff_r = abs(reg_poly.area - simp.area) / (simp.area + 1e-6)
                    if o_r >= 0.85 and a_diff_r <= 0.12 and h_r <= 1.50:
                        return reg_poly
            except Exception:
                pass

    # 4. Fallback ortogonal pe unghi dominant
    coords = list(simp.exterior.coords)[:-1]
    n = len(coords)
    if n < 4:
        return simp

    weighted_angles = []
    total_len = 0.0
    for i in range(n):
        p1 = coords[i]
        p2 = coords[(i + 1) % n]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.hypot(dx, dy)
        if length > 0.35:
            ang = math.degrees(math.atan2(dy, dx)) % 90.0
            weighted_angles.append((ang, length))
            total_len += length

    if not weighted_angles:
        return simp.simplify(0.35, preserve_topology=True)

    rad_angles = [math.radians(a * 4.0) for a, l in weighted_angles]
    weights = [l / total_len for a, l in weighted_angles]
    mean_sin = sum(w * math.sin(r) for w, r in zip(weights, rad_angles))
    mean_cos = sum(w * math.cos(r) for w, r in zip(weights, rad_angles))
    dom_angle = (math.degrees(math.atan2(mean_sin, mean_cos)) / 4.0) % 90.0

    origin = simp.centroid
    rot_poly = rotate(simp, -dom_angle, origin=origin)
    simp_rot = rot_poly.simplify(min(tolerance, 0.30), preserve_topology=True)
    if not simp_rot.is_valid:
        simp_rot = rot_poly

    ortho_poly = rotate(simp_rot, dom_angle, origin=origin)
    return ortho_poly if (ortho_poly.is_valid and ortho_poly.area > 5.0) else simp
