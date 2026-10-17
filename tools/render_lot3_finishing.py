"""Before/after evidence only; no new QGIS project is created."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_finishing_20261017'
manifest=json.loads((OUT/'workflow_inputs.json').read_text())
old=gpd.read_file(ROOT/'workspace/reviews/cadastral_workflow_v4_20261017/cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
new=gpd.read_file(OUT/'results/cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
frames={'T17':(390765,585430,390903,585553),'T18':(390585,585480,390674,585590)}
for ident,bounds in frames.items():
    case=next(c for c in manifest['cases'] if c['body_id'].startswith(ident))
    with rasterio.open(case['ortho']) as src:
        win=from_bounds(*bounds,src.transform).round_offsets().round_lengths()
        win=win.intersection(Window(0,0,src.width,src.height))
        rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1);tr=src.window_transform(win)
    ext=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
    fig,axes=plt.subplots(1,2,figsize=(16,8))
    for ax,df,title,col in zip(axes,[old,new],['INAINTE - problema pastrata in istoric','DUPA - finisare, necesita verdict'],['#ff8800','#00ffff']):
        ax.imshow(rgb,extent=ext)
        for _,row in df[df.body_id.str.startswith(ident)].iterrows():
            g=row.geometry;ax.plot(*g.exterior.xy,color=col,lw=2)
            for ring in g.interiors:ax.plot(*ring.xy,color=col,lw=2)
            pt=g.representative_point();ax.text(pt.x,pt.y,row.body_id,color='white',fontsize=9,
                      bbox=dict(facecolor='black',alpha=.5,edgecolor='none'))
        ax.set_xlim(bounds[0],bounds[2]);ax.set_ylim(bounds[1],bounds[3]);ax.set_title(ident+' / '+title);ax.axis('off')
    fig.tight_layout();fig.savefig(OUT/(ident+'_before_after.png'),dpi=150);plt.close(fig)
checks={'all_valid':bool(new.geometry.is_valid.all()),'bodies':[]}
for _,row in new.iterrows():
    g=row.geometry
    checks['bodies'].append({'body_id':row.body_id,'area_m2':g.area,'holes':len(g.interiors),
        'vertices':len(g.exterior.coords)-1+sum(len(r.coords)-1 for r in g.interiors)})
a=new[new.body_id=='T17:C1'].geometry.iloc[0];b=new[new.body_id=='T17:C2'].geometry.iloc[0]
checks.update(T17_intersection_m2=a.intersection(b).area,T17_minimum_gap_m=a.distance(b))
(OUT/'geometry_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks,indent=2))
