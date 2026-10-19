"""Auditable refinement of existing regional roof observations.

Reuses the mosaic reader, observation deduplication and simple roof fitter.
No QGIS dependency, accepted contours, hard-coded case IDs or reference shapes.
Height and RGB statistics are evidence, never building identity or acceptance.
"""
from dataclasses import asdict, dataclass
import math

import numpy as np
from rasterio.features import rasterize
from rasterio.transform import array_bounds
from scipy.ndimage import binary_dilation, gaussian_filter, sobel
from shapely.geometry import Point, box
from shapely.strtree import STRtree

from .regional_roofs import deduplicate_candidates, route_surface, sample_evidence
from .roof_simple_geometry import simple_roof_geometry


@dataclass(frozen=True)
class RegionalRefinementConfig:
    resolution_m: float = .15
    context_m: float = 8.
    max_vertices: int = 24
    min_edge_m: float = .8
    max_boundary_distance_m: float = .5
    max_area_change: float = .04
    min_support: float = .95
    min_coverage: float = .95
    duplicate_iou: float = .85
    duplicate_containment: float = .97
    conflict_area_m2: float = .05
    min_rgb_valid_fraction: float = .995

    def __post_init__(self):
        positive = [self.resolution_m, self.context_m, self.min_edge_m,
                    self.max_boundary_distance_m, self.conflict_area_m2]
        if not all(math.isfinite(x) and x > 0 for x in positive):
            raise ValueError('Finite positive physical parameters required')
        ratios = [self.max_area_change, self.min_support, self.min_coverage,
                  self.duplicate_iou, self.duplicate_containment, self.min_rgb_valid_fraction]
        if not all(math.isfinite(x) and 0 < x <= 1 for x in ratios):
            raise ValueError('Fractions must be finite in (0, 1]')
        if not isinstance(self.max_vertices, int) or self.max_vertices < 4:
            raise ValueError('At least four vertices required')


def vertices(geometry):
    if geometry.geom_type == 'Polygon':
        return len(geometry.exterior.coords)-1+sum(len(r.coords)-1 for r in geometry.interiors)
    return sum(vertices(g) for g in geometry.geoms)


def scene_evidence(geometry, rgb, valid, transform, height=None, counts=None):
    """Statistics use pixels inside geometry AND their explicit validity masks.

    Black RGB and zero height are valid observations when their masks say so.
    NoData never becomes zero-height ground. Trees can also have high H90.
    """
    rgb = np.asarray(rgb)
    valid = np.asarray(valid, dtype=bool)
    if rgb.shape != (*valid.shape, 3) or valid.ndim != 2:
        raise ValueError('Aligned RGB and explicit validity mask required')
    inside = rasterize([(geometry, 1)], out_shape=valid.shape, transform=transform,
                       dtype='uint8').astype(bool)
    n = int(inside.sum())
    if n == 0:
        return {'rgb_valid_fraction': 0., 'touches_nodata': True,
                'status': 'NO_SAMPLED_OPTICAL_PIXELS'}
    observed = inside & valid
    height = np.full(valid.shape, np.nan) if height is None else np.asarray(height)
    counts = np.full(valid.shape, np.nan) if counts is None else np.asarray(counts)
    if height.shape != valid.shape or counts.shape != valid.shape:
        raise ValueError('Aligned contextual grids required')
    vals = height[observed & np.isfinite(height)]
    result = dict(rgb_valid_fraction=float(observed.sum()/n),
                  touches_nodata=bool((binary_dilation(inside) & ~valid).any()),
                  height_valid_fraction=float(len(vals)/max(int(observed.sum()), 1)),
                  h90_m=float(np.percentile(vals, 90)) if len(vals) else None,
                  height_median_m=float(np.median(vals)) if len(vals) else None,
                  height_iqr_m=float(np.percentile(vals, 75)-np.percentile(vals, 25)) if len(vals) else None)
    if observed.any():
        result.update(route_surface(rgb, observed, height, counts))
    # Fraction inside the pixel grid as well as valid pixels: outside-grid area
    # must not be ignored by the denominator of a seemingly complete read.
    frame = box(*array_bounds(*valid.shape, transform))
    result['geometry_inside_read_fraction'] = float(geometry.intersection(frame).area/geometry.area)
    return result


