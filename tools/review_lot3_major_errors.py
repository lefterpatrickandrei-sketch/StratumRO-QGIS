"""Read-only geometry review: pair each current contour with unobscured imagery."""
from pathlib import Path
import json,hashlib
import geopandas as gpd
import rasterio
from rasterio.windows import from_bounds,Window
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_major_errors_20261017';OUT.mkdir(exist_ok=True)
source=ROOT/'workspace/reviews/lot3_edge_audit_20261017/lot3_display_snapshot.gpkg'
df=gpd.read_file(source,layer='CURRENT_REVIEW_HYPOTHESES')
manifest=json.loads((ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json').read_text())
metadata=[]
for case in manifest['cases']:
    ident=case['test_id'];selected=df[df.test_id==ident]
    bounds=np.array(case['search_bbox'],dtype=float)
    if len(selected):
        sb=selected.total_bounds;bounds=np.array([min(bounds[0],sb[0]),min(bounds[1],sb[1]),max(bounds[2],sb[2]),max(bounds[3],sb[3])])
    bounds+=np.array([-6,-6,6,6])
    path=Path(case['tile'])
    if not path.is_absolute():path=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi'/path
    if ident=='T18':path=ROOT/'workspace/reviews/lot3_edge_audit_20261017/T18_detail_5cm.tif'
    with rasterio.open(path) as s:
        win=from_bounds(*bounds,s.transform).round_offsets().round_lengths().intersection(Window(0,0,s.width,s.height))
        rgb=np.moveaxis(s.read([1,2,3],window=win),0,-1);tr=s.window_transform(win)
    extent=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
    fig,axes=plt.subplots(1,2,figsize=(15,8))
    for ax in axes:ax.imshow(rgb,extent=extent);ax.set_xlim(extent[:2]);ax.set_ylim(extent[2:]);ax.axis('off')
    axes[0].set_title(ident+' / IMAGINE FARA CONTUR')
    axes[1].set_title(ident+' / CONTURURI ACTUALE - NU VERDICT DE ACCEPTARE')
    bodies=[]
    for _,r in selected.iterrows():
        body=r.body_id if isinstance(r.body_id,str) else r.id;g=r.geometry
        axes[1].plot(*g.exterior.xy,color='orange' if body=='T18:C2' else 'cyan',lw=1.5)
        for ring in g.interiors:axes[1].plot(*ring.xy,color='cyan',lw=1.5)
        p=g.representative_point();axes[1].text(p.x,p.y,body,color='white',fontsize=10,bbox={'facecolor':'black','alpha':.7,'edgecolor':'none'})
        bodies.append({'body_id':body,'area_m2':g.area,'valid':bool(g.is_valid),'exterior_vertices':len(g.exterior.coords)-1})
    if not len(selected):axes[1].text(.5,.5,'NICIUN CONTUR RECUPERAT',ha='center',transform=axes[1].transAxes,color='red',bbox={'facecolor':'white','alpha':.8})
    fig.tight_layout();fig.savefig(OUT/(ident+'_unobscured_review.png'),dpi=140);plt.close(fig)
    metadata.append({'test_id':ident,'image':ident+'_unobscured_review.png','source_raster':str(path),'bodies':bodies})
(OUT/'review_inventory.json').write_text(json.dumps({'geometry_source':str(source),'geometry_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'cases':metadata,'predictions_changed':False},indent=2))
print('Rendered ten case comparisons; no geometries/project modified')
