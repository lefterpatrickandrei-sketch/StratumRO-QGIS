# -*- coding: utf-8 -*-
"""
Unit tests for deterministic complete_building_grid helper in lidar_processor.py.
Synthetic numpy arrays only (no QGIS, no Fiona, no new external dependencies).
"""

import unittest
import numpy as np
import tempfile
from pathlib import Path
import laspy
from stratum_ro.lidar_processor import complete_building_grid, LidarProcessor


class TestLidarCompletion(unittest.TestCase):
    def test_processor_legacy_default_and_experimental_policy_on_synthetic_las(self):
        """Real file IO with synthetic classes verifies the full caller integration."""
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'synthetic.las'
            header=laspy.LasHeader(point_format=1,version='1.2')
            header.scales=np.array([.01,.01,.01])
            cloud=laspy.LasData(header)
            yy,xx=np.mgrid[0:11,0:11]
            vx,vy=np.mgrid[2:8,2:8]
            cloud.x=np.r_[xx.ravel()+.5,vx.ravel()+.5]
            cloud.y=np.r_[yy.ravel()+.5,vy.ravel()+.5]
            cloud.z=np.r_[np.zeros(xx.size),np.full(vx.size,6.)]
            cloud.classification=np.r_[np.full(xx.size,2),np.full(vx.size,5)].astype(np.uint8)
            cloud.write(path)
            processor=LidarProcessor(str(path))
            default=processor.process_multicategory(auto_datum_adjust=False)
            legacy=processor.process_multicategory(auto_datum_adjust=False,completion_policy='legacy')
            experimental=processor.process_multicategory(auto_datum_adjust=False,completion_policy='exclude_known_vegetation')
            self.assertEqual(default['completion_policy'],'legacy')
            np.testing.assert_array_equal(default['main_buildings_grid'],legacy['main_buildings_grid'])
            self.assertGreater(default['main_buildings_grid'].sum(),0)
            self.assertEqual(experimental['main_buildings_grid'].sum(),0)
            np.testing.assert_array_equal(default['ndsm'],experimental['ndsm'])

    def test_unknown_policy_rejected_before_reading_source(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'placeholder.las'
            path.touch()
            with self.assertRaisesRegex(ValueError,'completion_policy'):
                LidarProcessor(str(path)).process_multicategory(completion_policy='unknown')

    def test_tall_class5_vegetation_patch_not_reintroduced(self):
        """A tall patch (ndsm >= 0.8) marked as vegetation (class 4/5) must not be added to buildings."""
        rows, cols = 20, 20
        res = 1.0
        base = np.zeros((rows, cols), dtype=np.uint8)
        ndsm = np.zeros((rows, cols), dtype=np.float32)
        veg = np.zeros((rows, cols), dtype=np.uint8)

        # 6x6 patch (36 m2 >= 35 m2) with height 5.0m
        ndsm[2:8, 2:8] = 5.0
        veg[2:8, 2:8] = 1

        out = complete_building_grid(base, ndsm, veg, resolution=res, min_area_m2=35.0)
        self.assertEqual(np.sum(out), 0, "Vegetation-only patch must not be introduced into buildings.")

    def test_building_touching_vegetation_not_bridged_through_vegetation_cells(self):
        """Building and nearby vegetation should not merge/bridge across vegetation cells."""
        rows, cols = 10, 30
        res = 1.0
        base = np.zeros((rows, cols), dtype=np.uint8)
        ndsm = np.zeros((rows, cols), dtype=np.float32)
        veg = np.zeros((rows, cols), dtype=np.uint8)

        # Building at [2:8, 2:8] (36 pixels) in base_grid
        base[2:8, 2:8] = 1
        ndsm[2:8, 2:8] = 3.0

        # Vegetation bridge at [4:6, 8:12] and tree patch at [2:8, 12:18]
        ndsm[4:6, 8:12] = 4.0
        veg[4:6, 8:12] = 1

        ndsm[2:8, 12:18] = 6.0
        veg[2:8, 12:18] = 1

        out = complete_building_grid(base, ndsm, veg, resolution=res, min_area_m2=35.0)

        # Only the original base building should be active
        self.assertTrue(np.all(out[2:8, 2:8] == 1))
        self.assertEqual(np.sum(out[4:6, 8:12]), 0, "Bridge vegetation cells must not become building.")
        self.assertEqual(np.sum(out[2:8, 12:18]), 0, "Vegetation patch must not become building.")
        self.assertEqual(np.sum(out), 36)

    def test_base_support_survives_mixed_vegetation_cell(self):
        """If base_grid has explicit building support, that cell is preserved even if vegetation occurs there."""
        rows, cols = 10, 10
        res = 1.0
        base = np.zeros((rows, cols), dtype=np.uint8)
        ndsm = np.zeros((rows, cols), dtype=np.float32)
        veg = np.zeros((rows, cols), dtype=np.uint8)

        # Single cell with base support and vegetation
        base[4, 4] = 1
        veg[4, 4] = 1
        ndsm[4, 4] = 2.5

        out = complete_building_grid(base, ndsm, veg, resolution=res, min_area_m2=35.0)
        self.assertEqual(out[4, 4], 1, "Base building support must survive mixed vegetation cell.")

    def test_area_threshold_consistent_at_different_resolutions(self):
        """35 m2 threshold is evaluated consistently at 0.5m and 2.0m resolutions."""
        # At 0.5m res: 1 pixel is 0.25 m2 -> 35 m2 requires 140 pixels.
        # Test 136 pixels (34 m2 -> rejected) vs 144 pixels (36 m2 -> accepted)
        rows, cols = 30, 30
        res_half = 0.5
        base = np.zeros((rows, cols), dtype=np.uint8)
        veg = np.zeros((rows, cols), dtype=np.uint8)

        # 34 m2 candidate (136 pixels)
        ndsm_sub = np.zeros((rows, cols), dtype=np.float32)
        ndsm_sub[0:17, 0:8] = 3.0  # 17 * 8 = 136 pixels = 34 m2
        out_sub = complete_building_grid(base, ndsm_sub, veg, resolution=res_half, min_area_m2=35.0)
        self.assertEqual(np.sum(out_sub), 0, "Candidate < 35 m2 at 0.5m resolution must be rejected.")

        # 36 m2 candidate (144 pixels)
        ndsm_super = np.zeros((rows, cols), dtype=np.float32)
        ndsm_super[0:12, 0:12] = 3.0  # 12 * 12 = 144 pixels = 36 m2
        out_super = complete_building_grid(base, ndsm_super, veg, resolution=res_half, min_area_m2=35.0)
        self.assertEqual(np.sum(out_super), 144, "Candidate >= 35 m2 at 0.5m resolution must be accepted.")

        # At 2.0m res: 1 pixel is 4.0 m2 -> 35 m2 requires ceil(35/4) = 9 pixels.
        # Test 8 pixels (32 m2 -> rejected) vs 9 pixels (36 m2 -> accepted)
        res_two = 2.0
        base_2 = np.zeros((10, 10), dtype=np.uint8)
        veg_2 = np.zeros((10, 10), dtype=np.uint8)

        # 8 pixels = 32 m2
        ndsm_2_sub = np.zeros((10, 10), dtype=np.float32)
        ndsm_2_sub[0:2, 0:4] = 2.5
        out_2_sub = complete_building_grid(base_2, ndsm_2_sub, veg_2, resolution=res_two, min_area_m2=35.0)
        self.assertEqual(np.sum(out_2_sub), 0, "Candidate < 35 m2 at 2m resolution must be rejected.")

        # 9 pixels = 36 m2 (3x3)
        ndsm_2_super = np.zeros((10, 10), dtype=np.float32)
        ndsm_2_super[0:3, 0:3] = 2.5
        out_2_super = complete_building_grid(base_2, ndsm_2_super, veg_2, resolution=res_two, min_area_m2=35.0)
        self.assertEqual(np.sum(out_2_super), 9, "Candidate >= 35 m2 at 2m resolution must be accepted.")

    def test_nan_and_inf_excluded(self):
        """NaN and inf values in nDSM must be cleanly excluded and not cause errors."""
        rows, cols = 15, 15
        base = np.zeros((rows, cols), dtype=np.uint8)
        veg = np.zeros((rows, cols), dtype=np.uint8)
        ndsm = np.full((rows, cols), np.nan, dtype=np.float32)
        ndsm[0:6, 0:6] = np.inf

        out = complete_building_grid(base, ndsm, veg, resolution=1.0, min_area_m2=35.0)
        self.assertEqual(np.sum(out), 0, "NaN and Inf values must not create building proposals.")

    def test_inputs_unchanged(self):
        """Inputs must never be mutated in-place."""
        base = np.zeros((10, 10), dtype=np.uint8)
        base[1, 1] = 1
        ndsm = np.full((10, 10), 2.0, dtype=np.float32)
        veg = np.zeros((10, 10), dtype=np.uint8)
        veg[2, 2] = 1

        base_copy = base.copy()
        ndsm_copy = ndsm.copy()
        veg_copy = veg.copy()

        out = complete_building_grid(base, ndsm, veg, resolution=1.0, min_area_m2=35.0)

        np.testing.assert_array_equal(base, base_copy)
        np.testing.assert_array_equal(ndsm, ndsm_copy)
        np.testing.assert_array_equal(veg, veg_copy)
        self.assertIsNot(out, base)

    def test_invalid_shape_and_resolution_rejected(self):
        """Invalid shapes and invalid resolutions must raise ValueError."""
        valid_2d = np.zeros((5, 5), dtype=np.uint8)
        mismatch_2d = np.zeros((6, 5), dtype=np.uint8)
        ndsm_2d = np.zeros((5, 5), dtype=np.float32)
        arr_3d = np.zeros((5, 5, 1), dtype=np.uint8)

        # Shape mismatch
        with self.assertRaises(ValueError):
            complete_building_grid(valid_2d, ndsm_2d, mismatch_2d, resolution=1.0)

        # 3D array
        with self.assertRaises(ValueError):
            complete_building_grid(arr_3d, ndsm_2d, valid_2d, resolution=1.0)

        # Non-positive or non-finite resolution
        with self.assertRaises(ValueError):
            complete_building_grid(valid_2d, ndsm_2d, valid_2d, resolution=0.0)

        with self.assertRaises(ValueError):
            complete_building_grid(valid_2d, ndsm_2d, valid_2d, resolution=-1.0)

        with self.assertRaises(ValueError):
            complete_building_grid(valid_2d, ndsm_2d, valid_2d, resolution=np.nan)


if __name__ == "__main__":
    unittest.main()
