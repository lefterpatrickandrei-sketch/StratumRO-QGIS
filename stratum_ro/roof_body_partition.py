"""Spectral seam hypotheses for adjacent roof bodies; never building identity.

A color transition may be material or illumination within ONE building. Every
partition requires human review; the parent mask must always remain available.
"""
import math
import numpy as np
from rasterio import Affine
from rasterio.features import rasterize
from shapely import affinity
from shapely.geometry import box
from .roof_simple_geometry import _axis_angle,simple_roof_geometry


def split_color_roof_bodies(geometry,image_rgb,transform,min_area_m2=20.):
    """Return one unchanged body or two supported simple partition hypotheses.

    Fit a single straight seam aligned with the parent roof, separating red and
    non-red RGB. Both parts >=20m2 and >=20% of parent, spectral accuracy >=90%.
    Reference polygons and feature IDs are never inputs to this operation.
    """
    unchanged=[{'geometry':geometry,'body_source':'PARENT_UNSPLIT','split_status':'NO_SUPPORTED_SEAM'}]
    if geometry is None or geometry.geom_type!='Polygon' or geometry.is_empty or not geometry.is_valid:
        raise ValueError('Valid Polygon required')
    if geometry.interiors:return unchanged
    if image_rgb.ndim!=3 or image_rgb.shape[2]!=3 or min_area_m2<=0:
        raise ValueError('RGB image and positive minimum area required')
    if not math.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
        raise ValueError('Invertible affine required')
    xmin,ymin,xmax,ymax=geometry.bounds
    points=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(math.floor(min(v[0] for v in points))));c1=min(image_rgb.shape[1],int(math.ceil(max(v[0] for v in points))))
    r0=max(0,int(math.floor(min(v[1] for v in points))));r1=min(image_rgb.shape[0],int(math.ceil(max(v[1] for v in points))))
    if c1<=c0 or r1<=r0:return unchanged
    rgb=image_rgb[r0:r1,c0:c1].astype(float);tr=transform*Affine.translation(c0,r0)
    inside=rasterize([(geometry,1)],out_shape=rgb.shape[:2],transform=tr,dtype='uint8').astype(bool)
    rows,cols=np.nonzero(inside)
    if len(rows)<20:return unchanged
    values=rgb[inside]
    angle=_axis_angle(geometry);theta=math.radians(angle)
    origin=geometry.centroid.coords[0]
    x,y=tr*(cols+.5,rows+.5);dx=x-origin[0];dy=y-origin[1]
    axes=[dx*math.cos(theta)+dy*math.sin(theta),-dx*math.sin(theta)+dy*math.cos(theta)]
    options=[]
    for threshold in (20,25,30,35,40):
        red=(values[:,0]-values[:,1]>threshold)&(values[:,0]-values[:,2]>15)
        if not .2<=red.mean()<=.8:continue
        for axis,coordinate in enumerate(axes):
            order=np.argsort(coordinate,kind='stable');labels=red[order];ordered=coordinate[order]
            cumulative=np.cumsum(labels);n=len(labels)
            indices=np.arange(max(1,int(.2*n)),min(n-1,int(.8*n)))
            left_red=cumulative[indices-1];right_red=cumulative[-1]-left_red
            correct=np.maximum(left_red+(n-indices-right_red),(indices-left_red)+right_red)
            idx=int(indices[np.argmax(correct)])
            cut=float((ordered[idx-1]+ordered[idx])/2)
            accuracy=float(correct.max()/n)
            options.append((accuracy,axis,cut,threshold))
    if not options:return unchanged
    accuracy,axis,cut,threshold=max(options)
    if accuracy<.90:return unchanged
    aligned=affinity.rotate(geometry,-angle,origin=origin)
    xmin,ymin,xmax,ymax=aligned.bounds
    # Coordinates above are centered; aligned shapely coordinates retain origin.
    cut+=origin[axis]
    if axis==0:clips=[box(xmin-1,ymin-1,cut,ymax+1),box(cut,ymin-1,xmax+1,ymax+1)]
    else:clips=[box(xmin-1,ymin-1,xmax+1,cut),box(xmin-1,cut,xmax+1,ymax+1)]
    result=[]
    for index,clip in enumerate(clips,1):
        part=aligned.intersection(clip)
        if part.geom_type!='Polygon' or part.area<max(min_area_m2,.2*geometry.area):return unchanged
        part=affinity.rotate(part,angle,origin=origin)
        simple,info=simple_roof_geometry(part,orientation_hint=geometry)
        if info['method']=='NEEDS_REVIEW':return unchanged
        # Clip at the exact shared seam to prevent independent fitting overlap.
        world_clip=affinity.rotate(clip,angle,origin=origin)
        simple=simple.intersection(world_clip)
        if simple.geom_type!='Polygon' or not simple.is_valid:return unchanged
        result.append({'geometry':simple,'body_source':f'SPECTRAL_SEAM_BODY_{index}',
                       'split_status':'PARTITION_REVIEW_REQUIRED','seam_accuracy':accuracy,
                       'seam_red_threshold':threshold,
                       'simple_method':info['method']})
    if result[0]['geometry'].intersection(result[1]['geometry']).area>1e-6:return unchanged
    return result
