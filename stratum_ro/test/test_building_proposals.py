import unittest
import numpy as np
from rasterio.transform import from_origin
from stratum_ro.building_proposals import building_proposals


class ProposalTests(unittest.TestCase):
    def data(self):
        return {'transform':from_origin(0,30,1,1),
                'class_evidence':{'building':np.zeros((30,30))},
                'main_buildings_grid':np.zeros((30,30)),
                'outbuildings_grid':np.zeros((30,30))}

    def test_two_roofs_not_lost_inside_one_vegetation_context(self):
        d = self.data()
        d['main_buildings_grid'][2:20,2:20] = 1
        d['class_evidence']['building'][3:7,3:7] = 1
        d['class_evidence']['building'][12:16,12:16] = 1
        p = building_proposals(d)
        self.assertEqual([v['source'] for v in p],['CLASS_6','CLASS_6','NDSM_CONTEXT'])
        self.assertEqual([v['area_m2'] for v in p],[16,16,324])

    def test_glass_roof_without_class6_kept(self):
        d = self.data()
        d['main_buildings_grid'][5:10,5:15] = 1
        p = building_proposals(d)
        self.assertEqual(len(p),1)
        self.assertEqual(p[0]['source'],'NDSM_CONTEXT')

    def test_exact_class6_legacy_duplicate_only_once(self):
        d = self.data()
        d['main_buildings_grid'][5:10,5:15] = 1
        d['class_evidence']['building'][5:10,5:15] = 1
        self.assertEqual(len(building_proposals(d)),1)

    def test_physical_area_and_inputs_unchanged(self):
        d = self.data()
        d['transform'] = from_origin(0,30,.5,.5)
        d['class_evidence']['building'][5:10,5:10] = 1
        original = d['class_evidence']['building'].copy()
        self.assertEqual(building_proposals(d),[])
        np.testing.assert_array_equal(original,d['class_evidence']['building'])
