from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import geopandas as gpd
from stratum_ro.api.service import PlatformService
p=ROOT/'workspace/reviews/option_b_refinement_20261018_final/refinement.gpkg'
a=gpd.read_file(p,layer='B4_FINAL_REVIEW');base=gpd.read_file(p,layer='B0_BASELINE').set_index('candidate_id')
cfg=json.loads((ROOT/'workspace/option_b_refinement_20261018/config_replay.json').read_text())
engine=PlatformService(ROOT).create_regional_roof_refiner([ROOT/x for x in cfg['orthophotos']])
records=[]
for _,r in a.iterrows():
 g=r.geometry;b=base.loc[r.candidate_id].geometry
 if g.geom_type=='MultiPolygon' and len(g.geoms)==1:g=g.geoms[0]
 if b.geom_type=='MultiPolygon' and len(b.geoms)==1:b=b.geoms[0]
 records.append(dict(candidate_id=r.candidate_id,geometry=g,baseline_geometry=b,qa_status=str(r.qa_status)))
result=engine.simplify_shapes(records)
old=gpd.read_file(ROOT/'workspace/reviews/option_b_simple_variations_20261018_v2/simple_variations.gpkg',layer='B_SIMPLE').set_index('candidate_id')
changed=[r['candidate_id'] for r in result['final'] if not r['geometry'].equals(old.loc[r['candidate_id']].geometry)]
report=dict(count=len(result['final']),variant_count=len(result['variants']),changed_vs_reviewed_output=changed,
 conflicts_before=len(result['conflicts_before']),conflicts_after=len(result['conflicts_after']),joint_reverted=result['jointly_reverted_ids'])
(ROOT/'workspace/option_b_consolidation_20261019/shared_batch_verification.json').write_text(json.dumps(report,indent=2))
print(report)
assert not changed
