import unittest
from shapely.geometry import Polygon,box
from stratum_ro.roof_simple_geometry import roof_shape_variations,roof_shape_family

class ShapeVariationTests(unittest.TestCase):
    def test_batch_identity_neighbor_guards_and_order_invariance(self):
        from stratum_ro.regional_refinement import RegionalRoofRefiner
        class Stub(RegionalRoofRefiner):
            def shape_variations(self,g,previous=None,**kwargs):
                # Each alone adds zero overlap; together the proposals overlap.
                proposed=box(0,0,10.6,10) if g.centroid.x<10 else box(10.4,0,20,10)
                info=dict(geometry=proposed,vertices=4,family='RECTANGLE',method='TEST',eligible=True,reasons=[])
                return info,[info]
        engine=Stub(None)
        records=[dict(candidate_id='A',geometry=box(0,0,10,10)),dict(candidate_id='B',geometry=box(11,0,20,10))]
        first=engine.simplify_shapes(records);second=engine.simplify_shapes(list(reversed(records)))
        self.assertEqual(set(first['jointly_reverted_ids']),{'A','B'})
        self.assertEqual(first['conflicts_after'],[])
        self.assertTrue(all(r['owner_verdict']=='PENDING_OWNER_REVIEW' for r in first['final']))
        by_id={r['candidate_id']:r['geometry'] for r in second['final']}
        self.assertTrue(all(r['geometry'].equals(by_id[r['candidate_id']]) for r in first['final']))
        with self.assertRaises(ValueError):engine.simplify_shapes(records+[records[0]])

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
    
