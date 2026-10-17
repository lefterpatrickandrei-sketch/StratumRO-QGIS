"""Continue the saved guidance experiment, preserving its initial outputs."""
from pathlib import Path
import sys,json
import argparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import box
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from stratum_ro.fusion_refinement import refine_fusion_mask
from tools.run_fusion_guidance_demo import aligned_evidence,AUDIT

INITIAL=ROOT/'workspace/reviews/fusion_demo_20261017'
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=ROOT/'workspace/reviews/fusion_rectified_20261017')
OUT=parser.parse_args().output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=False)
report=json.loads((INITIAL/'report.json').read_text())
inputs=gpd.read_file(INITIAL/'fusion_demo.gpkg',layer='IPOTEZE_NEACCEPTATE')
records=[];details=[]
for case in report['cases']:
    ident=case['test_id'];guidance=case['guidance']
    raw=inputs[(inputs.test_id==ident)&(inputs['mode']=='FUSION_GUIDANCE')].iloc[0].geometry
    with rasterio.open(INITIAL/(ident+'_ortho.tif')) as src:
        rgb=np.moveaxis(src.read([1,2,3]),0,-1);tr=src.transform
        valid=np.all(src.read_masks([1,2,3])>0,axis=0)
    heights=aligned_evidence(AUDIT/'relative_surface_1m.tif',tr,rgb.shape[:2],-9999)
    counts=aligned_evidence(AUDIT/'class6_density_1m.tif',tr,rgb.shape[:2])
    geom,diag=refine_fusion_mask(raw,guidance['point'],rgb,tr,heights,counts,valid,guidance['route'])
    vertices=len(geom.exterior.coords)-1+sum(len(r.coords)-1 for r in geom.interiors)
    records.append({'test_id':ident,'body_id':ident+':C1','route':guidance['route'],
                    'status':diag['status'],'method':diag['method'],'vertices':vertices,
                    'owner_verdict':'PENDING_OWNER_REVIEW','geometry':geom})
    details.append({'test_id':ident,'vertices':vertices,'area_m2':geom.area,'diagnostic':diag})
    fig,axes=plt.subplots(1,2,figsize=(16,8))
    ext=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
    for ax,g,title,color in zip(axes,[raw,geom],['Ghidare initiala - masca bruta','Verificare suprafata si forma - NECESITA VERDICT'],['#b24aff','#00ffff']):
        ax.imshow(rgb,extent=ext);ax.plot(*g.exterior.xy,color=color,lw=2)
        for hole in g.interiors:ax.plot(*hole.xy,color=color,lw=2)
        ax.set_title(ident+' / '+title);ax.axis('off')
    fig.suptitle(diag['status']+' | '+str(vertices)+' noduri | '+diag['method'])
    fig.tight_layout();fig.savefig(OUT/(ident+'_before_after.png'),dpi=145);plt.close(fig)
    print(json.dumps(details[-1]),flush=True)
gpd.GeoDataFrame(records,crs=3844).to_file(OUT/'fusion_rectified.gpkg',layer='IPOTEZE_RECTIFICATE',driver='GPKG')
inputs[inputs['mode']=='FUSION_GUIDANCE'].to_file(OUT/'fusion_rectified.gpkg',layer='MASTI_INITIALE',driver='GPKG')
(OUT/'report.json').write_text(json.dumps({'scope':'LOCAL_EXPERIMENT_NOT_FULL_PRODUCTION','owner_verdict':'PENDING_OWNER_REVIEW','cases':details},indent=2),encoding='utf-8')
