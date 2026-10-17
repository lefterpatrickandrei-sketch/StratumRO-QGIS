import unittest
import numpy as np
from rasterio import Affine
from stratum_ro.cadastral_roof_workflow import CadastralRoofWorkflow


class FakeSegmenter:
    def __init__(self):self.predictor=self;self.encodes=0;self.calls=0
    def set_image(self,rgb,tr):self.encodes+=1;self.shape=rgb.shape[:2]
    def predict(self,**kw):
        self.calls+=1
        mask=np.zeros(self.shape,dtype=bool);mask[20:60,20:60]=True
        return np.array([mask]),np.array([.8]),None


class CadastralRoofWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.model=FakeSegmenter();self.flow=CadastralRoofWorkflow(self.model)
        self.rgb=np.full((80,80,3),110,dtype='uint8');self.valid=np.ones((80,80),dtype=bool)
        self.tr=Affine.translation(0,20)*Affine.scale(.25,-.25)
        self.flow.set_scene(self.rgb,self.tr,self.valid,crs='EPSG:3844')

    def extract(self,id='B1',**kw):
        return self.flow.extract(id,(10,10),(5,5,15,15),reviewed=True,**kw)

    def test_ortho_only_does_not_invent_ground_footprint(self):
        r=self.extract()
        self.assertIsNotNone(r['geometry']);self.assertIsNone(r['ground_footprint'])
        self.assertEqual(r['owner_verdict'],'PENDING_OWNER_REVIEW')
        self.assertIn('LIDAR_NOT_USED_OR_INCOMPATIBLE',r['review_reasons'])

    def test_reuses_image_encoding(self):
        self.extract('B1');self.extract('B2')
        self.assertEqual(self.model.encodes,1);self.assertEqual(self.model.calls,2)

    def test_unreviewed_candidate_is_blocked_before_inference(self):
        with self.assertRaises(ValueError):self.flow.extract('B1',(10,10),(5,5,15,15))
        self.assertEqual(self.model.encodes,0)

    def test_nodata_context_blocks_inference_but_valid_black_does_not(self):
        self.valid[10,10]=False
        self.flow.set_scene(self.rgb,self.tr,self.valid,crs='EPSG:3844')
        with self.assertRaisesRegex(ValueError,'NODATA'):self.extract()
        self.valid[:]=True;self.rgb[10,10]=0
        self.flow.set_scene(self.rgb,self.tr,self.valid,crs='EPSG:3844')
        self.assertIsNotNone(self.extract()['geometry'])

    def test_incomplete_context_is_blocked(self):
        with self.assertRaisesRegex(ValueError,'COVERAGE'):self.extract(context_m=10)

    def test_masked_context_is_opt_in_and_invalid_pixels_stay_out(self):
        self.valid[10,10]=False
        self.flow.set_scene(self.rgb,self.tr,self.valid,crs='EPSG:3844')
        r=self.extract(allow_invalid_context=True,refinement_policy='OPTICAL_FIDELITY')
        self.assertIn('NODATA_NEAR_TARGET_COMPLETENESS_UNCONFIRMED',r['review_reasons'])

    def test_ids_stay_explicit(self):
        self.extract('T17:C1')
        with self.assertRaises(ValueError):self.extract('T17:C1')
        self.assertEqual(self.extract('T17:C2')['body_id'],'T17:C2')

    def test_geographic_crs_is_not_relabelled(self):
        with self.assertRaises(ValueError):self.flow.set_scene(self.rgb,self.tr,self.valid,crs='EPSG:4284')

    def test_low_score_is_retained_for_review(self):
        r=self.extract(score_threshold=.9)
        self.assertIn('LOW_OPTICAL_SCORE',r['review_reasons']);self.assertIsNotNone(r['geometry'])

    def test_raw_boundary_contact_is_reported_even_after_refinement(self):
        r=self.extract()
        check=r['search_window_check']
        self.assertEqual(check['raw_boundary_distance_m'],0)
        self.assertIn('POSSIBLE_SEARCH_WINDOW_TRUNCATION',r['review_reasons'])
        self.assertFalse(check['automatic_completeness_claim'])

    def test_wider_search_retains_auditable_positive_raw_margin(self):
        r=self.flow.extract('wide',(10,10),(4,4,16,16),reviewed=True,context_m=1)
        self.assertGreater(r['search_window_check']['raw_boundary_distance_m'],.3)
        self.assertNotIn('POSSIBLE_SEARCH_WINDOW_TRUNCATION',r['review_reasons'])

    def test_service_exposes_same_workflow_without_loading_real_model(self):
        from stratum_ro.api.service import PlatformService
        flow=PlatformService().create_cadastral_roof_workflow(self.model)
        self.assertIsInstance(flow,CadastralRoofWorkflow)

    def test_anchor_must_match_segmented_object(self):
        # A high-scoring mask that misses the reviewed object cannot become its result.
        result=self.flow.extract('B3',(17,10),(5,5,18,15),reviewed=True,context_m=1)
        self.assertEqual(result['status'],'NO_OPTICAL_MASK_FOR_REVIEWED_OBJECT')
        self.assertIsNone(result['geometry'])
