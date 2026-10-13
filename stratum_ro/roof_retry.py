"""Recover rejected compound-mask children using their OWN sensor-supported seed.

An inherited parent prompt may lie hundreds of metres away. No original prompt
or reference contour is used here. Empty evidence is reported, not a rectangle.
"""
import math
import numpy as np
from rasterio import Affine
from rasterio.features import rasterize,shapes
from scipy.ndimage import binary_closing,distance_transform_edt,label,find_objects
from shapely.geometry import Point,shape,Polygon


def roof_retry_prompts(geometry,image_rgb,transform,lidar_data,min_seed_area_m2=8.):
    """Return bounded per-body roof seed hypotheses and explicit failure reasons."""
    if geometry is None or geometry.geom_type!='Polygon' or geometry.is_empty or not geometry.is_valid:
        raise ValueError('Valid nonempty Polygon required')
    if image_rgb.ndim!=3 or image_rgb.shape[2]!=3 or not np.isfinite(min_seed_area_m2) or min_seed_area_m2<=0:
        raise ValueError('RGB and positive seed area required')
    if not np.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
        raise ValueError('Invertible RGB affine required')
    lt=lidar_data['transform']
    if not np.isfinite(lt.determinant) or abs(lt.determinant)<1e-12:
        raise ValueError('Invertible LiDAR affine required')
    if lidar_data['ndsm'].shape!=lidar_data['class_evidence']['building'].shape:
        raise ValueError('Matching LiDAR grids required')
    xmin,ymin,xmax,ymax=geometry.buffer(3).bounds
    corners=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(math.floor(min(v[0] for v in corners))));c1=min(image_rgb.shape[1],int(math.ceil(max(v[0] for v in corners))))
    r0=max(0,int(math.floor(min(v[1] for v in corners))));r1=min(image_rgb.shape[0],int(math.ceil(max(v[1] for v in corners))))
    answer={'status':'NO_SUPPORTED_ROOF_SEED','seeds':[]}
    if c1<=c0 or r1<=r0:return dict(answer,reason='OUTSIDE_IMAGE')
    rgb=image_rgb[r0:r1,c0:c1].astype(float);tr=transform*Affine.translation(c0,r0)
    inside=rasterize([(geometry,1)],out_shape=rgb.shape[:2],transform=tr,dtype='uint8').astype(bool)
    search=rasterize([(geometry.buffer(1),1)],out_shape=rgb.shape[:2],transform=tr,dtype='uint8').astype(bool)
    rr,cc=np.indices(rgb.shape[:2]);x,y=tr*(cc+.5,rr+.5);lc,lr=(~lidar_data['transform'])*(x,y)
    ndsm=lidar_data['ndsm'];building=lidar_data['class_evidence']['building']
    valid=(lc>=0)&(lr>=0)&(lc<ndsm.shape[1])&(lr<ndsm.shape[0])
    height=np.zeros(rgb.shape[:2]);support=np.zeros(rgb.shape[:2])
    ri=np.floor(lr[valid]).astype(int);ci=np.floor(lc[valid]).astype(int)
    height[valid]=ndsm[ri,ci];support[valid]=building[ri,ci]
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2];maximum=rgb.max(axis=2)
    saturation=(maximum-rgb.min(axis=2))/np.maximum(maximum,1)
    red=(r-g>20)&(r-b>15)
    neutral=(saturation<=.30)&(maximum>=60)
    vegetation=(saturation>.25)&(g>=.8*r)&(g>1.12*b)
    strong=search&valid&np.isfinite(height)&(height>=2)&(support>0)&~vegetation&(red|neutral)
    # Roof-colour islands may have sparse returns; closing only bridges .3m gaps.
    step=math.sqrt(abs(tr.determinant));radius=max(1,int(round(.15/step)))
    closed=binary_closing(np.pad(strong,radius),structure=np.ones((2*radius+1,2*radius+1)))[radius:-radius,radius:-radius]
    closed &= search&~vegetation
    labs,_=label(closed);seeds=[]
    for i,sl in enumerate(find_objects(labs),1):
        if sl is None:continue
        component=labs[sl]==i;area=component.sum()*abs(tr.determinant)
        core=component&strong[sl]&inside[sl]
        if area<min_seed_area_m2 or core.sum()*abs(tr.determinant)<min_seed_area_m2/2:continue
        dist=distance_transform_edt(np.pad(core,1))[1:-1,1:-1]
        pr,pc=np.unravel_index(np.argmax(dist),dist.shape);pr+=sl[0].start;pc+=sl[1].start
        point=tuple(float(v) for v in tr*(pc+.5,pr+.5))
        if not geometry.covers(Point(point)):continue
        component_heights=height[sl][component&valid[sl]&np.isfinite(height[sl])]
        reach=max(1,int(round(1./step)))
        nearby=(slice(max(0,pr-reach),min(height.shape[0],pr+reach+1)),
                slice(max(0,pc-reach),min(height.shape[1],pc+reach+1)))
        local=height[nearby][strong[nearby]&np.isfinite(height[nearby])]
        local_h=float(np.median(local)) if len(local) else float(np.median(component_heights))
        seeds.append({'point':point,'area_m2':float(area),'mean_h':float(np.mean(component_heights)),
                      'local_h':local_h,'max_h':float(np.max(component_heights)),
                      'red_fraction':float(red[sl][component].mean())})
    seeds.sort(key=lambda v:(-v['area_m2'],v['point']))
    answer.update(seeds=seeds[:4],status='SUPPORTED_LOCAL_SEED' if seeds else 'NO_SUPPORTED_ROOF_SEED',
                  building_color_area_m2=float(strong.sum()*abs(tr.determinant)),
                  vegetation_fraction=float(vegetation[inside].mean()) if inside.any() else 0.)
    return answer