def edge_support(geometry, rgb, valid, transform, tolerance_m=.6):
    """Diagnostic multiscale optical contrast near boundary, not an accuracy score."""
    from scipy.ndimage import maximum_filter
    step = math.sqrt(abs(transform.determinant))
    gray = np.asarray(rgb, dtype=float).mean(axis=2)
    # Normalize smoothing by physical scale, without sharpening NoData borders.
    weight = gaussian_filter(valid.astype(float), sigma=max(.6/step, .5))
    blurred = gaussian_filter(gray*valid, sigma=max(.6/step, .5))/np.maximum(weight, 1e-8)
    gradient = np.hypot(sobel(blurred, axis=0), sobel(blurred, axis=1))/(8*step)
    safe = weight > .999
    near = maximum_filter(np.where(safe, gradient, 0), size=2*max(1, int(tolerance_m/step))+1)
    spacing = max(step, .25)
    samples = np.arange(0, geometry.boundary.length, spacing)
    points = [geometry.boundary.interpolate(float(d)) for d in samples]
    inv = ~transform; values = []
    for p in points:
        c, r = inv*(p.x, p.y); c, r = int(math.floor(c)), int(math.floor(r))
        if 0 <= r < valid.shape[0] and 0 <= c < valid.shape[1] and safe[r, c]:
            values.append(float(near[r, c]))
    return {'sample_count': len(values), 'contrast_mean_per_m': float(np.mean(values)) if values else None,
            'role': 'DIAGNOSTIC_OPTICAL_CONTRAST_NOT_GROUND_TRUTH'}


def overlap_pairs(records, minimum_area=.05):
    if not records:
        return []
    tree = STRtree([r['geometry'] for r in records]); pairs = []
    for i, item in enumerate(records):
        a = item['geometry']
        for j in tree.query(a, predicate='intersects'):
            j = int(j)
            if j <= i:
                continue
            b = records[j]['geometry']; area = a.intersection(b).area
            if area > minimum_area:
                pairs.append(dict(a=item['candidate_id'], b=records[j]['candidate_id'],
                                  area_m2=float(area), iou=float(area/a.union(b).area),
                                  containment=float(area/min(a.area, b.area))))
    return pairs


