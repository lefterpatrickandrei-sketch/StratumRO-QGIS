"""Local SAM2 roof hypotheses with separate bodies and retained nDSM fallback."""
from shapely.geometry import box,Point
from .roof_body_proposals import color_body_proposals
from .building_proposals import building_proposals
from .sensor_review import review_candidates
from .roof_candidate_routing import route_roof_candidate, prioritize_roof_candidates,vegetation_color_fraction
from .roof_rectangle_core import rectangle_core
from .optical_roof_edges import refine_roof_color
from .roof_simple_geometry import simple_roof_geometry
from .roof_body_partition import split_color_roof_bodies
from .roof_retry import retry_roof_geometry
from .vectorizer import CadastralVectorizer


def _replace_roof_geometry(feature,geometry,method,lidar_data,vectorizer):
    ground=geometry.buffer(-.4,join_style=2)
    if ground.is_empty or not ground.is_valid:ground=geometry
    feature.update(geometry=geometry,geometry_sol=ground,area_m2=round(geometry.area,2),
                   perimeter_m=round(geometry.length,2),vertices=len(geometry.exterior.coords)-1,
                   clasa_forma=method,repair_type=method,center_x=round(geometry.centroid.x,2),
                   center_y=round(geometry.centroid.y,2),area_sol_m2=round(ground.area,2))
    quality=vectorizer.quality_gate.compute_composite_confidence(poly=geometry,
        sam2_score=float(feature.get('sam2_score',0)),ndsm_array=lidar_data['ndsm'],transform=lidar_data['transform'])
    feature.update({k:quality[k] for k in ['conf_final','action_code','step_valid_pct','std_acoperis']})


