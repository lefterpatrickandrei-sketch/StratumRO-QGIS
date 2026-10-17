"""Local LiDAR guidance for an independently supplied optical candidate.

Missing LiDAR is not negative evidence. This module does not detect RGB objects
or certify source alignment; the caller supplies those inputs and their quality.
"""
import numpy as np
from scipy.ndimage import label, distance_transform_edt


def select_fusion_prompt(anchor, transform, building_counts, relative_height,
                         valid_mask, lidar_compatible=True, max_anchor_gap_m=3.,
                         max_prompt_shift_m=None):
    counts=np.asarray(building_counts)
    height=np.asarray(relative_height)
    valid=np.asarray(valid_mask,dtype=bool)
    if counts.ndim!=2 or height.shape!=counts.shape or valid.shape!=counts.shape:
        raise ValueError('Matching 2D evidence grids required')
    if not np.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
        raise ValueError('Invertible transform required')
    if (len(anchor)!=2 or not np.all(np.isfinite(anchor)) or
        not np.isfinite(max_anchor_gap_m) or max_anchor_gap_m<0 or
        (max_prompt_shift_m is not None and
         (not np.isfinite(max_prompt_shift_m) or max_prompt_shift_m<0))):
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
    # A connected Class6 component may bridge adjacent roofs. Its global most
    # interior point must not move the reviewed candidate onto a neighbor.
    interior=distance_transform_edt(np.pad(component,1))[1:-1,1:-1]
    cr,cc=np.nonzero(component)
    cx,cy=transform*(cc+.5,cr+.5)
    shifts=np.hypot(cx-anchor[0],cy-anchor[1])
    # Bounded mode is opt-in: regression runs show that a local point improves
    # small annexes but may worsen large articulated roofs. Preserve both modes.
    eligible=shifts<=max_prompt_shift_m if max_prompt_shift_m is not None else np.ones(shifts.shape,dtype=bool)
    if not eligible.any():
        result['reason']='NO_SUPPORTED_PROMPT_WITHIN_IDENTITY_RADIUS'
        return result
    er,ec=cr[eligible],cc[eligible]
    best=int(np.argmax(interior[er,ec]));pr,pc=er[best],ec[best]
    gx,gy=transform*(pc+.5,pr+.5)
    result.update(route='LIDAR_GUIDED_REQUIRES_REVIEW',point=[float(gx),float(gy)],
                  source='LOCAL_CLASS6_AND_HEIGHT',reason='LOCAL_SUPPORT_FOUND',
                  support_cells=int(component.sum()),anchor_gap_m=float(distances[near]),
                  prompt_shift_m=float(np.hypot(gx-anchor[0],gy-anchor[1])),
                  max_prompt_shift_m=float(max_prompt_shift_m) if max_prompt_shift_m is not None else None)
    return result
