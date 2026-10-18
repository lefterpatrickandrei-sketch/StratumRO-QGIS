"""Regression checks for regional identity, NoData and bounded shape changes."""
import unittest
import tempfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from shapely.geometry import Polygon, box
from stratum_ro.roof_simple_geometry import simple_roof_geometry
from stratum_ro.regional_refinement import (RegionalRoofRefiner,
    RegionalRefinementConfig, scene_evidence, overlap_pairs)
from stratum_ro.api.service import PlatformService


class FlatMosaic:
    def read(self, bounds, resolution):
        a,b,c,d = bounds
        w,h = int(np.ceil((c-a)/resolution)), int(np.ceil((d-b)/resolution))
        return np.zeros((h,w,3), dtype='uint8'), np.ones((h,w),bool), from_origin(a,d,resolution,resolution), ['test']


class RefinementTests(unittest.TestCase):
    def test_black_roof_and_zero_height_remain_valid(self):
        rgb=np.zeros((8,8,3),dtype='uint8');valid=np.ones((8,8),bool)
        h=np.zeros((8,8));h[0,0]=np.nan
        e=scene_evidence(box(0,0,8,8),rgb,valid,from_origin(0,8,1,1),h)
        self.assertEqual(e['rgb_valid_fraction'],1)
        self.assertEqual(e['h90_m'],0)
        self.assertAlmostEqual(e['height_valid_fraction'],63/64)
        valid[3,3]=False
        e=scene_evidence(box(0,0,8,8),rgb,valid,from_origin(0,8,1,1),h)
        self.assertTrue(e['touches_nodata']);self.assertLess(e['rgb_valid_fraction'],1)

    def test_duplicate_observations_keep_lineage_and_distinct_nested_body(self):
        records=[dict(candidate_id='a',geometry=box(0,0,10,10)),
                 dict(candidate_id='b',geometry=box(.1,0,10.1,10)),
                 dict(candidate_id='annex',geometry=box(1,1,3,3)),
                 dict(candidate_id='neighbor',geometry=box(10.2,0,20.2,10))]
        result=RegionalRoofRefiner(FlatMosaic()).refine(records)
        self.assertEqual(len(result['duplicate_links']),1)
        self.assertEqual(len(result['baseline']),4)
        self.assertIn('annex',{r['candidate_id'] for r in result['final']})
        self.assertTrue(any(p['containment']>.99 for p in result['conflicts']))
        self.assertTrue(all(r['owner_verdict']=='PENDING_OWNER_REVIEW' for r in result['final']))
        self.assertIsNone(result['measured_accuracy'])

    def test_overlap_is_flagged_not_cut_or_union(self):
        records=[dict(candidate_id='a',geometry=box(0,0,10,10)),
                 dict(candidate_id='b',geometry=box(5,0,15,10))]
        result=RegionalRoofRefiner(FlatMosaic()).refine(records)
        self.assertEqual(len(result['conflicts']),1)
        self.assertAlmostEqual(result['conflicts'][0]['area_m2'],50)
        for r in result['final']:
            self.assertAlmostEqual(r['geometry'].area,100)
            self.assertIn('OVERLAPPING_IDENTITY_UNRESOLVED',r['review_reasons'])

    def test_courtyard_and_L_wing_survive(self):
        ring=Polygon(box(0,0,20,20).exterior,[box(5,5,15,15).exterior])
        ell=Polygon([(30,0),(50,0),(50,5),(35,5),(35,20),(30,20)])
        result=RegionalRoofRefiner(FlatMosaic()).refine([
            dict(candidate_id='court',geometry=ring),dict(candidate_id='L',geometry=ell)])
        by_id={r['candidate_id']:r for r in result['final']}
        self.assertEqual(len(by_id['court']['geometry'].interiors),1)
        self.assertAlmostEqual(by_id['L']['geometry'].area,ell.area)

    def test_strict_limits_apply_before_selecting_rectangle(self):
        shape=Polygon([(0,0),(10,0),(10,10),(6,10),(6,9),(4,9),(4,10),(0,10)])
        g,info=simple_roof_geometry(shape,min_support=.8,min_coverage=.8,max_vertices=12,
            max_boundary_distance=.2,max_area_change=.01)
        self.assertLessEqual(g.boundary.hausdorff_distance(shape.boundary),.2+1e-7)
        self.assertLessEqual(abs(g.area-shape.area)/shape.area,.01+1e-7)
        with self.assertRaises(ValueError):RegionalRefinementConfig(resolution_m=float('nan'))
        with self.assertRaises(ValueError):RegionalRefinementConfig(duplicate_iou=1.2)

    def test_source_identifiers_must_be_unique(self):
        with self.assertRaises(ValueError):
            RegionalRoofRefiner(FlatMosaic()).refine([
                dict(candidate_id='same',geometry=box(0,0,4,4)),
                dict(candidate_id='same',geometry=box(10,0,14,4))])

    def test_service_exposes_shared_engine(self):
        with tempfile.TemporaryDirectory() as folder:
            tile=Path(folder)/'rgb.tif'
            with rasterio.open(tile,'w',driver='GTiff',height=8,width=8,count=3,dtype='uint8',
                               crs='EPSG:3844',transform=from_origin(0,8,1,1)) as dst:
                dst.write(np.full((3,8,8),120,dtype='uint8'))
            engine=PlatformService().create_regional_roof_refiner([tile])
            result=engine.refine([dict(candidate_id='roof',geometry=box(2,2,6,6))])
            self.assertEqual(result['final'][0]['candidate_id'],'roof')
            self.assertAlmostEqual(result['decisions'][0]['evidence']['rgb_valid_fraction'],1)

    def test_retry_can_recover_beyond_old_mask_without_class6(self):
        class Predictor:
            def predict(self,**kwargs):
                mask=rasterize([(box(0,0,8,4),1)],out_shape=self.shape,transform=self.tr,dtype='uint8').astype(bool)
                return np.array([mask]),np.array([.95]),None
        class Segmenter:
            predictor=Predictor()
            def set_image(self,rgb,tr):self.predictor.shape=rgb.shape[:2];self.predictor.tr=tr
        original=box(0,0,4,4)
        record,audit=RegionalRoofRefiner(FlatMosaic()).retry_observation(
            dict(candidate_id='partial',geometry=original),Segmenter())
        self.assertEqual(audit['status'],'RESEGMENTED_HYPOTHESIS_PENDING_REVIEW')
        self.assertGreater(record['geometry'].bounds[2],original.bounds[2]+3)
        self.assertFalse(audit['automatic_completeness_claim'])

    def test_fidelity_option_preserves_even_small_courtyard(self):
        from stratum_ro.roof_mask_fidelity import simplify_observed_roof
        p=Polygon(box(0,0,10,10).exterior,[box(2,2,3,3).exterior])
        result,_=simplify_observed_roof(p,(5,5),min_hole_area_m2=0)
        self.assertEqual(len(result.interiors),1)

    def test_pinhole_requires_height_support_and_never_fills_nodata(self):
        from stratum_ro.roof_mask_fidelity import normalize_height_supported_pinholes
        p=Polygon(box(0,0,10,10).exterior,[box(2,2,3,3).exterior])
        valid=np.ones((20,20),bool);tr=from_origin(0,10,.5,.5)
        h=np.full(valid.shape,8.)
        g,info=normalize_height_supported_pinholes(p,valid,tr,h)
        self.assertEqual(info['removed_hole_count'],1)
        self.assertEqual(len(g.interiors),0)
        h[14:16,4:6]=0
        g,info=normalize_height_supported_pinholes(p,valid,tr,h)
        self.assertEqual(len(g.interiors),1)
        h[:]=8.;valid[14,4]=False
        g,info=normalize_height_supported_pinholes(p,valid,tr,h)
        self.assertEqual(len(g.interiors),1)

    def test_other_lot_match_is_linked_without_overwriting_existing_roof(self):
        existing=box(0,0,10,10);before=existing.wkb
        result=RegionalRoofRefiner(FlatMosaic()).refine([
            dict(candidate_id='new',geometry=box(.05,0,10.05,10))],
            existing_roofs=[dict(candidate_id='accepted_elsewhere',geometry=existing)])
        self.assertEqual(len(result['existing_lot_conflicts']),1)
        self.assertIn('ALREADY_OBSERVED_OTHER_LOT',result['final'][0]['review_reasons'])
        self.assertEqual(existing.wkb,before)


if __name__=='__main__':unittest.main()
