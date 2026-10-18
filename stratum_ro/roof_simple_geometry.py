"""Simple rectilinear roof hypotheses, constrained by observed optical support.

Coordinates must be projected metres. No reference contours are accepted.
Failure returns the observed polygon with NEEDS_REVIEW, never a forced rectangle.
"""
import math
import numpy as np
from shapely import affinity
from shapely.geometry import Polygon, box
from rasterio.features import rasterize
from rasterio.transform import from_origin


def _axis_angle(geometry):
    xy = np.asarray(geometry.minimum_rotated_rectangle.exterior.coords)
    edges = np.diff(xy, axis=0)
    edge = edges[np.argmax(np.linalg.norm(edges, axis=1))]
    return math.degrees(math.atan2(edge[1], edge[0]))


def _orthogonal_ring(polygon):
    """Fit alternating axis-aligned runs to a simplified polygon ring."""
    xy = np.asarray(polygon.exterior.coords)
    runs = []
    for a, b in zip(xy[:-1], xy[1:]):
        dx, dy = b - a
        axis = 0 if abs(dx) >= abs(dy) else 1  # horizontal / vertical
        weight = math.hypot(dx, dy)
        position = (a[1-axis] + b[1-axis]) / 2
        if runs and runs[-1][0] == axis:
            old = runs[-1]
            runs[-1] = (axis, (old[1]*old[2]+position*weight)/(old[2]+weight), old[2]+weight)
        else:
            runs.append((axis, position, weight))
    if len(runs)>1 and runs[0][0] == runs[-1][0]:
        a, b = runs[0], runs.pop()
        runs[0] = (a[0], (a[1]*a[2]+b[1]*b[2])/(a[2]+b[2]), a[2]+b[2])
    if len(runs)<4:return None
    corners=[]
    for previous, current in zip(runs[-1:]+runs[:-1],runs):
        h = previous if previous[0]==0 else current
        v = previous if previous[0]==1 else current
        corners.append((v[1],h[1]))
    candidate=Polygon(corners)
    return candidate if candidate.is_valid and candidate.area>0 else None


def simple_roof_geometry(optical, orientation_hint=None, min_support=.92,
                         min_coverage=.90, max_vertices=12, min_edge=.8,
                         angle_search_degrees=4):
    """Return (geometry, diagnostics), preferring the fewest supported corners.

    Simplification tolerances are physical metres. Orthogonal fits must retain
    >=90% of observed area and have >=92% of their area inside the observation.
    These development thresholds are not cadastral positional tolerances.
    A hint supplies orientation only, never location, size or a reference shape.
    """
    if optical is None or optical.geom_type!='Polygon' or optical.is_empty or not optical.is_valid:
        raise ValueError('A valid nonempty Polygon is required')
    if optical.interiors:
        return optical, {'method':'NEEDS_REVIEW','reason':'INTERIOR_RINGS'}
    if not (0<min_support<=1 and 0<min_coverage<=1 and max_vertices>=4 and min_edge>0
            and 0<=angle_search_degrees<=8):
        raise ValueError('Invalid geometry constraints')
    angle=_axis_angle(orientation_hint if orientation_hint is not None else optical)
    origin=optical.centroid.coords[0]
    aligned=affinity.rotate(optical,-angle,origin=origin)
    possibilities=[('SUPPORTED_RECTANGLE',box(*aligned.bounds))]
    # Occupancy quantiles ignore thin mask spurs. Support/coverage gates below
    # still reject boxes that erase a substantial annex or add an empty corner.
    xmin,ymin,xmax,ymax=aligned.bounds
    step=max(.15,math.sqrt((xmax-xmin)*(ymax-ymin)/150000))
    width=max(1,int(math.ceil((xmax-xmin)/step)))
    height=max(1,int(math.ceil((ymax-ymin)/step)))
    pixels=rasterize([(aligned,1)],out_shape=(height,width),
                     transform=from_origin(xmin,ymax,step,step),dtype='uint8')
    for fraction in (.01,.025,.04):
        bounds=[]
        for marginal in (pixels.sum(axis=0),pixels.sum(axis=1)):
            cumulative=np.cumsum(marginal)
            if cumulative[-1]==0:break
            lo=int(np.searchsorted(cumulative,fraction*cumulative[-1]))
            hi=int(np.searchsorted(cumulative,(1-fraction)*cumulative[-1]))
            bounds.append((lo,hi))
        if len(bounds)==2:
            (c0,c1),(r0,r1)=bounds
            possibilities.append(('SUPPORTED_CORE_RECTANGLE',box(xmin+c0*step,ymax-(r1+1)*step,
                                                              xmin+(c1+1)*step,ymax-r0*step)))
    for tolerance in (.35,.5,.75,1.,1.25,1.5,2.,2.5):
        simplified=aligned.simplify(tolerance,preserve_topology=True)
        fitted=_orthogonal_ring(simplified)
        if fitted is not None:possibilities.append(('SUPPORTED_ORTHOGONAL',fitted))
    accepted=[]
    for method,candidate in possibilities:
        vertices=len(candidate.exterior.coords)-1
        lengths=np.linalg.norm(np.diff(np.asarray(candidate.exterior.coords),axis=0),axis=1)
        if vertices>max_vertices or lengths.min()<min_edge:continue
        intersection=candidate.intersection(aligned).area
        support=intersection/candidate.area
        coverage=intersection/aligned.area
        if support<min_support or coverage<min_coverage:continue
        iou=intersection/candidate.union(aligned).area
        accepted.append((vertices,-iou,method,candidate,support,coverage))
    if not accepted:
        alternatives=[]
        hint=orientation_hint if orientation_hint is not None else optical
        for delta in range(-int(angle_search_degrees),int(angle_search_degrees)+1):
            if delta==0:continue
            fitted,info=simple_roof_geometry(optical,affinity.rotate(hint,delta),
                min_support,min_coverage,max_vertices,min_edge,angle_search_degrees=0)
            if info['method']!='NEEDS_REVIEW':
                info['orientation_search_delta_deg']=delta
                alternatives.append((fitted,info))
        if alternatives:
            return min(alternatives,key=lambda pair:(pair[1]['vertices'],-pair[1]['iou']))
        return optical,{'method':'NEEDS_REVIEW','reason':'NO_SUPPORTED_SIMPLE_FIT'}
    vertices,neg_iou,method,candidate,support,coverage=min(accepted,key=lambda x:(x[0],x[1]))
    result=affinity.rotate(candidate,angle,origin=origin)
    return result,{'method':method,'vertices':vertices,'support':float(support),
                   'coverage':float(coverage),'iou':float(-neg_iou),'angle_deg':angle,
                   'status':'REVIEW_REQUIRED'}
