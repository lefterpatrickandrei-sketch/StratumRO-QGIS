import geopandas as gpd
from tools.test_cadastral_clean import simplify_cadastral_polygon
import numpy as np

cl = gpd.read_file('workspace/output/cladiri_stereo70.gpkg', layer='CLADIRI_HIBRID')
gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')

# Match AI predictions with GT
matched_cl = []
for idx, gt_row in gt.iterrows():
    gt_p = gt_row.geometry
    best_iou = 0.0
    best_cl = None
    for _, cl_row in cl.iterrows():
        cl_p = cl_row.geometry
        if gt_p.intersects(cl_p):
            iou = gt_p.intersection(cl_p).area / gt_p.union(cl_p).area
            if iou > best_iou:
                best_iou = iou
                best_cl = cl_row
    if best_cl is not None and best_iou > 0.25:
        matched_cl.append((gt_row.id, best_cl, best_iou))

print(f"Matched AI buildings to GT: {len(matched_cl)} / {len(gt)}")
ai_v_orig = []
ai_v_clean = []
rects = 0
for g_id, cl_row, iou in matched_cl:
    raw_p = cl_row.geometry
    clean_p = simplify_cadastral_polygon(raw_p, tol=0.8)
    v_raw = len(raw_p.exterior.coords) - 1
    v_cl = len(clean_p.exterior.coords) - 1
    ai_v_orig.append(v_raw)
    ai_v_clean.append(v_cl)
    if v_cl == 4:
        rects += 1
    print(f"  {g_id} (IoU={iou:.2f}): raw_v={v_raw} -> clean_v={v_cl}")

print(f"\nAI raw mean vertices: {np.mean(ai_v_orig):.1f}")
print(f"AI clean mean vertices: {np.mean(ai_v_clean):.1f}")
print(f"Clean rectangles: {rects} / {len(matched_cl)}")
