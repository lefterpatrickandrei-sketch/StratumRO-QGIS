"""Run the shared regional refiner on existing hypotheses; no reference shapes.

Writes a fresh stage-by-stage review package and never overwrites source data.
Optional regional observation matching recovers provenance lost by older runners.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import geopandas as gpd
from shapely.strtree import STRtree
from stratum_ro.api.service import PlatformService
from stratum_ro.regional_refinement import overlap_pairs, vertices


def sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n',encoding='utf-8')


def save_layer(path, name, records):
    if not records:return
    rows=[]
    for item in records:
        row={}
        for key,val in item.items():
            if key=='geometry':row[key]=val
            elif key.endswith('_geometry'):continue
            elif isinstance(val,(dict,list,tuple)):row[key]=json.dumps(val,ensure_ascii=False,allow_nan=False)
            elif isinstance(val,(str,int,float,bool)) or val is None:row[key]=val
        rows.append(row)
    gpd.GeoDataFrame(rows,crs='EPSG:3844').to_file(path,layer=name,driver='GPKG')


def run(request, output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    source=ROOT/request['source'];data=gpd.read_file(source,layer=request['layer'])
    if data.crs.to_epsg()!=3844:raise ValueError('EPSG:3844 hypotheses required')
    sources=[ROOT/p for p in request['orthophotos']]
    engine=PlatformService(ROOT).create_regional_roof_refiner(sources,request.get('parameters'),
        ROOT/request['height'] if request.get('height') else None,
        ROOT/request['class6'] if request.get('class6') else None)
    pool=None;tree=None;matches=[]
    if request.get('observations'):
        pool=gpd.read_file(ROOT/request['observations'],layer=request['observation_layer'])
        if pool.crs.to_epsg()!=3844:raise ValueError('Observation CRS differs')
        tree=STRtree(pool.geometry.values)
    records=[]
    existing=[]
    for source_spec in request.get('existing_lots',[]):
        prior=gpd.read_file(ROOT/source_spec['path'],layer=source_spec['layer'])
        if prior.crs.to_epsg()!=3844:raise ValueError('Existing lot CRS differs')
        for field,values in source_spec.get('include',{}).items():prior=prior[prior[field].isin(values)]
        for field,values in source_spec.get('exclude',{}).items():prior=prior[~prior[field].isin(values)]
        for idx,row in prior.iterrows():
            existing.append(dict(candidate_id=str(row.get('body_id',row.get('id',row.get('test_id',idx)))),
                source=source_spec['path']+'|'+source_spec['layer'],geometry=row.geometry))
    for _,row in data.iterrows():
        ident=str(row[request.get('id_field','body_id')]);g=row.geometry
        record=dict(candidate_id=ident,body_id=ident,geometry=g,baseline_geometry=g)
        if tree is not None:
            hits=[]
            for j in tree.query(g,predicate='intersects'):
                j=int(j);raw=pool.geometry.iloc[j];inter=g.intersection(raw).area
                hits.append((inter/g.union(raw).area,j))
            if hits:
                iou,j=max(hits)
                # This is geometric provenance recovery, never an identity label.
                if iou>=request.get('observation_match_iou',.60):
                    obs=pool.iloc[j]
                    record.update(source_observation_id=str(obs.get('candidate_id',j)),
                        observation_match_iou=float(iou),sam_score=float(obs.get('sam_score',0)))
                    original=obs.geometry
                    if original.geom_type=='MultiPolygon' and len(original.geoms)==1:
                        original=original.geoms[0]  # exact single-part unwrap, no discarded geometry
                    if original.geom_type=='Polygon' and original.is_valid:
                        record['geometry']=original
                    else:
                        # Do not repeat the old largest-part selection: retain
                        # the baseline and preserve the whole source separately.
                        record['upstream_reasons']=['MATCHED_SOURCE_MULTIPART_OR_INVALID_REVIEW']
                    matches.append(dict(candidate_id=ident,source_observation_id=record['source_observation_id'],iou=float(iou)))
        records.append(record)
    print('Bound',len(records),'hypotheses;',len(matches),'matched source observations.',flush=True)
    result=engine.refine(records,existing_roofs=existing)
    initial=result
    retry_audits=[];retry_attempts=[];retry_observations=[]
    replayed=False
    if request.get('replay_retry_package'):
        package=ROOT/request['replay_retry_package']
        cached=gpd.read_file(package,layer=request.get('replay_retry_layer','B4_RETRY_OBSERVATIONS')).set_index('candidate_id')
        prior_report=json.loads(package.with_name('report.json').read_text(encoding='utf-8'))
        retry_audits=prior_report['retry_audits']
        cached_attempts=gpd.read_file(package,layer='SAM2_ALL_ATTEMPTS')
        retry_attempts=[row.to_dict() for _,row in cached_attempts.iterrows()]
        audited={r['candidate_id'] for r in retry_audits}
        if set(cached.index)!=audited:raise ValueError('Cached retry audit IDs differ from geometries')
        updated=[]
        for record in records:
            new=dict(record)
            if record['candidate_id'] in audited:
                row=cached.loc[record['candidate_id']]
                new.update(geometry=row.geometry,sam_score=float(row.get('sam_score',0)))
                retry_observations.append(dict(new))
                assessed=engine.refine([new])
                if vertices(assessed['final'][0]['geometry'])>engine.config.max_vertices:
                    new=record
                    audit=next(a for a in retry_audits if a['candidate_id']==record['candidate_id'])
                    audit['post_geometry_gate_status']='DIAGNOSTIC_ONLY_COMPLEXITY_UNRESOLVED'
            updated.append(new)
        result=engine.refine(updated,existing_roofs=existing);replayed=True
    if request.get('retry_manifest'):
        from stratum_ro.evaluation_preflight import validate_selection,require_ready
        manifest_path=ROOT/request['retry_manifest']
        selection=json.loads(manifest_path.read_text(encoding='utf-8'))
        preflight=validate_selection(selection,manifest_dir=manifest_path.parent,tile_dir=ROOT)
        save_json(output/'retry_preflight.json',preflight);require_ready(preflight)
        from stratum_ro.sam2_engine import SAM2BuildingSegmenter
        segmenter=SAM2BuildingSegmenter(checkpoint_path=str(ROOT/request['checkpoint']))
        wanted={bid for c in selection['cases'] for bid in c['source_body_ids']}
        unknown=wanted-{r['candidate_id'] for r in records}
        if unknown:raise ValueError('Retry selection IDs absent from this input: '+str(unknown))
        updated=[]
        for record in records:
            if record['candidate_id'] not in wanted:
                updated.append(record);continue
            print('SAM2 retry',record['candidate_id'],flush=True)
            new,audit=engine.retry_observation(record,segmenter)
            audit['candidate_id']=record['candidate_id']
            for attempt in audit['attempts']:
                retry_attempts.append({**attempt,'candidate_id':record['candidate_id'],
                    'reasons':attempt['reasons']})
            # Geometry goes to GPKG, numeric outcomes to JSON.
            audit['attempts']=[{k:v for k,v in a.items() if k!='geometry'} for a in audit['attempts']]
            retry_audits.append(audit);retry_observations.append(new);updated.append(new)
        result=engine.refine(updated,existing_roofs=existing)
    gpkg=output/'refinement.gpkg'
    if pool is not None:
        pool.to_file(gpkg,layer='SOURCE_OBSERVATIONS_POOL',driver='GPKG')
    save_layer(gpkg,'EXISTING_OTHER_LOTS',existing)
    for layer,key in [('B0_BASELINE','baseline'),('B1_OBSERVATIONS','observed'),
                      ('B2_DEDUPLICATED','deduplicated'),('B3_SIMPLE_FIT','simplified'),('B4_FINAL_REVIEW','final')]:
        save_layer(gpkg,layer,(result if key=='final' else initial)[key])
    if retry_audits:
        save_layer(gpkg,'B3_BEFORE_RETRY_QA',initial['final'])
        save_layer(gpkg,'B4_RETRY_OBSERVATIONS',retry_observations)
        save_layer(gpkg,'SAM2_ALL_ATTEMPTS',retry_attempts)
        save_json(output/'retry_audit.json',retry_audits)
    duplicate_ids={r['suppressed'] for r in result['duplicate_links']}
    save_layer(gpkg,'DUPLICATE_OBSERVATIONS',[r for r in result['observed'] if r['candidate_id'] in duplicate_ids])
    save_layer(gpkg,'UNRESOLVED_REVIEW',[r for r in result['final'] if r['review_reasons']])
    rejected=[]
    if request.get('rejected_layer'):
        frame=gpd.read_file(source,layer=request['rejected_layer'])
        for _,row in frame.iterrows():
            g=row.geometry;ident=str(row.get('rej_id',len(rejected)))
            try:
                from stratum_ro.regional_refinement import scene_evidence
                scene=engine.observe(g)
                evidence=scene_evidence(g,scene['rgb'],scene['valid'],scene['transform'],scene['height'],scene['counts'])
            except (ValueError,OSError) as exc:evidence={'error':str(exc)}
            rejected.append(dict(candidate_id=ident,geometry=g,previous_reason=str(row.get('reject_reason','')),
                qa_status='PREVIOUSLY_REJECTED_UNVERIFIED_RECALL_QUEUE',evidence=evidence,
                owner_verdict='PENDING_OWNER_REVIEW'))
        save_layer(gpkg,'B0_REJECTED_RECALL_QUEUE',rejected)
    report={k:result[k] for k in ['scope','config','duplicate_links','conflicts','decisions','measured_accuracy','measured_recall','existing_lot_conflicts']}
    baseline_pairs=overlap_pairs(result['baseline']);observed_pairs=overlap_pairs(result['observed'])
    statuses={}
    for r in result['final']:statuses[r['qa_status']]=statuses.get(r['qa_status'],0)+1
    report.update(input_count=len(records),source_observation_matches=matches,
        deduplicated_count=len(result['deduplicated']),final_count=len(result['final']),
        rejected_recall_queue_count=len(rejected),status_counts=statuses,
        baseline_conflicts=baseline_pairs,observation_conflicts=observed_pairs,
        total_nodes_before=sum(vertices(r['geometry']) for r in result['baseline']),
        total_nodes_after=sum(vertices(r['geometry']) for r in result['final']),
        execution_seconds=time.perf_counter()-start,new_sam2_inference=bool(retry_audits) and not replayed,
        reused_real_sam2_observations=len(retry_observations) if replayed else 0,
        retry_audits=retry_audits,pre_retry_conflicts=initial['conflicts'],
        owner_acceptance_changed=False,complete_building_inventory_claim=False)
    save_json(output/'report.json',report)
    # Small input binding in the versioned task folder, actual GIS stays local.
    paths=[source]+sources+[ROOT/request['height']] if request.get('height') else [source]+sources
    if request.get('observations'):paths.append(ROOT/request['observations'])
    if request.get('retry_manifest'):paths.extend([ROOT/request['retry_manifest'],ROOT/request['checkpoint']])
    if request.get('replay_retry_package'):paths.append(ROOT/request['replay_retry_package'])
    paths.extend(ROOT/s['path'] for s in request.get('existing_lots',[]))
    code=['tools/refine_regional_roofs.py','stratum_ro/regional_refinement.py',
          'stratum_ro/roof_simple_geometry.py','stratum_ro/regional_roofs.py','stratum_ro/api/service.py']
    save_json(output/'manifest.json',dict(request=request,
        inputs=[{'path':str(p),'sha256':sha(p)} for p in paths],
        code_sha256={p:sha(ROOT/p) for p in code},gpkg_sha256=sha(gpkg)))
    print(json.dumps({k:report[k] for k in ['input_count','deduplicated_count','final_count',
        'status_counts','total_nodes_before','total_nodes_after','execution_seconds']},indent=2),flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    run(json.loads(Path(args.config).read_text(encoding='utf-8')),args.output)
