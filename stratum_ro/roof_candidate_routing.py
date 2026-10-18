"""Conservative visual-inspection routing; preserves every raw hypothesis.

Rectangularity and optical support select a useful first inspection layer, not
proof of a building. Compound/occluded roofs stay in the full review layer.
"""
import math


def vegetation_color_fraction(geometry,image_rgb,transform):
    """Measure saturated yellow/green pixels; a routing cue, not classification."""
    import numpy as np
    from rasterio.features import rasterize
    from rasterio import Affine
    xmin,ymin,xmax,ymax=geometry.bounds
    points=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(np.floor(min(p[0] for p in points))))
    c1=min(image_rgb.shape[1],int(np.ceil(max(p[0] for p in points))))
    r0=max(0,int(np.floor(min(p[1] for p in points))))
    r1=min(image_rgb.shape[0],int(np.ceil(max(p[1] for p in points))))
    if c1<=c0 or r1<=r0:return 0.
    rgb=image_rgb[r0:r1,c0:c1].astype(float)
    inside=rasterize([(geometry,1)],out_shape=rgb.shape[:2],
                    transform=transform*Affine.translation(c0,r0),dtype='uint8').astype(bool)
    maximum=rgb.max(axis=2);inside &= maximum>0
    if not inside.any():return 0.
    saturation=(maximum-rgb.min(axis=2))/np.maximum(maximum,1.)
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    vegetation=(saturation>.25)&(g>=.75*r)&(g>1.15*b)
    return float(vegetation[inside].mean())


def route_roof_candidate(feature, raw_geometry):
    record = dict(feature)
    geom = record['geometry']
    if raw_geometry is None or raw_geometry.is_empty or not raw_geometry.is_valid:
        raise ValueError('A valid original optical mask is required')
    if geom.is_empty or not geom.is_valid or geom.area <= 0:
        raise ValueError('A valid candidate polygon is required')
    score = float(record.get('sam2_score',0))
    support = geom.intersection(raw_geometry).area / geom.area
    rectangle = geom.area / geom.minimum_rotated_rectangle.area
    # Unsupported glass roofs require stronger optical structure, not class6.
    lacks_building = float(record.get('qa_building_fraction',0)) == 0
    threshold = .90 if lacks_building else .85
    reasons = []
    if not math.isfinite(score) or score < .85:
        reasons.append('SCOR_OPTIC_INSUFICIENT')
    if rectangle < threshold:
        reasons.append('FORMA_COMPLEXA')
    if support < threshold:
        reasons.append('REGULARIZARE_FARA_SUPORT_OPTIC')
    if int(record.get('qa_returns',0)) == 0:
        reasons.append('FARA_OBSERVATII_LIDAR')
    if float(record.get('qa_building_fraction',0))<.10 and float(record.get('vegetation_color_fraction',0))>=.50:
        reasons.append('VEGETATIE_OPTICA_FARA_SUPORT_CLADIRE')
    record.update(optical_support=round(support,6), rectangularity=round(rectangle,6),
                  route='REVIZUIRE_COMPLEXA' if reasons else 'INSPECTIE_PRIORITARA',
                  route_reason=';'.join(reasons) or 'STRUCTURA_OPTICA_REGULATA')
    return record


def prioritize_roof_candidates(records):
    """Mark duplicate alternatives for review, using no reference geometry.

    Returns one copy of every input record. Never deletes a candidate or changes
    geometry; a selected layer can be derived by filtering the route attribute.
    """
    result = [dict(r) for r in records]
    order = sorted(range(len(result)),key=lambda i:(
        -float(result[i].get('optical_support',0)),
        -float(result[i].get('rectangularity',0)),
        -float(result[i].get('sam2_score',0)),
        str(result[i].get('qa_id','')), str(result[i].get('proposal_source',''))))
    kept=[]
    for i in order:
        item=result[i]
        if item['route'] != 'INSPECTIE_PRIORITARA':continue
        geom=item['geometry']
        for j in kept:
            other=result[j]['geometry']
            if not geom.intersects(other):continue
            overlap=geom.intersection(other).area
            if overlap/min(geom.area,other.area)>=.8:
                item['route']='REVIZUIRE_COMPLEXA'
                item['route_reason']='ALTERNATIVA_SUPRAPUSA'
                break
        else:kept.append(i)
    return result
