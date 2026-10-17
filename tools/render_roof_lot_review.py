"""Render source, raw mask and simplified hypothesis for every reviewed case."""
from pathlib import Path
import argparse,json
import numpy as np,rasterio,geopandas as gpd
from rasterio.windows import from_bounds
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--lot-dir',type=Path,required=True)
parser.add_argument('--run-name',default='attempt1')
parser.add_argument('--gpkg',default='cadastral_review.gpkg')
args=parser.parse_args();out=args.lot_dir.resolve()/args.run_name
m=json.loads((out/'inputs.json').read_text())
raw=gpd.read_file(out/args.gpkg,layer='RAW_OPTICAL_MASKS')
new=gpd.read_file(out/args.gpkg,layer='ROOF_HYPOTHESES')
dest=out/'visual';dest.mkdir(exist_ok=False)
for c in m['cases']:
    a,b,x,y=c['search_bounds'];bounds=[a-3,b-3,x+3,y+3]
    with rasterio.open(c['ortho']) as s:
        w=from_bounds(*bounds,s.transform).round_offsets().round_lengths()
        image=np.moveaxis(s.read([1,2,3],window=w),0,-1);mask=np.all(s.read_masks([1,2,3],window=w)>0,axis=0)
        bb=rasterio.windows.bounds(w,s.transform)
    fig,axes=plt.subplots(1,3,figsize=(18,8))
    for ax in axes:
        ax.imshow(np.dstack([image,mask.astype('uint8')*255]),extent=[bb[0],bb[2],bb[1],bb[3]])
        ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.axis('off')
    axes[0].set_title(c['body_id']+' / IMAGINE')
    for ax,data,title,color in [(axes[1],raw,'MASCA BRUTA','#ff8800'),(axes[2],new,'IPOTEZA / IN REVIZIE','#00ffff')]:
        for _,r in data[data.body_id==c['body_id']].iterrows():
            g=r.geometry;ax.plot(*g.exterior.xy,color=color,lw=1.3)
            for ring in g.interiors:ax.plot(*ring.xy,color=color,lw=1)
        ax.set_title(c['body_id']+' / '+title)
        if data[data.body_id==c['body_id']].empty:ax.text(.5,.08,'NEREZOLVAT / FARA CONTUR ADOPTAT',color='red',ha='center',transform=ax.transAxes,bbox={'facecolor':'white','alpha':.9})
    fig.tight_layout();fig.savefig(dest/(c['body_id'].replace(':','_')+'.png'),dpi=130);plt.close(fig)
print('Individual whole-case comparisons rendered.')
