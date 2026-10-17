import unittest
import numpy as np
from rasterio import Affine
from shapely.geometry import box
from stratum_ro.fusion_refinement import refine_fusion_mask


class FusionRefinementTests(unittest.TestCase):
    def setUp(self):
        self.rgb=np.full((80,80,3),110,dtype='uint8')
        self.height=np.zeros((80,80));self.height[20:60,20:60]=6
        self.counts=(self.height>0).astype(float)
        self.valid=np.ones((80,80),dtype=bool)
        self.tr=Affine.translation(0,20)*Affine.scale(.25,-.25)

    def run_case(self,route):
        return refine_fusion_mask(box(2,2,18,18),(10,10),self.rgb,self.tr,self.height,self.counts,self.valid,route)

    def test_lidar_removes_observed_ground(self):
        geom,diag=self.run_case('LIDAR_GUIDED_REQUIRES_REVIEW')
        self.assertLess(geom.area,130)
        self.assertGreater(geom.area,80)

    def test_rgb_fallback_survives_zero_height(self):
        self.height[:]=0;self.counts[:]=0
        geom,diag=self.run_case('RGB_FALLBACK_REQUIRES_REVIEW')
        self.assertGreater(geom.area,200)
        self.assertFalse(diag['lidar_used'])

    def test_large_courtyard_is_not_filled(self):
        self.height[32:48,32:48]=0
        # Seed deliberately outside courtyard.
        geom,diag=refine_fusion_mask(box(2,2,18,18),(7,10),self.rgb,self.tr,self.height,self.counts,self.valid,'LIDAR_GUIDED_REQUIRES_REVIEW')
        self.assertFalse(geom.covers(box(9,9,11,11)))

    def test_invalid_sensor_shapes_rejected(self):
        with self.assertRaises(ValueError):
            refine_fusion_mask(box(2,2,18,18),(10,10),self.rgb,self.tr,self.height[:2],self.counts,self.valid,'RGB_FALLBACK_REQUIRES_REVIEW')

    def test_connected_support_cannot_expand_into_distant_neighbor(self):
        self.height[20:60,20:79]=6
        self.counts=(self.height>0).astype(float)
        geom,diag=self.run_case('LIDAR_GUIDED_REQUIRES_REVIEW')
        self.assertLessEqual(geom.bounds[2],19.5)

    def test_missing_seed_keeps_explicit_failure(self):
        self.valid[:]=False
        geom,diag=self.run_case('RGB_FALLBACK_REQUIRES_REVIEW')
        self.assertEqual(diag['status'],'UNRESOLVED_SEED_NOT_COVERED')

    def test_class6_supported_dark_roof_is_not_lost_by_color_threshold(self):
        self.rgb[20:60,20:60]=[45,44,43]
        geom,diag=self.run_case('LIDAR_GUIDED_REQUIRES_REVIEW')
        self.assertGreater(geom.area,80)
        self.assertNotEqual(diag['method'],'RAW_PRESERVED')
