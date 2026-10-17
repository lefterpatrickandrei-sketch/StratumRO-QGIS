"""Bind the visually inspected Lot4 selection to source evidence before inference."""
from pathlib import Path
import json,hashlib
from shapely import wkt
from shapely.geometry import Point
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot4_20261017'
m=json.loads((OUT/'selection_review_draft.json').read_text())
revision=json.loads((OUT/'T26_target_revision.json').read_text())['cases'][0]
m['cases']=[revision if c['body_id']=='T26:C1' else c for c in m['cases']]
observations={
'T21':'Large articulated red roof with west wing and end projections. Whole roof inspected, including western eaves; adjacent paving is not roof. Preserve the wing, do not force a rectangle.',
'T22':'Large red complex with multiple wings and open parking recesses. Inspect the complete east/west ends and keep ground/parked cars outside; tree-covered eastern margins remain uncertain.',
'T23':'Red hip roof with a small entrance projection, next to a detached pale canopy at west. Primary red roof is the target; canopy is not silently claimed recovered. Small NoData patch is outside target.',
'T24':'Elongated red roof with a rounded entrance/bay projection, partially occluded at west by a tree. Preserve the observed bay; occluded boundary is uncertain.',
'T25':'Long brown tiled principal roof next to the northern road; mostly rectangular. Small roof fittings are not exterior building corners. Neighboring modern complex is excluded.',
'T26':'Distinct northeastern red L-shaped roof, with an open inner recess and gray neighboring structures. Primary red roof selected; separate cadastral identities of attachments are unconfirmed.',
'T27':'Elongated red roof with skylights, a narrower south end and a small pale southern entrance cover. Prompt is inside red roof, not eastern gutter or neighbor.',
'T28':'Narrow red rectangular roof with skylights between neighboring tile roofs and parked vehicles. Prompt moved safely inside roof. Target is primary red roof; neighbors remain separate.',
'T29':'Complete gray L-shaped hall including long southern arm and its terminal roof. Initial truncated window was enlarged before inference. Yard, equipment and parked vehicles are negative context.',
'T30':'Large transparent/glass greenhouse roof; two smaller plastic/glass structures south are separate. Whole principal roof inspected; absent building classification must not veto the optical route.'}
prior=json.loads((OUT/'previous_visible_targets.json').read_text());duplicates=[]
for case in m['cases']:
    ident=case['body_id'][:3]
    image=OUT/('selection_T26_revised' if ident=='T26' else 'selection_final')/(ident+'.png')
    distances=[Point(case['anchor']).distance(wkt.loads(p['wkt'])) for p in prior]
    assert min(distances)>0, 'Target duplicates a previous visible roof'
    duplicates.append({'body_id':case['body_id'],'nearest_previous_visible_roof_m':min(distances)})
    case.update(ortho=str(OUT/'covers'/(ident+'_5cm.tif')),reviewed=True,target_extent=case['search_bounds'][:],
        lidar_compatibility='NOT_USED',refinement_policy='OPTICAL_PLANAR_CORE' if ident in ['T25','T28','T30'] else 'OPTICAL_FIDELITY',
        positive_points=case.get('positive_points',[]),negative_points=case.get('negative_points',[]),
        selection_observations=observations[ident],selection_review={'object_kind':'BUILDING','point_on_roof':True,
        'full_target_visible':True,'reviewer':'Codex','observations':observations[ident],
        'image':str(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
    if ident=='T26':case['negative_points']=[[391169,585718],[391186,585725]]
m.update(schema_version=1,crs='EPSG:3844',owner_status='PENDING_OWNER_REVIEW',
    scope='TEN_REVIEWED_ROOF_CASES_NOT_FULL_BUILDING_INVENTORY_OR_UNSEEN_HOLDOUT',
    selected_before_inference=True,duplicate_review=duplicates,
    selection_history='T29 extended; T26 original candidate rejected before inference because of old T08 proximity. Original drafts preserved.')
m.pop('status',None)
(OUT/'workflow_inputs.json').write_bytes(json.dumps(m,indent=2).encode())
print('Ten inspected cases bound to source image hashes.')
