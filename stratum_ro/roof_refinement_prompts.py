# -*- coding: utf-8 -*-
"""
Roof Refinement Prompts Generator for SAM / Segment Anything candidate masks.
Separates neutral ground, driveways, terraces from red roof building masks
using native orthophoto RGB and airborne LiDAR nDSM/class-6 evidence.

Strictly deterministic local implementation adhering to AGENTS.md.
Does not call external models or APIs. Never certifies cadastral boundaries.
"""

from typing import Dict, List, Tuple, Any, Optional
import math
from collections import deque
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.affinity import affine_transform
from affine import Affine


def _ensure_affine(transform: Any) -> Affine:
    """Validates and converts transform to an invertible Affine instance."""
    if isinstance(transform, Affine):
        aff = transform
    elif hasattr(transform, "to_gdal") or hasattr(transform, "column_vectors"):
        # Could be rasterio Affine
        aff = Affine(*transform[:6])
    elif isinstance(transform, (tuple, list)) and len(transform) >= 6:
        aff = Affine(*transform[:6])
    else:
        raise ValueError("Invalid transform: expected Affine or 6-element tuple/list.")

    for val in (aff.a, aff.b, aff.c, aff.d, aff.e, aff.f):
        if not math.isfinite(val):
            raise ValueError("Affine transform contains non-finite parameters.")

    det = aff.a * aff.e - aff.b * aff.d
    if abs(det) < 1e-12 or not math.isfinite(det):
        raise ValueError("Affine transform is degenerate or not invertible.")

    return aff


def _validate_inputs(
    geometry: Any,
    image_rgb: np.ndarray,
    image_transform: Any,
    lidar_data: Dict[str, Any],
    max_negative_points: int,
) -> Tuple[Polygon, Affine, Affine]:
    """Validates input immutability, shapes, ranges, types, and geometries."""
    # Geometry validation
    if geometry is None:
        raise ValueError("Geometry cannot be None.")
    if not isinstance(geometry, (Polygon, MultiPolygon)):
        raise TypeError(f"Geometry must be Polygon or MultiPolygon, got {type(geometry).__name__}.")
    if geometry.is_empty:
        raise ValueError("Geometry cannot be empty.")
    if not geometry.is_valid:
        raise ValueError("Geometry must be valid.")

    # Image RGB validation
    if not isinstance(image_rgb, np.ndarray):
        raise TypeError("image_rgb must be a numpy ndarray.")
    if image_rgb.ndim != 3 or image_rgb.shape[2] != 3:
        raise ValueError(f"image_rgb must have shape (H, W, 3), got {image_rgb.shape}.")
    if not np.all(np.isfinite(image_rgb)):
        raise ValueError("image_rgb contains non-finite values (NaN or Inf).")
    if np.any(image_rgb < 0) or np.any(image_rgb > 255):
        raise ValueError("image_rgb values must be within [0, 255].")

    # Image transform validation
    img_aff = _ensure_affine(image_transform)

    # LiDAR data validation
    if not isinstance(lidar_data, dict):
        raise TypeError("lidar_data must be a dict.")

    required_keys = ("ndsm", "class6_count", "transform")
    for k in required_keys:
        if k not in lidar_data:
            raise KeyError(f"lidar_data missing required key: {k}")

    ndsm = lidar_data["ndsm"]
    class6_count = lidar_data["class6_count"]
    lidar_transform = lidar_data["transform"]

    if not isinstance(ndsm, np.ndarray) or ndsm.ndim != 2:
        raise ValueError("lidar_data['ndsm'] must be a 2D numpy ndarray.")
    if not isinstance(class6_count, np.ndarray) or class6_count.ndim != 2:
        raise ValueError("lidar_data['class6_count'] must be a 2D numpy ndarray.")
    if ndsm.shape != class6_count.shape:
        raise ValueError(
            f"Shape mismatch: ndsm shape {ndsm.shape} != class6_count shape {class6_count.shape}."
        )

    if not np.all(np.isfinite(class6_count)):
        raise ValueError("class6_count contains non-finite values.")
    if np.any(class6_count < 0):
        raise ValueError("class6_count cannot contain negative counts.")

    lidar_aff = _ensure_affine(lidar_transform)

    if not isinstance(max_negative_points, (int, np.integer)):
        raise TypeError("max_negative_points must be an integer.")
    if max_negative_points < 0:
        raise ValueError("max_negative_points must be non-negative.")

    return geometry, img_aff, lidar_aff


def _rasterize_polygon_mask(poly, height, width, transform):
    from rasterio.features import rasterize
    return rasterize([(poly,1)],out_shape=(height,width),transform=transform,dtype='uint8').astype(bool)


