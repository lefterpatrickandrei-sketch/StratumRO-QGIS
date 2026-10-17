"""Verify native/cached pixel correspondence before applying the project CRS interpretation."""
from pathlib import Path
import json
import rasterio,numpy as np
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'workspace/reviews/lot3_repairs_20261017'
m=json.loads((OUT/'workflow_inputs.json').read_text())
old=json.loads((ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json').read_text())
checks=[]
for scene in sorted({c['body_id'].split(':')[0] for c in m['cases']}):
    case=next(c for c in m['cases'] if c['body_id'].startswith(scene+':'))
    ref=Path(next(c for c in old['cases'] if c['test_id']==scene)['tile'])
    if not ref.is_absolute():ref=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi'/ref
    x,y=case['anchor'];bounds=[x-6,y-6,x+6,y+6]
    with rasterio.open(ref) as s:
        w=from_bounds(*bounds,s.transform).round_offsets().round_lengths();cached=s.read([1,2,3],window=w).astype(float)
        wb=rasterio.windows.bounds(w,s.transform);crs=s.crs
    with rasterio.open(case['ortho']) as s:
        native=s.read([1,2,3],window=from_bounds(*wb,s.transform),out_shape=cached.shape,resampling=Resampling.bilinear).astype(float)
        original_crs=str(s.crs);transform=list(s.transform)
    corr=float(np.corrcoef(cached.ravel(),native.ravel())[0,1])
    if corr<.9:raise ValueError(scene+' native/cache pixel correspondence not verified')
    with rasterio.open(case['ortho'],'r+') as dst:dst.crs=crs
    checks.append({'scene':scene,'original_native_crs':original_crs,'interpreted_crs':str(crs),
        'pixel_correlation_at_same_world_coordinates':corr,'mean_absolute_rgb_difference':float(np.abs(cached-native).mean()),
        'transform_unchanged':True,'datum_independently_validated':False,
        'interpretation':'Same coordinate mapping as existing project cache, not an independent geodetic certification'})
(OUT/'coordinate_checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks))
