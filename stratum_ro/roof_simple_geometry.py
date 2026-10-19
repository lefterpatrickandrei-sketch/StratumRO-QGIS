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


def roof_shape_family(geometry):
    """Descriptive geometry family, never a cadastral body classification."""
    if geometry.interiors:
        return 'COURTYARD'
    n = len(geometry.exterior.coords)-1
    xy = np.asarray(geometry.exterior.coords)
    edges = np.diff(xy, axis=0)
    lengths = np.linalg.norm(edges, axis=1)
    orthogonal = all(abs(np.dot(a,b))/(la*lb) < .03
        for a,b,la,lb in zip(edges,np.roll(edges,-1,axis=0),lengths,np.roll(lengths,-1)))
    if not orthogonal:
        return 'OBLIQUE_OR_IRREGULAR'
    if n == 4:return 'RECTANGLE'
    if n == 6:return 'L'
    if n == 8:
        from shapely.geometry.polygon import orient
        pts=np.asarray(orient(geometry,sign=1).exterior.coords)[:-1]
        reflex=[]
        for i,p in enumerate(pts):
            a=p-pts[i-1];b=pts[(i+1)%n]-p
            if a[0]*b[1]-a[1]*b[0]<0:reflex.append(i)
        if len(reflex)==2 and (reflex[1]-reflex[0]) in (1,n-1):return 'U'
        return 'T_OR_OFFSET'  # eight corners alone cannot distinguish T and Z
    return 'ARTICULATED_ORTHOGONAL'


