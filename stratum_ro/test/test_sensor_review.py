import unittest
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box
from shapely.ops import unary_union
from stratum_ro.sensor_review import build_class_evidence, review_candidates


class SensorReviewTests(unittest.TestCase):
    def setUp(self):
        self.tr = from_origin(0, 10, 1, 1)

    def test_vegetation_classified_roof_preserved_not_approved(self):
        evidence = build_class_evidence([2.5,2.5,2.5], [7.5]*3, [5,5,2], (10,10), self.tr)
        geom = box(2,7,3,8)
        source = {'id':21, 'geometry':geom}
        result = review_candidates([source], evidence, self.tr)
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['geometry'].equals_exact(geom,0))
        self.assertEqual(result[0]['qa_status'],'NECESITA_VERIFICARE')
        self.assertIn('VEGETATIE_DOMINANTA',result[0]['qa_reasons'])
        self.assertIn('FARA_SUPORT_CLASA_6',result[0]['qa_reasons'])
        self.assertNotIn('qa_status',source)

    def test_supported_rectangle_is_unreviewed_not_approved(self):
        evidence = build_class_evidence([2.5], [7.5], [6], (10,10), self.tr)
        result = review_candidates([{'geometry':box(2,7,3,8)}],evidence,self.tr)[0]
        self.assertEqual(result['qa_status'],'NEVERIFICAT')
        self.assertEqual(result['qa_building_fraction'],1.)

    def test_compound_body_routed_to_review_without_cutting(self):
        geom = unary_union([box(3,0,5,8),box(0,6,8,8)])
        evidence = {k:np.ones((10,10)) if k!='vegetation' else np.zeros((10,10))
                    for k in ['observed','building','vegetation']}
        result = review_candidates([{'geometry':geom}],evidence,self.tr)[0]
        self.assertIn('CORPURI_SAU_FORMA_CONCAVA',result['qa_reasons'])
        self.assertTrue(result['geometry'].equals(geom))

    def test_out_of_bounds_points_never_clipped_onto_roof(self):
        ev = build_class_evidence([-1,.5,10,np.nan],[9.5]*4,[6]*4,(10,10),self.tr)
        self.assertEqual(ev['observed'].sum(),1)
        self.assertEqual(ev['building'][0,0],1)

    def test_missing_data_and_outside_polygon_are_reviewed(self):
        ev = {k:np.zeros((10,10)) for k in ['observed','building','vegetation']}
        records = review_candidates([{'geometry':box(20,20,21,21)}],ev,self.tr)
        self.assertIn('DATE_LIDAR_INSUFICIENTE', records[0]['qa_reasons'])

    def test_impossible_class_counts_fail(self):
        ev = {'observed':np.ones((10,10)), 'building':np.ones((10,10)), 'vegetation':np.ones((10,10))}
        with self.assertRaises(ValueError):
            review_candidates([{'geometry':box(0,0,1,1)}],ev,self.tr)

    def test_stable_geometry_identity_independent_of_ring_order(self):
        ev = {k:np.zeros((10,10)) for k in ['observed','building','vegetation']}
        a = box(2,7,3,8)
        from shapely.geometry import Polygon
        b = Polygon(list(a.exterior.coords)[::-1])
        records = review_candidates([{'geometry':a},{'geometry':b}],ev,self.tr)
        self.assertEqual(records[0]['qa_id'],records[1]['qa_id'])

if __name__ == '__main__':
    unittest.main()
