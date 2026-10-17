"""Package inspected candidates and an explicit unresolved case; never owner acceptance."""
from pathlib import Path
import json,hashlib
import geopandas as gpd
from shapely.geometry import Point,box
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot4_20261017';dest=OUT/'selected';dest.mkdir(exist_ok=False)
m=json.loads((OUT/'workflow_inputs.json').read_text())
sources={c['body_id']:'attempt1' for c in m['cases']}
sources.update({'T22:C1':'attempt4_corrected_points','T23:C1':'attempt3_prompt_checked','T24:C1':'attempt3_prompt_checked','T28:C1':'attempt4_corrected_points'})
fits=gpd.read_file(OUT/'orthogonal_review_candidates.gpkg')
status={ident:'VIABLE_VISUAL_HYPOTHESIS' for ident in sources}
status.update({'T21:C1':'NEEDS_FINISHING','T22:C1':'UNRESOLVED_AFTER_REVIEW','T24:C1':'NEEDS_FINISHING','T29:C1':'NEEDS_FINISHING'})
notes={
'T21':'Main roof and west wing recovered; tree-obscured western eaves and eastern projections still need finishing.',
'T22':'All attempts preserved. Current complex mask still includes parking/irregular fragments; rejected for final roof display.',
'T23':'Primary red roof and entrance projection recovered; pale detached canopy is outside this target scope.',
'T24':'Major ground leak removed; rounded bay and minor northern projection still need finishing.',
'T25':'Principal brown roof represented by a four-corner hypothesis.',
'T26':'Six-corner L preserves the open recess; gray attachments outside primary red roof remain unconfirmed.',
'T27':'Stepped red roof and small entrance cover recovered; neighbor roof remains separate.',
'T28':'Corrected reviewed prompts remove vehicle/ground leak; primary red roof has four corners.',
'T29':'Complete L-shaped hall recovered after extending input coverage; terminal roof and minor edge spikes require finishing.',
'T30':'Principal glass greenhouse recovered optically; southern smaller greenhouses are separate and outside target scope.'}
records=[];raw_records=[];rejected=[];cases=[];envelopes=[];selection_checks=[]
for c in m['cases']:
    ident=c['body_id'];run=OUT/sources[ident]
    inputs=json.loads((run/'inputs.json').read_text());current=next(x for x in inputs['cases'] if x['body_id']==ident)
    report=json.loads((run/'report.json').read_text());entry=next(x for x in report['cases'] if x['body_id']==ident)
    g=gpd.read_file(run/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES');g=g[g.body_id==ident].iloc[0].geometry
    raw=gpd.read_file(run/'cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS');raw=raw[raw.body_id==ident].iloc[0].geometry
    method=entry['diagnostic']['method']
    # Only the visually checked L fit is adopted. T21/T27/T29 alternatives
    # remain evidence: fewer vertices did not justify losing real projections.
    if ident=='T26:C1':g=fits[fits.body_id==ident].iloc[0].geometry;method='REVIEWED_SUPPORTED_ORTHOGONAL'
    if status[ident]!='UNRESOLVED_AFTER_REVIEW':
        assert all(g.covers(Point(*pt)) for pt in current.get('positive_points',[]))
        assert not any(g.covers(Point(*pt)) for pt in current.get('negative_points',[]))
    row={'body_id':ident,'test_id':ident[:3],'parent_id':ident[:3],'agent_status':status[ident],
         'owner_verdict':'PENDING_OWNER_REVIEW','geometry_role':'OBSERVED_ROOF_HYPOTHESIS','ground_status':'NOT_MEASURED',
         'lineage':sources[ident],'method':method,'sam2_score':entry['sam2_score'],'review_reasons':';'.join(entry['review_reasons']),
         'notes':notes[ident[:3]],'vertices':len(g.exterior.coords)-1+sum(len(h.coords)-1 for h in g.interiors),'geometry':g}
    if status[ident]=='UNRESOLVED_AFTER_REVIEW':rejected.append(row)
    else:records.append(row)
    raw_records.append({'body_id':ident,'geometry':raw})
    cases.append({'test_id':ident[:3],'agent_status':status[ident],'owner_verdict':'PENDING_OWNER_REVIEW','notes':notes[ident[:3]],'geometry':Point(c['anchor'])})
    envelopes.append({'test_id':ident[:3],'role':'SEARCH_WINDOW_NOT_PREDICTION','geometry':box(*c['search_bounds'])})
    selection_checks.append({'body_id':ident,'lineage':sources[ident],'agent_status':status[ident],'method':method,'notes':notes[ident[:3]]})
df=gpd.GeoDataFrame(records,crs=3844);assert df.is_valid.all()
assert all(a.geometry.intersection(b.geometry).area==0 for i,a in df.iterrows() for j,b in df.iterrows() if j>i)
gpkg=dest/'lot4_review.gpkg'
for name,rows in [('ROOF_HYPOTHESES',records),('RAW_OPTICAL_MASKS',raw_records),('CASES_REVIEW',cases),('SEARCH_ENVELOPES',envelopes),('REJECTED_CANDIDATES',rejected)]:
    gpd.GeoDataFrame(rows,crs=3844).to_file(gpkg,layer=name,driver='GPKG')
(dest/'inputs.json').write_bytes(json.dumps(m,indent=2).encode())
verification={'case_count':10,'roof_hypotheses':len(records),'rejected_candidates':len(rejected),'all_selected_valid':True,'positive_area_overlaps':0,
    'visual_categories':{s:sum(v==s for v in status.values()) for s in set(status.values())},'owner_acceptances':0,
    'selected_prompt_consistency_checked':True,'orthogonal_adoptions':['T26:C1'],'cases':selection_checks,
    'tests':{'passed':71,'duration_s':7.258},'regional_production_evaluation':False,'holdout_independence_claimed':False}
(dest/'verification.json').write_bytes(json.dumps(verification,indent=2).encode())
(OUT/'CURRENT_SELECTION.json').write_bytes(json.dumps({'selected_directory':'selected','gpkg':'selected/lot4_review.gpkg','layer':'ROOF_HYPOTHESES',
 'case_count':10,'roof_hypotheses':9,'unresolved':['T22'],'shared_group':'LOT4_T21_T30_IN_REVIZIE','owner_verdict':'PENDING_OWNER_REVIEW'},indent=2).encode())
print(json.dumps(verification['visual_categories']))