def _compute_distance_transform_to_background(mask):
    from scipy.ndimage import distance_transform_edt
    return distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]


def _window(poly, transform, shape):
    xmin,ymin,xmax,ymax=poly.bounds
    corners=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(np.floor(min(p[0] for p in corners))))
    c1=min(shape[1],int(np.ceil(max(p[0] for p in corners))))
    r0=max(0,int(np.floor(min(p[1] for p in corners))))
    r1=min(shape[0],int(np.ceil(max(p[1] for p in corners))))
    return r0,r1,c0,c1


def refinement_prompts(geometry,image_rgb,image_transform,lidar_data,max_negative_points=4):
    """Red-roof anchors and neutral low-ground negatives; no reference inputs.

    Works on bounded raster windows. Neutral/glass roofs are never given ground
    negatives, because low heights can result from glass penetration.
    """
    from scipy.ndimage import label,find_objects
    data=lidar_data
    if isinstance(data,dict) and 'class6_count' not in data and 'class_evidence' in data:
        data=dict(data,class6_count=data['class_evidence']['building'])
    poly,itr,ltr=_validate_inputs(geometry,image_rgb,image_transform,data,max_negative_points)
    r0,r1,c0,c1=_window(poly,itr,image_rgb.shape[:2])
    disabled={'positive_points':[],'negative_points':[],'mode':'disabled'}
    if r1<=r0 or c1<=c0:return disabled
    rgb=image_rgb[r0:r1,c0:c1].astype(float);subtr=itr*Affine.translation(c0,r0)
    inside=_rasterize_polygon_mask(poly,rgb.shape[0],rgb.shape[1],subtr)
    red=(rgb[...,0]-rgb[...,1]>25)&(rgb[...,0]-rgb[...,2]>15)
    if not inside.any() or (inside&red).sum()/inside.sum()<.30:return disabled
    dist=_compute_distance_transform_to_background(inside&red)
    rr,cc=np.unravel_index(np.argmax(dist),dist.shape)
    positive=tuple(float(v) for v in subtr*(cc+.5,rr+.5))
    answer={'positive_points':[positive],'negative_points':[],'mode':'red_roof'}
    if max_negative_points==0:return answer
    lr0,lr1,lc0,lc1=_window(poly,ltr,data['ndsm'].shape)
    if lr1<=lr0 or lc1<=lc0:return answer
    lt=ltr*Affine.translation(lc0,lr0)
    ndsm=data['ndsm'][lr0:lr1,lc0:lc1];counts=data['class6_count'][lr0:lr1,lc0:lc1]
    inside_lidar=_rasterize_polygon_mask(poly,ndsm.shape[0],ndsm.shape[1],lt)
    ri,ci=np.indices(ndsm.shape);x,y=lt*(ci+.5,ri+.5);ic,ir=(~itr)*(x,y)
    valid=(ic>=0)&(ir>=0)&(ic<image_rgb.shape[1])&(ir<image_rgb.shape[0])
    values=np.zeros((*ndsm.shape,3),dtype=float)
    values[valid]=image_rgb[np.floor(ir[valid]).astype(int),np.floor(ic[valid]).astype(int)]
    maximum=values.max(axis=2);sat=(maximum-values.min(axis=2))/np.maximum(maximum,1)
    red_cell=(values[...,0]-values[...,1]>25)&(values[...,0]-values[...,2]>15)
    roof_samples=ndsm[inside_lidar&valid&red_cell&(counts>0)&np.isfinite(ndsm)]
    height_limit=max(1.,float(np.median(roof_samples))-2.) if len(roof_samples)>=3 else 1.
    negative=inside_lidar&valid&(counts==0)&np.isfinite(ndsm)&(ndsm<=height_limit)&(sat<=.40)&(maximum>=50)&~red_cell
    labs,_=label(negative);pixel_area=abs(lt.a*lt.e-lt.b*lt.d);candidates=[]
    for index,sl in enumerate(find_objects(labs),1):
        if sl is None:continue
        component=labs[sl]==index;area=component.sum()*pixel_area
        if area<3:continue
        d=_compute_distance_transform_to_background(component)
        rr,cc=np.unravel_index(np.argmax(d),d.shape)
        rr+=sl[0].start;cc+=sl[1].start
        point=tuple(float(v) for v in lt*(cc+.5,rr+.5))
        candidates.append((-area,rr,cc,point))
    for _,_,_,point in sorted(candidates):
        if len(answer['negative_points'])>=max_negative_points:break
        if all(math.dist(point,p)>=3 for p in answer['negative_points']):answer['negative_points'].append(point)
    return answer
