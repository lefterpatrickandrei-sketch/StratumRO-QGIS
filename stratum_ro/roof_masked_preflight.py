"""Explicit mask-aware extension for reviewed roofs near genuine NoData."""
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from .evaluation_preflight import validate_selection


def validate_masked_selection(selection,*,manifest_dir,tile_dir,policies):
    report=validate_selection(selection,manifest_dir=manifest_dir,tile_dir=tile_dir)
    global_errors=[e for e in report['errors'] if not any(e.startswith(c['test_id']+':') for c in report['cases'])]
    if global_errors:return report
    for item,case in zip(report['cases'],selection['cases']):
        if policies.get(case['test_id'])!='MASKED_CONTEXT_REVIEW':continue
        if item['errors']!=['RGB search contains NoData; repair input coverage']:continue
        path=Path(case['tile']);path=path if path.is_absolute() else Path(tile_dir)/path
        # The standard validator has already checked identity, evidence hash,
        # extents, CRS and full context bounds before this particular failure.
        with rasterio.open(path) as src:
            a,b,c,d=case['search_bbox'];px=max(4.,(24-(c-a))/2);py=max(4.,(24-(d-b))/2)
            win=from_bounds(a-px,b-py,c+px,d+py,src.transform).round_offsets().round_lengths()
            mask=np.all(src.read_masks([1,2,3],window=win)>0,axis=0)
            x,y=case['search_center'];row,col=src.index(x,y)
            from rasterio.windows import Window
            point_valid=np.all(src.read_masks([1,2,3],window=Window(col,row,1,1))>0)
            if point_valid and mask.mean()>=.90 and (~mask).any():
                item.update(ready=True,errors=[],warnings=['NODATA_NEAR_TARGET_COMPLETENESS_UNCONFIRMED'],
                            valid_context_fraction=float(mask.mean()),policy='MASKED_CONTEXT_REVIEW')
    report['errors']=global_errors+[f"{c['test_id']}: {e}" for c in report['cases'] for e in c['errors']]
    report['ready']=not report['errors']
    return report
