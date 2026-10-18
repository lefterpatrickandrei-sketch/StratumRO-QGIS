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

    def _build_lidar_data(self, ndsm=None, building=None, observed=None, vegetation=None):
        return {
            'transform': self.transform,
            'ndsm': self.ndsm if ndsm is None else ndsm,
            'class_evidence': {
                'building': self.building_class if building is None else building,
                'observed': np.ones((self.height, self.width), dtype=np.float32) if observed is None else observed,
                'vegetation': np.zeros((self.height, self.width), dtype=np.float32) if vegetation is None else vegetation,
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

    def test_trim_retry_roof_surface_retains_previously_excluded_reddish_tile_and_rejects_vegetation(self):
        """trim_retry_roof_surface retains reddish tile under tree overhang (failing old brown/neutral/ceiling) while rejecting vegetation."""
        from stratum_ro.roof_retry import trim_retry_roof_surface
        # Tile where r=110, g=76, b=75, sat = (110 - 75)/110 = 0.318:
        # Check old brown: (110 > 1.08*76=82.08 TRUE), (76 > 1.04*75=78.0 FALSE!), (110 - 75 = 35 > 18 TRUE) -> old brown is FALSE!
        # Check old neutral: sat = 0.318 > 0.30 -> old neutral is FALSE!
        # Check old height ceiling: h=11.5 > local_h(6.5) + 4.0 = 10.5 -> old height ceiling is FALSE!
        # Check new reddish: (110 - 76 = 34 > 14 TRUE), (110 - 75 = 35 > 14 TRUE), (110 > 55 TRUE) -> reddish is TRUE!
        # Check new high_overhang: (red_fraction>=0.5) & reddish & ~vegetation -> high_overhang is TRUE!
        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Roof area: rows 20:40, cols 20:40
        rgb[20:40, 20:40] = [110, 76, 75]
        # Surrounding area has vegetation: rows 15:20, cols 20:40
        rgb[15:20, 20:40] = [40, 160, 30]

        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[20:40, 20:40] = 11.5  # tree canopy height overhanging roof
        ndsm[15:20, 20:40] = 11.5  # pure tree canopy height
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[20:40, 20:40] = 1.0   # building returns under canopy
        bld[15:20, 20:40] = 0.0   # no building return on surrounding vegetation
        veg = np.zeros((self.height, self.width), dtype=np.float32)
        veg[15:20, 20:40] = 1.0
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld, vegetation=veg)

        seed = {'point': (30.0, 70.0), 'red_fraction': 0.8, 'mean_h': 6.5, 'local_h': 6.5, 'max_h': 7.0}
        poly = Polygon([(20.0, 60.0), (40.0, 60.0), (40.0, 85.0), (20.0, 85.0)])
        trimmed, color_status = trim_retry_roof_surface(poly, rgb, self.transform, lidar, seed)
        self.assertEqual(color_status, 'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        # Vegetation at y > 80 (rows 15:20) must be excluded from trimmed result
        self.assertLessEqual(trimmed.bounds[3], 80.5, "Vegetation above y=80 must not be retained")
        self.assertGreater(trimmed.area, 100.0, "Reddish tile body under canopy must be retained")

    def test_retry_roof_geometry_production_path_preserves_supported_l_shape(self):
        """Production path retry_roof_geometry preserves true L-shape under mock segmenter."""
        from stratum_ro.roof_retry import retry_roof_geometry

        # Set up an L-shaped roof in sensor arrays
        # L-shape: box(20, 60, 40, 80) + box(40, 60, 50, 70)
        # World coords: x in [20, 50], y in [60, 80]
        rgb = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        rgb[20:40, 20:40] = [180, 70, 70]   # Red tile main body
        rgb[30:40, 40:50] = [180, 70, 70]   # Red tile wing
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[20:40, 20:40] = 5.0
        ndsm[30:40, 40:50] = 5.0
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[20:40, 20:40] = 1.0
        bld[30:40, 40:50] = 1.0
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        l_poly = Polygon([(20.0, 60.0), (50.0, 60.0), (50.0, 70.0), (40.0, 70.0), (40.0, 80.0), (20.0, 80.0)])

        class FakeSegmenter:
            def segment_candidate(self, *bounds, **kwargs):
                return {'geometry': l_poly, 'sam2_score': 0.88, 'status': 'CONFIRMAT_HIBRID'}

        result = retry_roof_geometry(l_poly, rgb, self.transform, lidar, FakeSegmenter())
        self.assertEqual(result['status'], 'RECTIFIED_HYPOTHESES_PENDING_REVIEW')
        self.assertGreaterEqual(len(result['candidates']), 1)
        # Verify L-shape (6 vertices) is preserved and not forced into a 4-vertex rectangle
        cand = result['candidates'][0]
        self.assertEqual(cand['vertices'], 6, "True L-shape must retain 6 vertices, never forced to rectangle")
        self.assertGreater(cand['simple_support'], 0.90)
 
    def test_neutral_elevated_roof_requires_class6_support(self):
        """Elevated neutral roof requires class 6 support to produce a seed, returning NO_SUPPORTED_ROOF_SEED otherwise."""
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)  # neutral
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 5.0  # height = 5.0m
        bld = np.zeros((self.height, self.width), dtype=np.float32)  # zero class 6 returns

        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)
        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)
        self.assertEqual(res['status'], 'NO_SUPPORTED_ROOF_SEED')
        self.assertEqual(len(res['seeds']), 0)

    def test_trim_retry_roof_surface_excludes_neutral_flat_pavement(self):
        """trim_retry_roof_surface excludes neutral ground pavement (h < 2.0m, counts=0)."""
        from stratum_ro.roof_retry import trim_retry_roof_surface
        # Roof is at rows 20:30, cols 20:40 (h=5m, neutral gray 140)
        # Pavement is at rows 30:40, cols 20:40 (h=0.5m, neutral gray 140)
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[20:30, 20:40] = 5.0  # roof
        ndsm[30:40, 20:40] = 0.5  # ground pavement / courtyard
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        seed = {'point': (30.0, 75.0), 'red_fraction': 0.0, 'mean_h': 5.0, 'local_h': 5.0, 'max_h': 5.5, 'area_m2': 200.0}
        # Polygon covers both roof and pavement:
        poly = Polygon([(20.0, 60.0), (40.0, 60.0), (40.0, 80.0), (20.0, 80.0)])
        trimmed, color_status = trim_retry_roof_surface(poly, rgb, self.transform, lidar, seed)

        self.assertEqual(color_status, 'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        # Pavement below row 30 (which corresponds to y < 70 in Stereo 70) must be excluded:
        self.assertGreaterEqual(trimmed.bounds[1], 69.5, "Flat pavement below y=70 must be trimmed out")

    def test_retry_roof_geometry_passes_seed_area_to_segmenter(self):
        """retry_roof_geometry passes seed area to segment_candidate instead of search bbox area."""
        from stratum_ro.roof_retry import retry_roof_geometry
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 4.5
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[25:35, 25:35] = 1.0
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        large_search = Polygon([(10.0, 50.0), (50.0, 50.0), (50.0, 90.0), (10.0, 90.0)])  # 1600 m2
        captured_kwargs = {}

        class AreaSpySegmenter:
            def segment_candidate(self, *bounds, **kwargs):
                captured_kwargs.update(kwargs)
                return {'geometry': self.child_geom, 'sam2_score': 0.85, 'status': 'CONFIRMAT_HIBRID'}

            child_geom = Polygon([(25.0, 65.0), (35.0, 65.0), (35.0, 75.0), (25.0, 75.0)])

        result = retry_roof_geometry(large_search, rgb, self.transform, lidar, AreaSpySegmenter())
        self.assertIn('lidar_area', captured_kwargs)
        # Should be seed area (~100 m2), NOT search box area (1600 m2)
        self.assertLess(captured_kwargs['lidar_area'], 300.0)
        self.assertGreater(captured_kwargs['lidar_area'], 50.0)

    def test_retry_roof_geometry_passes_seed_bounds_not_parcel_bounds(self):
        """retry_roof_geometry passes locally padded seed bounds to segment_candidate instead of full parcel bounds."""
        from stratum_ro.roof_retry import retry_roof_geometry
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 4.5
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[25:35, 25:35] = 1.0
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        large_search = Polygon([(10.0, 50.0), (60.0, 50.0), (60.0, 95.0), (10.0, 95.0)])
        captured_bounds = []

        class BoundsSpySegmenter:
            def segment_candidate(self, *bounds, **kwargs):
                captured_bounds.append(bounds)
                return {
                    'geometry': Polygon([(25.0, 65.0), (35.0, 65.0), (35.0, 75.0), (25.0, 75.0)]),
                    'sam2_score': 0.90,
                    'status': 'CONFIRMAT_HIBRID',
                }

        retry_roof_geometry(large_search, rgb, self.transform, lidar, BoundsSpySegmenter())
        self.assertEqual(len(captured_bounds), 1)
        bx0, by0, bx1, by1 = captured_bounds[0]
        self.assertLess(bx1 - bx0, 20.0, "Seed bbox width must be local to the seed (~13m), not parcel width (50m)")
        self.assertLess(by1 - by0, 20.0, "Seed bbox height must be local to the seed (~13m), not parcel height (45m)")

    def test_elevated_cool_glass_roof_without_class6_produces_fallback_seed(self):
        """Elevated non-vegetation cool glass/metal roof without Class 6 produces fallback seed."""
        rgb = np.full((self.height, self.width, 3), 120, dtype=np.uint8)
        rgb[25:35, 25:35] = [145, 152, 160]  # cool glass/metal (b - r >= 3, g >= r - 2)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[25:35, 25:35] = 3.2
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        res = roof_retry_prompts(self.child_geom, rgb, self.transform, lidar, min_seed_area_m2=8.0)
        self.assertEqual(res['status'], 'SUPPORTED_LOCAL_SEED')
        self.assertEqual(len(res['seeds']), 1)
        self.assertTrue(res['seeds'][0].get('unclassified_lidar'))

    def test_trim_retry_roof_surface_removes_elevated_skylight_hole(self):
        """Elevated skylight/fixture spectral gap on roof does not create a false courtyard hole."""
        from stratum_ro.roof_retry import trim_retry_roof_surface
        rgb = np.full((self.height, self.width, 3), 140, dtype=np.uint8)
        rgb[28:32, 28:32] = [30, 80, 150]  # non-neutral skylight spectral anomaly (4x4 = 16 m2)
        ndsm = np.zeros((self.height, self.width), dtype=np.float32)
        ndsm[20:40, 20:40] = 6.0  # elevated everywhere including skylight
        bld = np.zeros((self.height, self.width), dtype=np.float32)
        bld[20:40, 20:40] = 1.0
        lidar = self._build_lidar_data(ndsm=ndsm, building=bld)

        seed = {'point': (23.0, 77.0), 'red_fraction': 0.0, 'mean_h': 6.0, 'local_h': 6.0, 'max_h': 6.5}
        poly = Polygon([(20.0, 60.0), (40.0, 60.0), (40.0, 80.0), (20.0, 80.0)])
        trimmed, status = trim_retry_roof_surface(poly, rgb, self.transform, lidar, seed)
        self.assertEqual(status, 'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        self.assertEqual(len(trimmed.interiors), 0, "Elevated skylight must not be preserved as a ground courtyard hole")


if __name__ == '__main__':
    unittest.main()