def trim_retry_roof_surface(geometry,image_rgb,transform,lidar_data,seed):
    """Trim a retry mask by local roof height and brown/red/neutral colour.

    Unlike the first RGB helper, this does not fill holes (courtyard protection)
    or require a predominantly bright red roof. Only used for rejected retries.
    """
    xmin,ymin,xmax,ymax=geometry.buffer(1).bounds
    corners=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(math.floor(min(v[0] for v in corners))));c1=min(image_rgb.shape[1],int(math.ceil(max(v[0] for v in corners))))
    r0=max(0,int(math.floor(min(v[1] for v in corners))));r1=min(image_rgb.shape[0],int(math.ceil(max(v[1] for v in corners))))
    if c1<=c0 or r1<=r0:return geometry,'NO_RGB_COVERAGE'
    rgb=image_rgb[r0:r1,c0:c1].astype(float);tr=transform*Affine.translation(c0,r0)
    inside=rasterize([(geometry,1)],out_shape=rgb.shape[:2],transform=tr,dtype='uint8').astype(bool)
    rr,cc=np.indices(rgb.shape[:2]);x,y=tr*(cc+.5,rr+.5);lc,lr=(~lidar_data['transform'])*(x,y)
    ndsm=lidar_data['ndsm'];building=lidar_data['class_evidence']['building']
    valid=(lc>=0)&(lr>=0)&(lc<ndsm.shape[1])&(lr<ndsm.shape[0])
    h=np.zeros(rgb.shape[:2]);counts=np.zeros(rgb.shape[:2]);ri=np.floor(lr[valid]).astype(int);ci=np.floor(lc[valid]).astype(int)
    h[valid]=ndsm[ri,ci];counts[valid]=building[ri,ci]
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2];maximum=rgb.max(axis=2)
    sat=(maximum-rgb.min(axis=2))/np.maximum(maximum,1)
    vegetation=(sat>.25)&(g>=.8*r)&(g>1.12*b)
    brown=(r>1.08*g)&(g>1.04*b)&(r-b>18)
    neutral=(sat<=.30)&(maximum>=50)
    spectral=(brown|(neutral&(counts>0))) if seed['red_fraction']>=.50 else neutral
    local_h=seed.get('local_h',seed['mean_h'])
    # A coherent height component is more reliable than a single locally low
    # return. Local height is needed when a component mixes low and high roofs.
    if seed.get('max_h',float('inf'))-seed['mean_h']<=2.:
        local_h=seed['mean_h']
    floor=max(2.,min(local_h,seed['mean_h'])-2.5)
    foreground=inside&valid&np.isfinite(h)&(h>=floor)&(h<=local_h+4.)&~vegetation&spectral
    radius=max(1,int(round(.15/math.sqrt(abs(tr.determinant)))))
    foreground=binary_closing(np.pad(foreground,radius),structure=np.ones((2*radius+1,2*radius+1)))[radius:-radius,radius:-radius]&inside
    labs,_=label(foreground);pc,pr=(~tr)*seed['point'];pr=int(math.floor(pr));pc=int(math.floor(pc))
    selected=labs[pr,pc] if 0<=pr<labs.shape[0] and 0<=pc<labs.shape[1] else 0
    if selected==0:return geometry,'LOCAL_SURFACE_SEED_NOT_COVERED'
    component=labs==selected
    polygons=[shape(g) for g,v in shapes(component.astype('uint8'),mask=component,transform=tr) if v==1]
    if not polygons:return geometry,'LOCAL_SURFACE_EMPTY'
    result=max(polygons,key=lambda p:p.area)
    # Small spectral gaps (e.g. roof fixtures) are not independent courtyards.
    # Larger holes remain explicit and therefore require complex-shape review.
    result=Polygon(result.exterior,[ring for ring in result.interiors if Polygon(ring).area>2.])
    result=result.simplify(.25,preserve_topology=True)
    if not result.is_valid or result.area<8 or result.area/geometry.area<.10:return geometry,'LOCAL_SURFACE_INSUFFICIENT'
    return result,'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE'


