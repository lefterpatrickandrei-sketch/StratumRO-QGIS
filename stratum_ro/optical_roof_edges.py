"""Roof-edge hypotheses from RGB and relative LiDAR heights; no reference inputs."""
import numpy as np
from scipy.ndimage import binary_closing,binary_fill_holes,label
from rasterio.features import rasterize,shapes
from rasterio import Affine
from shapely.geometry import shape
from shapely import affinity


def refine_roof_color(geometry,image_rgb,transform,lidar_data):
    """Trim lower neutral surfaces from red roofs or trace teal glass roofs.

    Returns (polygon, method). Keeps original if data/coverage are insufficient.
    This is a development heuristic, never automatic cadastral approval.
    """
    if geometry is None or geometry.geom_type!='Polygon' or geometry.is_empty or not geometry.is_valid:
        raise ValueError('Valid nonempty Polygon required')
    if image_rgb.ndim!=3 or image_rgb.shape[2]!=3 or not all(image_rgb.shape[:2]):
        raise ValueError('Nonempty H x W x 3 RGB image required')
    if not np.isfinite(transform.determinant) or abs(transform.determinant)<1e-12:
        raise ValueError('Invertible image transform required')
    xmin,ymin,xmax,ymax=geometry.buffer(2).bounds
    corners=[(~transform)*(x,y) for x in (xmin,xmax) for y in (ymin,ymax)]
    c0=max(0,int(np.floor(min(p[0] for p in corners))));c1=min(image_rgb.shape[1],int(np.ceil(max(p[0] for p in corners))))
    r0=max(0,int(np.floor(min(p[1] for p in corners))));r1=min(image_rgb.shape[0],int(np.ceil(max(p[1] for p in corners))))
    if r1<=r0 or c1<=c0:return geometry,'NONE'
    rgb=image_rgb[r0:r1,c0:c1].astype(float);tr=transform*Affine.translation(c0,r0)
    def mask(g):return rasterize([(g,1)],out_shape=rgb.shape[:2],transform=tr,dtype='uint8').astype(bool)
    inside=mask(geometry);core=mask(affinity.scale(geometry,.4,.4,origin='centroid'))
    if not inside.any() or not core.any():return geometry,'NONE'
    r,g,b=rgb[...,0],rgb[...,1],rgb[...,2]
    red=(r-g>25)&(r-b>15)
    median=np.median(rgb[core],axis=0)
    method='NONE'
    if (inside&red).sum()/inside.sum()>=.30:
        ndsm=lidar_data['ndsm'];counts=lidar_data['class_evidence']['building'];lt=lidar_data['transform']
        ri,ci=np.indices(rgb.shape[:2]);x,y=tr*(ci+.5,ri+.5);lc,lr=(~lt)*(x,y)
        valid=(lc>=0)&(lr>=0)&(lc<ndsm.shape[1])&(lr<ndsm.shape[0])
        heights=np.zeros(rgb.shape[:2]);building=np.zeros(rgb.shape[:2])
        lr=np.floor(lr[valid]).astype(int);lc=np.floor(lc[valid]).astype(int)
        heights[valid]=ndsm[lr,lc];building[valid]=counts[lr,lc]
        samples=heights[core&red&valid&(building>0)&np.isfinite(heights)]
        if len(samples)<3:return geometry,'NONE'
        threshold=max(1.,float(np.median(samples))-2.)
        keep=red|((building>0)&(heights>=threshold))
        method='RED_ROOF_RELATIVE_HEIGHT'
    elif median[1]>1.04*median[0] and median[2]>1.02*median[0]:
        keep=(g>1.04*r)&(b>1.02*r)
        method='TEAL_ROOF_COLOR'
    else:return geometry,'NONE'
    foreground=mask(geometry.buffer(.6))&keep
    foreground=binary_fill_holes(binary_closing(foreground,structure=np.ones((3,3))))
    labs,_=label(foreground);counts=np.bincount(labs[core]);counts[0]=0
    if not counts.any():return geometry,'NONE'
    foreground=labs==int(np.argmax(counts))
    polygons=[shape(g) for g,v in shapes(foreground.astype('uint8'),mask=foreground,transform=tr) if v==1]
    if not polygons:return geometry,'NONE'
    result=max(polygons,key=lambda p:p.area).simplify(.25,preserve_topology=True)
    if not result.is_valid or not .60<=result.area/geometry.area<=1.25:return geometry,'NONE'
    return result,method
