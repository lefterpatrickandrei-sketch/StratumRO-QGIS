"""Reusable reviewed-candidate roof workflow, independent of QGIS and UI.

This opt-in workflow produces roof hypotheses, never legal parcel boundaries or
measured ground footprints. It uses actual optical scores and local evidence.
"""
import math
import numpy as np
from scipy.ndimage import label
from rasterio.features import shapes
from shapely.geometry import shape, Point, box
from .fusion_guidance import select_fusion_prompt
from .fusion_refinement import refine_fusion_mask


def _component(mask,point_px,transform):
    labs,_=label(mask)
    col,row=np.floor(point_px).astype(int)
    if not (0<=row<mask.shape[0] and 0<=col<mask.shape[1]):return None
    ident=labs[row,col]
    if ident==0:return None
    selected=labs==ident
    polygons=[shape(g) for g,v in shapes(selected.astype('uint8'),mask=selected,transform=transform) if v==1]
    return max(polygons,key=lambda geom:geom.area) if polygons else None


def clip_roof_to_valid_grid(geometry,valid,transform,anchor):
    """Keep NoData excluded even if a later simplifier filled tiny mask holes."""
    if valid.all():return geometry
    from shapely.ops import unary_union
    invalid=[shape(g) for g,v in shapes((~valid).astype('uint8'),mask=~valid,transform=transform) if v==1]
    clipped=geometry.difference(unary_union(invalid))
    parts=list(clipped.geoms) if hasattr(clipped,'geoms') else [clipped]
    matches=[g for g in parts if g.geom_type=='Polygon' and g.covers(Point(*anchor))]
    if not matches:raise ValueError('REFINED_ROOF_LOST_VALID_ANCHOR')
    return max(matches,key=lambda g:g.area)


