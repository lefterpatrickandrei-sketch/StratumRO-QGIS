"""Deterministic unit tests for stratum_ro.roof_retry.roof_retry_prompts.

Verifies local sensor seed hypothesis generation without reference contours,
remote parent prompts, or building approvals.
"""
import copy
import unittest
import numpy as np
from rasterio import Affine
from shapely.geometry import Polygon, Point, MultiPolygon, LineString

from stratum_ro.roof_retry import roof_retry_prompts


class TestRoofRetryPrompts(unittest.TestCase):
    def setUp(self):
        # Grid: 100x100 at 1.0m resolution (origin at 0, 100)
        # World coordinates: x in [0, 100], y in [0, 100]
        # Pixel (r, c) -> (c + 0.5, 100 - (r + 0.5))
        self.height = 100
        self.width = 100
        self.transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 100.0)

        # Child polygon inside image: [20, 40] x [60, 80]
        # In pixel space: c in [20, 40], r in [20, 40]
        self.child_geom = Polygon([(20.0, 60.0), (40.0, 60.0), (40.0, 80.0), (20.0, 80.0)])

        # Distant parent polygon far away: [500, 520] x [500, 520]
        self.distant_parent_geom = Polygon([(500.0, 500.0), (520.0, 500.0), (520.0, 520.0), (500.0, 520.0)])

        # Default flat ground arrays
        self.image_rgb = np.full((self.height, self.width, 3), 120, dtype=np.uint8)
        self.ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        self.building_class = np.zeros((self.height, self.width), dtype=np.float32)

    def _build_lidar_data(self, ndsm=None, building=None):
        return {
            'transform': self.transform,
            'ndsm': self.ndsm if ndsm is None else ndsm,
            'class_evidence': {
                'building': self.building_class if building is None else building,
            },
        }

    def test_seed_lies_inside_child_geometry_and_image_not_distant_parent(self):
        """Own seed lies strictly inside child geometry and image bounds, not distant parent."""
        # Elevated neutral roof patch inside child geometry: r 25:35, c 25:35 (area 100 m2 >= 8 m2)
        rgb = np.full((self.height, self.width, 3), 150, dtype=np.uint8)  # neutral
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 6.0  # height >= 2m
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[25:35, 25:35] = 1.0  # class 6 building support

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'SUPPORTED_LOCAL_SEED')
        self.assertGreater(len(res['seeds']), 0)
        for seed in res['seeds']:
            pt = Point(seed['point'])
            self.assertTrue(self.child_geom.covers(pt), "Seed point must lie inside child geometry")
            # Image bounds: x in [0, 100], y in [0, 100]
            self.assertTrue(0.0 <= pt.x <= 100.0 and 0.0 <= pt.y <= 100.0, "Seed point must lie within image bounds")
            self.assertFalse(self.distant_parent_geom.covers(pt), "Seed point must not be inside distant parent")

    def test_class6_supported_neutral_elevated_roof_produces_seed(self):
        """Class 6 supported neutral elevated roof produces a valid local seed."""
        # Neutral color: sat <= 0.30 and max >= 60 (e.g. RGB 140, 140, 140)
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[24:36, 24:36] = 5.5
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[24:36, 24:36] = 1.0

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'SUPPORTED_LOCAL_SEED')
        self.assertGreater(len(res['seeds']), 0)
        first_seed = res['seeds'][0]
        self.assertGreaterEqual(first_seed['area_m2'], 8.0)
        self.assertAlmostEqual(first_seed['mean_h'], 5.5, delta=0.1)

    def test_red_elevated_roof_supported_class6_produces_seed(self):
        """Class 6 supported red elevated roof produces a valid local seed."""
        # Red color: r - g > 20 and r - b > 15 (e.g. RGB 180, 70, 70)
        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        rgb[24:36, 24:36] = [180, 70, 70]
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[24:36, 24:36] = 4.8
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[24:36, 24:36] = 1.0

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'SUPPORTED_LOCAL_SEED')
        self.assertGreater(len(res['seeds']), 0)
        self.assertGreater(res['seeds'][0]['red_fraction'], 0.5)

    def test_vegetation_only_tall_patch_yields_no_supported_roof_seed(self):
        """Tall vegetation patch (trees) with or without class6 support is rejected."""
        # Vegetation color: sat > 0.25 and g >= 0.8*r and g > 1.12*b (e.g. RGB 50, 160, 40)
        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        rgb[24:36, 24:36] = [50, 160, 40]
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[24:36, 24:36] = 12.0  # tall canopy
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[24:36, 24:36] = 1.0  # even if misclassified as class 6

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'NO_SUPPORTED_ROOF_SEED')
        self.assertEqual(len(res['seeds']), 0)
        self.assertGreater(res['vegetation_fraction'], 0.0)

    def test_terrain_with_no_class6_yields_no_seed(self):
        """Ground / terrain with no class 6 support yields no seed."""
        # Neutral roof-like color and flat height, but zero building support (class 2 ground)
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        bld = np.zeros((self.height, self.width), dtype=np.float32)

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'NO_SUPPORTED_ROOF_SEED')
        self.assertEqual(len(res['seeds']), 0)

    def test_outside_image_yields_reason_outside_image(self):
        """Geometry fully outside the image bounds returns reason OUTSIDE_IMAGE."""
        outside_geom = Polygon([(200.0, 200.0), (220.0, 200.0), (220.0, 220.0), (200.0, 220.0)])
        lidar = self._build_lidar_data()
        res = roof_retry_prompts(outside_geom, self.image_rgb, self.transform, lidar, min_seed_area_m2=8.0)

        self.assertEqual(res['status'], 'NO_SUPPORTED_ROOF_SEED')
        self.assertEqual(res['reason'], 'OUTSIDE_IMAGE')
        self.assertEqual(len(res['seeds']), 0)

    def test_input_immutability(self):
        """Input numpy arrays and geometry are not mutated during function execution."""
        rgb = np.full((self.height, self.width, 3), 150, dtype=np.uint8)
        rgb_copy = rgb.copy()

        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 6.0
        ndsm_copy = ndsm.copy()

        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[25:35, 25:35] = 1.0
        bld_copy = bld.copy()

        geom_wkt_before = self.child_geom.wkt
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        _ = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)

        np.testing.assert_array_equal(rgb, rgb_copy, err_msg="Input RGB array must remain immutable")
        np.testing.assert_array_equal(ndsm, ndsm_copy, err_msg="Input nDSM array must remain immutable")
        np.testing.assert_array_equal(bld, bld_copy, err_msg="Input building array must remain immutable")
        self.assertEqual(self.child_geom.wkt, geom_wkt_before, "Input geometry must remain unchanged")

    def test_invalid_geometry_rejected(self):
        """Invalid, empty, non-Polygon, or None geometries raise ValueError."""
        lidar = self._build_lidar_data()

        # None
        with self.assertRaises(ValueError):
            roof_retry_prompts(None, self.image_rgb, self.transform, lidar)

        # Empty polygon
        with self.assertRaises(ValueError):
            roof_retry_prompts(Polygon(), self.image_rgb, self.transform, lidar)

        # Non-Polygon (e.g. LineString)
        line = LineString([(0.0, 0.0), (10.0, 10.0)])
        with self.assertRaises(ValueError):
            roof_retry_prompts(line, self.image_rgb, self.transform, lidar)

        # MultiPolygon
        p1 = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        p2 = Polygon([(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 3.0)])
        multi_poly = MultiPolygon([p1, p2])
        with self.assertRaises(ValueError):
            roof_retry_prompts(multi_poly, self.image_rgb, self.transform, lidar)

        # Self-intersecting / invalid polygon (bow-tie)
        bowtie = Polygon([(0.0, 0.0), (10.0, 10.0), (0.0, 10.0), (10.0, 0.0), (0.0, 0.0)])
        with self.assertRaises(ValueError):
            roof_retry_prompts(bowtie, self.image_rgb, self.transform, lidar)


if __name__ == '__main__':
    unittest.main()
