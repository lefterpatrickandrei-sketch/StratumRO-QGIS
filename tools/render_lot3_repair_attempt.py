"""Render every repair, including failures, for whole-object visual adoption."""
from pathlib import Path
import argparse,json
import rasterio,numpy as np
from rasterio.windows import from_bounds,Window
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot3_repairs_20261017'
parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='attempt1');args=parser.parse_args()
run=OUT/args.attempt
m=json.loads((run/'inputs.json').read_text());new=gpd.read_file(run/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
old=gpd.read_file(ROOT/'workspace/reviews/lot3_edge_audit_20261017/lot3_display_snapshot.gpkg',layer='CURRENT_REVIEW_HYPOTHESES')
for scene in sorted({c['body_id'].split(':')[0] for c in m['cases']}):
    cases=[c for c in m['cases'] if c['body_id'].startswith(scene+':')]
    a=min(c['search_bounds'][0] for c in cases)-2;b=min(c['search_bounds'][1] for c in cases)-2
    c=max(c['search_bounds'][2] for c in cases)+2;d=max(c['search_bounds'][3] for c in cases)+2
    with rasterio.open(cases[0]['ortho']) as s:
        win=from_bounds(a,b,c,d,s.transform).round_offsets().round_lengths().intersection(Window(0,0,s.width,s.height))
        rgb=np.moveaxis(s.read([1,2,3],window=win),0,-1);tr=s.window_transform(win)
    extent=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
    fig,axes=plt.subplots(1,3,figsize=(19,8))
    for ax in axes:ax.imshow(rgb,extent=extent);ax.set_xlim(a,c);ax.set_ylim(b,d);ax.axis('off')
    for ax,df,title,color in [(axes[1],old,'ANTERIOR','#ff8800'),(axes[2],new,'NOU - DE VERIFICAT','#00ffff')]:
        for _,r in df[df.test_id==scene].iterrows():
            g=r.geometry;ident=r.get('body_id')
            if not isinstance(ident,str):ident=r.id
            ax.plot(*g.exterior.xy,color=color,lw=1.5)
            for ring in g.interiors:ax.plot(*ring.xy,color=color,lw=1.5)
            pt=g.representative_point();ax.text(pt.x,pt.y,ident,color='white',fontsize=9,bbox={'facecolor':'black','alpha':.6,'edgecolor':'none'})
        ax.set_title(scene+' / '+title)
    axes[0].set_title(scene+' / SID 5cm FARA CONTUR');fig.tight_layout();fig.savefig(run/(scene+'_comparison.png'),dpi=140);plt.close(fig)
print('All scene comparisons rendered')
