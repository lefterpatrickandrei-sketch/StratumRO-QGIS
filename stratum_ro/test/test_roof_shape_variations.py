import unittest
from shapely.geometry import Polygon,box
from stratum_ro.roof_simple_geometry import roof_shape_variations,roof_shape_family

class ShapeVariationTests(unittest.TestCase):
    def test_rectangle_does_not_become_more_complex(self):
        g=box(0,0,20,10)
        selected,_=roof_shape_variations(g)
        assert selected['vertices']==4 and selected['geometry'].equals(g)
    
    def test_real_l_cannot_be_filled_by_rectangle(self):
        g=Polygon([(0,0),(20,0),(20,5),(5,5),(5,20),(0,20)])
        selected,variants=roof_shape_variations(g)
        assert roof_shape_family(selected['geometry'])=='L'
        assert any(v['method']=='RECTANGLE' and not v['eligible'] for v in variants)
    
    def test_courtyard_and_u_remain_open(self):
        g=Polygon(box(0,0,20,20).exterior,[box(5,5,15,15).exterior.coords])
        selected,_=roof_shape_variations(g)
        assert selected['geometry'].intersection(box(5,5,15,15)).area==0
        u=Polygon([(0,0),(20,0),(20,20),(15,20),(15,5),(5,5),(5,20),(0,20)])
        selected,_=roof_shape_variations(u)
        assert roof_shape_family(selected['geometry'])=='U'
    
    def test_small_jogs_simplify_but_displaced_previous_is_rejected(self):
        g=Polygon([(0,0),(20,0),(20,10),(10,10),(10,10.15),(9,10.15),(9,10),(0,10)])
        selected,variants=roof_shape_variations(g,box(100,100,120,110))
        assert selected['vertices']==4
        assert not any(v['eligible'] and v['geometry'].centroid.x>50 for v in variants)
    
