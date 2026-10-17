"""Measure evidence in missed roof patches; prior output is diagnosis only."""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from tools.run_fusion_guidance_demo import aligned_evidence,AUDIT

OUT=ROOT/'workspace/reviews/lot3_finishing_20261017'
OUT.mkdir(exist_ok=True)
previous=gpd.read_file(ROOT/'workspace/reviews/fusion_complete_20261017/fusion_complete.gpkg',layer='IPOTEZE_RECTIFICATE')
current=gpd.read_file(ROOT/'workspace/reviews/cadastral_workflow_v4_20261017/cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
raws=gpd.read_file(ROOT/'workspace/reviews/cadastral_workflow_v4_20261017/cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS')
diagnostics=[]
for ident in ['T17:C1','T18:C1']:
    old=previous[previous.body_id==ident].geometry.iloc[0]
    new=current[current.body_id==ident].geometry.iloc[0]
    raw=raws[raws.body_id==ident].geometry.iloc[0]
    with rasterio.open(ROOT/'workspace/reviews/cadastral_workflow_v4_20261017'/(ident.replace(':','_')+'_ortho.tif')) as src:
        rgb=np.moveaxis(src.read([1,2,3]),0,-1);tr=src.transform
    heights=aligned_evidence(AUDIT/'relative_surface_1m.tif',tr,rgb.shape[:2],-9999)
    counts=aligned_evidence(AUDIT/'class6_density_1m.tif',tr,rgb.shape[:2])
    missed=old.difference(new)
    pieces=list(missed.geoms) if hasattr(missed,'geoms') else [missed]
    for patch in sorted(pieces,key=lambda g:g.area,reverse=True):
        if patch.area<1:continue
        mask=rasterize([(patch,1)],out_shape=heights.shape,transform=tr,dtype='uint8').astype(bool)
        if not mask.any():continue
        diagnostics.append({'body_id':ident,'area_m2':patch.area,'center':[patch.centroid.x,patch.centroid.y],
            'class6_fraction':float((counts[mask]>0).mean()),'height_percentiles':np.percentile(heights[mask],[5,50,95]).tolist(),
            'rgb_median':np.median(rgb[mask],axis=0).tolist(),'max_distance_to_raw_m':patch.hausdorff_distance(patch.intersection(raw)) if not patch.intersection(raw).is_empty else None})
(OUT/'missed_patch_diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf-8')
print(json.dumps(diagnostics,indent=2))