def retry_roof_geometry(geometry,image_rgb,transform,lidar_data,segmenter):
    """Run the bounded recovery stage used by pipeline and diagnostic scripts.

    Returns candidates, every optical attempt, sensor prompts and status. All
    candidates remain hypotheses. Unsupported terrain stays a recorded failure.
    """
    from .roof_simple_geometry import simple_roof_geometry
    from .optical_roof_edges import refine_roof_color
    from .roof_candidate_routing import vegetation_color_fraction
    from .sensor_review import review_candidates
    prompts=roof_retry_prompts(geometry,image_rgb,transform,lidar_data)
    answer={'prompts':prompts,'attempts':[],'candidates':[],'status':prompts['status']}
    height,width=image_rgb.shape[:2]
    bounds=geometry.buffer(4).bounds
    pixels=[(~transform)*(x,y) for x in (bounds[0],bounds[2]) for y in (bounds[1],bounds[3])]
    if any(not (0<=c<width and 0<=r<height) for c,r in pixels):
        answer['status']='NEEDS_COMPLETE_IMAGE_COVERAGE';return answer
    usable=[]
    for index,seed in enumerate(prompts['seeds'],1):
        result=segmenter.segment_candidate(*bounds,mean_h=seed['mean_h'],max_h=seed['max_h'],
            lidar_area=geometry.area,internal_pts_geo=[seed['point']],height_min_threshold=2.)
        optical=result.get('geometry')
        attempt={'index':index,'point':seed['point'],'sam2_score':result.get('sam2_score',0),
                 'status':result['status'],'raw_optical':optical}
        if optical is not None and optical.geom_type=='Polygon':
            trimmed,color=trim_retry_roof_surface(optical,image_rgb,transform,lidar_data,seed)
            if color!='LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE':
                trimmed,color=refine_roof_color(optical,image_rgb,transform,lidar_data)
            simple,info=simple_roof_geometry(trimmed)
            vegetation=vegetation_color_fraction(simple,image_rgb,transform)
            evidence=review_candidates([{'geometry':simple}],lidar_data['class_evidence'],lidar_data['transform'])[0]
            candidate={'geometry':simple,'sam2_score':result.get('sam2_score',0),
                       'simple_method':info['method'],'simple_support':info.get('support',0.),
                       'simple_coverage':info.get('coverage',0.),'seed_x':seed['point'][0],
                       'seed_y':seed['point'][1],'attempt_index':index,'color_method':color,
                       'vertices':len(simple.exterior.coords)-1,'vegetation_fraction':vegetation,
                       'building_fraction':evidence['qa_building_fraction']}
            attempt.update(candidate)
            if info['method']!='NEEDS_REVIEW' and vegetation<.35 and evidence['qa_building_fraction']>.15:
                usable.append(candidate)
        answer['attempts'].append(attempt)
    for candidate in sorted(usable,key=lambda r:(-r['sam2_score'],-r['geometry'].area)):
        g=candidate['geometry']
        if any(g.intersection(k['geometry']).area/min(g.area,k['geometry'].area)>.35 for k in answer['candidates']):continue
        answer['candidates'].append(candidate)
    answer['status']=('RECTIFIED_HYPOTHESES_PENDING_REVIEW' if answer['candidates'] else
                      ('NO_SUPPORTED_ROOF_SEED' if not prompts['seeds'] else 'UNRESOLVED_AFTER_LOCAL_RETRY'))
    return answer
