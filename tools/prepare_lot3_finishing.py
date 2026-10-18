"""Record the existing reviewed Lot3 targets for the finishing run."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'workspace/reviews/lot3_finishing_20261017'
out.mkdir(exist_ok=True)
source=ROOT/'workspace/reviews/fusion_complete_20261017/workflow_inputs_v2.json'
manifest=json.loads(source.read_text(encoding='utf-8'))
manifest['crs']='EPSG:3844'
manifest['previous_manifest']=str(source)
manifest['previous_manifest_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
manifest['cases']=[c for c in manifest['cases'] if c['body_id'] in ['T17:C1','T17:C2','T18:C1']]
observations={
    'T17:C1':'Red and gray-brown connected courtyard roof south of the long gray building. Courtyard is enclosed by roof connections; raw mask breaks one supported internal connection. Distinct from T17:C2.',
    'T17:C2':'Elongated gray roof north of the red courtyard body, with side projections. Corrected RGB anchor is inside the roof. Keep this as a distinct body.',
    'T18:C1':'Red-brown main roof and articulated western/lower wings. The latest full roof hypothesis includes supported wings; polish edges without hiding the wings or forcing a rectangle. Annex identities still require owner review.'}
for case in manifest['cases']:
    ident=case['body_id']
    image=ROOT/'workspace/reviews/cadastral_workflow_v4_20261017'/('T17_baseline_qgis.png' if ident.startswith('T17') else 'T18_current_qgis.png')
    case['selection_review']={'object_kind':'BUILDING','point_on_roof':True,'full_target_visible':True,
         'reviewer':'Codex','observations':observations[ident],'image':str(image),
         'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
manifest['owner_status']='NEEDS_FINISHING_NOT_ACCEPTED'
(out/'workflow_inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(out/'workflow_inputs.json')
