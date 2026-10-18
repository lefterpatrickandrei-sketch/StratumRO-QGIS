"""Render sensor evidence for T18 annex review; no predictions or GIS edits."""
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject,Resampling
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_continuation_20261017'
OUT.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'workspace/reviews/lot3_finishing_20261017/workflow_inputs.json').read_text())
case=next(c for c in manifest['cases'] if c['body_id']=='T18:C1')
with rasterio.open(case['ortho']) as src:
    win=from_bounds(390585,585485,390670,585580,src.transform).round_offsets().round_lengths()
    rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1);tr=src.window_transform(win)
grids={}
for key in ['relative_height','building_counts']:
    grid=np.full(rgb.shape[:2],np.nan,dtype='float32')
    with rasterio.open(manifest[key]) as src:
        reproject(rasterio.band(src,1),grid,src_transform=src.transform,src_crs=src.crs,
                  dst_transform=tr,dst_crs='EPSG:3844',dst_nodata=np.nan,resampling=Resampling.nearest)
    grids[key]=grid
ext=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
df=gpd.read_file(ROOT/'workspace/reviews/lot3_finishing_20261017/results/cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
fig,axes=plt.subplots(1,3,figsize=(19,9))
for ax,data,title in zip(axes,[rgb,np.ma.masked_where(grids['relative_height']<-100,grids['relative_height']),grids['building_counts']],['Ortofoto / coordonate','Inaltime relativa experimentala (m)','Returns Class6 / celula']):
    kwargs={} if data.ndim==3 else {'cmap':'viridis','vmin':0,'vmax':15 if 'Inaltime' in title else 10}
    im=ax.imshow(data,extent=ext,**kwargs)
    if data.ndim==2:fig.colorbar(im,ax=ax,shrink=.65)
    for geom in df[df.body_id=='T18:C1'].geometry:ax.plot(*geom.exterior.xy,color='cyan',lw=1)
    ax.set_title(title);ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(axis='x',rotation=90)
    ax.set_xticks(np.arange(390590,390671,10));ax.set_yticks(np.arange(585490,585581,10));ax.grid(alpha=.3)
fig.tight_layout();fig.savefig(OUT/'T18_sensor_evidence.png',dpi=160);plt.close(fig)
print(OUT/'T18_sensor_evidence.png')