class CadastralRoofWorkflow:
    """Encode once, process multiple explicitly reviewed candidates in a scene."""

    def __init__(self,segmenter,max_vertices=20):
        if not isinstance(max_vertices,int) or max_vertices<4:raise ValueError('At least four vertices required')
        self.segmenter=segmenter
        self.max_vertices=max_vertices
        self.rgb=None
        self._ids=set()

    def set_scene(self,rgb,transform,valid_mask,*,crs,relative_height=None,
                  building_counts=None,lidar_valid=None,lidar_compatible=False,
                  provenance=None):
        rgb=np.asarray(rgb)
        valid=np.asarray(valid_mask,dtype=bool)
        if rgb.ndim!=3 or rgb.shape[2]!=3 or valid.shape!=rgb.shape[:2]:
            raise ValueError('RGB image and aligned explicit valid mask required')
        if crs!='EPSG:3844':raise ValueError('Projected EPSG:3844 scene required; assigning CRS is not reprojection')
        if not np.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
            raise ValueError('Invertible scene transform required')
        supplied=[relative_height is not None,building_counts is not None,lidar_valid is not None]
        if any(supplied) and not all(supplied):raise ValueError('Supply all three LiDAR evidence grids or none')
        if all(supplied):
            height=np.asarray(relative_height,dtype=float);counts=np.asarray(building_counts,dtype=float)
            lv=np.asarray(lidar_valid,dtype=bool)
            if any(grid.shape!=valid.shape for grid in [height,counts,lv]):
                raise ValueError('LiDAR grids must already align with the scene')
        else:
            height=np.full(valid.shape,np.nan);counts=np.zeros(valid.shape);lv=np.zeros(valid.shape,dtype=bool)
            lidar_compatible=False
        self.rgb=rgb;self.transform=transform;self.valid=valid
        self.height=height;self.counts=counts;self.lidar_valid=lv
        self.lidar_compatible=bool(lidar_compatible);self.provenance=dict(provenance or {})
        self._ids=set();self._encoded=False

    def extract(self,body_id,anchor,search_bounds,*,reviewed=False,context_m=4.,score_threshold=.60,
                max_prompt_shift_m=None,refinement_policy='SENSOR_FUSION',positive_points=None,negative_points=None,
                allow_invalid_context=False):
        if self.rgb is None:raise RuntimeError('Set scene before extraction')
        if refinement_policy not in ['SENSOR_FUSION','OPTICAL_FIDELITY','OPTICAL_PLANAR_CORE']:raise ValueError('Unknown refinement policy')
        if not body_id or body_id in self._ids:raise ValueError('Unique nonempty body_id required per scene')
        if not reviewed:raise ValueError('Candidate identity and optical anchor must be reviewed')
        if len(search_bounds)!=4 or not np.all(np.isfinite(search_bounds)):
            raise ValueError('Finite search bounds required')
        a,b,c,d=map(float,search_bounds)
        if a>=c or b>=d:raise ValueError('Ordered nonempty search bounds required')
        if len(anchor)!=2 or not np.all(np.isfinite(anchor)) or not box(a,b,c,d).covers(Point(*anchor)):
            raise ValueError('Finite anchor inside search bounds required')
        if not math.isfinite(context_m) or context_m<0:raise ValueError('Nonnegative context required')
        if not math.isfinite(score_threshold) or not 0<=score_threshold<=1:raise ValueError('Valid score threshold required')
        inv=~self.transform
        corners=[inv*(x,y) for x in [a-context_m,c+context_m] for y in [b-context_m,d+context_m]]
        h,w=self.valid.shape
        if any(not (0<=x<=w and 0<=y<=h) for x,y in corners):
            raise ValueError('NEEDS_COMPLETE_IMAGE_COVERAGE')
        c0=int(np.floor(min(p[0] for p in corners)));c1=int(np.ceil(max(p[0] for p in corners)))
        r0=int(np.floor(min(p[1] for p in corners)));r1=int(np.ceil(max(p[1] for p in corners)))
        invalid_context=not self.valid[r0:r1,c0:c1].all()
        if invalid_context and (not allow_invalid_context or self.valid[r0:r1,c0:c1].mean()<.90):
            raise ValueError('NODATA_IN_REQUIRED_CONTEXT')
        ac,ar=inv*tuple(anchor)
        if not self.valid[int(ar),int(ac)]:raise ValueError('NODATA_AT_ROOF_ANCHOR')
        self._ids.add(body_id)
        from rasterio.features import rasterize
        local_region=rasterize([(box(a,b,c,d),1)],out_shape=self.valid.shape,
                               transform=self.transform,dtype='uint8').astype(bool)
        guidance=select_fusion_prompt(anchor,self.transform,self.counts,self.height,
                                      self.lidar_valid&local_region,lidar_compatible=self.lidar_compatible,
                                      max_prompt_shift_m=max_prompt_shift_m)
        if not self._encoded:
            self.segmenter.set_image(self.rgb,self.transform);self._encoded=True
        px=inv*tuple(guidance['point'])
        prompt_points=[px];prompt_labels=[1]
        for points,flag in [(positive_points or [],1),(negative_points or [],0)]:
            for point in points:
                if len(point)!=2 or not np.all(np.isfinite(point)):raise ValueError('Finite prompt point required')
                cp,rp=inv*tuple(point)
                if not(0<=cp<self.valid.shape[1] and 0<=rp<self.valid.shape[0]) or not self.valid[int(rp),int(cp)]:
                    raise ValueError('Prompt point outside valid image')
                prompt_points.append((cp,rp));prompt_labels.append(flag)
        prompt_corners=[inv*(x,y) for x in [a,c] for y in [b,d]]
        prompt_box=np.array([min(p[0] for p in prompt_corners),min(p[1] for p in prompt_corners),
                             max(p[0] for p in prompt_corners),max(p[1] for p in prompt_corners)],dtype='float32')
        # Predictor interface deliberately avoids the old mandatory height veto.
        import torch
        with torch.inference_mode():
            masks,scores,_=self.segmenter.predictor.predict(point_coords=np.array(prompt_points,dtype='float32'),
                point_labels=np.array(prompt_labels,dtype='int32'),box=prompt_box,multimask_output=True)
        options=[];rejected=[]
        def prompt_conflicts(geometry):
            conflicts=[]
            if any(not geometry.covers(Point(*p)) for p in (positive_points or [])):
                conflicts.append('POSITIVE_PROMPT_OUTSIDE_ANCHOR_COMPONENT')
            if any(geometry.covers(Point(*p)) for p in (negative_points or [])):
                conflicts.append('NEGATIVE_PROMPT_INSIDE_ROOF')
            return conflicts
        for mask,score in zip(masks,scores):
            if np.asarray(mask).shape!=self.valid.shape:raise ValueError('Predictor mask shape mismatch')
            raw=_component(np.asarray(mask,dtype=bool)&self.valid,px,self.transform)
            if raw is not None and raw.is_valid and raw.area>=8 and np.isfinite(score) and raw.covers(Point(*anchor)):
                conflicts=prompt_conflicts(raw)
                if conflicts:rejected.append({'score':float(score),'reasons':conflicts,'area_m2':raw.area})
                else:options.append((float(score),raw))
        result={'body_id':body_id,'guidance':guidance,'owner_verdict':'PENDING_OWNER_REVIEW',
                'geometry_role':'OBSERVED_ROOF_HYPOTHESIS','ground_footprint':None,
                'provenance':self.provenance,'geometry':None,'raw_geometry':None,
                'status':'NO_OPTICAL_MASK_FOR_REVIEWED_OBJECT','review_reasons':[],
                'prompt_consistency':{'rejected_candidates':rejected,'positive_points':positive_points or [],'negative_points':negative_points or []}}
        if not options:
            if rejected:result['review_reasons'].append('NO_PROMPT_CONSISTENT_MASK')
            return result
        score,raw=max(options,key=lambda item:item[0])
        if refinement_policy=='OPTICAL_PLANAR_CORE':
            from .roof_mask_fidelity import rectangular_roof_core
            geom,diagnostic=rectangular_roof_core(raw,anchor)
        elif refinement_policy=='OPTICAL_FIDELITY':
            from .roof_mask_fidelity import simplify_observed_roof
            geom,diagnostic=simplify_observed_roof(raw,anchor,max_vertices=self.max_vertices)
        else:
            geom,diagnostic=refine_fusion_mask(raw,guidance['point'],self.rgb,self.transform,
                self.height,self.counts,self.valid,guidance['route'],max_vertices=self.max_vertices)
        diagnostic['refinement_policy']=refinement_policy
        if not self.valid.all():
            geom=clip_roof_to_valid_grid(geom,self.valid,self.transform,anchor)
            diagnostic['final_validity_mask_applied']=True
        reasons=[]
        conflicts=prompt_conflicts(geom)
        if conflicts:
            # Simplification may fill a reviewed background hole or omit a
            # confirmed roof wing. Preserve the consistent observation instead.
            diagnostic={'status':'NEEDS_GEOMETRY_REVIEW','method':'PROMPT_CONSISTENT_RAW_PRESERVED',
                'rejected_refinement':diagnostic,'prompt_conflicts':conflicts,
                'refinement_policy':refinement_policy}
            geom=raw
            reasons.append('REFINEMENT_VIOLATES_REVIEWED_PROMPTS')
        if invalid_context:reasons.append('NODATA_NEAR_TARGET_COMPLETENESS_UNCONFIRMED')
        if guidance.get('prompt_shift_m',0)>3:
            reasons.append('GUIDANCE_POINT_MOVED_FAR_FROM_REVIEWED_ANCHOR')
        if score<score_threshold:reasons.append('LOW_OPTICAL_SCORE')
        if diagnostic['status']!='RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW':reasons.append(diagnostic['status'])
        boundary=box(a,b,c,d).boundary
        raw_margin=raw.distance(boundary)
        refined_margin=geom.distance(boundary)
        if raw_margin<.30:reasons.append('POSSIBLE_SEARCH_WINDOW_TRUNCATION')
        if not self.lidar_compatible:reasons.append('LIDAR_NOT_USED_OR_INCOMPATIBLE')
        result.update(geometry=geom,raw_geometry=raw,sam2_score=score,diagnostic=diagnostic,
            search_window_check={'bounds':[a,b,c,d],'raw_boundary_distance_m':raw_margin,
                'refined_boundary_distance_m':refined_margin,
                'raw_within_search':box(a,b,c,d).covers(raw),
                'refined_within_search':box(a,b,c,d).covers(geom),
                'automatic_completeness_claim':False},
            status='REQUIRES_REVIEW' if reasons else 'RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW',
            review_reasons=reasons,vertices=len(geom.exterior.coords)-1+sum(len(r.coords)-1 for r in geom.interiors))
        return result
