import unittest
from unittest.mock import MagicMock
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box,Point
from stratum_ro.roof_retry import retry_roof_geometry


class LocalRetryTests(unittest.TestCase):
    def scene(self):
        rgb=np.full((100,100,3),120,dtype=np.uint8);tr=from_origin(0,100,1,1)
        data={'ndsm':np.full((100,100),5.),'transform':tr,'class_evidence':{
            'building':np.ones((100,100)),'observed':np.ones((100,100)),
            'vegetation':np.zeros((100,100))}}
        return rgb,tr,data

    def test_new_sam_point_belongs_to_child(self):
        rgb,tr,data=self.scene();child=box(20,20,40,40)
        model=MagicMock();model.segment_candidate.return_value={'geometry':child,'status':'CONFIRMAT_HIBRID','sam2_score':.91}
        result=retry_roof_geometry(child,rgb,tr,data,model)
        self.assertEqual(len(result['candidates']),1)
        point=model.segment_candidate.call_args.kwargs['internal_pts_geo'][0]
        self.assertTrue(child.covers(Point(point)))
        self.assertEqual(result['status'],'RECTIFIED_HYPOTHESES_PENDING_REVIEW')
        self.assertEqual(result['candidates'][0]['vertices'],4)

    def test_no_building_evidence_does_not_invent_rectangle(self):
        rgb,tr,data=self.scene();data['class_evidence']['building'][:]=0
        model=MagicMock();result=retry_roof_geometry(box(20,20,40,40),rgb,tr,data,model)
        self.assertEqual(result['status'],'NO_SUPPORTED_ROOF_SEED')
        self.assertEqual(result['candidates'],[]);model.segment_candidate.assert_not_called()

    def test_clipped_tile_requests_coverage_before_inference(self):
        rgb,tr,data=self.scene();model=MagicMock()
        result=retry_roof_geometry(box(0,20,10,40),rgb,tr,data,model)
        self.assertEqual(result['status'],'NEEDS_COMPLETE_IMAGE_COVERAGE')
        model.segment_candidate.assert_not_called()


if __name__=='__main__':unittest.main()
