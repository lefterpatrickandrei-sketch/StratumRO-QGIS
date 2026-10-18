import unittest
import numpy as np
from shapely.geometry import box,Polygon
from shapely import affinity
from stratum_ro.roof_simple_geometry import simple_roof_geometry


class SimpleRoofGeometryTests(unittest.TestCase):
    def test_rotated_rectangle_preserved(self):
        p=affinity.rotate(box(0,0,12,20),23)
        result,info=simple_roof_geometry(p)
        self.assertEqual(info['vertices'],4)
        self.assertLess(result.symmetric_difference(p).area,1e-8)

    def test_steps_removed_without_terrace_regrowth(self):
        p=Polygon([(0,0),(10,0),(10,8),(9.8,8),(9.8,12),(0,12),(0,7),(.2,7),(.2,4),(0,4)])
        result,info=simple_roof_geometry(p,box(0,0,10,17))
        self.assertEqual(info['vertices'],4)
        self.assertLessEqual(result.bounds[3],12.1)
        self.assertGreater(info['support'],.95)

    def test_l_roof_preserves_real_extension(self):
        p=Polygon([(0,0),(10,0),(10,15),(6,15),(6,20),(0,20)])
        result,info=simple_roof_geometry(p)
        self.assertEqual(info['vertices'],6)
        self.assertLess(result.symmetric_difference(p).area,1e-8)

    def test_triangle_not_forced_to_rectangle(self):
        p=Polygon([(0,0),(12,0),(0,12)])
        result,info=simple_roof_geometry(p)
        self.assertEqual(info['method'],'NEEDS_REVIEW')
        self.assertTrue(result.equals(p))

    def test_holes_retained_for_review(self):
        p=Polygon(box(0,0,20,20).exterior.coords,[box(5,5,8,8).exterior.coords])
        result,info=simple_roof_geometry(p)
        self.assertEqual(info['reason'],'INTERIOR_RINGS')
        self.assertTrue(result.equals(p))

    def test_invalid_rejected(self):
        with self.assertRaises(ValueError):simple_roof_geometry(None)
        with self.assertRaises(ValueError):simple_roof_geometry(box(0,0,10,10),min_support=0)

    def test_output_edges_orthogonal_and_input_immutable(self):
        p=affinity.rotate(Polygon([(0,0),(10,0),(10,15),(6,15),(6,20),(0,20)]),17)
        before=p.wkb
        result,info=simple_roof_geometry(p)
        edges=np.diff(np.asarray(result.exterior.coords),axis=0)
        for a,b in zip(edges,np.roll(edges,-1,axis=0)):
            self.assertAlmostEqual(float(np.dot(a,b)),0,places=7)
        self.assertEqual(p.wkb,before)


if __name__=='__main__':unittest.main()
