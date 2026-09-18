import geopandas as gpd
from shapely.geometry import Polygon
import math
import numpy as np

gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')
print("--- Analiza Geometrii Tier 1 Ground Truth (29 Cladiri) ---")

def simplify_cadastral(poly, tol=0.8):
    """Simplifies polygon removing micro-edges and collinear vertices."""
    # 1. Douglas-Peucker with cadastral tolerance
    p_simp = poly.simplify(tol, preserve_topology=True)
    if not p_simp.is_valid or p_simp.is_empty:
        p_simp = poly
    
    # 2. Minimum Rotated Rectangle check for rectangular buildings
    mrr = p_simp.minimum_rotated_rectangle
    if mrr.area > 0 and p_simp.convex_hull.area > 0:
        solidity = p_simp.area / p_simp.convex_hull.area
        rect_ratio = p_simp.area / mrr.area
        # If it's very close to a rectangle, fit canonical 4-vertex OBB
        if solidity >= 0.88 and rect_ratio >= 0.85:
            return mrr
    
    # 3. Collinear vertex removal
    coords = list(p_simp.exterior.coords)[:-1]
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
            
            if d1 < 0.3 or d2 < 0.3:
                continue
            
            cross = v1[0] * v2[1] - v1[1] * v2[0]
            if abs(cross) / (d1 * d2 + 1e-6) < 0.08:
                continue # Collinear
            clean_pts.append(p_curr)
        
        if len(clean_pts) >= 4:
            clean_pts.append(clean_pts[0])
            p_clean = Polygon(clean_pts)
            if p_clean.is_valid and p_clean.area > 5.0:
                p_simp = p_clean
                
    return p_simp

results = []
for idx, row in gt.iterrows():
    orig_p = row.geometry
    v_orig = len(orig_p.exterior.coords) - 1
    simp_p = simplify_cadastral(orig_p, tol=0.8)
    v_simp = len(simp_p.exterior.coords) - 1
    mrr = simp_p.minimum_rotated_rectangle
    sol = simp_p.area / simp_p.convex_hull.area
    rr = simp_p.area / mrr.area
    results.append({
        "id": row.id,
        "v_orig": v_orig,
        "v_simp": v_simp,
        "area": round(simp_p.area, 1),
        "solidity": round(sol, 3),
        "rect_ratio": round(rr, 3)
    })
    print(f"{row.id}: V orig={v_orig} -> V simp={v_simp}, area={simp_p.area:.1f} m2, sol={sol:.2f}, rr={rr:.2f}")

v_orig_all = [r["v_orig"] for r in results]
v_simp_all = [r["v_simp"] for r in results]
print(f"\nTotal: V orig mean = {np.mean(v_orig_all):.1f}, V simp mean = {np.mean(v_simp_all):.1f}")
print(f"Dreptunghiuri 4 noduri: {sum(1 for v in v_simp_all if v == 4)} / {len(results)}")
