"""Tests for stratum_ro.roof_body_proposals.

Covers:
- Synthetic touching red/neutral roofs split cleanly into distinct components.
- Pixels outside RGB image bounds are excluded (never edge-clamped as evidence).
- LiDAR data with no class 6 building returns yields no proposals.
- Physical area calculations on non-square cells (different x/y resolution or shear).
- Positive point location is inside the geometry.
- Invalid arguments validation (shapes, transforms, ranges, counts).
- Input arrays and dicts are strictly preserved without mutation.
"""
import unittest
import numpy as np
import rasterio.transform
from shapely.geometry import Point

from stratum_ro.roof_body_proposals import color_body_proposals


class TestRoofBodyProposals(unittest.TestCase):

    def setUp(self):
        # Default 20x20 LiDAR grid with 1.0m resolution
        self.lidar_transform = rasterio.transform.from_origin(100.0, 200.0, 1.0, 1.0)
        self.image_transform = rasterio.transform.from_origin(100.0, 200.0, 1.0, 1.0)

    def test_synthetic_touching_red_neutral_roofs_split(self):
        """Adjacent neutral and red roofs with class 6 evidence split into distinct proposals."""
        rows, cols = 10, 10
        building = np.ones((rows, cols), dtype=np.int32)
        lidar_data = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": building},
        }

        # Left half neutral (e.g. 100, 100, 100 -> saturation = 0 <= 0.25)
        # Right half red (e.g. 180, 50, 50 -> R-G=130>25, R-B=130>15)
        image = np.zeros((rows, cols, 3), dtype=np.uint8)
        image[:, :5] = [100, 100, 100]
        image[:, 5:] = [180, 50, 50]

        proposals = color_body_proposals(
            lidar_data,
            image,
            self.image_transform,
            min_area_m2=20.0,
        )

        sources = [p["source"] for p in proposals]
        self.assertEqual(len(proposals), 2)
        self.assertIn("COLOR_NEUTRAL", sources)
        self.assertIn("COLOR_RED", sources)

        neutral_prop = next(p for p in proposals if p["source"] == "COLOR_NEUTRAL")
        red_prop = next(p for p in proposals if p["source"] == "COLOR_RED")

        # Each half is 5x10 = 50 m^2
        self.assertAlmostEqual(neutral_prop["area_m2"], 50.0)
        self.assertAlmostEqual(red_prop["area_m2"], 50.0)

        # Check positive point is inside each respective geometry
        self.assertTrue(neutral_prop["geometry"].contains(neutral_prop["positive_point_geo"]))
        self.assertTrue(red_prop["geometry"].contains(red_prop["positive_point_geo"]))

    def test_rgb_outside_excluded_no_edge_clamp(self):
        """LiDAR cells outside image bounds are never sampled or clamped as evidence."""
        # LiDAR covers [100, 120] in X, but image only covers [100, 105]
        # (Image is 5x20, LiDAR is 20x20)
        lidar_rows, lidar_cols = 20, 20
        building = np.ones((lidar_rows, lidar_cols), dtype=np.int32)
        lidar_data = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": building},
        }

        # Small image of 20 rows, 5 cols
        img_rows, img_cols = 20, 5
        image = np.full((img_rows, img_cols, 3), 100, dtype=np.uint8)  # Neutral

        proposals = color_body_proposals(
            lidar_data,
            image,
            self.image_transform,
            min_area_m2=20.0,
        )

        self.assertEqual(len(proposals), 1)
        prop = proposals[0]
        # Only the 5 columns inside image have proposals (20 x 5 = 100 m^2)
        self.assertAlmostEqual(prop["area_m2"], 100.0)
        self.assertFalse(np.any(prop["mask"][:, 5:]))

    def test_no_class6_yields_none(self):
        """No class 6 building returns (all zero) yields empty proposals."""
        rows, cols = 10, 10
        building = np.zeros((rows, cols), dtype=np.int32)
        lidar_data = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": building},
        }
        image = np.full((rows, cols, 3), 100, dtype=np.uint8)

        proposals = color_body_proposals(
            lidar_data,
            image,
            self.image_transform,
            min_area_m2=10.0,
        )
        self.assertEqual(len(proposals), 0)

    def test_physical_area_non_square(self):
        """Physical area correctly incorporates non-square cell resolutions via affine determinant."""
        # dx = 0.5m, dy = -2.0m -> cell area = 0.5 * 2.0 = 1.0 m^2
        transform_rect = rasterio.transform.from_origin(100.0, 200.0, 0.5, 2.0)
        rows, cols = 10, 10
        building = np.zeros((rows, cols), dtype=np.int32)
        # 6x6 component = 36 cells -> area = 36.0 m^2
        building[2:8, 2:8] = 5

        lidar_data = {
            "transform": transform_rect,
            "class_evidence": {"building": building},
        }
        image = np.full((rows, cols, 3), 120, dtype=np.uint8)

        proposals = color_body_proposals(
            lidar_data,
            image,
            transform_rect,
            min_area_m2=20.0,
        )

        self.assertEqual(len(proposals), 1)
        self.assertAlmostEqual(proposals[0]["area_m2"], 36.0)

        # Another case: dx = 2.0, dy = 3.0 -> cell area = 6.0 m^2
        transform_large = rasterio.transform.from_origin(100.0, 200.0, 2.0, 3.0)
        lidar_data_large = {
            "transform": transform_large,
            "class_evidence": {"building": building},
        }
        proposals_large = color_body_proposals(
            lidar_data_large,
            image,
            transform_large,
            min_area_m2=50.0,
        )
        self.assertEqual(len(proposals_large), 1)
        self.assertAlmostEqual(proposals_large[0]["area_m2"], 36 * 6.0)

    def test_positive_point_inside_geometry(self):
        """Positive prompt point must strictly reside inside the proposed geometry."""
        rows, cols = 15, 15
        building = np.zeros((rows, cols), dtype=np.int32)
        # Create an L-shaped neutral component
        building[2:10, 2:5] = 2
        building[7:10, 2:10] = 2

        lidar_data = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": building},
        }
        image = np.full((rows, cols, 3), 100, dtype=np.uint8)

        proposals = color_body_proposals(
            lidar_data,
            image,
            self.image_transform,
            min_area_m2=15.0,
        )

        self.assertEqual(len(proposals), 1)
        prop = proposals[0]
        self.assertIsInstance(prop["positive_point_geo"], Point)
        self.assertTrue(prop["geometry"].contains(prop["positive_point_geo"]))

    def test_invalid_args_validation(self):
        """Validates error checking on shapes, transforms, channel counts, values, and bounds."""
        valid_b = np.ones((5, 5), dtype=np.int32)
        valid_lidar = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": valid_b},
        }
        valid_img = np.zeros((5, 5, 3), dtype=np.uint8)

        # Non-dict lidar_data
        with self.assertRaises(ValueError):
            color_body_proposals("invalid", valid_img, self.image_transform)

        # Missing class_evidence
        with self.assertRaises(ValueError):
            color_body_proposals({"transform": self.lidar_transform}, valid_img, self.image_transform)

        # Singular lidar transform
        singular_tf = rasterio.transform.Affine(0, 0, 0, 0, 0, 0)
        with self.assertRaises(ValueError):
            color_body_proposals(
                {"transform": singular_tf, "class_evidence": {"building": valid_b}},
                valid_img,
                self.image_transform,
            )

        # Negative building counts
        with self.assertRaises(ValueError):
            color_body_proposals(
                {"transform": self.lidar_transform, "class_evidence": {"building": -np.ones((5, 5))}},
                valid_img,
                self.image_transform,
            )

        # Non-2D building array
        with self.assertRaises(ValueError):
            color_body_proposals(
                {"transform": self.lidar_transform, "class_evidence": {"building": np.ones((5,))}},
                valid_img,
                self.image_transform,
            )

        # Invalid min_area_m2
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, valid_img, self.image_transform, min_area_m2=0.0)
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, valid_img, self.image_transform, min_area_m2=-5.0)

        # Invalid image channel count (2 channels)
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, np.zeros((5, 5, 2), dtype=np.uint8), self.image_transform)

        # Image out of 0..255 range
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, np.full((5, 5, 3), 300.0), self.image_transform)
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, np.full((5, 5, 3), -10.0), self.image_transform)

        # Image containing NaN/inf
        bad_img = np.zeros((5, 5, 3), dtype=np.float32)
        bad_img[0, 0, 0] = np.nan
        with self.assertRaises(ValueError):
            color_body_proposals(valid_lidar, bad_img, self.image_transform)

    def test_input_preservation(self):
        """Guarantees that input arrays and dictionaries are not mutated."""
        rows, cols = 8, 8
        building_orig = np.ones((rows, cols), dtype=np.int32)
        building_copy = building_orig.copy()

        lidar_data = {
            "transform": self.lidar_transform,
            "class_evidence": {"building": building_orig},
        }

        image_orig = np.full((rows, cols, 3), 120, dtype=np.uint8)
        image_copy = image_orig.copy()

        color_body_proposals(lidar_data, image_orig, self.image_transform, min_area_m2=20.0)

        np.testing.assert_array_equal(building_orig, building_copy)
        np.testing.assert_array_equal(image_orig, image_copy)
        self.assertIn("building", lidar_data["class_evidence"])

    def test_gap_closed_only_within_same_color_and_mask_matches_slice(self):
        counts=np.zeros((12,12));counts[2:10,2:10]=1;counts[5,5]=0
        d={'transform':self.lidar_transform,'class_evidence':{'building':counts}}
        image=np.full((12,12,3),100,dtype=np.uint8)
        p=color_body_proposals(d,image,self.image_transform)[0]
        self.assertEqual(p['area_m2'],64)
        self.assertEqual(p['mask'].shape,counts[p['slice']].shape)
        self.assertTrue(p['geometry'].covers(p['positive_point_geo']))
        image[5,5]=[0,200,0]
        p=color_body_proposals(d,image,self.image_transform)[0]
        self.assertEqual(p['area_m2'],63)

    def test_nonfinite_translation_rejected(self):
        d={'transform':rasterio.transform.Affine(1,0,float('nan'),0,-1,20),
           'class_evidence':{'building':np.ones((12,12))}}
        with self.assertRaises(ValueError):
            color_body_proposals(d,np.full((12,12,3),100,dtype=np.uint8),self.image_transform)


if __name__ == "__main__":
    unittest.main()
