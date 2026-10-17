"""Render native edge comparison and all ten current Lot3 cases for review."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
import geopandas as gpd
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_edge_audit_20261017'
before=gpd.read_file(ROOT/'workspace/reviews/lot3_continuation_20261017/annex_review_final.gpkg',layer='CURRENT_ROOFS_AND_ANNEX_HYPOTHESIS')
after=gpd.read_file(OUT/'observed_edges.gpkg',layer='ROOF_HYPOTHESES')
with rasterio.open(OUT/'T18_native_seam.tif') as s:rgb=np.moveaxis(s.read([1,2,3]),0,-1);b=s.bounds
fig,axes=plt.subplots(1,2,figsize=(16,9))
for ax,df,title in zip(axes,[before,after],['INAINTE: suprapunere 5.78 m2','DUPA: doua margini observate, fara suprapunere']):
    ax.imshow(rgb,extent=[b.left,b.right,b.bottom,b.top])
    for _,r in df[df.body_id.str.startswith('T18')].iterrows():
        ax.plot(*r.geometry.exterior.xy,color='cyan' if r.body_id.endswith('C1') else 'orange',lw=1.5)
    ax.set_xlim(390604,390625);ax.set_ylim(585519,585543);ax.axis('off');ax.set_title(title)
fig.tight_layout();fig.subplots_adjust(top=.94);fig.savefig(OUT/'T18_native_before_after.png',dpi=160);plt.close(fig)
manifest=json.loads((ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json').read_text())
old=gpd.read_file(ROOT/'workspace/reviews/lot3_revision_v3_20261016/results/lot3_results.gpkg',layer='CORPURI_EXTRASE_LOT3')
snapshot=gpd.GeoDataFrame(pd.concat([old[~old.test_id.isin(['T17','T18'])],after],ignore_index=True),crs=old.crs)
if not (OUT/'lot3_display_snapshot.gpkg').exists():
    snapshot.to_file(OUT/'lot3_display_snapshot.gpkg',layer='CURRENT_REVIEW_HYPOTHESES',driver='GPKG')
(OUT/'audit_crops').mkdir(exist_ok=True)
tile_dir=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi'
summaries=[]
for page in [0,1]:
    fig,axes=plt.subplots(3,2,figsize=(14,18))
    for ax,c in zip(axes.flat,manifest['cases'][page*5:page*5+5]):
        ident=c['test_id'];selected=after[after.test_id==ident] if ident in ['T17','T18'] else old[old.test_id==ident]
        bounds=list(c['search_bbox'])
        if ident=='T17':bounds=[390765,585430,390903,585553]
        path=Path(c['tile']);path=path if path.is_absolute() else tile_dir/path
        with rasterio.open(path) as s:
            win=from_bounds(bounds[0]-5,bounds[1]-5,bounds[2]+5,bounds[3]+5,s.transform).round_offsets().round_lengths()
            data=np.moveaxis(s.read([1,2,3],window=win),0,-1);tr=s.window_transform(win)
            mask=np.all(s.read_masks([1,2,3],window=win)>0,axis=0)
            profile=s.profile.copy();profile.update(driver='GTiff',height=data.shape[0],width=data.shape[1],
                count=3,transform=tr,nodata=None,compress='deflate')
        crop=OUT/'audit_crops'/(ident+'_display_ortho.tif')
        if not crop.exists():
            with rasterio.open(crop,'w',**profile) as dst:
                dst.write(np.moveaxis(data,-1,0));dst.write_mask(mask.astype('uint8')*255)
        ax.imshow(data,extent=[tr.c,tr.c+data.shape[1]*tr.a,tr.f+data.shape[0]*tr.e,tr.f])
        for j,(_,row) in enumerate(selected.iterrows()):
            geom=row.geometry
            if geom.geom_type!='Polygon':continue
            color='orange' if row.get('body_id')=='T18:C2' else 'cyan'
            ax.plot(*geom.exterior.xy,color=color,lw=1.5)
            for ring in geom.interiors:ax.plot(*ring.xy,color=color,lw=1.5)
        if len(selected)==0:ax.text(.5,.5,'FARA CONTUR RECUPERAT',transform=ax.transAxes,color='red',ha='center',bbox={'facecolor':'white','alpha':.8})
        ax.set_title(f'{ident} | {len(selected)} ipoteze | IN REVIZIE');ax.axis('off')
        summaries.append({'test_id':ident,'displayed_hypotheses':len(selected),'owner_status':'PENDING_OWNER_REVIEW'})
    axes.flat[-1].axis('off');fig.suptitle('LOT3 / situatie curenta - contururile sunt ipoteze, nu acceptari',fontsize=15)
    fig.tight_layout(rect=(0,0,1,.97));fig.savefig(OUT/f'Lot3_review_page_{page+1}.png',dpi=150);plt.close(fig)
(OUT/'lot3_case_inventory.json').write_text(json.dumps(summaries,indent=2))
print(json.dumps(summaries))
