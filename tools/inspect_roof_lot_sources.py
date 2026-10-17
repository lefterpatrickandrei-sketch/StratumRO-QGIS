"""Check coordinate correspondence/masks and render source-only selection evidence."""
from pathlib import Path
import argparse,json
import numpy as np,rasterio
from rasterio.windows import from_bounds
from rasterio.enums import Resampling
from rasterio.warp import reproject
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--selection',default='selection_draft.json')
parser.add_argument('--evidence-name',default='selection_evidence')
args=parser.parse_args();out=args.output_dir.resolve()
selection=json.loads((out/args.selection).read_text());evidence=out/args.evidence_name;evidence.mkdir(exist_ok=False)
checks=[]
for case in selection['cases']:
    name=case['body_id'].split(':')[0];path=out/'covers'/(name+'_5cm.tif')
    x,y=case['anchor']
    with rasterio.open(out/'cached_mosaic.vrt') as ref:
        win=from_bounds(x-6,y-6,x+6,y+6,ref.transform).round_offsets().round_lengths()
        cached=ref.read([1,2,3],window=win).astype(float);bounds=rasterio.windows.bounds(win,ref.transform)
        with rasterio.open(path) as src:
            native=src.read([1,2,3],window=from_bounds(*bounds,src.transform),out_shape=cached.shape,resampling=Resampling.bilinear).astype(float)
            crs_before=str(src.crs);tr=src.transform;shape=(src.height,src.width);b=src.bounds
        correlation=float(np.corrcoef(cached.ravel(),native.ravel())[0,1])
        # A nearly uniform glass patch can have low local correlation despite
        # matching coordinates. Independently compare the whole reviewed window.
        whole=from_bounds(*case['search_bounds'],ref.transform).round_offsets().round_lengths()
        context=ref.read([1,2,3],window=whole).astype(float)
        whole_bounds=rasterio.windows.bounds(whole,ref.transform)
        with rasterio.open(path) as src:
            context_native=src.read([1,2,3],window=from_bounds(*whole_bounds,src.transform),out_shape=context.shape,resampling=Resampling.bilinear).astype(float)
        context_correlation=float(np.corrcoef(context.ravel(),context_native.ravel())[0,1])
        if context_correlation<.9:raise ValueError(name+' full-window coordinate correspondence failed')
        mw=from_bounds(*b,ref.transform).round_offsets().round_lengths()
        mask=np.all(ref.read_masks([1,2,3],window=mw)>0,axis=0).astype('uint8')
        mask_tr=ref.window_transform(mw)
        valid=np.zeros(shape,dtype='uint8')
        reproject(mask,valid,src_transform=mask_tr,src_crs=ref.crs,dst_transform=tr,dst_crs=ref.crs,resampling=Resampling.nearest)
        interpreted_crs=ref.crs
    with rasterio.open(path,'r+') as src:
        src.crs=interpreted_crs;src.write_mask(valid*255)
        rgb=np.moveaxis(src.read([1,2,3]),0,-1)
        a,bb,c,d=case['search_bounds'];w=from_bounds(a,bb,c,d,src.transform).round_offsets().round_lengths()
        search_valid=float(np.all(src.read_masks([1,2,3],window=w)>0,axis=0).mean())
    checks.append({'body_id':case['body_id'],'crop_crs_before_this_check':crs_before,'original_sid_crs_metadata':'EMPTY','interpreted_crs':str(interpreted_crs),
        'local_patch_correlation':correlation,'whole_window_correlation':context_correlation,'transform_unchanged':True,'datum_independently_validated':False,
        'mask_source':'Existing project cache masks, nearest-neighbor transfer; not RGB-darkness threshold',
        'valid_search_fraction':search_valid})
    fig,ax=plt.subplots(figsize=(10,10));ax.imshow(np.dstack([rgb,valid*255]),extent=[b.left,b.right,b.bottom,b.top])
    ax.plot([a,c,c,a,a],[bb,bb,d,d,bb],color='orange',lw=1)
    ax.plot(x,y,'r+',ms=12);ax.set_title(name+' / SOURCE ONLY / amber=search window, red=prompt')
    ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(axis='x',rotation=45);ax.grid(alpha=.25)
    fig.tight_layout();fig.savefig(evidence/(name+'.png'),dpi=125);plt.close(fig)
(out/('coordinate_checks_'+args.evidence_name+'.json')).write_bytes(json.dumps(checks,indent=2).encode())
print(json.dumps(checks))
