"""Compare wider-window results and report sensor evidence; no automatic adoption."""
from pathlib import Path
import json,argparse,sys
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.warp import reproject,Resampling
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from stratum_ro.roof_revision_review import review_roof_revision
OUT=ROOT/'workspace/reviews/lot3_continuation_20261017'
parser=argparse.ArgumentParser()
parser.add_argument('--results',default='results')
args=parser.parse_args()
run=OUT/args.results
manifest=json.loads((OUT/'workflow_inputs.json').read_text())
old=gpd.read_file(ROOT/'workspace/reviews/lot3_finishing_20261017/results/cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
new=gpd.read_file(run/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
revision=review_roof_revision(dict(zip(old.body_id,old.geometry)),dict(zip(new.body_id,new.geometry)))
(run/'revision_guard.json').write_text(json.dumps(revision,indent=2))
checks=[]
for _,row in new.iterrows():
    geom=row.geometry;ident=row.body_id
    case=next(c for c in manifest['cases'] if c['body_id']==ident)
    crop=run/(ident.replace(':','_')+'_ortho.tif')
    with rasterio.open(crop) as src:tr=src.transform;sz=(src.height,src.width)
    inside=rasterize([(geom,1)],out_shape=sz,transform=tr,dtype='uint8').astype(bool)
    evidence={}
    for key in ['relative_height','building_counts']:
        grid=np.full(sz,np.nan,dtype='float32')
        with rasterio.open(manifest[key]) as src:
            reproject(rasterio.band(src,1),grid,src_transform=src.transform,src_crs=src.crs,
                dst_transform=tr,dst_crs='EPSG:3844',dst_nodata=np.nan,resampling=Resampling.nearest)
        valid=inside&np.isfinite(grid)&(grid>-100)
        values=grid[valid]
        evidence[key]={'observed_fraction':float(valid.sum()/max(1,inside.sum())),
            'median':float(np.median(values)) if values.size else None,
            'p10':float(np.percentile(values,10)) if values.size else None,
            'p90':float(np.percentile(values,90)) if values.size else None}
    prior=old[old.body_id==ident]
    item={'body_id':ident,'valid':bool(geom.is_valid),'area_m2':geom.area,'holes':len(geom.interiors),
          'sensor_summary':evidence,'automatic_adoption':False}
    if len(prior)==1:
        p=prior.geometry.iloc[0]
        item.update(iou_to_previous=p.intersection(geom).area/p.union(geom).area,
                    area_change_m2=geom.area-p.area,previous_holes=len(p.interiors))
    checks.append(item)
overlaps=[]
for i,a in new.iterrows():
    for j,b in new.iterrows():
        if j>i:overlaps.append({'a':a.body_id,'b':b.body_id,'intersection_m2':a.geometry.intersection(b.geometry).area})
(run/'comparison_and_sensor_checks.json').write_text(json.dumps({'bodies':checks,'pair_overlaps':overlaps},indent=2))
for ident in ['T17','T18']:
    case=next(c for c in manifest['cases'] if c['body_id'].startswith(ident))
    with rasterio.open(case['ortho']) as src:
        rgb=np.moveaxis(src.read([1,2,3]),0,-1);bounds=src.bounds
    fig,axes=plt.subplots(1,2,figsize=(16,8))
    for ax,df,title,col in zip(axes,[old,new],['ANTERIOR','TEST CU CONTEXT EXTINS / NEVERIFICAT'],['#ff8800','#00ffff']):
        ax.imshow(rgb,extent=[bounds.left,bounds.right,bounds.bottom,bounds.top])
        for _,row in df[df.body_id.str.startswith(ident)].iterrows():
            g=row.geometry;ax.plot(*g.exterior.xy,color=col,lw=2)
            for ring in g.interiors:ax.plot(*ring.xy,color=col,lw=2)
            p=g.representative_point();ax.text(p.x,p.y,row.body_id,color='white',bbox=dict(facecolor='black',alpha=.5))
        ax.set_title(ident+' / '+title);ax.axis('off')
    fig.tight_layout();fig.savefig(run/(ident+'_context_comparison.png'),dpi=150);plt.close(fig)
print(json.dumps({'bodies':checks,'pair_overlaps':overlaps},indent=2))
