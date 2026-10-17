"""Complete a separately identified gray T17 body on an expanded reviewed scene."""
from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import geopandas as gpd
import torch
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.fusion_guidance import select_fusion_prompt
from stratum_ro.fusion_refinement import refine_fusion_mask
from tools.run_fusion_guidance_demo import aligned_evidence,prompted_component,AUDIT

OUT=ROOT/'workspace/reviews/fusion_complete_20261017'
OUT.mkdir(parents=True,exist_ok=False)
INITIAL=ROOT/'workspace/reviews/fusion_demo_20261017'
REVISION=ROOT/'workspace/reviews/fusion_rectified_v4_20261017'
bounds=(390770,585475,390899,585550)
anchor=(390820,585510)
source=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi/cache_tile_Cluj-0-1_halo.tif'
with rasterio.open(source) as src:
    win=from_bounds(bounds[0]-4,bounds[1]-4,bounds[2]+4,bounds[3]+4,src.transform).round_offsets().round_lengths()
    if win.col_off<0 or win.row_off<0 or win.col_off+win.width>src.width or win.row_off+win.height>src.height:raise ValueError('Incomplete gray roof coverage')
    rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1);tr=src.window_transform(win)
    valid=np.all(src.read_masks([1,2,3],window=win)>0,axis=0)
    if not valid.all() or np.any(np.all(rgb==0,axis=2)):raise ValueError('NoData in gray roof window')
    profile=src.profile.copy()
profile.update(driver='GTiff',height=rgb.shape[0],width=rgb.shape[1],transform=tr,count=3,nodata=None,compress='deflate')
with rasterio.open(OUT/'T17_gray_ortho.tif','w',**profile) as dst:
    dst.write(np.moveaxis(rgb,-1,0));dst.write_mask(valid.astype('uint8')*255)
height=aligned_evidence(AUDIT/'relative_surface_1m.tif',tr,rgb.shape[:2],-9999)
counts=aligned_evidence(AUDIT/'class6_density_1m.tif',tr,rgb.shape[:2])
guidance=select_fusion_prompt(anchor,tr,counts,height,np.isfinite(height)&(height!=-9999))
model=SAM2BuildingSegmenter();model.set_image(rgb,tr)
inv=~tr;point=guidance['point'];px=inv*tuple(point)
left,top=inv*(bounds[0],bounds[3]);right,bottom=inv*(bounds[2],bounds[1])
with torch.inference_mode():
    masks,scores,_=model.predictor.predict(point_coords=np.array([px],dtype='float32'),point_labels=np.array([1],dtype='int32'),box=np.array([left,top,right,bottom],dtype='float32'),multimask_output=True)
options=[]
for mask,score in zip(masks,scores):
    p=prompted_component(mask,px,tr)
    if p is not None and p.is_valid and p.area>=8:options.append((float(score),p))
if not options:raise ValueError('No optical hypothesis for gray body')
score,raw=max(options,key=lambda item:item[0])
geom,diag=refine_fusion_mask(raw,point,rgb,tr,height,counts,valid,guidance['route'])
existing=gpd.read_file(REVISION/'fusion_rectified.gpkg',layer='IPOTEZE_RECTIFICATE')
new={'test_id':'T17_GRAY','body_id':'T17:C2','route':guidance['route'],'status':diag['status'],
     'method':diag['method'],'vertices':len(geom.exterior.coords)-1+sum(len(r.coords)-1 for r in geom.interiors),
     'owner_verdict':'PENDING_OWNER_REVIEW','geometry':geom}
import pandas as pd
combined=gpd.GeoDataFrame(pd.concat([existing,gpd.GeoDataFrame([new],crs=3844)],ignore_index=True),crs=3844)
combined.to_file(OUT/'fusion_complete.gpkg',layer='IPOTEZE_RECTIFICATE',driver='GPKG')
historical=gpd.read_file(REVISION/'fusion_rectified.gpkg',layer='MASTI_INITIALE')
historical.to_file(OUT/'fusion_complete.gpkg',layer='MASTI_INITIALE',driver='GPKG')
gpd.GeoDataFrame([{'test_id':'T17_GRAY','score':score,'geometry':raw}],crs=3844).to_file(OUT/'fusion_complete.gpkg',layer='MASCA_GRAY_INITIALA',driver='GPKG')
fig,axes=plt.subplots(1,2,figsize=(16,7))
ext=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
for ax,g,title,col in zip(axes,[raw,geom],['SAM2 ghidat de LiDAR','Rectificare corp gri separat - NEVERIFICAT'],['#b24aff','#00ffff']):
    ax.imshow(rgb,extent=ext);ax.plot(*g.exterior.xy,color=col,lw=2);ax.set_title(title);ax.axis('off')
fig.suptitle('T17:C2 / '+diag['status']);fig.tight_layout();fig.savefig(OUT/'T17_gray_before_after.png',dpi=145);plt.close(fig)
report={'scope':'LOCAL_EXPERIMENT_WITH_REVIEWED_ANCHORS_NOT_AUTOMATIC_BUILDING_DETECTOR',
        'owner_verdict':'PENDING_OWNER_REVIEW','gray_body':{'anchor':anchor,'search_bounds':bounds,'source':str(source),'guidance':guidance,'sam2_score':score,'diagnostic':diag},
        'cases':json.loads((REVISION/'report.json').read_text())['cases'],'bodies':combined.drop(columns='geometry').to_dict(orient='records'),
        'selection_review':{'reviewer':'Codex','observations':'Expanded native view inspected: elongated gray roof north of red courtyard body, independent body identity. Envelope is search context, not reference geometry.'}}
(OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report['gray_body']),flush=True)
