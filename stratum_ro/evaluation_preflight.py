"""Fail-closed prerequisites for visual building evaluation, independent of agent.

Records attest to inspection; they do not replace it or prove cadastral truth.
Raster masks and image hashes are checked against actual files before inference.
"""
import hashlib
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
from shapely.geometry import Point, box


class EvaluationBlocked(ValueError):
    pass


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _bounds(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise EvaluationBlocked(f'{name}: four bounds required')
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in value):
        raise EvaluationBlocked(f'{name}: finite numeric bounds required')
    if value[0] >= value[2] or value[1] >= value[3]:
        raise EvaluationBlocked(f'{name}: empty or reversed bounds')
    return box(*value)


def validate_selection(manifest, *, manifest_dir, tile_dir):
    """Return all blockers; never label a rejected selection an extraction miss.

    target_extent is a loose search envelope, NOT a reference roof polygon.
    search_center must identify the roof itself, not a parcel centroid.
    """
    errors, checked = [], []
    if manifest.get('schema_version') != 2:
        errors.append('schema_version=2 required; legacy selection needs visual review')
    if manifest.get('crs') != 'EPSG:3844':
        errors.append('manifest crs must be EPSG:3844')
    cases = manifest.get('cases')
    if not isinstance(cases, list) or not cases:
        return {'ready': False, 'errors': errors + ['nonempty cases list required'], 'cases': []}
    seen = set()
    for case in cases:
        name = str(case.get('test_id', 'UNKNOWN'))
        reasons = []
        try:
            if name == 'UNKNOWN' or name in seen:
                raise EvaluationBlocked('missing or duplicate test_id')
            seen.add(name)
            search = _bounds(case.get('search_bbox'), 'search_bbox')
            target = _bounds(case.get('target_extent'), 'target_extent')
            if not search.covers(target):
                raise EvaluationBlocked('search window truncates target_extent')
            point = case.get('search_center')
            if not isinstance(point, (list, tuple)) or len(point) != 2 or not all(
                isinstance(v, (int, float)) and math.isfinite(v) for v in point
            ):
                raise EvaluationBlocked('finite roof search_center required')
            if not target.covers(Point(point)):
                raise EvaluationBlocked('roof point outside target_extent')
            review = case.get('selection_review', {})
            if review.get('object_kind') != 'BUILDING' or review.get('point_on_roof') is not True:
                raise EvaluationBlocked('building identity and roof point not visually confirmed')
            if review.get('full_target_visible') is not True:
                raise EvaluationBlocked('full target not visually inspected')
            if not str(review.get('reviewer', '')).strip() or not str(review.get('observations', '')).strip():
                raise EvaluationBlocked('reviewer and describe-first observations required')
            evidence = Path(review.get('image', ''))
            if not evidence.is_absolute():
                evidence = Path(manifest_dir) / evidence
            if not evidence.is_file() or sha256_file(evidence) != review.get('image_sha256'):
                raise EvaluationBlocked('missing or changed selection image; review again')
            from PIL import Image
            with Image.open(evidence) as image:
                image.verify()
            tile = Path(case.get('tile', ''))
            if not tile.is_absolute():
                tile = Path(tile_dir) / tile
            with rasterio.open(tile) as src:
                if src.crs is None or src.crs.to_epsg() != 3844 or src.count < 3:
                    raise EvaluationBlocked('RGB raster must have 3 bands and EPSG:3844')
                if src.transform.b or src.transform.d:
                    raise EvaluationBlocked('rotated raster must be warped before evaluation')
                x0, y0, x1, y1 = search.bounds
                px, py = max(4., (24. - (x1-x0))/2), max(4., (24. - (y1-y0))/2)
                required = box(x0-px, y0-py, x1+px, y1+py)
                if not box(*src.bounds).covers(required):
                    raise EvaluationBlocked('RGB does not cover search plus retry padding; use covering tile/mosaic')
                window = from_bounds(*required.bounds, src.transform)
                c0, r0 = math.floor(window.col_off), math.floor(window.row_off)
                c1, r1 = math.ceil(window.col_off+window.width), math.ceil(window.row_off+window.height)
                win = Window(c0, r0, c1-c0, r1-r0)
                mask = src.read_masks([1, 2, 3], window=win)
                rgb_win = src.read([1, 2, 3], window=win)
                if not np.all(mask > 0) or np.any(np.all(rgb_win == 0, axis=0)):
                    raise EvaluationBlocked('RGB search contains NoData; repair input coverage')
                row, col = src.index(*point)
                pt_win = Window(col, row, 1, 1)
                if not np.all(src.read_masks([1, 2, 3], window=pt_win) > 0) or np.all(src.read([1, 2, 3], window=pt_win) == 0):
                    raise EvaluationBlocked('roof point falls on NoData')
        except (ValueError, TypeError, OSError, rasterio.errors.RasterioError) as exc:
            reasons.append(str(exc))
        checked.append({'test_id': name, 'ready': not reasons, 'errors': reasons})
        errors.extend(f'{name}: {reason}' for reason in reasons)
    return {'ready': not errors, 'errors': errors, 'cases': checked}


def require_ready(report):
    if not report['ready']:
        raise EvaluationBlocked('SELECTION_BLOCKED:\n' + '\n'.join(report['errors']))


def checked_qgis_result(response, marker):
    """A caught PyQGIS exception is still failure, even in a successful RPC."""
    result = response.get('result', {})
    stdout = result.get('stdout', '')
    if (response.get('status') != 'success' or result.get('timed_out')
            or result.get('stderr') or 'Traceback' in stdout
            or 'PYQGIS_EXCEPTION' in stdout or marker not in stdout.splitlines()):
        raise EvaluationBlocked(f'QGIS integration not verified: {response}')
    return result
