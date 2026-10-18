import unittest
import numpy as np
from rasterio import Affine
from stratum_ro.fusion_guidance import select_fusion_prompt


class FusionGuidanceTests(unittest.TestCase):
    def setUp(self):
        self.tr=Affine.translation(100,200)*Affine.scale(1,-1)
        self.counts=np.zeros((20,20));self.counts[2:8,2:8]=3
        self.height=np.full((20,20),5.)
        self.valid=np.ones((20,20),dtype=bool)

    def call(self,anchor=(104,196),**kw):
        return select_fusion_prompt(anchor,self.tr,self.counts,self.height,self.valid,**kw)

    def test_local_support_guides(self):
        result=self.call()
        self.assertEqual(result['source'],'LOCAL_CLASS6_AND_HEIGHT')
        self.assertEqual(result['support_cells'],36)

    def test_absent_class_is_not_veto(self):
        self.counts[:]=0
        result=self.call()
        self.assertEqual(result['point'],[104.,196.])
        self.assertEqual(result['negative_points'],[])
        self.assertEqual(result['route'],'RGB_FALLBACK_REQUIRES_REVIEW')

    def test_other_building_does_not_move_anchor(self):
        result=self.call(anchor=(118,182))
        self.assertEqual(result['reason'],'BUILDING_SUPPORT_BELONGS_ELSEWHERE')

    def test_invalid_or_incompatible_evidence_is_ignored(self):
        self.valid[:]=False
        self.assertEqual(self.call()['source'],'REVIEWED_RGB_ANCHOR')
        self.valid[:]=True
        self.assertEqual(self.call(lidar_compatible=False)['source'],'REVIEWED_RGB_ANCHOR')

    def test_height_required_for_lidar_guidance(self):
        self.height[:]=0
        self.assertEqual(self.call()['source'],'REVIEWED_RGB_ANCHOR')

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            select_fusion_prompt((1,2),self.tr,self.counts,self.height[:2],self.valid)

    def test_connected_neighbor_cannot_steal_prompt(self):
        self.counts[:]=0
        self.counts[8:11,1:4]=3
        self.counts[9,4:10]=3
        self.counts[2:18,10:19]=3
        anchor=(102.5,190.5)
        r=self.call(anchor=anchor,max_prompt_shift_m=3.)
        self.assertLessEqual(np.linalg.norm(np.array(r['point'])-anchor),3.)
        self.assertLess(r['point'][0],106)

    def test_nonfinite_identity_radius_is_rejected(self):
        with self.assertRaises(ValueError):self.call(max_prompt_shift_m=float('nan'))
