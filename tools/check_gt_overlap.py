import pyogrio
import geopandas as gpd

gt = gpd.read_file('data/ground_truth/tier1_teren.geojson')
print('Ground truth tier1 count:', len(gt))
print('Columns:', gt.columns.tolist())
vertex_counts = [len(geom.exterior.coords) for geom in gt.geometry if geom.geom_type == 'Polygon']
print(f'Tier 1 GT vertices: min={min(vertex_counts)}, max={max(vertex_counts)}, mean={sum(vertex_counts)/len(vertex_counts):.1f}')

# Check overlap with CLADIRI_HIBRID
cl = gpd.read_file('workspace/output/cladiri_stereo70.gpkg', layer='CLADIRI_HIBRID')
print('CLADIRI_HIBRID count:', len(cl))
v_cl = [len(geom.exterior.coords) for geom in cl.geometry if geom.geom_type == 'Polygon']
print(f'CLADIRI_HIBRID vertices: min={min(v_cl)}, max={max(v_cl)}, mean={sum(v_cl)/len(v_cl):.1f}')

# Intersection / matches
matches = 0
for idx, gt_row in gt.iterrows():
    gt_geom = gt_row.geometry
    for _, cl_row in cl.iterrows():
        cl_geom = cl_row.geometry
        if gt_geom.intersects(cl_geom):
            iou = gt_geom.intersection(cl_geom).area / gt_geom.union(cl_geom).area
            if iou > 0.3:
                matches += 1
                break
print(f'Matches between GT (29) and CLADIRI_HIBRID (195): {matches} / {len(gt)}')
