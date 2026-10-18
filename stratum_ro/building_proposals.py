"""Separate observed class-6 objects from nDSM context without discarding either."""
import numpy as np
from scipy.ndimage import label, find_objects
from rasterio.features import shapes
from rasterio import Affine
from shapely.geometry import shape


def building_proposals(lidar_data, min_area_m2=8.):
    """Return class-6 and legacy proposals separately, never unioning their grids.

    Raw nDSM remains a fallback because glass roofs may have no class-6 returns.
    Exact duplicate cell masks are removed. No reference coordinates are used.
    """
    transform = lidar_data['transform']
    pixel_area = abs(transform.a*transform.e-transform.b*transform.d)
    class6 = lidar_data['class_evidence']['building'] > 0
    legacy = (lidar_data['main_buildings_grid'] > 0) | (lidar_data['outbuildings_grid'] > 0)
    if class6.shape != legacy.shape or not np.isfinite(min_area_m2) or min_area_m2 <= 0:
        raise ValueError('Matching evidence grids and positive minimum area required')
    proposals, seen = [], set()
    for source, grid in [('CLASS_6',class6),('NDSM_CONTEXT',legacy)]:
        labels, _ = label(grid)
        for ident, sl in enumerate(find_objects(labels),1):
            if sl is None:
                continue
            comp = labels[sl] == ident
            area = float(comp.sum())*pixel_area
            if area < min_area_m2:
                continue
            identity = (sl[0].start,sl[1].start,comp.shape,comp.tobytes())
            if identity in seen:
                continue
            seen.add(identity)
            tr = transform * Affine.translation(sl[1].start,sl[0].start)
            geometry = max((shape(g) for g,v in shapes(comp.astype('uint8'),mask=comp,transform=tr)
                            if v == 1),key=lambda g:g.area)
            proposals.append({'geometry':geometry, 'source':source, 'slice':sl,
                              'mask':comp, 'area_m2':area})
    return proposals
