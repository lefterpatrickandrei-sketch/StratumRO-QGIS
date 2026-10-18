import unittest
from shapely.geometry import box,Polygon
from stratum_ro.roof_revision_review import review_roof_revision


class RoofRevisionReviewTests(unittest.TestCase):
    def test_overlapping_identities_need_review(self):
        a=box(0,0,10,10);b=box(9,0,20,10)
        r=review_roof_revision({'A':a},{'A':a,'B':b})
        self.assertEqual(r['overlaps'][0]['intersection_m2'],10)
        self.assertIn('BODY_IDENTITY_OVERLAP',[v['reason'] for v in r['review_reasons']])

    def test_lost_wing_is_flagged_despite_valid_rectangle(self):
        old=box(0,0,10,10).union(box(10,0,15,5))
        r=review_roof_revision({'A':old},{'A':box(0,0,10,10)})
        self.assertIn('PREVIOUS_ROOF_SURFACE_OMITTED',[v['reason'] for v in r['review_reasons']])

    def test_filled_courtyard_is_not_automatically_adopted(self):
        old=Polygon(box(0,0,10,10).exterior,[box(3,3,7,7).exterior])
        r=review_roof_revision({'A':old},{'A':box(0,0,10,10)})
        self.assertIn('COURTYARD_TOPOLOGY_CHANGED',[v['reason'] for v in r['review_reasons']])

    def test_matching_hypotheses_are_still_not_owner_acceptance(self):
        a=box(0,0,10,10);r=review_roof_revision({'A':a},{'A':a})
        self.assertEqual(r['review_reasons'],[])
        self.assertFalse(r['automatic_adoption_allowed'])
