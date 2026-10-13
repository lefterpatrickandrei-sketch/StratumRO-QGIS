import math
import unittest
import numpy as np
from rasterio import Affine
from shapely import affinity
from shapely.geometry import box, Polygon
from stratum_ro.roof_body_partition import split_color_roof_bodies


class RoofBodyPartitionTests(unittest.TestCase):
    def setUp(self):
        # 100x100 pixels, resolution 0.1m/px, origin (0, 10) so row 0 is y=10, row 100 is y=0
        # transform: x = col * 0.1, y = 10.0 - row * 0.1
        self.res = 0.1
        self.transform = Affine(self.res, 0.0, 0.0, 0.0, -self.res, 10.0)

    def test_compound_roof_splits_into_two_valid_parts(self):
        # 10x10m geometry box(0, 0, 10, 10) -> area 100 m2
        # Top-half y in [5, 10] -> rows 0 to 50: pure red [180, 50, 50]
        # Bottom-half y in [0, 5] -> rows 50 to 100: neutral gray [120, 120, 120]
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:50, :] = [180, 50, 50]
        img[50:, :] = [120, 120, 120]

        geom = box(0.0, 0.0, 10.0, 10.0)
        parts = split_color_roof_bodies(geom, img, self.transform, min_area_m2=20.0)

        self.assertEqual(len(parts), 2)
        for part in parts:
            self.assertEqual(part['split_status'], 'PARTITION_REVIEW_REQUIRED')
            self.assertTrue(part['geometry'].is_valid)
            self.assertEqual(part['geometry'].geom_type, 'Polygon')
            self.assertGreaterEqual(part['geometry'].area, 20.0)
            self.assertIn(part['body_source'], ('SPECTRAL_SEAM_BODY_1', 'SPECTRAL_SEAM_BODY_2'))
            self.assertGreaterEqual(part['seam_accuracy'], 0.90)

        # Non-overlapping
        overlap_area = parts[0]['geometry'].intersection(parts[1]['geometry']).area
        self.assertLessEqual(overlap_area, 1e-6)

        # Retains most area (>= 90% of parent area)
        combined_area = parts[0]['geometry'].area + parts[1]['geometry'].area
        self.assertGreaterEqual(combined_area, 0.90 * geom.area)

    def test_uniform_red_roof_remains_unchanged(self):
        img = np.full((100, 100, 3), [180, 50, 50], dtype=np.uint8)
        geom = box(0.0, 0.0, 10.0, 10.0)

        parts = split_color_roof_bodies(geom, img, self.transform, min_area_m2=20.0)

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]['body_source'], 'PARENT_UNSPLIT')
        self.assertEqual(parts[0]['split_status'], 'NO_SUPPORTED_SEAM')
        self.assertTrue(parts[0]['geometry'].equals(geom))

    def test_tiny_skylight_minority_patch_remains_unchanged(self):
        # Mostly neutral gray roof [120, 120, 120] with a tiny red skylight patch (e.g. 5x5 pixels = 0.5x0.5m)
        img = np.full((100, 100, 3), [120, 120, 120], dtype=np.uint8)
        img[45:50, 45:50] = [180, 50, 50]
        geom = box(0.0, 0.0, 10.0, 10.0)

        parts = split_color_roof_bodies(geom, img, self.transform, min_area_m2=20.0)

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]['body_source'], 'PARENT_UNSPLIT')
        self.assertEqual(parts[0]['split_status'], 'NO_SUPPORTED_SEAM')
        self.assertTrue(parts[0]['geometry'].equals(geom))

    def test_out_of_image_geometry_remains_unchanged(self):
        img = np.full((100, 100, 3), [120, 120, 120], dtype=np.uint8)
        # Geometry entirely outside the image raster extent (x in [50, 60], y in [50, 60])
        geom = box(50.0, 50.0, 60.0, 60.0)

        parts = split_color_roof_bodies(geom, img, self.transform, min_area_m2=20.0)

        self.assertEqual(len(parts), 1)
        self.assertEqual(parts[0]['body_source'], 'PARENT_UNSPLIT')
        self.assertEqual(parts[0]['split_status'], 'NO_SUPPORTED_SEAM')
        self.assertTrue(parts[0]['geometry'].equals(geom))

    def test_rotated_compound_roof_splits_cleanly(self):
        # A compound roof rotated by 30 degrees around origin
        # Coordinate bounds and raster set up with an affine transform matching the rotated scene
        # Construct an image and affine transform covering a 20x20m bounding area
        transform = Affine(0.1, 0.0, -5.0, 0.0, -0.1, 15.0)
        img = np.zeros((200, 200, 3), dtype=np.uint8)

        # Geometry: 10x10m box rotated by 30 degrees
        unrotated_geom = box(0.0, 0.0, 10.0, 10.0)
        rotated_geom = affinity.rotate(unrotated_geom, 30.0, origin=(5.0, 5.0))

        # Color the raster based on unrotated coordinate along the seam axis
        # For each pixel center (x, y), transform back by rotating -30 deg around (5, 5)
        # and assign red if y_unrot >= 5.0 else gray
        cols, rows = np.meshgrid(np.arange(200), np.arange(200))
        xs, ys = transform * (cols + 0.5, rows + 0.5)
        rad = math.radians(-30.0)
        dx = xs - 5.0
        dy = ys - 5.0
        y_unrot = dx * math.sin(rad) + dy * math.cos(rad) + 5.0

        is_red = y_unrot >= 5.0
        img[is_red] = [180, 50, 50]
        img[~is_red] = [120, 120, 120]

        parts = split_color_roof_bodies(rotated_geom, img, transform, min_area_m2=20.0)

        self.assertEqual(len(parts), 2)
        for part in parts:
            self.assertEqual(part['split_status'], 'PARTITION_REVIEW_REQUIRED')
            self.assertTrue(part['geometry'].is_valid)
            self.assertEqual(part['geometry'].geom_type, 'Polygon')
            self.assertGreaterEqual(part['geometry'].area, 20.0)

        overlap_area = parts[0]['geometry'].intersection(parts[1]['geometry']).area
        self.assertLessEqual(overlap_area, 1e-6)

        combined_area = parts[0]['geometry'].area + parts[1]['geometry'].area
        self.assertGreaterEqual(combined_area, 0.90 * rotated_geom.area)

    def test_input_immutability(self):
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:50, :] = [180, 50, 50]
        img[50:, :] = [120, 120, 120]
        img_copy = img.copy()

        geom = box(0.0, 0.0, 10.0, 10.0)
        geom_wkb = geom.wkb

        parts = split_color_roof_bodies(geom, img, self.transform, min_area_m2=20.0)

        self.assertEqual(geom.wkb, geom_wkb)
        np.testing.assert_array_equal(img, img_copy)

    def test_invalid_geometry_raises_value_error(self):
        img = np.full((100, 100, 3), [120, 120, 120], dtype=np.uint8)

        # None geometry
        with self.assertRaises(ValueError):
            split_color_roof_bodies(None, img, self.transform)

        # Empty polygon
        with self.assertRaises(ValueError):
            split_color_roof_bodies(Polygon(), img, self.transform)

        # Self-intersecting / invalid polygon
        bowtie = Polygon([(0, 0), (10, 10), (0, 10), (10, 0), (0, 0)])
        with self.assertRaises(ValueError):
            split_color_roof_bodies(bowtie, img, self.transform)

        # Non-polygon geometry (e.g. LineString)
        from shapely.geometry import LineString
        with self.assertRaises(ValueError):
            split_color_roof_bodies(LineString([(0, 0), (10, 10)]), img, self.transform)

        # Invalid image dimensions or invalid minimum area
        valid_geom = box(0, 0, 10, 10)
        with self.assertRaises(ValueError):
            split_color_roof_bodies(valid_geom, np.zeros((100, 100)), self.transform)
        with self.assertRaises(ValueError):
            split_color_roof_bodies(valid_geom, img, self.transform, min_area_m2=0.0)


if __name__ == '__main__':
    unittest.main()
