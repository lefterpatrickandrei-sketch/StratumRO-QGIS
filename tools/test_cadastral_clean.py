import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
import math
import numpy as np

def simplify_cadastral_polygon(poly: Polygon, tol: float = 0.8) -> Polygon:
    """
    Simplifies a building polygon to clean cadastral lines:
    1. Removes tiny sub-decimetric jitter.
    2. Snaps rectangular buildings to canonical 4-vertex OBB (90 degrees).
    3. Simplifies complex buildings, removing micro-notches and collinear vertices.
    """
    if poly is None or poly.is_empty or not poly.is_valid:
        if poly is not None:
            poly = make_valid(poly)
            if poly.geom_type == 'MultiPolygon':
                poly = max(poly.geoms, key=lambda g: g.area)
        if poly is None or poly.is_empty:
            return poly

    # 1. Pre-simplification with cadastral tolerance (e.g. 0.6m - 0.8m)
    simp = poly.simplify(tol, preserve_topology=True)
    if not simp.is_valid or simp.is_empty or simp.area < 5.0:
        simp = poly

    # 2. Check canonical rectangle (OBB - 4 vertices, 90 deg)
    mrr = simp.minimum_rotated_rectangle
    if mrr.area > 0 and simp.convex_hull.area > 0:
        solidity = simp.area / simp.convex_hull.area
        rect_ratio = simp.area / mrr.area
        if solidity >= 0.86 and rect_ratio >= 0.82:
            return mrr

    # 3. Collinear and micro-edge removal
    coords = list(simp.exterior.coords)[:-1]
    n = len(coords)
    if n > 4:
        clean_pts = []
        for i in range(n):
            p_prev = coords[(i - 1) % n]
            p_curr = coords[i]
            p_next = coords[(i + 1) % n]

            v1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
            v2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])
            d1 = math.hypot(v1[0], v1[1])
            d2 = math.hypot(v2[0], v2[1])

            # Eliminate micro-edges < 35 cm
            if d1 < 0.35 or d2 < 0.35:
                continue

            # Eliminate collinear vertices
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if abs(cross) / (d1 * d2 + 1e-6) < 0.08:
                continue

            clean_pts.append(p_curr)

        if len(clean_pts) >= 4:
            clean_pts.append(clean_pts[0])
            p_clean = Polygon(clean_pts)
            if p_clean.is_valid and p_clean.area >= 5.0:
                simp = p_clean

    return simp

# Test on GT buildings
gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')
print("Testing simplify_cadastral_polygon on GT 29 buildings:")
v_counts = []
rect_count = 0
for idx, row in gt.iterrows():
    p = row.geometry
    s = simplify_cadastral_polygon(p, tol=0.8)
    v = len(s.exterior.coords) - 1
    v_counts.append(v)
    if v == 4:
        rect_count += 1
    print(f"  {row.id}: orig_v={len(p.exterior.coords)-1} -> clean_v={v}, area={s.area:.1f}")

print(f"\nSummary:")
print(f"Total buildings: {len(gt)}")
print(f"Mean vertices: {np.mean(v_counts):.1f}")
print(f"Rectangles (4 vertices at 90 deg): {rect_count} ({rect_count/len(gt)*100:.1f}%)")
