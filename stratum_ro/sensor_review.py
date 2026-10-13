"""Reference-free review evidence. Flags preserve candidates; none imply approval.

LAS classifications are observations, not truth: glass roofs can be vegetation
classified. Thresholds below route work to review and never remove geometry.
"""
import hashlib
import numpy as np
from rasterio.features import rasterize
from rasterio.windows import Window, transform as window_transform


def build_class_evidence(x, y, classification, grid_shape, transform):
    """Count observed, class 6, and class 4/5 returns per raster cell."""
    x, y, classification = map(np.asarray, (x, y, classification))
    if x.ndim != 1 or x.shape != y.shape or x.shape != classification.shape:
        raise ValueError("Point arrays must be matching one-dimensional arrays")
    rows, cols = grid_shape
    if rows <= 0 or cols <= 0:
        raise ValueError("Grid must be nonempty")
    cf, rf = (~transform) * (x, y)
    valid = np.isfinite(cf) & np.isfinite(rf)
    valid &= (cf >= 0) & (cf < cols) & (rf >= 0) & (rf < rows)
    ci, ri = np.floor(cf[valid]).astype(int), np.floor(rf[valid]).astype(int)
    classes = classification[valid]
    flat = ri * cols + ci
    result = {}
    for name, keep in [('observed', np.ones(len(flat), dtype=bool)),
                       ('building', classes == 6),
                       ('vegetation', np.isin(classes, [4, 5]))]:
        result[name] = np.bincount(flat[keep], minlength=rows*cols).reshape(grid_shape)
    return result


def review_candidates(features, evidence, transform):
    """Copy and annotate every feature, using point fractions and shape ambiguity.

    Majority vegetation, absent building support, sparse observations, and a
    concave compound footprint are review reasons, never rejection criteria.
    Unflagged results remain NEVERIFICAT until a person reviews them.
    """
    arrays = [np.asarray(evidence[k]) for k in ('observed', 'building', 'vegetation')]
    if any(a.ndim != 2 or a.shape != arrays[0].shape for a in arrays):
        raise ValueError("Evidence grids must have matching 2D shapes")
    if any(np.any(a < 0) or not np.all(np.isfinite(a)) for a in arrays):
        raise ValueError("Evidence counts must be finite and nonnegative")
    if np.any(arrays[1] + arrays[2] > arrays[0]):
        raise ValueError("Class evidence cannot exceed observed returns")
    rows, cols = arrays[0].shape
    annotated = []
    for item in features:
        record = dict(item)
        geom = item.get('geometry')
        if geom is None or geom.is_empty or not geom.is_valid or geom.area <= 0:
            raise ValueError("Review requires a valid nonempty polygon")
        xmin, ymin, xmax, ymax = geom.bounds
        corners = [(~transform) * p for p in [(xmin,ymin),(xmin,ymax),(xmax,ymin),(xmax,ymax)]]
        c0 = max(0, int(np.floor(min(p[0] for p in corners))))
        c1 = min(cols, int(np.ceil(max(p[0] for p in corners))))
        r0 = max(0, int(np.floor(min(p[1] for p in corners))))
        r1 = min(rows, int(np.ceil(max(p[1] for p in corners))))
        totals = [0, 0, 0]
        cells = sampled = 0
        if r1 > r0 and c1 > c0:
            mask = rasterize([(geom, 1)], out_shape=(r1-r0,c1-c0),
                             transform=window_transform(Window(c0,r0,c1-c0,r1-r0), transform),
                             dtype='uint8').astype(bool)
            totals = [int(a[r0:r1,c0:c1][mask].sum()) for a in arrays]
            cells = int(mask.sum())
            sampled = int((arrays[0][r0:r1,c0:c1][mask] > 0).sum())
        observed, building, vegetation = totals
        bf = building / observed if observed else 0.
        vf = vegetation / observed if observed else 0.
        hull_ratio = geom.area / geom.convex_hull.area
        reasons = []
        if not observed or not cells or sampled / cells < .5:
            reasons.append('DATE_LIDAR_INSUFICIENTE')
        if not building:
            reasons.append('FARA_SUPORT_CLASA_6')
        if vf >= .5:
            reasons.append('VEGETATIE_DOMINANTA')
        if hull_ratio < .85:
            reasons.append('CORPURI_SAU_FORMA_CONCAVA')
        record.update(qa_id=hashlib.sha256(geom.normalize().wkb).hexdigest()[:20],
                      qa_status='NECESITA_VERIFICARE' if reasons else 'NEVERIFICAT',
                      qa_reasons=';'.join(reasons) or 'FARA_CONFLICT_EVIDENT',
                      qa_returns=observed, qa_building_fraction=round(bf,6),
                      qa_vegetation_fraction=round(vf,6), qa_hull_ratio=round(hull_ratio,6))
        annotated.append(record)
    return annotated
