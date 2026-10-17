"""Diagnose the optical gap at T18 using the native raster, not prior clipping."""
from pathlib import Path
import sys,json
import numpy as np
import rasterio
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_gap_edges import fit_roof_gap,fit_red_roof_edge
OUT=ROOT/'workspace/reviews/lot3_edge_audit_20261017'
df=gpd.read_file(ROOT/'workspace/reviews/lot3_continuation_20261017/annex_review_final.gpkg',layer='CURRENT_ROOFS_AND_ANNEX_HYPOTHESIS')
annex=df[df.body_id=='T18:C2'].geometry.iloc[0]
coords=list(annex.exterior.coords)
# The eastern longitudinal edge is selected from the previously generated
# rectangle; its position/orientation are only an approximate search corridor.
p,q=coords[1],coords[2]
with rasterio.open(OUT/'T18_native_seam.tif') as src:
    rgb=np.moveaxis(src.read([1,2,3]),0,-1);valid=np.all(src.read_masks([1,2,3])>0,axis=0)
    report=fit_roof_gap(rgb,src.transform,valid,p,q)
(OUT/'T18_observed_gap.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='samples'},indent=2))
main=df[df.body_id=='T18:C1'].geometry.iloc[0];edge=list(main.exterior.coords)
with rasterio.open(OUT/'T18_detail_5cm.tif') as src:
    rgb=np.moveaxis(src.read([1,2,3]),0,-1);valid=np.all(src.read_masks([1,2,3])>0,axis=0)
    full=fit_red_roof_edge(rgb,src.transform,valid,edge[1],edge[2],main.representative_point().coords[0])
(OUT/'T18_main_edge.json').write_text(json.dumps(full,indent=2))
print(json.dumps({k:v for k,v in full.items() if k!='samples'},indent=2))
