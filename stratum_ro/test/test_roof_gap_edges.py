import unittest
import numpy as np
from rasterio import Affine
from shapely.geometry import box
from stratum_ro.roof_gap_edges import fit_roof_gap,fit_red_roof_edge,replace_observed_edge


class RoofGapEdgesTests(unittest.TestCase):
    def setUp(self):
        self.rgb=np.full((100,200,3),[120,85,65],dtype='uint8')
        self.rgb[:,90:110]=25;self.rgb[:,110:]=[160,70,60]
        self.valid=np.ones((100,200),dtype=bool)
        self.tr=Affine.translation(0,5)*Affine.scale(.05,-.05)

    def test_independent_edges_preserve_a_real_gap(self):
        r=fit_roof_gap(self.rgb,self.tr,self.valid,(5,1),(5,4))
        self.assertEqual(r['status'],'OBSERVED_OPTICAL_GAP_REQUIRES_REVIEW')
        xs=sorted(e['coordinates'][0][0] for e in r['edges'])
        self.assertAlmostEqual(xs[0],4.5,delta=.15);self.assertAlmostEqual(xs[1],5.5,delta=.15)
        self.assertFalse(r['automatic_acceptance'])

    def test_uniform_roof_does_not_invent_a_gap(self):
        self.rgb[:]=100
        self.assertTrue(fit_roof_gap(self.rgb,self.tr,self.valid,(5,1),(5,4))['status'].startswith('UNRESOLVED'))

    def test_unknown_pixels_are_not_dark_gap_evidence(self):
        self.valid[:]=False
        self.assertTrue(fit_roof_gap(self.rgb,self.tr,self.valid,(5,1),(5,4))['status'].startswith('UNRESOLVED'))

    def test_red_roof_edge_is_independent_of_neighbor_polygon(self):
        r=fit_red_roof_edge(self.rgb,self.tr,self.valid,(5,1),(5,4),(7,2))
        self.assertEqual(r['status'],'OBSERVED_RED_ROOF_EDGE_REQUIRES_REVIEW')
        self.assertAlmostEqual(r['coordinates'][0][0],5.5,delta=.15)

    def test_vertex_update_retains_other_edges_and_blocks_large_motion(self):
        p=box(0,0,10,10)
        result=replace_observed_edge(p,0,[(9.5,-1),(9.5,11)])
        self.assertTrue(result.is_valid);self.assertEqual(len(result.exterior.coords),5)
        with self.assertRaises(ValueError):replace_observed_edge(p,0,[(4,-1),(4,11)])
