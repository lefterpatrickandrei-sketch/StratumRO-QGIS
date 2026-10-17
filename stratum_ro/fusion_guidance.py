"""Local LiDAR guidance for an independently supplied optical candidate.

Missing LiDAR is not negative evidence. This module does not detect RGB objects
or certify source alignment; the caller supplies those inputs and their quality.
"""
import numpy as np
from scipy.ndimage import label, distance_transform_edt


def select_fusion_prompt(anchor, transform, building_counts, relative_height,
                         valid_mask, lidar_compatible=True, max_anchor_gap_m=3.):
    counts=np.asarray(building_counts)
    height=np.asarray(relative_height)
    valid=np.asarray(valid_mask,dtype=bool)
    if counts.ndim!=2 or height.shape!=counts.shape or valid.shape!=counts.shape:
        raise ValueError('Matching 2D evidence grids required')
    if not np.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
        raise ValueError('Invertible transform required')
    if len(anchor)!=2 or not np.all(np.isfinite(anchor)) or max_anchor_gap_m<0:
        raise ValueError('Finite anchor and nonnegative distance required')
    result={'route':'RGB_FALLBACK_REQUIRES_REVIEW','point':list(map(float,anchor)),
            'source':'REVIEWED_RGB_ANCHOR','reason':'LIDAR_UNAVAILABLE_OR_INCOMPATIBLE',
            'negative_points':[],'owner_verdict':'PENDING_OWNER_REVIEW'}
    if not lidar_compatible:
        return result
    support=valid&np.isfinite(height)&(height>=1.8)&(counts>0)
    rr,cc=np.nonzero(support)
    if not len(rr):
        result['reason']='NO_LOCAL_BUILDING_SUPPORT'
        return result
    xx,yy=transform*(cc+.5,rr+.5)
    distances=np.hypot(xx-anchor[0],yy-anchor[1])
    near=int(np.argmin(distances))
    if distances[near]>max_anchor_gap_m:
        result['reason']='BUILDING_SUPPORT_BELONGS_ELSEWHERE'
        return result
    labs,_=label(support)
    component=labs==labs[rr[near],cc[near]]
    # Interior point of this component, not a distant neighboring building.
    interior=distance_transform_edt(np.pad(component,1))[1:-1,1:-1]
    pr,pc=np.unravel_index(np.argmax(interior),interior.shape)
    gx,gy=transform*(pc+.5,pr+.5)
    result.update(route='LIDAR_GUIDED_REQUIRES_REVIEW',point=[float(gx),float(gy)],
                  source='LOCAL_CLASS6_AND_HEIGHT',reason='LOCAL_SUPPORT_FOUND',
                  support_cells=int(component.sum()),anchor_gap_m=float(distances[near]))
    return result
