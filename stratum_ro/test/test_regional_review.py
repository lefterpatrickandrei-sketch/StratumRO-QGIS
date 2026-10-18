import tempfile
import unittest
from pathlib import Path
import rasterio
from rasterio.transform import from_origin
import numpy as np
from shapely.geometry import box
from stratum_ro.regional_roofs import OrthoMosaic
from stratum_ro.regional_review import clip_to_valid_mosaic


class MaskBoundaryTests(unittest.TestCase):
    def test_refinement_cannot_add_area_over_invalid_hole_or_outside_source(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.tif'
            valid=np.ones((10,10),dtype='uint8')*255;valid[4:6,4:6]=0
            with rasterio.open(path,'w',driver='GTiff',width=10,height=10,count=3,
                dtype='uint8',crs='EPSG:3844',transform=from_origin(0,10,1,1)) as dst:
                dst.write(np.zeros((3,10,10),dtype='uint8'));dst.write_mask(valid)
            # All RGB is black but the declared mask, not brightness, defines data.
            source=OrthoMosaic([path])
            clipped,removed=clip_to_valid_mosaic(box(-1,-1,11,11),source,resolution=1)
            self.assertAlmostEqual(clipped.area,96)
            self.assertAlmostEqual(removed,48)
            self.assertEqual(len(clipped.interiors),1)

    def test_boundary_only_contacts_do_not_turn_surface_into_geometry_collection(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.tif'
            valid=np.zeros((4,4),dtype='uint8');valid[:2,:2]=255;valid[3,3]=255
            with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=3,
                dtype='uint8',crs='EPSG:3844',transform=from_origin(0,4,1,1)) as dst:
                dst.write(np.full((3,4,4),100,dtype='uint8'));dst.write_mask(valid)
            clipped,removed=clip_to_valid_mosaic(box(0,1,3,4),OrthoMosaic([path]),resolution=1)
            self.assertEqual(clipped.geom_type,'Polygon')
            self.assertAlmostEqual(clipped.area,4)


if __name__=='__main__':unittest.main()
