"""Prepare explicit reviewed roof targets; native covers are extracted separately."""
from pathlib import Path
import json,hashlib
import geopandas as gpd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_repairs_20261017';OUT.mkdir(exist_ok=True)
source=ROOT/'workspace/reviews/lot3_edge_audit_20261017/lot3_display_snapshot.gpkg'
df=gpd.read_file(source,layer='CURRENT_REVIEW_HYPOTHESES')
cases=[]
for _,row in df.iterrows():
    ident=row.body_id if isinstance(row.body_id,str) else row.id
    if ident.startswith('T17') or ident in ['T11:C1','T11:C2','T20:C1']:continue
    g=row.geometry;a,b,c,d=g.bounds
    pad=5 if ident=='T11:C3' else 3
    bounds=[a-pad,b-pad,c+pad,d+pad]
    anchor=list(g.representative_point().coords[0]);positive=[];negative=[]
    if ident=='T11:C3':anchor=[391230.,585610.]
    if ident=='T18:C1':anchor=[390626.1,585538.6];positive=[[390611.,585512.]];negative=[[390614.,585530.]]
    if ident=='T18:C2':anchor=[390614.,585530.]
    cases.append({'body_id':ident,'anchor':anchor,'search_bounds':bounds,'positive_points':positive,'negative_points':negative})
cases.extend([
 {'body_id':'T19:C1','anchor':[390781.,585122.],'search_bounds':[390762.,585095.,390814.,585142.],
  'positive_points':[[390797.,585116.],[390785.,585106.],[390791.,585129.]],'negative_points':[]},
 {'body_id':'T20:C1','anchor':[390971.,585254.],'search_bounds':[390951.,585240.,390988.,585267.],
  'positive_points':[],'negative_points':[]},
 {'body_id':'T20:C2','anchor':[390969.,585226.],'search_bounds':[390953.,585208.,390988.,585245.],
  'positive_points':[],'negative_points':[]}])
observations={
 'T11':'Northern red-roof house; previous C3 has grossly wrong orientation. Complete roof, including gray attached surface, needs independent optical delineation.',
 'T12':'Reviewed residential roof. Previous outlines cut roof surfaces and may mix terrace/annex. Keep identity explicit; optical mask fidelity is an experiment, not owner acceptance.',
 'T13':'Small gray articulated roof, partly obscured by vegetation. Preserve observed steps without forcing a rectangle.',
 'T14':'Long red roof with actual side/corner projections; previous rectangle clips ends and includes adjoining surfaces.',
 'T15':'Gray rectangular roof, adjacent equipment and other roofs remain independent targets.',
 'T16':'Patched and tile roof sections; inspect complete optical outline, color difference alone does not establish two buildings.',
 'T18':'Main hall with western wing and separate brown annex; previous local edge fix did not validate full shape. Main hall has an explicit negative point on the annex.',
 'T19':'Whole roof complex: light flat roof at roughly 5-7m experimental relative height, with two higher gray roof portions. Positive prompts identify observed roof surfaces, not pavement.',
 'T20':'Separate upper gray roof and lower white roof surface hypotheses. Previous upper contour was a small arbitrary fragment. Body identities remain provisional.'}
for case in cases:
    scene=case['body_id'].split(':')[0]
    image=ROOT/'workspace/reviews/lot3_major_errors_20261017'/(scene+'_unobscured_review.png')
    case.update(ortho=str(OUT/'covers'/(scene+'_5cm.tif')),reviewed=True,
       target_extent=case['search_bounds'][:],lidar_compatibility='NOT_USED',refinement_policy='OPTICAL_FIDELITY',
       selection_observations=observations[scene],selection_review={'object_kind':'BUILDING','point_on_roof':True,
       'full_target_visible':True,'reviewer':'Codex','observations':observations[scene],
       'image':str(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
m={'schema_version':1,'crs':'EPSG:3844','cases':cases,'owner_status':'PENDING_OWNER_REVIEW',
   'purpose':'Native-detail optical repair, no automatic owner acceptance; reviewed prompts are not ground truth.',
   'previous_snapshot':str(source),'previous_snapshot_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
(OUT/'workflow_inputs.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
print('Prepared',len(cases),'reviewed candidates')
