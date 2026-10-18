"""Final valid-pixel boundary guard for regional review geometries."""
import math
import numpy as np
from rasterio.features import shapes
from shapely.geometry import shape
from shapely.ops import unary_union


def clip_to_valid_mosaic(geometry,mosaic,resolution=.15):
    """Intersect with actual valid-pixel footprints, never a blackness threshold."""
    a,b,c,d=geometry.bounds;x0,_,_,y0=mosaic.bounds
    # Same grid phase as the regional planner, so this is not a shifted-mask fit.
    bounds=(x0+math.floor((a-x0)/resolution)*resolution-resolution,
        y0+math.floor((b-y0)/resolution)*resolution-resolution,
        x0+math.ceil((c-x0)/resolution)*resolution+resolution,
        y0+math.ceil((d-y0)/resolution)*resolution+resolution)
    _,valid,tr,_=mosaic.read(bounds,resolution)
    if valid.all():return geometry,0.
    footprints=[shape(g) for g,v in shapes(valid.astype('uint8'),mask=valid,transform=tr) if v]
    result=geometry.intersection(unary_union(footprints))
    # An intersection may include boundary-only line contacts. Preserve all
    # polygon parts, not a GeometryCollection masquerading as a roof surface.
    def polygons(g):
        if g.geom_type=='Polygon':return [g]
        if hasattr(g,'geoms'):return [p for item in g.geoms for p in polygons(item)]
        return []
    result=unary_union(polygons(result))
    return result,float(geometry.difference(result).area)
