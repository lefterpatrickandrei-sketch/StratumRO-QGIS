"""Automatic, resumable scan of a declared RGB mosaic. No manual roof prompts.

CLI defaults are local only. A configuration JSON binds source order, models,
resolution and optional contextual LiDAR. All views and uncertain objects remain
auditable. This is a regional proposal baseline, not a certified building model.
"""
from pathlib import Path
import sys,json,time,hashlib,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from shapely.geometry import shape,mapping,box
from stratum_ro.regional_roofs import (RegionalRoofConfig,OrthoMosaic,plan_windows,
    sample_evidence,vectorize_automatic_masks,deduplicate_candidates,
    simplify_regional_roof,sha256_file,expand_edge_candidate)
from stratum_ro.regional_review import clip_to_valid_mosaic


def write_json(path,value):
    temp=path.with_suffix(path.suffix+'.partial')
    temp.write_text(json.dumps(value,indent=2,allow_nan=False),encoding='utf-8')
    os.replace(temp,path)


def serialize(records):
    return [{**r,'geometry':mapping(r['geometry'])} for r in records]


def deserialize(records):
    return [{**r,'geometry':shape(r['geometry'])} for r in records]


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    parser.add_argument('--audit-only',action='store_true')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    cfg_path=Path(args.config).resolve();request=json.loads(cfg_path.read_text())
    config=RegionalRoofConfig(**request.get('parameters',{}))
    paths=[ROOT/p for p in request['orthophotos']]
    mosaic=OrthoMosaic(paths,max_pixels=config.max_window_pixels)
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=args.resume)
    windows=plan_windows(mosaic.bounds,config)
    sources=[{**item,'sha256':sha256_file(item['path'])} for item in mosaic.sources]
    modules=['stratum_ro/regional_roofs.py','stratum_ro/regional_review.py',
             'stratum_ro/roof_simple_geometry.py','tools/run_regional_roofs.py']
    code={p:sha256_file(ROOT/p) for p in modules}
    lidar={name:dict(path=str((ROOT/request[name]).resolve()),sha256=sha256_file(ROOT/request[name]))
           for name in ['height','class6'] if request.get(name)}
    checkpoint=ROOT/request['checkpoint'];checkpoint_hash=sha256_file(checkpoint)
    fingerprint=hashlib.sha256(json.dumps(dict(request=request,sources=sources,code=code,
        lidar=lidar,checkpoint=checkpoint_hash),sort_keys=True).encode()).hexdigest()
    binding=out/'input_audit.json'
    if binding.exists() and json.loads(binding.read_text())['fingerprint']!=fingerprint:
        raise ValueError('Resume inputs, code, model or configuration changed; use a new output directory')
    write_json(binding,dict(scope='AUTOMATIC_REGIONAL_PROPOSALS_NOT_VALIDATED_INVENTORY',
        fingerprint=fingerprint,config=request,sources=sources,code_sha256=code,
        lidar=lidar,checkpoint_sha256=checkpoint_hash,source_bounds=mosaic.bounds,
        source_bbox_area_m2=box(*mosaic.bounds).area,window_count=len(windows),
        no_reference_contours_or_reviewed_anchors=True,cloud_uploads=False))
    write_json(out/'window_plan.json',windows)
    if args.audit_only:
        print(json.dumps(dict(status='AUDIT_ONLY_NO_INFERENCE',windows=len(windows),bounds=mosaic.bounds)),flush=True)
        return
    (out/'windows').mkdir(exist_ok=args.resume)
    import torch
    from sam2.build_sam import build_sam2
    from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
    device='cuda' if torch.cuda.is_available() else 'cpu'
    model=build_sam2(request.get('model_cfg','sam2_hiera_t.yaml'),str(checkpoint),device=device)
    generator=SAM2AutomaticMaskGenerator(model,points_per_side=config.points_per_side,
        points_per_batch=config.points_per_batch,pred_iou_thresh=config.pred_iou_thresh,
        stability_score_thresh=config.stability_score_thresh,min_mask_region_area=0,
        output_mode='binary_mask')
    if device=='cuda':torch.cuda.reset_peak_memory_stats()
    start=time.perf_counter(); all_records=[];coverage=[]
    for num,window in enumerate(windows,1):
        path=out/'windows'/(window['window_id']+'.json')
        if path.exists():
            saved=json.loads(path.read_text()); all_records.extend(deserialize(saved['candidates']))
            coverage.append(saved['coverage']);continue
        begin=time.perf_counter()
        rgb,valid,tr,used=mosaic.read(window['context'],config.resolution_m)
        yy,xx=np.indices(valid.shape)
        gx,gy=tr*(xx+.5,yy+.5)
        a,b,c,d=window['core'];core=(gx>=a)&(gx<c)&(gy>=b)&(gy<d)
        core_pixels=int(core.sum());valid_core=int((core&valid).sum())
        cov=dict(**window,core_pixels=core_pixels,valid_core_pixels=valid_core,
            valid_core_area_m2=float(valid_core*config.resolution_m**2),
            source_count=len(used),model_ran=False,mask_count=0)
        records=[];exclusions={}
        if valid_core:
            height=sample_evidence(ROOT/request['height'] if request.get('height') else None,tr,valid.shape)
            counts=sample_evidence(ROOT/request['class6'] if request.get('class6') else None,tr,valid.shape)
            try:
                with torch.inference_mode():
                    masks=generator.generate(rgb)
                if device=='cuda':torch.cuda.synchronize()
                records,exclusions=vectorize_automatic_masks(masks,rgb,valid,tr,height,counts,config,window['window_id'])
                cov.update(model_ran=True,mask_count=len(masks),status='SCANNED_NOT_PROOF_OF_NO_OMISSIONS')
                del masks
            except torch.cuda.OutOfMemoryError as exc:
                torch.cuda.empty_cache();cov.update(status='FAILED_GPU_OOM',error=str(exc))
        else:cov['status']='NO_VALID_RGB_IN_CORE'
        cov['elapsed_s']=time.perf_counter()-begin
        saved=dict(coverage=cov,excluded_component_counts=exclusions,candidates=serialize(records))
        write_json(path,saved);all_records.extend(records);coverage.append(cov)
        print(json.dumps(dict(window=num,total=len(windows),id=window['window_id'],
            status=cov['status'],objects=len(records),elapsed_s=round(cov['elapsed_s'],3))),flush=True)
    selected,duplicates=deduplicate_candidates(all_records)
    (out/'edge_retries').mkdir(exist_ok=args.resume)
    for index,item in enumerate(selected):
        if not item['touches_window'] or item['route']=='LIKELY_VEGETATION_REVIEW':continue
        path=out/'edge_retries'/(item['candidate_id']+'.json')
        if path.exists():
            selected[index]=deserialize([json.loads(path.read_text())['candidate']])[0];continue
        revised,audit=expand_edge_candidate(item,mosaic,generator.predictor,config,
            ROOT/request['height'] if request.get('height') else None,
            ROOT/request['class6'] if request.get('class6') else None)
        write_json(path,dict(audit=audit,candidate=serialize([revised])[0]));selected[index]=revised
    selected,extra_duplicates=deduplicate_candidates(selected)
    duplicates.extend(extra_duplicates)
    valid_mask_clips=[]
    for item in selected:
        raw=item['geometry']; refined,diag=simplify_regional_roof(raw)
        if item['touches_nodata']:
            refined,removed=clip_to_valid_mosaic(refined,mosaic,config.resolution_m)
            if refined.is_empty:raise ValueError('Final geometry lost valid source coverage: '+item['candidate_id'])
            if removed>0:valid_mask_clips.append(dict(candidate_id=item['candidate_id'],removed_m2=removed))
        item['raw_geometry']=raw;item['geometry']=refined
        item.update(method=diag['method'],geometry_status=diag['status'],owner_verdict='PENDING_OWNER_REVIEW')
        if item['touches_window'] or item['touches_nodata']:
            item['geometry_status']='INCOMPLETE_CONTEXT_REVIEW'
    # No clipping/union to make intersecting roof identities appear resolved.
    if selected:
        tree=__import__('shapely').STRtree([r['geometry'] for r in selected])
        for i,item in enumerate(selected):
            item['overlap_conflicts']=sum(1 for j in tree.query(item['geometry'],predicate='intersects')
                if int(j)!=i and item['geometry'].intersection(selected[int(j)]['geometry']).area>1.)
    import geopandas as gpd
    gpkg=out/'regional_roofs.gpkg'
    for layername,records in [('ROOF_CANDIDATES',[r for r in selected if r['route']=='ROOF_CANDIDATE_REVIEW']),
        ('OPTICAL_UNKNOWN',[r for r in selected if r['route']=='OPTICAL_UNKNOWN_REVIEW']),
        ('LIKELY_VEGETATION',[r for r in selected if r['route']=='LIKELY_VEGETATION_REVIEW'])]:
        if records:
            flat=[{k:v for k,v in r.items() if k!='raw_geometry'} for r in records]
            gpd.GeoDataFrame(flat,crs=3844).to_file(gpkg,layer=layername,driver='GPKG')
    if selected:
        gpd.GeoDataFrame([dict(candidate_id=r['candidate_id'],route=r['route'],geometry=r['raw_geometry'])
            for r in selected],crs=3844).to_file(gpkg,layer='RAW_SELECTED_OBSERVATIONS',driver='GPKG')
    gpd.GeoDataFrame([dict(window_id=w['window_id'],status=w['status'],
        valid_area_m2=w['valid_core_area_m2'],geometry=box(*w['core'])) for w in coverage],
        crs=3844).to_file(gpkg,layer='SCAN_COVERAGE',driver='GPKG')
    write_json(out/'duplicate_lineage.json',duplicates)
    write_json(out/'final_valid_mask_clips.json',valid_mask_clips)
    routes={route:sum(r['route']==route for r in selected) for route in
        ['ROOF_CANDIDATE_REVIEW','OPTICAL_UNKNOWN_REVIEW','LIKELY_VEGETATION_REVIEW']}
    failures=[w['window_id'] for w in coverage if w['status'].startswith('FAILED')]
    report=dict(status='SCAN_COMPLETED_WITH_FAILED_WINDOWS' if failures else 'SCAN_COMPLETED_UNVALIDATED',
        fingerprint=fingerprint,windows_planned=len(windows),windows_scanned=sum(w['model_ran'] for w in coverage),
        windows_no_valid_rgb=sum(w['status']=='NO_VALID_RGB_IN_CORE' for w in coverage),failed_windows=failures,
        valid_core_area_m2=sum(w['valid_core_area_m2'] for w in coverage),
        raw_observations=len(all_records),deduplicated_observations=len(selected),routes=routes,
        incomplete_context=sum(r['geometry_status']=='INCOMPLETE_CONTEXT_REVIEW' for r in selected),
        overlap_conflicts=sum(r['overlap_conflicts']>0 for r in selected),device=device,
        execution_elapsed_s=time.perf_counter()-start,scope='WHOLE_SOURCE_MOSAIC_AUTO_SCAN_NOT_COMPLETE_BUILDING_INVENTORY',
        peak_cuda_allocated_bytes=torch.cuda.max_memory_allocated() if device=='cuda' else None,
        peak_cuda_reserved_bytes=torch.cuda.max_memory_reserved() if device=='cuda' else None,
        ground_footprints_generated=False,accuracy=None,recall=None,clean_training_labels=False,
        limitations=['Class-agnostic SAM grid can miss small objects and merge roofs.',
            'Context LiDAR CRS/acquisition correspondence is not independently certified.',
            'Roof routing is an experimental heuristic, not a trained semantic classifier.',
            'One expanded-context retry is attempted; unresolved source/window edges stay flagged.',
            'Unknown proposals are retained; zero Class6 is not an absence verdict.'])
    write_json(out/'report.json',report)
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
