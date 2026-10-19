import tempfile
import unittest
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box,Polygon
from shapely.ops import unary_union
from stratum_ro.regional_roofs import (OrthoMosaic,RegionalRoofConfig,plan_windows,
    deduplicate_candidates,route_surface,vectorize_automatic_masks,ground_footprint_scenarios,
    simplify_regional_roof,sample_evidence,
    remove_duplicate_consecutive_nodes,remove_spurious_interior_rings)


class RegionalRoofTests(unittest.TestCase):
    def write_tile(self,path,x,value,mask=None):
        with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=3,
            dtype='uint8',crs='EPSG:3844',transform=from_origin(x,4,1,1)) as dst:
            dst.write(np.full((3,4,4),value,dtype='uint8'))
            if mask is not None:dst.write_mask(mask.astype('uint8')*255)

    def test_cross_source_read_keeps_black_valid_and_does_not_fill_nodata(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=Path(folder)/'a.tif',Path(folder)/'b.tif'
            mask=np.ones((4,4),bool);mask[0,0]=False
            self.write_tile(a,0,0,mask);self.write_tile(b,4,160)
            rgb,valid,tr,used=OrthoMosaic([a,b]).read((0,0,8,4),1)
            self.assertTrue(valid[1,1]);self.assertTrue((rgb[1,1]==0).all())
            self.assertFalse(valid[0,0]);self.assertTrue(valid[:,4:].all())
            self.assertTrue((rgb[:,4:]==160).all());self.assertEqual(len(used),2)
            self.assertEqual(tr*(4,0),(4,4))

    def test_invalid_overlap_falls_back_to_valid_second_source(self):
        with tempfile.TemporaryDirectory() as folder:
            a,b=Path(folder)/'a.tif',Path(folder)/'b.tif'
            mask=np.ones((4,4),bool);mask[:,2:]=False
            self.write_tile(a,0,90,mask);self.write_tile(b,0,170)
            rgb,valid,_,_=OrthoMosaic([a,b]).read((0,0,4,4),1)
            self.assertTrue(valid.all());self.assertTrue((rgb[:,:2]==90).all())
            self.assertTrue((rgb[:,2:]==170).all())

    def test_read_memory_budget_and_missing_crs_are_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            a=Path(folder)/'a.tif';self.write_tile(a,0,0)
            with self.assertRaises(ValueError):OrthoMosaic([a],max_pixels=4).read((0,0,8,8),1)
            missing=Path(folder)/'missing.tif'
            with rasterio.open(missing,'w',driver='GTiff',width=4,height=4,count=3,
                dtype='uint8',transform=from_origin(0,4,1,1)) as dst:
                dst.write(np.zeros((3,4,4),dtype='uint8'))
            with self.assertRaises(ValueError):OrthoMosaic([missing])

    def test_full_extent_covered_once_by_cores_and_context_crosses_seams(self):
        config=RegionalRoofConfig(core_m=96)
        region=box(0,0,201,150);windows=plan_windows(region.bounds,config)
        cores=[box(*w['core']) for w in windows]
        self.assertAlmostEqual(unary_union(cores).area,region.area)
        self.assertAlmostEqual(sum(g.area for g in cores),region.area)
        self.assertTrue(all(box(*w['context']).contains(box(*w['core'])) for w in windows))

    def test_missing_class6_and_missing_lidar_never_drop_optical_candidate(self):
        rgb=np.full((5,5,3),120,dtype='uint8');mask=np.ones((5,5),bool)
        result=route_surface(rgb,mask,np.full((5,5),np.nan),np.zeros((5,5)))
        self.assertEqual(result['route'],'OPTICAL_UNKNOWN_REVIEW')
        self.assertIsNone(result['elevated_fraction'])
        result=route_surface(rgb,mask,np.ones((5,5))*3,np.zeros((5,5)))
        self.assertEqual(result['route'],'OPTICAL_UNKNOWN_REVIEW')

    def test_autumn_tree_height_is_not_building_identity(self):
        rgb=np.full((5,5,3),[170,100,40],dtype='uint8');mask=np.ones((5,5),bool)
        tree=route_surface(rgb,mask,np.full((5,5),12.),np.zeros((5,5)))
        self.assertEqual(tree['elevated_fraction'],1.)
        self.assertEqual(tree['route'],'OPTICAL_UNKNOWN_REVIEW')
        roof=route_surface(rgb,mask,np.full((5,5),12.),np.ones((5,5)))
        self.assertEqual(roof['route'],'ROOF_CANDIDATE_REVIEW')

    def test_invalid_edge_flag_is_retained_after_mask_clip(self):
        rgb=np.full((10,10,3),120,dtype='uint8');valid=np.ones((10,10),bool);valid[:,0]=False
        mask=np.zeros((10,10),bool);mask[2:8,0:6]=True
        record,_=vectorize_automatic_masks([dict(segmentation=mask,predicted_iou=.9,stability_score=.98)],
            rgb,valid,from_origin(0,10,1,1),np.full((10,10),np.nan),np.zeros((10,10)),RegionalRoofConfig(),'W')
        self.assertEqual(len(record),1);self.assertTrue(record[0]['touches_nodata'])
        self.assertAlmostEqual(record[0]['geometry'].area,30)

    def test_dedupe_suppresses_same_view_but_preserves_adjacent_and_small_nested_body(self):
        def item(id,g,edge=False):
            return dict(candidate_id=id,geometry=g,touches_window=edge,touches_nodata=False,
                route='ROOF_CANDIDATE_REVIEW',sam_score=.95)
        records=[item('partial',box(0,0,9,10),True),item('full',box(0,0,10,10)),
                 item('neighbor',box(10,0,20,10)),item('small_body',box(1,1,3,3))]
        kept,links=deduplicate_candidates(records)
        self.assertEqual({r['candidate_id'] for r in kept},{'full','neighbor','small_body'})
        self.assertEqual(links,[dict(suppressed='partial',retained='full')])

    def test_real_L_wing_and_courtyard_not_replaced_by_rectangle(self):
        roof=Polygon([(0,0),(20,0),(20,5),(5,5),(5,20),(0,20)])
        geom,_=simplify_regional_roof(roof)
        self.assertLess(geom.symmetric_difference(roof).area,1)
        ring=Polygon(box(0,0,20,20).exterior,[box(5,5,15,15).exterior])
        geom,_=simplify_regional_roof(ring)
        self.assertEqual(len(geom.interiors),1)

    def test_ground_footprint_requires_explicit_assumptions_and_labels_them(self):
        results=ground_footprint_scenarios(box(0,0,10,10),[.25,.5])
        self.assertAlmostEqual(results[0]['geometry'].area,90.25)
        self.assertAlmostEqual(results[1]['geometry'].area,81)
        self.assertIn('NOT_MEASURED',results[0]['status'])
        with self.assertRaises(ValueError):ground_footprint_scenarios(box(0,0,1,1),[1])

    def test_unknown_evidence_outside_coverage_stays_unknown(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'height.tif'
            with rasterio.open(path,'w',driver='GTiff',width=2,height=2,count=1,
                dtype='float32',crs='EPSG:3844',transform=from_origin(0,2,1,1),nodata=-9999) as dst:
                dst.write(np.array([[3,-9999],[4,0]],dtype='float32'),1)
            values=sample_evidence(path,from_origin(0,2,1,1),(2,4))
            self.assertEqual(values[1,1],0);self.assertTrue(np.isnan(values[0,1]))
            self.assertTrue(np.isnan(values[:,2:]).all())

    def test_remove_duplicate_consecutive_nodes(self):
        poly = Polygon([(0,0), (0,0), (10,0), (10,10), (10,10), (0,10), (0,0)])
        cleaned = remove_duplicate_consecutive_nodes(poly, tolerance=0.05)
        self.assertEqual(len(cleaned.exterior.coords), 5)
        self.assertTrue(cleaned.is_valid)

    def test_remove_spurious_interior_rings(self):
        # Exterior 20x20, one pinhole 1x1 (area 1.0 < 2.0), one genuine courtyard 4x4 (area 16.0 >= 2.0)
        ring_small = box(1, 1, 2, 2).exterior.coords
        ring_large = box(5, 5, 9, 9).exterior.coords
        poly = Polygon(box(0, 0, 20, 20).exterior.coords, [ring_small, ring_large])
        cleaned = remove_spurious_interior_rings(poly, min_hole_area=2.0)
        self.assertEqual(len(cleaned.interiors), 1)
        self.assertAlmostEqual(Polygon(cleaned.interiors[0]).area, 16.0)

    def test_extreme_containment_deduplication(self):
        # 1. Extreme containment without height difference or sub-body tag -> suppressed
        rec_main = dict(candidate_id='OPT_B_126:C1', geometry=box(0,0,20,20), sam_score=0.95, touches_window=False, touches_nodata=False)
        rec_dup = dict(candidate_id='OPT_B_174:C1', geometry=box(0,0,15,15), sam_score=0.90, touches_window=False, touches_nodata=False)
        kept, links = deduplicate_candidates([rec_main, rec_dup])
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]['candidate_id'], 'OPT_B_126:C1')
        self.assertEqual(len(links), 1)

        # 2. Extreme containment with LiDAR Delta h >= 1.5m -> retained as sub-body C2
        rec_tower = dict(candidate_id='OPT_B_174:C1', geometry=box(2,2,8,8), sam_score=0.90,
                         touches_window=False, touches_nodata=False, median_height=8.5)
        rec_base = dict(candidate_id='OPT_B_126:C1', geometry=box(0,0,20,20), sam_score=0.95,
                        touches_window=False, touches_nodata=False, median_height=3.0)
        kept2, links2 = deduplicate_candidates([rec_base, rec_tower])
        self.assertEqual(len(kept2), 2)
        self.assertEqual(len(links2), 0)
        tower_kept = next(r for r in kept2 if r['candidate_id'] == 'OPT_B_174:C1')
        self.assertTrue(tower_kept.get('is_sub_body'))
        self.assertEqual(tower_kept.get('sub_body_tier'), 'C2')

    def test_simplify_with_courtyard_and_pinholes(self):
        # Outer is 20x20 with small jitter nodes, inside has a 1x1 pinhole and a 5x5 courtyard
        coords_ext = [(0,0), (10,0.05), (20,0), (20,10.05), (20,20), (10,19.95), (0,20), (0,0)]
        pinhole = box(2, 2, 3, 3).exterior.coords
        courtyard = box(8, 8, 13, 13).exterior.coords
        poly = Polygon(coords_ext, [pinhole, courtyard])
        simplified, info = simplify_regional_roof(poly)
        self.assertIn('RECTANGLE', info['method'])
        self.assertEqual(len(simplified.interiors), 1)
        self.assertAlmostEqual(Polygon(simplified.interiors[0]).area, 25.0)


if __name__=='__main__':unittest.main()