def roof_shape_variations(observed, previous=None, *, min_support=.92,
                          min_coverage=.92, max_area_change=.08,
                          max_boundary_distance=1.5, min_edge=1., limit=6,
                          local_change_tolerance=.35, max_local_change_area=.75):
    """Generate and rank simple alternatives using the existing ring fitter.

    Projected metres required. Limits describe development generalization, not
    survey accuracy. Preserve holes exactly and reject lost substantial wings.
    Keep a rejected rectangle for transparent comparison, not forced output.
    Each family/complexity competes independently; no fixed template is imposed.
    """
    if observed.geom_type!='Polygon' or not observed.is_valid or observed.is_empty:
        raise ValueError('Valid Polygon required')
    if not (0<min_support<=1 and 0<min_coverage<=1 and 0<=max_area_change<=1
            and max_boundary_distance>0 and min_edge>0 and limit>=2
            and math.isfinite(local_change_tolerance) and local_change_tolerance>0
            and math.isfinite(max_local_change_area) and max_local_change_area>=0):
        raise ValueError('Invalid variation constraints')
    options=[];seen=set()
    from shapely.geometry import Point
    hull=observed.convex_hull
    void=hull.difference(Polygon(observed.exterior))
    recesses=[]
    for pocket in getattr(void,'geoms',[void]):
        if pocket.is_empty or pocket.geom_type!='Polygon' or pocket.area<1.:continue
        depth=max(Point(xy).distance(hull.boundary) for xy in pocket.exterior.coords)
        if depth>=.8:recesses.append(pocket)
    def add(g,method):
        if g is None or not g.is_valid or g.is_empty or g.geom_type!='Polygon':return
        g=g.simplify(1e-7,preserve_topology=True)
        key=g.normalize().wkb
        if key in seen:return
        seen.add(key)
        inter=g.intersection(observed).area
        support=inter/g.area;coverage=inter/observed.area
        shift=g.boundary.hausdorff_distance(observed.boundary)
        change=abs(g.area-observed.area)/observed.area
        # Global area fractions hide small but deep notches on large roofs.
        # Measure changes beyond a physical boundary band, in projected metres.
        # This is fidelity to the observation, not proof it is a whole roof.
        added_core=g.difference(observed.buffer(local_change_tolerance))
        removed_core=observed.difference(g.buffer(local_change_tolerance))
        def largest_area(geometry):
            # Long thin edge bands are not compact lost wings/notches. Keep
            # global support/distance checks for these, instead of preserving
            # every mask wobble simply because its total length is large.
            areas=[]
            for part in getattr(geometry,'geoms',[geometry]):
                if part.is_empty or part.geom_type!='Polygon':continue
                rectangle=np.asarray(part.minimum_rotated_rectangle.exterior.coords)
                width=np.linalg.norm(np.diff(rectangle,axis=0),axis=1).min()
                if width>=.8:areas.append(part.area)
            return max(areas,default=0.)
        added_local=largest_area(added_core);removed_local=largest_area(removed_core)
        lengths=np.linalg.norm(np.diff(np.asarray(g.exterior.coords),axis=0),axis=1)
        reasons=[]
        def minimum_angle(polygon):
            xy=np.asarray(polygon.exterior.coords)[:-1]
            a=np.roll(xy,1,axis=0)-xy;b=np.roll(xy,-1,axis=0)-xy
            cosine=(a*b).sum(axis=1)/(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1))
            return float(np.degrees(np.arccos(np.clip(cosine,-1.,1.))).min())
        if minimum_angle(g)<40. and minimum_angle(observed)>=40.:
            reasons.append('INTRODUCES_ACUTE_SPUR')
        if support<min_support:reasons.append('ADDED_UNSUPPORTED_AREA')
        if coverage<min_coverage:reasons.append('LOST_OBSERVED_WING_OR_AREA')
        if shift>max_boundary_distance:reasons.append('BOUNDARY_DISTANCE')
        if change>max_area_change:reasons.append('AREA_CHANGE')
        if added_local>max_local_change_area:reasons.append('FILLS_LOCAL_RECESS_OR_ADDS_SPUR')
        if removed_local>max_local_change_area:reasons.append('CUTS_LOCAL_WING_OR_CORNER')
        if any(g.intersection(pocket).area/pocket.area>.30 for pocket in recesses):
            reasons.append('FILLS_SIGNIFICANT_RECESS')
        # Holes are evidence of unknown courtyards/lightwells, never auto-fill.
        for hole in observed.interiors:
            if g.intersection(Polygon(hole)).area>1e-6:reasons.append('FILLS_COURTYARD')
        if lengths.min()<min_edge and method!='OBSERVATION':reasons.append('SHORT_EDGE')
        options.append(dict(geometry=g,method=method,family=roof_shape_family(g),
            vertices=len(g.exterior.coords)-1+sum(len(r.coords)-1 for r in g.interiors),
            support=float(support),coverage=float(coverage),iou=float(inter/g.union(observed).area),
            boundary_distance_m=float(shift),area_change_fraction=float(change),
            added_local_core_m2=float(added_local),removed_local_core_m2=float(removed_local),
            eligible=not reasons,reasons=sorted(set(reasons))))
    add(observed,'OBSERVATION')
    if previous is not None:add(previous,'PREVIOUS_SIMPLE_PROPOSAL')
    angle=_axis_angle(observed);origin=observed.centroid.coords[0]
    for delta in (0,-2,2):
        aligned=affinity.rotate(observed,-angle-delta,origin=origin)
        add(affinity.rotate(box(*aligned.bounds),angle+delta,origin=origin),'RECTANGLE')
        for tolerance in (.4,.75,1.,1.5,2.,3.,4.):
            simple=aligned.simplify(tolerance,preserve_topology=True)
            fitted=_orthogonal_ring(simple)
            if fitted is not None:
                world=affinity.rotate(fitted,angle+delta,origin=origin)
                # Preserve original interior rings rather than reconstruct holes.
                if observed.interiors:world=Polygon(world.exterior,[r.coords for r in observed.interiors])
                add(world,'ORTHOGONAL_RUNS')
            # Genuine oblique roofs may be simpler without being orthogonal.
            add(affinity.rotate(simple,angle+delta,origin=origin),'FREE_DIRECTION_LINES')
    eligible=[o for o in options if o['eligible']]
    chosen=min(eligible,key=lambda o:(o['vertices'], -o['iou'])) if eligible else options[0]
    # One best example per shape family/vertex count; avoid near-identical clutter.
    representatives={}
    for o in sorted(options,key=lambda o:(not o['eligible'],o['vertices'],-o['iou'])):
        representatives.setdefault((o['family'],o['vertices']),o)
    alternatives=[chosen]
    for o in representatives.values():
        if o is not chosen and len(alternatives)<limit:alternatives.append(o)
    if all(o['method']!='RECTANGLE' for o in alternatives):
        rectangle=next((o for o in options if o['method']=='RECTANGLE'),None)
        if rectangle is not None:alternatives[-1]=rectangle
    return chosen,alternatives


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
                         angle_search_degrees=4, *, max_boundary_distance=None,
                         max_area_change=None):
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
    for limit in (max_boundary_distance, max_area_change):
        if limit is not None and (not math.isfinite(limit) or limit < 0):
            raise ValueError('Finite nonnegative optional change limits required')
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
        # Physical guards apply to every candidate, including rectangles, before
        # selecting the fewest vertices. Mask agreement is not ground truth.
        if max_boundary_distance is not None and candidate.boundary.hausdorff_distance(aligned.boundary)>max_boundary_distance:
            continue
        if max_area_change is not None and abs(candidate.area-aligned.area)/aligned.area>max_area_change:
            continue
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
                min_support,min_coverage,max_vertices,min_edge,angle_search_degrees=0,
                max_boundary_distance=max_boundary_distance,max_area_change=max_area_change)
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
