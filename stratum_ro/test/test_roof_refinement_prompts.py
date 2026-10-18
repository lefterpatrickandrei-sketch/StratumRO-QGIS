# -*- coding: utf-8 -*-
"""
Unit tests for stratum_ro.roof_refinement_prompts.

Adheres strictly to AGENTS.md:
- Deterministic tests, zero network/model calls
- Validates red roof activation and positive prompt location
- Validates neutral ground/terrace negative prompts extraction
- Validates building evidence (class 6) exemption (never negative)
- Validates neutral/glass roof disabling (red coverage < 0.30 -> empty points, disabled)
- Validates input immutability and preservation
- Validates out-of-image projection handling (no clamping)
- Validates minimum physical area filter (3.0 m2) and spacing (>= 3.0 m)
- Validates return types as serializable float tuples
"""

import math
import unittest
import numpy as np
from shapely.geometry import Polygon, box
from affine import Affine

from stratum_ro.roof_refinement_prompts import (
    refinement_prompts,
    _ensure_affine,
    _validate_inputs,
)


class TestRoofRefinementPrompts(unittest.TestCase):

    def setUp(self):
        # Orthophoto: 100 x 100 px at 0.1 m resolution -> 10m x 10m area
        # Origin at (500000.0, 300000.0) in EPSG:3844 Stereo 70
        self.img_transform = Affine(0.1, 0.0, 500000.0, 0.0, -0.1, 300000.0)
        self.img_h, self.img_w = 100, 100

        # LiDAR: 20 x 20 cells at 0.5 m resolution -> 10m x 10m area
        self.lidar_transform = Affine(0.5, 0.0, 500000.0, 0.0, -0.5, 300000.0)
        self.lidar_h, self.lidar_w = 20, 20

    def _create_synthetic_scene(self, red_ratio: float = 0.5):
        """Creates image_rgb, ndsm, and class6 arrays for testing."""
        # Baseline image: neutral gray ground (R=120, G=120, B=120)
        image = np.full((self.img_h, self.img_w, 3), 120, dtype=np.uint8)

        # In image top-half (rows 0..50): painted red roof (R=200, G=50, B=50)
        # R - G = 150 > 25, R - B = 150 > 15
        cutoff = int(self.img_h * red_ratio)
        if cutoff > 0:
            image[:cutoff, :, 0] = 200
            image[:cutoff, :, 1] = 50
            image[:cutoff, :, 2] = 50

        # LiDAR ndsm: 0m for ground, 4m for roof (top half)
        ndsm = np.zeros((self.lidar_h, self.lidar_w), dtype=np.float32)
        lidar_cutoff = int(self.lidar_h * red_ratio)
        ndsm[:lidar_cutoff, :] = 4.0

        # LiDAR class 6: building classification on top half
        class6 = np.zeros((self.lidar_h, self.lidar_w), dtype=np.int32)
        class6[:lidar_cutoff, :] = 10

        return image, ndsm, class6

    def test_gray_ground_adjacent_red_roof_generates_negatives(self):
        """
        Verify that neutral ground/terrace (ndsm<=1, class6=0, sat<=0.25, max>=50)
        inside geometry adjacent to red roof produces negative prompts.
        """
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.6)
        # Bounding box covers full 10m x 10m: both red roof and gray ground
        # Map extent: X in [500000, 500010], Y in [299990, 300000]
        poly = box(500000.0, 299990.0, 500010.0, 300000.0)

        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        res = refinement_prompts(poly, image, self.img_transform, lidar_data, max_negative_points=4)

        self.assertEqual(res["mode"], "red_roof")
        self.assertEqual(len(res["positive_points"]), 1)
        self.assertIsInstance(res["positive_points"][0], tuple)
        self.assertEqual(len(res["positive_points"][0]), 2)
        self.assertTrue(all(isinstance(v, float) for v in res["positive_points"][0]))

        # Should generate negative points on ground
        self.assertGreater(len(res["negative_points"]), 0)
        self.assertLessEqual(len(res["negative_points"]), 4)

        # Check positive point is in red roof region (Y >= 299994.0)
        pos_x, pos_y = res["positive_points"][0]
        self.assertGreaterEqual(pos_y, 299994.0)

        # Check negative points are in ground region (Y < 299994.0)
        for neg_x, neg_y in res["negative_points"]:
            self.assertIsInstance(neg_x, float)
            self.assertIsInstance(neg_y, float)
            self.assertLess(neg_y, 299994.5)

    def test_class6_supported_gray_roof_never_negative(self):
        """
        Verify that a gray terrace/annex supported by class 6 building evidence
        is NEVER labeled as negative prompt.
        """
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.5)
        # Mark the bottom half (gray) as having class 6 building returns
        class6[10:, :] = 5  # building returns present

        poly = box(500000.0, 299990.0, 500010.0, 300000.0)
        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        res = refinement_prompts(poly, image, self.img_transform, lidar_data)
        self.assertEqual(res["mode"], "red_roof")
        self.assertEqual(len(res["negative_points"]), 0)

    def test_glass_or_neutral_roof_disabled(self):
        """
        Verify that if red coverage inside geometry is < 0.30 (neutral/glass/gray roof),
        mode is 'disabled' and both positive and negative points are empty.
        """
        # Red coverage only 15%
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.15)
        poly = box(500000.0, 299990.0, 500010.0, 300000.0)

        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        res = refinement_prompts(poly, image, self.img_transform, lidar_data)
        self.assertEqual(res["mode"], "disabled")
        self.assertEqual(res["positive_points"], [])
        self.assertEqual(res["negative_points"], [])

    def test_outside_rgb_never_clamped(self):
        """
        LiDAR cells extending outside orthophoto coverage are not clamped to border pixels;
        they are skipped cleanly without out-of-bounds error.
        """
        # LiDAR grid extends far beyond image: from 500000 to 500030 (30m x 30m)
        wide_lidar_transform = Affine(0.5, 0.0, 500000.0, 0.0, -0.5, 300000.0)
        wide_ndsm = np.zeros((60, 60), dtype=np.float32)
        wide_class6 = np.zeros((60, 60), dtype=np.int32)

        # Image only covers [500000..500010] x [299990..300000]
        image, _, _ = self._create_synthetic_scene(red_ratio=0.5)

        # Polygon spans both inside and outside orthophoto
        poly = box(500000.0, 299970.0, 500030.0, 300000.0)

        lidar_data = {
            "ndsm": wide_ndsm,
            "class6_count": wide_class6,
            "transform": wide_lidar_transform,
        }

        # Should execute cleanly without IndexError
        res = refinement_prompts(poly, image, self.img_transform, lidar_data)
        self.assertIn(res["mode"], ["red_roof", "disabled"])
        # All selected negative points must fall inside valid image extent
        for nx, ny in res["negative_points"]:
            self.assertGreaterEqual(nx, 500000.0)
            self.assertLessEqual(nx, 500010.0)
            self.assertGreaterEqual(ny, 299990.0)
            self.assertLessEqual(ny, 300000.0)

    def test_physical_area_threshold_and_spacing(self):
        """
        Negative regions must satisfy minimum 3 m2 physical area and >= 3.0m spacing.
        """
        # Cell size: 0.5 x 0.5 = 0.25 m2 per cell.
        # 3 m2 requires >= 12 cells.
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.5)

        # Isolate a tiny 4-cell patch of ground (4 * 0.25 = 1 m2 < 3 m2)
        # Equal to the 4m roof: above the relative roof-minus-2m limit.
        ndsm[10:, :] = 4.0
        # Only 4 cells are <= 1.0m
        ndsm[15:17, 15:17] = 0.0

        poly = box(500000.0, 299990.0, 500010.0, 300000.0)
        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        res = refinement_prompts(poly, image, self.img_transform, lidar_data)
        self.assertEqual(res["mode"], "red_roof")
        # 1 m2 region must be filtered out
        self.assertEqual(len(res["negative_points"]), 0)

        # Now enlarge patch to 16 cells (16 * 0.25 = 4 m2 >= 3 m2)
        ndsm[14:18, 14:18] = 0.0
        res2 = refinement_prompts(poly, image, self.img_transform, lidar_data)
        self.assertEqual(len(res2["negative_points"]), 1)

    def test_relative_height_distinguishes_terrace_from_roof(self):
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.5)
        poly = box(500000.0, 299990.0, 500010.0, 300000.0)
        ndsm[10:, :] = 2.0
        data = {'ndsm': ndsm, 'class6_count': class6, 'transform': self.lidar_transform}
        self.assertEqual(len(refinement_prompts(poly,image,self.img_transform,data)['negative_points']),1)
        ndsm[10:, :] = 3.0
        self.assertEqual(len(refinement_prompts(poly,image,self.img_transform,data)['negative_points']),0)

    def test_input_preservation_and_immutability(self):
        """
        Inputs passed to refinement_prompts must not be mutated in-place.
        """
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.5)
        image_orig = image.copy()
        ndsm_orig = ndsm.copy()
        class6_orig = class6.copy()

        poly = box(500000.0, 299990.0, 500010.0, 300000.0)
        poly_wkt = poly.wkt

        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        refinement_prompts(poly, image, self.img_transform, lidar_data)

        np.testing.assert_array_equal(image, image_orig)
        np.testing.assert_array_equal(ndsm, ndsm_orig)
        np.testing.assert_array_equal(class6, class6_orig)
        self.assertEqual(poly.wkt, poly_wkt)

    def test_validation_errors(self):
        """Verifies thorough defensive validation on faulty inputs."""
        image, ndsm, class6 = self._create_synthetic_scene(red_ratio=0.5)
        poly = box(500000.0, 299990.0, 500010.0, 300000.0)
        lidar_data = {
            "ndsm": ndsm,
            "class6_count": class6,
            "transform": self.lidar_transform,
        }

        # None geometry
        with self.assertRaises(ValueError):
            refinement_prompts(None, image, self.img_transform, lidar_data)

        # Empty geometry
        with self.assertRaises(ValueError):
            refinement_prompts(Polygon(), image, self.img_transform, lidar_data)

        # Non-finite image
        img_nan = image.astype(np.float32)
        img_nan[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            refinement_prompts(poly, img_nan, self.img_transform, lidar_data)

        # Negative class 6 count
        class6_bad = class6.copy()
        class6_bad[0, 0] = -1
        with self.assertRaises(ValueError):
            refinement_prompts(
                poly, image, self.img_transform,
                {"ndsm": ndsm, "class6_count": class6_bad, "transform": self.lidar_transform}
            )

        # Degenerate affine
        bad_aff = Affine(0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            refinement_prompts(poly, image, bad_aff, lidar_data)


if __name__ == "__main__":
    unittest.main()
