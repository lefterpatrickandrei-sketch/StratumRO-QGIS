import unittest
from shapely.geometry import box,Point
from stratum_ro.roof_candidate_routing import route_roof_candidate,prioritize_roof_candidates,vegetation_color_fraction


class RoofRoutingTests(unittest.TestCase):
    def feature(self,g,building=0):
        return {'geometry':g,'sam2_score':.95,'qa_building_fraction':building,'qa_returns':100,'qa_status':'NECESITA_VERIFICARE'}

    def test_glass_roof_not_rejected_for_lack_of_class6(self):
        g=box(0,0,30,10)
        r=route_roof_candidate(self.feature(g),g)
        self.assertEqual(r['route'],'INSPECTIE_PRIORITARA')
        self.assertEqual(r['qa_status'],'NECESITA_VERIFICARE')

    def test_tree_mask_must_not_become_rectangle_by_regularization(self):
        raw=Point(0,0).buffer(10)
        candidate=box(-10,-10,10,10)
        r=route_roof_candidate(self.feature(candidate),raw)
        self.assertEqual(r['route'],'REVIZUIRE_COMPLEXA')
        self.assertIn('REGULARIZARE_FARA_SUPORT_OPTIC',r['route_reason'])

    def test_compound_roof_body_can_be_supported_by_larger_raw_mask(self):
        body=box(0,0,10,30)
        raw=body.union(box(-20,0,30,10))
        r=route_roof_candidate(self.feature(body,1),raw)
        self.assertEqual(r['route'],'INSPECTIE_PRIORITARA')

    def test_duplicate_hypotheses_preserved_and_one_selected(self):
        g=box(0,0,10,10)
        a=route_roof_candidate(self.feature(g,1),g)
        b=route_roof_candidate(self.feature(g,1),g)
        result=prioritize_roof_candidates([a,b])
        self.assertEqual(len(result),2)
        self.assertEqual(sum(v['route']=='INSPECTIE_PRIORITARA' for v in result),1)
        self.assertEqual(a['route'],'INSPECTIE_PRIORITARA')

    def test_nonfinite_score_does_not_pass(self):
        g=box(0,0,10,10);f=self.feature(g);f['sam2_score']=float('nan')
        self.assertEqual(route_roof_candidate(f,g)['route'],'REVIZUIRE_COMPLEXA')

    def test_yellow_green_canopy_routed_to_review_even_if_rectangular(self):
        import numpy as np
        from rasterio.transform import from_origin
        g=box(0,0,10,10);image=np.zeros((10,10,3),dtype=np.uint8);image[:]=[150,150,40]
        fraction=vegetation_color_fraction(g,image,from_origin(0,10,1,1))
        self.assertEqual(fraction,1.)
        f=self.feature(g);f['vegetation_color_fraction']=fraction
        self.assertEqual(route_roof_candidate(f,g)['route'],'REVIZUIRE_COMPLEXA')

    def test_neutral_glass_roof_kept_despite_vegetation_lidar_class(self):
        import numpy as np
        from rasterio.transform import from_origin
        g=box(0,0,10,10);image=np.zeros((10,10,3),dtype=np.uint8);image[:]=[100,120,115]
        f=self.feature(g)
        f['vegetation_color_fraction']=vegetation_color_fraction(g,image,from_origin(0,10,1,1))
        self.assertEqual(route_roof_candidate(f,g)['route'],'INSPECTIE_PRIORITARA')
