import unittest
import numpy as np
from rasterio.transform import from_origin
from shapely.geometry import box
from stratum_ro.roof_retry import trim_retry_roof_surface
from stratum_ro.roof_simple_geometry import simple_roof_geometry


class RetrySurfaceTests(unittest.TestCase):
    def scene(self):
        rgb=np.full((100,100,3),120,dtype=np.uint8);tr=from_origin(0,10,.1,.1)
        ndsm=np.full((100,100),5.)
        return rgb,tr,{'ndsm':ndsm,'transform':tr,'class_evidence':{'building':np.ones((100,100))}}

    def test_large_courtyard_is_preserved(self):
        rgb,tr,data=self.scene();data['ndsm'][30:60,30:60]=0
        result,method=trim_retry_roof_surface(box(0,0,10,10),rgb,tr,data,{'point':(2.,8.),'mean_h':5.,'red_fraction':0.})
        self.assertEqual(method,'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        self.assertEqual(len(result.interiors),1)
        self.assertLess(result.intersection(box(3,4,6,7)).area,.5)

    def test_small_spectral_hole_does_not_block_rectangle(self):
        rgb,tr,data=self.scene();data['ndsm'][40:50,40:50]=0
        result,method=trim_retry_roof_surface(box(0,0,10,10),rgb,tr,data,{'point':(2.,8.),'mean_h':5.,'red_fraction':0.})
        self.assertEqual(len(result.interiors),0)
        simple,info=simple_roof_geometry(result)
        self.assertEqual(info['vertices'],4)

    def test_open_u_courtyard_not_filled(self):
        rgb,tr,data=self.scene();rgb[:]=[150,100,70]
        rgb[:20,:20]=[120,120,120]  # LiDAR-supported gray patch is still roof.
        data['ndsm'][40:,30:70]=0
        result,method=trim_retry_roof_surface(box(0,0,10,10),rgb,tr,data,{'point':(1.,8.),'mean_h':5.,'red_fraction':1.})
        simple,info=simple_roof_geometry(result)
        self.assertEqual(info['vertices'],8)
        self.assertLess(simple.intersection(box(3,0,7,6)).area,.5)

    def test_local_height_separates_lower_neutral_annex(self):
        rgb,tr,data=self.scene();data['ndsm'][:,40:]=16.
        # Parent average mixes a 5m annex and a16m main roof; the seed's local
        # height must guide this body instead of the compound's mean.
        result,method=trim_retry_roof_surface(box(0,0,10,10),rgb,tr,data,
            {'point':(2.,8.),'mean_h':11.6,'local_h':5.,'red_fraction':0.})
        self.assertEqual(method,'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        self.assertLess(result.intersection(box(4.1,0,10,10)).area,.1)
        self.assertGreater(result.area,35.)

    def test_coherent_component_does_not_use_low_local_outlier(self):
        rgb,tr,data=self.scene();data['ndsm'][90:,:]=2.2
        result,method=trim_retry_roof_surface(box(0,0,10,10),rgb,tr,data,
            {'point':(2.,8.),'mean_h':5.,'local_h':2.5,'max_h':5.8,'red_fraction':0.})
        self.assertEqual(method,'LOCAL_HEIGHT_BROWN_NEUTRAL_SURFACE')
        self.assertLess(result.intersection(box(0,0,10,.9)).area,.1)


if __name__=='__main__':unittest.main()
