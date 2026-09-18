import geopandas as gpd

gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')
cl = gpd.read_file('workspace/output/cladiri_stereo70.gpkg', layer='CLADIRI_HIBRID')

print(f"Total CLADIRI_HIBRID: {len(cl)}")
matched_cl_ids = set()
for idx, gt_row in gt.iterrows():
    gt_p = gt_row.geometry
    for _, cl_row in cl.iterrows():
        cl_p = cl_row.geometry
        if gt_p.intersects(cl_p):
            inter_area = gt_p.intersection(cl_p).area
            if inter_area > 15.0 or (inter_area / cl_p.area > 0.2):
                matched_cl_ids.add(cl_row.id)

print(f"CLADIRI_HIBRID matching GT buildings: {len(matched_cl_ids)}")

non_matched = cl[~cl.id.isin(matched_cl_ids)]
print(f"Non-matched features: {len(non_matched)}")
print("Non-matched action codes:")
print(non_matched['action_code'].value_counts())
print("Non-matched mean area:", non_matched.geometry.area.mean())
print("Non-matched area quantiles:")
print(non_matched.geometry.area.quantile([0.1, 0.25, 0.5, 0.75, 0.9]))
