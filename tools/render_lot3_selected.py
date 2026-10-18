"""Render entire cases, keeping old context and native detail visible together."""
from pathlib import Path
import json,argparse
import numpy as np,rasterio
from rasterio.windows import from_bounds,Window
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot3_repairs_20261017'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--selected-dir',default='selected')
args=parser.parse_args()
if Path(args.selected_dir).name!=args.selected_dir:raise ValueError('A directory name is required')
dest=OUT/args.selected_dir
new=gpd.read_file(dest/'lot3_repaired.gpkg',layer='REPAIRED_ROOF_CANDIDATES')
old=gpd.read_file(ROOT/'workspace/reviews/lot3_edge_audit_20261017/lot3_display_snapshot.gpkg',layer='CURRENT_REVIEW_HYPOTHESES')
m=json.loads((ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json').read_text())
frames={}
for case in m['cases']:
    ident=case['test_id'];df=new[new.test_id==ident]
    b=df.total_bounds;b=b+[-5,-5,5,5];frames[ident]=b.tolist()
    if ident=='T11':b=old[old.test_id==ident].total_bounds+[-6,-6,6,6];frames[ident]=b.tolist()
    path=Path(case['tile'])
    if not path.is_absolute():path=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi'/path
    sources=[path];native=OUT/'covers'/(ident+'_5cm.tif')
    if native.exists():sources.append(native)
    fig,axes=plt.subplots(1,3,figsize=(18,8))
    for source in sources:
        with rasterio.open(source) as s:
            win=from_bounds(*b,s.transform).round_offsets().round_lengths().intersection(Window(0,0,s.width,s.height))
            image=np.moveaxis(s.read([1,2,3],window=win),0,-1);tr=s.window_transform(win)
            valid=np.all(s.read_masks([1,2,3],window=win)>0,axis=0)
        ext=[tr.c,tr.c+image.shape[1]*tr.a,tr.f+image.shape[0]*tr.e,tr.f]
        rgba=np.dstack([image,valid.astype('uint8')*255])
        for ax in axes:ax.imshow(rgba,extent=ext)
    for ax in axes:ax.set_xlim(b[0],b[2]);ax.set_ylim(b[1],b[3]);ax.axis('off')
    for ax,data,title,col in [(axes[1],old,'ANTERIOR','#ff8800'),(axes[2],new,'REPARAT / NECESITA VERDICT','#00ffff')]:
        for _,r in data[data.test_id==ident].iterrows():
            g=r.geometry;body=r.get('body_id');body=body if isinstance(body,str) else r.id
            ax.plot(*g.exterior.xy,color=col,lw=1.5)
            for ring in g.interiors:ax.plot(*ring.xy,color=col,lw=1.5)
            pt=g.representative_point();ax.text(pt.x,pt.y,body,color='white',fontsize=8,clip_on=True,bbox={'facecolor':'black','alpha':.6,'edgecolor':'none'})
        ax.set_title(ident+' / '+title)
    axes[0].set_title(ident+' / IMAGINE');fig.tight_layout();fig.savefig(dest/(ident+'_before_after.png'),dpi=140);plt.close(fig)
(dest/'case_frames.json').write_text(json.dumps(frames,indent=2))
print('Ten whole-case before/after comparisons rendered')
