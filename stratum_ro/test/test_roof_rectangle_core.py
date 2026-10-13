import unittest
from shapely.geometry import box,Point
from shapely import affinity
from stratum_ro.roof_rectangle_core import rectangle_core
from stratum_ro.roof_candidate_routing import route_roof_candidate


class RectangleCoreTests(unittest.TestCase):
    def test_small_spur_removed_with_optical_support(self):
        roof=box(0,0,40,10);spurred=roof.union(box(15,10,18,14))
        repaired=rectangle_core(spurred,spurred)
        self.assertGreater(repaired.intersection(roof).area/repaired.union(roof).area,.95)
        self.assertEqual(len(repaired.exterior.coords),5)

    def test_rotated_spur_without_reference(self):
        spurred=affinity.rotate(box(0,0,40,10).union(box(15,10,18,14)),23)
        repaired=rectangle_core(spurred,spurred)
        self.assertEqual(len(repaired.exterior.coords),5)
        self.assertGreater(repaired.intersection(spurred).area/repaired.union(spurred).area,.8)

    def test_large_T_body_not_collapsed_to_rectangle(self):
        t=box(0,0,10,30).union(box(-20,20,30,30))
        self.assertTrue(rectangle_core(t,t).equals(t))

    def test_tree_regularization_not_accepted_as_supported_roof(self):
        tree=Point(0,0).buffer(10)
        candidate=box(-10,-10,10,10)
        repaired=rectangle_core(candidate,tree)
        r=route_roof_candidate({'geometry':repaired,'sam2_score':.99,
            'qa_building_fraction':0,'qa_returns':100},tree)
        self.assertEqual(r['route'],'REVIZUIRE_COMPLEXA')
