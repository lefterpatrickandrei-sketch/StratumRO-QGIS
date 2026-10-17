"""Evidence-constrained refinement of prompted roof masks; never owner approval."""
import numpy as np
from scipy.ndimage import binary_opening,binary_closing,label,binary_fill_holes
from rasterio.features import rasterize,shapes
from shapely.geometry import Polygon,Point,shape
from .roof_simple_geometry import simple_roof_geometry


def refine_fusion_mask(raw,anchor,rgb,transform,height,building_counts,valid,
                       route,min_area_m2=8.):
    if raw is None or raw.geom_type!='Polygon' or not raw.is_valid:
        raise ValueError('Valid raw Polygon required')
    if rgb.shape[:2]!=height.shape or height.shape!=building_counts.shape or valid.shape!=height.shape:
        raise ValueError('Aligned sensor grids required')
    inside=rasterize([(raw,1)],out_shape=height.shape,transform=transform,dtype='uint8').astype(bool)
    colors=rgb.astype(float);r,g,b=np.moveaxis(colors,-1,0)
    high=colors.max(axis=2);sat=(high-colors.min(axis=2))/np.maximum(high,1)
    vegetation=(sat>.25)&(g>=.8*r)&(g>1.12*b)
    neutral=(sat<=.25)&(high>=65)
    reddish=(r-g>14)&(r-b>14)&(r>55)
    brown=(r>1.08*g)&(g>1.04*b)&(r-b>18)
    lidar_used=route=='LIDAR_GUIDED_REQUIRES_REVIEW'
    if lidar_used:
        observed=np.isfinite(height)&(height!=-9999)
        support=valid&observed&(height>=1.8)&(building_counts>0)&~vegetation
        support_labs,_=label(support)
        ac,ar=(~transform)*tuple(anchor);ac,ar=int(ac),int(ar)
        sid=support_labs[ar,ac] if 0<=ar<height.shape[0] and 0<=ac<height.shape[1] else 0
        local_support=(support_labs==sid) if sid else np.zeros(height.shape,dtype=bool)
        # Recover omitted roof pixels only from the same LiDAR component,
        # with spectral support. Keep the optical parent as audit evidence.
        nearby=rasterize([(raw.buffer(1.5),1)],out_shape=height.shape,transform=transform,dtype='uint8').astype(bool)
        envelope=inside|(local_support&nearby)
        # In this explicit compatible route, ground returns are evidence against
        # mask contamination. Unknown pixels remain separate, never fake ground.
        foreground=envelope&valid&observed&(height>=1.8)&~vegetation&(neutral|reddish|brown)
    else:
        # Optical-only route must not inherit the incompatible height veto.
        foreground=inside&valid&~vegetation&neutral
        envelope=inside
    step=np.sqrt(abs(transform.determinant))
    radius=max(1,int(round(.45/step)))
    yy,xx=np.ogrid[-radius:radius+1,-radius:radius+1]
    disk=(xx*xx+yy*yy<=radius*radius)
    # LiDAR is rasterized at 1m in this experiment; optical-only evidence does
    # not need the same gap repair and must not grow thin equipment ledges.
    close_radius=max(1,int(round((.6 if lidar_used else .15)/step)))
    cy,cx=np.ogrid[-close_radius:close_radius+1,-close_radius:close_radius+1]
    foreground=binary_closing(foreground,structure=(cx*cx+cy*cy<=close_radius*close_radius))&envelope&valid
    foreground=binary_opening(foreground,structure=disk)
    labs,_=label(foreground)
    c,rr=(~transform)*tuple(anchor);c,rr=int(c),int(rr)
    ident=labs[rr,c] if 0<=rr<labs.shape[0] and 0<=c<labs.shape[1] else 0
    if not ident:return raw,{'status':'UNRESOLVED_SEED_NOT_COVERED','method':'RAW_PRESERVED'}
    component=labs==ident
    polys=[shape(g) for g,v in shapes(component.astype('uint8'),mask=component,transform=transform) if v==1]
    observed=max(polys,key=lambda p:p.area)
    # Fill only small holes. Large courtyard observations remain explicit.
    holes=[ring for ring in observed.interiors if Polygon(ring).area>4]
    observed=Polygon(observed.exterior,holes).simplify(.3,preserve_topology=True)
    if not observed.is_valid or observed.area<min_area_m2:
        return raw,{'status':'UNRESOLVED_INSUFFICIENT_SURFACE','method':'RAW_PRESERVED'}
    shell=Polygon(observed.exterior)
    simple,info=simple_roof_geometry(shell)
    if info['method']=='NEEDS_REVIEW':
        return observed,{'status':'NEEDS_GEOMETRY_REVIEW','method':'EVIDENCE_TRIM_ONLY','lidar_used':lidar_used}
    retained=[]
    for ring in observed.interiors:
        hole=Polygon(ring)
        candidate,hinfo=simple_roof_geometry(hole)
        if hinfo['method']=='NEEDS_REVIEW':
            return observed,{'status':'NEEDS_COURTYARD_REVIEW','method':'EVIDENCE_TRIM_ONLY','lidar_used':lidar_used}
        if not simple.contains(candidate):
            return observed,{'status':'NEEDS_COURTYARD_REVIEW','method':'EVIDENCE_TRIM_ONLY','lidar_used':lidar_used}
        retained.append(candidate.exterior)
    result=Polygon(simple.exterior,retained)
    if not result.is_valid or not result.covers(Point(*anchor)):
        return observed,{'status':'NEEDS_GEOMETRY_REVIEW','method':'EVIDENCE_TRIM_ONLY','lidar_used':lidar_used}
    return result,{'status':'RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW','method':info['method'],
                   'lidar_used':lidar_used,'courtyards':len(retained),'raw_area_m2':raw.area,
                   'trimmed_area_m2':observed.area,'support':info.get('support'),'coverage':info.get('coverage')}
