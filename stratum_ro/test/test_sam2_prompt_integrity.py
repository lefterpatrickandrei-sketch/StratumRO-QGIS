# -*- coding: utf-8 -*-
"""
Unit tests for SAM2 prompt integrity, point prompt routing, negative prompt filtering,
and robust polygon selection.
"""

import unittest
from unittest.mock import MagicMock
import numpy as np
import rasterio
from shapely.geometry import Point, Polygon

from stratum_ro.sam2_engine import SAM2BuildingSegmenter


class TestSAM2PromptIntegrity(unittest.TestCase):
    """
    Validates SAM 2 prompt routing, polygon selection with positive points,
    negative prompt handling, affine non-square pixel area calculation, and error modes.
    """

    def setUp(self):
        # Create an uninitialized segmenter instance without downloading or loading weights
        self.segmenter = SAM2BuildingSegmenter.__new__(SAM2BuildingSegmenter)
        self.segmenter.predictor = MagicMock()

        # Image size 100x100
        # Affine transform: origin (100.0, 200.0), non-square pixels: x_res = 0.5, y_res = -1.0
        # pixel_area = abs(0.5 * (-1.0) - 0.0 * 0.0) = 0.5 m^2
        self.tr = rasterio.Affine(0.5, 0.0, 100.0, 0.0, -1.0, 200.0)
        self.inv_tr = ~self.tr
        self.img_h, self.img_w = 100, 100

        self.segmenter.current_transform = self.tr
        self.segmenter.current_inv_transform = self.inv_tr
        self.segmenter.current_image_shape = (self.img_h, self.img_w)

    def test_mask_to_stereo70_polygon_largest_unprompted_vs_small_prompted(self):
        """
        When positive points are supplied, ensure the polygon containing the positive point
        is chosen even if another disconnected polygon in the mask has larger area.
        """
        # Create a mask with two disconnected components in pixel space:
        # Component 1 (small): r in [10, 20], c in [10, 20] -> 10x10 = 100 pixels (50 m^2)
        # Component 2 (large): r in [40, 80], c in [40, 80] -> 40x40 = 1600 pixels (800 m^2)
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[10:20, 10:20] = 1
        mask[40:80, 40:80] = 1

        # Point inside Component 1 in geographic coords:
        # pixel (c=15, r=15) -> tr * (15, 15)
        pos_pt_geo = self.tr * (15, 15)

        # 1. Without internal_pts_geo (backward compatibility fallback to largest)
        poly_largest = self.segmenter._mask_to_stereo70_polygon(
            mask, bx_min=0, by_min=0, bx_max=99, by_max=99,
            full_transform=self.tr,
            internal_pts_geo=None
        )
        self.assertIsNotNone(poly_largest)
        self.assertTrue(poly_largest.contains(Point(self.tr * (50, 50))))
        self.assertFalse(poly_largest.contains(Point(pos_pt_geo)))
        self.assertGreater(poly_largest.area, 500.0)

        # 2. With internal_pts_geo pointing to Component 1 (small prompted)
        poly_prompted = self.segmenter._mask_to_stereo70_polygon(
            mask, bx_min=0, by_min=0, bx_max=99, by_max=99,
            full_transform=self.tr,
            internal_pts_geo=[pos_pt_geo]
        )
        self.assertIsNotNone(poly_prompted)
        self.assertTrue(poly_prompted.contains(Point(pos_pt_geo)))
        self.assertFalse(poly_prompted.contains(Point(self.tr * (50, 50))))
        self.assertLess(poly_prompted.area, 100.0)

    def test_mask_to_stereo70_polygon_no_positive_polygon(self):
        """
        If valid positive points are supplied but none are covered by any polygon in the mask,
        return None rather than selecting another disconnected object.
        """
        mask = np.zeros((100, 100), dtype=np.uint8)
        mask[40:80, 40:80] = 1  # only large component present

        # Point in region r=15, c=15 (where mask is 0)
        uncovered_pt_geo = self.tr * (15, 15)

        poly = self.segmenter._mask_to_stereo70_polygon(
            mask, bx_min=0, by_min=0, bx_max=99, by_max=99,
            full_transform=self.tr,
            internal_pts_geo=[uncovered_pt_geo]
        )
        self.assertIsNone(poly)

    def test_segment_candidate_negatives_labels_and_out_of_image_filtering(self):
        """
        Validate that positive points get label 1 and negative points get label 0,
        out-of-image points are filtered, and valid in-image points are correctly passed
        to the predictor.
        """
        # Internal points: 1 in-image (c=10, r=10), 1 out-of-image (c=-50, r=-50)
        in_pos = self.tr * (10, 10)
        out_pos = self.tr * (-50, -50)

        # External points: 1 in-image (c=20, r=20), 1 out-of-image (c=150, r=150)
        in_neg = self.tr * (20, 20)
        out_neg = self.tr * (150, 150)

        # Candidate bounding box covering pixels 5 to 50
        b_p1 = self.tr * (5, 5)
        b_p2 = self.tr * (50, 50)
        b_xmin, b_xmax = min(b_p1[0], b_p2[0]), max(b_p1[0], b_p2[0])
        b_ymin, b_ymax = min(b_p1[1], b_p2[1]), max(b_p1[1], b_p2[1])

        # Mock predictor output
        dummy_mask = np.zeros((100, 100), dtype=bool)
        dummy_mask[8:15, 8:15] = True  # covers in_pos (10, 10) -> area ~ 49*0.5 = 24.5 m2
        self.segmenter.predictor.predict.return_value = (
            [dummy_mask],
            [0.85],
            None
        )

        res = self.segmenter.segment_candidate(
            b_xmin=b_xmin,
            b_ymin=b_ymin,
            b_xmax=b_xmax,
            b_ymax=b_ymax,
            mean_h=3.5,
            max_h=4.0,
            lidar_area=25.0,
            internal_pts_geo=[in_pos, out_pos],
            external_pts_geo=[in_neg, out_neg]
        )

        # Verify arguments passed to predictor.predict
        predict_args = self.segmenter.predictor.predict.call_args[1]
        coords = predict_args["point_coords"]
        labels = predict_args["point_labels"]

        # Only 2 points should be retained (the in-bounds ones)
        self.assertEqual(len(coords), 2)
        self.assertEqual(len(labels), 2)

        # First point should be positive (label 1), second negative (label 0)
        self.assertEqual(labels[0], 1)
        self.assertEqual(labels[1], 0)
        np.testing.assert_allclose(coords[0], [10.0, 10.0], atol=1e-3)
        np.testing.assert_allclose(coords[1], [20.0, 20.0], atol=1e-3)

        self.assertEqual(res["status"], "CONFIRMAT_HIBRID")
        self.assertIsNotNone(res["optical_poly"])
        self.assertTrue(res["optical_poly"].contains(Point(in_pos)))

    def test_segment_candidate_empty_or_undersized_masks_rejected(self):
        """
        When all candidate masks are under 5 m2 or non-finite,
        segment_candidate must return status 'RESPINS' with an explanatory reason,
        without crashing or arbitrarily picking masks[0].
        """
        b_p1 = self.tr * (5, 5)
        b_p2 = self.tr * (50, 50)
        b_xmin, b_xmax = min(b_p1[0], b_p2[0]), max(b_p1[0], b_p2[0])
        b_ymin, b_ymax = min(b_p1[1], b_p2[1]), max(b_p1[1], b_p2[1])

        # Under 5 m2: pixel_area = 0.5 m2, 4 pixels = 2.0 m2 (< 5.0)
        tiny_mask = np.zeros((100, 100), dtype=bool)
        tiny_mask[10:12, 10:12] = True

        self.segmenter.predictor.predict.return_value = (
            [tiny_mask, np.zeros((100, 100), dtype=bool)],
            [0.90, np.nan],
            None
        )

        res = self.segmenter.segment_candidate(
            b_xmin=b_xmin,
            b_ymin=b_ymin,
            b_xmax=b_xmax,
            b_ymax=b_ymax,
            mean_h=3.5,
            max_h=4.0,
            lidar_area=25.0
        )

        self.assertEqual(res["status"], "RESPINS")
        self.assertIn("Nicio mască validă", res["reason"])

    def test_high_score_unprompted_mask_does_not_hide_valid_alternative(self):
        wrong = np.zeros((100,100), dtype=bool)
        wrong[40:60,40:60] = True
        correct = np.zeros((100,100), dtype=bool)
        correct[10:20,10:20] = True
        self.segmenter.predictor.predict.return_value = ([wrong,correct],[.99,.8],None)
        positive = self.tr * (15,15)
        result = self.segmenter.segment_candidate(100,120,140,200,4,5,200,
                                                   internal_pts_geo=[positive])
        self.assertEqual(result['status'],'CONFIRMAT_HIBRID')
        self.assertTrue(result['geometry'].covers(Point(positive)))
        self.assertEqual(result['sam2_area_m2'],50.)

    def test_affine_non_square_pixel_area_calculation(self):
        """
        Ensures pixel area calculation uses abs(a*e - b*d) rather than a*a.
        """
        # Non-square, rotated affine matrix:
        # a=0.3, b=0.4, d=-0.4, e=0.3 -> det = (0.3*0.3 - 0.4*(-0.4)) = 0.09 + 0.16 = 0.25
        # If incorrectly computed as a*a = 0.09
        shear_tr = rasterio.Affine(0.3, 0.4, 50.0, -0.4, 0.3, 50.0)
        self.segmenter.current_transform = shear_tr
        self.segmenter.current_inv_transform = ~shear_tr

        b_xmin, b_ymin, b_xmax, b_ymax = 45.0, 45.0, 55.0, 55.0

        # Mask of 100 pixels:
        # with true det = 0.25, area = 25.0 m2
        mask = np.zeros((100, 100), dtype=bool)
        mask[10:20, 10:20] = True  # 100 pixels

        self.segmenter.predictor.predict.return_value = (
            [mask],
            [0.80],
            None
        )

        res = self.segmenter.segment_candidate(
            b_xmin=b_xmin,
            b_ymin=b_ymin,
            b_xmax=b_xmax,
            b_ymax=b_ymax,
            mean_h=3.5,
            max_h=4.0,
            lidar_area=25.0
        )

        self.assertEqual(res["sam2_area_m2"], 25.0)


if __name__ == "__main__":
    unittest.main()
