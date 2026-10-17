"""Fit all sides of the reviewed white roof from native optical transitions."""
from pathlib import Path
import sys,json
import numpy as np,rasterio,geopandas as gpd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_gap_edges import fit_red_roof_edge,replace_observed_edge
OUT=ROOT/'workspace/reviews/lot3_repairs_20261017';src=OUT/'T20_planar_v2'
dest=OUT/'T20_edges';dest.mkdir(exist_ok=False)
df=gpd.read_file(src/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES')
with rasterio.open(OUT/'covers/T20_5cm.tif') as s:
    rgb=np.moveaxis(s.read([1,2,3]),0,-1);tr=s.transform;valid=np.all(s.read_masks([1,2,3])>0,axis=0)
logs=[]
for idx,row in df.iterrows():
    if row.body_id!='T20:C2':continue
    g=row.geometry;original=g;edges=list(original.exterior.coords)
    for edge in range(4):
        report=fit_red_roof_edge(rgb,tr,valid,edges[edge],edges[edge+1],original.representative_point().coords[0],signal_kind='BRIGHTNESS',profiles=31)
        if 'coordinates' in report:
            try:g=replace_observed_edge(g,edge,report['coordinates'],max_corner_shift_m=3.5,max_area_change=.15);report['applied']=True
            except ValueError as e:report['applied']=False;report['reason']=str(e)
        logs.append({'body_id':row.body_id,'edge':edge,'report':report})
    df.at[idx,'geometry']=g;df.at[idx,'method']='PLANAR_CORE_WITH_OBSERVED_BRIGHT_EDGES'
df.to_file(dest/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES',driver='GPKG')
(dest/'edge_reports.json').write_text(json.dumps(logs,indent=2));(dest/'inputs.json').write_text((src/'inputs.json').read_text(),encoding='utf-8')
print([(r.body_id,r.geometry.area) for _,r in df.iterrows()])
