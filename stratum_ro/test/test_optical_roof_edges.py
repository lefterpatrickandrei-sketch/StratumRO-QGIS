import unittest
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box
from stratum_ro.optical_roof_edges import refine_roof_color


class OpticalRoofEdgesTests(unittest.TestCase):
    def scene(self):
        rgb=np.full((100,100,3),120,dtype=np.uint8)
        rgb[:70]=[180,65,60]
        ndsm=np.zeros((100,100));ndsm[:70]=5
        building=np.zeros((100,100));building[:70]=1
        tr=from_origin(0,10,.1,.1)
        return rgb,tr,{'ndsm':ndsm,'transform':tr,'class_evidence':{'building':building}}

    def test_red_roof_trims_neutral_terrace(self):
        rgb,tr,data=self.scene();p=box(0,0,10,10)
        before=rgb.copy();result,method=refine_roof_color(p,rgb,tr,data)
        self.assertEqual(method,'RED_ROOF_RELATIVE_HEIGHT')
        self.assertLess(result.intersection(box(0,0,10,2.9)).area,.2)
        self.assertGreater(result.area,65)
        np.testing.assert_array_equal(before,rgb)

    def test_supported_gray_roof_part_preserved(self):
        rgb,tr,data=self.scene();data['ndsm'][70:]=5;data['class_evidence']['building'][70:]=1
        result,method=refine_roof_color(box(0,0,10,10),rgb,tr,data)
        self.assertGreater(result.area,95)

    def test_unknown_roof_color_keeps_original(self):
        rgb,tr,data=self.scene();rgb[:]=[90,90,90];p=box(0,0,10,10)
        result,method=refine_roof_color(p,rgb,tr,data)
        self.assertEqual(method,'NONE');self.assertTrue(result.equals(p))

    def test_teal_roof_excludes_ground(self):
        rgb,tr,data=self.scene();rgb[:]=[120,110,95];rgb[:70]=[80,110,115]
        result,method=refine_roof_color(box(0,0,10,10),rgb,tr,data)
        self.assertEqual(method,'TEAL_ROOF_COLOR');self.assertLess(result.area,75)

    def test_invalid_polygon_rejected(self):
        rgb,tr,data=self.scene()
        with self.assertRaises(ValueError):refine_roof_color(None,rgb,tr,data)


if __name__=='__main__':unittest.main()
