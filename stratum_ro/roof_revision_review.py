"""Conservative comparison of roof revisions, never ground truth or acceptance."""
def review_roof_revision(previous, proposed, *, min_previous_coverage=.97,
                         overlap_tolerance_m2=.25):
    """Require explicit review of omitted previous surfaces and identity conflicts.

    Previous hypotheses can be wrong. These checks protect against silent
    replacement; they do not force the proposed geometry to match a reference.
    """
    reasons=[];changes=[];overlaps=[]
    for ident,geom in proposed.items():
        if not geom.is_valid or geom.is_empty:
            reasons.append({'body_id':ident,'reason':'INVALID_GEOMETRY'})
            continue
        if ident not in previous:
            reasons.append({'body_id':ident,'reason':'NEW_BODY_IDENTITY_REQUIRES_REVIEW'})
            continue
        old=previous[ident]
        coverage=old.intersection(geom).area/old.area
        missing=old.difference(geom).area
        holes_before=len(getattr(old,'interiors',[]));holes_after=len(getattr(geom,'interiors',[]))
        changes.append({'body_id':ident,'previous_coverage':coverage,'omitted_previous_m2':missing,
                        'holes_before':holes_before,'holes_after':holes_after})
        if coverage<min_previous_coverage:
            reasons.append({'body_id':ident,'reason':'PREVIOUS_ROOF_SURFACE_OMITTED'})
        if holes_before!=holes_after:
            reasons.append({'body_id':ident,'reason':'COURTYARD_TOPOLOGY_CHANGED'})
    for ident in previous.keys()-proposed.keys():
        reasons.append({'body_id':ident,'reason':'PREVIOUS_BODY_MISSING'})
    items=list(proposed.items())
    for i,(a,ga) in enumerate(items):
        for b,gb in items[i+1:]:
            if not ga.is_valid or not gb.is_valid:continue
            area=ga.intersection(gb).area
            if area>overlap_tolerance_m2:
                overlaps.append({'a':a,'b':b,'intersection_m2':area})
                reasons.append({'body_ids':[a,b],'reason':'BODY_IDENTITY_OVERLAP'})
    return {'comparison_role':'PREVIOUS_HYPOTHESES_NOT_GROUND_TRUTH',
            'automatic_adoption_allowed':False,'review_reasons':reasons,
            'changes':changes,'overlaps':overlaps}
