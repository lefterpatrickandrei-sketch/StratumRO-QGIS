"""Remove small roof-outline spurs using occupied raster profiles, not references."""
import math
import numpy as np
from shapely import affinity
from shapely.geometry import box
from rasterio.features import rasterize
from rasterio.transform import from_origin


def rectangle_core(geometry, optical_mask):
    """Return a supported rectangle or the original geometry unchanged.

    At least80% IoU with the existing candidate and90% optical support are
    required. This proposes a geometric repair; it does not identify buildings.
    """
    if geometry is None or geometry.is_empty or not geometry.is_valid:
        raise ValueError('Valid nonempty geometry required')
    if geometry.geom_type != 'Polygon' or geometry.area<=0:return geometry
    if geometry.area/geometry.minimum_rotated_rectangle.area>=.90:return geometry
    coords=np.asarray(geometry.exterior.coords)
    edges=np.diff(coords,axis=0);lengths=np.linalg.norm(edges,axis=1)
    v=edges[int(np.argmax(lengths))]
    angle=math.degrees(math.atan2(v[1],v[0]))
    origin=geometry.centroid.coords[0]
    aligned=affinity.rotate(geometry,-angle,origin=origin)
    xmin,ymin,xmax,ymax=aligned.bounds
    step=max(.20,math.sqrt((xmax-xmin)*(ymax-ymin)/100000))
    width=max(1,int(math.ceil((xmax-xmin)/step)))
    height=max(1,int(math.ceil((ymax-ymin)/step)))
    mask=rasterize([(aligned,1)],out_shape=(height,width),
                   transform=from_origin(xmin,ymax,step,step),dtype='uint8')
    rows=mask.sum(axis=1);cols=mask.sum(axis=0)
    if not rows.any() or not cols.any():return geometry
    rr=np.flatnonzero(rows>=.5*rows.max());cc=np.flatnonzero(cols>=.5*cols.max())
    core=box(xmin+cc[0]*step,ymax-(rr[-1]+1)*step,
             xmin+(cc[-1]+1)*step,ymax-rr[0]*step)
    core=affinity.rotate(core,angle,origin=origin)
    overlap=core.intersection(geometry).area
    iou=overlap/core.union(geometry).area
    support=core.intersection(optical_mask).area/core.area
    if iou>=.80 and support>=.90:return core
    return geometry
