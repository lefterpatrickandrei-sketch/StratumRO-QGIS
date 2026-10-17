"""Opt-in simplification that preserves the observed optical roof outline."""
from shapely.geometry import Point,Polygon
from .roof_simple_geometry import simple_roof_geometry


def simplify_observed_roof(raw,anchor,*,max_vertices=32,min_fidelity=.975,max_boundary_shift_m=.8):
    if raw.geom_type!='Polygon' or not raw.is_valid:raise ValueError('Valid optical polygon required')
    # Pixel pinholes/skylight texture are not courtyard boundaries. Preserve
    # all substantial holes and disclose any small-hole cleanup in diagnostics.
    original=raw
    raw=Polygon(raw.exterior,[ring for ring in raw.interiors if Polygon(ring).area>=4.])
    small_holes_removed=len(original.interiors)-len(raw.interiors)
    candidates=[]
    if not raw.interiors:
        g,info=simple_roof_geometry(raw,min_support=min_fidelity,min_coverage=min_fidelity,max_vertices=max_vertices)
        if info['method']!='NEEDS_REVIEW':candidates.append((g,info['method']))
    for tolerance in [.10,.20,.30,.40,.50,.60,.80]:
        candidates.append((raw.simplify(tolerance,preserve_topology=True),'FAITHFUL_OPTICAL_SIMPLIFICATION'))
        for radius in [.15,.30]:
            smoothed=raw.buffer(radius).buffer(-radius).buffer(-radius).buffer(radius)
            if smoothed.geom_type=='Polygon':
                candidates.append((smoothed.simplify(tolerance,preserve_topology=True),'FAITHFUL_DENOISED_OPTICAL'))
    accepted=[]
    for g,method in candidates:
        n=len(g.exterior.coords)-1+sum(len(r.coords)-1 for r in g.interiors)
        if not g.is_valid or not g.covers(Point(*anchor)) or len(g.interiors)!=len(raw.interiors):continue
        intersection=g.intersection(raw).area;coverage=intersection/raw.area;support=intersection/g.area
        shift=g.exterior.hausdorff_distance(raw.exterior)
        if n<=max_vertices and min(coverage,support)>=min_fidelity and shift<=max_boundary_shift_m:
            accepted.append((n,-intersection/g.union(raw).area,g,method,coverage,support,shift))
    if not accepted:
        return raw.simplify(.2,preserve_topology=True),{'status':'NEEDS_GEOMETRY_REVIEW','method':'OPTICAL_MASK_PRESERVED','lidar_used':False,
                 'small_holes_removed':small_holes_removed}
    n,_,g,method,coverage,support,shift=min(accepted,key=lambda x:(x[0],x[1]))
    return g,{'status':'RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW','method':method,'lidar_used':False,
              'coverage':coverage,'support':support,'boundary_shift_m':shift,'vertices':n,
              'small_holes_removed':small_holes_removed,
              'comparison_role':'RAW_OPTICAL_MASK_NOT_GROUND_TRUTH','courtyards':len(g.interiors)}


def rectangular_roof_core(raw,anchor,*,opening_radius_m=1.,max_removed_fraction=.30):
    """Opt-in planar-roof fit removing thin attached equipment/duct masks.

    Only use after the target has been reviewed as a rectangular roof plane.
    Detached surfaces and removed areas remain explicit review diagnostics.
    """
    raw=Polygon(raw.exterior,[ring for ring in raw.interiors if Polygon(ring).area>=4.])
    for radius in [opening_radius_m,opening_radius_m*1.5,opening_radius_m*2,opening_radius_m*2.5]:
        opened=raw.buffer(-radius).buffer(radius)
        parts=list(opened.geoms) if hasattr(opened,'geoms') else [opened]
        parts=[p for p in parts if p.geom_type=='Polygon' and p.covers(Point(*anchor))]
        if not parts:continue
        core=max(parts,key=lambda p:p.area);removed=raw.difference(core).area/raw.area
        if removed>max_removed_fraction:continue
        geom,info=simple_roof_geometry(Polygon(core.exterior),min_support=.94,min_coverage=.90,max_vertices=4)
        if info['method']=='NEEDS_REVIEW':continue
        return geom,{'status':'RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW','method':'REVIEWED_PLANAR_ROOF_CORE',
            'lidar_used':False,'removed_mask_fraction':removed,'removed_mask_m2':raw.difference(core).area,
            'opening_radius_m':radius,'coverage':info['coverage'],'support':info['support'],'raw_mask_is_ground_truth':False}
    return raw,{'status':'NEEDS_GEOMETRY_REVIEW','method':'NO_SUPPORTED_PLANAR_CORE','lidar_used':False}