class RegionalRoofRefiner:
    """Shared product entry point for CLI/service; all outputs remain hypotheses."""

    def __init__(self, mosaic, config=None, height_path=None, counts_path=None):
        self.config = config or RegionalRefinementConfig()
        self.mosaic = mosaic
        self.height_path = height_path
        self.counts_path = counts_path

    def observe(self, geometry):
        cfg = self.config
        bounds = box(*geometry.bounds).buffer(cfg.context_m).bounds
        rgb, valid, tr, used = self.mosaic.read(bounds, cfg.resolution_m)
        height = sample_evidence(self.height_path, tr, valid.shape)
        counts = sample_evidence(self.counts_path, tr, valid.shape)
        return dict(rgb=rgb, valid=valid, transform=tr, height=height, counts=counts,
                    bounds=list(bounds), sources=used)

    def shape_variations(self, observed, previous=None, **parameters):
        """Opt-in simpler proposals; inspect actual RGB validity and edge evidence.

        Uses the same mosaic/service as refinement. Does not accept a building,
        infer missing bodies or alter the original observation.
        """
        from .roof_simple_geometry import roof_shape_variations
        chosen, variants=roof_shape_variations(observed,previous,**parameters)
        scene=self.observe(observed.buffer(2))
        before=edge_support(observed,scene['rgb'],scene['valid'],scene['transform'])
        for option in variants:
            g=option['geometry']
            ev=scene_evidence(g,scene['rgb'],scene['valid'],scene['transform'])
            after=edge_support(g,scene['rgb'],scene['valid'],scene['transform'])
            option['optical_evidence']=ev;option['edge_evidence']=after
            if (ev.get('rgb_valid_fraction',0)<self.config.min_rgb_valid_fraction
                    or ev.get('geometry_inside_read_fraction',0)<.999 or ev.get('touches_nodata',True)):
                option['reasons'].append('INCOMPLETE_OPTICAL_COVERAGE')
            b=before['contrast_mean_per_m'];a=after['contrast_mean_per_m']
            if b and a is not None and a<.85*b:option['reasons'].append('OPTICAL_EDGE_CONTRAST_DEGRADED')
            option['eligible']=not option['reasons']
        safe=[v for v in variants if v['eligible']]
        if safe:chosen=min(safe,key=lambda o:(o['vertices'],-o['iou']))
        else:
            chosen=dict(geometry=observed,method='OBSERVATION_PRESERVED',family='UNRESOLVED',
                vertices=vertices(observed),eligible=False,reasons=['NO_SAFE_SIMPLE_VARIANT'])
        return chosen,variants

    def simplify_shapes(self, records, **parameters):
        """Canonical B batch stage: proposals, sensor gates and joint topology QA.

        Called by report/CLI and other service consumers. No file writes, render
        code, reference contours, inference or owner acceptance. Keep all IDs and
        original shapes when a simplification increases neighbor intersection.
        Alternative eligibility is local; batch guards can still block selection.
        """
        records=list(records)
        ids=[r.get('candidate_id') for r in records]
        if any(not isinstance(i,str) or not i for i in ids) or len(set(ids))!=len(ids):
            raise ValueError('Unique nonempty candidate IDs required')
        for r in records:
            g=r['geometry']
            if g.geom_type!='Polygon' or g.is_empty or not g.is_valid:
                raise ValueError('Valid single Polygon observations required')
        previous=[dict(candidate_id=r['candidate_id'],geometry=r['geometry']) for r in records]
        by_old={r['candidate_id']:r['geometry'] for r in records}
        final=[];variants=[];decisions=[];selected={}
        tree=STRtree([r['geometry'] for r in records]) if records else None
        threshold=self.config.conflict_area_m2
        for item in records:
            ident=item['candidate_id'];g=item['geometry']
            chosen,options=self.shape_variations(g,item.get('baseline_geometry'),**parameters)
            # Search the actual proposal as well as the old shape; do not assume
            # a fixed buffer contains every possible user-supplied tolerance.
            for j in tree.query(g.union(chosen['geometry']),predicate='intersects'):
                neighbor=records[int(j)]
                if neighbor['candidate_id']==ident:continue
                n=neighbor['geometry']
                if chosen['geometry'].intersection(n).area>g.intersection(n).area+threshold:
                    chosen=dict(geometry=g,vertices=vertices(g),family='UNRESOLVED',
                        method='PREVIOUS_CONFLICT_GUARD',eligible=False,reasons=['INCREASES_NEIGHBOR_OVERLAP'])
                    break
            selected[ident]=chosen
            final.append(dict(candidate_id=ident,geometry=chosen['geometry'],family=chosen['family'],
                vertices=chosen['vertices'],method=chosen['method'],owner_verdict='PENDING_OWNER_REVIEW',
                qa_status='SHAPE_PROPOSAL_REVIEW_REQUIRED',previous_qa_status=item.get('qa_status','UNKNOWN'),
                reasons=list(chosen['reasons'])))
            for n,option in enumerate(options,1):
                variants.append(dict(candidate_id=ident,variant_id=f'{ident}:V{n}',**option))
        reverted=[]
        while True:
            bad=set()
            for pair in overlap_pairs(final,threshold):
                a,b=pair['a'],pair['b']
                if pair['area_m2']>by_old[a].intersection(by_old[b]).area+threshold:bad.update([a,b])
            changed=False
            for r in final:
                ident=r['candidate_id']
                if ident in bad and not r['geometry'].equals(by_old[ident]):
                    r.update(geometry=by_old[ident],method='JOINT_CONFLICT_GUARD',family='UNRESOLVED',
                        vertices=vertices(by_old[ident]),reasons=['JOINT_OVERLAP_INCREASE'])
                    selected[ident]=dict(r);reverted.append(ident);changed=True
            if not changed:break
        for r in final:
            ident=r['candidate_id']
            decisions.append(dict(candidate_id=ident,nodes_before=vertices(by_old[ident]),nodes_after=r['vertices'],
                selected={k:v for k,v in selected[ident].items() if k not in ('geometry','candidate_id')},
                alternatives=[{k:v for k,v in o.items() if k not in ('geometry','candidate_id','variant_id')}
                    for o in variants if o['candidate_id']==ident]))
        return dict(previous=previous,final=final,variants=variants,decisions=decisions,
            jointly_reverted_ids=reverted,conflicts_before=overlap_pairs(previous,threshold),
            conflicts_after=overlap_pairs(final,threshold),measured_accuracy=None,measured_recall=None,
            scope='EXISTING_B_PROPOSALS_SIMPLE_SHAPE_ALTERNATIVES')

    def retry_observation(self, record, segmenter, *, context_m=24.):
        """Automatic mask retry using actual RGB/LiDAR context, never fake review.

        Caller must enforce the appropriate evaluation preflight for test cases.
        Generates an interior seed from the observed roof, not a parcel centroid.
        Does not clip the new mask to the old bounds. All alternatives survive in
        the audit, including rejected masks and their coverage reasons.
        """
        import torch
        from scipy.ndimage import distance_transform_edt, label
        from .regional_roofs import RegionalRoofConfig, vectorize_automatic_masks
        g=record['geometry']; cfg=self.config
        bounds=box(*g.bounds).buffer(context_m).bounds
        rgb,valid,tr,sources=self.mosaic.read(bounds,cfg.resolution_m)
        inside=rasterize([(g,1)],out_shape=valid.shape,transform=tr,dtype='uint8').astype(bool)
        if not inside.any() or not valid[inside].all():
            return record,dict(status='RETRY_BLOCKED_INCOMPLETE_TARGET',attempts=[])
        height=sample_evidence(self.height_path,tr,valid.shape)
        counts=sample_evidence(self.counts_path,tr,valid.shape)
        red,green,blue=np.moveaxis(rgb.astype(float),-1,0)
        vegetation=(green>1.08*red)&(green>1.12*blue)&((rgb.max(axis=2)-rgb.min(axis=2))>20)
        seed=inside&valid&~vegetation
        elevated=seed&np.isfinite(height)&(height>=1.8)
        # Missing/low-height LiDAR never vetoes a visible optical seed.
        if elevated.sum()*abs(tr.determinant)>=2.:seed=elevated
        if not seed.any():seed=inside&valid
        distance=distance_transform_edt(np.pad(seed,1))[1:-1,1:-1]
        rr,cc=np.unravel_index(np.argmax(distance),distance.shape)
        anchor=tr*(cc+.5,rr+.5)
        negatives=[]
        near=rasterize([(g.buffer(8.),1)],out_shape=valid.shape,transform=tr,dtype='uint8').astype(bool)
        background=near&~inside&valid&np.isfinite(height)&(height<1.)
        labels,n=label(background)
        for ident in sorted(range(1,n+1),key=lambda k:int((labels==k).sum()),reverse=True)[:4]:
            comp=labels==ident
            if comp.sum()*abs(tr.determinant)<3.:continue
            dist=distance_transform_edt(np.pad(comp,1))[1:-1,1:-1]
            nr,nc=np.unravel_index(np.argmax(dist),dist.shape)
            negatives.append((float(nc)+.5,float(nr)+.5))
        point_labels=np.array([1]+[0]*len(negatives),dtype='int32')
        points=np.array([(float(cc)+.5,float(rr)+.5)]+negatives,dtype='float32')
        segmenter.set_image(rgb,tr)
        with torch.inference_mode():
            masks,scores,_=segmenter.predictor.predict(point_coords=points,point_labels=point_labels,multimask_output=True)
        options=[];attempts=[];shape_cfg=RegionalRoofConfig(resolution_m=cfg.resolution_m)
        for i,(mask,score) in enumerate(zip(masks,scores)):
            candidates,_=vectorize_automatic_masks([dict(segmentation=mask,predicted_iou=score,stability_score=0.)],
                rgb,valid,tr,height,counts,shape_cfg,record.get('window_id','RETRY'))
            for option in candidates:
                geom=option['geometry'];coverage=geom.intersection(g).area/g.area
                reasons=[]
                if not geom.covers(Point(*anchor)):reasons.append('LOST_OWN_SEED')
                if coverage<.80:reasons.append('LOST_OBSERVED_ROOF_AREA')
                if float(score)<.70:reasons.append('LOW_MASK_SCORE')
                if option['touches_window']:reasons.append('RETRY_WINDOW_TRUNCATION')
                if option['touches_nodata']:reasons.append('RETRY_NODATA_BOUNDARY')
                if any(geom.covers(Point(*(tr*p))) for p in negatives):reasons.append('GROUND_PROMPT_INCLUDED')
                attempts.append(dict(mask_index=i,score=float(score),coverage=float(coverage),
                    area_m2=geom.area,reasons=reasons,geometry=geom))
                if not reasons:options.append((float(score),coverage,option))
        audit=dict(status='NO_SAFE_RETRY_MASK',anchor=list(anchor),negative_points=[list(tr*p) for p in negatives],
            sources=sources,bounds=list(bounds),attempts=attempts,
            seed_role='AUTOMATIC_SENSOR_SUPPORTED_NOT_OWNER_REVIEWED',automatic_completeness_claim=False)
        if not options:return record,audit
        score,coverage,best=max(options,key=lambda x:(x[0],x[1]))
        updated={**record,'geometry':best['geometry'],'sam_score':score,
                 'retry_coverage':coverage,'retry_area_ratio':best['geometry'].area/g.area}
        checked=self.refine([updated])
        if vertices(checked['final'][0]['geometry'])>cfg.max_vertices:
            audit['status']='RETRY_MASK_KEPT_DIAGNOSTIC_COMPLEXITY_UNRESOLVED'
            return record,audit
        audit['status']='RESEGMENTED_HYPOTHESIS_PENDING_REVIEW'
        return updated,audit

    def refine(self, records, *, existing_roofs=None):
        cfg = self.config
        ids = [r['candidate_id'] for r in records]
        if len(ids) != len(set(ids)) or any(not x for x in ids):
            raise ValueError('Unique nonempty candidate IDs required')
        baseline = []; observations = []
        for r in records:
            g = r['geometry']
            if g is None or g.is_empty or not g.is_valid or g.geom_type != 'Polygon':
                raise ValueError('Valid Polygon observations required; split multipart with explicit lineage')
            baseline.append({**r, 'geometry': r.get('baseline_geometry', g)})
            item = dict(r)
            item.update(touches_window=False, touches_nodata=False,
                        route='OPTICAL_UNKNOWN_REVIEW', sam_score=float(r.get('sam_score', 0.)))
            try:
                scene = self.observe(g)
                evidence = scene_evidence(g, scene['rgb'], scene['valid'], scene['transform'],
                                          scene['height'], scene['counts'])
                item['evidence'] = evidence
                item['touches_nodata'] = evidence['touches_nodata']
                item['route'] = evidence.get('route', 'OPTICAL_UNKNOWN_REVIEW')
            except (ValueError, OSError) as exc:
                item['evidence'] = {'status': 'SCENE_NOT_READ', 'error': str(exc)}
                item['touches_nodata'] = True
            observations.append(item)
        # Existing conservative observation suppression, with stricter thresholds.
        # Never union geometry or suppress a smaller nested body by containment alone.
        kept, links = deduplicate_candidates(observations, cfg.duplicate_iou, cfg.duplicate_containment)
        pre = []; final = []; decisions = []
        for item in kept:
            g = item['geometry']; candidate = g
            evidence = item['evidence']; reasons = list(item.get('upstream_reasons', []))
            info = {'method': 'OBSERVATION_PRESERVED'}
            if evidence.get('status') == 'SCENE_NOT_READ':
                reasons.append('SCENE_NOT_READ')
            elif (evidence.get('rgb_valid_fraction', 0) < cfg.min_rgb_valid_fraction or
                  evidence.get('geometry_inside_read_fraction', 0) < cfg.min_rgb_valid_fraction or
                  evidence.get('touches_nodata', True)):
                reasons.append('INCOMPLETE_OPTICAL_COVERAGE')
            else:
                from .roof_mask_fidelity import normalize_height_supported_pinholes
                scene=self.observe(g)
                fit_input,holes=normalize_height_supported_pinholes(g,scene['valid'],scene['transform'],scene['height'])
                if (fit_input.area-g.area)/g.area>cfg.max_area_change:
                    fit_input=g;holes={'removed_hole_count':0,'role':'HOLE_CLEANUP_AREA_GUARD'}
                candidate, info = simple_roof_geometry(fit_input, min_support=cfg.min_support,
                    min_coverage=cfg.min_coverage, max_vertices=cfg.max_vertices, min_edge=cfg.min_edge_m,
                    max_boundary_distance=cfg.max_boundary_distance_m, max_area_change=cfg.max_area_change)
                if info['method'] == 'NEEDS_REVIEW':
                    from .roof_mask_fidelity import simplify_observed_roof
                    anchor=g.representative_point()
                    faithful, fi = simplify_observed_roof(fit_input,(anchor.x,anchor.y),max_vertices=cfg.max_vertices,
                        min_fidelity=.975,max_boundary_shift_m=cfg.max_boundary_distance_m,min_hole_area_m2=0.)
                    if (fi['status']=='RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW' and
                        faithful.boundary.hausdorff_distance(fit_input.boundary)<=cfg.max_boundary_distance_m and
                        abs(faithful.area-g.area)/g.area<=cfg.max_area_change):
                        candidate=faithful;info=fi
                    else:
                        reasons.append(info['reason'])
                if holes['removed_hole_count']:
                    info['height_supported_pinhole_cleanup']=holes
                    reasons.append('SMALL_MASK_HOLES_FILLED_REVIEW_REQUIRED')
                if abs(candidate.area-g.area)/g.area>cfg.max_area_change:
                    candidate=g;reasons.append('TOTAL_AREA_CHANGE_GUARD')
                # A changed shape cannot cross into invalid pixels after fitting.
                scene = self.observe(candidate)
                ce = scene_evidence(candidate, scene['rgb'], scene['valid'], scene['transform'])
                if ce.get('rgb_valid_fraction', 0) < cfg.min_rgb_valid_fraction or ce.get('touches_nodata', True):
                    candidate = g; reasons.append('FIT_CROSSES_NODATA')
                info['optical_before'] = edge_support(g, scene['rgb'], scene['valid'], scene['transform'])
                info['optical_after'] = edge_support(candidate, scene['rgb'], scene['valid'], scene['transform'])
                eb = info['optical_before']['contrast_mean_per_m']; ea = info['optical_after']['contrast_mean_per_m']
                if eb is not None and ea is not None and eb > 0 and ea < .85*eb:
                    candidate = g; reasons.append('OPTICAL_EDGE_CONTRAST_DEGRADED')
            if evidence.get('route') == 'LIKELY_VEGETATION_REVIEW':
                reasons.append('VEGETATION_EVIDENCE_REVIEW')
            if vertices(candidate) > cfg.max_vertices:
                reasons.append('COMPLEX_BOUNDARY_REVIEW')
            pre.append({**item, 'geometry': candidate})
            result = {**item, 'geometry': candidate, 'owner_verdict': 'PENDING_OWNER_REVIEW',
                      'review_reasons': reasons,
                      'qa_status': 'NEEDS_REVIEW' if reasons else 'SIMPLE_ROOF_HYPOTHESIS'}
            final.append(result)
            decisions.append(dict(candidate_id=item['candidate_id'], nodes_before=vertices(g),
                nodes_after=vertices(candidate), area_before_m2=g.area, area_after_m2=candidate.area,
                boundary_distance_m=g.boundary.hausdorff_distance(candidate.boundary),
                area_change_fraction=abs(g.area-candidate.area)/g.area, method=info,
                evidence=evidence, review_reasons=reasons))
        conflicts = overlap_pairs(final, cfg.conflict_area_m2)
        by_id = {r['candidate_id']: r for r in final}
        for pair in conflicts:
            for ident in [pair['a'], pair['b']]:
                r = by_id[ident]
                if 'OVERLAPPING_IDENTITY_UNRESOLVED' not in r['review_reasons']:
                    r['review_reasons'].append('OVERLAPPING_IDENTITY_UNRESOLVED')
                r['qa_status'] = 'NEEDS_REVIEW'
        existing_conflicts=[]
        if existing_roofs:
            tree=STRtree([r['geometry'] for r in existing_roofs])
            for r in final:
                for j in tree.query(r['geometry'],predicate='intersects'):
                    other=existing_roofs[int(j)];a=r['geometry'];b=other['geometry']
                    area=a.intersection(b).area
                    if area<=cfg.conflict_area_m2:continue
                    iou=area/a.union(b).area
                    existing_conflicts.append(dict(candidate_id=r['candidate_id'],
                        existing_id=other['candidate_id'],source=other.get('source',''),
                        area_m2=float(area),iou=float(iou)))
                    reason='ALREADY_OBSERVED_OTHER_LOT' if iou>=cfg.duplicate_iou else 'INTERSECTS_EXISTING_OTHER_LOT'
                    if reason not in r['review_reasons']:r['review_reasons'].append(reason)
                    r['qa_status']='NEEDS_REVIEW'
        return dict(baseline=baseline, observed=observations, deduplicated=kept,
                    simplified=pre, final=final, duplicate_links=links, conflicts=conflicts,
                    decisions=decisions, config=asdict(cfg), existing_lot_conflicts=existing_conflicts,
                    scope='EXISTING_REGIONAL_CANDIDATE_REFINEMENT_NOT_NEW_AREA_DETECTION',
                    measured_accuracy=None, measured_recall=None)
