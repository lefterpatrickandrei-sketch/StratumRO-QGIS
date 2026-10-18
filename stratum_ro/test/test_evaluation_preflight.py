"""Selection errors must stop evaluation before inference, never inflate misses."""
import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from rasterio.transform import from_origin

from stratum_ro.evaluation_preflight import validate_selection, require_ready, EvaluationBlocked, sha256_file, checked_qgis_result


class TestEvaluationPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        Image.new('RGB', (32, 32), 'gray').save(self.root / 'selection.png')
        self.write_raster()
        self.manifest = {'schema_version': 2, 'crs': 'EPSG:3844', 'cases': [{
            'test_id': 'NEW1', 'tile': 'rgb.tif', 'search_center': [50, 50],
            'search_bbox': [30, 30, 70, 70], 'target_extent': [40, 40, 60, 60],
            'selection_review': {'object_kind': 'BUILDING', 'point_on_roof': True,
                'full_target_visible': True, 'reviewer': 'fixture',
                'observations': 'synthetic roof used only for unit test',
                'image': 'selection.png', 'image_sha256': sha256_file(self.root / 'selection.png')}
        }]}

    def write_raster(self, hole=False):
        data = np.full((3, 100, 100), 120, dtype='uint8')
        if hole:
            data[:, 50, 50] = 0
        with rasterio.open(self.root / 'rgb.tif', 'w', driver='GTiff', width=100,
                           height=100, count=3, dtype='uint8', crs='EPSG:3844',
                           transform=from_origin(0, 100, 1, 1), nodata=0) as dst:
            dst.write(data)

    def check(self, manifest=None):
        return validate_selection(manifest or self.manifest, manifest_dir=self.root, tile_dir=self.root)

    def test_reviewed_covered_selection_proceeds(self):
        require_ready(self.check())

    def test_legacy_random_windows_blocked(self):
        m = copy.deepcopy(self.manifest)
        del m['schema_version']
        del m['cases'][0]['selection_review']
        with self.assertRaises(EvaluationBlocked):
            require_ready(self.check(m))

    def test_grass_not_a_building_evaluation_case(self):
        self.manifest['cases'][0]['selection_review']['object_kind'] = 'OTHER_SURFACE'
        self.assertFalse(self.check()['ready'])

    def test_changed_evidence_requires_new_review(self):
        Image.new('RGB', (32, 32), 'red').save(self.root / 'selection.png')
        self.assertIn('changed selection image', str(self.check()['errors']))

    def test_window_must_include_whole_target(self):
        self.manifest['cases'][0]['target_extent'] = [40, 40, 90, 90]
        self.assertIn('truncates target', str(self.check()['errors']))

    def test_tile_must_include_padding(self):
        self.manifest['cases'][0]['search_bbox'] = [1, 1, 70, 70]
        self.assertIn('retry padding', str(self.check()['errors']))

    def test_nodata_is_input_failure_not_recall_failure(self):
        self.write_raster(hole=True)
        self.assertIn('NoData', str(self.check()['errors']))

    def test_unmasked_black_pixel_hole_is_rejected_even_when_nodata_is_none(self):
        data = np.full((3, 100, 100), 120, dtype='uint8')
        data[:, 45, 45] = 0
        with rasterio.open(self.root / 'rgb.tif', 'w', driver='GTiff', width=100,
                           height=100, count=3, dtype='uint8', crs='EPSG:3844',
                           transform=from_origin(0, 100, 1, 1), nodata=None) as dst:
            dst.write(data)
        self.assertIn('NoData', str(self.check()['errors']))

    def test_duplicate_ids_blocked(self):
        self.manifest['cases'].append(copy.deepcopy(self.manifest['cases'][0]))
        self.assertIn('duplicate', str(self.check()['errors']))

    def test_caught_qgis_error_cannot_be_reported_as_success(self):
        with self.assertRaises(EvaluationBlocked):
            checked_qgis_result({'status': 'success', 'result': {
                'stdout': 'PYQGIS_EXCEPTION: Traceback: failed'}}, 'PYQGIS_SUCCESS')

    def test_qgis_success_requires_complete_marker_and_no_stderr(self):
        checked_qgis_result({'status': 'success', 'result': {
            'stdout': 'Added layers\nPYQGIS_SUCCESS\n'}}, 'PYQGIS_SUCCESS')
        for result in ({'stdout': 'PYQGIS_SUCCESS', 'timed_out': True},
                       {'stdout': 'PYQGIS_SUCCESS', 'stderr': 'error'},
                       {'stdout': 'almost PYQGIS_SUCCESS'}):
            with self.assertRaises(EvaluationBlocked):
                checked_qgis_result({'status': 'success', 'result': result}, 'PYQGIS_SUCCESS')