def recover_roof_bodies(lidar_data, image_rgb, image_transform, segmenter,
                        roi_bounds=None, simple_edges=False):
    """Generate, reconstruct individually, and route hypotheses without references.

    Optional ROI limits computation for diagnostic experiments. Its boundary is
    never used as a SAM prompt. No reference polygon or reference seed is read.
    """
    segmenter.set_image(image_rgb, image_transform)
    proposals = color_body_proposals(lidar_data,image_rgb,image_transform)
    proposals += building_proposals(lidar_data)
    roi = box(*roi_bounds) if roi_bounds is not None else None
    candidates, raw, seen = [], [], set()
    vectorizer = CadastralVectorizer()
    import numpy as np
    from scipy.ndimage import distance_transform_edt
    for proposal in proposals:
        geom = proposal['geometry']
        if roi is not None and not geom.intersects(roi):continue
        # Ignore components whose center is outside this RGB tile.
        if geom.wkb in seen:continue
        sl,comp=proposal['slice'],proposal['mask']
        positive=proposal.get('positive_point_geo')
        if positive is None:
            dist=distance_transform_edt(np.pad(comp,1))[1:-1,1:-1]
            rr,cc=np.unravel_index(np.argmax(dist),dist.shape)
            x,y=lidar_data['transform']*(sl[1].start+cc+.5,sl[0].start+rr+.5)
        else:x,y=positive.x,positive.y
        ix,iy=(~image_transform)*(x,y)
        if not (0<=iy<image_rgb.shape[0] and 0<=ix<image_rgb.shape[1]):continue
        seen.add(geom.wkb)
        h=lidar_data['ndsm'][sl][comp]
        result=segmenter.segment_candidate(*geom.bounds,mean_h=float(np.mean(h)),
                 max_h=float(np.max(h)),lidar_area=proposal['area_m2'],
                 internal_pts_geo=[(x,y)],height_min_threshold=2.)
        optical=result.get('geometry')
        if optical is None:
            # Preserve direct LiDAR proposals in review; never invent optical support.
            if result['status']!='LIDAR_DIRECT':continue
            result=dict(result,geometry=geom)
            optical=geom
        raw_id=f"R{len(raw)+1:05d}"
        raw.append({'id':raw_id,'geometry':optical,'proposal_source':proposal['source'],
                    'status':result['status'],'sam2_score':result.get('sam2_score',0),
                    'prompt_x':x,'prompt_y':y})
        bodies=split_color_roof_bodies(optical,image_rgb,image_transform) if simple_edges and result['status']!='LIDAR_DIRECT' else [{'geometry':optical,'split_status':'NOT_REQUESTED'}]
        features=[]
        for body_index,body in enumerate(bodies,1):
            formatted=vectorizer.format_hybrid_buildings([dict(result,geometry=body['geometry'])],tolerance=.5,
                        eave_offset_m=.4,ndsm_array=lidar_data['ndsm'],
                        ndsm_transform=lidar_data['transform'])
            for item in formatted:
                item.update(_body_mask=body['geometry'],body_index=body_index,body_count=len(bodies),
                            split_status=body['split_status'],sam2_score_scope='PARENT_MASK')
            features.extend(formatted)
        retry_siblings=[]
        for feature in features:
            body_optical=feature.pop('_body_mask')
            old=feature['geometry']
            edge_info = None
            if simple_edges and result['status'] != 'LIDAR_DIRECT':
                if feature['body_count']>1:
                    # Partition already fitted and clipped both simple bodies at
                    # a common seam. Color dilation must not regrow a sibling.
                    repaired=body_optical;color_method='PARTITION_PRESERVED'
                    edge_info={'method':'SUPPORTED_SEPARATE_BODY','support':1.,'coverage':1.}
                else:
                    trimmed, color_method = refine_roof_color(body_optical,image_rgb,image_transform,lidar_data)
                    repaired, edge_info = simple_roof_geometry(trimmed)
                feature.update(edge_color_method=color_method, edge_method=edge_info['method'],
                               edge_support=edge_info.get('support',0.),
                               edge_coverage=edge_info.get('coverage',0.),
                               edge_status='REVIEW_REQUIRED')
            else:
                repaired=rectangle_core(old,optical)
            inherited_prompt_outside=not old.buffer(.5).covers(Point(x,y))
            if simple_edges and feature['body_count']==1 and (result['status']=='LIDAR_DIRECT' or
                    (edge_info and edge_info['method']=='NEEDS_REVIEW') or inherited_prompt_outside):
                retry=retry_roof_geometry(old,image_rgb,image_transform,lidar_data,segmenter)
                feature.update(retry_status=retry['status'],inherited_prompt_outside=inherited_prompt_outside)
                retry_raw_ids={}
                for attempt in retry['attempts']:
                    if attempt.get('raw_optical') is not None:
                        fresh_raw_id=f"R{len(raw)+1:05d}"
                        retry_raw_ids[attempt['index']]=fresh_raw_id
                        raw.append({'id':fresh_raw_id,'geometry':attempt['raw_optical'],
                                    'parent_raw_id':raw_id,'proposal_source':'LOCAL_BODY_RETRY',
                                    'status':attempt['status'],'sam2_score':attempt['sam2_score'],
                                    'prompt_x':attempt['point'][0],'prompt_y':attempt['point'][1]})
                if retry['candidates']:
                    best=retry['candidates'][0];repaired=best['geometry']
                    edge_info={'method':best['simple_method'],'support':best['simple_support'],'coverage':best['simple_coverage']}
                    feature.update(sam2_score=best['sam2_score'],retry_succeeded=True,
                        edge_method=best['simple_method'],edge_color_method=best['color_method'],
                        edge_support=best['simple_support'],edge_coverage=best['simple_coverage'],
                        retry_seed_x=best['seed_x'],retry_seed_y=best['seed_y'],edge_status='REVIEW_REQUIRED')
                    feature.update(retry_raw_id=retry_raw_ids.get(best['attempt_index'],raw_id),
                                   sam2_score_scope='LOCAL_CHILD_MASK',validare='IPOTEZA_RELUATA_NEVERIFICATA')
                    feature['_routing_optical']=next(a['raw_optical'] for a in retry['attempts']
                        if a['index']==best['attempt_index'])
                    if len(retry['candidates'])>1:
                        feature.update(body_count=len(retry['candidates']),body_index=1,
                                       split_status='LOCAL_RETRY_MULTIPLE_BODIES_REVIEW_REQUIRED')
                    for sibling_index,sibling in enumerate(retry['candidates'][1:],2):
                        extra=dict(feature)
                        extra.update(sam2_score=sibling['sam2_score'],body_index=sibling_index,
                            retry_raw_id=retry_raw_ids[sibling['attempt_index']],
                            retry_seed_x=sibling['seed_x'],retry_seed_y=sibling['seed_y'],
                            edge_method=sibling['simple_method'],edge_color_method=sibling['color_method'],
                            edge_support=sibling['simple_support'],edge_coverage=sibling['simple_coverage'])
                        extra['_routing_optical']=next(a['raw_optical'] for a in retry['attempts']
                            if a['index']==sibling['attempt_index'])
                        _replace_roof_geometry(extra,sibling['geometry'],sibling['simple_method'],lidar_data,vectorizer)
                        retry_siblings.append(extra)
            feature['repair_type']=(edge_info['method'] if edge_info else 'RECTANGLE_CORE') if not repaired.equals(old) else 'NONE'
            if not repaired.equals(old) or feature.get('retry_succeeded'):
                _replace_roof_geometry(feature,repaired,edge_info['method'] if edge_info else 'RECTANGLE_CORE',lidar_data,vectorizer)
        features.extend(retry_siblings)
        features=review_candidates(features,lidar_data['class_evidence'],lidar_data['transform'])
        for feature in features:
            feature['vegetation_color_fraction']=vegetation_color_fraction(feature['geometry'],image_rgb,image_transform)
            routing_optical=feature.pop('_routing_optical',optical)
            item=route_roof_candidate(feature,routing_optical)
            if feature.get('retry_succeeded'):item['action_code']='REVIZUIRE_MANUALA'
            if feature.get('body_count',1)>1:
                item['route']='REVIZUIRE_COMPLEXA'
                item['route_reason']=('CORPURI_RECUPERATE_LOCAL;CONFIRMA_IDENTITATEA' if feature.get('retry_succeeded') else 'CORPURI_SEPARATE_CULOARE;CONFIRMA_IDENTITATEA')
            if feature.get('edge_method')=='NEEDS_REVIEW':
                item['route']='REVIZUIRE_COMPLEXA';item['route_reason']='FORMA_SIMPLA_FARA_SUPORT'
            if feature.get('retry_status') in ['NO_SUPPORTED_ROOF_SEED','UNRESOLVED_AFTER_LOCAL_RETRY','NEEDS_COMPLETE_IMAGE_COVERAGE']:
                item['route']='REVIZUIRE_COMPLEXA';item['route_reason']=feature['retry_status']
            if result['status']=='LIDAR_DIRECT' and not feature.get('retry_succeeded'):
                item['route']='REVIZUIRE_COMPLEXA';item['route_reason']='FARA_CONFIRMERE_OPTICA'
            item.update(id=f"B{len(candidates)+1:05d}",raw_id=raw_id,
                        proposal_source=proposal['source'])
            candidates.append(item)
    candidates=prioritize_roof_candidates(candidates)
    return {'candidates':candidates,'raw':raw,
            'selected':[c for c in candidates if c['route']=='INSPECTIE_PRIORITARA'],
            'review':[c for c in candidates if c['route']!='INSPECTIE_PRIORITARA']}
