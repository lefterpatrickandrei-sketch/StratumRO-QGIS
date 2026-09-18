import geopandas as gpd

gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')
cl = gpd.read_file('workspace/output/cladiri_stereo70.gpkg', layer='CLADIRI_HIBRID')

print(f"{'GT ID':<16} {'GT V':<6} {'AI V':<6} {'IoU':<8} {'Conf':<8} {'Action Code'}")
print("-" * 65)

for idx, gt_row in gt.iterrows():
    gt_p = gt_row.geometry
    for _, cl_row in cl.iterrows():
        cl_p = cl_row.geometry
        if gt_p.intersects(cl_p):
            iou = gt_p.intersection(cl_p).area / gt_p.union(cl_p).area
            if iou > 0.2:
                gt_v = len(gt_p.exterior.coords) - 1
                cl_v = len(cl_p.exterior.coords) - 1
                conf = cl_row.get('conf_final', 0.0)
                code = cl_row.get('action_code', '')
                print(f"{gt_row.id:<16} {gt_v:<6} {cl_v:<6} {iou:<8.3f} {conf:<8.3f} {code}")
