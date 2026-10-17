"""Compare reviewed RGB prompts with local LiDAR guidance; isolated experiment."""
from pathlib import Path
import json,sys,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import reproject,Resampling
from rasterio.features import shapes
from scipy.ndimage import label
from shapely.geometry import shape,Point,box
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import torch
from stratum_ro.fusion_guidance import select_fusion_prompt
from stratum_ro.sam2_engine import SAM2BuildingSegmenter
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.evaluation_preflight import validate_selection,require_ready

OUT=ROOT/'workspace/reviews/fusion_demo_20261017'
MANIFEST=ROOT/'workspace/reviews/lot3_revision_v3_20261016/selection_manifest.json'
TILES=ROOT/'workspace/reviews/prompt_recovery_20261013/full_aoi'
AUDIT=ROOT/'workspace/reviews/lidar_audit_20261017'


def aligned_evidence(path,transform,shape_,nodata=0):
    result=np.full(shape_,nodata,dtype='float32')
    with rasterio.open(path) as src:
        reproject(rasterio.band(src,1),result,src_transform=src.transform,
                  src_crs=src.crs,dst_transform=transform,dst_crs='EPSG:3844',
                  src_nodata=src.nodata,dst_nodata=nodata,resampling=Resampling.nearest)
    return result


def prompted_component(mask,anchor_px,transform):
    labs,_=label(mask)
    c,r=np.floor(anchor_px).astype(int)
    ident=labs[r,c] if 0<=r<mask.shape[0] and 0<=c<mask.shape[1] else 0
    if not ident:return None
    selected=labs==ident
    polygons=[shape(g) for g,v in shapes(selected.astype('uint8'),mask=selected,transform=transform) if v==1]
    return max(polygons,key=lambda g:g.area) if polygons else None


