"""Prepare a transparent wider-window experiment and a reviewed T18 annex."""
from pathlib import Path
import json,hashlib,copy
import rasterio
import numpy as np
from rasterio.merge import merge
from contextlib import ExitStack
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace/reviews/lot3_continuation_20261017'
if (OUT/'results').exists():raise FileExistsError('Preserve executed manifests and covers; use a new experiment directory')
source=ROOT/'workspace/reviews/lot3_finishing_20261017/workflow_inputs.json'
manifest=json.loads(source.read_text())
manifest['previous_manifest']=str(source)
manifest['previous_manifest_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
for c in manifest['cases']:
    bounds=c['search_bounds'];c['target_extent']=bounds[:]
    c['search_bounds']=[bounds[0]-6,bounds[1]-6,bounds[2]+6,bounds[3]+6]
    if c['body_id']=='T18:C1':c['search_bounds'][0]=bounds[0]-2
    c['selection_observations']+=' Continuation: search envelope expanded by 6m on each side to diagnose boundary contact; same reviewed anchor and target identity.'
    if c['body_id']=='T18:C1':
        c['selection_observations']+=' West expansion limited to 2m: a real NoData patch lies farther west, outside the reviewed target; full target extent and 4m valid context remain mandatory.'
annex=copy.deepcopy(manifest['cases'][-1])
annex.update(body_id='T18:C2',anchor=[390614.,585530.],search_bounds=[390603.,585518.,390626.,585545.],
             target_extent=[390605.,585521.,390623.,585541.],
             selection_observations='Brown pitched roof west of the main red hall, visibly distinct roof boundary with elevated Class6 returns. Hypothesis of a separate body, not an owner-confirmed cadastral identity.')
image=OUT/'T18_sensor_evidence.png'
annex['selection_review']={'object_kind':'BUILDING','point_on_roof':True,'full_target_visible':True,
    'reviewer':'Codex','observations':annex['selection_observations'],'image':str(image),
    'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest()}
manifest['cases'].append(annex)
manifest['experiment']='WIDER_SEARCH_AND_T18_ANNEX_NOT_AUTOMATIC_ADOPTION'
# Expanded requests cross the previous crops. Read real neighboring cached tiles,
# preserve explicit validity, and never fake coverage by padding/clipping RGB.
covers=OUT/'covers';covers.mkdir(exist_ok=True)
tiles=sorted((ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi').glob('cache_tile_Cluj-*_halo.tif'))
with ExitStack() as stack:
    sources=[stack.enter_context(rasterio.open(p)) for p in tiles]
    for ident in ['T17','T18']:
        cases=[c for c in manifest['cases'] if c['body_id'].startswith(ident)]
        bounds=[min(c['search_bounds'][0] for c in cases)-10,min(c['search_bounds'][1] for c in cases)-10,
                max(c['search_bounds'][2] for c in cases)+10,max(c['search_bounds'][3] for c in cases)+10]
        data,tr=merge(sources,bounds=bounds,indexes=[1,2,3],masked=True,target_aligned_pixels=True)
        valid=~np.any(np.ma.getmaskarray(data),axis=0)
        dest=covers/(ident+'_expanded_ortho.tif')
        with rasterio.open(dest,'w',driver='GTiff',height=data.shape[1],width=data.shape[2],count=3,
                           dtype=data.dtype,crs=sources[0].crs,transform=tr,compress='deflate') as dst:
            dst.write(data.filled(0));dst.write_mask(valid.astype('uint8')*255)
        for c in cases:c['ortho']=str(dest)
manifest['cover_sources']=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in tiles]
(OUT/'workflow_inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(OUT/'workflow_inputs.json')
