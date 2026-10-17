"""Reapply the product simplifier to saved real masks; no repeated inference."""
from pathlib import Path
import sys,json,shutil,argparse
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from stratum_ro.roof_mask_fidelity import simplify_observed_roof,rectangular_roof_core
OUT=ROOT/'workspace/reviews/lot3_repairs_20261017'
parser=argparse.ArgumentParser();parser.add_argument('--source',default='attempt1');parser.add_argument('--output',default='simplified2');parser.add_argument('--only-scene');args=parser.parse_args()
src=OUT/args.source;dest=OUT/args.output;dest.mkdir(exist_ok=False)
m=json.loads((src/'inputs.json').read_text());raw=gpd.read_file(src/'cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS')
if args.only_scene:
    m['cases']=[c for c in m['cases'] if c['body_id'].startswith(args.only_scene+':')]
    raw=raw[raw.body_id.str.startswith(args.only_scene+':')]
rows=[];reports=[]
for _,r in raw.iterrows():
    c=next(c for c in m['cases'] if c['body_id']==r.body_id)
    if r.body_id.startswith('T20:'):g,d=rectangular_roof_core(r.geometry,c['anchor'])
    else:g,d=simplify_observed_roof(r.geometry,c['anchor'],max_vertices=48)
    rows.append({'body_id':r.body_id,'test_id':r.body_id.split(':')[0],'owner_verdict':'PENDING_OWNER_REVIEW',
        'geometry_role':'OBSERVED_ROOF_HYPOTHESIS','method':d['method'],'status':d['status'],'geometry':g})
    reports.append({'body_id':r.body_id,'vertices':len(g.exterior.coords)-1+sum(len(h.coords)-1 for h in g.interiors),'area_m2':g.area,'diagnostic':d})
gpd.GeoDataFrame(rows,crs=3844).to_file(dest/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES',driver='GPKG')
(dest/'inputs.json').write_text(json.dumps(m,indent=2),encoding='utf-8');(dest/'report.json').write_text(json.dumps(reports,indent=2))
print(json.dumps(reports))
