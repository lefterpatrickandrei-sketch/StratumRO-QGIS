import unittest
from shapely.geometry import Polygon,box
from stratum_ro.roof_mask_fidelity import simplify_observed_roof
from stratum_ro.roof_mask_fidelity import rectangular_roof_core


class MaskFidelityTests(unittest.TestCase):
    def test_small_real_wing_is_not_erased_by_rectangle(self):
        raw=box(0,0,20,10).union(box(20,0,23,3))
        g,d=simplify_observed_roof(raw,(10,5))
        self.assertGreater(g.intersection(box(20,0,23,3)).area,8)
        self.assertGreater(d['coverage'],.985)

    def test_courtyard_is_not_filled(self):
        raw=Polygon(box(0,0,20,20).exterior,[box(5,5,10,10).exterior])
        g,d=simplify_observed_roof(raw,(2,2))
        self.assertEqual(len(g.interiors),1)

    def test_rectangle_not_rotated_to_world_axes(self):
        from shapely.affinity import rotate
        raw=rotate(box(0,0,10,20),33)
        g,d=simplify_observed_roof(raw,raw.representative_point().coords[0])
        self.assertGreater(g.intersection(raw).area/g.union(raw).area,.985)

    def test_reviewed_plane_removes_narrow_attached_duct(self):
        raw=box(0,0,20,15).union(box(9,-8,10,0))
        g,d=rectangular_roof_core(raw,(10,8))
        self.assertEqual(len(g.exterior.coords)-1,4)
        self.assertLess(g.intersection(box(9,-8,10,-2)).area,1)

    def test_small_mask_pinholes_do_not_destroy_planar_core(self):
        raw=Polygon(box(0,0,20,15).exterior,[box(5,5,5.2,5.2).exterior])
        g,d=rectangular_roof_core(raw,(10,8))
        self.assertEqual(d['status'],'RECTIFIED_HYPOTHESIS_PENDING_OWNER_REVIEW')