def main():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    preflight=validate_selection(manifest,manifest_dir=MANIFEST.parent,tile_dir=TILES)
    require_ready(preflight)
    OUT.mkdir(parents=True,exist_ok=False)
    (OUT/'preflight.json').write_text(json.dumps(preflight,indent=2),encoding='utf-8')
    (OUT/'selection_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    model=SAM2BuildingSegmenter()
    records=[];prompts=[];windows=[];cases=[]
    for case in manifest['cases']:
        if case['test_id'] not in ['T17','T18','T20']:continue
        ident=case['test_id'];a,b,c,d=case['search_bbox']
        path=Path(case['tile']);path=path if path.is_absolute() else TILES/path
        with rasterio.open(path) as src:
            win=from_bounds(a-4,b-4,c+4,d+4,src.transform).round_offsets().round_lengths()
            if win.col_off<0 or win.row_off<0 or win.col_off+win.width>src.width or win.row_off+win.height>src.height:
                raise ValueError(ident+': incomplete crop')
            rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1)
            valid=np.all(src.read_masks([1,2,3],window=win)>0,axis=0)
            if not valid.all() or np.any(np.all(rgb==0,axis=2)):
                raise ValueError(ident+': missing RGB coverage')
            tr=src.window_transform(win);profile=src.profile.copy()
        profile.update(driver='GTiff',height=rgb.shape[0],width=rgb.shape[1],count=3,transform=tr,nodata=None,compress='deflate')
        with rasterio.open(OUT/(ident+'_ortho.tif'),'w',**profile) as dst:
            dst.write(np.moveaxis(rgb,-1,0));dst.write_mask(valid.astype('uint8')*255)
        counts=aligned_evidence(AUDIT/'class6_density_1m.tif',tr,rgb.shape[:2])
        height=aligned_evidence(AUDIT/'relative_surface_1m.tif',tr,rgb.shape[:2],-9999)
        lidar_valid=np.isfinite(height)&(height!=-9999)
        guidance=select_fusion_prompt(case['search_center'],tr,counts,height,lidar_valid,
                                     lidar_compatible=True)
        guidance['compatibility_status']='EXPERIMENTAL_STEREO70_HYPOTHESIS_NOT_CERTIFIED'
        # The full reviewed search envelope is kept. A seed bounds box never clips the roof.
        inv=~tr
        bx0,by0=inv*(a,d);bx1,by1=inv*(c,b)
        bbox=np.array([bx0,by0,bx1,by1],dtype='float32')
        encode_start=time.perf_counter();model.set_image(rgb,tr)
        if model.device=='cuda':torch.cuda.synchronize()
        encode_s=time.perf_counter()-encode_start
        fig,axes=plt.subplots(1,2,figsize=(16,8))
        extent=[tr.c,tr.c+rgb.shape[1]*tr.a,tr.f+rgb.shape[0]*tr.e,tr.f]
        details=[]
        for ax,mode,point in zip(axes,['RGB_REVIEWED_POINT','FUSION_GUIDANCE'],[case['search_center'],guidance['point']]):
            px=inv*tuple(point)
            begin=time.perf_counter()
            with torch.inference_mode():
                masks,scores,_=model.predictor.predict(point_coords=np.array([px],dtype='float32'),point_labels=np.array([1],dtype='int32'),box=bbox,multimask_output=True)
            if model.device=='cuda':torch.cuda.synchronize()
            elapsed=time.perf_counter()-begin
            options=[]
            for mask,score in zip(masks,scores):
                geom=prompted_component(mask,px,tr)
                # Keep correspondence to the same reviewed object in both routes.
                if geom is not None and geom.is_valid and geom.area>=8 and geom.covers(Point(*case['search_center'])):
                    options.append((float(score),geom))
            best=max(options,key=lambda item:item[0]) if options else None
            detail={'mode':mode,'point':point,'decode_s':elapsed,'status':'NO_MASK_FOR_REVIEWED_OBJECT'}
            ax.imshow(rgb,extent=extent)
            if best:
                score,raw=best
                geom,diag=simple_roof_geometry(raw)
                crop=box(extent[0],extent[2],extent[1],extent[3])
                touches=raw.distance(crop.boundary)<.3
                status='POSSIBLY_TRUNCATED_REQUIRES_REVIEW' if touches else 'PENDING_OWNER_REVIEW'
                detail.update(score=score,area_m2=geom.area,vertices=len(geom.exterior.coords)-1,status=status,simple_method=diag.get('method'),touches_crop=touches)
                records.append({'test_id':ident,'mode':mode,'route':guidance['route'] if mode=='FUSION_GUIDANCE' else 'RGB_REVIEWED_POINT','status':status,'owner_verdict':'PENDING_OWNER_REVIEW','score':score,'area_m2':geom.area,'vertices':len(geom.exterior.coords)-1,'geometry':geom})
                ax.plot(*raw.exterior.xy,color='#b24aff',lw=1,label='Masca SAM2 bruta')
                ax.plot(*geom.exterior.xy,color='#00ffff' if mode=='RGB_REVIEWED_POINT' else '#00ff00',lw=2,label='Forma simplificata - NEVERIFICATA')
            prompts.append({'test_id':ident,'mode':mode,'source':guidance['source'] if mode=='FUSION_GUIDANCE' else 'REVIEWED_RGB_ANCHOR','geometry':Point(*point)})
            ax.plot(*point,'+',color='yellow',markersize=12,label='Punct de ghidare')
            ax.set_title(ident+' / '+mode+'\n'+detail['status']);ax.axis('off');ax.legend(fontsize=8)
            details.append(detail)
        fig.suptitle('EXPERIMENT LOCAL - puncte revizuite, nu detector automat; rezultate neacceptate')
        fig.tight_layout();fig.savefig(OUT/(ident+'_comparison.png'),dpi=145);plt.close(fig)
        windows.append({'test_id':ident,'geometry':box(a,b,c,d)})
        cases.append({'test_id':ident,'guidance':guidance,'encode_s_shared':encode_s,'comparison':details})
        print(json.dumps(cases[-1]),flush=True)
    gpkg=OUT/'fusion_demo.gpkg'
    if records:gpd.GeoDataFrame(records,crs=3844).to_file(gpkg,layer='IPOTEZE_NEACCEPTATE',driver='GPKG')
    gpd.GeoDataFrame(prompts,crs=3844).to_file(gpkg,layer='PUNCTE_GHIDARE',driver='GPKG')
    gpd.GeoDataFrame(windows,crs=3844).to_file(gpkg,layer='FERESTRE_COMPARATIE',driver='GPKG')
    report={'scope':'LOCAL_PROMPT_GUIDANCE_EXPERIMENT_NOT_FULL_PRODUCTION_OR_AUTOMATIC_DETECTION',
            'lidar_crs':'EPSG3844 hypothesis only','cases':cases,'owner_verdict':'PENDING_OWNER_REVIEW',
            'checkpoint_sha256':hashlib.sha256(Path(model.checkpoint_path).read_bytes()).hexdigest(),
            'speed_claim':'None: shared encoding and different prompts, no controlled end-to-end benchmark'}
    (OUT/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')


if __name__=='__main__':main()
