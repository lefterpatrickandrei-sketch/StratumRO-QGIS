"""Execute the product roof workflow from explicit inputs into a new review pack."""
from pathlib import Path
import argparse,json,sys,hashlib,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
import rasterio
from rasterio.warp import reproject,Resampling
import geopandas as gpd
from rasterio.windows import from_bounds,Window
from stratum_ro.api.service import PlatformService


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--max-vertices',type=int,default=20)
    parser.add_argument('--compare-to',type=Path,help='Previous roof hypotheses, for post-run review only; never model prompts')
    args=parser.parse_args();manifest_path=args.manifest.resolve()
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('schema_version')!=1 or not manifest.get('cases'):raise ValueError('Reviewed workflow manifest required')
    ids=[c['body_id'] for c in manifest['cases']]
    if len(set(ids))!=len(ids):raise ValueError('Duplicate body identities')
    out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=False)
    (out/'.gitignore').write_text('*.gpkg-wal\n*.gpkg-shm\n*.qgz~\n*.qgs~\n',encoding='utf-8')
    (out/'inputs.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    flow=PlatformService(ROOT).create_cadastral_roof_workflow(max_vertices=args.max_vertices)
    report=[];records=[];raw=[];current=None;sources={}
    def resolve(value):
        path=Path(value)
        return path if path.is_absolute() else (manifest_path.parent/path).resolve()
    for case in manifest['cases']:
        if not case.get('reviewed') or not case.get('selection_observations'):raise ValueError('Documented selection review required')
        path=resolve(case['ortho'])
        scene_key=(str(path),case.get('lidar_compatibility','NOT_USED'),tuple(case['search_bounds']))
        if current!=scene_key:
            with rasterio.open(path) as src:
                if src.crs!=rasterio.crs.CRS.from_epsg(3844):raise ValueError('Source raster CRS mismatch')
                a,b,c,d=case['search_bounds']
                win=from_bounds(a-4,b-4,c+4,d+4,src.transform)
                col0,row0=int(np.floor(win.col_off)),int(np.floor(win.row_off))
                col1,row1=int(np.ceil(win.col_off+win.width)),int(np.ceil(win.row_off+win.height))
                if col0<0 or row0<0 or col1>src.width or row1>src.height:raise ValueError('NEEDS_COMPLETE_IMAGE_COVERAGE')
                win=Window(col0,row0,col1-col0,row1-row0)
                rgb=np.moveaxis(src.read([1,2,3],window=win),0,-1)
                valid=np.all(src.read_masks([1,2,3],window=win)>0,axis=0)
                transform=src.window_transform(win)
                profile=src.profile.copy()
                profile.update(driver='GTiff',height=rgb.shape[0],width=rgb.shape[1],count=3,transform=transform,nodata=None,compress='deflate')
            with rasterio.open(out/(case['body_id'].replace(':','_')+'_ortho.tif'),'w',**profile) as crop:
                crop.write(np.moveaxis(rgb,-1,0));crop.write_mask(valid.astype('uint8')*255)
            evidence={}
            for key,nodata in [('relative_height',-9999),('building_counts',0)]:
                if key not in manifest:continue
                ep=resolve(manifest[key]);grid=np.full(valid.shape,nodata,dtype='float32')
                with rasterio.open(ep) as es:
                    if es.crs!=rasterio.crs.CRS.from_epsg(3844):raise ValueError('Evidence CRS mismatch')
                    reproject(rasterio.band(es,1),grid,src_transform=es.transform,src_crs=es.crs,
                              dst_transform=transform,dst_crs='EPSG:3844',src_nodata=es.nodata,
                              dst_nodata=nodata,resampling=Resampling.nearest)
                evidence[key]=grid;sources[str(ep)]=sha256(ep)
            use=case.get('lidar_compatibility')=='EXPERIMENTAL_STEREO70_HYPOTHESIS'
            if case.get('lidar_compatibility') not in ['EXPERIMENTAL_STEREO70_HYPOTHESIS','NOT_USED']:
                raise ValueError('Explicit supported LiDAR compatibility state required')
            if use and len(evidence)!=2:raise ValueError('LiDAR evidence missing')
            kwargs={}
            if evidence:
                kwargs=dict(relative_height=evidence['relative_height'],building_counts=evidence['building_counts'],
                            lidar_valid=np.isfinite(evidence['relative_height'])&(evidence['relative_height']!=-9999))
            sources[str(path)]=sha256(path)
            flow.set_scene(rgb,transform,valid,crs='EPSG:3844',lidar_compatible=use,
                           provenance={'ortho':str(path),'lidar_compatibility':case.get('lidar_compatibility')},**kwargs)
            current=scene_key
        start=time.perf_counter()
        result=flow.extract(case['body_id'],case['anchor'],case['search_bounds'],reviewed=True)
        geometry=result.pop('geometry');original=result.pop('raw_geometry')
        result['duration_s']=time.perf_counter()-start
        report.append(result)
        print(json.dumps(result),flush=True)
        if geometry is not None:
            records.append({'body_id':case['body_id'],'test_id':case['body_id'].split(':')[0],
                'route':result['guidance']['route'],'status':result['status'],'method':result['diagnostic']['method'],
                'owner_verdict':result['owner_verdict'],'geometry_role':result['geometry_role'],
                'ground_status':'NOT_MEASURED','vertices':result['vertices'],'sam2_score':result['sam2_score'],
                'review_reasons':';'.join(result['review_reasons']),'geometry':geometry})
        if original is not None:raw.append({'body_id':case['body_id'],'geometry':original})
    if records:gpd.GeoDataFrame(records,crs=3844).to_file(out/'cadastral_review.gpkg',layer='ROOF_HYPOTHESES',driver='GPKG')
    if raw:gpd.GeoDataFrame(raw,crs=3844).to_file(out/'cadastral_review.gpkg',layer='RAW_OPTICAL_MASKS',driver='GPKG')
    final={'scope':'PRODUCT_WORKFLOW_ON_REVIEWED_CANDIDATES_NOT_REGIONAL_DETECTOR',
           'ground_footprints_created':0,'owner_verdict':'PENDING_OWNER_REVIEW','cases':report,
           'source_hashes':sources,'input_manifest_sha256':sha256(manifest_path),
           'model_checkpoint_sha256':sha256(flow.segmenter.checkpoint_path),
           'model_config':flow.segmenter.model_cfg}
    final['geometry_max_exterior_vertices']=args.max_vertices
    if args.compare_to:
        baseline=gpd.read_file(args.compare_to,layer='IPOTEZE_RECTIFICATE')
        checks=[]
        for record in records:
            previous=baseline[baseline.body_id==record['body_id']]
            if len(previous)!=1:
                checks.append({'body_id':record['body_id'],'status':'BASELINE_CORRESPONDENCE_UNRESOLVED'});continue
            old=previous.iloc[0].geometry;new=record['geometry']
            checks.append({'body_id':record['body_id'],'iou':old.intersection(new).area/old.union(new).area,
                           'baseline_holes':len(old.interiors),'current_holes':len(new.interiors),
                           'topology_changed':len(old.interiors)!=len(new.interiors),
                           'automatic_adoption_allowed':False})
        final['comparison_to_previous_hypotheses']={'path':str(args.compare_to.resolve()),
             'sha256':sha256(args.compare_to),'is_ground_truth':False,'checks':checks}
    (out/'report.json').write_text(json.dumps(final,indent=2),encoding='utf-8')


if __name__=='__main__':main()
