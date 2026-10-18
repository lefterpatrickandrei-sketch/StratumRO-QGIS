"""Apply independently observed edges and preserve previous hypotheses as history."""
from pathlib import Path
import sys,json
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_gap_edges import replace_observed_edge
OUT=ROOT/'workspace/reviews/lot3_edge_audit_20261017'
df=gpd.read_file(ROOT/'workspace/reviews/lot3_continuation_20261017/annex_review_final.gpkg',layer='CURRENT_ROOFS_AND_ANNEX_HYPOTHESIS')
gap=json.loads((OUT/'T18_observed_gap.json').read_text());main=json.loads((OUT/'T18_main_edge.json').read_text())
assert gap['status']=='OBSERVED_OPTICAL_GAP_REQUIRES_REVIEW'
assert main['status']=='OBSERVED_RED_ROOF_EDGE_REQUIRES_REVIEW'
before={r.body_id:r.geometry for _,r in df.iterrows()}
for ident,index,edge in [('T18:C1',1,main['coordinates']),('T18:C2',1,gap['edges'][0]['coordinates'])]:
    i=df.index[df.body_id==ident][0]
    df.at[i,'geometry']=replace_observed_edge(df.at[i,'geometry'],index,edge)
    df.at[i,'method']='NATIVE_OBSERVED_STRAIGHT_EDGE'
    df.at[i,'review_reasons']='NATIVE_EDGE_REQUIRES_OWNER_REVIEW;LIDAR_ALIGNMENT_EXPERIMENTAL'
    df.at[i,'status']='REQUIRES_REVIEW'
a=df[df.body_id=='T18:C1'].geometry.iloc[0];b=df[df.body_id=='T18:C2'].geometry.iloc[0]
overlap=a.intersection(b).area
if overlap>.01:raise ValueError('Observed edges still overlap; do not hide conflict')
dest=OUT/'observed_edges.gpkg'
if dest.exists():raise FileExistsError('Preserve historical geometry')
df.to_file(dest,layer='ROOF_HYPOTHESES',driver='GPKG')
report={'owner_verdict':'PENDING_OWNER_REVIEW','overlap_before_m2':5.781771071492054,
        'overlap_after_m2':overlap,'minimum_roof_gap_m':a.distance(b),'all_valid':bool(df.is_valid.all()),
        'bodies':[{'body_id':r.body_id,'area_before_m2':before[r.body_id].area,'area_after_m2':r.geometry.area,
                   'vertices':len(r.geometry.exterior.coords)-1,'unchanged':r.geometry.equals(before[r.body_id])} for _,r in df.iterrows()],
        'method':'Independent optical edge fits; no clipping against a prior reference',
        'lidar_evidence':'Existing local relative height supports distinct elevated roofs; absolute alignment remains experimental'}
(OUT/'edge_correction_report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
